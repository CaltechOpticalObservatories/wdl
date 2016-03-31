# -----------------------------------------------------------------------------
# @file     wdlParser.py
# @brief    parser for the Waveform Development Language
# @author   David Hale
# @date     2016-xx-xx
# @modified 2016-03-28 DH
# @modified 2016-03-29 DH
# @modified 2016-03-31 DH output is returned instead of printed
# 
# This is the parser for the Waveform Development Language (WDL).
# -----------------------------------------------------------------------------
from __future__ import print_function
import sys
import Lexer as lexer
from Symbols import *

gotMain      = False
token        = None
sslot        = []   # SET slot
schan        = []   # SET chan
paramList    = []
paramNames   = []
subroutines  = []
level        = 0
evalTime     = 0    # evaluated time for waveform line
maxTime      = 0    # max time for each waveform
timeStamps   = {}   # dictionary of time stamps, timelabel:time
drvOutput    = ""
adcOutput    = ""
hvlOutput    = ""
hvhOutput    = ""
dioOutput    = ""
sysOutput    = ""

# -----------------------------------------------------------------------------
# @fn     dq
# @brief  wrap double quotes around a string
# @param  string, s
# @return string, s
# -----------------------------------------------------------------------------
def dq(s):
    """
    wrap double quotes around a string 's' and return quoted string
    """
    return '"%s"' %s

# -----------------------------------------------------------------------------
# @fn     getToken
# @brief  assign next token from source text to global var
# @param  none
# @return none
# -----------------------------------------------------------------------------
def getToken():
    """
    Gets the next token from the source text and assigns it to the
    global variable 'token'.
    """
    global token
    token = lexer.get()

# -----------------------------------------------------------------------------
# @fn     found
# @brief  
# @param  token type
# @return True or False
# -----------------------------------------------------------------------------
def found(argTokenType):
        """
        """
        if token.type.upper() == argTokenType.upper():
                return True
        return False

# -----------------------------------------------------------------------------
# @fn     error
# @brief  
# @param  msg
# @return none
# -----------------------------------------------------------------------------
def error(msg):
    """
    """
    token.abort(msg)

# -----------------------------------------------------------------------------
# @fn     consume
# @brief  
# @param  argTokenType
# @return none
# -----------------------------------------------------------------------------
def consume(argTokenType):
    """
    Consume a token of a given type and get the next token.
    If the current token is NOT of the expected type, then
    raise an error.
    """
    if token.type.upper() == argTokenType.upper():
        getToken()
    else:
        error("expected " + dq(argTokenType) + 
              " but got " + token.show(align=False) )

# -----------------------------------------------------------------------------
# @fn     module
# @brief  
# @param  none
# @return none
# -----------------------------------------------------------------------------
def module():
    """
    """
    global token
    module_name = token.cargo
    if   module_name == "driver"  : type = 1
    elif module_name == "ad"      : type = 2
    elif module_name == "lvbias"  : type = 3
    elif module_name == "hvbias"  : type = 4
    elif module_name == "heater"  : type = 5
    elif module_name == "hs"      : type = 7
    elif module_name == "hvxbias" : type = 8
    elif module_name == "lvxbias" : type = 9
    elif module_name == "lvds"    : type = 10
    else:
        error("unrecognized module type: " + dq(module_name))
    return(type)

# -----------------------------------------------------------------------------
# @fn     dio
# @brief  
# @param  none
# @return none
# -----------------------------------------------------------------------------
def dio(slotNumber):
    """
    """
    global token
    global dioOutput

    if found(NUMBER):
        dioChan = token.cargo
    consume(NUMBER)
    consume("[")
    while not found("]"):
        if found(NUMBER):
            source = token.cargo
        consume(NUMBER)
        consume(",")
        if found(NUMBER):
            direction = token.cargo
        consume(NUMBER)
    consume("]")
    consume(";")

    dioOutput += "MOD" + slotNumber + "\LABEL"  + dioChan + "=\n"
    dioOutput += "MOD" + slotNumber + "\SOURCE" + dioChan + "=" + source    + "\n"
    dioOutput += "MOD" + slotNumber + "\DIR"    + dioChan + "=" + direction + "\n"

