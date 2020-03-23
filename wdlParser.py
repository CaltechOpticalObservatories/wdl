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
# @modified 2016-04-19 DH changes to implement INCLUDE_FILE= in .conf file
# @modified 2016-04-19 DH remove requirement for MAIN sequence
# @modified 2016-04-19 DH remove \???_LABEL from output
# @modified 2016-04-19 DH implement manual sequence return
# @modified 2016-04-21 DH fix bug in waveform() for manual sequence return
# @modified 2016-05-06 DH parse Python commands and clean up get_subroutines()
# @modified 2016-05-09 DH return pyextension separately from label name
# @modified 2016-06-07 DH allow for signed values of CLAMP
# @modified 2016-08-23 DH implemented \???_LABEL
# @modified 2016-09-21 DH allow RETURN to alternate sequences, waveforms
# @modified 2018-03-15 DH throw error if an undefined param is used in a sequence
# @modified 2020-03-20 DH added support for HEATER card
# 
# This is the parser for the Waveform Development Language (WDL).
# -----------------------------------------------------------------------------

# Copyright (C) <2018> California Institute of Technology
# Software written by: <Dave Hale and Peter Mao>
# 
#     This program is part of the Waveform Definition Language (WDL) developed
#     for ZTF.  This program is free software: you can redistribute it and/or
#     modify it under the terms of the GNU General Public License as published
#     by the Free Software Foundation, either version 3 of the License, or
#     any later version.
# 
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
# 
#     Please see the GNU General Public License at:
#     <http://www.gnu.org/licenses/>.
# 
#     Report any bugs or suggested improvements to:
# 
#     David Hale <dhale@caltech.edu> or
#     Stephen Kaye <skaye@caltech.edu>

from __future__ import print_function
import sys
sys.dont_write_bytecode = True
import Lexer as lexer
from Symbols import *

class ParserError(Exception): pass

token         = None
module_name   = None
setSlot       = []   # SET slot
setChan       = []   # SET chan
setSlew       = -1   # SET slew
setLevel      = 0
constList     = []
constNames    = []
paramList     = []
paramNames    = []
subroutines   = []
evalTime      = 0    # evaluated time for waveform line
maxTime       = 0    # max time for each waveform
wavReturnTime = 0    # time at which a waveform has manually specified a return
wavReturnTo   = ""   # optional, alternate waveform name to return to (not supported by wavgen)
wavReturn     = False # manual RETURN specified
timeStamps    = {}   # dictionary of time stamps, timelabel:time
drvOutput     = ""
adcOutput     = ""
hvlOutput     = ""
hvhOutput     = ""
lvlOutput     = ""
lvhOutput     = ""
dioOutput     = ""
sysOutput     = ""
sensorOutput  = ""
heaterOutput  = ""
pidOutput     = ""
rampOutput    = ""

