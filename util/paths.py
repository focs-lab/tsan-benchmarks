from pathlib import Path
from util import Context
from util.enums import V8Suite
import logging
import sys


class Paths:
    config_path = Path("config.yaml")
    log_path = Path("tbench.log")
    llvm_patch_path = Path("llvm.patch")

    # For builder.py and runner.py
    programs_path = Path("programs")
    depot_path = programs_path / "depot_tools"
    v8_path = programs_path / "v8"
    v8_benchmarks_path = v8_path / "test" / "benchmarks" / "data"
    v8_csuite_path = v8_path / "test" / "benchmarks" / "csuite"
    llvm_path = v8_path / "third_party" / "llvm"
    results_path = Path("results")
    v8_results_path = Path("results") / "v8"
    reports_path = Path("reports")

    def __init__(self, ctx: Context):
        self.logger = ctx.logger



    def maybe_mkdir(self, path: Path) -> None:
        if path.exists():
            return
        path.mkdir()

    def maybe_mkdir_programs(self) -> None:
        self.maybe_mkdir(self.programs_path)

    def maybe_mkdir_results(self) -> None:
        self.maybe_mkdir(self.results_path)
        self.maybe_mkdir(self.results_path / "v8")
        for suite in V8Suite:
            self.maybe_mkdir(self.results_path / "v8" / suite.name)

    def maybe_mkdir_reports(self) -> None:
        self.maybe_mkdir(self.reports_path)

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
