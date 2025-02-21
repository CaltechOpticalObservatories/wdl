# -----------------------------------------------------------------------------
# @file     wdlParser.py
# @brief    Parser for the Waveform Development Language
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
# @modified 2018-03-15 DH throw error if an undefined param used in a sequence
# @modified 2020-03-20 DH added support for HEATER card
# @modified 2022-06-08 DH added DriverX support (copy of Driver)
# @modified 2022-09-28 DH fixed DriverX support (add type=16 to module function)
#
# This is the Parser for the Waveform Development Language (WDL).
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

# for backwards compatibility with python 2


import Lexer
from Symbols import *
import sys

sys.dont_write_bytecode = True


class ParserError(Exception):
    pass


setSlot = []  # SET slot
setChan = []  # SET chan
setSlew = -1  # SET slew
setLevel = 0
constList = []
constNames = []
paramList = []
paramNames = []
subroutines = []
evalTime = 0  # evaluated time for waveform line
maxTime = 0  # max time for each waveform
wavReturnTime = 0  # time at which a waveform has manually specified a return
wavReturnTo = ""  # optional, alternate waveform name to return to
# (not supported by wavgen)
wavReturn = False  # manual RETURN specified
timeStamps = {}  # dictionary of time stamps, timelabel:time
drvOutput = ""
drvxOutput = ""
adcOutput = ""
hvlOutput = ""
hvhOutput = ""
lvlOutput = ""
lvhOutput = ""
dioOutput = ""
sysOutput = ""
sensorOutput = ""
heaterOutput = ""
pidOutput = ""
rampOutput = ""
pbiasOutput = ""
nbiasOutput = ""

__SLEW_FAST = 1
__SLEW_SLOW = 0
__SLEW_NONE = -1


# -----------------------------------------------------------------------------
# @fn     abort
# @brief  throw a Parser error
# @param  self, msg
# @return none
# -----------------------------------------------------------------------------
def abort(msg):
    """
    throw a Parser error
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
    Wrap double quotes around a string 's' and return the quoted string.
    """
    return '"{}"'.format(s)


# -----------------------------------------------------------------------------
# @fn     get_token
# @brief  assign next token from source text to global var
# @param  none
# @return none
# -----------------------------------------------------------------------------
def get_token():
    """
    Gets the next token from the source text and assigns it to the
    global variable 'token'.
    """
    global token
    token = Lexer.get()


# -----------------------------------------------------------------------------
# @fn     found
# @brief  returns True if the current token type matches the parameter
# @param  token type
# @return True or False
# -----------------------------------------------------------------------------
def found(arg_token_type):
    """
    returns True if the current token type matches the parameter
    """
    if token.type.upper() == arg_token_type.upper():
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
def consume(arg_token_type):
    """
    Consume a token of a given type and get the next token.
    If the current token is NOT of the expected type, then
    throw an error.
    """
    if token.type.upper() == arg_token_type.upper():
        get_token()
    else:
        error(
            "(wdlParser.py::consume) expected "
            f"{arg_token_type} but got {token.show(align=False)}"
        )


# -----------------------------------------------------------------------------
# @fn     module
# @brief  return an integer type for the module of the current token
# @param  none
# @return integer module type
# -----------------------------------------------------------------------------
def module():
    """
    Return an integer type for the module of the current token.
    """
    global token
    global module_name
    module_name = token.cargo

    # Convert all comparisons to upper for case-insensitivity
    module_map = {
        "DRIVER": 1,
        "AD": 2,
        "LVBIAS": 3,
        "HVBIAS": 4,
        "HEATER": 5,
        "HS": 7,
        "HVXBIAS": 8,
        "LVXBIAS": 9,
        "LVDS": 10,
        "HEATERX": 11,
        "XVBIAS": 12,
        "ADF": 13,
        "ADX": 14,
        "ADLN": 15,
        "DRIVERX": 16,
    }

    mod_type = module_map.get(module_name.upper(), -1)

    if mod_type == -1:
        error(f"(wdlParser.py::module) unrecognized module type: {dq(module_name)}")

    return mod_type

# -----------------------------------------------------------------------------
# @fn     dio
# @brief  rules for the DIO keyword
# @param  string slotNumber
# @param  int type
# @return none, appends to global variable "dioOutput"
# -----------------------------------------------------------------------------
def dio(slot_number):
    """
    These are the rules for the DIO keyword, encountered while parsing
    the SLOT command for the modules (.mod) file. Required format is
    DIO # [#,#];

    where # is any number
    format of numbers is channel [source, direction]
    """
    global token
    global dioOutput

    dio_chan = None

    if found(NUMBER):
        dio_chan = token.cargo
        if module_name.upper() in {"LVBIAS", "LVXBIAS", "HEATER", "HEATERX"}:
            if not (1 <= int(dio_chan) <= 8):
                error(
                    f"DIO channel {dq(dio_chan)} outside range {{1:8}} for module: "
                    f"{module_name.upper()}"
                )
        elif module_name.upper() in {"HS", "LVDS"}:
            if not (1 <= int(dio_chan) <= 4):
                error(
                    f"DIO channel {dq(dio_chan)} outside range for HS, LVDS {{1:4}}"
                )
        else:
            error(f"DIO is an invalid keyword for module: {module_name.upper()}")

    consume(NUMBER)
    source = None
    direction = None
    consume("[")
    while not found("]"):
        if token.type == EOF:
            break
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
        label = token.cargo[1:-1]  # strip leading and trailing quote chars
        consume(STRING)
    else:
        label = ""
    consume(";")

    dioOutput += "MOD" + slot_number + "\DIO_SOURCE" + dio_chan + "=" + source + "\n"

    # for LVBIAS and HEATER cards there are 8 DIO outputs but only 4 directions
    if (
        module_name.upper() == "LVBIAS"
        or module_name.upper() == "LVXBIAS"
        or module_name.upper() == "HEATER"
        or module_name.upper() == "HEATERX"
    ):
        chan = int(dio_chan)
        # for odd number channels 1,3,5,7 then DIO_DIR is DIO_DIR12, 34, 56, 78
        if chan % 2 == 1:
            dioOutput += (
                "MOD"
                + slot_number
                + "\DIO_DIR"
                + str(chan)
                + str(chan + 1)
                + "="
                + direction
                + "\n"
            )
            if label != "":
                dioOutput += "MOD" + slot_number + "\DIO_LABEL" + dio_chan + "=" + label + "\n"
    elif module_name.upper() == "HS" or module_name.upper() == "LVDS":
        dioOutput += (
            "MOD" + slot_number + "\DIO_DIR" + dio_chan + "=" + direction + "\n"
        )
        if label != "" and module_name.upper() == "LVDS":
            dioOutput += "MOD" + slot_number + "\LVDS_LABEL" + dio_chan + "=" + label + "\n"



