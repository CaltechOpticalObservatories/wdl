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

import numpy as np

# import matplotlib.mlab as mlab
import matplotlib.pyplot as plt
import scipy.sparse as sparse  # need 0.18.1
import re
import sys
import os
import collections
import timing_segment as ts

# from IPython.core.debugger import Tracer
# from IPython.core.magic import register_line_magic
# import time as t

class WavGen: 
    def __init__(self):
        self.period_ns = 10  # ns
        self.slot = {
            "drvr": [],
            "lvds": [],
            "htr": [],
            "xvbd": [],
            "adc": [],
            "back": [0],
            "hvbd": [],
            "lvbd": [],
        }
        self.__boardTypes__ = (
            "drvr", "lvds", "htr", "xvbd", "adc", "back", "hvbd", "lvbd"
        )
        self.__chan_per_board__ = {
            "drvr": 2 * 12,  # 2* to take care of level and slew flag
            "lvds": 20,
            "htr": 8,
            "xvbd": 8,  # why is this 8? 8 voltages: 4pos, 4neg
            "adc": 1,
            "back": 6,
            "hvbd": 30,
            "lvbd": 38,
        }  # 8 DIO's + 30 bias (like hvbd)
        self.UniqueStateArr = np.array([])
        self.Catalog = []  # list of all TimingSegment objects
        self.Parameters = collections.OrderedDict()  # all the parameters
        self.Constants = collections.OrderedDict()  # all the constants
        self.SignalByName = {}
        self.SignalByIndx = {}
        self.__seq_ID__ = 0
        self.__TStypes__ = ("", "waveform", "sequence")
        self.GenerateFigs = False  # set to True to plot waveforms when loadWDL is called.
        self.__padmax__ = 25  # padding for comments in script


    def loadWDL(self, infile, outfile="/dev/null", verbose=1):
        """Load a WDL compiled waveform, write ACF state and script files.
        Automatically generates plots for non-static signals in waveforms.
        Use 'stdout' or sys.stdout to dump to terminal."""

        # user command and arguments for feedback
        usercommands = []

        # default mod file
        # ModFile = '/home/ztf/devel/python/wdl/demo.mod'
        ModFile = "/home/user/wdl/demo.mod"
        __SignalFile__ = ""

        # read through file to find the mod file
        infile = os.path.abspath(os.path.expanduser(infile))
        print("Infile path: ", infile)
        wdl_file_did_not_specify_mod_file = True
        with open(infile, "r") as f:
            for line in f:
                # look for mod file
                match = re.search("^modulefile\\s+([~\\w./]+)\\s*$", line)
                if match is not None:
                    ModFile = os.path.abspath(os.path.expanduser(match.group(1)))
                    wdl_file_did_not_specify_mod_file = False
                    break
        if not os.path.isfile(ModFile):
            print("MOD file specified does not exist (%s)" % ModFile)
            print("Using existing slot definitions")
        else:
            if wdl_file_did_not_specify_mod_file:
                print("Using default MOD file: %s" % ModFile)
            else:
                if verbose > 0:
                    print("Using MOD file: %s" % ModFile)
            self.load_mod(ModFile)

        # global slot is now well-defined, read in the file again for WDL content.
        with open(infile, "r") as f:
            for line in f:
                line = re.sub("#.*$", "", line)  # strip comments
                line = re.sub("^\s*$", "", line)  # clear empty lines
                if line == "":
                    continue
                # look for mod file
                match = re.search("^modulefile\\s+([~\\w./]+)\\s*$", line)
                if match is not None:
                    continue
                # look for signal file
                match = re.search("^signalfile\\s+([~\\w./]+)\\s*$", line)
                if match is not None:
                    __SignalFile__ = os.path.abspath(os.path.expanduser(match.group(1)))
                    if not os.path.isfile(__SignalFile__):
                        print("Signal file specified does not exist (%s)" % __SignalFile__)
                    continue
                # look for parameters
                match = re.search("^parameter\s+(\w+)=(\d+)\s*$", line)
                if match is not None:
                    pname = match.group(1)
                    pval = int(match.group(2))
                    self.Parameters.update({pname: pval})
                    continue
                # look for constants
                match = re.search("^constant\s+(\w+)=(\d+)\s*$", line)
                if match is not None:
                    cname = match.group(1)
                    cval = int(match.group(2))
                    self.Constants.update({cname: cval})
                    continue
                # look for a label
                match = re.search(
                    "^(sequence|waveform)" r"\s+(\w+)(\.(\w+)\((.*)\))?:\s*$", line
                )
                if match is not None:
                    # SEQUENCE HEADER:  acf label found, generate sequence object
                    TStype = match.group(1)
                    acfLabel = match.group(2)
                    pycmd = match.group(4)
                    pyargs = match.group(5)
                    if TStype == "sequence":
                        thisTS = ts.TimingSegment(self.Catalog, self.UniqueStateArr, self.SignalByIndx, acfLabel, TStype)
                        ctr = 0
                        print("THIS TS", thisTS)
                    elif TStype == "waveform":
                        thisTS = ts.TimingSegment(self.Catalog, self.UniqueStateArr, self.SignalByIndx, acfLabel, TStype, endline=-1)
                        print("THIS TS", thisTS)
                    else:
                        print("INVALID TimingSegment type: %s" % TStype)
                        print(">> %s" % line)
                    if pycmd is not None:
                        usercommands.append([eval("thisTS.%s" % pycmd), pyargs])
                else:  # SEQUENCE BODY: line not matching code segment label/header
                    if TStype == "sequence":
                        thisTS.sequenceDef.append([ctr, line[:-1]])
                        ctr += 1
                    elif TStype == "waveform":
                        match = re.search("(\d+)\s+(\d+)\s+(\d+)\s+([+-]?[\d\.]+)", line)
                        if match is not None:
                            # body of a waveform
                            time = int(match.group(1))
                            nslot = int(match.group(2))
                            chan = int(match.group(3))  # this is the slot channel
                            value = float(match.group(4))
                            # get the key for the slot
                            foundBoardType = False
                            for board_type in self.slot:
                                print("Board type:", board_type)
                                if nslot in self.slot[board_type]:
                                    foundBoardType = True
                                    if chan >= self.__chan_per_board__[board_type]:
                                        print(
                                            "*** INVALID channel (%d) for %s "
                                            "(slot %d) in %s ***"
                                            % (chan, board_type, nslot, f.name)
                                        )
                                        continue
                                    TSchan = (
                                        self.__chan_per_board__[board_type]
                                        * np.where(np.array(self.slot[board_type]) == nslot)[0][
                                            0
                                        ]
                                        + chan
                                    )
                                    print("self.__chan_per_board__[board_type]:", self.__chan_per_board__[board_type])
                                    # uncomment below to debug waveform read-in
                                    # print '%s[%d]
                                    # <-- (%d,%g)'%(board_type,TSchan,time,value)
                                    thisTS.events[board_type][TSchan].append(
                                        np.array((time, value))
                                    )
                            if not foundBoardType:
                                print(
                                    "*** [loadWDL error] Board type for slot "
                                    "%s unkown ***" % nslot
                                )
                        else:
                            # handle the end line of a waveform.
                            match = re.search("(\d+)\s+(\w+)", line)
                            thisTS.nperiods = int(match.group(1))
                            if thisTS.nperiods == 0:
                                print(
                                    "WARNING: nperiods for %s %s is 0" % (TStype, acfLabel)
                                )
        if verbose > 0:
            print("Loading signal mnemonics from %s" % __SignalFile__)
        self.__loadSignals__(__SignalFile__)
        if outfile == "/dev/null":  # default condition
            ok = self.script(outfile)
            self.state(outfile)
            if verbose > 0:
                print(
                    "Specify base file name to generate output, "
                    "or 'stdout' to print to screen."
                )
        elif outfile == "stdout" or outfile == sys.stdout:
            ok = self.script()
            self.state()
        else:
            ok = self.script(outfile + ".script")
            if ok:
                print("Wrote script to %s.script" % outfile)
            self.state(outfile + ".states")
            print("Wrote states to %s.states" % outfile)
        if ok:
            if verbose > 0:
                print("Catalog of timing objects:")
                self.catalog()
            if len(usercommands) > 0:
                print("Running user-specified commands...")
            for usercmd in usercommands:
                eval("usercmd[0](%s)" % usercmd[1])
            if self.GenerateFigs:
                print("Generating figures...")
                tstypes = np.array([obj.tstype for obj in self.Catalog])
                indxWaveform = np.where(tstypes == "waveform")[0]
                for kk in indxWaveform:
                    self.Catalog[kk].plot()
        return


    def load_mod(self, ModFile):  # subroutine of loadWDL()
        """load the module definition file to configure global variable slot"""
        typeID = {
            "driver": "drvr",
            "ad": "adc",
            "hvbias": "hvbd",
            "lvds": "lvds",
            "heater": "htr",
            "xvbias": "xvbd",
            "lvbias": "lvbd",
        }
        # slotnum = []
        # btype = []
        with open(ModFile, "r") as f:
            for line in f:
                match = re.search("^\s*SLOT\s+(\d+)\s+(\w+)\s{", line)
                if match is not None:
                    thisSlotNum = int(match.group(1))
                    thisBoardLabel = match.group(2)
                    if thisBoardLabel == "driverx":
                        thisBoardLabel = "driver"
                    if thisBoardLabel == "hvxbias":
                        thisBoardLabel = "hvbias"
                    if thisBoardLabel == "lvxbias":
                        thisBoardLabel = "lvbias"
                    if thisBoardLabel == "heaterx":
                        thisBoardLabel = "heater"
                    if thisBoardLabel in typeID:
                        thisBoardType = typeID[thisBoardLabel]
                        self.slot[thisBoardType].append(thisSlotNum)
                    else:
                        print(
                            "*** Unrecognized board type (%s) in %s"
                            % (thisBoardLabel, ModFile)
                        )
        return


    def __loadSignals__(self, __SignalFile__):  # subroutine of loadWDL()
        """load the signals file"""

        if not os.path.isfile(__SignalFile__):
            print("Signal file specified does not exist (%s)..." % __SignalFile__)
            return False
        with open(__SignalFile__, "r") as f:
            for line in f:
                # look for signal file
                match = re.search("^#define (\w+)\s+(\d+)\s+:\s+(\d+)", line)
                if match is not None:
                    signame = match.group(1)
                    sigslot = int(match.group(2))
                    sigchan = int(match.group(3)) - 1
                    if sigslot in self.slot["drvr"]:
                        sigchan *= 2
                    LVLindx = self.__get_level_index_from_chan_slot__(sigslot, sigchan)
                    if LVLindx >= 0:
                        self.SignalByIndx.update({LVLindx: signame})
                        self.SignalByName.update({signame: LVLindx})
                        if sigslot in self.slot["drvr"]:
                            FASTindx = LVLindx + 1
                            fastname = signame + "_fast"
                            self.SignalByIndx.update({FASTindx: fastname})
                            self.SignalByName.update({fastname: FASTindx})
                    else:
                        print("*** Error in signal file %s ***" % __SignalFile__)
        return


    # subroutine of __loadSignals__()
    def __get_level_index_from_chan_slot__(self, slotnum, channel):
        """given slot and channel,
        returns corresponding the level|change column index"""
        # isDrvr = False
        # 1. determine board type from slot
        for boardname in self.slot:
            if slotnum in self.slot[boardname]:
                # 1. check that channel is valid for board type.
                if channel >= self.__chan_per_board__[boardname]:
                    print(
                        "*** INVALID channel (%d) specified for slot "
                        "(%d,%s) ***" % (channel, slotnum, boardname)
                    )
                    return -1
                # 2. determine index in global slot for board type (0 for
                # the first board of that type, etc.)
                indx_slot = np.where(np.array(self.slot[boardname]) == slotnum)[0][0]
                # 3. calculate the base index (boardname index * slot index)
                signalPartitions = np.cumsum(
                    [
                        0,
                        # !driver-speed-keep
                        self.__chan_per_board__["drvr"] * len(self.slot["drvr"]),
                        self.__chan_per_board__["lvds"] * len(self.slot["lvds"]),
                        self.__chan_per_board__["htr"] * len(self.slot["htr"]),
                        self.__chan_per_board__["xvbd"] * len(self.slot["xvbd"]),
                        self.__chan_per_board__["adc"] * len(self.slot["adc"]),
                        self.__chan_per_board__["back"] * len(self.slot["back"]),
                        self.__chan_per_board__["hvbd"] * len(self.slot["hvbd"]),
                        self.__chan_per_board__["lvbd"] * len(self.slot["lvbd"]),
                    ]
                )
                indx_LVL_boardname = np.where(np.array(self.__boardTypes__) == boardname)[0][0]
                indx_base = (
                    signalPartitions[indx_LVL_boardname]
                    + indx_slot * self.__chan_per_board__[boardname]
                )
                # 4. add the channel offset
                return indx_base + channel


    # only used in TimingSegment.plot()
    def __get_slot_chan_from_level_index__(self, levelColumnIndex):
        """given the column index in the level subset (even columns) of the
        UniqueStateArr, return the slot and channel number"""

        signalPartitions = np.cumsum(
            [
                0,
                self.__chan_per_board__["drvr"] * len(self.slot["drvr"]),  # !driver-speed-keep
                self.__chan_per_board__["lvds"] * len(self.slot["lvds"]),
                self.__chan_per_board__["htr"] * len(self.slot["htr"]),
                self.__chan_per_board__["xvbd"] * len(self.slot["xvbd"]),
                self.__chan_per_board__["adc"] * len(self.slot["adc"]),
                self.__chan_per_board__["back"] * len(self.slot["back"]),
                self.__chan_per_board__["hvbd"] * len(self.slot["hvbd"]),
                self.__chan_per_board__["lvbd"] * len(self.slot["lvbd"]),
            ]
        )
        bn = np.where(levelColumnIndex >= signalPartitions)[-1]
        boardname = self.__boardTypes__[bn]
        rawindex = levelColumnIndex - signalPartitions[bn]
        thisChan = np.mod(rawindex, self.__chan_per_board__[boardname])
        thisSlot = self.slot[boardname][rawindex // self.__chan_per_board__[boardname]]
        return thisSlot, thisChan, boardname


    def __index_of__(self, Name):  # access Catalog elements by name instead of index
        """returns the Catalog index number of a named time segment
        in the waveform"""
        CatalogNames = np.array([obj.name for obj in self.Catalog])
        return np.where(CatalogNames == Name)[0][0]

    def state(self, outfile=None):
        """write states from the UniqueStateArr to the
        file or file handle specified"""

        if outfile is None:
            ofile = sys.stdout
        elif type(outfile) is str:
            ofile = open(outfile, "w")
        else:
            ofile = outfile

        # write the script to /dev/null before writing states.
        self.script("/dev/null", quiet=True)

        ofile.write("[CONFIG]\n")
        ii = 0
        for ii in range(np.size(self.UniqueStateArr, 0)):
            # take out 2 \\'s if we don't need the double \
            prefix = "STATE%d\\" % ii
            ofile.write(prefix + "NAME=STATE%03d\n" % ii)
            offset = 0  # to keep track of position in array
            for clkslot in self.slot["drvr"]:
                ofile.write(prefix + 'MOD%d="' % clkslot)
                statestring = ""
                # driver-speed-keep !!!!!
                for clkchan in range(int(self.__chan_per_board__["drvr"] / 2)):
                    jj_level = offset + 4 * clkchan + 0
                    jj_changeL = offset + 4 * clkchan + 1
                    jj_fast = offset + 4 * clkchan + 2
                    jj_changeF = offset + 4 * clkchan + 3
                    if not (
                        self.UniqueStateArr[ii, jj_changeL] and self.UniqueStateArr[ii, jj_changeF]
                    ):
                        # do not change anything UNLESS level and
                        # fast are both CHANGE
                        # this branch keeps everything the same.
                        statestring += ",1,1,"
                        if self.UniqueStateArr[ii, jj_changeL] != self.UniqueStateArr[ii, jj_changeF]:
                            # write an error message if change flags don't agree.
                            if jj_level / 2 in self.SignalByIndx:
                                thisSigName = self.SignalByIndx[jj_level / 2]
                            else:
                                thisSigName = "%d:%d" % (clkslot, clkchan + 1)
                            print(
                                "*** WARNING: Driver signal (%s) has "
                                "inconsistent KEEP flags ***" % thisSigName
                            )
                            print(
                                "*** check signals or waveform input files for "
                                "consistency  ***"
                            )
                            print(
                                "*** For clock waveforms, 'FAST' or 'SLOW' "
                                "needs to be specified ***"
                            )
                    else:
                        # in USA, 0==FAST 1==SLOW.  IN ACF, 1==FAST, 0==SLOW.
                        statestring += "%g,%d,0," % (
                            self.UniqueStateArr[ii, jj_level],
                            int(not bool(self.UniqueStateArr[ii, jj_fast])),
                        )

                statestring = statestring[:-1] + '"'
                ofile.write(statestring + "\n")
                offset += 2 * self.__chan_per_board__["drvr"]  # !driver-speed-keep
            for lvdsslot in self.slot["lvds"]:
                ofile.write(prefix + 'MOD%d="' % lvdsslot)
                statestring = ""
                for lvdschan in range(self.__chan_per_board__["lvds"]):
                    jj_level = offset + 2 * lvdschan + 0
                    jj_change = offset + 2 * lvdschan + 1
                    if not self.UniqueStateArr[ii, jj_change]:
                        statestring += "1,1,"
                    else:
                        statestring += "%d,0," % (self.UniqueStateArr[ii, jj_level])
                statestring = statestring[:-1] + '"'
                ofile.write(statestring + "\n")
                offset += 2 * self.__chan_per_board__["lvds"]
            for htrslot in self.slot["htr"]:
                ofile.write(prefix + 'MOD%d="' % htrslot)
                statestring = ""
                for htrchan in range(self._chan_per_board__["htr"]):
                    jj_level = offset + 2 * htrchan + 0
                    jj_change = offset + 2 * htrchan + 1
                    if not self.UniqueStateArr[ii, jj_change]:
                        statestring += "1,1,"
                    else:
                        statestring += "%d,0," % (self.UniqueStateArr[ii, jj_level])
                statestring = statestring[:-1] + '"'
                ofile.write(statestring + "\n")
                offset += 2 * self.__chan_per_board__["htr"]
            for xvslot in self.slot["xvbd"]:  # this is similar to the hvbd states
                # In teh acf there are two entries, and they are
                # (!pKEEP,pchan,pvalue,!nKeep,nchan,nvalue)
                ofile.write(prefix + 'MOD%d="' % xvslot)
                statestring = ""
                # Do like the hvbd processing, but on positive bits (first half)
                # and then the negative bits (second half)
                # really only want the first half of all xvbd states
                n_xvbd_pos_X_2 = 2 * self.__chan_per_board__["xvbd"] / 2
                pxvbdLevel = self.UniqueStateArr[ii, offset : offset + n_xvbd_pos_X_2 : 2]
                pxvbdKeep = np.invert(
                    self.UniqueStateArr[ii, offset + 1 : offset + n_xvbd_pos_X_2 : 2].astype(
                        "bool"
                    )
                ).astype("int")
                # Check that there is only one non-keep for the positive voltages
                # in pxvbdKeep
                pKeepSum = sum(pxvbdKeep)
                # nothing changed and only first half of xvbd channels
                if pKeepSum == (self.__chan_per_board__["xvbd"] / 2):
                    # need a comma at the end of string since negative bits will
                    # come after
                    statestring += "0,1,0,"
                # proper change for positive voltage
                elif (pKeepSum + 1) == (self.__chan_per_board__["xvbd"] / 2):
                    # 2. get the level corresponding to on the non-keep.
                    pxvbd_chan = np.where(pxvbdKeep == 0)[0]
                    # again need comma at end of pops string
                    statestring += "1,%d,%g," % (pxvbd_chan + 1, pxvbdLevel[pxvbd_chan])
                else:
                    print(
                        "Error in positive XVBD state call -- multiple changes "
                        "in a state"
                    )
                # Do just like hvbd processing, but now on the negative bits
                # (second half)
                # skip over the positive xvbd voltages
                offset += 2 * self.__chan_per_board__["xvbd"] / 2
                # really only want the second half of all xvbd states
                n_xvbd_neg_X_2 = 2 * self.__chan_per_board__["xvbd"] / 2
                nxvbdLevel = self.UniqueStateArr[ii, offset : offset + n_xvbd_neg_X_2 : 2]
                nxvbdKeep = np.invert(
                    self.UniqueStateArr[ii, offset + 1 : offset + n_xvbd_neg_X_2 : 2].astype(
                        "bool"
                    )
                ).astype("int")
                # Check that there is only one non-keep for the negative voltages
                # in nxvbdKeep
                nKeepSum = sum(nxvbdKeep)
                # nothing changed and only second half of xvbd channels
                if nKeepSum == (self.__chan_per_board__["xvbd"] / 2):
                    statestring += "0,1,0"
                # proper change for positive voltage
                elif (nKeepSum + 1) == (self.__chan_per_board__["xvbd"] / 2):
                    # 2. get the level corresponding to on the non-keep.
                    nxvbd_chan = np.where(nxvbdKeep == 0)[0]
                    statestring += "1,%d,%g" % (nxvbd_chan + 1, nxvbdLevel[nxvbd_chan])
                else:
                    print(
                        "Error in negative XVBD state call -- multiple changes "
                        "in a state"
                    )
                #            statestring = statestring[:-1] + '"'
                ofile.write(statestring + '"\n')
                # skip over the last half of the xvbd channels
                offset += 2 * self.__chan_per_board__["xvbd"] / 2
            for adcslot in self.slot["adc"]:
                ofile.write(prefix + 'MOD%d="' % adcslot)
                statestring = ""
                jj_level = offset
                jj_change = offset + 1
                if not self.UniqueStateArr[ii, jj_change]:
                    statestring += "0,1,"
                else:
                    statestring += "%d,0," % (self.UniqueStateArr[ii, jj_level])
                statestring = statestring[:-1] + '"'
                ofile.write(statestring + "\n")
                offset += 2
            if True:  # Backplane
                n_back = self.__chan_per_board__["back"]
                bn = 2 ** np.arange(0, n_back)  # to convert backplane states to hex
                level = sum(
                    bn * self.UniqueStateArr[ii, (offset + 0) : (offset + 2 * n_back) : 2]
                )
                keep = sum(
                    bn
                    * (
                        np.invert(
                            self.UniqueStateArr[
                                ii, (offset + 1) : (offset + 2 * n_back) : 2
                            ].astype("bool")
                        ).astype("int")
                    )
                )
                ofile.write(prefix + 'CONTROL="%X,%X"\n' % (int(level), int(keep)))
                offset += 2 * n_back
            for hvbdslot in self.slot["hvbd"]:  # different from the other states,
                # in the acf, there is only one entry, and it is
                # (!KEEP, chan, value)
                ofile.write(prefix + 'MOD%d="' % hvbdslot)
                statestring = ""
                n_hvbd_X_2 = 2 * self.__chan_per_board__["hvbd"]
                hvbdLevel = self.UniqueStateArr[ii, offset : offset + n_hvbd_X_2 : 2]
                hvbdKeep = np.invert(
                    self.UniqueStateArr[ii, offset + 1 : offset + n_hvbd_X_2 : 2].astype("bool")
                ).astype("int")
                # 1. check that there is only one non-keep in hvbdKeep
                KeepSum = sum(hvbdKeep)
                if KeepSum == self.__chan_per_board__["hvbd"]:  # nothing changed
                    statestring += "0,1,0"
                elif (KeepSum + 1) == self.__chan_per_board__["hvbd"]:  # proper change
                    # 2. get the level corresponding to the non-keep.
                    hvbd_chan = np.where(hvbdKeep == 0)[0]
                    statestring += "1,%d,%g" % (hvbd_chan + 1, hvbdLevel[hvbd_chan])
                else:
                    print("Error in HVBD state call -- multiple changes in a state")
                ofile.write(statestring + '"\n')
                offset += n_hvbd_X_2
            for lvbdslot in self.slot["lvbd"]:
                # this is an ugly amalgamation of lvds and hvbd...
                ofile.write(prefix + 'MOD%d="' % lvbdslot)
                statestring = ""
                n_LVBIAS = 30
                n_LVDIO = 8
                # the "-30" in the for loop below is to exclude the 30 bias channels
                # This will always evaluate to 0, maybe chan_per_board should be 38
                # this loop is supposed to create the DIO states
                # maybe we'll make it range(30:38) to put the DIO at the end
                # and the voltages at the beginning, but as of now 7/23/2020 it's
                # DIO then voltages Make the DIO the buts after the voltages, set
                # offset = 8 move offset to past voltages
                offset += 2 * (self.__chan_per_board__["lvbd"] - n_LVDIO)
                for lvbdchan in range(self.__chan_per_board__["lvbd"] - n_LVBIAS):
                    jj_level = offset + 2 * lvbdchan + 0
                    jj_change = offset + 2 * lvbdchan + 1
                    if not self.UniqueStateArr[ii, jj_change]:
                        statestring += "1,1,"
                    else:
                        statestring += "%d,0," % (self.UniqueStateArr[ii, jj_level])

                # move back to beginning of voltages
                offset -= 2 * (self.__chan_per_board__["lvbd"] - n_LVDIO)
                # move the offset past the 8 DIO's
                # offset += 2*(__chan_per_board__['lvbd'] - n_LVBIAS)
                # now for the "HVBD"-style part of this board
                n_lvbd_X_2 = 2 * n_LVBIAS  # there are only 30 channels of voltages
                # the offset will be
                lvbdLevel = self.UniqueStateArr[ii, offset : offset + n_lvbd_X_2 : 2]
                lvbdKeep = np.invert(
                    self.UniqueStateArr[ii, offset + 1 : offset + n_lvbd_X_2 : 2].astype("bool")
                ).astype("int")
                # 1. check that there is only one non-keep in lvbdKeep
                KeepSum = sum(lvbdKeep)
                # __chan_per_board__['lvbd']: # nothing changed
                if KeepSum == n_LVBIAS:
                    statestring += "0,1,0"
                # __chan_per_board__['lvbd']: # proper change
                elif (KeepSum + 1) == n_LVBIAS:
                    # 2. get the level corresponding to the non-keep.
                    lvbd_chan = np.where(lvbdKeep == 0)[0]
                    statestring += "1,%d,%g" % (lvbd_chan + 1, lvbdLevel[lvbd_chan])
                else:
                    print("Error in LVBD state call -- multiple changes in a state")
                ofile.write(statestring + '"\n')
                # offset += n_lvbd_X_2 # this is fine for voltages after DIO
                # use for DIO after voltages
                offset += 2 * (self.__chan_per_board__["lvbd"])

        ofile.write("STATES=%d\n" % (ii + 1))

        # CatalogNames = [obj.name for obj in Catalog]
        # Easter egg activated by existence of a sequence or waveform named
        # 'RawPixel'.  Parameter 'Pixels' and the wdl-calculated clocks for
        # 'RawPixel' determines the maximum safe number of raw samples to take on a
        # line (the largest multiple of 1024 samples).
        #
        # Note that the Parameters 'Pixels' and 'Lines' determine the action of the
        # ACF loop, whereas the ACF keywords 'LINECOUNT' and 'PIXELCOUNT' determine
        # the size of the cds image. Generally, they are the same, but the keyword
        # values can be smaller than the parameter values.
        #
        # In specifying the raw data section, everything counts from 0, except for
        # the number of RAWSAMPLES.  In specifying the CDS image or the loop, the
        # values count from 1.
        #
        # The number of RAWSAMPLES is maximized UNLESS the ACF keyword 'RAWENDLINE'
        # is greater than the Parameter 'Lines' - 1.
        #
        # This Easter egg may be abandoned in favor of a post-processing script
        # that looks at the ACF and the WDL files and adjusts the ACF accordingly.
        ###
        # if 'RawPixel' in CatalogNames and 'Pixels' in Parameters:
        #     RP_label = __index_of__('RawPixel')
        #     RP_time  = Catalog[RP_label].time
        #     samples_per_line = Parameters['Pixels'] * RP_time
        #     rawsamples_per_line = int(np.floor(samples_per_line / 1024.) * 1024)
        #     rawsamples_per_line = max(rawsamples_per_line, 1024)
        #     ofile.write('RAWSAMPLES=%d\n'%rawsamples_per_line)
        #     if samples_per_line != rawsamples_per_line:
        #         print('Warning: %d samples per line will be skipped' %
        #               (samples_per_line-rawsamples_per_line))
        #     if 'Lines' in Parameters:
        #         cds_size = Parameters['Pixels']*Parameters['Lines']*4**3
        #         rawspace = 768*2**20 - cds_size
        #         maxrawlines = rawspace/(rawsamples_per_line*2)
        #         if maxrawlines < Parameters['Lines'] and maxrawlines > 0:
        #             ofile.write('RAWENDLINE=%d\n'%(maxrawlines-1))
        if ofile.name != "<stdout>":  # don't close stdout!
            ofile.close()


    def script(self, outfile=None, quiet=False):
        """generate ACF scripts and calculates times.  Reports state of
        Catalog if a consistent script cannot be generated"""

        jj_nocalc = np.where(np.isnan([obj.time for obj in self.Catalog]))[0]
        N_nocalc = len(jj_nocalc)  # number of segments with uncalculated time
        while N_nocalc > 0:
            for kk in jj_nocalc:  # was reversed before
                if self.Catalog[kk] is not None:
                    self.Catalog[kk].script("/dev/null")
            N_old = N_nocalc
            jj_nocalc = np.where(np.isnan([obj.time for obj in self.Catalog]))[0]
            N_nocalc = len(jj_nocalc)
            if N_nocalc == N_old:
                break

        if N_nocalc == 0:
            # remove the existing file before writing to it.
            if outfile is None:
                outfilehandle = sys.stdout
            elif type(outfile) is str:
                outfilehandle = open(outfile, "w")
            else:
                outfilehandle = outfile
            if len(self.Parameters) > 0:
                outfilehandle.write("[PARAMETER#]\n")
                for param in self.Parameters:
                    outfilehandle.write("%s=%d\n" % (param, self.Parameters[param]))
            if len(self.Constants) > 0:
                outfilehandle.write("[CONSTANT#]\n")
                for const in self.Constants:
                    outfilehandle.write("%s=%d\n" % (const, self.Constants[const]))
            outfilehandle.write("[LINE#]\n")
            if outfilehandle.name != "<stdout>":
                outfilehandle.close()
            for TS in self.Catalog:
                TS.script(outfile)
        elif not quiet:
            print("Timing did not converge:")
            self.catalog()
            print("No script output due to undefined sequence or waveform.")
            return False

        return True


    # @register_line_magic
    def catalog(self):  # MagicNullArgument=None):
        """print catalog in human-readable form"""
        print("index  label                                type  exit  time [us]")
        print("-----------------------------------------------------------------")
        for jj in range(len(self.Catalog)):
            print(
                "%4d:  %-32s %-8s   %03d %10.2f"
                % (
                    jj,
                    self.Catalog[jj].name,
                    self.Catalog[jj].tstype,
                    self.Catalog[jj].ExitState,
                    self.Catalog[jj].time / 100.0,
                )
            )


    # @register_line_magic
    def wplot(self, TimingObjectLabel):
        """Plot the waveform of the specified sequence"""
        CatalogNames = [obj.name for obj in self.Catalog]
        if TimingObjectLabel not in CatalogNames:
            print(CatalogNames)
            return

        self.Catalog[self.__index_of__(TimingObjectLabel)].plot()

        return