from .driverbase import WDLDriver
from argparse import ArgumentParser
from sys import stdout
from shutil import which
import warnings


class FindGPP(WDLDriver):
    @classmethod
    def setup_subparser(cls, subparsers) -> ArgumentParser:
        return super().setup_subparser(subparsers, fname_arg_setup=False)

    def __init__(self):
        #For now, just find system gpp, in future we can check bundled as well
        self._gpppath = which("gpp")

    def __call__(self) -> None:
        
    
