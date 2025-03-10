from abc import ABCMeta, abstractmethod
from argparse import ArgumentParser, _SubParsersAction, Namespace
from pathlib import Path
from io import TextIOWrapper
from sys import stdin
from contextlib import contextmanager
from typing import ContextManager

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
