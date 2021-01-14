# wdl
waveform definition language for Archons


## Requirements:
 - any version of make
 - GPP (https://logological.org/gpp)
 - Python 2.7 (see **PYTHON NOTES** below)
 
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

WDL requires Python 2.7 which is no longer supported but 2.7 compatibility can be achieved with Anaconda.
Install Anaconda on your system using the appropriate method (e.g. sudo apt-get anaconda). Then create
an environment for a 2.7 python package. For example:

```
$ sudo apt-get anaconda
$ sudo sh /tmp/Anaconda3-2020.11-Linux-x86_64.sh
$ conda install python=2.7
$ sudo /opt/anaconda3/bin/conda create --name py2 python=2.7
```

That last command creates an environment named "py2".
You can now activate a Python 2.7 environment using the following command:

```
(base) $ conda activate py2
(py2) $
```

You are now in a Python 2.7 environment suitable for running WDL.