# -----------------------------------------------------------------------------
# @fn     diopower
# @brief  rules for the DIOPOWER keyword
# @param  string slotNumber
# @return none, appends to global variable "dioOutput"
# -----------------------------------------------------------------------------
def diopower(slot_number):
    """
    These are the rules for the DIOPOWER keyword, encountered while parsing
    the SLOT command for the modules (.mod) file. Required format is
    DIOPOWER=?;

    where ? is 0,1,enabled,disabled
    """
    global token
    global dioOutput

    dio_power = None
    consume("=")
    while not found(";"):
        if token.type == EOF:
            break
        # if it's a number then allow a 0 or 1
        if found(NUMBER):
            if token.cargo == "0":
                dio_power = "0"
            elif token.cargo == "1":
                dio_power = "1"
            else:
                error(
                    "DIOPOWER unrecognized value: "
                    + dq(token.cargo)
                    + "\nexpected 0 or 1"
                )
            consume(NUMBER)
        # or "enabled" or "disabled", convert to upper for case-insensitivity
        elif found(IDENTIFIER):
            if "ENABLE" in token.cargo.upper():
                dio_power = "0"
            elif "DISABLE" in token.cargo.upper():
                dio_power = "1"
            else:
                error(
                    "DIOPOWER unrecognized value: "
                    + dq(token.cargo)
                    + "\nexpected "
                    + dq("low")
                    + " or "
                    + dq("high")
                )
            consume(IDENTIFIER)
    consume(";")

    dioOutput += "MOD" + slot_number + "\DIO_POWER=" + dio_power + "\n"


# -----------------------------------------------------------------------------
# @fn     updatetime
# @brief  rules for the UPDATETIME keyword
# @param  string slotNumber
# @return none, appends to global variable "heaterOutput"
# -----------------------------------------------------------------------------
def updatetime(slot_number):
    """
    These are the rules for the UPDATETIME keyword, encountered while parsing
    the SLOT command for the modules (.mod) file. Required format is
    UPDATETIME=#;

    where # is {1:30000}
    """
    global token
    global heaterOutput

    update_time = None
    consume("=")
    while not found(";"):
        if token.type == EOF:
            break
        # if it's a number then allow a 0 or 1
        if found(NUMBER):
            update_time = int(token.cargo)
            if update_time < 1 or update_time > 30000:
                error(
                    "UPDATETIME: " + dq(str(update_time)) + " outside range {1:30000}"
                )
            consume(NUMBER)
    consume(";")

    heaterOutput += "MOD" + slot_number + "\HEATERUPDATETIME=" + str(update_time) + "\n"


# -----------------------------------------------------------------------------
# @fn     preampgain
# @brief  rules for the PREAMPGAIN keyword
# @param  string slotNumber
# @return none, appends to global variable "adcOutput"
# -----------------------------------------------------------------------------
def preampgain(slot_number):
    """
    These are the rules for the PREAMPGAIN keyword, encountered while parsing
    the SLOT command for the modules (.mod) file. Required format is
    PREAMPGAIN=?;

    where ? is 0,1,low,high
    """
    global token
    global adcOutput

    preamp_gain = None
    consume("=")
    while not found(";"):
        if token.type == EOF:
            break
        # if it's a number then allow a 0 or 1
        if found(NUMBER):
            if token.cargo == "0":
                preamp_gain = "0"
            elif token.cargo == "1":
                preamp_gain = "1"
            else:
                error(
                    "PREAMPGAIN unrecognized value: "
                    + dq(token.cargo)
                    + "\nexpected 0 or 1"
                )
            consume(NUMBER)
        # or "low" or "high", converted to upper for case-insensitivity
        elif found(IDENTIFIER):
            if token.cargo.upper() == "LOW":
                preamp_gain = "0"
            elif token.cargo.upper() == "HIGH":
                preamp_gain = "1"
            else:
                error(
                    "PREAMPGAIN unrecognized value: "
                    + dq(token.cargo)
                    + "\nexpected "
                    + dq("low")
                    + " or "
                    + dq("high")
                )
            consume(IDENTIFIER)
    consume(";")

    adcOutput += "MOD" + slot_number + "\PREAMPGAIN=" + preamp_gain + "\n"


# -----------------------------------------------------------------------------
# @fn     clamp
# @brief  rules for the CLAMP keyword
# @param  string slotNumber
# @return none, appends to global variable "adcOutput"
# -----------------------------------------------------------------------------
def clamp(slot_number):
    """
    These are the rules for the CLAMP keyword, encountered while parsing
    the SLOT command for the modules (.mod) file. Required format is
    CLAMP #=#;

    where ? is any number
    format of numbers is channel=level
    """
    global token
    global adcOutput

    ad_chan = None
    if found(NUMBER):
        ad_chan = token.cargo
        if int(ad_chan) < 1 or int(ad_chan) > 4:
            error("CLAMP channel " + dq(ad_chan) + " outside range [1..4]")
    consume(NUMBER)
    _clamp = None
    consume("=")
    while not found(";"):
        if token.type == EOF:
            break

        # could have a negative number...
        sign = +1
        if found("-"):
            consume("-")
            sign = -1

        if found(NUMBER):
            _clamp = sign * float(token.cargo)
        consume(NUMBER)
    consume(";")

    adcOutput += "MOD" + slot_number + "\CLAMP" + ad_chan + "=" + str(_clamp) + "\n"


# -----------------------------------------------------------------------------
# @fn     hvhc
# @brief  rules for the HVHC keyword
# @param  string slotNumber
# @return none, appends to the global variable "hvhOutput"
# -----------------------------------------------------------------------------
def hvhc(slot_number):
    """
    These are the rules for the HVHC keyword, encountered while parsing
    the SLOT command for the modules (.mod) file. Required format is
    HVHC # [#,#,#,#];

    where # is any number
    format of numbers is channel [volts, current_limit, order, enable]
    """
    global token
    global hvhOutput

    hvh_chan = None
    if found(NUMBER):
        hvh_chan = token.cargo
        if not (1 <= int(hvh_chan) <= 6):
            error(f"HVHC channel {dq(hvh_chan)} outside range [1..6]")

    consume(NUMBER)
    volts = None
    current = None
    order = None
    enable = None
    consume("[")

    while not found("]"):
        if token.type == EOF:
            break
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
    label = ""
    if found(STRING):
        label = token.cargo[1:-1]  # Strip leading and trailing quote chars
        consume(STRING)
    consume(";")

    hvhOutput += f"MOD{slot_number}\\HVHC_ENABLE{hvh_chan}={enable}\n"
    hvhOutput += f"MOD{slot_number}\\HVHC_V{hvh_chan}={volts}\n"
    hvhOutput += f"MOD{slot_number}\\HVHC_IL{hvh_chan}={current}\n"
    hvhOutput += f"MOD{slot_number}\\HVHC_ORDER{hvh_chan}={order}\n"

    if label:
        hvhOutput += f"MOD{slot_number}\\HVHC_LABEL{hvh_chan}={label}\n"