# -----------------------------------------------------------------------------
# @fn     diopower
# @brief  
# @param  none
# @return none
# -----------------------------------------------------------------------------
def diopower(slotNumber):
    """
    """
    global token
    global dioOutput

    consume("=")
    while not found(";"):
        # allow a 0 or 1
        if found(NUMBER):
            if token.cargo == "0":
                diopower = "0"
            elif token.cargo == "1":
                diopower = "1"
            else:
                error("unrecognized value: " + dq(token.cargo) + "\nexpected 0 or 1")
            consume(NUMBER)
        # or "low" or "high"
        elif found(IDENTIFIER):
            if token.cargo == "low":
                diopower = "0"
            elif token.cargo == "high":
                diopower = "1"
            else:
                error("unrecognized value: " + dq(token.cargo) + "\nexpected "+dq("low")+" or "+dq("high"))
            consume(IDENTIFIER)
    consume(";")

    dioOutput += "MOD" + slotNumber + "\DIO_POWER=" + diopower + "\n"

# -----------------------------------------------------------------------------
# @fn     preampgain
# @brief  
# @param  none
# @return none
# -----------------------------------------------------------------------------
def preampgain(slotNumber):
    """
    """
    global token
    global adcOutput

    consume("=")
    while not found(";"):
        # allow a 0 or 1
        if found(NUMBER):
            if token.cargo == "0":
                preampgain = "0"
            elif token.cargo == "1":
                preampgain = "1"
            else:
                error("unrecognized value: " + dq(token.cargo) + "\nexpected 0 or 1")
            consume(NUMBER)
        # or "low" or "high"
        elif found(IDENTIFIER):
            if token.cargo == "low":
                preampgain = "0"
            elif token.cargo == "high":
                preampgain = "1"
            else:
                error("unrecognized value: " + dq(token.cargo) + "\nexpected "+dq("low")+" or "+dq("high"))
            consume(IDENTIFIER)
    consume(";")

    adcOutput += "MOD" + slotNumber + "\PREAMPGAIN=" + preampgain + "\n"

# -----------------------------------------------------------------------------
# @fn     clamp
# @brief  
# @param  none
# @return none
# -----------------------------------------------------------------------------
def clamp(slotNumber):
    """
    """
    global token
    global adcOutput

    if found(NUMBER):
        adChan = token.cargo
    consume(NUMBER)
    consume("=")
    while not found(";"):
        if found(NUMBER):
            clamp = token.cargo
        consume(NUMBER)
    consume(";")

    adcOutput += "MOD" + slotNumber + "\CLAMP" + adChan + "=" + clamp + "\n"

# -----------------------------------------------------------------------------
# @fn     hvhc
# @brief  
# @param  none
# @return none
# -----------------------------------------------------------------------------
def hvhc(slotNumber):
    """
    """
    global token
    global hvhOutput

    if found(NUMBER):
        hvhChan = token.cargo
    consume(NUMBER)
    consume("[")
    while not found("]"):
        if found(NUMBER):
            volts = token.cargo
        consume(NUMBER)
        consume(",")
        if found(NUMBER):
            current = token.cargo
        consume(NUMBER)
        consume(",")
        if found(NUMBER):
            order = token.cargo
        consume(NUMBER)
        consume(",")
        if found(NUMBER):
            enable = token.cargo
        consume(NUMBER)
    consume("]")
    consume(";")

    hvhOutput += "MOD" + slotNumber + "\LABEL"   + hvhChan + "=\n"
    hvhOutput += "MOD" + slotNumber + "\HVLC_V"  + hvhChan + "=" + volts   + "\n"
    hvhOutput += "MOD" + slotNumber + "\HVLC_IL" + hvhChan + "=" + current + "\n"
    hvhOutput += "MOD" + slotNumber + "\ORDER"   + hvhChan + "=" + order   + "\n"

