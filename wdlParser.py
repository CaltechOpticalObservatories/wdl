# -----------------------------------------------------------------------------
# @file     wdlParser.py
# @brief    parser for the Waveform Development Language
# @author   David Hale
# @date     2016-xx-xx
# @modified 2016-03-28 DH
# @modified 2016-03-29 DH
# @modified 2016-03-31 DH output is returned instead of printed
# @modified 2016-04-04 DH implement make_include in support of .conf files
# @modified 2016-04-05 DH waveform output written differently depending on slew
# @modified 2016-04-07 DH additional error checking of inputs
# @modified 2016-04-18 DH implement GOTO
# 
# This is the parser for the Waveform Development Language (WDL).
# -----------------------------------------------------------------------------
from __future__ import print_function
import sys
sys.dont_write_bytecode = True
import Lexer as lexer
from Symbols import *

class ParserError(Exception): pass

gotMain      = False
token        = None
setSlot      = []   # SET slot
setChan      = []   # SET chan
setSlew      = -1   # SET slew
setLevel     = 0
paramList    = []
paramNames   = []
subroutines  = []
evalTime     = 0    # evaluated time for waveform line
maxTime      = 0    # max time for each waveform
timeStamps   = {}   # dictionary of time stamps, timelabel:time
drvOutput    = ""
adcOutput    = ""
hvlOutput    = ""
hvhOutput    = ""
dioOutput    = ""
sysOutput    = ""

__SLEW_FAST  =  1
__SLEW_SLOW  =  0
__SLEW_NONE  = -1

# -----------------------------------------------------------------------------
# @fn     abort
# @brief  throw a parser error
# @param  self, msg
# @return none
# -----------------------------------------------------------------------------
def abort(self, msg):
    """
    throw a parser error
    """
    raise ParserError(msg)

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
# @brief  returns True if the current token type matches the parameter
# @param  token type
# @return True or False
# -----------------------------------------------------------------------------
def found(argTokenType):
        """
        returns True if the current token type matches the parameter
        """
        if token.type.upper() == argTokenType.upper():
                return True
        return False

# -----------------------------------------------------------------------------
# @fn     error
# @brief  abort the parsing process
# @param  msg
# @return none
# -----------------------------------------------------------------------------
def error(msg):
    """
    abort the parsing process
    """
    token.abort(msg)

# -----------------------------------------------------------------------------
# @fn     consume
# @brief  consume a token of the specified type and get the next token
# @param  argTokenType
# @return none
# -----------------------------------------------------------------------------
def consume(argTokenType):
    """
    Consume a token of a given type and get the next token.
    If the current token is NOT of the expected type, then
    throw an error.
    """
    if token.type.upper() == argTokenType.upper():
        getToken()
    else:
        error("expected " + argTokenType + 
              " but got " + token.show(align=False) )

# -----------------------------------------------------------------------------
# @fn     module
# @brief  return an integer type for the module of the current token
# @param  none
# @return integer module type
# -----------------------------------------------------------------------------
def module():
    """
    return an integer type for the module of the current token
    """
    global token
    module_name = token.cargo
    # convert all comparisons to upper for case-insensitivity
    if   module_name.upper() == "DRIVER"  : type = 1
    elif module_name.upper() == "AD"      : type = 2
    elif module_name.upper() == "LVBIAS"  : type = 3
    elif module_name.upper() == "HVBIAS"  : type = 4
    elif module_name.upper() == "HEATER"  : type = 5
    elif module_name.upper() == "HS"      : type = 7
    elif module_name.upper() == "HVXBIAS" : type = 8
    elif module_name.upper() == "LVXBIAS" : type = 9
    elif module_name.upper() == "LVDS"    : type = 10
    else:
        error("unrecognized module type: " + dq(module_name))
    return(type)

