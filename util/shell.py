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

def run_cmd_with_out(cmd: str, logger: logging.Logger, out_file: Path, cwd: Path=Path(".")) -> None:
    run_cmdlist_with_out(cmd.split(), logger, out_file, cwd)

def run_cmdlist_with_out(cmd: List[str], logger: logging.Logger, out_file: Path, cwd: Path=Path(".")) -> None:
    try:
        subprocess.run(cmd, cwd=cwd, stdout=open(out_file, "w"))
    except subprocess.CalledProcessError:
        logger.error(traceback.format_exc())
        sys.exit(1)
    except subprocess.TimeoutExpired:
        logger.error(traceback.format_exc())
        sys.exit(1)

def check_cmd_output(cmd: str, logger: logging.Logger, cwd: Path=Path(".")) -> None:
    check_cmdlist_output(cmd.split(), logger, cwd)

def check_cmdlist_output(cmd: List[str], logger: logging.Logger, cwd: Path=Path(".")) -> bytes:
    try:
        return subprocess.check_output(cmd, cwd=cwd)
    except subprocess.CalledProcessError:
        logger.error(traceback.format_exc())
        sys.exit(1)
    except subprocess.TimeoutExpired:
        logger.error(traceback.format_exc())
        sys.exit(1)
