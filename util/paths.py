from pathlib import Path
from util import Context
import logging
import sys


class Paths:

    def __init__(self, ctx: Context):
        self.logger = ctx.logger

        self.programs_path = Path("programs")
        self.depot_path = self.programs_path / "depot_tools"
        self.v8_path = self.programs_path / "v8"
        self.llvm_path = self.v8_path / "third_party" / "llvm"
        self.results_path = Path("results")

    def maybe_mkdir(self, path: Path) -> None:
        if path.exists():
            return
        path.mkdir()

    def maybe_mkdir_programs(self) -> None:
        self.maybe_mkdir(self.programs_path)

    def maybe_mkdir_results(self) -> None:
        self.maybe_mkdir(self.results_path)

    def ensure_v8_exists(self) -> None:
        if not self.v8_path.is_dir():
            self.logger.error("v8/ not found in programs/. Aborting!")
            sys.exit(1)

    def ensure_llvm_exists(self) -> None:
        self.ensure_v8_exists()
        if not self.llvm_path.is_dir():
            self.logger.error("llvm/ not found in programs/v8/third_party/. Aborting!")
            sys.exit(1)

    def ensure_path_exists(self, path: Path) -> None:
        if not path.exists():
            self.logger.error(f"{path} not found. Aborting!")
            sys.exit(1)