# -----------------------------------------------------------------------------
# @fn     dio
# @brief  rules for the DIO keyword
# @param  string slotNumber
# @return none, appends to global variable "dioOutput"
# -----------------------------------------------------------------------------
def dio(slotNumber):
    """
    These are the rules for the DIO keyword, encountered while parsing
    the SLOT command for the modules (.mod) file. Required format is
    DIO # [#,#];

    where # is any number
    format of numbers is channel [source, direction]
    """
    global token
    global dioOutput

    if found(NUMBER):
        dioChan = token.cargo
        if int(dioChan) < 1 or int(dioChan) > 4:
            error("DIO channel " + dq(dioChan) + " outside range [1..4]")
    consume(NUMBER)
    consume("[")
    while not found("]"):
        if found(NUMBER):
            source = token.cargo
            if source != "0" and source != "1" and source != "2" and source != "3":
                error("DIO source " + dq(source) + " must be 0, 1, 2 or 3")
        consume(NUMBER)
        consume(",")
        if found(NUMBER):
            direction = token.cargo
            if direction != "0" and direction != "1":
                error("DIO direction " + dq(direction) + " must be 0 or 1")
        consume(NUMBER)
    consume("]")
    consume(";")

#    dioOutput += "MOD" + slotNumber + "\DIO_LABEL"  + dioChan + "=\n"
    dioOutput += "MOD" + slotNumber + "\DIO_SOURCE" + dioChan + "=" + source    + "\n"
    dioOutput += "MOD" + slotNumber + "\DIO_DIR"    + dioChan + "=" + direction + "\n"

# -----------------------------------------------------------------------------
# @fn     diopower
# @brief  rules for the DIOPOWER keyword
# @param  string slotNumber
# @return none, appends to global variable "dioOutput"
# -----------------------------------------------------------------------------
def diopower(slotNumber):
    """
    These are the rules for the DIOPOWER keyword, encountered while parsing
    the SLOT command for the modules (.mod) file. Required format is
    DIOPOWER=?;

    where ? is 0,1,enabled,disabled
    """
    global token
    global dioOutput

    consume("=")
    while not found(";"):
        # if it's a number then allow a 0 or 1
        if found(NUMBER):
            if token.cargo == "0":
                diopower = "0"
            elif token.cargo == "1":
                diopower = "1"
            else:
                error("unrecognized value: " + dq(token.cargo) + "\nexpected 0 or 1")
            consume(NUMBER)
        # or "enabled" or "disabled", convert to upper for case-insensitivity
        elif found(IDENTIFIER):
            if token.cargo.upper() == "ENABLED":
                diopower = "0"
            elif token.cargo.upper() == "DISABLED":
                diopower = "1"
            else:
                error("unrecognized value: " + dq(token.cargo) +\
                      "\nexpected "+dq("low")+" or "+dq("high"))
            consume(IDENTIFIER)
    consume(";")

    dioOutput += "MOD" + slotNumber + "\DIO_POWER=" + diopower + "\n"

# -----------------------------------------------------------------------------
# @fn     preampgain
# @brief  rules for the PREAMPGAIN keyword
# @param  string slotNumber
# @return none, appends to global variable "adcOutput"
# -----------------------------------------------------------------------------
def preampgain(slotNumber):
    """
    These are the rules for the PREAMPGAIN keyword, encountered while parsing
    the SLOT command for the modules (.mod) file. Required format is
    PREAMPGAIN=?;

    where ? is 0,1,low,high
    """
    global token
    global adcOutput

    consume("=")
    while not found(";"):
        # if it's a number then allow a 0 or 1
        if found(NUMBER):
            if token.cargo == "0":
                preampgain = "0"
            elif token.cargo == "1":
                preampgain = "1"
            else:
                error("unrecognized value: " + dq(token.cargo) + "\nexpected 0 or 1")
            consume(NUMBER)
        # or "low" or "high", converted to upper for case-insensitivity
        elif found(IDENTIFIER):
            if token.cargo.upper() == "LOW":
                preampgain = "0"
            elif token.cargo.upper() == "HIGH":
                preampgain = "1"
            else:
                error("unrecognized value: " + dq(token.cargo) +\
                      "\nexpected "+dq("low")+" or "+dq("high"))
            consume(IDENTIFIER)
    consume(";")

    adcOutput += "MOD" + slotNumber + "\PREAMPGAIN=" + preampgain + "\n"