# -----------------------------------------------------------------------------
# @fn     hvlc
# @brief  
# @param  none
# @return none
# -----------------------------------------------------------------------------
def hvlc(slotNumber):
    """
    """
    global token
    global hvlOutput

    if found(NUMBER):
        hvlChan = token.cargo
    consume(NUMBER)
    consume("[")
    while not found("]"):
        if found(NUMBER):
            volts = token.cargo
        consume(NUMBER)
        consume(",")
        if found(NUMBER):
            order = token.cargo
        consume(NUMBER)
    consume("]")
    consume(";")

    hvlOutput += "MOD" + slotNumber + "\LABEL"  + hvlChan + "=\n"
    hvlOutput += "MOD" + slotNumber + "\HVLC_V" + hvlChan + "=" + volts + "\n"
    hvlOutput += "MOD" + slotNumber + "\ORDER"  + hvlChan + "=" + order + "\n"

# -----------------------------------------------------------------------------
# @fn     drv
# @brief  
# @param  none
# @return none
# -----------------------------------------------------------------------------
def drv(slotNumber):
    """
    """
    global token
    global drvOutput

    if found(NUMBER):
        drvChan = token.cargo
    consume(NUMBER)
    consume("[")
    while not found("]"):
        if found(NUMBER):
            slewfast = token.cargo
        consume(NUMBER)
        consume(",")
        if found(NUMBER):
            slewslow = token.cargo
        consume(NUMBER)
        consume(",")
        if found(NUMBER):
            enable = token.cargo
        consume(NUMBER)
    consume("]")
    consume(";")

    drvOutput += "MOD" + slotNumber + "\LABEL"        + drvChan + "=\n"
    drvOutput += "MOD" + slotNumber + "\ENABLE"       + drvChan + "=" + enable   + "\n"
    drvOutput += "MOD" + slotNumber + "\FASTSLEWRATE" + drvChan + "=" + slewfast + "\n"
    drvOutput += "MOD" + slotNumber + "\SLOWSLEWRATE" + drvChan + "=" + slewslow + "\n"

# -----------------------------------------------------------------------------
# @fn     slot
# @brief  
# @param  none
# @return none
# -----------------------------------------------------------------------------
def slot():
    """
    """
    global token
    global sysOutput

    consume("SLOT")

    if found(NUMBER):
        slotNumber = token.cargo
    consume(NUMBER)

    if found(IDENTIFIER):
        type = module()
    consume(IDENTIFIER)

    # Then, until the end of the waveform (delimited by curly brace),
    # check for the waveform rules.
    consume("{")
    while not found("}"):
        if found("DRV"):
            consume("DRV")
            drv(slotNumber)
        elif found("CLAMP"):
            consume("CLAMP")
            clamp(slotNumber)
        if found("PREAMPGAIN"):
            consume("PREAMPGAIN")
            preampgain(slotNumber)
        if found("HVLC"):
            consume("HVLC")
            hvlc(slotNumber)
        if found("HVHC"):
            consume("HVHC")
            hvhc(slotNumber)
        if found("DIO"):
            consume("DIO")
            dio(slotNumber)
        if found("DIOPOWER"):
            consume("DIOPOWER")
            diopower(slotNumber)
        else:
            getToken()
    consume("}")

    # build up the information for a .system file
    sysOutput += "MOD" + slotNumber + "_ID=0000000000000000\n"
    sysOutput += "MOD" + slotNumber + "_REV=0\n"
    sysOutput += "MOD" + slotNumber + "_VERSION=0.0.0\n"
    sysOutput += "MOD" + slotNumber + "_TYPE=" + str(type) + "\n"

    return

# -----------------------------------------------------------------------------
# @fn     timelabel
# @brief  
# @param  none
# @return none
# -----------------------------------------------------------------------------
def timelabel():
    """
    """
    global token
    global timeStamps
    global evalTime

    # if there is an equal sign then a label has been assigned to this time
    if found("="):
        consume("=")
        # Store the time at this time stamp label in a dictionary, label:time
        # for later retrieval (used in the time() function).
        timeStamps[token.cargo] = evalTime
        consume(IDENTIFIER)

