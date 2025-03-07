from argparse import ArgumentParser, _SubParsersAction, Namespace
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from sys import stdin, stdout
from typing  import Optional, ContextManager
from contextlib import contextmanager
from io import TextIOWrapper
import warnings

from wdl.wdlParser import make_include_sequence, parse_modules, parse_system, make_include
from wdl.ini2acf import generate_acf
import wdl.wavgen as wavgen
import wdl.modegen as modegen
import fileinput
import logging
import matplotlib.pyplot as plt
from pathlib import Path
import os

logger = logging.getLogger(__name__)

class WDLDriver(metaclass=ABCMeta):
    @classmethod
    def setup_subparser(cls, subparsers: _SubParsersAction, fname_arg_setup: bool=True) -> ArgumentParser:
        """sets up a sub-parser for arguments specific to this particular type of WDL subcommand driver"""

        #Get a name to put in the parser, either explicit or named after the class
        cmdname: str = getattr(cls, "CMD_NAME", cls.__name__)
        cmddesc: str = getattr(cls, "CMD_DESCRIPTION", None)
        parser = subparsers.add_parser(name=cmdname, description=cmddesc)

        if fname_arg_setup:
            parser.add_argument("fname", help="file to read input from. Use '-' to read from stdin")            

        def runner(args: Namespace) -> None:
            kwargs = vars(args)
            obj: cls = cls(**kwargs)
            obj()

        parser.set_defaults(func=runner)
        return parser

    @classmethod
    def find_input_files(cls, basepath: str | Path) -> list[str]:
        if not hasattr(cls, "CMD_FILE_EXTENSIONS"):
            raise AttributeError("don't know file extensions to search for")
        if isinstance(basepath, str):
            basepath: Path = Path(basepath)
        for extn in cls.CMD_FILE_EXTENSIONS:
            possible_files = basepath.glob(f"*.{extn}")
        return possible_files
    
    def __init__(self, fname: str, **kwargs):
        """The default __init__ of a driver takes a filename and reads it into the ._text attribute of the class.
        Since this is the most common operation of a WDL driver program"""
        self._text = self._read_file_or_stdin(fname)

    @abstractmethod
    def __call__(self) -> None: ...

    @contextmanager
    def _file_or_stdin(self, fname: str) -> ContextManager[TextIOWrapper]:
        """context manager that opens a specified file or uses sys.stdin for the special case of file '-'"""
        if fname == "-":
            yield stdin
        else:
            f = open(fname, "r")
            yield f
            f.close()

    @contextmanager
    def _file_or_stdout(self, output: TextIOWrapper | str) -> ContextManager[TextIOWrapper]:
        if isinstance(output, str):
            f = open(output, "w")
            yield f
        else:
            yield output

    def _read_file_or_stdin(self, fname: str) -> str:
        with self._file_or_stdin(fname) as f:
            return f.read()


class SeqParserDriver(WDLDriver):
    CMD_NAME: str = "seq"
    CMD_DESCRIPTION: str = "parse a .conf file and make an include list from it"

    def __call__(self) -> None:
        logger.info("making include sequence")
        make_include_sequence(self._text)

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

    def __call__(self) -> None:
        logger.debug("writing output to .modules file...")
        self._write_output("CONFIG", "modules", parse_modules(self._text))

        #Presumably the reason parse_system() here needs no keywords is some hideous global state
        # awfulness. DO NOT MOVE THIS LINE ABOVE THE PREVIOUS ONE, therefore
        logger.debug("writing output to .system file...")
        self._write_output("SYSTEM", "system", parse_system())


    def _write_output(self, archonkw: str, fileext: str, output: str) -> None:
        fname: str = f"{self._projname}.{fileext}"
        with open(fname, "w") as f:
            f.writelines([f"[{archonkw}]"])
            f.write(output)

class IncParserDriver(WDLDriver):
    CMD_NAME: str = "inc"
    CMD_DESCRIPTION: str = "parse an include file"

    def __call__(self) -> None:
        make_include(self._text)

class WdlParserDriver(WDLDriver):
    CMD_NAME: str = "wdl"
    CMD_DESCRIPTION: str = "parse the subroutines from a WDL input file"

    def __call__(self) -> None:
        logger.info("parsing WDL file...")
        output = parse(self._text)


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

    def __call__(self) -> None:
        #global variable because OF COURSE IT IS
        wavgen.GenerateFigs = self._plots
        wavgen.loadWDL(f"{self._fname}.wdl", self._fname)

        #ok this breaks previous behaviour because even if plot option was false
        #the original program still did a plt.show(). This seems utterly without reason to me
        #so here we only actually do that if it was asked for...
        #Again, all the plots are done with implicit global state rather than using the MPL object interface...
        if self._plots:
            plt.show(block=True)

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

    def __call__(self) -> None:
        modegen.Modegen(self._modefile, self._acffile)

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
        self._outfile = sys.stdout if outfile is None else outfile

    def __call__(self) -> None:
        outtxt: str = generate_acf(self._text, treat_str_as_content=True)
        with self._file_or_stdout(self._outfile) as f:
            f.write(outtxt)

        
def main():
    ap = ArgumentParser(prog="wdl",
                             description="command line interface to Waveform Definition Language (WDL)")
    ap.add_argument("--debug", help="print verbose debugging output", action="store_true")
    subparsers = ap.add_subparsers(required=True, help="the WDL subcommand to run")

    for cls in [SeqParserDriver, ModParserDriver, IncParserDriver, WdlParserDriver,
                WavgenDriver, ModegenDriver, Ini2acfDriver]:
        cls.setup_subparser(subparsers)

    args = ap.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    #call the command
    args.func(args)


if __name__ == "__main__":
    main()
