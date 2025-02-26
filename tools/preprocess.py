import subprocess
from pathlib import Path
import platform
from typing import Optional

def find_gpp_path() -> Optional[Path]:
    """attempts to find gpp preprocessor program
       Throws if gpp is not found 
    """

    if platform.system() == "Windows":
        #NOTE, until tested on windows, assume cmd.exe rather than powershell for now.
        #Might need to handle powershell case with Get-Command rather than where
        cmd: str = "where"
    else:
        cmd: str = "which"

    # Default case is POSIX
    proc_output = subprocess.run([cmd, "gpp"], capture_output=True)

    # Throws if return code is not right
    try:
        proc_output.check_returncode()
    except subprocess.CalledProcessError as err:
        raise RuntimeError("failed to find GPP program") from err
    return Path(proc_output.stdout.decode("UTF-8").strip())