# -----------------------------------------------------------------------------
# @fn     hvlc
# @brief  rules for the HVHC keyword
# @param  string slotNumber
# @return none, appends to the global variable "hvlOutput"
# -----------------------------------------------------------------------------
def hvlc(slot_number):
    """
    These are the rules for the HVLC keyword, encountered while parsing
    the SLOT command for the modules (.mod) file. Required format is
    HVLC # [#,#];

    where # is any number
    format of numbers is [volts, order]
    """
    global token
    global hvlOutput

    hvl_chan = None
    if found(NUMBER):
        hvl_chan = token.cargo
        if int(hvl_chan) < 1 or int(hvl_chan) > 24:
            error("HVLC channel " + dq(hvl_chan) + " outside range [1..24]")
    consume(NUMBER)
    volts = None
    order = None
    consume("[")
    while not found("]"):
        if token.type == EOF:
            break
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
        label = token.cargo[1:-1]  # strip leading and trailing quote chars
        consume(STRING)
    else:
        label = ""
    consume(";")

    hvlOutput += "MOD" + slot_number + "\HVLC_V" + hvl_chan + "=" + volts + "\n"
    hvlOutput += "MOD" + slot_number + "\HVLC_ORDER" + hvl_chan + "=" + order + "\n"
    if label != "":
        hvlOutput += "MOD" + slot_number + "\HVLC_LABEL" + hvl_chan + "=" + label + "\n"


# -----------------------------------------------------------------------------
# @fn     lvhc
# @brief  rules for the LVHC keyword
# @param  string slotNumber
# @return none, appends to the global variable "lvhOutput"
# -----------------------------------------------------------------------------
def lvhc(slot_number):
    """
    These are the rules for the LVHC keyword, encountered while parsing
    the SLOT command for the modules (.mod) file. Required format is
    LVHC # [#,#,#,#];

    where # is any number
    format of numbers is channel [volts, current_limit, order, enable]
    """
    global token
    global lvhOutput

    lvh_chan = None
    if found(NUMBER):
        lvh_chan = token.cargo
        if int(lvh_chan) < 1 or int(lvh_chan) > 6:
            error("LVHC channel " + dq(lvh_chan) + " outside range [1..6]")
    consume(NUMBER)
    volts = None
    current = None
    order = None
    enable = None
    consume("[")
    while not found("]"):
        if token.type == EOF:
            break
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
        label = token.cargo[1:-1]  # strip leading and trailing quote chars
        consume(STRING)
    else:
        label = ""
    consume(";")

    lvhOutput += "MOD" + slot_number + "\LVHC_ENABLE" + lvh_chan + "=" + enable + "\n"
    lvhOutput += "MOD" + slot_number + "\LVHC_V" + lvh_chan + "=" + str(volts) + "\n"
    lvhOutput += "MOD" + slot_number + "\LVHC_IL" + lvh_chan + "=" + current + "\n"
    lvhOutput += "MOD" + slot_number + "\LVHC_ORDER" + lvh_chan + "=" + order + "\n"
    if label != "":
        lvhOutput += "MOD" + slot_number + "\LVHC_LABEL" + lvh_chan + "=" + label + "\n"


# -----------------------------------------------------------------------------
# @fn     lvlc
# @brief  rules for the LVLC keyword
# @param  string slotNumber
# @return none, appends to the global variable "lvlOutput"
# -----------------------------------------------------------------------------
def lvlc(slot_number):
    """
    These are the rules for the LVLC keyword, encountered while parsing
    the SLOT command for the modules (.mod) file. Required format is
    LVLC # [#,#];

    where # is any number
    format of numbers is [volts, order]
    """
    global token
    global lvlOutput

    lvl_chan = None
    if found(NUMBER):
        lvl_chan = token.cargo
        if int(lvl_chan) < 1 or int(lvl_chan) > 24:
            error("LVLC channel " + dq(lvl_chan) + " outside range [1..24]")
    consume(NUMBER)
    volts = None
    order = None
    consume("[")
    while not found("]"):
        if token.type == EOF:
            break

        # could have a negative number...
        sign = +1
        if found("-"):
            consume("-")
            sign = -1

        if found(NUMBER):
            volts = sign * float(token.cargo)
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
        label = token.cargo[1:-1]  # strip leading and trailing quote chars
        consume(STRING)
    else:
        label = ""
    consume(";")

    lvlOutput += "MOD" + slot_number + "\LVLC_V" + lvl_chan + "=" + str(volts) + "\n"
    lvlOutput += "MOD" + slot_number + "\LVLC_ORDER" + lvl_chan + "=" + order + "\n"
    if label != "":
        lvlOutput += "MOD" + slot_number + "\LVLC_LABEL" + lvl_chan + "=" + label + "\n"


# -----------------------------------------------------------------------------
# @fn     sensor
# @brief  rules for the HEATER keyword
# @param  string slotNumber
# @return none, appends to the global variable "sensorOutput"
# -----------------------------------------------------------------------------
def sensor(slot_number):
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

    sensor_chan = None
    if found(IDENTIFIER):
        sensor_chan = token.cargo
        if sensor_chan != "A" and sensor_chan != "B" and sensor_chan != "C":
            error("SENSOR channel " + sensor_chan + ": must be {A,B,C}")
    consume(IDENTIFIER)
    sensorType = None
    sensor_current = None
    sensor_lo_lim = None
    sensor_hi_lim = None
    sensor_filter = None
    consume("[")
    while not found("]"):
        if token.type == EOF:
            break
        if found(NUMBER):
            sensorType = token.cargo
            if int(sensorType) < 0 or int(sensorType) > 5:
                error("SENSOR type: " + sensorType + ": must be in range {0:5}")
        consume(NUMBER)
        consume(",")
        if found(NUMBER):
            sensor_current = token.cargo
        consume(NUMBER)
        consume(",")
        # sensor_lo_lim could have a negative number...
        sign = +1
        if found("-"):
            consume("-")
            sign = -1
        if found(NUMBER):
            sensor_lo_lim = sign * float(token.cargo)
            if sensor_lo_lim < -150.0 or sensor_lo_lim > 50.0:
                error(
                    "SENSOR lower limit "
                    + str(sensor_lo_lim)
                    + ": must be in range {-150:50} deg C"
                )
        consume(NUMBER)
        consume(",")
        # sensor_hi_lim could have a negative number...
        sign = +1
        if found("-"):
            consume("-")
            sign = -1
        if found(NUMBER):
            sensor_hi_lim = sign * float(token.cargo)
            if sensor_hi_lim < -150.0 or sensor_hi_lim > 50.0:
                error(
                    "SENSOR upper limit "
                    + str(sensor_hi_lim)
                    + ": must be in range {-150:50} deg C"
                )
        consume(NUMBER)
        consume(",")
        if found(NUMBER):
            sensor_filter = token.cargo
            if int(sensor_filter) < 0 or int(sensor_filter) > 8:
                error("SENSOR filter " + sensor_filter + ": must be in range {0:8}")
        consume(NUMBER)
    consume("]")
    # there can be an optional label, specified as token type=STRING
    if found(STRING):
        label = token.cargo[1:-1]  # strip leading and trailing quote chars
        consume(STRING)
    else:
        label = ""
    consume(";")

    sensorOutput += (
        "MOD" + slot_number + "\SENSOR" + sensor_chan + "TYPE" + "=" + sensorType + "\n"
    )
    sensorOutput += (
        "MOD"
        + slot_number
        + "\SENSOR"
        + sensor_chan
        + "CURRENT"
        + "="
        + sensor_current
        + "\n"
    )
    sensorOutput += (
        "MOD"
        + slot_number
        + "\SENSOR"
        + sensor_chan
        + "LOWERLIMIT"
        + "="
        + str(sensor_lo_lim)
        + "\n"
    )
    sensorOutput += (
        "MOD"
        + slot_number
        + "\SENSOR"
        + sensor_chan
        + "UPPERLIMIT"
        + "="
        + str(sensor_hi_lim)
        + "\n"
    )
    sensorOutput += (
        "MOD"
        + slot_number
        + "\SENSOR"
        + sensor_chan
        + "FILTER"
        + "="
        + sensor_filter
        + "\n"
    )
    sensorOutput += (
        "MOD" + slot_number + "\SENSOR" + sensor_chan + "LABEL" + "=" + label + "\n"
    )