# -----------------------------------------------------------------------------
# @fn     clamp
# @brief  rules for the CLAMP keyword
# @param  string slotNumber
# @return none, appends to global variable "adcOutput"
# -----------------------------------------------------------------------------
def clamp(slotNumber):
    """
    These are the rules for the CLAMP keyword, encountered while parsing
    the SLOT command for the modules (.mod) file. Required format is
    CLAMP #=#;

    where ? is any number
    format of numbers is channel=level
    """
    global token
    global adcOutput

    if found(NUMBER):
        adChan = token.cargo
        if int(adChan) < 1 or int(adChan) > 4:
            error("CLAMP channel " + dq(adChan) + " outside range [1..4]")
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
# @brief  rules for the HVHC keyword
# @param  string slotNumber
# @return none, appends to the global variable "hvhOutput"
# -----------------------------------------------------------------------------
def hvhc(slotNumber):
    """
    These are the rules for the HVHC keyword, encountered while parsing
    the SLOT command for the modules (.mod) file. Required format is
    HVHC # [#,#,#,#];

    where # is any number
    format of numbers is channel [volts, current_limit, order, enable]
    """
    global token
    global hvhOutput

    if found(NUMBER):
        hvhChan = token.cargo
        if int(hvhChan) < 1 or int(hvhChan) > 6:
            error("HVHC channel " + dq(hvhChan) + " outside range [1..6]")
    consume(NUMBER)
    consume("[")
    while not found("]"):
        if found(NUMBER):
            volts = token.cargo
            if float(volts) < 0 or float(volts) > 31:
                error("HVHC volts " + dq(volts) + " outside range [0..31] V")
        consume(NUMBER)
        consume(",")
        if found(NUMBER):
            current = token.cargo
            if float(current) < 0 or float(current) > 250:
                error("HVHC current " + dq(current) + " outside range [0..250] mA")
        consume(NUMBER)
        consume(",")
        if found(NUMBER):
            order = token.cargo
            if int(order) < 0 or int(order) > 6:
                error("HVHC order " + dq(order) + " outside range [0..6]")
        consume(NUMBER)
        consume(",")
        if found(NUMBER):
            enable = token.cargo
            if enable != "0" and enable != "1":
                error("HVHC enable " + dq(enable) + " must be 0 or 1")
        consume(NUMBER)
    consume("]")
    consume(";")

#    hvhOutput += "MOD" + slotNumber + "\HVHC_LABEL"   + hvhChan + "=\n"
    hvhOutput += "MOD" + slotNumber + "\HVHC_V"  + hvhChan + "=" + volts   + "\n"
    hvhOutput += "MOD" + slotNumber + "\HVHC_IL" + hvhChan + "=" + current + "\n"
    hvhOutput += "MOD" + slotNumber + "\HVHC_ORDER"   + hvhChan + "=" + order   + "\n"

# -----------------------------------------------------------------------------
# @fn     hvlc
# @brief  rules for the HVHC keyword
# @param  string slotNumber
# @return none, appends to the global variable "hvlOutput"
# -----------------------------------------------------------------------------
def hvlc(slotNumber):
    """
    These are the rules for the HVLC keyword, encountered while parsing
    the SLOT command for the modules (.mod) file. Required format is
    HVLC # [#,#];

    where # is any number
    format of numbers is [volts, order]
    """
    global token
    global hvlOutput

    if found(NUMBER):
        hvlChan = token.cargo
        if int(hvlChan) < 1 or int(hvlChan) > 24:
            error("HVLC channel " + dq(hvlChan) + " outside range [1..24]")
    consume(NUMBER)
    consume("[")
    while not found("]"):
        if found(NUMBER):
            volts = token.cargo
            if float(volts) < 0 or float(volts) > 31:
                error("HVLC volts " + dq(volts) + " outside range [0..31] V")
        consume(NUMBER)
        consume(",")
        if found(NUMBER):
            order = token.cargo
            if int(order) < 0 or int(order) > 24:
                error("HVLC order " + dq(order) + " outside range [0..24]")
        consume(NUMBER)
    consume("]")
    consume(";")

