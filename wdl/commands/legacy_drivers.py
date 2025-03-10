import logging
import warnings
from typing import Optional
from argparse import ArgumentParser
from sys import stdout

from .driverbase import WDLDriver

from wdl.ini2acf import generate_acf


# horrible legacy code imports here, TODO: gradually chip away at it
import wdl.wavgen as wavgen
import wdl.modegen as modegen
from wdl.wdlParser import make_include_sequence, parse_modules, parse_system, make_include
import wdl.wdlParser as Parser

# TODO: separate out plotting, no need for this
import matplotlib.pyplot as plt


logger = logging.getLogger(__name__)


class SeqParserDriver(WDLDriver):
    CMD_NAME: str = "seq"
    CMD_DESCRIPTION: str = "parse a .conf file and make an include list from it"

    def __call__(self) -> int:
        logger.info("making include sequence")
        make_include_sequence(self._text)
        return 0


class ModParserDriver(WDLDriver):
    CMD_NAME: str = "mod"
    CMD_DESCRIPTION: str = "parse a .mod file and create .system and .modules from it"

    @classmethod
    def setup_subparser(cls, *args, **kwargs) -> ArgumentParser:
        parser = super().setup_subparser(*args, **kwargs)
        parser.add_argument("--projname", type=str, help="""project name to use. If not given,
        the legacy behaviour is followed (the first line of the input text is assumed to be the project name""")
        return parser

    def __init__(self, fname: str, projname: Optional[str] = None, **kwargs):
        with self._file_or_stdin(fname) as f:
            if projname is None:
                warnings.warn("parsing module file assuming the first line is the project name... This is fragile behaviour, ideally please use the --name argument to the command instead")
                projname = f.readline()

            logger.info("project name is: %s", projname)
            self._projname: str = projname
            self._text: str = f.read()

    def __call__(self) -> int:
        logger.debug("writing output to .modules file...")
        self._write_output("CONFIG", "modules", parse_modules(self._text))

        #Presumably the reason parse_system() here needs no keywords is some hideous global state
        # awfulness. DO NOT MOVE THIS LINE ABOVE THE PREVIOUS ONE, therefore
        logger.debug("writing output to .system file...")
        self._write_output("SYSTEM", "system", parse_system())
        return 0

    def _write_output(self, archonkw: str, fileext: str, output: str) -> int:
        fname: str = f"{self._projname}.{fileext}"
        with open(fname, "w") as f:
            f.writelines([f"[{archonkw}]"])
            f.write(output)

class IncParserDriver(WDLDriver):
    CMD_NAME: str = "inc"
    CMD_DESCRIPTION: str = "parse an include file"

    def __call__(self) -> int:
        make_include(self._text)
        return 0

class WdlParserDriver(WDLDriver):
    CMD_NAME: str = "wdl"
    CMD_DESCRIPTION: str = "parse the subroutines from a WDL input file"

    def __call__(self) -> int:
        logger.info("parsing WDL file...")

        # TODO:blergh
        global subroutines 
        subroutines = Parser.get_subroutines(self._text)
        Parser.get_params(self._text)
        output: str = Parser.parse(self._text)

        #apparently this one just prints it out, to stdout I guess?
        stdout.write(output)
        return 0

class WavgenDriver(WDLDriver):
    CMD_NAME: str = "wavgen"
    CMD_DESCRIPTION: str = "generate archon waveforms from WDL description"

    @classmethod
    def setup_subparser(cls, *args, **kwargs) -> ArgumentParser:
        parser = super().setup_subparser(*args, **kwargs)
        parser.add_argument("--plots", action="store_true", help="generate plots to go with waveforms")
        return parser

    def __init__(self, fname: str, plots: bool):
        #For some reason I don't understand, legacy wavegenDriver.py wants the BASE NAME of the project as
        #the argument, not the actual filename. Implement this behaviour here for compatibility even though
        #I must stress it seems a little odd

        self._fname: str = fname
        self._plots: bool = plots

    def __call__(self) -> int:
        # global variable because OF COURSE IT IS
        wavgen.GenerateFigs = self._plots
        wavgen.loadWDL(f"{self._fname}.wdl", self._fname)

        # ok this breaks previous behaviour because even if plot option was false
        # the original program still did a plt.show(). This seems utterly without reason to me
        # so here we only actually do that if it was asked for...
        # Again, all the plots are done with implicit global state rather than using the MPL object interface...
        if self._plots:
            plt.show(block=True)

        return 0


class ModegenDriver(WDLDriver):
    CMD_NAME: str = "modegen"
    CMD_DESCRIPTION: str = "generate archon modes from WDL description"

    @classmethod
    def setup_subparser(cls, subparsers) -> ArgumentParser:
        parser = super().setup_subparser(subparsers, fname_arg_setup=False)
        #need two filenames here, a mode file and an acf file
        parser.add_argument("modefile", type=str, help="the mode file to use")
        parser.add_argument("acffile", type=str, help="the ACF file to append to")
        return parser

    def __init__(self, modefile: str, acffile: str):
        self._modefile = modefile
        self._acffile = acffile

    def __call__(self) -> int:
        modegen.Modegen(self._modefile, self._acffile)
        return 0

class Ini2acfDriver(WDLDriver):
    CMD_NAME: str = "ini2acf"
    CMD_DESCRIPTION: str = "convert a INI syntax file into ACF"

    @classmethod
    def setup_subparser(cls, subparsers) -> ArgumentParser:
        parser = super().setup_subparser(subparsers)
        parser.add_argument("-o,--outfile",help="output file to use. By default, outputs to stdout", type=str)
        return parser

    def __init__(self, fname: str, outfile: Optional[str]):
        super().__init__(fname)
        self._outfile = stdout if outfile is None else outfile

    def __call__(self) -> int:
        outtxt: str = generate_acf(self._text, treat_str_as_content=True)
        with self._file_or_stdout(self._outfile) as f:
            f.write(outtxt)
            return 0
