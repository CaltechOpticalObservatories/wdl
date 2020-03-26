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
import matplotlib.mlab as mlab
import matplotlib.pyplot as plt
import scipy.sparse as sparse # need 0.18.1
import re,sys, os, collections
from IPython.core.debugger import Tracer
#lfrom IPython.core.magic import register_line_magic
#import time as t

# system parameters
period_ns        = 10  # ns
slot = { 'drvr' : [], 
         'lvds' : [], 
         'htr'  : [], 
         'adc'  : [],
         'back' : [0], 
         'hvbd' : [],
         'lvbd' : [] }
__boardTypes__     = ('drvr','lvds','htr','adc','back','hvbd','lvbd')
__chan_per_board__ = { 'drvr' : 2*8, # 2* to take care of level and slew flag
                       'lvds' : 20,
                       'htr'  : 8,
                       'adc'  : 1,
                       'back' : 6,
                       'hvbd' : 30,
                       'lvbd' : 8+30 } # 8 DIO's + 30 bias (like hvbd)
UniqueStateArr   = np.array([]);
Catalog          = [] # list of all TimingSegment objects
Parameters       = collections.OrderedDict() # all of the parameters
Constants        = collections.OrderedDict() # all of the constants
__SignalByName__ = {}
__SignalByIndx__ = {}
__seq_ID__       = 0
__TStypes__      = ('','waveform','sequence')
GenerateFigs     = False # set to True to plot waveforms when loadWDL is called.
__padmax__       = 25 # padding for comments in script

def loadWDL(infile,outfile='/dev/null',verbose=1):
    """Load a WDL compiled waveform, write ACF state and script files.
Automatically generates plots for non-static signals in waveforms.
Use 'stdout' or sys.stdout to dump to terminal. """
    global slot
    global __chan_per_board__
    global Parameters
    global Constants

    # user command and arguments for feedback
    usercommands = []
    
    #default mod file
    # ModFile = '/home/ztf/devel/python/wdl/test.mod'
    ModFile = '/home/user/wdl/test.mod'
    __SignalFile__ = ''

    # read through file to find the mod file
    infile = os.path.abspath(os.path.expanduser(infile))
    wdl_file_did_not_specify_mod_file = True
    with open(infile,'r') as f:
        for line in f:
            match = re.search('^modulefile\s+([~\w./]+)\s*$',line) # look for mod file
            if match != None:
                ModFile = os.path.abspath(os.path.expanduser(match.group(1)))
                wdl_file_did_not_specify_mod_file = False
                break
    if not os.path.isfile(ModFile):
        print "MOD file specified does not exist (%s)"%ModFile
        print "Using existing slot definitions"
    else:
        if wdl_file_did_not_specify_mod_file:
            print "Using default MOD file: %s"%ModFile
        else:
            if verbose > 0:
                print "Using MOD file: %s"%ModFile
        __loadMod__(ModFile);

    ## global slot is now well defined, read in the file again for WDL content.
    with open(infile,'r') as f:
        for line in f:
            line = re.sub(r'#.*$','',line) # strip comments
            line = re.sub(r'^\s*$','',line) # clear empty lines
            if line == '':
                continue
            match = re.search('^modulefile\s+([~\w./]+)\s*$',line) # look for mod file
            if match != None:
                continue
            match = re.search('^signalfile\s+([~\w./]+)\s*$',line) # look for signal file
            if match != None:
                __SignalFile__ = os.path.abspath(os.path.expanduser(match.group(1)))
                if not os.path.isfile(__SignalFile__):
                    print "Signal file specified does not exist (%s)"%__SignalFile__
                continue
            match = re.search('^parameter\s+(\w+)=(\d+)\s*$',line) # look for parameters
            if match != None:
                pname = match.group(1)
                pval  = int(match.group(2))
                Parameters.update({pname:pval})
                continue
            match = re.search('^constant\s+(\w+)=(\d+)\s*$',line) # look for constants
            if match != None:
                cname = match.group(1)
                cval  = int(match.group(2))
                Constants.update({cname:cval})
                continue
            match = re.search(r'^(sequence|waveform)\s+(\w+)(\.(\w+)\((.*)\))?:\s*$',line) # look for a label
            if match != None:
                # SEQUENCE HEADER:  acf label found, generate sequence object
                TStype  = match.group(1)
                acfLabel = match.group(2)
                pycmd   = match.group(4)
                pyargs  = match.group(5)
                if TStype == 'sequence':
                    thisTS = TimingSegment(acfLabel,TStype)
                    ctr = 0
                elif TStype == 'waveform':
                    thisTS = TimingSegment(acfLabel,TStype,endline=-1)
                else:
                    print 'INVALID TimingSegment type: %s'%TStype
                    print '>> %s'%line
                if pycmd != None:
                    usercommands.append([eval('thisTS.%s'%pycmd),pyargs])
            else: # SEQUENCE BODY: line does not match a code segment label/header
                if TStype == 'sequence':
                    thisTS.sequenceDef.append([ctr,line[:-1]]);
                    ctr += 1
                elif TStype == 'waveform':
                    match = re.search('(\d+)\s+(\d+)\s+(\d+)\s+([+-]?[\d\.]+)',line)
                    if match != None:
                        # body of a waveform
                        time  = int(match.group(1))
                        nslot = int(match.group(2))
                        chan  = int(match.group(3)) # this is the slot channel
                        value = float(match.group(4))
                        # get the key for the slot
                        foundBoardType = False
                        for board_type in slot.keys():
                            if nslot in slot[board_type]:
                                foundBoardType = True
                                if chan >= __chan_per_board__[board_type]:
                                    print '*** INVALID channel (%d) for %s (slot %d) in %s ***'\
                                        %(chan,board_type,nslot,f.name)
                                    continue
                                TSchan = __chan_per_board__[board_type] \
                                         * np.where(np.array(slot[board_type]) == nslot)[0][0] \
                                         + chan
                                # uncomment below to debug waveform read-in
                                # print '%s[%d] <-- (%d,%g)'%(board_type,TSchan,time,value)
                                thisTS.events[board_type][TSchan].append(np.array((time,value)))
                        if not foundBoardType:
                            print "*** [loadWDL error] Board type for slot %s unkown ***"%nslot
                    else:
                        # handle the end line of a waveform.
                        match = re.search('(\d+)\s+(\w+)',line);
                        thisTS.nperiods = int(match.group(1))
                        if thisTS.nperiods == 0:
                            print 'WARNING: nperiods for %s %s is 0'%(TStype,acfLabel)
    if verbose > 0:
        print 'Loading signal mnemonics from %s'%__SignalFile__
    __loadSignals__(__SignalFile__)
    if outfile == '/dev/null': #default condition
        ok = script(outfile)
        state(outfile)
        if verbose > 0:
            print "Specify base file name to generate output, or 'stdout' to print to screen."
    elif outfile == 'stdout' or outfile == sys.stdout:
        ok = script();
        state();
    else:
        ok = script(outfile + '.script');
        if ok:
            print 'Wrote script to %s.script'%outfile
        state(outfile + '.states');
        print 'Wrote states to %s.states'%outfile
    if ok:
        if verbose > 0:
            print 'Catalog of timing objects:'
            catalog()
        if len(usercommands) > 0:
            print "Running user-specified commands..."
        for usercmd in usercommands:
            eval('usercmd[0](%s)'%usercmd[1]);
        global GenerateFigs
        if GenerateFigs:
            print 'Generating figures...'
            tstypes = np.array([obj.tstype for obj in Catalog])
            indxWaveform = np.where(tstypes == 'waveform')[0]
            for kk in indxWaveform:
                Catalog[kk].plot()
    return

