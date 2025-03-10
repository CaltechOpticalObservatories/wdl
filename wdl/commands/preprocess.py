from .driverbase import WDLDriver
from argparse import ArgumentParser
from sys import stdout
from shutil import which
import os
import warnings


class FindGPP(WDLDriver):
    CMD_NAME: str = "find_gpp"


    @classmethod
    def setup_subparser(cls, subparsers) -> ArgumentParser:
        return super().setup_subparser(subparsers, fname_arg_setup=False)

    def __init__(self, **kwargs):
        #For now, just find system gpp, in future we can check bundled as well
        self._gpppath = which("gpp")

    def __call__(self) -> int:
        if self._gpppath is not None:
            stdout.write(f"{self._gpppath}{os.linesep}")
            return 0
        else:
            warn("did not find GPP...")
            stdout.write(f"{os.linesep}")
            return 1
