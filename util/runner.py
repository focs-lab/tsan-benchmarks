from dataclasses import dataclass
from pathlib import Path
from util import Context, Paths, shell, CommitInfo
from util.enums import V8Suite
from typing import List
import datetime
import sys


class Report:
    def __init__(self) -> None:
        self.contents: List[str] = []

    def add(self, stuff: str) -> None:
        self.contents.append(stuff)

    def extend(self, report: "Report") -> None:
        self.contents.extend(report.contents)

    def __str__(self):
        return "\n\n".join(self.contents)

class Runner:
    ctx: Context

    def __init__(self, ctx: Context, small: bool):
        self.ctx = ctx
        self.paths = Paths(ctx)
        self.llvm_commits = ctx.config.llvm_commits
        self.llvm_commits.append(ctx.config.dev_llvm_commit)
        self.dev_llvm_commit = ctx.config.dev_llvm_commit
        self.v8_baseline_name = ctx.config.v8_baseline_name

        self.run_v8 = ctx.config.run_v8
        self.run_mysql = ctx.config.run_mysql

        self.v8_suites = [V8Suite.SunSpider, V8Suite.Octane, V8Suite.Kraken]

        self.small = small

    def run_one(self, name: str) -> None:
        report = Report()

        if self.run_v8:
            self._run_benchmark_for_one_v8(name)
            report.extend(self._make_v8_report_for_one(name))
        if self.run_mysql:
            self._run_benchmark_for_one_mysql(name)
        self._export_report(report)

    def run_all(self) -> None:
        report = Report()
        if self.run_v8:
            self._run_v8_benchmarks()
            report.extend(self._make_v8_report_for_all())
        if self.run_mysql:
            self._run_mysql_benchmarks()
        self._export_report(report)

    # code copied from v8's test/benchmarks/csuite/csuite.py
    def _run_v8_benchmark_for_commit(self, suite: V8Suite, commit: CommitInfo) -> None:
        self.paths.ensure_v8_exists()
        logger = self.ctx.logger
        mode = "baseline" if commit.name == self.v8_baseline_name else "compare"
        logger.info(f"Running V8 benchmark {suite.name} on out/{commit.name}/d8 ({mode})")
        d8_path = self.paths.v8_path / "out" / commit.name / "d8"
        if not d8_path.exists():
            logger.error(f"{d8_path} does not exist. Aborting!")
            sys.exit(1)

        self.paths.maybe_mkdir_results()

        # shell.run_cmd(f"test/benchmarks/csuite/csuite.py {suite} {mode} out/{commit.name}/d8", logger, self.paths.v8_path)

        @dataclass
        class BenchmarkSetup:
            runs: int
            suite_path: Path
            js_path: Path

        match suite:
            case V8Suite.Octane:
                setup = BenchmarkSetup(
                    runs=10 if not self.small else 1,
                    suite_path=self.paths.v8_benchmarks_path / "octane",
                    js_path=self.paths.v8_benchmarks_path / "octane" / "run.js"
                )
            case V8Suite.Kraken:
                setup = BenchmarkSetup(
                    runs=80 if not self.small else 1,
                    suite_path=self.paths.v8_benchmarks_path / "kraken",
                    js_path=self.paths.v8_csuite_path.absolute() / "run-kraken.js"
                )
            case V8Suite.SunSpider:
                setup = BenchmarkSetup(
                    runs=100 if not self.small else 1,
                    suite_path=self.paths.v8_benchmarks_path / "sunspider",
                    js_path=self.paths.v8_csuite_path.absolute() / "sunspider-standalone-driver.js"
                )

        inner_command = f'{d8_path.absolute()} --expose-gc --dump-system-memory-stats {setup.js_path.absolute()}'
        benchmark_command_list = [
            "python3",
           str((self.paths.v8_csuite_path / "benchmark.py").absolute()),
           "-c",
            inner_command,
            "-fv",
            "-r",
            str(setup.runs),
            "-d",
            str(self.paths.v8_results_path.absolute())
        ]
        logger.info(f"Running V8 benchmark script - {' '.join(benchmark_command_list)}")
        shell.run_cmdlist_with_out(benchmark_command_list, logger, self.paths.v8_results_path / suite.name / commit.name, cwd=setup.suite_path)

    def _run_v8_benchmark(self, suite: V8Suite) -> None:
        logger = self.ctx.logger
        logger.info(f"Running V8 benchmark - {suite.name}")
        for commit in self.llvm_commits:
            self._run_v8_benchmark_for_commit(suite, commit)

    def _run_benchmark_for_one_v8(self, name: str) -> None:
        commit = next(filter(lambda x: x.name == name, self.llvm_commits), None)
        if commit is None:
            self.ctx.logger.error(f"Failed to find {name} under LLVM commits in the config file. Aborting!")
            sys.exit(1)
        for suite in self.v8_suites:
            self._run_v8_benchmark_for_commit(suite, commit)

    def _run_v8_benchmarks(self) -> None:
        logger = self.ctx.logger
        logger.info(f"Running V8 benchmarks")

        for suite in self.v8_suites:
            self._run_v8_benchmark(suite)

    def _run_benchmark_for_one_mysql(self, name: str) -> None:
        # TODO(dwslim): implement
        pass

    def _run_mysql_benchmarks(self) -> None:
        self.ctx.logger.info(f"Running MySQL benchmarks")
        # TODO(dwslim): implement

    def _v8_compare_one_vs_all(self, name: str) -> Report:
        logger = self.ctx.logger
        report = Report()
        for suite in self.v8_suites:
            self.paths.ensure_path_exists(self.paths.v8_results_path / suite.name)
            cmdlist = [
                "python3",
                str((self.paths.v8_csuite_path / "compare-baseline.py").absolute()),
                "-f",
                str((self.paths.v8_results_path / suite.name / name).absolute()),
                "-b",
                str((self.paths.v8_results_path / suite.name).absolute()),
                "-n"       # no color in output
            ]

            output = shell.check_cmdlist_output(cmdlist, logger).decode()
            message = f"V8 {suite.name} results ({name} vs all)\n{output}"
            logger.info(message)
            report.add(message)

        return report

    def _make_v8_report_for_one(self, name: str) -> Report:
        report = self._v8_compare_one_vs_all(name)
        return report

    def _make_v8_report_for_all(self) -> Report:
        report = self._v8_compare_one_vs_all(self.v8_baseline_name)
        return report

    def _export_report(self, report: Report) -> None:
        self.paths.maybe_mkdir_reports()
        logger = self.ctx.logger
        logger.info(f"Exporting report to {self.paths.reports_path.absolute()}")

        def make_report_header() -> str:
            header = ""
            header += f"=== Config:\n{open(self.paths.config_path).read()}\n\n"
            header += f"=== Dev LLVM Patch:\n{open(self.paths.v8_path / 'out' / self.dev_llvm_commit.name / self.paths.llvm_patch_path).read()}\n\n"
            return header

        now = datetime.datetime.now()
        dts = now.strftime("%Y-%m-%d-%H-%M-%S")
        with open(self.paths.reports_path / f"{dts}.report", "w") as report_file:
            report_file.write(make_report_header())
            report_file.write("=== Benchmark Results\n")
            report_file.write(str(report))

        # TODO(dwslim): mysql
