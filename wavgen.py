import numpy as np
import matplotlib.mlab as mlab
import matplotlib.pyplot as plt
import re,sys, os
sys.dont_write_bytecode = True
from IPython.core.debugger import Tracer
from IPython.core.magic import register_line_magic
from timeit import default_timer as timer

# system parameters
period_ns        = 10  # ns
slot = { 'drvr' : [], 
         'lvds' : [], 
         'adc'  : [],
         'back' : [0], 
         'hvbd' : [] }
__boardTypes__     = ('drvr','lvds','adc','back','hvbd')
__chan_per_board__ = { 'drvr' : 2*8, # 2* to take care of level and slew flag
                       'lvds' : 20,
                       'adc'  : 1,
                       'back' : 6,
                       'hvbd' : 30 }
UniqueStateArr   = np.array([]);
Catalog          = {'Name':[],
                    'Time':[],
                    'TimeSegment': [],
                    'Type': []}
Parameters       = {} # all of the parameters
__SignalByName__ = {}
__SignalByIndx__ = {}
__seq_ID__       = 0
__TStypes__      = ('','waveform','sequence')
GenerateFigs     = False # set to True to plot waveforms when loadWDL is called.
__padmax__       = 25 # padding for comments in script

def loadWDL(infile,outfile='/dev/null'):
    """Load a WDL compiled waveform, write ACF state and script files.
Automatically generates plots for non-static signals in waveforms.
Use 'stdout' or sys.stdout to dump to terminal. """
    global slot
    global __chan_per_board__
    global Parameters

    # user command and arguments for feedback
    usercommands = []
    
    #default mod file
    ModFile = '/home/ztf/devel/wdl/test.mod'
    __SignalFile__ = ''

    # read through file to find the mod file
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
                #                Parameters.append(match.group(1))
                pname = match.group(1)
                pval  = int(match.group(2))
                Parameters.update({pname:pval})
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
                                         * mlab.find(np.array(slot[board_type]) == nslot) \
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
    print 'Loading signal mnemonics from %s'%__SignalFile__
    __loadSignals__(__SignalFile__)
    if outfile == '/dev/null': #default condition
        ok = script(outfile)
        state(outfile)
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
        print 'Catalog of timing objects:'
        catalog()
        if len(usercommands) > 0:
            print "Running user-specified commands..."
        for usercmd in usercommands:
            eval('usercmd[0](%s)'%usercmd[1]);
        global GenerateFigs
        if GenerateFigs:
            print 'Generating figures...'
            indxWaveform = mlab.find(np.array(Catalog['Type']) == 'waveform')
            for kk in indxWaveform:
                Catalog['TimeSegment'][kk].plot()
    return

def __loadMod__(ModFile):
    """ load the module definition file to configure global variable slot """
    global __ModFile__
    global slot
    typeID  = {'driver': 'drvr', 'ad': 'adc', 'hvbias': 'hvbd', 'lvds': 'lvds'}
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
                if thisBoardLabel in typeID.keys():
                    thisBoardType = typeID[thisBoardLabel]
                    slot[thisBoardType].append(thisSlotNum)
                else:
                    print "*** Unrecognized board type (%s) in %s"%\
                        (thisBoardLabel,ModFile)
    return
    
def __loadSignals__(__SignalFile__):
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

def __get_level_index_from_chan_slot__(slotnum, channel):
    """ given slot and channel, returns corresponding the level|keep column index """
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
            indx_slot = mlab.find(np.array(slot[boardname]) == slotnum)[0]
            # 3. calculate the base index (boardname index * slot index)
            signalPartitions = np.cumsum([ 0,
                                           __chan_per_board__['drvr'] * len(slot['drvr']), ## !driver-speed-keep
                                           __chan_per_board__['lvds'] * len(slot['lvds']),
                                           __chan_per_board__['adc']  * len(slot['adc']),
                                           __chan_per_board__['back'] * len(slot['back']),
                                           __chan_per_board__['hvbd'] * len(slot['hvbd']) ])
            indx_LVL_boardname = mlab.find(np.array(__boardTypes__) == boardname)[0]
            indx_base = signalPartitions[indx_LVL_boardname] + indx_slot * __chan_per_board__[boardname]
            # 4. add the channel offset
            return (indx_base + channel)