# -----------------------------------------------------------------------------
# @fn     time
# @brief  evaluate the time stamp for each entry in the waveform
# @param  none
# @return none
# -----------------------------------------------------------------------------
def time():
    """
    evaluate the time stamp for each entry in the waveform
    """
    global evalTime
    global maxTime
    global timeStamps

    if found("SET"):       # If no time found, then this waveform happens at the
        return             # same time as the previous line, so just return.

    # init an equation from which the time will be calculated

    if found(".+"):        # start new equation with the last eval time
        eqn = str(evalTime) + "+"
        consume(".+")
    else:                  # or start anew
        eqn = ""

    # form an equation from which the time will be evaluated using everything up to the ":"
    while not found(":"):
        if found(IDENTIFIER):
            # if we found a time stamp label then get its actual time from the dictionary
            if token.cargo in timeStamps:
                eqn += str( timeStamps[token.cargo] )
            else:
                print( "Unresolved symbol " + dq(token.cargo), file=sys.stderr )
            consume(IDENTIFIER)
        else:
            eqn += token.cargo   # if not a label then we have a number or an arithmetic symbol
            getToken()
    consume(":")
    evalTime = int( eval(eqn) )  # new evaluated time

    # need to remember the max time, for the RETURN
    if evalTime > maxTime:
        maxTime = evalTime

# -----------------------------------------------------------------------------
# @fn     set
# @brief  
# @param  none
# @return none
# -----------------------------------------------------------------------------
def set():
    """
    """
    global sslot
    global schan
    sslot = []
    schan = []

    consume("SET")

    # may be a set enclosed in square brackets
    if found("["):
        consume("[")

    while not found(","):
        if found (NUMBER):
            sslot.append(token.cargo)
        consume(NUMBER)
        consume(":")
        if found (NUMBER):
            schan.append(token.cargo)
        consume(NUMBER)

        if found(","):
            consume(",")
        else:
            break
    if found("]"):
        consume("]")

# -----------------------------------------------------------------------------
# @fn     to
# @brief  
# @param  none
# @return none
# -----------------------------------------------------------------------------
def to():
    """
    """
    global level

    consume("TO")
    # could be a negative number...
    if found("-"):
        # if so, consume the sign and remember it
        consume("-")
        sign=-1.0
    else:
        sign=1.0
    if found(NUMBER):
        # multiply the value by the sign from above (hehe)
        level = str( sign * float(token.cargo) )
    consume(NUMBER)

# -----------------------------------------------------------------------------
# @fn     eol
# @brief  check for end-of-line character
# @param  none
# @return none
# -----------------------------------------------------------------------------
def eol():
    """
    check for the end-of-line character (semi-colon)
    """
    consume(";")

# -----------------------------------------------------------------------------
# @fn     waverules
# @brief  rules for defining a waveform
# @param  none
# @return none
# -----------------------------------------------------------------------------
def waverules():
    """
    These are the rules for defining a waveform:

        [time]: [=timelabel] SET signallabel TO level;
 
        time: at least one time label is required, followed by colon
              (if omitted then SET... lines are all at the same time as previous time)
              arithmetic operations are allowed for time
              units are allowed to follow numbers, E.G. ns, us, ms
              ".+" means to add to the previous time
 
        =timelabel is an optional label for this time, which can be used elsewhere
 
        SET signallabel TO level; 
        is required and must end with a semi-colon
        signallabel and level can be defined anywhere
    """
    time()
    timelabel()
    set()
    to()
    eol()

# -----------------------------------------------------------------------------
# @fn     wavelabel
# @brief  
# @param  none
# @return none
# -----------------------------------------------------------------------------
def wavelabel():
    """
    """
    if found(IDENTIFIER):
        waveformName = token.cargo
    else:
        print( "missing waveform label", file=sys.stderr )
        waveformName = ""
    consume(IDENTIFIER)
    return waveformName

