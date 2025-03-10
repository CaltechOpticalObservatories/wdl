from argparse import ArgumentParser
import sys

from .commands.legacy_drivers import (
    SeqParserDriver, ModParserDriver, IncParserDriver,
    WdlParserDriver, WavgenDriver, ModegenDriver, Ini2acfDriver)

from .commands.preprocess import FindGPP


import logging

logger = logging.getLogger(__name__)

def main():
    ap = ArgumentParser(prog="wdl",
                             description="command line interface to Waveform Definition Language (WDL)")
    ap.add_argument("--debug", help="print verbose debugging output", action="store_true")
    subparsers = ap.add_subparsers(required=True, help="the WDL subcommand to run")

    for cls in [SeqParserDriver, ModParserDriver, IncParserDriver, WdlParserDriver,
                WavgenDriver, ModegenDriver, Ini2acfDriver, FindGPP]:
        cls.setup_subparser(subparsers)

    args = ap.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # call the command
    return args.func(args)


if __name__ == "__main__":
    retcode = main()
    sys.exit(retcode)
