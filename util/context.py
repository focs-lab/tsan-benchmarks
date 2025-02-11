from dataclasses import dataclass
from util import Config
import argparse
import logging

@dataclass
class Context:
    args: argparse.Namespace
    config: Config
    logger: logging.Logger