# -----------------------------------------------------------------------------
# @fn     pid
# @brief  rules for the PID keyword
# @param  string slotNumber
# @return none, appends to the global variable "pidOutput"
# -----------------------------------------------------------------------------
def pid(slot_number):
    """
    These are the rules for the PID keyword, encountered while parsing
    the SLOT command for the modules (.mod) file. Required format is
    PID c [#,#,#,#];

    where # is any number
    format of numbers is [
    """
    global token
    global pidOutput

    heater_chan = None
    if found(IDENTIFIER):
        heater_chan = token.cargo
        if heater_chan != "A" and heater_chan != "B":
            error("PID invalid heater: " + heater_chan + ": must be {A,B}")
    consume(IDENTIFIER)
    heater_p = None
    heater_i = None
    heater_d = None
    heater_ilim = None
    consume("[")
    while not found("]"):
        if token.type == EOF:
            break
        if found(NUMBER):
            heater_p = token.cargo
        consume(NUMBER)
        consume(",")
        if found(NUMBER):
            heater_i = token.cargo
        consume(NUMBER)
        consume(",")
        if found(NUMBER):
            heater_d = token.cargo
        consume(NUMBER)
        consume(",")
        if found(NUMBER):
            heater_ilim = token.cargo
        consume(NUMBER)
    consume("]")
    consume(";")

    pidOutput += (
        "MOD" + slot_number + "\HEATER" + heater_chan + "P" + "=" + heater_p + "\n"
    )
    pidOutput += (
        "MOD" + slot_number + "\HEATER" + heater_chan + "I" + "=" + heater_i + "\n"
    )
    pidOutput += (
        "MOD" + slot_number + "\HEATER" + heater_chan + "D" + "=" + heater_d + "\n"
    )
    pidOutput += (
        "MOD" + slot_number + "\HEATER" + heater_chan + "IL" + "=" + heater_ilim + "\n"
    )


# -----------------------------------------------------------------------------
# @fn     ramp
# @brief  rules for the RAMP keyword
# @param  string slotNumber
# @return none, appends to global variable "rampOutput"
# -----------------------------------------------------------------------------
def ramp(slot_number):
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

    ramp_chan = None
    if found(IDENTIFIER):
        ramp_chan = token.cargo
        if ramp_chan != "A" and ramp_chan != "B":
            error("RAMP heater channel " + ramp_chan + ": must be {A,B}")
    consume(IDENTIFIER)
    ramprate = None
    ramp_enable = None
    consume("[")
    while not found("]"):
        if token.type == EOF:
            break
        if found(NUMBER):
            ramprate = int(token.cargo)
            if ramprate < 1 or ramprate > 32767:
                error("RAMP rate " + dq(str(ramprate)) + " must be in range {1:32767}")
        consume(NUMBER)
        consume(",")
        # if it's a number then allow a 0 or 1
        if found(NUMBER):
            if token.cargo == "0":
                ramp_enable = "0"
            elif token.cargo == "1":
                ramp_enable = "1"
            else:
                error(
                    "RAMP enable unrecognized value: "
                    + dq(token.cargo)
                    + "\nexpected 0 or 1"
                )
            consume(NUMBER)
        # or "enabled" or "disabled", convert to upper for case-insensitivity
        elif found(IDENTIFIER):
            if "ENABLE" in token.cargo.upper():
                ramp_enable = "1"
            elif "DISABLE" in token.cargo.upper():
                ramp_enable = "0"
            else:
                error(
                    "RAMP enable unrecognized value: "
                    + dq(token.cargo)
                    + "\nexpected "
                    + dq("enable")
                    + " or "
                    + dq("disable")
                )
            consume(IDENTIFIER)
    consume("]")
    consume(";")

    rampOutput += (
        "MOD" + slot_number + "\HEATER" + ramp_chan + "RAMPRATE=" + str(ramprate) + "\n"
    )
    rampOutput += (
        "MOD" + slot_number + "\HEATER" + ramp_chan + "RAMP=" + ramp_enable + "\n"
    )


