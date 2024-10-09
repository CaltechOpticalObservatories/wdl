import numpy as np
import matplotlib
matplotlib.use('Agg')  # or any other non-interactive backend
# import matplotlib.mlab as mlab
import matplotlib.pyplot as plt
import scipy.sparse as sparse 
import re
import sys

class TimingSegment(object):
    """general timing segment object (waveforms and sequences)
    to generate ACF states and script"""

    def __init__(self, catalog=[], UniqueStateArr = np.array([]),  signal_by_index={}, name="", TStype="", nperiods=1, endline=-2):
        """initialize state definition arrays. by default nperiods is minimal
        and there is no auto-generated end to the segment"""

        # endline defines where to go at the end of this timing segment
        # -2: nothing
        # -1: RETURN name
        # >=0: GOTO SubName[endline]
        # this is handled at the script-writing stage.
        self.endline = endline
        self.catalog = catalog
        self.unique_state_arr = UniqueStateArr
        self.signal_by_index = signal_by_index

        # provide a unique identifier for this timing segment and
        # catalog its name in the list of subroutines
        __seq_ID__ = 0
        __TStypes__ = ("", "waveform", "sequence")
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
        CatalogNames = [obj.name for obj in self.catalog]
        NotifyTSTypeChange = False
        if TStype not in __TStypes__:
            # TStype must be changed here if invalid, but notification
            # has to wait until self.label is known
            NotifyTSTypeChange = True
            TStype_orig = TStype
            TStype = ""
        else:
            TStype_orig = ""

        if name not in CatalogNames:  # initialize entry in Catalog
            self.label = __seq_ID__
            __seq_ID__ += 1
            self.catalog.append(self)
        else:  # or REINITIALIZE entry in Catalog
            self.label = self.__index_of__(name)
            self.catalog[self.label] = self

        self.name = name
        self.time = np.nan
        self.tstype = TStype

        if NotifyTSTypeChange:
            print("invalid TimingSegment type (TStype) specified: %s" % TStype_orig)
            print("modify <ThisModule>.Catalog[%d].tstype" % self.label)

        # target length of the sequence -- may be exceeded if timing
        # states are defined at t > nperiods
        self.nperiods = nperiods

        self.sequenceDef = []  # subroutine calls

        # this is meant to replace self.XXXDef except sequenceDef.
        self.events = {}
        for kk in self.__chan_per_board__:
            self.events.update({kk: []})
            # initialize each type of board with sufficient channels
            for jj in range(len(self.slot[kk]) * self.__chan_per_board__[kk]):
                self.events[kk].append([])

        # create the do-nothing-state and insert it into UniqueStateArr
        # all levels = 0, all driver speeds = 1, all keeps = 1
        if np.size(self.unique_state_arr, 0) == 0:  # empty condition
            levels = np.hstack(
                (
                    np.array([[0, 0] * int(len(self.events["drvr"]) / 2)]),
                    np.zeros(
                        (
                            1,
                            len(self.events["lvds"])
                            + len(self.events["htr"])
                            + len(self.events["xvbd"])
                            + len(self.events["adc"])
                            + len(self.events["back"])
                            + len(self.events["hvbd"])
                            + len(self.events["lvbd"]),
                        )
                    ),
                )
            )
            changes = np.zeros(
                (
                    1,
                    # !driver-speed-keep
                    len(self.events["drvr"])
                    + len(self.events["lvds"])
                    + len(self.events["htr"])
                    + len(self.events["xvbd"])
                    + len(self.events["adc"])
                    + len(self.events["back"])
                    + len(self.events["hvbd"])
                    + len(self.events["lvbd"]),
                )
            )
            self.unique_state_arr = np.reshape(np.vstack((levels, changes)), (1, -1), "F")

        # Default exit state and level (not necessarily consistent!)
        self.ExitState = 0
        self.ExitLevel = self.unique_state_arr[0:1, 0::2]  # :1 keeps it 2D
        # other defaults
        self.Params = {}
        self.Consts = {}

    def __tmax(self, reset=False):  # subroutine of __make_states()
        """determines the number of periods in the timing script"""
        if reset:
            tmax = 1
        else:
            tmax = self.nperiods
        for chan in range(len(self.events["drvr"])):
            for tt in range(len(self.events["drvr"][chan])):
                tmax = max(tmax, self.events["drvr"][chan][tt][0] + 1)
        for chan in range(len(self.events["lvds"])):
            for tt in range(len(self.events["lvds"][chan])):
                tmax = max(tmax, self.events["lvds"][chan][tt][0] + 1)
        for chan in range(len(self.events["htr"])):
            for tt in range(len(self.events["htr"][chan])):
                tmax = max(tmax, self.events["htr"][chan][tt][0] + 1)
        for chan in range(len(self.events["xvbd"])):
            for tt in range(len(self.events["xvbd"][chan])):
                tmax = max(tmax, self.events["xvbd"][chan][tt][0] + 1)
        for chan in range(len(self.events["adc"])):
            for tt in range(len(self.events["adc"][chan])):
                tmax = max(tmax, self.events["adc"][chan][tt][0] + 1)
        for chan in range(len(self.events["back"])):
            for tt in range(len(self.events["back"][chan])):
                tmax = max(tmax, self.events["back"][chan][tt][0] + 1)
        for chan in range(len(self.events["hvbd"])):
            for tt in range(len(self.events["hvbd"][chan])):
                tmax = max(tmax, self.events["hvbd"][chan][tt][0] + 1)
        for chan in range(len(self.events["lvbd"])):
            for tt in range(len(self.events["lvbd"][chan])):
                tmax = max(tmax, self.events["lvbd"][chan][tt][0] + 1)
        for tt in range(len(self.sequenceDef)):
            tmax = max(tmax, self.sequenceDef[tt][0] + 1)
        return tmax

    def __fill_state(self, boardtype):  # subroutine of __make_states()
        """fill level and boolean change arrays (row sparse format) for state
        definition.  Called in __make_states() for each board type."""

        events = self.events[boardtype]
        n_chan = len(events)

        row = []
        col = []
        val = []

        for chan in range(n_chan):  # loop over channels
            for jj in range(len(events[chan])):  # loop over entries
                time = events[chan][jj][0]
                if (boardtype == "drvr") and (np.mod(chan, 2) == 1):
                    # 0 <--> 1 for FAST flags
                    level = int(not events[chan][jj][1])
                else:
                    level = events[chan][jj][1]

                # level info
                col.append(2 * chan)
                row.append(time)
                val.append(level)

                # change/keep info
                col.append(2 * chan + 1)
                row.append(time)
                val.append(1)

        if len(row) > 0:
            # the first bit here is to handle multple entries in the waveform
            # this takes the last value requested.
            rc = np.array(row) + 1j * np.array(col)
            # index of last unique element
            uniq_j = len(rc) - np.unique(rc[::-1], return_index=True)[1] - 1
            # only arrays can be indexed, not lists????
            val = np.array(val)[uniq_j]
            row = np.array(row)[uniq_j]
            col = np.array(col)[uniq_j]
            levelchangematrix = sparse.csc_matrix(
                (val, (row, col)), shape=(self.nperiods, 2 * n_chan)
            )
        else:
            # if the levelchangematrix is all zeros
            levelchangematrix = sparse.csc_matrix((self.nperiods, 2 * n_chan))

        return levelchangematrix

    def __make_states(self):
        """Make the state array from the event array. In here are the initial
        definitions of do_anything_tt, do_anything_dt, unique_state_ID.  Adds
        new states to UniqueStateArr.

        """
        # enlarge nperiods, if necessary, to encompass all events
        self.nperiods = self.__tmax()

        # these are all nperiods X nchannel arrays
        drvr_level_change = self.__fill_state("drvr")
        lvds_level_change = self.__fill_state("lvds")
        htr_level_change = self.__fill_state("htr")
        xvbd_level_change = self.__fill_state("xvbd")
        adcs_level_change = self.__fill_state("adc")
        back_level_change = self.__fill_state("back")
        hvbd_level_change = self.__fill_state("hvbd")
        lvbd_level_change = self.__fill_state("lvbd")

        # fill the sequence array (kept separate from STATEs for now)
        call_subroutine_tt = []
        for event in range(len(self.sequenceDef)):
            call_subroutine_tt.append(self.sequenceDef[event][0])

        # GENERATE THE STATES #
        # even columns are levels or slew rate switches, odd columns are CHANGE
        # flags relative to Archon, I've inserted an extra change flag for
        # driver to produce a more regular pattern
        #
        #   L1a K1a L2a K2a L3a K3a
        #   L1b K1b L2b K2b L3b K3b
        #   L1c K1c L2c K2c L3c K3c
        #
        state_arr = sparse.hstack(
            (
                drvr_level_change,
                lvds_level_change,
                htr_level_change,
                xvbd_level_change,
                adcs_level_change,
                back_level_change,
                hvbd_level_change,
                lvbd_level_change,
            ),
            format="csc",
        )

        # Find unique states in state_arr and store them in UniqueStateArr
        # UNIQUE_STATE_ID will hold the row in UNIQUE_STATES for each time step

        # unique_state_ID = np.zeros((self.nperiods,)).astype('int')

        (times, chans, datas) = sparse.find(state_arr)
        times = np.unique(times)
        unique_state_IDs = []
        for tt in times:
            state_matches_ustate = np.where(
                np.sum(
                    np.abs(np.asarray(state_arr.getrow(tt).todense()) - self.unique_state_arr),
                    1,
                )
                == 0
            )[0]
            if len(state_matches_ustate) == 0:
                # unique_state_ID[tt] = len(UniqueStateArr)
                unique_state_IDs.append(len(self.unique_state_arr))
                self.unique_state_arr = np.vstack(
                    (self.unique_state_arr, state_arr.getrow(tt).toarray())
                )
            elif len(state_matches_ustate) > 1:
                print("problem: state matches multiple unique states")
            else:
                # unique_state_ID[tt] = state_matches_ustate[0]
                unique_state_IDs.append(state_matches_ustate[0])

        unique_state_ID = sparse.csc_matrix(
            (unique_state_IDs, (np.zeros(np.shape(times)), times)),
            shape=(1, self.nperiods),
            dtype="int",
        )

        # identify the time steps where something happens and calculate the
        # time gaps. Do_nothing_state = 0 # by definition in initialization of
        # first TS## do_something_tt = mlab.find(unique_state_ID != do_nothing
        # _state)
        junk, do_something_tt, more_junk = sparse.find(unique_state_ID)
        do_anything_tt = np.unique(
            np.hstack(
                (
                    [0],  # start
                    do_something_tt,  # states
                    call_subroutine_tt,  # sub calls
                    self.nperiods - 1,
                )
            )
        )  # end
        do_anything_dt = np.hstack((np.diff(do_anything_tt), [0]))

        # self-ify the keeper variables
        self.sequence_times = np.array(call_subroutine_tt).astype("int")
        self.do_anything_tt = do_anything_tt.astype("int")
        self.do_anything_dt = do_anything_dt.astype("int")
        self.unique_state_ID = unique_state_ID

        return
        # end of __make_states

    def script(self, outfile=sys.stdout):
        """Append script to file or file handle, generates new unique states
        as needed. Calculate time for time segment to complete, stores the
        exit state and the parameters used in Catalog"""

        if type(outfile) is str:
            ofile = open(str(outfile), "a")
        else:
            ofile = outfile

        if not hasattr(self, "unique_state_ID"):
            self.__make_states()

        global Parameters
        global __padmax__

        if self.name != "":
            ofile.write("%s: # %s\n" % (self.name, self.tstype))

        do_anything_tt = self.do_anything_tt
        do_anything_dt = self.do_anything_dt

        count = -1
        time = 0

        if do_anything_dt[0] < 0:
            print("waveform definition error - event at t=0")
        for jj in range(len(do_anything_dt)):
            pad = __padmax__  # column to start comment
            EOL = False  # end of line flag
            count += 1
            time += 1
            pad -= 11
            this_state = self.unique_state_ID[0, do_anything_tt[jj]]
            ofile.write("STATE%03d; " % this_state)
            # overwrite the exit state if the unique_state_ID is nonzero
            if this_state > 0:
                self.ExitState = this_state
                # until __make_waveform is run, this is the best guess
                # for the exit levels
                self.ExitLevel = self.unique_state_arr[this_state : this_state + 1, 0::2]

            seq_indx = np.where(self.sequence_times == do_anything_tt[jj])[0]
            # true condition means this is a subroutine call,
            # not a state change.
            if len(seq_indx):
                this_sub_call = self.sequenceDef[seq_indx[0]][1]
                pad -= len(this_sub_call)
                ofile.write("%s" % this_sub_call)
                EOL = True
                if this_sub_call[0:3].upper() == "IF ":
                    # get the first word after IF...
                    regexmatch = re.search(r"\w+\s+!?([\w]+)", this_sub_call)
                    this_param = regexmatch.group(1)
                    try:  # demo if this_param is an integer
                        int(this_param)
                    # if it's not, then it's a parameter,
                    # so add it to self.Param dict
                    except:
                        if this_param not in self.Params:
                            if this_param not in Parameters:
                                # use 0 as default param value
                                Parameters.update({this_param: 0})
                            self.Params.update({this_param: Parameters[this_param]})

                # increment count for Param-- or Param++
                if "--" in this_sub_call or "++" in this_sub_call:
                    # this assumes that the decrement is not happening in the
                    # IF TEST part of a call is something like IF TEST-- TEST2--
                    # even legal in ACF?
                    count += 1
                    time += 1
                    # I'm assuming it's a bare call
                    this_param = this_sub_call[:-2]
                    if this_param not in self.Params:
                        if this_param not in Parameters:
                            # use 0 as default param value
                            Parameters.update({this_param: 0})
                        self.Params.update({this_param: Parameters[this_param]})
                else:
                    # parse the label name and iterations from the sub call
                    # and use that info to calculate the time.
                    regexmatch = re.search(
                        r"([\w]+)\s+([\w]+)(\(([\w]+)\))?$", this_sub_call
                    )
                    if regexmatch is None:
                        print(
                            "*** Regular expression could not match wdl "
                            "input in %s %s. ***" % (self.tstype, self.name)
                        )
                        print("input string: '%s'" % this_sub_call)
                    this_sub_command = regexmatch.group(1)
                    this_sub_name = regexmatch.group(2)
                    # ultimately if it's not an integer,
                    # it should be pulled from parameters
                    try:
                        this_sub_iterations = int(regexmatch.group(4))
                    except:
                        this_sub_iterations = 1
                        if regexmatch.lastindex > 2:
                            this_param = regexmatch.group(4)
                            if this_param not in self.Params:
                                if this_param not in Parameters:
                                    # use 0 as default param value
                                    Parameters.update({this_param: 0})
                                self.Params.update({this_param: Parameters[this_param]})
                    SubName = [obj.name for obj in self.catalog]
                    if this_sub_name in SubName:
                        this_sub_time = self.catalog[self.__index_of__(this_sub_name)].time
                        # there may be a cleaner implementation
                        # for this_sub_time.
                    else:
                        # if the called subroutine has not been defined in
                        # Catalog, then insert a holder if the inputs are
                        # sensible, this code never gets excercised
                        this_sub_time = np.nan
                        # initialize a timing segment with this name
                        TimingSegment(self.catalog, self.unique_state_arr, self.signal_by_index, this_sub_name)
                        print("boo!")
                    if this_sub_command.upper() == "CALL":
                        # only add time if this is not a call to itself
                        # (usually RETURN)
                        time += this_sub_time * this_sub_iterations
                        # update the exit state and level with that of
                        # the subroutine
                        if self.catalog[self.__index_of__(this_sub_name)].ExitState != 0:
                            self.ExitState = self.catalog[
                                self.__index_of__(this_sub_name)
                            ].ExitState
                            self.ExitLevel = self.catalog[
                                self.__index_of__(this_sub_name)
                            ].ExitLevel
            # END OF SUBROUTINE PARSING
            if do_anything_tt[jj] == self.nperiods - 1:
                if self.endline == -1:
                    pad -= 7 + len(self.name)
                    ofile.write("RETURN %s" % self.name)
                elif 0 <= self.endline < len(self.catalog):
                    pad -= 6 + len(self.catalog[self.endline].name)
                    ofile.write("GOTO %s" % self.catalog[self.endline].name)
                    # SubName[self.endline]))
                EOL = True
            if (do_anything_dt[jj] > 1) and not EOL:
                # if the time to the next THING is more than 1 period
                # away, then print a DO_NOTHING
                count += do_anything_dt[jj] - 1
                time += do_anything_dt[jj] - 1
                pad -= 8
                ofile.write("STATE000")  # the do-nothing-state
                if do_anything_dt[jj] > 2:
                    # add the repeat counter if more than 1 are required.
                    pad -= np.ceil(np.log10(do_anything_dt[jj] - 1)).astype(int) + 2
                    ofile.write("(%d)" % (do_anything_dt[jj] - 1))
            if pad < __padmax__:
                # comment line with the counter, END LINE
                if pad < 1:
                    __padmax__ -= pad - 1
                ofile.write("%s# %6d %8.0f\n" % (" " * pad, max(count, 0), time))
        self.time = time
        if ofile.name != "<stdout>":  # don't close stdout!
            ofile.close()

        return True

    def __make_waveform(self, initialLevel=None):
        """generate a signal-level matrix from the state array.  called by
        TimingSegment.plot() or by recursion"""
        # should be sparse?
        state_arr = np.atleast_2d(
            self.unique_state_arr[np.squeeze(self.unique_state_ID.toarray()), :]
        )
        keep = np.invert(state_arr[:, 1::2].astype("bool"))
        level = state_arr[:, 0::2]

        if initialLevel is None:
            initialLevel = self.ExitLevel

        # true level should be generated incrementally with  calls to subs.
        true_level = initialLevel
        this_level = np.zeros(np.shape(true_level))
        for tt in range(self.nperiods):
            # keep
            this_level[0, keep[tt, :]] = true_level[-1, keep[tt, :]]
            # get new values
            this_level[0, ~keep[tt, :]] = level[tt, ~keep[tt, :]]
            true_level = np.vstack((true_level, this_level))

            seq_indx = np.where(self.sequence_times == tt)[0]
            # true condition means this is a subroutine call,
            # not a state change.
            if len(seq_indx):
                this_sub_call = self.sequenceDef[seq_indx[0]][1]
                match = re.search(
                    r"(IF\s+(?P<N0>!)?(?P<P0>\w+)(?P<D0>--)?\s+)?"
                    + r"((?P<CMD>RETURN|GOTO|CALL)\s+(?P<TS>\w+)\(?)?"
                    + r"(\(?(?P<P1>\w+)?(?P<D1>--)?)\)?",
                    this_sub_call,
                )
                #  REGEX labels:
                #  N0: negation of IF demo (!)
                #  P0: IF demo parameter
                #  D0: decrement of demo parameter (--)
                #  CMD: branching command (RETURN, GOTO or CALL)
                #  TS: Time segment to call
                #  P1: Parameter
                #  D1: Parameter decrement (--)
                runcmd = True
                if match.group("P0") is not None:
                    runcmd = self.Params[match.group("P0")]
                    if match.group("N0") == "!":
                        runcmd = not runcmd
                    # decrement P0
                    if match.group("D0") == "--" and self.Params[match.group("P0")] > 0:
                        self.Params[match.group("P0")] -= 1
                if runcmd:
                    if match.group("P1") is not None:
                        if match.group("P1").isdigit():
                            repeats = int(match.group("P1"))
                        else:
                            repeats = self.Params[match.group("P1")]
                    else:
                        repeats = 1
                    # decrement P0
                    if match.group("D1") == "--" and self.Params[match.group("P1")] > 0:
                        self.Params[match.group("P1")] -= 1
                    if match.group("CMD") == "CALL" and match.group("TS") is not None:
                        print("calling %s" % match.group("TS"))
                        TSindx = self.__index_of__(match.group("TS"))
                        for jj in range(repeats):
                            calledLevel = self.catalog[TSindx].__make_waveform(this_level)
                            true_level = np.vstack((true_level, calledLevel))
                            this_level = true_level[-1:, :]

        # chop off the initial condition.
        true_level = true_level[1:, :]
        # update the Exit level
        self.ExitLevel = true_level[-1:, :]  # colon after -1 keeps the array 2D
        return true_level

    def plot(self, cycles=2, initialLevel=None):
        """plot the states in the timing script. optionally takes an initial
        condition (default=last non-zero state)"""

        if self.tstype == "sequence":
            print("plt_waves is intended for waveforms. " "this object is a sequence")
            print("Warning: results may not make sense.")
        if not hasattr(self, "unique_state_ID"):
            self.__make_states()

        state_arr = np.atleast_2d(
            self.self.unique_state_arr[np.squeeze(self.unique_state_ID.toarray()), :]
        )
        keep = np.invert(state_arr[:, 1::2].astype("bool"))
        level = state_arr[:, 0::2]

        if initialLevel is None:
            initialLevel = self.ExitLevel
        true_level = np.zeros((0, np.shape(level)[1]))  # 0xN empty array
        for jj in range(cycles):
            true_level = np.vstack((true_level, self.__make_waveform(initialLevel)))
            initialLevel = self.ExitLevel

        # find the static channels
        nonstatic = np.asarray(
            [x != y for x, y in zip(np.amax(true_level, 0), np.amin(true_level, 0))]
        )
        # nonstatic = np.amax(true_level, 0) != np.amin(true_level, 0)
        # find the commanded channels
        commanded = np.amin(keep, 0) == 0

        print("--- %s" % self.name, end=" ")

        if sum(nonstatic):
            # calculate the slot/channel numbers for the nonstatic traces.
            # drvr, lvds, adc, back, hvbd, lvbd
            signalID = np.where(nonstatic)[0]
            nsignals = len(signalID)

            fig = plt.figure(self.label)
            plt.clf()
            figXLeft = 0.15
            figYBtm = 0.1
            figYTop = 0.06
            gap = 0.02
            vspace = (1 - figYBtm - figYTop) / nsignals
            vgap = vspace * gap // 2
            axes = []
            kk = 0
            for kk in range(nsignals):
                thisSigID = signalID[nsignals - kk - 1]
                (thisSlot, thisChan, boardname) = self.__get_slot_chan_from_level_index__(
                    thisSigID
                )
                if thisSigID in self.signal_by_index:
                    thisSigLabel = self.signal_by_index[thisSigID]
                else:
                    thisSigLabel = "???"
                # left, bottom, width, height (range 0 to 1)
                axes.append(
                    fig.add_axes(
                        [
                            figXLeft,
                            figYBtm + kk * vspace + vgap,
                            0.97 - figXLeft,
                            vspace * (1 - gap),
                        ]
                    )
                )
                period_ns = 10  # ns
                period_us = period_ns // 1000.0
                time = np.arange(np.shape(true_level)[0]) * period_us
                axes[kk].plot(time, true_level[:, thisSigID])
                axes[kk].set_ylabel(
                    "%s\n%s\n(%d,%d)"
                    % (boardname, thisSigLabel, thisSlot, thisChan + 1)
                )
                yy = axes[kk].set_ylim()
                dy = np.diff(yy)
                yy = axes[kk].set_ylim((yy[0] - 0.1 * dy, yy[1] + 0.1 * dy))
                for nn in range(cycles):
                    axes[kk].plot(
                        [len(time) / cycles * period_us * (nn + 1)] * 2, yy, "k--"
                    )
                axes[kk].grid("on")
                if kk > 0:
                    axes[kk].set_xticklabels([])
            axes[0].set_xlabel("time [$\mu$s]")
            axes[kk].set_title("non-static waveforms for %s" % self.name)
            plt.draw()
        print("(Figure %d)" % self.label, end=" ")
        print("---")
        # report levels of signals that are commanded, but static
        staticID = np.where(commanded & ~nonstatic)[0]
        for thisID in staticID:
            if thisID in self.signal_by_index:
                thisLabel = self.signal_by_index[thisID]
            else:
                (thisSlot, thisChan, boardname) = self.__get_slot_chan_from_level_index__(
                    thisID
                )
                thisLabel = "%s[%d:%d]" % (boardname, thisSlot, thisChan + 1)
            try:
                thisLevel = level[np.where(keep[:, thisID] == 0)[0][0], thisID]
                print(
                    "  %s %s= %3g" % (thisLabel, " " * (16 - len(thisLabel)), thisLevel)
                )
            except:
                print("error")
        #               Tracer()()
        return
    
    # only used in TimingSegment.plot()
    def __get_slot_chan_from_level_index__(self, levelColumnIndex):
        """given the column index in the level subset (even columns) of the
        UniqueStateArr, return the slot and channel number"""
        global slot
        global __boardTypes__

        signalPartitions = np.cumsum(
            [
                0,
                self.__chan_per_board__["drvr"] * len(slot["drvr"]),  # !driver-speed-keep
                self.__chan_per_board__["lvds"] * len(slot["lvds"]),
                self.__chan_per_board__["htr"] * len(slot["htr"]),
                self.__chan_per_board__["xvbd"] * len(slot["xvbd"]),
                self.__chan_per_board__["adc"] * len(slot["adc"]),
                self.__chan_per_board__["back"] * len(slot["back"]),
                self.__chan_per_board__["hvbd"] * len(slot["hvbd"]),
                self.__chan_per_board__["lvbd"] * len(slot["lvbd"]),
            ]
        )
        bn = np.where(levelColumnIndex >= signalPartitions)[-1]
        boardname = __boardTypes__[bn]
        rawindex = levelColumnIndex - signalPartitions[bn]
        thisChan = np.mod(rawindex, self.__chan_per_board__[boardname])
        thisSlot = self.slot[boardname][rawindex // self.__chan_per_board__[boardname]]
        return thisSlot, thisChan, boardname
        
    def __index_of__(self, Name):  # access Catalog elements by name instead of index
        """returns the Catalog index number of a named time segmentin the waveform"""
        CatalogNames = np.array([obj.name for obj in self.catalog])
        return np.where(CatalogNames == Name)[0][0]