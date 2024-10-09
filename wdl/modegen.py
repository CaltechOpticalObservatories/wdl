import os
import re
import numpy as np
import sys

class Modegen:
    """Process the modes file after the ACF has been made."""

    def __init__(self, modefile, acffile):

        self.__OK2write = True

        self.modefile = os.path.expanduser(modefile)
        self.acffile = os.path.expanduser(acffile)

        if not os.path.isfile(self.modefile):
            print("MODE FILE NOT FOUND: %s" % self.modefile)
        if not os.path.isfile(self.acffile):
            print("ACF FILE NOT FOUND: %s" % self.acffile)

        self.modeKVpair = {}  # mode KEY=VALUE pairs
        self.union = {}  # the union of mode keys
        self.modelist = {}  # non-KEY=VALUE mode statements (not propagated)
        self.taplines = {}  # taplines by mode

        self.__read_inputfile()
        self.__assign_defaults_from_acf()
        self.__index_modeKVpair()

        # print error messages for keys in union that are not declared in
        # all non-default modes
        # nondefault = self.modeKVpair.copy()
        # nondefault.pop('MODE_DEFAULT')
        # for key in self.union:
        #     if self.union[key] == None:
        #         if not all([key in nondefault[mode] for mode in nondefault]) :
        #             print("WARNING: '%s' is undefined for some modes."%key)

        # print error messages for keys in union that are not
        # declared the default mode
        for key in self.union:
            if self.union[key] is None:
                print("WARNING: '%s' needs to be defined in MODE_DEFAULT." % key)
                self.__OK2write = False

    def __read_inputfile(self):
        """read the input file"""
        with open(self.modefile) as FILE:
            for line in FILE:
                # look for headers
                match = re.search(r"^\[(.*?)\]", line)
                if match:
                    # initialize the KVpair entry
                    self.modeKVpair.update({match.group(1): {}})
                    # init the nonKV list
                    self.modelist.update({match.group(1): []})
                    thismode = match.group(1)
                else:
                    # look for key=value pairs, matching the LAST = on the line
                    match = re.search(r"^(.+:.+)\s*=\s*(.+?)\n", line)
                    if match:
                        # union will hold one of every key specified
                        self.union.update({match.group(1): None})
                        # modes only hold specified key=value pairs
                        self.modeKVpair[thismode].update(
                            {match.group(1): match.group(2)}
                        )
                        # if the key is a non-empty TAPLINE setting,
                        # then increment self.taplines[thismode]
                        if re.search(r'ACF:TAPLINE\d+="[\w,]+"', line):
                            if thismode not in self.taplines:
                                self.taplines.update({thismode: 1})
                            else:
                                self.taplines[thismode] += 1
                        continue
                    # look for non key=value statements
                    match = re.search(r"^(.+:[^=]+)\n", line)
                    if match:
                        self.modelist[thismode].append(match.group(1))
                        continue
                    # both matches failed - issue warning
                    if re.search(r"[^\w]+", line[:-1]):
                        print(
                            "WARNING: '%s' in %s not recognized as a "
                            "mode-setting statement" % (line[:-1], thismode)
                        )
        # add calculated TAPLINES to each mode
        # for which at least one TAPLINE# is set
        for mode in self.taplines:
            self.modeKVpair[mode].update({"ACF:TAPLINES": self.taplines[mode]})
            # initialize the union dict
            self.union.update({"ACF:TAPLINES": None})

    def __assign_defaults_from_acf(self):
        """populate self.union with values from the acf file"""

        allkeys = np.sort(list(self.union))
        with open(self.acffile) as ACF:
            for line in ACF:
                # skip [MODE_X] statments
                if re.search(r"^\w+:\w", line):
                    continue
                # look for key=value pairs in ACF
                match = re.search(r"^(.+)=(.+?)\n", line)
                if match:
                    ACFKEY = "ACF:" + match.group(1)
                    ACFVAL = match.group(2)
                    temp = ACFKEY.split('"')
                    if re.search(r"PARAMETER", temp[0]):
                        ACFKEY = "ACF:" + temp[-1]

                    if ACFKEY in allkeys:
                        self.union[ACFKEY] = ACFVAL
                    else:
                        # Parse the '%d' that typically shows up
                        # in 'ACF:PARAMETER'-keys
                        for unionkey in allkeys:  # do the reverse check
                            if re.search(r"%d", unionkey):
                                # make regex from printf %d ONLY IF
                                # it appears in the key
                                unionregex = re.sub(r"%d", r"(\d+)", unionkey)
                                kmatch = re.search(unionregex, ACFKEY)
                                if kmatch:
                                    try:
                                        newkey = unionkey % int(kmatch.group(1))
                                    except:
                                        print("error")
                                    # Tracer()()
                                    self.union.update({newkey: ACFVAL})
                                    # default for unionkey is set now with
                                    # the proper index, so we can now
                                    # discard unionkey
                                    self.union.pop(unionkey)
                                    break

        # the DEFAULT MODE in the input is special -- it assigns
        # non ACF defaults to the union
        TheDefaultMode = self.modeKVpair["MODE_DEFAULT"]
        baddefault = False  # flag for bad default setting warning
        for key in TheDefaultMode:
            match = re.search(r"^ACF:", key)
            if not match:  # any key that isn't an ACF key
                self.union[key] = TheDefaultMode[key]
            else:
                print(
                    "WARNING: '%s' declared in MODE_DEFAULT does not "
                    "propagate to other modes." % key
                )
                baddefault = True
        if baddefault:
            print("**NOTE** 'ACF:'-type keys use default values from %s" % self.acffile)

    def __index_modeKVpair(self):
        """convert (\d+)'s into proper ACF indices"""
        for mode in self.modeKVpair:
            for key in self.modeKVpair[mode]:
                # search the "ACF:" keys for "%d="
                match = re.search(r"^ACF:.+?%d=(.+)", key)
                # NOTE: the above regex won't work for keys that do not
                # have a "=" in them, ie, this will not work for LINE
                # or MOD ACF statements, as they would not be unique
                if match:
                    # now figure out which key in self.union this corresponds to
                    keyregex = re.sub(r"%d", r"(\d+)", key)
                    for ukey in self.union:
                        kmatch = re.search(keyregex, ukey)
                        if kmatch:
                            newkey = key % int(kmatch.group(1))
                            self.modeKVpair[mode].update(
                                {newkey: self.modeKVpair[mode].pop(key)}
                            )
                            break

    def write(self, append=None):
        """write the mode sections to standard out"""
        if not self.__OK2write:
            print(
                "** Something is wrong -- check error messages from " "initialization."
            )
            if append:
                print("WARNING: no modes written to %s." % self.acffile)
            return False

        allkeys = np.sort(list(self.union))

        if append:
            sys.stdout = open(self.acffile, "a")

        for mode in self.modeKVpair:
            # loop over all modes declared
            print("[%s]" % mode)
            modekeys = list(self.modeKVpair[mode])
            # first, print the K=V entries for this mode.
            for key in allkeys:
                if key in modekeys:
                    print("%s=%s" % (key, self.modeKVpair[mode][key]))
                else:
                    print("%s=%s" % (key, self.union[key]))
            # print the non K=V entries for this mode.
            for line in self.modelist[mode]:
                print(line)
            # propagate any non K=V in MODE_DEFAULT with
            # neither thought nor regard
            if mode != "MODE_DEFAULT":
                for line in self.modelist["MODE_DEFAULT"]:
                    print(line)
        if append:
            sys.stdout.close()
            sys.stdout = sys.__stdout__
            print("Modes appended to %s" % self.acffile)