def __loadMod__(ModFile): #subroutine of loadWDL()
    """ load the module definition file to configure global variable slot """
    global slot
    typeID  = {'driver': 'drvr', 'ad': 'adc', 'hvbias': 'hvbd', 'lvds': 'lvds', 'heater': 'htr', 'lvbias' : 'lvbd'}
    slotnum = []
    btype   = []
    with open(ModFile,'r') as f:
        for line in f:
            match = re.search('^\s*SLOT\s+(\d+)\s+(\w+)\s{',line)
            if match != None:
                thisSlotNum    = int(match.group(1));
                thisBoardLabel = match.group(2)
                if thisBoardLabel == 'hvxbias':
                    thisBoardLabel = 'hvbias'
                if thisBoardLabel == 'lvxbias':
                    thisBoardLabel = 'lvbias'
                if thisBoardLabel in typeID.keys():
                    thisBoardType = typeID[thisBoardLabel]
                    slot[thisBoardType].append(thisSlotNum)
                else:
                    print "*** Unrecognized board type (%s) in %s"%\
                        (thisBoardLabel,ModFile)
    return
    
def __loadSignals__(__SignalFile__): #subroutine of loadWDL()
    """ load the signals file """
    global __boardTypes__
    global __SignalbyName__
    global __SignalbyIndx__
    
    if not os.path.isfile(__SignalFile__):
        print "Signal file specified does not exist (%s)..."%__SignalFile__
        return False
    with open(__SignalFile__,'r') as f:
        for line in f:
            match = re.search('^#define (\w+)\s+(\d+)\s+:\s+(\d+)',line) # look for signal file
            if match != None:
                signame = match.group(1)
                sigslot = int(match.group(2))
                sigchan = int(match.group(3)) - 1
                if sigslot in slot['drvr']:
                    sigchan *= 2
                LVLindx = __get_level_index_from_chan_slot__(sigslot,sigchan)
                if LVLindx >= 0:
                    __SignalByIndx__.update({LVLindx:signame})
                    __SignalByName__.update({signame:LVLindx})
                    if sigslot in slot['drvr']:
                        FASTindx = LVLindx + 1
                        fastname = signame + '_fast'
                        __SignalByIndx__.update({FASTindx:fastname})
                        __SignalByName__.update({fastname:FASTindx})
                else:
                    print "*** Error in signal file %s ***"%__SignalFile__
    return

def __get_level_index_from_chan_slot__(slotnum, channel): # subroutine of __loadSignals__()
    """ given slot and channel, returns corresponding the level|change column index """
    global slot
    global __boardTypes__
    isDrvr = False
    # 1. determine board type from slot
    for boardname in slot.keys():
        if slotnum in slot[boardname]:
            # 1. check that channel is valid for board type.
            if channel >= __chan_per_board__[boardname]:
                print "*** INVALID channel (%d) specified for slot (%d,%s) ***"%(channel,slotnum,boardname)
                return -1
            # 2. determine index in global slot for board type (0 for the first board of that type, etc)
            indx_slot = np.where(np.array(slot[boardname]) == slotnum)[0][0]
            # 3. calculate the base index (boardname index * slot index)
            signalPartitions = np.cumsum([ 0,
                                           __chan_per_board__['drvr'] * len(slot['drvr']), ## !driver-speed-keep
                                           __chan_per_board__['lvds'] * len(slot['lvds']),
                                           __chan_per_board__['htr']  * len(slot['htr']),
                                           __chan_per_board__['adc']  * len(slot['adc']),
                                           __chan_per_board__['back'] * len(slot['back']),
                                           __chan_per_board__['hvbd'] * len(slot['hvbd']),
                                           __chan_per_board__['lvbd'] * len(slot['lvbd']) ])
            indx_LVL_boardname = np.where(np.array(__boardTypes__) == boardname)[0][0]
            indx_base = signalPartitions[indx_LVL_boardname] + indx_slot * __chan_per_board__[boardname]
            # 4. add the channel offset
            return (indx_base + channel)

def __get_slot_chan_from_level_index__(levelColumnIndex): # only used in TimingSegment.plot()
    """given the column index in the level subset (even columns) of the UniqueStateArr,
return the slot and channel number"""
    global slot
    global __boardTypes__

    signalPartitions = np.cumsum([ 0,
                                   __chan_per_board__['drvr'] * len(slot['drvr']), ## !driver-speed-keep
                                   __chan_per_board__['lvds'] * len(slot['lvds']),
                                   __chan_per_board__['htr']  * len(slot['htr']),
                                   __chan_per_board__['adc']  * len(slot['adc']),
                                   __chan_per_board__['back'] * len(slot['back']),
                                   __chan_per_board__['hvbd'] * len(slot['hvbd']),
                                   __chan_per_board__['lvbd'] * len(slot['lvbd'])  ])
    bin = np.where( levelColumnIndex >= signalPartitions )[-1]
    boardname = __boardTypes__[bin]
    rawindex  = levelColumnIndex - signalPartitions[bin]
    thisChan = np.mod(rawindex,__chan_per_board__[boardname])
    thisSlot = slot[boardname][rawindex/__chan_per_board__[boardname]]
    return thisSlot, thisChan, boardname

def __index_of__(Name): # access Catalog elements by name instead of index
    """ returns the Catalog index number of a named time segment in the waveform """
    global Catalog
    CatalogNames = np.array([obj.name for obj in Catalog])
    return np.where(CatalogNames == Name)[0][0]