# -----------------------------------------------------------------------------
# @fn     waveform
# @brief  waveform definition
# @param  none
# @return none
# -----------------------------------------------------------------------------
def waveform():
    """
    waveform definition
    """
    global token
    global evalTime
    global maxTime
    global level

    outputText = ""
    maxTime    = 0

    # a waveform must start with the "WAVEFORM" keyword, ...
    consume("WAVEFORM")

    # ...followed by a label for the waveform.
    waveformName = wavelabel()
    outputText   += "waveform " + waveformName + ":" + "\n"

    # Then, until the end of the waveform (delimited by curly brace),
    # check for the waveform rules.
    consume("{")
    while not found("}"):
        waverules()
        for index in range(len(sslot)):
            outputText += str(evalTime)     + " " +\
                          str(sslot[index]) + " " +\
                          str(schan[index]) + " " +\
                          str(level)        + "\n"
    consume("}")

    # "RETURN" marks the end of the waveform output
    outputText += str(maxTime+1) + " RETURN " + waveformName + "\n\n"
    return outputText

# -----------------------------------------------------------------------------
# @fn     sequence_label
# @brief  
# @param  none
# @return sequence name
# -----------------------------------------------------------------------------
def sequence_label():
    """
    """
    global token

    if found(IDENTIFIER):
        name = token.cargo
    else:
        name = ""
    consume(IDENTIFIER)
    return name

# -----------------------------------------------------------------------------
# @fn     generic_sequence
# @brief  
# @param  optional sequenceName
# @return none
# 
# The optional sequenceName parameter is used for the RETURN statement,
# when applicable.
# -----------------------------------------------------------------------------
def generic_sequence(*sequenceName):
    """
    """
    global token
    # sequence/waveform must start with an open (left) curly brace, {
    consume("{")
    outputText = ""
    # process until end-of-sequence
    while not found("}"):
        sequenceLine = ""
        # process until end-of-line
        while not found(";"):
            if  ( found(IDENTIFIER) ) and \
                ( token.cargo not in subroutines ) and \
                ( token.cargo not in paramNames ):
                error("undefined symbol " + token.show(align=False) )
            # If token is in the list of subroutines then it must be CALLed
            # and must be followed by parentheses and an optional number
            if token.cargo in subroutines:
                sequenceLine += "CALL " + token.cargo
                consume(IDENTIFIER)
                consume("(")
                # if the next token isn't a closing paren then assume it's a number or param
                if not found(")"):
                    sequenceLine += "(" + token.cargo #+ ")"
            elif found("RETURN"):
                consume("RETURN")
                outputText += "RETURN " + sequenceName[0] + "\n"
                break
            else:
                sequenceLine += token.cargo
            getToken()
            # if next token not a symbol then pad with a space
            if token.cargo not in TwoCharacterSymbols and \
               token.cargo not in OneCharacterSymbols:
                sequenceLine += " "
        # line must end with a semi-colon
        consume(";")
        # won't normally have a 0-length sequenceLine, but could happen during testing
        if len(sequenceLine) > 0:
            outputText += sequenceLine + "\n"
    # sequence/waveform must end with an close (right) curly brace, }
    consume("}")
    return outputText

# -----------------------------------------------------------------------------
# @fn     sequence
# @brief  
# @param  none
# @return none
# -----------------------------------------------------------------------------
def sequence():
    """
    """
    global token
    global subroutines

    sequenceName = sequence_label()
    outputText = "sequence " + sequenceName + ":" + "\n"
    outputText += generic_sequence(sequenceName) + "\n"
    return outputText

# -----------------------------------------------------------------------------
# @fn     main
# @brief  
# @param  none
# @return none
# -----------------------------------------------------------------------------
def main():
    """
    MAIN is a special sequence which is an infinite loop. Every script has
    a MAIN and every MAIN has a goto MAIN.
    """
    global token
    global gotMain

    if gotMain:
        error("cannot have more than one MAIN")

    consume("MAIN")
    outputText = "sequence MAIN:" + "\n"
    outputText += generic_sequence()
    outputText += "GOTO MAIN" + "\n"
    gotMain = True
    return outputText

# -----------------------------------------------------------------------------
# @fn     parse_waveform
# @brief  
# @param  sourceText
# @return none
# -----------------------------------------------------------------------------
def parse_waveform(sourceText):
    """
    """
    global token

    lexer.initialize(sourceText)

    while True:
        getToken()
        if token.type == EOF: break
        waveform()

