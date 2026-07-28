from .driverbase import WDLDriver
from argparse import ArgumentParser
from sys import stdout
from shutil import which
import os
import warnings
from typing import Optional
import logging
import subprocess

logger = logging.getLogger(__name__)

#TODO: something cleverer on windows, if that
#ever happens
def _find_gpp_program() -> Optional[str]:
    return which("gpp")


class FindGPP(WDLDriver):
    CMD_NAME: str = "find_gpp"

    @classmethod
    def setup_subparser(cls, subparsers) -> ArgumentParser:
        return super().setup_subparser(subparsers, fname_arg_setup=False)

    def __init__(self, **kwargs):
        #For now, just find system gpp, in future we can check bundled as well
        self._gpppath = _find_gpp_program()

    def __call__(self) -> int:
        if self._gpppath is not None:
            stdout.write(f"{self._gpppath}{os.linesep}")
            return 0
        else:
            warn("did not find GPP...")
            stdout.write(f"{os.linesep}")
            return 1

class PreprocessGPP(WDLDriver):
    CMD_NAME: str = "gpp_preprocess"
    ACCEPTS_EXTRA_ARGS: bool = True

    @classmethod
    def setup_subparser(cls, subparsers) -> ArgumentParser:
        return super().setup_subparser(subparsers, fname_arg_setup=False)

    def __init__(self, gppargs: list[str], **kwargs):
        self._gpppath = _find_gpp_program()
        self._gppargs = gppargs
        print(f" keyword args: {kwargs}")

    def __call__(self, cli_mode: bool) -> int:
        if self._gpppath is None:
            stdout.write("could not find GPP program, the gpp_preprocess command cannot continue")
            return 1

        logger.debug("gpp path is: %s", self._gpppath)
        logger.debug("extra gpp args are: %s", str(self._gppargs))

        procresult = subprocess.run(self._gpppath, self._gppargs)
        return procresult.return_code