def __get_slot_chan_from_level_index__(levelColumnIndex):
    """given the column index in the level subset (even columns) of the UniqueStateArr,
return the slot and channel number"""
    global slot
    global __boardTypes__

    signalPartitions = np.cumsum([ 0,
                                   __chan_per_board__['drvr'] * len(slot['drvr']), ## !driver-speed-keep
                                   __chan_per_board__['lvds'] * len(slot['lvds']),
                                   __chan_per_board__['adc']  * len(slot['adc']),
                                   __chan_per_board__['back'] * len(slot['back']),
                                   __chan_per_board__['hvbd'] * len(slot['hvbd']) ])
    bin = mlab.find( levelColumnIndex >= signalPartitions )[-1]
    boardname = __boardTypes__[bin]
    rawindex  = levelColumnIndex - signalPartitions[bin]
    thisChan = np.mod(rawindex,__chan_per_board__[boardname])
    thisSlot = slot[boardname][rawindex/__chan_per_board__[boardname]]
    return thisSlot, thisChan, boardname

def __index_of__(Name):
    """ returns the Catalog index number of a named time segment in the waveform """
    global Catalog
    return mlab.find(np.array(Catalog['Name']) == Name)[0]

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
        NotifyTSTypeChange = False
        if TStype not in __TStypes__:
            # TStype must be changed here if invalid, but notification
            # has to wait until self.label is known
            NotifyTSTypeChange = True
            TStype_orig = TStype
            TStype = ''

        if name not in Catalog['Name']: # initialize entry in Catalog
            self.label = __seq_ID__
            __seq_ID__ += 1
            Catalog['Name'].append(name)
            Catalog['Time'].append(np.nan)
            Catalog['TimeSegment'].append(self)
            Catalog['Type'].append(TStype)
        else: # or reinitialize entry in Catalog
            self.label = __index_of__(name)
            Catalog['Time'][self.label] = np.nan
            Catalog['TimeSegment'][self.label] = self
            Catalog['Type'][self.label] = TStype
                                            
        if NotifyTSTypeChange:
            print "invalid TimingSegment type (TStype) specified: %s"%TStype_orig
            print "modifly in <ThisModule>.Catalog['Type'][%d]"%self.label

        # target length of the sequence -- may be exceeded if timing
        # states are defined at t > nperiods
        self.nperiods = nperiods

        self.sequenceDef  = [] # subroutine calls

        # this is meant to replace self.XXXdef except sequenceDef.
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
            levels = np.hstack( (np.array([[0,1]*(len(self.events['drvr'])/2)]),
                                 np.zeros((1,
                                           len(self.events['lvds']) +
                                           len(self.events['adc']) +
                                           len(self.events['back']) +
                                           len(self.events['hvbd']))) ) )
            keeps  = np.ones((1, 
                              len(self.events['drvr']) + ## !driver-speed-keep
                              len(self.events['lvds']) +
                              len(self.events['adc'])  +
                              len(self.events['back']) +
                              len(self.events['hvbd']) ))  
            UniqueStateArr = np.reshape(np.vstack((levels,keeps)), (1,-1), 'F')

        # Default exit state and level (not necessarily consistent!)
        self.ExitState = 0
        self.ExitLevel = UniqueStateArr[0:1,0::2]
        # other defaults
        self.Params = {};

    def __tmax(self,reset=False):
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
        for chan in range(len(self.events['adc'])):
            for tt in range(len(self.events['adc'][chan])):
                tmax = max(tmax, self.events['adc'][chan][tt][0]+1)
        for chan in range(len(self.events['back'])):
            for tt in range(len(self.events['back'][chan])):
                tmax = max(tmax, self.events['back'][chan][tt][0]+1)
        for chan in range(len(self.events['hvbd'])):
            for tt in range(len(self.events['hvbd'][chan])):
                tmax = max(tmax, self.events['hvbd'][chan][tt][0]+1)
        for tt in range(len(self.sequenceDef)):
            tmax = max(tmax,self.sequenceDef[tt][0]+1)
        return tmax

    def __fill_state(self, definition, isDriver=False):
        """ fill level and boolean keep for state definition """

        #############################################################################
        ## this subroutine needs to be fixed in order to compress the state array. ##
        #############################################################################

        n_defs = len(definition)
        level  = np.zeros((self.nperiods, n_defs))
        keep   = np.ones((self.nperiods, n_defs)).astype('bool')

        if isDriver: ## ugh.  for driver, we need to set all the odd
                     ## numbered columns (fast slew switch) to 1
            level[:,1::2] = 1

        for chan in range(n_defs): # loop over channels
            if len(definition[chan]) > 0:   # loop over state entries (time,val)
                for jj in range(len(definition[chan])): # loop over entries
                    tt = definition[chan][jj][0]
                    keep[tt,chan] = False
                    level[tt,chan] = definition[chan][jj][1]
        return level, keep

    def __make_states(self):
        """Make the state array from the event array. In here are the initial
definitions of do_anything_tt, do_anything_dt, unique_state_ID and
__sequence_list__.  Adds new states to UniqueStateArr.

        """

        # enlarge nperiods, if necessary, to encompass all events
        self.nperiods = self.__tmax()

        drvrdef   = self.events['drvr']
        lvdsdef   = self.events['lvds']
        clampdef  = self.events['adc']
        backdef   = self.events['back']
        hvbddef   = self.events['hvbd']

        num_drvr  = len(drvrdef)
        num_lvds  = len(lvdsdef)
        num_clamp = len(clampdef)
        num_back  = len(backdef)
        num_hvbd  = len(hvbddef)

        ## these are all nperiods X nchannel arrays
        drvr_level , drvr_keep  = self.__fill_state(drvrdef,isDriver=True)
        lvds_level , lvds_keep  = self.__fill_state(lvdsdef)
        clamp_level, clamp_keep = self.__fill_state(clampdef)
        back_level , back_keep  = self.__fill_state(backdef)
        hvbd_level , hvbd_keep  = self.__fill_state(hvbddef)

        # fill the sequence array (kept separate from STATEs for now)
        sequence_list = ['']*self.nperiods
        for event in range(len(self.sequenceDef)):
            sequence_list[self.sequenceDef[event][0]] = self.sequenceDef[event][1]

                    
        ### GENERATE THE STATES ###
        # even columns are levels or slew rate switches, odd columns are KEEP flags
        # relative to Archon, i've inserted an extra keep flag for driver to produce a more regular pattern
        #
        # L1a L2a L3a 
        # L1b L2b L3b          L1a K1a L2a K2a L3a K3a
        # L1c L2c L3c ======>  L1b K1b L2b K2b L3b K3b
        # K1a K2a K3a          L1c K1c L2c K2c L3c K3c
        # K1b K2b K3b
        # K1c K2c K3c
        state_arr = np.hstack((np.reshape(np.vstack((drvr_level,drvr_keep)),## !driver-speed-keep 
                                          (self.nperiods, 2*num_drvr), 'F'),## !driver-speed-keep
                               np.reshape(np.vstack((lvds_level ,lvds_keep)) ,
                                          (self.nperiods, 2*num_lvds)  , 'F'),
                               np.reshape(np.vstack((clamp_level,clamp_keep)),
                                          (self.nperiods, 2*num_clamp), 'F'),
                               np.reshape(np.vstack((back_level ,back_keep)) ,
                                          (self.nperiods, 2*num_back)  , 'F'),
                               np.reshape(np.vstack((hvbd_level ,hvbd_keep)) ,
                                          (self.nperiods, 2*num_hvbd)  , 'F')))

        # Find unique states in state_arr and store them in UniqueStateArr
        # UNIQUE_STATE_ID will hold the row in UNIQUE_STATES for each time step
        unique_state_ID = np.zeros((self.nperiods,)).astype('int')
        global UniqueStateArr
        ## this never happens, since USA is set up in __init__
        # if np.size(UniqueStateArr,0) == 0: # empty condition
        # UniqueStateArr = np.array([state_arr[0,:]])
        for tt in range(self.nperiods):
            state_matches_ustate = mlab.find(np.sum(np.abs(state_arr[tt,:] - UniqueStateArr),1) == 0)
            if len(state_matches_ustate) == 0:
                unique_state_ID[tt] = len(UniqueStateArr)
                UniqueStateArr = np.vstack((UniqueStateArr, state_arr[tt,:]))
            elif len(state_matches_ustate) > 1:
                print "problem: state matches multiple unique states"
            else:
                unique_state_ID[tt] = state_matches_ustate[0]

        # identify the time steps where something happens and calculate the time gaps
        do_nothing_state = 0; # by definition in initialization of first TS
        do_something_tt = mlab.find(unique_state_ID != do_nothing_state)
        call_subrtne_tt = mlab.find(np.array(sequence_list) != '')
        do_anything_tt  = np.unique(np.hstack(([0],                # start
                                               do_something_tt,    # states
                                               call_subrtne_tt,    # sub calls
                                               self.nperiods-1 ))) # end
        do_anything_dt  = np.hstack((np.diff(do_anything_tt),[0]))

        # self-ify the keeper variables
        self.do_anything_tt   = do_anything_tt
        self.do_anything_dt   = do_anything_dt
        self.unique_state_ID  = unique_state_ID

        # this one is a bit redundant with sequenceDef, but it saves a
        # lot of index dereferencing in TS.script
        self.__sequence_list__= sequence_list

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

        scriptName = Catalog['Name'][self.label]
        scriptType = Catalog['Type'][self.label]
        SubName = Catalog['Name']

        if scriptName != '':
            outfile.write('%s: # %s\n'%(scriptName,scriptType))
        
        do_anything_tt   = self.do_anything_tt
        do_anything_dt   = self.do_anything_dt
        unique_state_ID  = self.unique_state_ID
        
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
            this_state = unique_state_ID[do_anything_tt[jj]]
            outfile.write("STATE%03d; "%(this_state))
            # over write the exit state if the unique_state_ID is nonzero
            if this_state > 0:
                self.ExitState = this_state
                # until __make_waveform is run, this is the best guess
                # for the exit levels
                self.ExitLevel = UniqueStateArr[this_state:this_state+1,0::2]
            this_sub_call = self.__sequence_list__[do_anything_tt[jj]]
            # true condition means this is a subroutine call, not a state change.
            if (this_sub_call != ''): 
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
                            %(scriptType, scriptName)
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
                    if this_sub_name in Catalog['Name']:
                        this_sub_time = Catalog['Time'][__index_of__(this_sub_name)]
                    else:
                        # if the called subroutine has not been defined in Catalog, then insert a holder
                        global __seq_ID__
                        __seq_ID__ += 1
                        this_sub_time = np.nan
                        Catalog['Name'].append(this_sub_name)
                        Catalog['Time'].append(this_sub_time)
                        Catalog['TimeSegment'].append(None)
                        Catalog['Type'].append('')
                    if this_sub_command.upper() == 'CALL':
                        # only add time if this is not a call to itself (usually RETURN)
                        time += this_sub_time * this_sub_iterations
                        # update the exit state and level with that of the subroutine
                        if  Catalog['TimeSegment'][__index_of__(this_sub_name)].ExitState != 0:
                            self.ExitState = Catalog['TimeSegment'][__index_of__(this_sub_name)].ExitState
                            self.ExitLevel = Catalog['TimeSegment'][__index_of__(this_sub_name)].ExitLevel
            ## END OF SUBROUTINE PARSING
            if (do_anything_tt[jj] == self.nperiods - 1):
                if self.endline == -1:
                    pad -= 7 + len(scriptName)
                    outfile.write("RETURN %s"%(scriptName))
                elif self.endline >= 0 and self.endline < len(SubName):
                    pad -= 6 + len(SubName[self.endline])
                    outfile.write("GOTO %s"%(SubName[self.endline]))
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
                    pad -= np.ceil(np.log10(do_anything_dt[jj]-1)) + 2
                    outfile.write("(%d)"%(do_anything_dt[jj]-1))
            if pad < __padmax__:
                # comment line with the counter, END LINE
                if pad < 1:
                    __padmax__ -= (pad - 1)
                outfile.write("%s# %6d %8.0f\n"%(' '*pad,max(count,0),time))
        Catalog['Time'][self.label] = time
        if outfile.name != '<stdout>': # don't close stdout!
            outfile.close()

        return True

    def __make_waveform(self, initialLevel=[]):
        """ generate a signal-level matrix from the state array """
        global UniqueStateArr
        global Catalog
        state_arr = UniqueStateArr[self.unique_state_ID.astype('int'),:]
        keep  = state_arr[:,1::2].astype('bool')
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
            if self.__sequence_list__[tt] != '':
                match = re.search('(IF\s+(?P<N0>!)?(?P<P0>\w+)(?P<D0>--)?\s+)?'+
                                  '((?P<CMD>RETURN|GOTO|CALL)\s+(?P<TS>\w+)\(?)?'+
                                  '(\(?(?P<P1>\w+)?(?P<D1>--)?)\)?', self.__sequence_list__[tt])
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
                            calledLevel = Catalog['TimeSegment'][TSindx].__make_waveform(this_level)
                            true_level = np.vstack((true_level,calledLevel))
                            this_level = true_level[-1:,:];
                            
                    