class TimingSegment(object):
    """ general timing segment object (waveforms and sequences) to generate ACF states and script"""

    def __init__(self, name='', TStype = '', nperiods=1, endline=-2):
        """initialize state definition arrays. by default nperiods is minimal
and there is no auto-generated end to the segment"""

        # endline defines where to go at the end of this timing segment
        # -2: nothing
        # -1: RETURN name
        # >=0: GOTO SubName[endline] 
        # this is handled at the script-writing stage.
        self.endline = endline

        # provide a unique identifier for this timing segment and
        # catalog its name in the list of subroutines
        global __seq_ID__
        global __TStypes__
        global Catalog
        CatalogNames = [obj.name for obj in Catalog]
        NotifyTSTypeChange = False
        if TStype not in __TStypes__:
            # TStype must be changed here if invalid, but notification
            # has to wait until self.label is known
            NotifyTSTypeChange = True
            TStype_orig = TStype
            TStype = ''

        if name not in CatalogNames: # initialize entry in Catalog
            self.label = __seq_ID__
            __seq_ID__ += 1
            Catalog.append(self)
        else: # or REINITIALIZE entry in Catalog
            self.label = __index_of__(name)
            Catalog[self.label] = self

        self.name   = name
        self.time   = np.nan
        self.tstype = TStype
            
        if NotifyTSTypeChange:
            print "invalid TimingSegment type (TStype) specified: %s"%TStype_orig
            print "modify <ThisModule>.Catalog[%d].tstype"%self.label

        # target length of the sequence -- may be exceeded if timing
        # states are defined at t > nperiods
        self.nperiods = nperiods

        self.sequenceDef  = [] # subroutine calls

        # this is meant to replace self.XXXDef except sequenceDef.
        global __chan_per_board__
        self.events = {}
        for kk in __chan_per_board__.keys():
            self.events.update({kk: []})
            # initialize each type of board with sufficient channels
            for jj in range(len(slot[kk]) * __chan_per_board__[kk]):
                self.events[kk].append([])
        
        # create the do-nothing-state and insert it into UniqueStateArr
        # all levels = 0, all driver speeds = 1, all keeps = 1
        global UniqueStateArr
        if np.size(UniqueStateArr,0) == 0: # empty condition
            levels = np.hstack( (np.array([[0,0]*(len(self.events['drvr'])/2)]),
                                 np.zeros((1,
                                           len(self.events['lvds']) +
                                           len(self.events['htr']) +
                                           len(self.events['adc']) +
                                           len(self.events['back']) +
                                           len(self.events['hvbd']) +
                                           len(self.events['lvbd']) )) ) )
            changes  = np.zeros((1, 
                                 len(self.events['drvr']) + ## !driver-speed-keep
                                 len(self.events['lvds']) +
                                 len(self.events['htr']) +
                                 len(self.events['adc'])  +
                                 len(self.events['back']) +
                                 len(self.events['hvbd']) +
                                 len(self.events['lvbd']) ))  
            UniqueStateArr = np.reshape(np.vstack((levels,changes)), (1,-1), 'F')

        # Default exit state and level (not necessarily consistent!)
        self.ExitState = 0
        self.ExitLevel = UniqueStateArr[0:1,0::2] # :1 keeps it 2D
        # other defaults
        self.Params = {};
        self.Consts = {};

    def __tmax(self,reset=False): # subroutine of __make_states()
        """ determines the number of periods in the timing script """
        if reset:
            tmax = 1
        else:
            tmax = self.nperiods
        for chan in range(len(self.events['drvr'])):
            for tt in range(len(self.events['drvr'][chan])):
                tmax = max(tmax, self.events['drvr'][chan][tt][0]+1)
        for chan in range(len(self.events['lvds'])):
            for tt in range(len(self.events['lvds'][chan])):
                tmax = max(tmax, self.events['lvds'][chan][tt][0]+1)
        for chan in range(len(self.events['htr'])):
            for tt in range(len(self.events['htr'][chan])):
                tmax = max(tmax, self.events['htr'][chan][tt][0]+1)
        for chan in range(len(self.events['adc'])):
            for tt in range(len(self.events['adc'][chan])):
                tmax = max(tmax, self.events['adc'][chan][tt][0]+1)
        for chan in range(len(self.events['back'])):
            for tt in range(len(self.events['back'][chan])):
                tmax = max(tmax, self.events['back'][chan][tt][0]+1)
        for chan in range(len(self.events['hvbd'])):
            for tt in range(len(self.events['hvbd'][chan])):
                tmax = max(tmax, self.events['hvbd'][chan][tt][0]+1)
        for chan in range(len(self.events['lvbd'])):
            for tt in range(len(self.events['lvbd'][chan])):
                tmax = max(tmax, self.events['lvbd'][chan][tt][0]+1)
        for tt in range(len(self.sequenceDef)):
            tmax = max(tmax,self.sequenceDef[tt][0]+1)
        return tmax

    def __fill_state(self, boardtype): # subroutine of __make_states()
        """fill level and boolean change arrays (row sparse format) for state
        definition.  Called in __make_states() for each board type."""

        events = self.events[boardtype]
        n_chan = len(events)

        row = [];
        col = [];
        val = [];
        
        for chan in range(n_chan): # loop over channels
            for jj in range(len(events[chan])): # loop over entries
                time  = events[chan][jj][0]
                if (boardtype == 'drvr') and (np.mod(chan,2) == 1):
                    # 0 <--> 1 for FAST flags
                    level = int(not events[chan][jj][1])
                else:
                    level = events[chan][jj][1]
                
                # level info
                col.append(2*chan);
                row.append(time);
                val.append(level);
                
                # change/keep info
                col.append(2*chan+1);
                row.append(time);
                val.append(1);

        if len(row) > 0:
            # the first bit here is to handle multple entries in the waveform
            # this takes the last value requested.
            rc  = np.array(row) + 1j * np.array(col);
            uniq_j = len(rc) - np.unique(rc[::-1], return_index=True)[1] - 1; # index of last unique element
            val = np.array(val)[uniq_j]; # only arrays can be indexed, not lists????
            row = np.array(row)[uniq_j];
            col = np.array(col)[uniq_j];
            levelchangematrix = sparse.csc_matrix((val, (row,col)), shape=(self.nperiods,2*n_chan))
        else:
            # if the levelchangematrix is all zeros
            levelchangematrix = sparse.csc_matrix((self.nperiods,2*n_chan))

        return levelchangematrix

    def __make_states(self):
        """Make the state array from the event array. In here are the initial
definitions of do_anything_tt, do_anything_dt, unique_state_ID.  Adds
new states to UniqueStateArr.

        """
        # enlarge nperiods, if necessary, to encompass all events
        self.nperiods = self.__tmax()

        ## these are all nperiods X nchannel arrays
        drvr_level_change = self.__fill_state('drvr')
        lvds_level_change = self.__fill_state('lvds')
        htr_level_change  = self.__fill_state('htr')
        adcs_level_change = self.__fill_state('adc')
        back_level_change = self.__fill_state('back')
        hvbd_level_change = self.__fill_state('hvbd')
        lvbd_level_change = self.__fill_state('lvbd')

        # fill the sequence array (kept separate from STATEs for now)
        call_subroutine_tt = []
        for event in range(len(self.sequenceDef)):
            call_subroutine_tt.append(self.sequenceDef[event][0])
                    
        ### GENERATE THE STATES ###
        # even columns are levels or slew rate switches, odd columns are CHANGE flags
        # relative to Archon, i've inserted an extra change flag for driver to produce a more regular pattern
        # 
        #   L1a K1a L2a K2a L3a K3a
        #   L1b K1b L2b K2b L3b K3b
        #   L1c K1c L2c K2c L3c K3c
        #
        state_arr = sparse.hstack( ( drvr_level_change,
                                     lvds_level_change,
                                     htr_level_change,
                                     adcs_level_change,
                                     back_level_change,
                                     hvbd_level_change,
                                     lvbd_level_change ), format='csc')
        
        # Find unique states in state_arr and store them in UniqueStateArr
        # UNIQUE_STATE_ID will hold the row in UNIQUE_STATES for each time step

        # unique_state_ID = np.zeros((self.nperiods,)).astype('int')
        global UniqueStateArr
        (times,chans,datas) = sparse.find(state_arr)
        times = np.unique(times)
        unique_state_IDs = []
        for tt in times:
            state_matches_ustate = np.where(np.sum(np.abs( np.asarray(state_arr.getrow(tt).todense()) - UniqueStateArr ),1) == 0)[0]
            if len(state_matches_ustate) == 0:
                # unique_state_ID[tt] = len(UniqueStateArr)
                unique_state_IDs.append(len(UniqueStateArr))
                UniqueStateArr = np.vstack((UniqueStateArr, state_arr.getrow(tt).toarray() ))
            elif len(state_matches_ustate) > 1:
                print "problem: state matches multiple unique states"
            else:
                # unique_state_ID[tt] = state_matches_ustate[0]
                unique_state_IDs.append(state_matches_ustate[0])

        unique_state_ID = sparse.csc_matrix(( unique_state_IDs,
                                              (np.zeros(np.shape(times)),
                                               times) ), shape=(1,self.nperiods), dtype='int')

        # identify the time steps where something happens and calculate the time gaps
        ## do_nothing_state = 0; # by definition in initialization of first TS
        ## do_something_tt = mlab.find(unique_state_ID != do_nothing_state)
        junk,do_something_tt,more_junk = sparse.find(unique_state_ID)
        do_anything_tt  = np.unique(np.hstack(([0],                # start
                                               do_something_tt,    # states
                                               call_subroutine_tt, # sub calls
                                               self.nperiods-1 ))) # end
        do_anything_dt  = np.hstack((np.diff(do_anything_tt),[0]))
        
        # self-ify the keeper variables
        self.sequence_times   = np.array(call_subroutine_tt).astype('int')
        self.do_anything_tt   = do_anything_tt.astype('int')
        self.do_anything_dt   = do_anything_dt.astype('int')
        self.unique_state_ID  = unique_state_ID

        return
        # end of __make_states

    def script(self, outfile=sys.stdout):
        """Append script to file or file handle, generates new unique states
as needed. Calculate time for time segment to complete, stores the
exit state and the parameters used in Catalog """

        if type(outfile)==str:
            outfile = open(outfile, 'a')

        if not hasattr(self,'unique_state_ID'):
            self.__make_states()
            
        global Catalog
        global Parameters
        global __padmax__

        if self.name != '':
            outfile.write('%s: # %s\n'%(self.name,self.tstype))
        
        do_anything_tt   = self.do_anything_tt
        do_anything_dt   = self.do_anything_dt
        
        count  = -1
        time   = 0
        
        if do_anything_dt[0] < 0:
            print "waveform definition error - event at t=0"
        for jj in range(len(do_anything_dt)):
            pad  = __padmax__ # column to start comment
            EOL = False # end of line flag
            count += 1
            time  += 1
            pad   -= 11
            this_state = self.unique_state_ID[0,do_anything_tt[jj]]
            outfile.write("STATE%03d; "%(this_state))
            # over write the exit state if the unique_state_ID is nonzero
            if this_state > 0:
                self.ExitState = this_state
                # until __make_waveform is run, this is the best guess
                # for the exit levels
                self.ExitLevel = UniqueStateArr[this_state:this_state+1,0::2]

            seq_indx = np.where(self.sequence_times == do_anything_tt[jj])[0]
            if len(seq_indx): # true condition means this is a subroutine call, not a state change.
                this_sub_call = self.sequenceDef[seq_indx[0]][1]
                pad -= len(this_sub_call)
                outfile.write("%s"%(this_sub_call))
                EOL = True
                if this_sub_call[0:3].upper() == 'IF ':
                    # get the first word after IF...
                    regexmatch = re.search('\w+\s+!?([\w]+)',this_sub_call)
                    this_param = regexmatch.group(1)
                    try: # test if this_param is an integer
                        int(this_param)
                    except: # if its not, then its a parameter, so add it to self.Param dict
                        if this_param not in self.Params.keys():
                            if this_param not in Parameters.keys():
                                Parameters.update({this_param:0}) # use 0 as default param value
                            self.Params.update({this_param:Parameters[this_param]})
                if '--' in this_sub_call: # increment count for Param--'s
                    # this assumes that the decrement is not happening in the IF TEST part of a call
                    # is something like IF TEST-- TEST2-- even legal in ACF?
                    count += 1
                    time  += 1
                    this_param = this_sub_call[:-2]  # I'm assuming it's a bare call
                    if this_param not in self.Params.keys():
                        if this_param not in Parameters.keys():
                            Parameters.update({this_param:0}) # use 0 as default param value
                        self.Params.update({this_param:Parameters[this_param]})
                else:
                    # parse the label name and iterations from the sub call
                    # and use that info to calculate the time.
                    regexmatch = re.search(r'([\w]+)\s+([\w]+)(\(([\w]+)\))?$',this_sub_call)
                    if regexmatch == None:
                        print '*** Regular expression could not match wdl input in %s %s. ***'\
                            %(self.tstype, self.name)
                        print "input string: '%s'"%this_sub_call
                    this_sub_command    = regexmatch.group(1)
                    this_sub_name       = regexmatch.group(2)
                    try: # ultimately if it's not an integer, it should be pulled from parameters
                        this_sub_iterations = int(regexmatch.group(4))
                    except:
                        this_sub_iterations = 1
                        if regexmatch.lastindex > 2:
                            this_param = regexmatch.group(4)
                            if this_param not in self.Params.keys():
                                if this_param not in Parameters.keys():
                                    Parameters.update({this_param:0}) # use 0 as default param value
                                self.Params.update({this_param:Parameters[this_param]})
                    SubName = [obj.name for obj in Catalog]
                    if this_sub_name in SubName:
                        this_sub_time = Catalog[__index_of__(this_sub_name)].time
                        ## there may be a cleaner implementation for this_sub_time.
                    else:
                        # if the called subroutine has not been defined in Catalog, then insert a holder
                        # if the inputs are sensible, this code never gets excercised
                        global __seq_ID__
                        this_sub_time = np.nan
                        TimingSegment(this_sub_name) # initialize a timing segment with this name
                        print "boo!"
                    if this_sub_command.upper() == 'CALL':
                        # only add time if this is not a call to itself (usually RETURN)
                        time += this_sub_time * this_sub_iterations
                        # update the exit state and level with that of the subroutine
                        if  Catalog[__index_of__(this_sub_name)].ExitState != 0:
                            self.ExitState = Catalog[__index_of__(this_sub_name)].ExitState
                            self.ExitLevel = Catalog[__index_of__(this_sub_name)].ExitLevel
            ## END OF SUBROUTINE PARSING
            if (do_anything_tt[jj] == self.nperiods - 1):
                if self.endline == -1:
                    pad -= 7 + len(self.name)
                    outfile.write("RETURN %s"%(self.name))
                elif self.endline >= 0 and self.endline < len(Catalog):
                    pad -= 6 + len(Catalog[self.endline].name)
                    outfile.write("GOTO %s"%(Catalog[self.endline].name))#SubName[self.endline]))
                EOL = True
            if (do_anything_dt[jj] > 1) and not EOL:
                # if the time to the next THING is more than 1 period
                # away, then print a DO_NOTHING
                count += do_anything_dt[jj] - 1
                time  += do_anything_dt[jj] - 1
                pad   -= 8
                outfile.write("STATE000") # the do-nothing-state
                if do_anything_dt[jj] > 2:
                    # add the repeat counter if more than 1 are required.
                    pad -= np.ceil(np.log10(do_anything_dt[jj]-1)).astype(int) + 2
                    outfile.write("(%d)"%(do_anything_dt[jj]-1))
            if pad < __padmax__:
                # comment line with the counter, END LINE
                if pad < 1:
                    __padmax__ -= (pad - 1)
                outfile.write("%s# %6d %8.0f\n"%(' '*pad,max(count,0),time))
        self.time = time
        if outfile.name != '<stdout>': # don't close stdout!
            outfile.close()

        return True

    def __make_waveform(self, initialLevel=[]):
        """generate a signal-level matrix from the state array.  called by
        TimingSegment.plot() or by recursion"""
        global UniqueStateArr
        global Catalog
        state_arr = np.atleast_2d(UniqueStateArr[np.squeeze(self.unique_state_ID.toarray()),:]) # should be sparse?
        keep  = np.invert(state_arr[:,1::2].astype('bool'))
        level = state_arr[:,0::2]

        if initialLevel == []:
            initialLevel = self.ExitLevel

        ##true level should be generated incrementally with  calls to subs.
        true_level = initialLevel
        this_level = np.zeros(np.shape(true_level))
        for tt in range(self.nperiods):
            this_level[0, keep[tt,:]] = true_level[-1, keep[tt,:]] # keep
            this_level[0,~keep[tt,:]] =      level[tt,~keep[tt,:]] # get new values
            true_level = np.vstack((true_level,this_level))

            seq_indx = np.where(self.sequence_times == tt)[0]
            if len(seq_indx): # true condition means this is a subroutine call, not a state change.
                this_sub_call = self.sequenceDef[seq_indx[0]][1]
                match = re.search('(IF\s+(?P<N0>!)?(?P<P0>\w+)(?P<D0>--)?\s+)?'+
                                  '((?P<CMD>RETURN|GOTO|CALL)\s+(?P<TS>\w+)\(?)?'+
                                  '(\(?(?P<P1>\w+)?(?P<D1>--)?)\)?', this_sub_call)
                ## REGEX labels:
                #  N0: negation of IF test (!)
                #  P0: IF test parameter 
                #  D0: decrement of test parameter (--)
                #  CMD: branching command (RETURN, GOTO or CALL)
                #  TS: Time segment to call
                #  P1: Parameter
                #  D1: Parameter decrement (--)
                runcmd = True
                if match.group('P0') != None:
                    runcmd = self.Params[match.group('P0')]
                    if match.group('N0') == '!':
                        runcmd = not runcmd
                    if (match.group('D0') == '--' and #decrement P0
                        self.Params[match.group('P0')] > 0):
                        self.Params[match.group('P0')] -= 1
                if runcmd:
                    if match.group('P1') != None:
                        if match.group('P1').isdigit():
                            repeats = int(match.group('P1'))
                        else:
                            repeats = self.Params[match.group('P1')]
                    else:
                        repeats = 1
                    if (match.group('D1') == '--' and  #decrement P0
                        self.Params[match.group('P1')] > 0):
                        self.Params[match.group('P1')] -= 1
                    if match.group('CMD') == 'CALL' and match.group('TS') != None:
                        print 'calling %s'%match.group('TS')
                        TSindx  = __index_of__(match.group('TS'))
                        for jj in range(repeats):
                            calledLevel = Catalog[TSindx].__make_waveform(this_level)
                            true_level = np.vstack((true_level,calledLevel))
                            this_level = true_level[-1:,:];

        # chop off the initial condition.
        true_level = true_level[1:,:]
        # update the Exit level
        self.ExitLevel = true_level[-1:,:] # colon after -1 keeps the array 2D
        return true_level
            
    def plot(self, cycles=2, initialLevel=[]):
        """plot the states in the timing script. optionally takes an initial
condition (default=last non-zero state) """

        global Catalog

        if self.tstype == 'sequence':
            print 'plt_waves is intended for waveforms. this object is a sequence'
            print 'Warning: results may not make sense.'
        if not hasattr(self,'unique_state_ID'):
            self.__make_states()

        global UniqueStateArr
        state_arr = np.atleast_2d(UniqueStateArr[np.squeeze(self.unique_state_ID.toarray()),:])
        keep  = np.invert(state_arr[:,1::2].astype('bool'))
        level = state_arr[:,0::2]

        if initialLevel == []:
            initialLevel = self.ExitLevel
        true_level = np.zeros((0,np.shape(level)[1])); # 0xN empty array
        for jj in range(cycles):
            true_level = np.vstack((true_level, self.__make_waveform(initialLevel)))
            initialLevel = self.ExitLevel

        # find the static channels
        nonstatic = np.amax(true_level,0) != np.amin(true_level,0)
        # find the commanded channels
        commanded = np.amin(keep, 0) == 0

        print "--- %s"%self.name,

        if sum(nonstatic):
        # calculate the slot/channel numbers for the nonstatic traces.
        # drvr, lvds, adc, back, hvbd, lvbd
            signalID = np.where(nonstatic)[0]
            nsignals = len(signalID)

            fig = plt.figure(self.label)
            plt.clf();
            figXLeft = 0.15
            figYBtm = 0.1
            figYTop = 0.06
            gap     = 0.02
            vspace  = (1 - figYBtm - figYTop)/nsignals
            vgap    = vspace * gap / 2
            axes = []
            for kk in range(nsignals):
                thisSigID = signalID[nsignals - kk - 1]
                (thisSlot, thisChan, boardname) = __get_slot_chan_from_level_index__(thisSigID)
                if thisSigID in __SignalByIndx__.keys():
                    thisSigLabel = __SignalByIndx__[thisSigID]
                else:
                    thisSigLabel = '???'
                # left, bottom, width, height (range 0 to 1)
                axes.append(fig.add_axes([figXLeft, figYBtm + kk*vspace + vgap,
                                          0.97 - figXLeft, vspace*(1-gap)]))
                global period_ns
                period_us = period_ns / 1000.
                time = np.arange(np.shape(true_level)[0]) * period_us
                axes[kk].plot(time,true_level[:,thisSigID])
                axes[kk].set_ylabel('%s\n%s\n(%d,%d)'%(boardname,thisSigLabel,thisSlot,thisChan+1))
                yy = axes[kk].set_ylim()
                dy = np.diff(yy)
                yy = axes[kk].set_ylim((yy[0] - .1*dy, yy[1] + .1*dy))
                for nn in range(cycles):
                    axes[kk].plot([len(time)/cycles * period_us * (nn+1)]*2, yy,'k--')
                axes[kk].grid('on')
                if kk > 0:
                    axes[kk].set_xticklabels([])
            axes[0].set_xlabel('time [$\mu$s]');
            axes[kk].set_title('non-static waveforms for %s'%self.name)
            plt.draw()
            print '(Figure %d)'%(self.label),
        print '---'
        # report levels of signals that are commanded, but static
        staticID = np.where(commanded & ~nonstatic)[0]
        for thisID in staticID:
            if thisID in __SignalByIndx__.keys():
                thisLabel = __SignalByIndx__[thisID]
            else:
                (thisSlot, thisChan, boardname) = __get_slot_chan_from_level_index__(thisID)
                thisLabel = "%s[%d:%d]"%(boardname,thisSlot,thisChan+1)
            try:
                thisLevel = level[np.where(keep[:,thisID]==0)[0][0], thisID]
                print "  %s %s= %3g"%(thisLabel,' '*(16-len(thisLabel)),thisLevel)
            except:
                Tracer()()
        return

