from pathlib import Path
from typing import List

import subprocess
import traceback
import logging
import sys


def run_cmd(cmd: str, logger: logging.Logger, cwd: Path=Path(".")) -> None:
    run_cmd_list(cmd.split(), logger, cwd)

def run_cmd_list(cmd: List[str], logger: logging.Logger, cwd: Path=Path(".")) -> None:
    try:
        subprocess.run(cmd, cwd=cwd)
    except subprocess.CalledProcessError:
        logger.error(traceback.format_exc())
        sys.exit(1)
    except subprocess.TimeoutExpired:
        logger.error(traceback.format_exc())
        sys.exit(1)