#                match = re.search('CALL (\w+)',self.__sequence_list__[tt])
#                if match != None and match.lastindex > 0:
#                    callTSname = match.group(1)
#                    print 'calling %s'%callTSname
#                    callTSlevel = Catalog['TimeSegment'][__index_of__(callTSname)]\
#                        .__make_waveform(initialLevel=this_level)
#                    true_level = np.vstack((true_level,callTSlevel))
#                    
        # chop off the initial condition.
        true_level = true_level[1:,:]
        # update the Exit level
        self.ExitLevel = true_level[-1:,:] # colon after -1 keeps the array 2D
        return true_level
            
    def plot(self, cycles=2, initialLevel=[]):
        """plot the states in the timing script. optionally takes an initial
condition (default=last non-zero state) """

        global Catalog
        if Catalog['Type'][self.label] == 'sequence':
            print 'plt_waves is intended for waveforms. this object is a sequence'
            print 'Warning: results may not make sense.'
        if not hasattr(self,'unique_state_ID'):
            self.__make_states()


        global UniqueStateArr
        state_arr = UniqueStateArr[self.unique_state_ID.astype('int'),:]
        keep  = state_arr[:,1::2].astype('bool')
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

        print "--- %s"%Catalog['Name'][self.label],
        if sum(nonstatic):
        # calculate the slot/channel numbers for the nonstatic traces.
        # drvr, lvds, adc, back, hvbd
            signalID = mlab.find(nonstatic)
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
            axes[kk].set_title('non-static waveforms for %s'%(Catalog['Name'][self.label]))
            plt.draw()
            print '(Figure %d)'%(self.label),
        print '---'
        # report levels of signals that are commanded, but static
        staticID = mlab.find(commanded & ~nonstatic)
        for thisID in staticID:
            if thisID in __SignalByIndx__.keys():
                thisLabel = __SignalByIndx__[thisID]
            else:
                (thisSlot, thisChan, boardname) = __get_slot_chan_from_level_index__(thisID)
                thisLabel = "%s[%d:%d]"%(boardname,thisSlot,thisChan+1)
            try:
                thisLevel = level[mlab.find(keep[:,thisID]==0)[0], thisID]
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
                jj_level = offset + 4*clkchan + 0
                jj_keepL = offset + 4*clkchan + 1
                jj_fast  = offset + 4*clkchan + 2
                jj_keepF = offset + 4*clkchan + 3
                if UniqueStateArr[id,jj_keepL] or UniqueStateArr[id,jj_keepF]:
                    # do not change anything UNLESS level and fast are NOT keep
                    statestring += ",1,1,"
                    if UniqueStateArr[id,jj_keepL] != UniqueStateArr[id,jj_keepF]:
                        # write an error message if keep flags don't agree.
                        if jj_level in __SignalByIndx__.keys():
                            thisSigName = __SignalByIndx__[jj_level/2]
                        else:
                            thisSigName = '%d:%d'%(clkslot,clkchan+1)
                        print "*** WARNING: Driver signal (%s) has inconsistent KEEP flags ***"%thisSigName
                        print "*** check signals or waveform input files for consistency  ***"
                else:
                    statestring += "%g,%d,0,"%(UniqueStateArr[id,jj_level],
                                               int(bool(UniqueStateArr[id,jj_fast])))
                    
            statestring = statestring[:-1] + '"'
            outfile.write(statestring + '\n')
            offset += 2 * __chan_per_board__['drvr'] ## !driver-speed-keep
        for lvdsslot in slot['lvds']:
            outfile.write(prefix + 'MOD%d="'%lvdsslot)
            statestring = ""
            for lvdschan in range(__chan_per_board__['lvds']):
                jj_level= offset + 2*lvdschan + 0
                jj_keep = offset + 2*lvdschan + 1
                if UniqueStateArr[id,jj_keep] == True:
                    statestring += "1,1,"
                else:
                    statestring += "%d,0,"%(UniqueStateArr[id,jj_level])
            statestring = statestring[:-1] + '"'
            outfile.write(statestring + '\n')
            offset += 2 * __chan_per_board__['lvds']
        for adcslot in slot['adc']:
            outfile.write(prefix + 'MOD%d="'%adcslot)
            statestring = ""
            jj_level= offset 
            jj_keep = offset + 1
            if UniqueStateArr[id,jj_keep] == True:
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
            keep  = sum(bin*UniqueStateArr[id,(offset+1):(offset+2*n_back):2])
            outfile.write(prefix + 'CONTROL="%X,%X"\n'%(level,keep))
            offset += 2*n_back
        for hvbdslot in slot['hvbd']: # this is different from the other states,
            # in the acf, there is only one entry and it is
            # (!KEEP, chan, value)
            outfile.write(prefix + 'MOD%d="'%hvbdslot)
            statestring = ""
            n_hvbd_X_2 = 2*__chan_per_board__['hvbd']
            hvbdLevel = UniqueStateArr[id,offset:offset+n_hvbd_X_2:2]
            hvbdKeep  = UniqueStateArr[id,offset+1:offset+n_hvbd_X_2:2]
            # 1. check that there is only one non-keep in hvbdKeep
            KeepSum = sum(hvbdKeep)
            if KeepSum == __chan_per_board__['hvbd']: # nothing changed
                statestring += "0,1,0"                
            elif (KeepSum + 1) == __chan_per_board__['hvbd']: # proper change 
                # 2. get the level corresponding to the non-keep.
                hvbd_chan = mlab.find(hvbdKeep == 0)
                statestring += "1,%d,%g"%(hvbd_chan+1,hvbdLevel[hvbd_chan])
            else: 
                print "Error in HVBD state call -- multiple changes in a state"
            outfile.write(statestring + '"\n')
            offset += n_hvbd_X_2
    outfile.write('STATES=%d\n'%(id+1))

    global Catalog
    global Parameters
    if 'RawPixel' in Catalog['Name'] and 'Pixels' in Parameters.keys():
        RP_label = __index_of__('RawPixel')
        RP_time  = Catalog['Time'][RP_label]
        samples_per_line = Parameters['Pixels'] * RP_time
        rawsamples_per_line = int(np.floor(samples_per_line / 1024.) * 1024)
        rawsamples_per_line = max(rawsamples_per_line, 1024)
        outfile.write('RAWSAMPLES=%d\n'%rawsamples_per_line)
        if samples_per_line != rawsamples_per_line:
            print('Warning: %d samples per line will be skipped'%(samples_per_line-rawsamples_per_line))
    if outfile.name != '<stdout>': # don't close stdout!
        outfile.close()

