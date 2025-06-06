from argparse import ArgumentParser
import sys
from .commands.driverbase import WDLDriver
from .commands.legacy_drivers import (
    SeqParserDriver, ModParserDriver, IncParserDriver,
    WdlParserDriver, WavgenDriver, ModegenDriver, Ini2acfDriver)

from .commands.preprocess import FindGPP, PreprocessGPP

import logging

logger = logging.getLogger(__name__)

def main():
    ap = ArgumentParser(prog="wdl",
                             description="command line interface to Waveform Definition Language (WDL)")
    ap.add_argument("--debug", help="print verbose debugging output", action="store_true")
    subparsers = ap.add_subparsers(required=True, help="the WDL subcommand to run",
                                   dest="command_name")

    #NOTE: could  have done a fancy autoreg thing here but there's only a few and this is likely
    #clearer until there are lots more IMO
    command_classes: list[type] = [SeqParserDriver, ModParserDriver, IncParserDriver, WdlParserDriver,
                                   WavgenDriver, ModegenDriver, Ini2acfDriver, FindGPP, PreprocessGPP]

    for cls in command_classes:
        cls.setup_subparser(subparsers)

    args, unknown_args = ap.parse_known_args()


    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    #the default func is setup by the class method above to just return which class it is
    #that will be operating the command
    run_command_tp: type[WDLDriver] = args.func(args)

    if run_command_tp.ACCEPTS_EXTRA_ARGS:
        obj = run_command_tp(unknown_args, **vars(args))
    elif len(unknown_args) > 0:
        logger.error("extra (unknown) arguments provided to command that doesn't accept them")
        logger.error(f"those arguments were: {unknown_args}")
        #my instinct is to throw here but that seems unpopular round these parts so just bail out
        sys.exit(1)
    else:
        kwargs = vars(args)
        obj = run_command_tp(**kwargs)

    #run the command
    return obj(cli_mode=True)


if __name__ == "__main__":
    retcode = main()
    sys.exit(retcode)