__SLEW_FAST   =  1
__SLEW_SLOW   =  0
__SLEW_NONE   = -1

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
        error("(wdlParser.py::consume) expected " + argTokenType + 
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
    global module_name
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
        error("(wdlParser.py::module) unrecognized module type: " + dq(module_name))
    return(type)

# -----------------------------------------------------------------------------
# @fn     dio
# @brief  rules for the DIO keyword
# @param  string slotNumber
# @param  int type
# @return none, appends to global variable "dioOutput"
# -----------------------------------------------------------------------------
def dio(slotNumber, type):
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
        if module_name.upper() == "LVBIAS" or module_name.upper() == "HEATER":
            if int(dioChan) < 1 or int(dioChan) > 8:
                error("DIO channel " + dq(dioChan) + " outside range {1:8} for module: " + module_name.upper())
        elif module_name.upper() == "HS" or module_name.upper() == "LVDS":
            if int(dioChan) < 1 or int(dioChan) > 4:
                error("DIO channel " + dq(dioChan) + " outside range for HS, LVDS {1:4}")
        else:
                error("DIO is invalid keyword for module: " + module_name.upper())
    consume(NUMBER)
    consume("[")
    while not found("]"):
        if token.type == EOF: break
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
    # there can be an optional label, specified as token type=STRING
    if found(STRING):
        label=token.cargo[1:-1]  # strip leading and trailing quote chars
        consume(STRING)
    else:
        label=""
    consume(";")

    dioOutput += "MOD" + slotNumber + "\DIO_SOURCE" + dioChan + "=" + source    + "\n"

    # for LVBIAS and HEATER cards there are 8 DIO outputs but only 4 directions
    if module_name.upper() == "LVBIAS" or module_name.upper() == "HEATER":
        chan = int(dioChan)
        # for odd number channels 1,3,5,7 then DIO_DIR is DIO_DIR12, 34, 56, 78
        if chan % 2 == 1:
            dioOutput += "MOD" + slotNumber + "\DIO_DIR"    + str(chan) + str(chan+1) + "=" + direction + "\n"
    elif module_name.upper() == "HS" or module_name.upper() == "LVDS":
        dioOutput += "MOD" + slotNumber + "\DIO_DIR"    + dioChan + "=" + direction + "\n"
    if (label != ""):
        dioOutput += "MOD" + slotNumber + "\DIO_LABEL" + dioChan + "=" + label     + "\n"

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
        if token.type == EOF: break
        # if it's a number then allow a 0 or 1
        if found(NUMBER):
            if token.cargo == "0":
                diopower = "0"
            elif token.cargo == "1":
                diopower = "1"
            else:
                error("DIOPOWER unrecognized value: " + dq(token.cargo) + "\nexpected 0 or 1")
            consume(NUMBER)
        # or "enabled" or "disabled", convert to upper for case-insensitivity
        elif found(IDENTIFIER):
            if "ENABLE" in token.cargo.upper():
                diopower = "0"
            elif "DISABLE" in token.cargo.upper():
                diopower = "1"
            else:
                error("DIOPOWER unrecognized value: " + dq(token.cargo) +\
                      "\nexpected "+dq("low")+" or "+dq("high"))
            consume(IDENTIFIER)
    consume(";")

    dioOutput += "MOD" + slotNumber + "\DIO_POWER=" + diopower + "\n"

# -----------------------------------------------------------------------------
# @fn     updatetime
# @brief  rules for the UPDATETIME keyword
# @param  string slotNumber
# @return none, appends to global variable "heaterOutput"
# -----------------------------------------------------------------------------
def updatetime(slotNumber):
    """
    These are the rules for the UPDATETIME keyword, encountered while parsing
    the SLOT command for the modules (.mod) file. Required format is
    UPDATETIME=#;

    where # is {1:30000}
    """
    global token
    global heaterOutput

    consume("=")
    while not found(";"):
        if token.type == EOF: break
        # if it's a number then allow a 0 or 1
        if found(NUMBER):
            updateTime = int(token.cargo)
            if updateTime < 1 or updateTime > 30000:
                error("UPDATETIME: " + dq(str(updateTime)) + " outside range {1:30000}")
            consume(NUMBER)
    consume(";")

    heaterOutput += "MOD" + slotNumber + "\HEATERUPDATETIME=" + str(updateTime) + "\n"

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
        if token.type == EOF: break
        # if it's a number then allow a 0 or 1
        if found(NUMBER):
            if token.cargo == "0":
                preampgain = "0"
            elif token.cargo == "1":
                preampgain = "1"
            else:
                error("PREAMPGAIN unrecognized value: " + dq(token.cargo) + "\nexpected 0 or 1")
            consume(NUMBER)
        # or "low" or "high", converted to upper for case-insensitivity
        elif found(IDENTIFIER):
            if token.cargo.upper() == "LOW":
                preampgain = "0"
            elif token.cargo.upper() == "HIGH":
                preampgain = "1"
            else:
                error("PREAMPGAIN unrecognized value: " + dq(token.cargo) +\
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
        if token.type == EOF: break

        # could have a negative number...
        sign = +1
        if found("-"):
            consume("-")
            sign = -1

        if found(NUMBER):
            clamp = sign * float(token.cargo)
        consume(NUMBER)
    consume(";")

    adcOutput += "MOD" + slotNumber + "\CLAMP" + adChan + "=" + str(clamp) + "\n"

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
        if token.type == EOF: break
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
    # there can be an optional label, specified as token type=STRING
    if found(STRING):
        label=token.cargo[1:-1]  # strip leading and trailing quote chars
        consume(STRING)
    else:
        label=""
    consume(";")

    hvhOutput += "MOD" + slotNumber + "\HVHC_ENABLE"  + hvhChan + "=" + enable  + "\n"
    hvhOutput += "MOD" + slotNumber + "\HVHC_V"       + hvhChan + "=" + volts   + "\n"
    hvhOutput += "MOD" + slotNumber + "\HVHC_IL"      + hvhChan + "=" + current + "\n"
    hvhOutput += "MOD" + slotNumber + "\HVHC_ORDER"   + hvhChan + "=" + order   + "\n"
    if (label != ""):
        hvhOutput += "MOD" + slotNumber + "\HVHC_LABEL" + hvhChan + "=" + label + "\n"

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
        if token.type == EOF: break
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
    # there can be an optional label, specified as token type=STRING
    if found(STRING):
        label=token.cargo[1:-1]  # strip leading and trailing quote chars
        consume(STRING)
    else:
        label=""
    consume(";")

    hvlOutput += "MOD" + slotNumber + "\HVLC_V"     + hvlChan + "=" + volts + "\n"
    hvlOutput += "MOD" + slotNumber + "\HVLC_ORDER" + hvlChan + "=" + order + "\n"
    if (label != ""):
        hvlOutput += "MOD" + slotNumber + "\HVLC_LABEL" + hvlChan + "=" + label + "\n"


# -----------------------------------------------------------------------------
# @fn     lvhc
# @brief  rules for the LVHC keyword
# @param  string slotNumber
# @return none, appends to the global variable "lvhOutput"
# -----------------------------------------------------------------------------
def lvhc(slotNumber):
    """
    These are the rules for the LVHC keyword, encountered while parsing
    the SLOT command for the modules (.mod) file. Required format is
    LVHC # [#,#,#,#];

    where # is any number
    format of numbers is channel [volts, current_limit, order, enable]
    """
    global token
    global lvhOutput

    if found(NUMBER):
        lvhChan = token.cargo
        if int(lvhChan) < 1 or int(lvhChan) > 6:
            error("LVHC channel " + dq(lvhChan) + " outside range [1..6]")
    consume(NUMBER)
    consume("[")
    while not found("]"):
        if token.type == EOF: break
        # could have a negative number here...
        sign = +1
        if found("-"):
            consume("-")
            sign = -1
        if found(NUMBER):
            volts = sign * float(token.cargo)
            if float(volts) < -14 or float(volts) > 14:
                error("LVHC volts " + dq(str(volts)) + " outside range [-14..14] V")
        consume(NUMBER)
        consume(",")
        if found(NUMBER):
            current = token.cargo
            if float(current) < 0 or float(current) > 250:
                error("LVHC current " + dq(current) + " outside range [0..250] mA")
        consume(NUMBER)
        consume(",")
        if found(NUMBER):
            order = token.cargo
            if int(order) < 0 or int(order) > 6:
                error("LVHC order " + dq(order) + " outside range [0..6]")
        consume(NUMBER)
        consume(",")
        if found(NUMBER):
            enable = token.cargo
            if enable != "0" and enable != "1":
                error("LVHC enable " + dq(enable) + " must be 0 or 1")
        consume(NUMBER)
    consume("]")
    # there can be an optional label, specified as token type=STRING
    if found(STRING):
        label=token.cargo[1:-1]  # strip leading and trailing quote chars
        consume(STRING)
    else:
        label=""
    consume(";")

    lvhOutput += "MOD" + slotNumber + "\LVHC_ENABLE"  + lvhChan + "=" + enable  + "\n"
    lvhOutput += "MOD" + slotNumber + "\LVHC_V"       + lvhChan + "=" + str(volts) + "\n"
    lvhOutput += "MOD" + slotNumber + "\LVHC_IL"      + lvhChan + "=" + current + "\n"
    lvhOutput += "MOD" + slotNumber + "\LVHC_ORDER"   + lvhChan + "=" + order   + "\n"
    if (label != ""):
        lvhOutput += "MOD" + slotNumber + "\LVHC_LABEL" + lvhChan + "=" + label + "\n"

# -----------------------------------------------------------------------------
# @fn     lvlc
# @brief  rules for the LVLC keyword
# @param  string slotNumber
# @return none, appends to the global variable "lvlOutput"
# -----------------------------------------------------------------------------
def lvlc(slotNumber):
    """
    These are the rules for the LVLC keyword, encountered while parsing
    the SLOT command for the modules (.mod) file. Required format is
    LVLC # [#,#];

    where # is any number
    format of numbers is [volts, order]
    """
    global token
    global lvlOutput

    if found(NUMBER):
        lvlChan = token.cargo
        if int(lvlChan) < 1 or int(lvlChan) > 24:
            error("LVLC channel " + dq(lvlChan) + " outside range [1..24]")
    consume(NUMBER)
    consume("[")
    while not found("]"):
        if token.type == EOF: break

        # could have a negative number...
        sign = +1
        if found("-"):
            consume("-")
            sign = -1

        if found(NUMBER):
            volts = sign*float(token.cargo)
            if volts < -14 or volts > 14:
                error("LVLC volts " + dq(str(volts)) + " outside range [-14..14] V")
        consume(NUMBER)
        consume(",")
        if found(NUMBER):
            order = token.cargo
            if int(order) < 0 or int(order) > 24:
                error("LVLC order " + dq(order) + " outside range [0..24]")
        consume(NUMBER)
    consume("]")
    # there can be an optional label, specified as token type=STRING
    if found(STRING):
        label=token.cargo[1:-1]  # strip leading and trailing quote chars
        consume(STRING)
    else:
        label=""
    consume(";")

    lvlOutput += "MOD" + slotNumber + "\LVLC_V"     + lvlChan + "=" + str(volts) + "\n"
    lvlOutput += "MOD" + slotNumber + "\LVLC_ORDER" + lvlChan + "=" + order + "\n"
    if (label != ""):
        lvlOutput += "MOD" + slotNumber + "\LVLC_LABEL" + lvlChan + "=" + label + "\n"

# -----------------------------------------------------------------------------
# @fn     sensor
# @brief  rules for the HEATER keyword
# @param  string slotNumber
# @return none, appends to the global variable "sensorOutput"
# -----------------------------------------------------------------------------
def sensor(slotNumber):
    """
    These are the rules for the SENSOR keyword, encountered while parsing
    the SLOT command for the modules (.mod) file. Required format is
    SENSOR n [s,#,#,#,#,#];

    where n is sensor = {A,B,C}
    and   # is any number
    format of numbers is [type, current, lolim, hilim, filter]
    """
    global token
    global sensorOutput

    if found(IDENTIFIER):
        sensorChan = token.cargo
        if sensorChan != 'A' and sensorChan != 'B' and sensorChan != 'C':
            error("SENSOR channel " + sensorChan + ": must be {A,B,C}")
    consume(IDENTIFIER)
    consume("[")
    while not found ("]"):
        if token.type == EOF: break
        if found(NUMBER):
            sensorType = token.cargo
            if int(sensorType) < 0 or int(sensorType) > 5:
                error("SENSOR type: " + sensorType + ": must be in range {0:5}")
        consume(NUMBER)
        consume(",")
        if found(NUMBER):
            sensorCurrent = token.cargo
        consume(NUMBER)
        consume(",")
        # sensorLoLim could have a negative number...
        sign = +1
        if found("-"):
            consume("-")
            sign = -1
        if found(NUMBER):
            sensorLoLim = sign * float(token.cargo)
            if sensorLoLim < -150.0 or sensorLoLim > 50.0:
                error("SENSOR lower limit " + str(sensorLoLim) + ": must be in range {-150:50} deg C")
        consume(NUMBER)
        consume(",")
        # sensorHiLim could have a negative number...
        sign = +1
        if found("-"):
            consume("-")
            sign = -1
        if found(NUMBER):
            sensorHiLim = sign * float(token.cargo)
            if sensorHiLim < -150.0 or sensorHiLim > 50.0:
                error("SENSOR upper limit " + str(sensorHiLim) + ": must be in range {-150:50} deg C")
        consume(NUMBER)
        consume(",")
        if found(NUMBER):
            sensorFilter = token.cargo
            if int(sensorFilter) < 0 or int(sensorFilter) > 8:
                error("SENSOR filter " + sensorFilter + ": must be in range {0:8}")
        consume(NUMBER)
    consume("]")
    # there can be an optional label, specified as token type=STRING
    if found(STRING):
        label=token.cargo[1:-1]  # strip leading and trailing quote chars
        consume(STRING)
    else:
        label=""
    consume(";")

    sensorOutput += "MOD" + slotNumber + "\SENSOR" + sensorChan + "TYPE"       + "=" + sensorType       + "\n"
    sensorOutput += "MOD" + slotNumber + "\SENSOR" + sensorChan + "CURRENT"    + "=" + sensorCurrent    + "\n"
    sensorOutput += "MOD" + slotNumber + "\SENSOR" + sensorChan + "LOWERLIMIT" + "=" + str(sensorLoLim) + "\n"
    sensorOutput += "MOD" + slotNumber + "\SENSOR" + sensorChan + "UPPERLIMIT" + "=" + str(sensorHiLim) + "\n"
    sensorOutput += "MOD" + slotNumber + "\SENSOR" + sensorChan + "FILTER"     + "=" + sensorFilter     + "\n"
    sensorOutput += "MOD" + slotNumber + "\SENSOR" + sensorChan + "LABEL"      + "=" + label            + "\n"

# -----------------------------------------------------------------------------
# @fn     pid
# @brief  rules for the PID keyword
# @param  string slotNumber
# @return none, appends to the global variable "pidOutput"
# -----------------------------------------------------------------------------
def pid(slotNumber):
    """
    These are the rules for the PID keyword, encountered while parsing
    the SLOT command for the modules (.mod) file. Required format is
    PID c [#,#,#,#];

    where # is any number
    format of numbers is [
    """
    global token
    global pidOutput

    if found(IDENTIFIER):
        heaterChan = token.cargo
        if heaterChan != 'A' and heaterChan != 'B':
            error("PID invalid heater: " + heaterChan + ": must be {A,B}")
    consume(IDENTIFIER)
    consume("[")
    while not found ("]"):
        if token.type == EOF: break
        if found(NUMBER):
            heaterP = token.cargo
        consume(NUMBER)
        consume(",")
        if found(NUMBER):
            heaterI = token.cargo
        consume(NUMBER)
        consume(",")
        if found(NUMBER):
            heaterD = token.cargo
        consume(NUMBER)
        consume(",")
        if found(NUMBER):
            heaterIlim = token.cargo
        consume(NUMBER)
    consume("]")
    consume(";")

    pidOutput += "MOD" + slotNumber + "\HEATER" + heaterChan + "P"  + "=" + heaterP    + "\n"
    pidOutput += "MOD" + slotNumber + "\HEATER" + heaterChan + "I"  + "=" + heaterI    + "\n"
    pidOutput += "MOD" + slotNumber + "\HEATER" + heaterChan + "D"  + "=" + heaterD    + "\n"
    pidOutput += "MOD" + slotNumber + "\HEATER" + heaterChan + "IL" + "=" + heaterIlim + "\n"

# -----------------------------------------------------------------------------
# @fn     ramp
# @brief  rules for the RAMP keyword
# @param  string slotNumber
# @return none, appends to global variable "rampOutput"
# -----------------------------------------------------------------------------
def ramp(slotNumber):
    """
    These are the rules for the RAMP keyword, encountered while parsing
    the SLOT command for the modules (.mod) file. Required format is
    RAMP n [#,#];

    where n is heater {A,B}
    and   # is any number
    format of numbers is channel [source, direction]
    """
    global token
    global rampOutput

    if found(IDENTIFIER):
        rampChan = token.cargo
        if rampChan != 'A' and rampChan != 'B':
            error("RAMP heater channel " + rampChan + ": must be {A,B}")
    consume(IDENTIFIER)
    consume("[")
    while not found("]"):
        if token.type == EOF: break
        if found(NUMBER):
            ramprate = int(token.cargo)
            if ramprate < 1 or ramprate > 32767:
                error("RAMP rate " + dq(str(ramprate)) + " must be in range {1:32767}")
        consume(NUMBER)
        consume(",")
        # if it's a number then allow a 0 or 1
        if found(NUMBER):
            if token.cargo == "0":
                rampEnable = "0"
            elif token.cargo == "1":
                rampEnable = "1"
            else:
                error("RAMP enable unrecognized value: " + dq(token.cargo) + "\nexpected 0 or 1")
            consume(NUMBER)
        # or "enabled" or "disabled", convert to upper for case-insensitivity
        elif found(IDENTIFIER):
            if "ENABLE" in token.cargo.upper():
                rampEnable = "1"
            elif "DISABLE" in token.cargo.upper():
                rampEnable = "0"
            else:
                error("RAMP enable unrecognized value: " + dq(token.cargo) +\
                      "\nexpected "+dq("enable")+" or "+dq("disable"))
            consume(IDENTIFIER)
    consume("]")
    consume(";")

    rampOutput += "MOD" + slotNumber + "\HEATER" + rampChan + "RAMPRATE=" + str(ramprate) + "\n"
    rampOutput += "MOD" + slotNumber + "\HEATER" + rampChan + "RAMP="     + rampEnable    + "\n"

# -----------------------------------------------------------------------------
# @fn     heater
# @brief  rules for the HEATER keyword
# @param  string slotNumber
# @return none, appends to the global variable "heaterOutput"
# -----------------------------------------------------------------------------
def heater(slotNumber):
    """
    These are the rules for the HEATER keyword, encountered while parsing
    the SLOT command for the modules (.mod) file. Required format is
    HEATER n [#,c,#,#,#,#] "label";

    where # is any number
    format of numbers is [ ]
    """
    global token
    global heaterOutput

    if found(IDENTIFIER):
        heaterChan = token.cargo
        if heaterChan != 'A' and heaterChan != 'B':
            error("HEATER channel " + heaterChan + ": must be {A,B}")
    consume(IDENTIFIER)
    consume("[")
    while not found ("]"):
        if token.type == EOF: break
        # heaterTarget could have a negative number...
        sign = +1
        if found("-"):
            consume("-")
            sign = -1
        if found(NUMBER):
            heaterTarget = sign * float(token.cargo)
            if heaterTarget < -150.0 or heaterTarget > 50.0:
                error("HEATER target " + str(heaterTarget) + ": must be in range {-150:50}")
        consume(NUMBER)
        consume(",")
        # heaterSensor
        if found(IDENTIFIER):
            heaterSensor = token.cargo
            if heaterSensor == 'A':
                heaterSensor = '0'
            elif heaterSensor == 'B':
                heaterSensor = '1'
            elif heaterSensor == 'C':
                heaterSensor = '2'
            else:
                error("HEATER sensor " + heaterSensor + ": must be {A,B,C}")
        consume(IDENTIFIER)
        consume(",")
        # heaterLimit
        if found(NUMBER):
            heaterLimit = float(token.cargo)
            if heaterLimit < 0.0 or heaterLimit > 25.0:
                error("HEATER volt limit " + str(heaterLimit) + ": must be in range {0:25}")
        consume(NUMBER)
        consume(",")
        # heaterForcelevel
        if found(NUMBER):
            heaterForcelevel = float(token.cargo)
            if heaterForcelevel < 0.0 or heaterForcelevel > 25.0:
                error("HEATER volt force level " + str(heaterForcelevel) + ": must be in range {0:25}")
        consume(NUMBER)
        consume(",")
        # heaterForce
        # if it's a number then allow a 0 or 1
        if found(NUMBER):
            if token.cargo == "0":
                heaterForce = "0"
            elif token.cargo == "1":
                heaterForce = "1"
            else:
                error("HEATER force unrecognized value: " + dq(token.cargo) + "\nexpected 0 or 1")
            consume(NUMBER)
        # or "force" or "normal", convert to upper for case-insensitivity
        elif found(IDENTIFIER):
            if "FORCE" in token.cargo.upper():
                heaterForce = "1"
            elif "NORMAL" in token.cargo.upper():
                heaterForce = "0"
            else:
                error("HEATER force unrecognized value: " + dq(token.cargo) +\
                      "\nexpected "+dq("force")+" or "+dq("normal"))
            consume(IDENTIFIER)
        consume(",")
        # heaterEnable
        # if it's a number then allow a 0 or 1
        if found(NUMBER):
            if token.cargo == "0":
                heaterEnable = "0"
            elif token.cargo == "1":
                heaterEnable = "1"
            else:
                error("HEATER enable unrecognized value: " + dq(token.cargo) + "\nexpected 0 or 1")
            consume(NUMBER)
        # or "enabled" or "disabled", convert to upper for case-insensitivity
        elif found(IDENTIFIER):
            if "ENABLE" in token.cargo.upper():
                heaterEnable = "1"
            elif "DISABLE" in token.cargo.upper():
                heaterEnable = "0"
            else:
                error("HEATER enable unrecognized value: " + dq(token.cargo) +\
                      "\nexpected "+dq("enable")+" or "+dq("disable"))
            consume(IDENTIFIER)
    consume("]")
    # there can be an optional label, specified as token type=STRING
    if found(STRING):
        label=token.cargo[1:-1]  # strip leading and trailing quote chars
        consume(STRING)
    else:
        label=""
    consume(";")

    heaterOutput += "MOD" + slotNumber + "\HEATER" + heaterChan + "TARGET"     + "=" + str(heaterTarget) + "\n"
    heaterOutput += "MOD" + slotNumber + "\HEATER" + heaterChan + "SENSOR"     + "=" + heaterSensor      + "\n"
    heaterOutput += "MOD" + slotNumber + "\HEATER" + heaterChan + "LIMIT"      + "=" + str(heaterLimit)      + "\n"
    heaterOutput += "MOD" + slotNumber + "\HEATER" + heaterChan + "FORCELEVEL" + "=" + str(heaterForcelevel) + "\n"
    heaterOutput += "MOD" + slotNumber + "\HEATER" + heaterChan + "FORCE"      + "=" + heaterForce       + "\n"
    heaterOutput += "MOD" + slotNumber + "\HEATER" + heaterChan + "ENABLE"     + "=" + heaterEnable      + "\n"

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
        if token.type == EOF: break
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
    # there can be an optional label, specified as token type=STRING
    if found(STRING):
        label=token.cargo[1:-1]  # strip leading and trailing quote chars
        consume(STRING)
    else:
        label=""
    consume(";")

    drvOutput += "MOD" + slotNumber + "\ENABLE"       + drvChan + "=" + enable   + "\n"
    drvOutput += "MOD" + slotNumber + "\FASTSLEWRATE" + drvChan + "=" + slewfast + "\n"
    drvOutput += "MOD" + slotNumber + "\SLOWSLEWRATE" + drvChan + "=" + slewslow + "\n"
    if (label != ""):
        drvOutput += "MOD" + slotNumber + "\LABEL" + drvChan + "=" + label + "\n"

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

    where param is DRV, CLAMP, PREAMPGAIN, HVLC, HVHC, LVLC, LVHC, DIO, DIOPOWER
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
        if token.type == EOF: break
        if found("PRINT"):
            PRINT()
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
        if found("LVLC"):
            consume("LVLC")
            lvlc(slotNumber)
        if found("LVHC"):
            consume("LVHC")
            lvhc(slotNumber)
        if found("DIO"):
            consume("DIO")
            dio(slotNumber,type)
        if found("DIOPOWER"):
            consume("DIOPOWER")
            diopower(slotNumber)
        if found("UPDATETIME"):
            consume("UPDATETIME")
            updatetime(slotNumber)
        if found("PID"):
            consume("PID")
            pid(slotNumber)
        if found("SENSOR"):
            consume("SENSOR")
            sensor(slotNumber)
        if found("HTR"):
            consume("HTR")
            heater(slotNumber)
        if found("RAMP"):
            consume("RAMP")
            ramp(slotNumber)
        if found("HEATER"):
            consume("HEATER")
            heater(slotNumber)
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
# @fn     wav_return
# @brief  
# @param  
# @return 
# -----------------------------------------------------------------------------
def wav_return():
    """
    
    """
    global evalTime
    global maxTime
    global wavReturnTime
    global wavReturnTo
    global wavReturn
    global setSlew

    # manual return specified
    if found("RETURN"):
        consume("RETURN")
        wavReturn = True
        wavReturnTime = evalTime
        # alternate waveform name to return to (other than current waveform)
        # currently not supported by wavgen.py
        if found(IDENTIFIER):
            wavReturnTo = token.cargo
            consume(IDENTIFIER)
    else:
        wavReturn = False
        # If manual return not specified then remember the max time, for the RETURN
        if evalTime > maxTime:
            maxTime = evalTime

    return wavReturn

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
        if token.type == EOF: break
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
        if token.type == EOF: break
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
        error("SLEW expected SLOW | FAST but got: " + dq(token.cargo))

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
    if not wav_return():
        set()
        to()
        slew()
    eol()

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
    global wavReturn
    global wavReturnTime
    global wavReturnTo

    outputText = ""
    wavReturnTo= ""
    maxTime    = 0
    wavReturn  = False  # True if a manual waveform return is specified

    # a waveform must start with the "WAVEFORM" keyword, ...
    consume("WAVEFORM")

    # ...followed by a label for the waveform.
    waveformName, pyextension = name_label()
    outputText   += "waveform " + waveformName + pyextension + ":" + "\n"

    # Then, until the end of the waveform (delimited by curly brace),
    # check for the waveform rules.
    consume("{")
    while not found("}"):
        waverules()
        # If a manual waveform return was specified then write it here,
        if wavReturn:
            # if an alternate return name not specified then the default is current waveform
            if wavReturnTo == "":
                wavReturnTo = waveformName
            outputText += str(wavReturnTime) + " RETURN " + wavReturnTo + "\n\n"
        # otherwise loop through all the slots that were set and write a line for each
        else:
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
        if token.type == EOF: break
    consume("}")

    # "RETURN" marks the end of the waveform output
    if not wavReturn:
        outputText += str(maxTime+1) + " RETURN " + waveformName + "\n\n"
    if wavReturn and (wavReturnTime <= maxTime):
        error("waveform return time: " + str(wavReturnTime) + " must be > " + str(maxTime))
    return outputText

# -----------------------------------------------------------------------------
# @fn     python_commands
# @brief  parse python command text appended to a sequence|waveform label name
# @param  none
# @return sequence name
# -----------------------------------------------------------------------------
def python_commands():
    """
    Parses the python command text appended to a sequence|waveform label name.
    The period "." is consumed before calling this function so that the next
    token available is the identifier of the python command. Require open
    and close parentheses and copy everthing inbetween.
    """
    global token
    pyCommand = token.cargo         # first token is the name label itself
    consume("IDENTIFIER")
    pyCommand += token.cargo        # next must be an open paren
    consume("(")
    while not found(")"):           # copy everything until a close paren
        if token.type == EOF: break
        pyCommand += token.cargo
        getToken()
    pyCommand += token.cargo
    consume(")")
    return pyCommand

# -----------------------------------------------------------------------------
# @fn     name_label
# @brief  parses the name label for waveforms and sequences
# @param  none
# @return waveform|sequence name, pyextension
#
# The waveform|sequence name is returned as a separate element from the
# python extension, so that they can be used individually
# -----------------------------------------------------------------------------
def name_label():
    """
    Parses the name label for waveforms and sequences. The name identifier
    can also be followed with ".pythoncommand(arg1=arg, arg2=arg, ...)".
    The name can be a simple identifier but if followed by a period then there
    must be another identifier followed by open/close parentheses. The contents
    within the parentheses are not examined.
    """
    global token

    if found(IDENTIFIER):
        name = token.cargo
    else:
        print( "waveform or sequence missing name label", file=sys.stderr )
        name = ""
    consume(IDENTIFIER)   # require an identifier for sequence|waveform name

    # If there is a period after the sequence name, then require that
    # it be followed by another set of rules
    if found("."):
        consume(".")      # next token will be examined in python_commands()
        pyextension = "." + python_commands()
    else:
        pyextension = ""
    return name, pyextension

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
            if token.type == EOF: break
            if  ( found(IDENTIFIER) ) and \
                ( token.cargo not in subroutines ) and \
                ( token.cargo not in paramNames ):
                error("(wdlParser.py::generic_sequence) undefined symbol " + token.show(align=False) )
            # If token is a GOTO then the next token must be in the list
            # of subroutines() with open and close parentheses and nothing else
            if found("GOTO"):
                consume("GOTO")
                # Check next token against list of subroutines
                if token.cargo not in subroutines:
                    error("(wdlParser.py::generic_sequence) undefined waveform or sequence: " + dq(token.cargo))
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
                    # and if it's not a number then it must be a defined param
                    if not found(NUMBER) and token.cargo not in paramNames:
                        error("(wdlParser.py::generic_sequence) undefined param " + token.show(align=False) )
            elif found("RETURN"):
                consume("RETURN")
                # check for an alternate sequence specified for the return
                if found(IDENTIFIER):
                    seqReturnTo = token.cargo
                    consume(IDENTIFIER)
                # use the current sequenceName as the default, if none specified
                else:
                    seqReturnTo = sequenceName[0]
                outputText += "RETURN " + seqReturnTo + "\n"
                break
            else:
                sequenceLine += token.cargo
            prevToken = token.cargo
            getToken()
            # if next token not a symbol then pad with a space
            if token.cargo not in TwoCharacterSymbols and \
               token.cargo not in OneCharacterSymbols and \
               prevToken   not in PreSpaceSymbols:
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

    consume("SEQUENCE")
    sequenceName, pyextension = name_label()
    outputText = "sequence " + sequenceName + pyextension + ":" + "\n"
    outputText += generic_sequence(sequenceName) + "\n"
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
# @fn     const
# @brief  pulls out constants from anywhere in .seq file and stores in a list
# @param  none
# @return none
# -----------------------------------------------------------------------------
def const():
    """
    """
    global token
    global constList
    global constNames

    line = "constant "
    consume("const")
    constNames.append(token.cargo)
    line += token.cargo
    consume(IDENTIFIER)
    line += token.cargo
    consume("=")
    line += token.cargo
    consume(NUMBER)
    constList.append(line)

# -----------------------------------------------------------------------------
# @fn     print
# @brief  prints a string to stderr
# @param  string to print
# @return none
# -----------------------------------------------------------------------------
def PRINT():
    """
    """
    global token

    consume("PRINT")
    consume("(")
    if found(STRING):
        message = token.cargo.strip('"')
    consume(STRING)
    sys.stderr.write(message + "\n")
    while not found(";"):
        getToken()
        if token.type == EOF: break
    consume(";")

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
    PRINT()
    param()
    const()

    while True:
        getToken()
        if token.type == EOF: break
        param()
        const()
        PRINT()
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

    getToken()
    while True:
        if token.type == EOF: break
        # look only for sequences or waveforms
        if found("SEQUENCE") or found("WAVEFORM"):
            # consume whichever keyword was found
            if found("SEQUENCE"):
                consume("SEQUENCE")
            if found("WAVEFORM"):
                consume("WAVEFORM")

            # next token has to be an identifier
            name = token.cargo
            consume(IDENTIFIER)

            # if there is an appended Python command then strip it
            if found("."):
                consume(".")
                python_commands()
            # otherwise there ought to be open and close braces
            consume("{")
            while not found("}"):
                getToken()
                if token.type == EOF: break
            consume("}")
            # finally! add the name to the list of subroutines
            subroutines.append(name)
        else:
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
# @brief  creates the .modules file
# @param  sourceText
# @return .modules file output string
#
# This is called by modParserDriver.py when we want the .modules file.
# The only valid keyword is SLOT.
#
# The text for the .system file is assembled here (in sysOutput) but
# not returned from here.
# -----------------------------------------------------------------------------
def parse_modules(sourceText):
    """
    This is called to create the .modules file. The only valid keyword is SLOT.
    The text for the .system file is assembled here in global variable sysOutput
    but not returned from here.
    """
    global token
    global drvOutput
    global adcOutput
    global hvlOutput
    global hvhOutput
    global lvlOutput
    global lvhOutput
    global sysOutput
    global sensorOutput
    global heaterOutput
    global pidOutput
    global rampOutput

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
            # parse the rules for the SLOT keyword
            slot()
        elif found("PRINT"):
            PRINT()
        else:
            # We should only be parsing modules now
            error("(wdlParser.py::parse_modules) unrecognized token " + token.show(align=False) )
            break

    retval = ""
    retval += drvOutput
    retval += adcOutput
    retval += hvlOutput
    retval += hvhOutput
    retval += lvlOutput
    retval += lvhOutput
    retval += dioOutput
    retval += sensorOutput
    retval += heaterOutput
    retval += pidOutput
    retval += rampOutput

    return retval

# -----------------------------------------------------------------------------
# @fn     parse_system
# @brief  returns the text for the .system file
# @param  sourceText
# @return none
#
# This is called by modParserDriver.py when we want the .system file.
# The text string that is returned has already been built by previous calls
# to slot() and parse_modules().
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
#
# This is called by wdlParserDriver.py
# -----------------------------------------------------------------------------
def parse(sourceText):
    """
    """
    global token
    global paramList
    global constList

    lexer.initialize(sourceText)

    waveformText = ""
    sequenceText = ""
    moduleFile   = ""
    signalFile   = ""

    getToken()
    while True:
        if token.type == EOF:
            break
        elif found("SIGNALS"):
            consume("SIGNALS")
            consume("{")
            consume("}")
        elif found("WAVEFORM"):
            waveformText += waveform()
        elif found("PRINT"):
            PRINT()
        elif found("param"):
            param()
        elif found("const"):
            const()
        elif found("SEQUENCE"):
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
            error("(wdlParser.py::parse) unrecognized token " + token.show(align=False) )
            break

    retval =""
    retval += "modulefile " + moduleFile + "\n"
    retval += "signalfile " + signalFile + "\n\n"
    retval += sequenceText
    retval += waveformText
    for p in paramList:
        retval += p + "\n"
    for c in constList:
        retval += c + "\n"

    return retval

# -----------------------------------------------------------------------------
# @fn     make_include
# @brief  produces the #include directives from the .conf file
# @param  sourceText is the text of the .conf file
# @return none
# 
# Parse all the input of the .conf file, making sure it meets criteria,
# but act only on the INCLUDE_FILE tokens.
# -----------------------------------------------------------------------------
def make_include(sourceText):
    """
    produces the #include directives from the .conf file
    """
    global token

    lexer.initialize(sourceText)

    getToken()
    while True:
        if token.type == EOF:
            break
        elif found("INCLUDE_FILE"):
            consume("INCLUDE_FILE")
            consume("=")
            print( "#include " + token.cargo.strip("\"")   )
            consume(STRING)
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
        elif found("CDS_FILE"):
            consume("CDS_FILE")
            consume("=")
            consume(STRING)
        # MODE_FILE is specific to ZTF (i.e. ROBO-AO)
        elif found("MODE_FILE"):
            consume("MODE_FILE")
            consume("=")
            consume(STRING)
        else:
            error("(wdlParser.py::make_include) unrecognized keyword: " + dq(token.cargo))

# -----------------------------------------------------------------------------
# @fn     make_include_sequence
# @brief  produces output for assembling the sequence files from .conf
# @param  sourceText is the text of the .conf file
# @return none
# 
# Parse all the input of the .conf file, making sure it meets criteria.
# -----------------------------------------------------------------------------
def make_include_sequence(sourceText):
    """
    produces output for assembling the sequence files from .conf
    """
    global token

    moduleFile   = ""
    waveformFile = []
    signalFile   = ""
    sequenceFile = ""
    includeFiles = []

    lexer.initialize(sourceText)

    getToken()
    while True:
        if token.type == EOF:
            break
        elif found("INCLUDE_FILE"):
            consume("INCLUDE_FILE")
            consume("=")
            includeFiles.append( token.cargo )
            consume(STRING)
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
                waveformFile.append( token.cargo )
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
        elif found("CDS_FILE"):
            consume("CDS_FILE")
            consume("=")
            consume(STRING)
        # MODE_FILE is specific to ZTF (i.e. ROBO-AO)
        elif found("MODE_FILE"):
            consume("MODE_FILE")
            consume("=")
            consume(STRING)
        else:
            error("(wdlParser.py::make_include_sequence) unrecognized keyword: " + dq(token.cargo))

    if len(waveformFile) == 0:
        raise ParserError("missing WAVEFORM_FILE")

    if len(signalFile) == 0:
        raise ParserError("missing SIGNAL_FILE")

    if len(sequenceFile) == 0:
        raise ParserError("missing SEQUENCE_FILE")

    print( "MODULE_FILE " + moduleFile )  # PHM requires this to appear in the output
    print( "SIGNAL_FILE " + signalFile )  # PHM requires this to appear in the output

    # global include files come first, since they can have defines/conditionals
    # that might affect things downstream
    for incf in includeFiles:
        print( "#include " + incf )

    # signal files must come before waveforms and sequences, since the waveforms
    # will use #defines from the signal file
    print( "#include " + signalFile   )

    for wf in waveformFile:
        print( "#include " + wf )

    print( "#include " + sequenceFile )
