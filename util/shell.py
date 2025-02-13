from pathlib import Path

import subprocess
import traceback
import logging
import sys


def run_cmd_with_error_handling(cmd: str, logger: logging.Logger, cwd: Path=Path(".")) -> None:
    try:
        subprocess.run(cmd.split(), cwd=cwd)
    except subprocess.CalledProcessError:
        logger.error(traceback.format_exc())
        sys.exit(1)
    except subprocess.TimeoutExpired:
        logger.error(traceback.format_exc())
        sys.exit(1)