def script(outfile=sys.stdout, quiet=False):
    """generate ACF scripts and calculates times.  Reports state of
Catalog if a consistent script cannot be generated  """
    global Catalog
    global Parameters
    jj_nocalc = mlab.find(np.isnan(Catalog['Time']))
    N_nocalc  = len(jj_nocalc) # number of segments with uncalculated time
    while N_nocalc > 0:
        for kk in jj_nocalc: # was reversed before
            if Catalog['TimeSegment'][kk] != None:
                Catalog['TimeSegment'][kk].script('/dev/null')
        N_old = N_nocalc
        jj_nocalc = mlab.find(np.isnan(Catalog['Time']))
        N_nocalc  = len(jj_nocalc)
        if N_nocalc == N_old:
            break

    if N_nocalc == 0:
        # remove the existing file before writing to it.
        if type(outfile) == str:
            #os.remove(outfile)
            outfilehandle = open(outfile, 'w')
        else:
            outfilehandle = outfile
        if len(Parameters) > 0:
            outfilehandle.write('[PARAMETER#]\n')
            for param in Parameters.keys():
                outfilehandle.write('%s=%d\n'%(param,Parameters[param]))
        outfilehandle.write('[LINE#]\n')
        if outfilehandle.name != '<stdout>':
            outfilehandle.close();
        for TS in Catalog['TimeSegment']:
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
    for jj in range(len(Catalog['Time'])):
        print "%4d:  %-32s %-8s   %03d %10.2f"%(jj,Catalog['Name'][jj], 
                                                Catalog['Type'][jj],    
                                                Catalog['TimeSegment'][jj].ExitState,
                                                Catalog['Time'][jj]/100.)

# @register_line_magic
def wplot(TimingObjectLabel):
    """ Plot the waveform of the specified sequence """

    global Catalog

    if TimingObjectLabel not in Catalog['Name']:
        print Catalog['Name']
        return

    Catalog['TimeSegment'][__index_of__(TimingObjectLabel)].plot()

    return

#def __in_ipython__():
#    try:
#        __IPYTHON__
#    except NameError:
#        return False
#    else:
#        return True
