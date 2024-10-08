# Waveform Definition Language (WDL) for Archons

## Overview
WDL (Waveform Definition Language) is designed for use with Archons. This project provides tools and instructions for setting up and using WDL efficiently.

## Requirements

### System Requirements:
- Python 3.x
- GNU Make
- GPP (GNU Preprocessor) [Download GPP](https://logological.org/gpp)

### Python Packages:
The following Python packages are required:
- `numpy`
- `scipy`
- `matplotlib`
- `pyqt`

1. **Create a Virtual Environment**:
   If you don't have `venv` installed, you can install it with:
   ```bash
   sudo apt install python3-venv  # For Ubuntu
   ```
   **Create Command**
   ```bash
   python -m venv venv 
   ```

2. **Activate the Virtual Environment**:
   Once you have created your virtual environment, you need to activate it to start using it. Activation sets up your shell to use the Python interpreter and libraries from the virtual environment instead of the global Python environment.  
   
   **Activation Commands**
-  **On macOS and Linux**:
   ```bash
   source venv/bin/activate
   ```

3. **Install Required Packages**

   Once your virtual environment is activated, you can install the necessary Python packages listed in the `requirements.txt` file.

   **Installation Command**
   Run the following command to install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Setup Instructions

1. Directory Structure:
   - It is recommended to keep WDL in a separate directory from your ACF source files.
2. Copy the Makefile:
   - Copy the Makefile from the WDL directory to the directory containing your ACF source files.
3. Update Paths in Makefile:
   - Edit the Makefile to update the following lines with the correct paths

     ```makefile
     GPP       = /usr/local/bin/gpp
     WDLPATH   = $(HOME)/Software/wdl
     ACFPATH   = $(HOME)/Software/acf
     ```
     Ensure these paths point to your GPP executable, WDL directory, and ACF source files respectively.
4. Run make
   ```bash
    $ make ${TARGET}
   ```

## Demo Build
```bash
$ cd demo
$ make Demo
```