def state(outfile=sys.stdout):
    """ write states from the UniqueStateArr to the file or file handle specified """
    global UniqueStateArr
    global __chan_per_board__

    if type(outfile)==str:
        outfile = open(outfile, 'w')

    # write the script to /dev/null before writing states.
    script('/dev/null',quiet=True)

    outfile.write('[CONFIG]\n')
    for id in range(np.size(UniqueStateArr,0)):
        prefix = "STATE%d\\"%id  ## take out 2 \\'s if we don't need the double \
        outfile.write(prefix + "NAME=STATE%03d\n"%id)
        offset=0 # to keep track of position in array
        for clkslot in slot['drvr']:
            outfile.write(prefix + 'MOD%d="'%clkslot)
            statestring = ""
            for clkchan in range(__chan_per_board__['drvr']/2):## driver-speed-keep !!!!!
                jj_level   = offset + 4*clkchan + 0
                jj_changeL = offset + 4*clkchan + 1
                jj_fast    = offset + 4*clkchan + 2
                jj_changeF = offset + 4*clkchan + 3
                if not(UniqueStateArr[id,jj_changeL] and UniqueStateArr[id,jj_changeF]):
                    # do not change anything UNLESS level and fast are both CHANGE
                    # this branch keeps everything the same.
                    statestring += ",1,1,"
                    if UniqueStateArr[id,jj_changeL] != UniqueStateArr[id,jj_changeF]:
                        # write an error message if change flags don't agree.
                        if jj_level/2 in __SignalByIndx__.keys():
                            thisSigName = __SignalByIndx__[jj_level/2]
                        else:
                            thisSigName = '%d:%d'%(clkslot,clkchan+1)
                        print "*** WARNING: Driver signal (%s) has inconsistent KEEP flags ***"%thisSigName
                        print "*** check signals or waveform input files for consistency  ***"
                        print "*** For clock waveforms, 'FAST' or 'SLOW' needs to be specified ***"
                else:
                    # in USA, 0==FAST 1==SLOW.  IN ACF, 1==FAST, 0==SLOW.
                    statestring += "%g,%d,0,"%(UniqueStateArr[id,jj_level],
                                               int(not bool(UniqueStateArr[id,jj_fast])))
                    
            statestring = statestring[:-1] + '"'
            outfile.write(statestring + '\n')
            offset += 2 * __chan_per_board__['drvr'] ## !driver-speed-keep
        for lvdsslot in slot['lvds']:
            outfile.write(prefix + 'MOD%d="'%lvdsslot)
            statestring = ""
            for lvdschan in range(__chan_per_board__['lvds']):
                jj_level  = offset + 2*lvdschan + 0
                jj_change = offset + 2*lvdschan + 1
                if UniqueStateArr[id,jj_change] == False:
                    statestring += "1,1,"
                else:
                    statestring += "%d,0,"%(UniqueStateArr[id,jj_level])
            statestring = statestring[:-1] + '"'
            outfile.write(statestring + '\n')
            offset += 2 * __chan_per_board__['lvds']
        for htrslot in slot['htr']:
            outfile.write(prefix + 'MOD%d="'%htrslot)
            statestring = ""
            for htrchan in range(__chan_per_board__['htr']):
                jj_level  = offset + 2*htrchan + 0
                jj_change = offset + 2*htrchan + 1
                if UniqueStateArr[id,jj_change] == False:
                    statestring += "1,1,"
                else:
                    statestring += "%d,0,"%(UniqueStateArr[id,jj_level])
            statestring = statestring[:-1] + '"'
            outfile.write(statestring + '\n')
            offset += 2 * __chan_per_board__['htr']
        for adcslot in slot['adc']:
            outfile.write(prefix + 'MOD%d="'%adcslot)
            statestring = ""
            jj_level  = offset 
            jj_change = offset + 1
            if UniqueStateArr[id,jj_change] == False:
                statestring += "0,1,"
            else:
                statestring += "%d,0,"%(UniqueStateArr[id,jj_level])
            statestring = statestring[:-1] + '"'
            outfile.write(statestring + '\n')
            offset += 2
        if True: # Backplane
            n_back = __chan_per_board__['back']    
            bin = 2**np.arange(0,n_back) # to convert backplane states to hex
            level = sum(bin*UniqueStateArr[id,(offset+0):(offset+2*n_back):2])
            keep  = sum(bin*(np.invert(UniqueStateArr[id,(offset+1):(offset+2*n_back):2].astype('bool')).astype('int')))
            outfile.write(prefix + 'CONTROL="%X,%X"\n'%(level,keep))
            offset += 2*n_back
        for hvbdslot in slot['hvbd']: # this is different from the other states,
            # in the acf, there is only one entry and it is
            # (!KEEP, chan, value)
            outfile.write(prefix + 'MOD%d="'%hvbdslot)
            statestring = ""
            n_hvbd_X_2 = 2*__chan_per_board__['hvbd']
            hvbdLevel = UniqueStateArr[id,offset:offset+n_hvbd_X_2:2]
            hvbdKeep  = np.invert(UniqueStateArr[id,offset+1:offset+n_hvbd_X_2:2].astype('bool')).astype('int')
            # 1. check that there is only one non-keep in hvbdKeep
            KeepSum = sum(hvbdKeep)
            if KeepSum == __chan_per_board__['hvbd']: # nothing changed
                statestring += "0,1,0"                
            elif (KeepSum + 1) == __chan_per_board__['hvbd']: # proper change 
                # 2. get the level corresponding to the non-keep.
                hvbd_chan = np.where(hvbdKeep == 0)[0]
                statestring += "1,%d,%g"%(hvbd_chan+1,hvbdLevel[hvbd_chan])
            else: 
                print "Error in HVBD state call -- multiple changes in a state"
            outfile.write(statestring + '"\n')
            offset += n_hvbd_X_2
        for lvbdslot in slot['lvbd']:
            # this is an ugly amalgamation of lvds and hvbd...
            outfile.write(prefix + 'MOD%d="'%lvbdslot)
            statestring = ""
            n_LVBIAS = 30
            # the "-30" in the for loop below is to exclude the 30 bias channels
            for lvbdchan in range(__chan_per_board__['lvbd'] - n_LVBIAS):
                jj_level  = offset + 2*lvbdchan + 0
                jj_change = offset + 2*lvbdchan + 1
                if UniqueStateArr[id,jj_change] == False:
                    statestring += "1,1,"
                else:
                    statestring += "%d,0,"%(UniqueStateArr[id,jj_level])
            offset += 2*(__chan_per_board__['lvbd'] - n_LVBIAS) # move the offset past the 8 DIO's
            # now for the "HVBD"-style part of this board
            n_lvbd_X_2 = 2*n_LVBIAS
            lvbdLevel = UniqueStateArr[id,offset:offset+n_lvbd_X_2:2]
            lvbdKeep  = np.invert(UniqueStateArr[id,offset+1:offset+n_lvbd_X_2:2].astype('bool')).astype('int')
            # 1. check that there is only one non-keep in lvbdKeep
            KeepSum = sum(lvbdKeep)
            if KeepSum == __chan_per_board__['lvbd']: # nothing changed
                statestring += "0,1,0"
            elif (KeepSum + 1) == __chan_per_board__['lvbd']: # proper change
                # 2. get the level corresponding to the non-keep.
                lvbd_chan = np.where(lvbdKeep == 0)[0]
                statestring += "1,%d,%g"%(lvbd_chan+1,lvbdLevel[lvbd_chan])
            else:
                print "Error in LVBD state call -- multiple changes in a state"
            outfile.write(statestring + '\n')
            offset += n_lvbd_X_2

    outfile.write('STATES=%d\n'%(id+1))

    global Catalog
    global Parameters
    CatalogNames = [obj.name for obj in Catalog]
    # easter egg activated by existence of a sequence or waveform named 'RawPixel'.  Parameter
    # 'Pixels' and the wdl-calculated clocks for 'RawPixel' determines the maximum safe number of
    # raw samples to take on a line (the largest multiple of 1024 samples).
    #
    # Note that the Parameters 'Pixels' and 'Lines' determine the action of the ACF loop, whereas
    # the ACF keywords 'LINECOUNT' and 'PIXELCOUNT' determine the size of the cds image.
    # Generally, they are the same, but the keyword values can be smaller than the parameter
    # values.
    #
    # In specifying the raw data section, everything counts from 0, except for the number of
    # RAWSAMPLES.  In specifying the CDS image or the loop, the values count from 1.
    #
    # The number of RAWSAMPLES is maximized UNLESS the ACF keyword 'RAWENDLINE' is greater than the
    # Parameter 'Lines' - 1.
    #
    # This easter egg may be abandoned in favor of a post-processing script that looks at the ACF
    # and the WDL files and adjusts the ACF accordingly.
    ###
    # if 'RawPixel' in CatalogNames and 'Pixels' in Parameters.keys():
    #     RP_label = __index_of__('RawPixel')
    #     RP_time  = Catalog[RP_label].time
    #     samples_per_line = Parameters['Pixels'] * RP_time
    #     rawsamples_per_line = int(np.floor(samples_per_line / 1024.) * 1024)
    #     rawsamples_per_line = max(rawsamples_per_line, 1024)
    #     outfile.write('RAWSAMPLES=%d\n'%rawsamples_per_line)
    #     if samples_per_line != rawsamples_per_line:
    #         print('Warning: %d samples per line will be skipped'%(samples_per_line-rawsamples_per_line))
    #     if 'Lines' in Parameters.keys():
    #         cds_size = Parameters['Pixels']*Parameters['Lines']*4**3;
    #         rawspace = 768*2**20 - cds_size;
    #         maxrawlines = rawspace/(rawsamples_per_line*2);
    #         if maxrawlines < Parameters['Lines'] and maxrawlines > 0:
    #             outfile.write('RAWENDLINE=%d\n'%(maxrawlines-1));
    if outfile.name != '<stdout>': # don't close stdout!
        outfile.close()