# -----------------------------------------------------------------------------
# @fn     heater
# @brief  rules for the HEATER keyword
# @param  string slotNumber
# @return none, appends to the global variable "heaterOutput"
# -----------------------------------------------------------------------------
def heater(slot_number):
    """
    These are the rules for the HEATER keyword, encountered while parsing
    the SLOT command for the modules (.mod) file. Required format is
    HEATER n [#,c,#,#,#,#] "label";

    where # is any number
    format of numbers is [ ]
    """
    global token
    global heaterOutput

    heater_chan = None
    if found(IDENTIFIER):
        heater_chan = token.cargo
        if heater_chan != "A" and heater_chan != "B":
            error("HEATER channel " + heater_chan + ": must be {A,B}")
    consume(IDENTIFIER)
    heater_target = None
    heater_sensor = None
    heater_limit = None
    heater_forcelevel = None
    heater_force = None
    heater_enable = None
    consume("[")
    while not found("]"):
        if token.type == EOF:
            break
        # heater_target could have a negative number...
        sign = +1
        if found("-"):
            consume("-")
            sign = -1
        if found(NUMBER):
            heater_target = sign * float(token.cargo)
            if heater_target < -150.0 or heater_target > 50.0:
                error(
                    "HEATER target "
                    + str(heater_target)
                    + ": must be in range {-150:50}"
                )
        consume(NUMBER)
        consume(",")
        # heater_sensor
        if found(IDENTIFIER):
            heater_sensor = token.cargo
            if heater_sensor == "A":
                heater_sensor = "0"
            elif heater_sensor == "B":
                heater_sensor = "1"
            elif heater_sensor == "C":
                heater_sensor = "2"
            else:
                error("HEATER sensor " + heater_sensor + ": must be {A,B,C}")
        consume(IDENTIFIER)
        consume(",")
        # heater_limit
        if found(NUMBER):
            heater_limit = float(token.cargo)
            if heater_limit < 0.0 or heater_limit > 25.0:
                error(
                    "HEATER volt limit "
                    + str(heater_limit)
                    + ": must be in range {0:25}"
                )
        consume(NUMBER)
        consume(",")
        # heater_forcelevel
        if found(NUMBER):
            heater_forcelevel = float(token.cargo)
            if heater_forcelevel < 0.0 or heater_forcelevel > 25.0:
                error(
                    "HEATER volt force level "
                    + str(heater_forcelevel)
                    + ": must be in range {0:25}"
                )
        consume(NUMBER)
        consume(",")
        # heater_force
        # if it's a number then allow a 0 or 1
        if found(NUMBER):
            if token.cargo == "0":
                heater_force = "0"
            elif token.cargo == "1":
                heater_force = "1"
            else:
                error(
                    "HEATER force unrecognized value: "
                    + dq(token.cargo)
                    + "\nexpected 0 or 1"
                )
            consume(NUMBER)
        # or "force" or "normal", convert to upper for case-insensitivity
        elif found(IDENTIFIER):
            if "FORCE" in token.cargo.upper():
                heater_force = "1"
            elif "NORMAL" in token.cargo.upper():
                heater_force = "0"
            else:
                error(
                    "HEATER force unrecognized value: "
                    + dq(token.cargo)
                    + "\nexpected "
                    + dq("force")
                    + " or "
                    + dq("normal")
                )
            consume(IDENTIFIER)
        consume(",")
        # heater_enable
        # if it's a number then allow a 0 or 1
        if found(NUMBER):
            if token.cargo == "0":
                heater_enable = "0"
            elif token.cargo == "1":
                heater_enable = "1"
            else:
                error(
                    "HEATER enable unrecognized value: "
                    + dq(token.cargo)
                    + "\nexpected 0 or 1"
                )
            consume(NUMBER)
        # or "enabled" or "disabled", convert to upper for case-insensitivity
        elif found(IDENTIFIER):
            if "ENABLE" in token.cargo.upper():
                heater_enable = "1"
            elif "DISABLE" in token.cargo.upper():
                heater_enable = "0"
            else:
                error(
                    "HEATER enable unrecognized value: "
                    + dq(token.cargo)
                    + "\nexpected "
                    + dq("enable")
                    + " or "
                    + dq("disable")
                )
            consume(IDENTIFIER)
    consume("]")
    # there can be an optional label, specified as token type=STRING
    if found(STRING):
        label = token.cargo[1:-1]  # strip leading and trailing quote chars
        consume(STRING)
    else:
        label = ""
    consume(";")

    heaterOutput += (
        "MOD"
        + slot_number
        + "\HEATER"
        + heater_chan
        + "TARGET"
        + "="
        + str(heater_target)
        + "\n"
    )
    heaterOutput += (
        "MOD"
        + slot_number
        + "\HEATER"
        + heater_chan
        + "SENSOR"
        + "="
        + heater_sensor
        + "\n"
    )
    heaterOutput += (
        "MOD"
        + slot_number
        + "\HEATER"
        + heater_chan
        + "LIMIT"
        + "="
        + str(heater_limit)
        + "\n"
    )
    heaterOutput += (
        "MOD"
        + slot_number
        + "\HEATER"
        + heater_chan
        + "FORCELEVEL"
        + "="
        + str(heater_forcelevel)
        + "\n"
    )
    heaterOutput += (
        "MOD"
        + slot_number
        + "\HEATER"
        + heater_chan
        + "FORCE"
        + "="
        + heater_force
        + "\n"
    )
    heaterOutput += (
        "MOD"
        + slot_number
        + "\HEATER"
        + heater_chan
        + "ENABLE"
        + "="
        + heater_enable
        + "\n"
    )


# -----------------------------------------------------------------------------
# @fn     pbias
# @brief  rules for the PBIAS keyword
# @param  string slotNumber
# @return none, appends to the global variable "pbiasOutput"
# -----------------------------------------------------------------------------
def pbias(slot_number):
    """
    These are the rules for the PBIAS keyword, encountered while parsing
    the xvbias command for the modules (.mod) file. Required format is
    PBIAS n b [#,#] "label";

    where n is channel number
    where b is 0 - disabled, 1 - enabled
    where # is any number
        format is [source, direction]
    where "label" is a string
    """
    global token
    global pbiasOutput

    bias_chan = None
    if found(NUMBER):
        bias_chan = token.cargo
        if int(bias_chan) < 1 or int(bias_chan) > 4:
            error("PBIAS channel " + dq(bias_chan) + " outside range {1:4}")
    consume(NUMBER)

    if found(NUMBER):
        enable = token.cargo
        if int(enable) < 0 or int(enable) > 1:
            error("PBIAS enable " + dq(enable) + " must be 0 or 1")
        consume(NUMBER)
    else:
        enable = "1"

    cmd = None
    order = None
    consume("[")
    while not found("]"):
        if token.type == EOF:
            break
        if found(NUMBER):
            order = token.cargo
            if int(order) < 0:
                error("PBIAS order " + order + " must be >= 0")
        consume(NUMBER)

        consume(",")

        if found(NUMBER):
            cmd = token.cargo
        consume(NUMBER)

    consume("]")
    # there can be an optional label, specified as token type=STRING
    if found(STRING):
        label = token.cargo[1:-1]  # strip leading and trailing quote chars
        consume(STRING)
    else:
        label = ""
    consume(";")

    pbiasOutput += "MOD" + slot_number + "\XVP_V" + bias_chan + "=" + cmd + "\n"
    pbiasOutput += "MOD" + slot_number + "\XVP_ORDER" + bias_chan + "=" + order + "\n"
    pbiasOutput += "MOD" + slot_number + "\XVP_ENABLE" + bias_chan + "=" + enable + "\n"
    if label != "":
        pbiasOutput += (
            "MOD" + slot_number + "\XVP_LABEL" + bias_chan + "=" + label + "\n"
        )


# -----------------------------------------------------------------------------
# @fn     nbias
# @brief  rules for the NBIAS keyword
# @param  string slotNumber
# @return none, appends to the global variable "nbiasOutput"
# -----------------------------------------------------------------------------
def nbias(slot_number):
    """
    These are the rules for the NBIAS keyword, encountered while parsing
    the xvbias command for the modules (.mod) file. Required format is
    NBIAS n b [#,#] "label";

    where n is channel number
    where b is 0 - disabled, 1 - enabled
    where # is any number
        format is [source, direction]
    where "label" is a string
    """
    global token
    global nbiasOutput

    bias_chan = None
    if found(NUMBER):
        bias_chan = token.cargo
        if int(bias_chan) < 1 or int(bias_chan) > 4:
            error("NBIAS channel " + dq(bias_chan) + " outside range {1:4}")
    consume(NUMBER)

    if found(NUMBER):
        enable = token.cargo
        if int(enable) < 0 or int(enable) > 1:
            error("NBIAS enable " + dq(enable) + " must be 0 or 1")
        consume(NUMBER)
    else:
        enable = "1"

    order = None
    cmd = None
    consume("[")
    while not found("]"):
        if token.type == EOF:
            break
        if found(NUMBER):
            order = token.cargo
            if int(order) < 0:
                error("NBIAS order " + order + " must be >= 0")
        consume(NUMBER)

        consume(",")

        # must be a negative number...
        consume("-")
        if found(NUMBER):
            cmd = token.cargo
        consume(NUMBER)

    consume("]")
    # there can be an optional label, specified as token type=STRING
    if found(STRING):
        label = token.cargo[1:-1]  # strip leading and trailing quote chars
        consume(STRING)
    else:
        label = ""
    consume(";")

    nbiasOutput += "MOD" + slot_number + "\XVN_V" + bias_chan + "=-" + cmd + "\n"
    nbiasOutput += "MOD" + slot_number + "\XVN_ORDER" + bias_chan + "=" + order + "\n"
    nbiasOutput += "MOD" + slot_number + "\XVN_ENABLE" + bias_chan + "=" + enable + "\n"
    if label != "":
        nbiasOutput += (
            "MOD" + slot_number + "\XVN_LABEL" + bias_chan + "=" + label + "\n"
        )


