# wdl
waveform definition language for Archons


## Requirements:
 - any version of make
 - GPP (https://logological.org/gpp)
 - Python 3.x or 2.7 (see **PYTHON NOTES** below)
 - numpy
 - scipy
 - matplotlib
 - pyqt
 
## Instructions:

 - It is advised that wdl be in a separate directory from you ACF source files.
 - Copy the Makefile from the wdl directory to the directory which contains your ACF source files.
 - Edit the following three lines in your Makefile to indicate the correct locations of
 GPP, the path to your WDL directory (this directory), and the path to your ACF source files.
 
```
GPP       = /usr/local/bin/gpp
WDLPATH   = $(HOME)/Software/wdl
ACFPATH   = $(HOME)/Software/acf
```

## PYTHON NOTES:

WDL has been tested with python 3.8 and 3.11 as well as python 2.7.  Using a more modern python is preferred.

Using your system's python should work as long as you also have the packages listed above.
