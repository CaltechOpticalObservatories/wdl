"""Rewrite of ini2acf.pl utility in reasonably modern and intelligible python"""

from io import TextIOWrapper
from pathlib import Path
from typing import Generator, Optional
import sys
from argparse import ArgumentParser

def _extract_section_name(line: str) -> Optional[tuple[str, bool]]:
    if '[' not in line:
        return None
    else:
        secname: str = line.split("[")[1].split("]")[0]
        if '#' not in secname:
            return secname, False
        return secname.strip('#'), True


def _section_replace_filter(inp: str) -> Generator[tuple[str, list[str]], None, None]:
    #The original script uses a regex here to get the tag names but we'll just do it a
    #way that even a physicist can understand here
    thissection: Optional[str] = None
    seclines: list[str] = []
    for line in inp:
        if (tpl :=_extract_section_name(line)) is not None:
            secname, process = tpl
            # This is a new section. If we are already processing one, yield it out and start the next
            # Otherwise, start processing the lines
            if thissection is not None:
                yield thissection, seclines, process
            thissection = secname
            seclines.clear()

def generate_acf(inifile: str | Path | TextIOWrapper,
                 treat_str_as_content: bool=False) -> str:
    """the way this seems to work is the WDL legacy tools spit out files that have an ini section that is labelled e.g.
    [PARAMETER#]... with the # character in it. Here, we are (I think) supposed to just go through the items in that section
    and number them"""


    #note my first thought here was to use the built in INI parsing "configparser" module,
    #but unfortunately, it can't quite handle things like the [PARAMETER#] lines. Shame

    if isinstance(inifile, Path) or (isinstance(inifile, str) and not treat_str_as_content):
        with open(inifile, "r") as f:
            inp: str = f.read()
    elif isinstance(inifile, str):
        #This is a string containing the content of an inifile
        inp = inifile
    else:
        #This is an already open file like opject
        inp: str = inifile.read()

    outp: list[str] = []
    for secname, seclines, process in _section_replace_filter(inp):
        outp.append(f"[{secname}]")
        if process:
            for ind, line in enumerate(seclines):
                #strip whitespace and remove any trailing comment
                line = line.split("#")[0].strip()
                newline: str = f'{secname}{ind}="{line}"'
                outp.append(newline)
            # A line telling us how many we had
            outp.append(f'{secname}S={ind+1}')
        else:
            outp.extend(seclines)
    return outp

def main():
    ap = ArgumentParser(prog="ini2acf",
                        description="""

                        This is a python rewrite of David Hale and Peter Mao's ini2acf.pl script.
                        It is intended to be call compatible with that script. The original
                        documentation follows...

                        Format an INI type file for insertion into ACF.  Removes comments, and
                        trailing whitespace.  

                        In the input file, lines of the same tag type are grouped under [TAG].
                        When the tag is specified as [TAG#], the acf lines are numbered and
                        the number of lines of a tag type are reported when a new tag is
                        encountered or the end of file is reached.

                        Appropriate for numbered tags: LINE, PARAMETER, CONSTANT, TAPLINE

                        This code is NOT smart enough to know if you use the same tag in
                        two disjoint parts of the INI file.

                        """)
    ap.add_argument("infile", help="input ini file", type=str)
    ap.add_argument("-o,--outfile", help="output file to use. By default, outputs to stdout", type=str)

    args = ap.parse_args()

    out_content: str = generate_acf(args.inifile)

    if args.outfile is not None:
        with open(args.outfile,"w") as f:
            f.write(out_content)

    else:
        sys.stdout.write(out_content)

    return 0


if __name__ == "__main__":
    #basic direct call behaviour to mimic the old ini2acf.pl script
    # TODO
    return main()