# -----------------------------------------------------------------------------
# @fn     param
# @brief  pulls out params from anywhere in .seq file and stores in a list
# @param  none
# @return none
# -----------------------------------------------------------------------------
def param():
    """
    """
    global token
    global paramList
    global paramNames

    line = "parameter "
    consume("param")
    paramNames.append(token.cargo)
    line += token.cargo
    consume(IDENTIFIER)
    line += token.cargo
    consume("=")
    line += token.cargo
    consume(NUMBER)
    paramList.append(line)

# -----------------------------------------------------------------------------
# @fn     parse_sequence
# @brief  
# @param  sourceText
# @return none
# -----------------------------------------------------------------------------
def parse_sequence(sourceText):
    """
    """
    global token
    global paramList

    lexer.initialize(sourceText)

    getToken()
    param()
    main()

    while True:
        getToken()
        if token.type == EOF: break
        param()
        sequence()

# -----------------------------------------------------------------------------
# @fn     get_subroutines
# @brief  
# @param  sourceText
# @return none
# -----------------------------------------------------------------------------
def get_subroutines(sourceText):
    """
    """
    global token
    global subroutines

    lexer.initialize(sourceText)

    subroutines = []

    while True:
        getToken()
        if token.type == EOF: break
        if found(IDENTIFIER):
            name = token.cargo
            consume(IDENTIFIER)
            if found("{"):
                subroutines.append(name)
                consume("{")
                while not found("}"):
                    getToken()

    return subroutines

# -----------------------------------------------------------------------------
# @fn     get_params
# @brief  
# @param  sourceText
# @return none
# -----------------------------------------------------------------------------
def get_params(sourceText):
    """
    """
    global token
    global paramNames

    lexer.initialize(sourceText)

    while True:
        getToken()
        if token.type == EOF: break
        if found("param"):
            consume("param")
            paramNames.append(token.cargo)
            consume(IDENTIFIER)
            consume("=")
            consume(NUMBER)

    return paramNames

# -----------------------------------------------------------------------------
# @fn     parse_modules
# @brief  
# @param  sourceText
# @return none
# -----------------------------------------------------------------------------
def parse_modules(sourceText):
    """
    """
    global token
    global drvOutput
    global adcOutput
    global hvlOutput
    global hvhOutput
    global sysOutput

    lexer.initialize(sourceText)

    # initialize the system output string
    sysOutput = ""
    sysOutput += "BACKPLANE_ID=0000000000000000\n"
    sysOutput += "BACKPLANE_REV=0\n"
    sysOutput += "BACKPLANE_TYPE=1\n"
    sysOutput += "BACKPLANE_VERSION=0.0.0\n"

    getToken()
    while True:
        if token.type == EOF:
            break
        elif found("SLOT"):
            slot()
        else:
            error("unrecognized token " + token.show(align=False) )
            break

    retval = ""
    retval += drvOutput
    retval += adcOutput
    retval += hvlOutput
    retval += hvhOutput
    retval += dioOutput

    return retval

# -----------------------------------------------------------------------------
# @fn     parse_system
# @brief  
# @param  sourceText
# @return none
# -----------------------------------------------------------------------------
def parse_system():
    """
    """
    global sysOutput
    return sysOutput

# -----------------------------------------------------------------------------
# @fn     parse
# @brief  parses everything
# @param  sourceText
# @return none
# -----------------------------------------------------------------------------
def parse(sourceText):
    """
    """
    global token
    global paramList

    lexer.initialize(sourceText)

    waveformText = ""
    sequenceText = ""
    mainText     = ""

    getToken()
    while True:
        if token.type == EOF:
            break
        elif found("WAVEFORM"):
            waveformText += waveform()
        elif found("param"):
            param()
        elif found("MAIN"):
            mainText = main()
        elif found(IDENTIFIER):
            sequenceText += sequence()
        else:
            error("unrecognized token " + token.show(align=False) )
            break

    retval =""
    retval += mainText
    retval += sequenceText
    retval += waveformText
    for p in paramList:
        retval += p + "\n"

    return retval