def script(outfile=sys.stdout, quiet=False):
    """generate ACF scripts and calculates times.  Reports state of
Catalog if a consistent script cannot be generated  """
    global Catalog
    global Parameters
    global Constants

    jj_nocalc = np.where(np.isnan([obj.time for obj in Catalog]))[0]
    N_nocalc  = len(jj_nocalc) # number of segments with uncalculated time
    while N_nocalc > 0:
        for kk in jj_nocalc: # was reversed before
            if Catalog[kk] != None:
                Catalog[kk].script('/dev/null')
        N_old = N_nocalc
        jj_nocalc = np.where(np.isnan([obj.time for obj in Catalog]))[0]
        N_nocalc  = len(jj_nocalc)
        if N_nocalc == N_old:
            break

    if N_nocalc == 0:
        # remove the existing file before writing to it.
        if type(outfile) == str:
            outfilehandle = open(outfile, 'w')
        else:
            outfilehandle = outfile
        if len(Parameters) > 0:
            outfilehandle.write('[PARAMETER#]\n')
            for param in Parameters.keys():
                outfilehandle.write('%s=%d\n'%(param,Parameters[param]))
        if len(Constants) > 0:
            outfilehandle.write('[CONSTANT#]\n')
            for const in Constants.keys():
                outfilehandle.write('%s=%d\n'%(const,Constants[const]))
        outfilehandle.write('[LINE#]\n')
        if outfilehandle.name != '<stdout>':
            outfilehandle.close();
        for TS in Catalog:
            TS.script(outfile)
    elif not quiet:
        print "Timing did not converge:"
        catalog()
        print "No script output due to undefined sequence or waveform."
        return False

    return True
        