#    hvlOutput += "MOD" + slotNumber + "\HVLC_LABEL"  + hvlChan + "=\n"
    hvlOutput += "MOD" + slotNumber + "\HVLC_V" + hvlChan + "=" + volts + "\n"
    hvlOutput += "MOD" + slotNumber + "\HVLC_ORDER"  + hvlChan + "=" + order + "\n"

# -----------------------------------------------------------------------------
# @fn     drv
# @brief  rules for the DRV keyword
# @param  string slotNumber
# @return none, appends to the global variable "drvOutput"
# -----------------------------------------------------------------------------
def drv(slotNumber):
    """
    These are the rules for the DRV keyword, encountered while parsing
    the SLOT command for the modules (.mod) file. Required format is
    DRV # [#,#,#];

    where # is any number
    format of numbers is [slewfast, slewslow, enable]
    """
    global token
    global drvOutput

    if found(NUMBER):
        drvChan = token.cargo
        if int(drvChan) < 0 or int(drvChan) > 8:
            error("DRV channel " + dq(drvChan) + " outside range [1..8]")
    consume(NUMBER)
    consume("[")
    while not found("]"):
        if found(NUMBER):
            slewfast = token.cargo
            if float(slewfast) < 0.001 or float(slewfast) > 1000:
                error("DRV Fast Slew Rate " + dq(slewfast) + " outside range [0.001..1000] V/us")
        consume(NUMBER)
        consume(",")
        if found(NUMBER):
            slewslow = token.cargo
            if float(slewslow) < 0.001 or float(slewslow) > 1000:
                error("DRV Slow Slew Rate " + dq(slewslow) + " outside range [0.001..1000] V/us")
        consume(NUMBER)
        consume(",")
        if found(NUMBER):
            enable = token.cargo
            if enable != "0" and enable != "1":
                error("DRV enable " + dq(enable) + " must be 0 or 1")
        consume(NUMBER)
    consume("]")
    consume(";")

#    drvOutput += "MOD" + slotNumber + "\LABEL"        + drvChan + "=\n"
    drvOutput += "MOD" + slotNumber + "\ENABLE"       + drvChan + "=" + enable   + "\n"
    drvOutput += "MOD" + slotNumber + "\FASTSLEWRATE" + drvChan + "=" + slewfast + "\n"
    drvOutput += "MOD" + slotNumber + "\SLOWSLEWRATE" + drvChan + "=" + slewslow + "\n"

# -----------------------------------------------------------------------------
# @fn     slot
# @brief  rules for the SLOT Keyword
# @param  none
# @return none
# -----------------------------------------------------------------------------
def slot():
    """
    These are the rules for the SLOT keyword, encountered while parsing
    the modules (.mod) file. Required format is

    SLOT # type { param }

    where param is DRV, CLAMP, PREAMPGAIN, HVLC, HVHC, DIO, DIOPOWER
                followed by param specific rules,
          type  is a valid Archon module type,
          #     is any number.
    """
    global token
    global sysOutput

    consume("SLOT")

    if found(NUMBER):
        slotNumber = token.cargo
        if int(slotNumber) < 1 or int(slotNumber) > 12:
            error("SLOT " + dq(slotNumber) + " outside range [1..12]")
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
            pass
    consume("}")

    # Build up the information for a .system file --
    # Values of ID, REV, VERSION don't matter, but they need to be defined if the
    # resultant .acf file is to be loaded by the GUI without an error. The important
    # value here is the TYPE, so that the correct tabs are created.
    sysOutput += "MOD" + slotNumber + "_ID=0000000000000000\n"
    sysOutput += "MOD" + slotNumber + "_REV=0\n"
    sysOutput += "MOD" + slotNumber + "_VERSION=0.0.0\n"
    sysOutput += "MOD" + slotNumber + "_TYPE=" + str(type) + "\n"

    return

