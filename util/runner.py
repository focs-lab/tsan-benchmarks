from pathlib import Path
from util import Context, Paths, shell, CommitInfo
import sys


class Runner:
    ctx: Context

    def __init__(self, ctx: Context):
        self.ctx = ctx
        self.paths = Paths(ctx)
        self.llvm_commits = ctx.config.llvm_commits
        self.llvm_commits.append(ctx.config.dev_llvm_commit)
        self.v8_baseline_name = ctx.config.v8_baseline_name

        self.run_v8 = ctx.config.run_v8
        self.run_mysql = ctx.config.run_mysql

        self.v8_benchmarks = ["sunspider", "octane", "kraken"]

    def run_one(self, name: str) -> None:
        if self.run_v8:
            self._run_benchmark_for_one_v8(name)
        if self.run_mysql:
            self._run_benchmark_for_one_mysql(name)
        self._export_results()

    def run_all(self) -> None:
        self._run_v8_benchmarks()
        self._run_mysql_benchmarks()
        self._export_results()

    def _run_v8_benchmark_for_commit(self, benchmark, commit):
        self.paths.ensure_v8_exists()
        logger = self.ctx.logger
        mode = "baseline" if commit.name == self.v8_baseline_name else "compare"
        logger.info(f"Running V8 benchmark {benchmark} on out/{commit.name}/d8 ({mode})")
        d8_path = self.paths.v8_path / "out" / commit.name / "d8"
        if not d8_path.exists():
            logger.error(f"{d8_path} does not exist. Aborting!")
            sys.exit(1)

        shell.run_cmd(f"test/benchmarks/csuite/csuite.py {benchmark} {mode} out/{commit.name}/d8", logger, self.paths.v8_path)

    def _run_v8_benchmark(self, benchmark) -> None:
        logger = self.ctx.logger
        logger.info(f"Running V8 benchmark - {benchmark}")
        for commit in self.llvm_commits:
            self._run_v8_benchmark_for_commit(benchmark, commit)

    def _run_benchmark_for_one_v8(self, name: str) -> None:
        commit = next(filter(lambda x: x.name == name, self.llvm_commits), None)
        for bm in self.v8_benchmarks:
            self._run_v8_benchmark_for_commit(bm, commit)

    def _run_benchmark_for_one_mysql(self, name: str) -> None:
        # TODO(dwslim): implement
        pass

    def _run_v8_benchmarks(self) -> None:
        logger = self.ctx.logger
        logger.info(f"Running V8 benchmarks")

        for bm in self.v8_benchmarks:
            self._run_v8_benchmark(bm)

    def _run_mysql_benchmarks(self) -> None:
        self.ctx.logger.info(f"Running MySQL benchmarks")
        # TODO(dwslim): implement

    def _export_results(self) -> None:
        self.ctx.logger.info("Exporting results to results/ directory")
        # TODO(dwslim): implement