# -----------------------------------------------------------------------------
# @fn     drv
# @brief  rules for the DRV keyword
# @param  string slotNumber
# @return none, appends to the global variable "drvOutput"
# -----------------------------------------------------------------------------
def drv(slot_number):
    """
    These are the rules for the DRV keyword, encountered while parsing
    the SLOT command for the modules (.mod) file. Required format is
    DRV # [#,#,#];

    where # is any number
    format of numbers is [slewfast, slewslow, enable]
    """
    global token
    global drvOutput

    drv_chan = None
    if found(NUMBER):
        drv_chan = token.cargo
        if int(drv_chan) < 0 or int(drv_chan) > 8:
            error("DRV channel " + dq(drv_chan) + " outside range [1..8]")
    consume(NUMBER)
    slewfast = None
    slewslow = None
    enable = None
    consume("[")
    while not found("]"):
        if token.type == EOF:
            break
        if found(NUMBER):
            slewfast = token.cargo
            if float(slewfast) < 0.001 or float(slewfast) > 1000:
                error(
                    "DRV Fast Slew Rate "
                    + dq(slewfast)
                    + " outside range [0.001..1000] V/us"
                )
        consume(NUMBER)
        consume(",")
        if found(NUMBER):
            slewslow = token.cargo
            if float(slewslow) < 0.001 or float(slewslow) > 1000:
                error(
                    "DRV Slow Slew Rate "
                    + dq(slewslow)
                    + " outside range [0.001..1000] V/us"
                )
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
        label = token.cargo[1:-1]  # strip leading and trailing quote chars
        consume(STRING)
    else:
        label = ""
    consume(";")

    drvOutput += "MOD" + slot_number + "\ENABLE" + drv_chan + "=" + enable + "\n"
    drvOutput += (
        "MOD" + slot_number + "\FASTSLEWRATE" + drv_chan + "=" + slewfast + "\n"
    )
    drvOutput += (
        "MOD" + slot_number + "\SLOWSLEWRATE" + drv_chan + "=" + slewslow + "\n"
    )
    if label != "":
        drvOutput += "MOD" + slot_number + "\LABEL" + drv_chan + "=" + label + "\n"