# -----------------------------------------------------------------------------
# @fn     timelabel
# @brief  when a time label is encountered, store the time in a dictionary
# @param  none
# @return none
# -----------------------------------------------------------------------------
def timelabel():
    """
    When a time label is encountered in the waveform, store the time in a 
    dictionary under that given label.
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
    Evaluate the time stamp for each entry in the waveform.
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
            eqn += token.cargo   # if not a label then we have a number or math symbol
            getToken()
    consume(":")
    evalTime = int( eval(eqn) )  # new evaluated time

    # need to remember the max time, for the RETURN
    if evalTime > maxTime:
        maxTime = evalTime

# -----------------------------------------------------------------------------
# @fn     set
# @brief  rules for the SET keyword
# @param  none
# @return none
# -----------------------------------------------------------------------------
def set():
    """
    These are the rules for the SET keyword, encountered while parsing
    waveforms. Format is

    SET signallabel TO level [,slew]

    see waverules() for more details.
    """
    global setSlot
    global setChan
    setSlot = []
    setChan = []

    consume("SET")

    # may be a set enclosed in square brackets (but isn't required)
    if found("["):
        consume("[")

    while not found(","):
        # SLOT
        if found (NUMBER):
            setSlot.append(token.cargo)
        consume(NUMBER)
        consume(":")
        # CHANNEL
        if found (NUMBER):
            setChan.append(token.cargo)
        consume(NUMBER)

        # There can be a list of SLOT:CHAN, SLOT:CHAN within the [brackets]
        # so consume the comma and continue, if there is one,
        if found(","):
            consume(",")
        # otherwise get out of the loop if there is no list.
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
    global setLevel

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
        setLevel = str( sign * float(token.cargo) )
    consume(NUMBER)

# -----------------------------------------------------------------------------
# @fn     slew
# @brief  
# @param  none
# @return none
# -----------------------------------------------------------------------------
def slew():
    """
    """
    global setSlew

    # If the next token isn't a comma then there is no slew rate,
    # I.E. this isn't a driver, so flag as such (-1) and return
    if not found(","):
        setSlew = __SLEW_NONE
        return

    # otherwise continue, flag as fast (1) or slow (0)
    consume(",")
    if found("SLOW"):
        consume("SLOW")
        setSlew = __SLEW_SLOW
    elif found("FAST"):
        consume("FAST")
        setSlew = __SLEW_FAST
    else:
        error("expected SLOW | FAST but got: " + dq(token.cargo))

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

        [time]: [=timelabel] SET signallabel TO level [,slew];
 
        time: at least one time label is required, followed by colon
              (if omitted then SET... lines are all at the same time as previous time)
              arithmetic operations are allowed for time
              units are allowed to follow numbers, E.G. ns, us, ms
              ".+" means to add to the previous time
 
        =timelabel is an optional label for this time, which can be used elsewhere
 
        SET signallabel TO level; 
        is required and must end with a semi-colon

        signallabel and level can be defined anywhere and is of the form
        slot:chan or a list of [slot:chan, slot:chan, ...]
        and level is a voltage

        slew is an optional "fast" or "slow" and selects which of the slew
        rates, defined in the .mod file, to be used for this particular state
        (applicable only to driver outputs).
    """
    time()
    timelabel()
    set()
    to()
    slew()
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
    global setLevel
    global setSlew

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
        for index in range(len(setSlot)):
            # The output is written differently depending on whether or not
            # a slew rate (fast | slow) has been specified.
            if (setSlew == __SLEW_NONE):
                outputText += str(evalTime)                + " " +\
                              str(setSlot[index])          + " " +\
                              str(int(setChan[index])-1)   + " " +\
                              str(setLevel)                + "\n"
            else:
                outputText += str(evalTime)                + " " +\
                              str(setSlot[index])          + " " +\
                              str(2*int(setChan[index])-2) + " " +\
                              str(setLevel)                + "\n"
                outputText += str(evalTime)                + " " +\
                              str(setSlot[index])          + " " +\
                              str(2*int(setChan[index])-1) + " " +\
                              str(setSlew)                 + "\n"
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
            # If token is a GOTO then the next token must be in the list
            # of subroutines() with open and close parentheses and nothing else
            if found("GOTO"):
                consume("GOTO")
                # Check next token against list of subroutines
                if token.cargo not in subroutines:
                    error("undefined waveform or sequence: " + dq(token.cargo))
                else:
                    sequenceLine += "GOTO " + token.cargo
                    # then consume the IDENTIFIER and the open/close parentheses
                    # and break, because that's it for the line.
                    consume(IDENTIFIER)
                    consume("(")
                    consume(")")
                    break
            # If token is in the list of subroutines then it must be CALLed
            # and must be followed by parentheses and an optional number
            if token.cargo in subroutines:
                sequenceLine += "CALL " + token.cargo
                consume(IDENTIFIER)
                consume("(")
                # if next token isn't a closing paren then assume it's a number or param
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
    a MAIN (and only one MAIN) and every MAIN has an implicit goto MAIN (which
    is forced to be explicit, here).
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
    moduleFile   = ""
    signalFile   = ""

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
        elif found("MODULE_FILE"):
            consume("MODULE_FILE")
            moduleFile = token.cargo.strip('"')
            consume(STRING)
        elif found("SIGNAL_FILE"):
            consume("SIGNAL_FILE")
            signalFile = token.cargo.strip('"')
            consume(STRING)
        else:
            error("unrecognized token " + token.show(align=False) )
            break

    if not gotMain:
        error("must define at least one MAIN in the .seq file")

    retval =""
    retval += "modulefile " + moduleFile + "\n"
    retval += "signalfile " + signalFile + "\n\n"
    retval += mainText
    retval += sequenceText
    retval += waveformText
    for p in paramList:
        retval += p + "\n"

    return retval