# @register_line_magic
def catalog(MagicNullArgument=None):
    """ print catalog in human readable form """
    global Catalog
    print "index  label                                type  exit  time [us]"
    print "-----------------------------------------------------------------"
    for jj in range(len(Catalog)):
        print "%4d:  %-32s %-8s   %03d %10.2f"%(jj,
                                                Catalog[jj].name, 
                                                Catalog[jj].tstype,
                                                Catalog[jj].ExitState,
                                                Catalog[jj].time/100.)

# @register_line_magic
def wplot(TimingObjectLabel):
    """ Plot the waveform of the specified sequence """

    global Catalog
    CatalogNames = [obj.name for obj in Catalog]
    if TimingObjectLabel not in CatalogNames:
        print CatalogNames
        return

    Catalog[__index_of__(TimingObjectLabel)].plot()

    return

class modegen():
    """ Process the modes file.  This must happen AFTER the ACF has been made """

    def __init__(self, modefile, acffile):

        self.__OK2write = True

        self.modefile = os.path.expanduser(modefile)
        self.acffile = os.path.expanduser(acffile)

        if not os.path.isfile(self.modefile):
            print "MODE FILE NOT FOUND: %s"%self.modefile
            return False
        if not os.path.isfile(self.acffile):
            print "ACF FILE NOT FOUND: %s"%self.acffile
            return False
        
        self.modeKVpair = {} # dict of mode KEY=VALUE pairs
        self.union      = {} # the union of mode keys
        self.modelist   = {} # dict of non-KEY=VALUE mode statements (not propagated)
        self.taplines   = {} # dict of taplines by mode

        self.__read_inputfile()
        self.__assign_defaults_from_acf()
        self.__index_modeKVpair()

        # # print error messages for keys in union that are not declared in all non-default modes
        # nondefault = self.modeKVpair.copy()
        # nondefault.pop('MODE_DEFAULT')
        # for key in self.union.keys():
        #     if self.union[key] == None:
        #         if not all([key in nondefault[mode] for mode in nondefault.keys()]) :
        #             print "WARNING: '%s' is undefined for some modes."%key

        # print error messages for keys in union that are not declared the default mode
        for key in self.union.keys():
            if self.union[key] == None:
                print "WARNING: '%s' needs to be defined in MODE_DEFAULT."%key
                self.__OK2write = False

    def __read_inputfile(self):
        """ read the input file """
        with open(self.modefile) as FILE:
            for line in FILE:
                # look for headers
                match = re.search('^\[(.*?)\]',line)
                if match:
                    self.modeKVpair.update({match.group(1):{}}) # initialize the KVpair entry
                    self.modelist.update({match.group(1):[]}) # init the nonKV list
                    thismode = match.group(1)
                else:
                    # look for key=value pairs, matching the LAST = on the line
                    match = re.search('^(.+:.+)\s*=\s*(.+?)\n',line)
                    if match:
                        # union will hold one of every key specified
                        self.union.update({match.group(1):None})
                        # modes only hold specified key=value pairs
                        self.modeKVpair[thismode].update({match.group(1):match.group(2)})
                        # if the key is a non-empty TAPLINE setting, then increment self.taplines[thismode]
                        if re.search('ACF:TAPLINE\d+="[\w,]+"',line):
                            if thismode not in self.taplines.keys():
                                self.taplines.update({thismode:1})
                            else:
                                self.taplines[thismode] += 1
                        continue
                    # look for non key=value statements
                    match = re.search('^(.+:[^=]+)\n',line)
                    if match:
                        self.modelist[thismode].append(match.group(1))
                        continue
                    # both matches failed - issue warning
                    if re.search('[^\w]+',line[:-1]):
                        print "WARNING: '%s' in %s not recognized as a mode-setting statement"%(line[:-1],thismode)
        ## add calculated TAPLINES to each mode for which at least one TAPLINE# is set
        for mode in self.taplines.keys():
            self.modeKVpair[mode].update({'ACF:TAPLINES':self.taplines[mode]})
            self.union.update({'ACF:TAPLINES':None}) # initialize the union dict
            
    def __assign_defaults_from_acf(self):
        """ populate self.union with values from the acf file """

        allkeys = np.sort(self.union.keys())
        with open(self.acffile) as ACF:
            for line in ACF:
                # skip [MODE_X] statments
                if re.search('^\w+:\w',line):
                    continue
                # look for key=value pairs in ACF
                match = re.search('^(.+)=(.+?)\n',line)
                if match:
                    ACFKEY = 'ACF:'+match.group(1)
                    ACFVAL = match.group(2)
                    if ACFKEY in allkeys:
                        self.union[ACFKEY] = ACFVAL
                    else:
                        # Parse the '%d' that typically shows up in 'ACF:PARAMETER'-keys
                        for unionkey in allkeys: # do the reverse check
                            if re.search('%d',unionkey):
                                # make regex from printf %d ONLY IF it appears in the key
                                unionregex = re.sub('%d','(\d+)',unionkey)
                                kmatch = re.search(unionregex,ACFKEY)
                                if kmatch:
                                    try:
                                        newkey = unionkey%int(kmatch.group(1))
                                    except:
                                        Tracer()()
                                    self.union.update({newkey:ACFVAL})
                                    # default for unionkey is set now with
                                    # the proper index, so we can now
                                    # discard unionkey
                                    self.union.pop(unionkey)
                                    break

        # the DEFAULT MODE in the input is special -- it assigns non ACF defaults to the union
        TheDefaultMode = self.modeKVpair['MODE_DEFAULT']
        baddefault = False # flag for bad default setting warning
        for key in TheDefaultMode:
            match = re.search('^ACF:',key) 
            if not match: # any key that isn't an ACF key
                self.union[key] = TheDefaultMode[key]
            else:
                print "WARNING: '%s' declared in MODE_DEFAULT does not propagate to other modes."%key
                baddefault = True
        if baddefault:
            print "**NOTE** 'ACF:'-type keys use default values from %s"%self.acffile
                
                
    def __index_modeKVpair(self):
        """ convert (\d+)'s into proper ACF indices """
        allkeys = np.sort(self.union.keys())
        for mode in self.modeKVpair:
            for key in self.modeKVpair[mode]:
                match = re.search('^ACF:.+?%d=(.+)', key) # search the "ACF:" keys for "%d="
                # NOTE: the above regex wont work for keys that do not
                # have a "=" in them, ie, this will not work for LINE
                # or MOD ACF statements, as they would not be unique
                if match:
                    # now figure out which key in self.union this corresponds to
                    keyregex = re.sub('%d','(\d+)',key)
                    for ukey in self.union:
                        kmatch = re.search(keyregex, ukey)
                        if kmatch:
                            newkey = key%int(kmatch.group(1))
                            self.modeKVpair[mode].update({newkey:self.modeKVpair[mode].pop(key)})
                            break
        
    def write(self,append=None):
        """ write the mode sections to standard out """
        if not self.__OK2write:
            print "** Something is wrong -- check error messages from initialization."
            if append:
                print "WARNING: no modes written to %s."%self.acffile
            return False

        allkeys = np.sort(self.union.keys())

        if append:
            sys.stdout = open(self.acffile,'a')
        
        for mode in self.modeKVpair:
            # loop over all modes declared
            print "[%s]"%mode
            modekeys = self.modeKVpair[mode].keys()
            # first, print the K=V entries for this mode.
            for key in allkeys:
                if key in modekeys:
                    print "%s=%s"%(key,self.modeKVpair[mode][key])
                else:
                    print "%s=%s"%(key,self.union[key])
            # print the non K=V entries for this mode.
            for line in self.modelist[mode]:
                print line
            # propagate any non K=V in MODE_DEFAULT with neither thought or regard
            if mode != 'MODE_DEFAULT':
                for line in self.modelist['MODE_DEFAULT']:
                    print line
        if append:
            sys.stdout.close()
            sys.stdout = sys.__stdout__
            print "Modes appended to %s"%self.acffile

    ## the grep function here needs PHM.acf.wdl()
    # def grep(self, regex):
    #     """ scour the wdl input files for keys used in modes """
    #     for wdlinput in self.wdl.inputfiles:
    #         with open(wdlinput) as WDLINPUT:
    #             for text in WDLINPUT:
    #                 match = re.search("(^|[^\w])%s[^\w]"%regex, text)
    #                 if match:
    #                     match2 = re.search('(\w+)=(.*)',text[:-1])
    #                     self.wdl.grep(match2.group(2))

#def __in_ipython__():
#    try:
#        __IPYTHON__
#    except NameError:
#        return False
#    else:
#        return True