# -----------------------------------------------------------------------------
# @fn     drvx
# @brief  rules for the DRVX keyword
# @param  string slotNumber
# @return none, appends to the global variable "drvxOutput"
# -----------------------------------------------------------------------------
def drvx(slot_number):
    """
    These are the rules for the DRVX keyword, encountered while parsing
    the SLOT command for the modules (.mod) file. Required format is
    DRVX # [#,#,#];

    where # is any number
    format of numbers is [slewfast, slewslow, enable]
    """
    global token
    global drvxOutput

    drv_chan = None
    if found(NUMBER):
        drv_chan = token.cargo
        if int(drv_chan) < 0 or int(drv_chan) > 12:
            error(f"DRVX channel {dq(drv_chan)} outside range [1..12]")

    consume(NUMBER)
    slewfast = None
    slewslow = None
    enable = None
    consume("[")
    while not found("]"):
        if token.type == EOF:
            break
        if found(NUMBER):
            slewfast = token.cargo
            if float(slewfast) < 0.001 or float(slewfast) > 1000:
                error(f"DRVX Slow Slew Rate {dq(slewslow)} outside range [0.001..1000] V/us")
        consume(NUMBER)
        consume(",")
        if found(NUMBER):
            slewslow = token.cargo
            if float(slewslow) < 0.001 or float(slewslow) > 1000:
                error(
                    "DRVX Slow Slew Rate "
                    + dq(slewslow)
                    + " outside range [0.001..1000] V/us"
                )
        consume(NUMBER)
        consume(",")
        if found(NUMBER):
            enable = token.cargo
            if enable != "0" and enable != "1":
                error(f"DRVX enable {dq(enable)} must be 0 or 1")
        consume(NUMBER)
    consume("]")
    # there can be an optional label, specified as token type=STRING
    label = ""
    if found(STRING):
        label = token.cargo[1:-1]  # Strip leading and trailing quote chars
        consume(STRING)

    consume(";")

    drvxOutput += f"MOD{slot_number}\\ENABLE{drv_chan}={enable}\n"
    drvxOutput += f"MOD{slot_number}\\FASTSLEWRATE{drv_chan}={slewfast}\n"
    drvxOutput += f"MOD{slot_number}\\SLOWSLEWRATE{drv_chan}={slewslow}\n"

    if label:
        drvxOutput += f"MOD{slot_number}\\LABEL{drv_chan}={label}\n"


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

    where param is DRV, DRVX, CLAMP, PREAMPGAIN, HVLC, HVHC, LVLC, LVHC, DIO,
                DIOPOWER
                followed by param specific rules,
          type  is a valid Archon module type,
          #     is any number.
    """
    global token
    global sysOutput

    consume("SLOT")

    slot_number = None
    if found(NUMBER):
        slot_number = token.cargo
        if int(slot_number) < 1 or int(slot_number) > 12:
            error("SLOT " + dq(slot_number) + " outside range [1..12]")
    consume(NUMBER)

    mod_type = None
    if found(IDENTIFIER):
        mod_type = module()
    consume(IDENTIFIER)

    # Then, until the end of the waveform (delimited by curly brace),
    # check for the waveform rules.
    consume("{")
    while not found("}"):
        if token.type == EOF:
            break
        if found("PRINT"):
            wprint()
        if found("DRV"):
            consume("DRV")
            drv(slot_number)
        if found("DRVX"):
            consume("DRVX")
            drvx(slot_number)
        elif found("CLAMP"):
            consume("CLAMP")
            clamp(slot_number)
        if found("PREAMPGAIN"):
            consume("PREAMPGAIN")
            preampgain(slot_number)
        if found("HVLC"):
            consume("HVLC")
            hvlc(slot_number)
        if found("HVHC"):
            consume("HVHC")
            hvhc(slot_number)
        if found("LVLC"):
            consume("LVLC")
            lvlc(slot_number)
        if found("LVHC"):
            consume("LVHC")
            lvhc(slot_number)
        if found("DIO"):
            consume("DIO")
            dio(slot_number)
        if found("DIOPOWER"):
            consume("DIOPOWER")
            diopower(slot_number)
        if found("UPDATETIME"):
            consume("UPDATETIME")
            updatetime(slot_number)
        if found("PID"):
            consume("PID")
            pid(slot_number)
        if found("SENSOR"):
            consume("SENSOR")
            sensor(slot_number)
        if found("HTR"):
            consume("HTR")
            heater(slot_number)
        if found("RAMP"):
            consume("RAMP")
            ramp(slot_number)
        if found("HEATER"):
            consume("HEATER")
            heater(slot_number)
        if found("PBIAS"):
            consume("PBIAS")
            pbias(slot_number)
        if found("NBIAS"):
            consume("NBIAS")
            nbias(slot_number)
        else:
            pass
    consume("}")

    # Build up the information for a .system file --
    # Values of ID, REV, VERSION don't matter, but they need to be defined
    # if the resultant .acf file is to be loaded by the GUI without an error.
    # The important value here is the TYPE, so that the correct tabs are
    # created.
    sysOutput += "MOD" + slot_number + "_ID=0000000000000000\n"
    sysOutput += "MOD" + slot_number + "_REV=0\n"
    sysOutput += "MOD" + slot_number + "_VERSION=0.0.0\n"
    sysOutput += "MOD" + slot_number + "_TYPE=" + str(mod_type) + "\n"

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
    """ """
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
        # If manual return not specified then remember the max time,
        # for the RETURN
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

    if found("SET"):  # If no time found, then this waveform happens at the
        return  # same time as the previous line, so just return.

    # init an equation from which the time will be calculated

    if found(".+"):  # start new equation with the last eval time
        eqn = str(evalTime) + "+"
        consume(".+")
    else:  # or start anew
        eqn = ""

    # form an equation from which the time will be evaluated using everything
    # up to the ":"
    while not found(":"):
        if token.type == EOF:
            break
        if found(IDENTIFIER):
            # if we found a time stamp label then get its actual time from
            # the dictionary
            if token.cargo in timeStamps:
                eqn += str(timeStamps[token.cargo])
            else:
                print("Unresolved symbol " + dq(token.cargo), file=sys.stderr)
            consume(IDENTIFIER)
        else:
            eqn += token.cargo  # if not a label then we have a number or
            # math symbol
            get_token()
    consume(":")
    evalTime = int(eval(eqn))  # new evaluated time


# -----------------------------------------------------------------------------
# @fn     set
# @brief  rules for the SET keyword
# @param  none
# @return none
# -----------------------------------------------------------------------------
def wset():
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
        if token.type == EOF:
            break
        # SLOT
        if found(NUMBER):
            setSlot.append(token.cargo)
        consume(NUMBER)
        consume(":")
        # CHANNEL
        if found(NUMBER):
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
    """ """
    global setLevel

    consume("TO")
    # could be a negative number...
    if found("-"):
        # if so, consume the sign and remember it
        consume("-")
        sign = -1.0
    else:
        sign = 1.0
    if found(NUMBER):
        # multiply the value by the sign from above (hehe)
        setLevel = str(sign * float(token.cargo))
    consume(NUMBER)


# -----------------------------------------------------------------------------
# @fn     slew
# @brief
# @param  none
# @return none
# -----------------------------------------------------------------------------
def slew():
    """ """
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
    check for the end-of-line character (semicolon)
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
              (if omitted then SET... lines are all at the same time as
               previous time)
              arithmetic operations are allowed for time
              units are allowed to follow numbers, E.G. ns, us, ms
              ".+" means to add to the previous time

        =timelabel is an optional label for this time, which can be used
         elsewhere

        SET signallabel TO level;
        is required and must end with a semicolon

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
        wset()
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

    output_text = ""
    wavReturnTo = ""
    maxTime = 0
    wavReturn = False  # True if a manual waveform return is specified

    # a waveform must start with the "WAVEFORM" keyword, ...
    consume("WAVEFORM")

    # ...followed by a label for the waveform.
    waveform_name, pyextension = name_label()
    output_text += "waveform " + waveform_name + pyextension + ":" + "\n"

    # Then, until the end of the waveform (delimited by curly brace),
    # check for the waveform rules.
    consume("{")
    while not found("}"):
        waverules()
        # If a manual waveform return was specified then write it here,
        if wavReturn:
            # if an alternate return name not specified then
            # the default is current waveform
            if wavReturnTo == "":
                wavReturnTo = waveform_name
            output_text += str(wavReturnTime) + " RETURN " + wavReturnTo + "\n\n"
        # otherwise loop through all the slots that were set and
        # write a line for each
        else:
            for index in range(len(setSlot)):
                # The output is written differently depending on whether
                # a slew rate (fast | slow) has been specified.
                if setSlew == __SLEW_NONE:
                    output_text += (
                        str(evalTime)
                        + " "
                        + str(setSlot[index])
                        + " "
                        + str(int(setChan[index]) - 1)
                        + " "
                        + str(setLevel)
                        + "\n"
                    )
                else:
                    output_text += (
                        str(evalTime)
                        + " "
                        + str(setSlot[index])
                        + " "
                        + str(2 * int(setChan[index]) - 2)
                        + " "
                        + str(setLevel)
                        + "\n"
                    )
                    output_text += (
                        str(evalTime)
                        + " "
                        + str(setSlot[index])
                        + " "
                        + str(2 * int(setChan[index]) - 1)
                        + " "
                        + str(setSlew)
                        + "\n"
                    )
        if token.type == EOF:
            break
    consume("}")

    # "RETURN" marks the end of the waveform output
    if not wavReturn:
        output_text += str(maxTime + 1) + " RETURN " + waveform_name + "\n\n"
    if wavReturn and (wavReturnTime <= maxTime):
        error(
            "waveform return time: " + str(wavReturnTime) + " must be > " + str(maxTime)
        )
    return output_text


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
    py_command = token.cargo  # first token is the name label itself
    consume("IDENTIFIER")
    py_command += token.cargo  # next must be an open paren
    consume("(")
    while not found(")"):  # copy everything until a close paren
        if token.type == EOF:
            break
        py_command += token.cargo
        get_token()
    py_command += token.cargo
    consume(")")
    return py_command


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
        print("waveform or sequence missing name label", file=sys.stderr)
        name = ""
    consume(IDENTIFIER)  # require an identifier for sequence|waveform name

    # If there is a period after the sequence name, then require that
    # it be followed by another set of rules
    if found("."):
        consume(".")  # next token will be examined in python_commands()
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
    """ """
    global token
    # sequence/waveform must start with an open (left) curly brace, {
    consume("{")
    output_text = ""
    # process until end-of-sequence
    while not found("}"):
        sequence_line = ""
        # process until end-of-line
        while not found(";"):
            if token.type == EOF:
                break
            if (
                (found(IDENTIFIER))
                and (token.cargo not in subroutines)
                and (token.cargo not in paramNames)
            ):
                error(
                    "(wdlParser.py::generic_sequence) undefined symbol "
                    + token.show(align=False)
                )
            # If token is a GOTO then the next token must be in the list
            # of subroutines() with open and close parentheses and nothing else
            if found("GOTO"):
                consume("GOTO")
                # Check next token against list of subroutines
                if token.cargo not in subroutines:
                    error(
                        "(wdlParser.py::generic_sequence) undefined waveform "
                        "or sequence: " + dq(token.cargo)
                    )
                else:
                    sequence_line += "GOTO " + token.cargo
                    # then consume the IDENTIFIER and the open/close parentheses
                    # and break, because that's it for the line.
                    consume(IDENTIFIER)
                    consume("(")
                    consume(")")
                    break
            # If token is in the list of subroutines then it must be CALLed
            # and must be followed by parentheses and an optional number
            if token.cargo in subroutines:
                sequence_line += "CALL " + token.cargo
                consume(IDENTIFIER)
                consume("(")
                # if next token isn't a closing paren then assume
                # it's a number or param
                if not found(")"):
                    sequence_line += "(" + token.cargo  # + ")"
                    # and if it's not a number then it must be a defined param
                    if not found(NUMBER) and token.cargo not in paramNames:
                        error(
                            "(wdlParser.py::generic_sequence) undefined "
                            "param " + token.show(align=False)
                        )
            elif found("RETURN"):
                consume("RETURN")
                # check for an alternate sequence specified for the return
                if found(IDENTIFIER):
                    seq_return_to = token.cargo
                    consume(IDENTIFIER)
                # use the current sequenceName as the default, if none specified
                else:
                    seq_return_to = sequenceName[0]
                output_text += "RETURN " + seq_return_to + "\n"
                break
            else:
                sequence_line += token.cargo
            prev_token = token.cargo
            get_token()
            # if next token not a symbol then pad with a space
            if (
                token.cargo not in TwoCharacterSymbols
                and token.cargo not in OneCharacterSymbols
                and prev_token not in PreSpaceSymbols
            ):
                sequence_line += " "
        # line must end with a semicolon
        consume(";")
        # won't normally have a 0-length sequence_line,
        # but could happen during testing
        if len(sequence_line) > 0:
            output_text += sequence_line + "\n"
    # sequence/waveform must end with a close (right) curly brace, }
    consume("}")
    return output_text


# -----------------------------------------------------------------------------
# @fn     sequence
# @brief
# @param  none
# @return none
# -----------------------------------------------------------------------------
def sequence():
    """ """
    global token
    global subroutines

    consume("SEQUENCE")
    sequence_name, pyextension = name_label()
    output_text = "sequence " + sequence_name + pyextension + ":" + "\n"
    output_text += generic_sequence(sequence_name) + "\n"
    return output_text


# -----------------------------------------------------------------------------
# @fn     parse_waveform
# @brief
# @param  source_text
# @return none
# -----------------------------------------------------------------------------
def parse_waveform(source_text):
    """ """
    global token

    Lexer.initialize(source_text)

    while True:
        get_token()
        if token.type == EOF:
            break
        waveform()


# -----------------------------------------------------------------------------
# @fn     param
# @brief  pulls out params from anywhere in .seq file and stores in a list
# @param  none
# @return none
# -----------------------------------------------------------------------------
def param():
    """ """
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
    """ """
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
def wprint():
    """ """
    global token

    consume("PRINT")
    consume("(")
    if found(STRING):
        message = token.cargo.strip('"')
    else:
        message = None
    consume(STRING)
    sys.stderr.write(message + "\n")
    while not found(";"):
        get_token()
        if token.type == EOF:
            break
    consume(";")


# -----------------------------------------------------------------------------
# @fn     parse_sequence
# @brief
# @param  source_text
# @return none
# -----------------------------------------------------------------------------
def parse_sequence(source_text):
    """ """
    global token
    global paramList

    Lexer.initialize(source_text)

    get_token()
    wprint()
    param()
    const()

    while True:
        get_token()
        if token.type == EOF:
            break
        param()
        const()
        wprint()
        sequence()


# -----------------------------------------------------------------------------
# @fn     get_subroutines
# @brief
# @param  source_text
# @return none
# -----------------------------------------------------------------------------
def get_subroutines(source_text):
    """ """
    global token
    global subroutines

    Lexer.initialize(source_text)

    subroutines = []

    get_token()
    while True:
        if token.type == EOF:
            break
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
                get_token()
                if token.type == EOF:
                    break
            consume("}")
            # finally! add the name to the list of subroutines
            subroutines.append(name)
        else:
            get_token()

    return subroutines


# -----------------------------------------------------------------------------
# @fn     get_params
# @brief
# @param  source_text
# @return none
# -----------------------------------------------------------------------------
def get_params(source_text):
    """ """
    global token
    global paramNames

    Lexer.initialize(source_text)

    while True:
        get_token()
        if token.type == EOF:
            break
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
# @param  source_text
# @return .modules file output string
#
# This is called by modParserDriver.py when we want the .modules file.
# The only valid keyword is SLOT.
#
# The text for the .system file is assembled here (in sysOutput) but
# not returned from here.
# -----------------------------------------------------------------------------
def parse_modules(source_text):
    """
    This is called to create the .modules file. The only valid keyword is SLOT.
    The text for the .system file is assembled here in global variable sysOutput
    but not returned from here.
    """
    global token
    global drvOutput
    global drvxOutput
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
    global pbiasOutput
    global nbiasOutput

    Lexer.initialize(source_text)

    # initialize the system output string
    sysOutput = ""
    sysOutput += "BACKPLANE_ID=0000000000000000\n"
    sysOutput += "BACKPLANE_REV=0\n"
    sysOutput += "BACKPLANE_TYPE=1\n"
    sysOutput += "BACKPLANE_VERSION=0.0.0\n"

    get_token()
    while True:
        if token.type == EOF:
            break
        elif found("SLOT"):
            # parse the rules for the SLOT keyword
            slot()
        elif found("PRINT"):
            wprint()
        else:
            # We should only be parsing modules now
            error(
                "(wdlParser.py::parse_modules) unrecognized token "
                + token.show(align=False)
            )
            break

    retval = ""
    retval += drvOutput
    retval += drvxOutput
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
    retval += pbiasOutput
    retval += nbiasOutput

    return retval


# -----------------------------------------------------------------------------
# @fn     parse_system
# @brief  returns the text for the .system file
# @param  source_text
# @return none
#
# This is called by modParserDriver.py when we want the .system file.
# The text string that is returned has already been built by previous calls
# to slot() and parse_modules().
# -----------------------------------------------------------------------------
def parse_system():
    """ """
    global sysOutput
    return sysOutput


# -----------------------------------------------------------------------------
# @fn     parse
# @brief  parses everything
# @param  source_text
# @return none
#
# This is called by wdlParserDriver.py
# -----------------------------------------------------------------------------
def parse(source_text):
    """ """
    global token
    global paramList
    global constList

    Lexer.initialize(source_text)

    waveform_text = ""
    sequence_text = ""
    module_file = ""
    signal_file = ""

    get_token()
    while True:
        if token.type == EOF:
            break
        elif found("SIGNALS"):
            consume("SIGNALS")
            consume("{")
            consume("}")
        elif found("WAVEFORM"):
            waveform_text += waveform()
        elif found("PRINT"):
            wprint()
        elif found("param"):
            param()
        elif found("const"):
            const()
        elif found("SEQUENCE"):
            sequence_text += sequence()
        elif found("MODULE_FILE"):
            consume("MODULE_FILE")
            module_file = token.cargo.strip('"')
            consume(STRING)
        elif found("SIGNAL_FILE"):
            consume("SIGNAL_FILE")
            signal_file = token.cargo.strip('"')
            consume(STRING)
        else:
            error("(wdlParser.py::parse) unrecognized token " + token.show(align=False))
            break

    retval = ""
    retval += "modulefile " + module_file + "\n"
    retval += "signalfile " + signal_file + "\n\n"
    retval += sequence_text
    retval += waveform_text
    for p in paramList:
        retval += p + "\n"
    for c in constList:
        retval += c + "\n"

    return retval


# -----------------------------------------------------------------------------
# @fn     make_include
# @brief  produces the #include directives from the .conf file
# @param  source_text is the text of the .conf file
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

    Lexer.initialize(sourceText)

    get_token()
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
# @param  source_text is the text of the .conf file
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

    Lexer.initialize(sourceText)

    get_token()
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