# -----------------------------------------------------------------------------
# @fn     make_include
# @brief  
# @param  
# @return none
# -----------------------------------------------------------------------------
def make_include(sourceText):
    """
    """
    global token

    moduleFile   = ""
    waveformFile = ""
    signalFile   = ""
    sequenceFile = ""

    lexer.initialize(sourceText)

    getToken()
    while True:
        if token.type == EOF:
            break
        elif found("MODULE_FILE"):
            consume("MODULE_FILE")
            consume("=")
            if found(STRING):
                moduleFile = token.cargo
            consume(STRING)
        elif found("WAVEFORM_FILE"):
            consume("WAVEFORM_FILE")
            consume("=")
            if found(STRING):
                waveformFile = token.cargo
            consume(STRING)
        elif found("SIGNAL_FILE"):
            consume("SIGNAL_FILE")
            consume("=")
            if found(STRING):
                signalFile = token.cargo
            consume(STRING)
        elif found("SEQUENCE_FILE"):
            consume("SEQUENCE_FILE")
            consume("=")
            if found(STRING):
                sequenceFile = token.cargo
            consume(STRING)
        else:
            error("unrecognized keyword: " + dq(token.cargo))

    if len(waveformFile) == 0:
        raise ParserError("missing WAVEFORM_FILE")

    if len(signalFile) == 0:
        raise ParserError("missing SIGNAL_FILE")

    if len(sequenceFile) == 0:
        raise ParserError("missing SEQUENCE_FILE")

    print( "MODULE_FILE " + moduleFile )  # PHM requires this to appear in the output
    print( "SIGNAL_FILE " + signalFile )  # PHM requires this to appear in the output

    print( "#include " + signalFile   )
    print( "#include " + waveformFile )
    print( "#include " + sequenceFile )
