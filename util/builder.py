from util import Context, CommitInfo, Config, shell, Paths
from pathlib import Path

import sys
import os


class Builder:
    ctx: Context

    def __init__(self, ctx: Context):
        self.ctx = ctx

        self.paths = Paths(ctx)

        self.v8_commit = ctx.config.v8_commit
        self.llvm_commits = ctx.config.llvm_commits
        if len(self.llvm_commits) == 0:
            self.ctx.logger.error("llvm_commits field in config is empty. Aborting!")
            sys.exit(1)

        self.run_mysql = ctx.config.run_mysql
        self.run_v8 = ctx.config.run_v8
        self.optimize_v8 = ctx.config.optimize_v8
        self.build_num_cpus = ctx.config.build_num_cpus

        os.environ['PATH'] = str(self.paths.depot_path.absolute()) + os.pathsep + os.environ.get('PATH', '')

    def build_one(self, name: str) -> None:
        self.paths.maybe_mkdir_programs()
        # We are using V8's LLVM build script so pull it regardless of whether we want to run V8.
        self._maybe_fetch_v8()
        # self._sync_and_build_llvm()

        commit = next(filter(lambda x: x.name == name, self.llvm_commits), None)

        logger = self.ctx.logger
        if commit is None:
            logger.error(f"No such LLVM commit for {name} in the config file. Aborting!")
            sys.exit(1)

        logger.info(f"Building benchmarks with LLVM commit {commit.commit} ({name})")
        self._sync_and_build_llvm(commit)
        if self.run_v8:
            self._rebuild_v8(commit)
        if self.run_mysql:
            self._rebuild_mysql(commit)

    def build_all(self) -> None:
        self.paths.maybe_mkdir_programs()
        # We are using V8's LLVM build script so pull it regardless of whether we want to run V8.
        self._maybe_fetch_v8()
        # self._sync_and_build_llvm()

        for commit in self.llvm_commits:
            self._sync_and_build_llvm(commit)
            if self.run_v8:
                self._rebuild_v8(commit)
            if self.run_mysql:
                self._rebuild_mysql(commit)

    # def _maybe_clone_llvm(self) -> None:
    #     if self.paths.llvm_path.exists():
    #         return

    #     self.ctx.logger.info(f"Cloning LLVM")
    #     logger = self.ctx.logger

    #     shell.run_cmd("git clone https://github.com/focs-lab/llvm-project", logger, self.paths.programs_path)
    #     shell.run_cmd("git remote add upstream https://github.com/llvm/llvm-project", logger, self.paths.llvm_path)
    #     shell.run_cmd("git fetch upstream", logger, self.paths.llvm_path)

    def _maybe_clone_llvm_in_v8(self) -> None:
        self.paths.ensure_v8_exists()

        if self.paths.llvm_path.is_dir():
            return

        logger = self.ctx.logger
        logger.info(f"Cloning Chromium's LLVM")
        shell.run_cmd("./tools/clang/scripts/build.py --without-android --without-fuchsia --with-ccache --skip-build", logger, self.paths.v8_path)

    def _sync_llvm(self, commit: CommitInfo) -> None:
        self.paths.ensure_llvm_exists()

        logger = self.ctx.logger
        logger.info(f"Syncing LLVM to commit {commit.commit}")
        shell.run_cmd(f"git fetch", logger, self.paths.llvm_path)
        shell.run_cmd(f"git checkout {commit.commit}", logger, self.paths.llvm_path)

    def _build_llvm(self) -> None:
        self.paths.ensure_llvm_exists()

        def reset_build_script():
            shell.run_cmd("git checkout build.py", self.ctx.logger, self.paths.v8_path / "tools" / "clang" / "scripts")

        def replace_ninja_jobs():
            script_path = self.paths.v8_path / "tools" / "clang" / "scripts" / "build.py"
            script_contents = open(script_path).read()
            script_contents = script_contents.replace("'ninja'", f"'ninja', '-j{self.build_num_cpus}'")
            open(script_path, "w").write(script_contents)

        logger = self.ctx.logger
        logger.info(f"Building LLVM")
        # Build LLVM that was configured inside V8. Before that, change the number of jobs spawned by ninja.
        reset_build_script()
        replace_ninja_jobs()
        shell.run_cmd(f"./tools/clang/scripts/build.py --without-android --without-fuchsia --with-ccache --skip-checkout", logger, self.paths.v8_path)

    def _sync_and_build_llvm(self, commit: CommitInfo) -> None:
        self._maybe_clone_llvm_in_v8()
        self._sync_llvm(commit)
        self._build_llvm()

    def _maybe_clone_depot_tools(self) -> None:
        if self.paths.depot_path.is_dir():
            return

        self.ctx.logger.info("Cloning depot tools")
        shell.run_cmd("git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git",
                       self.ctx.logger,
                       self.paths.programs_path)

    def _maybe_fetch_v8(self) -> None:
        if self.paths.v8_path.is_dir():
            return

        logger = self.ctx.logger
        logger.info("Fetching V8")
        self._maybe_clone_depot_tools()
        shell.run_cmd("gclient", logger)
        shell.run_cmd("fetch v8", logger, self.paths.programs_path)
        shell.run_cmd(f"git checkout {self.v8_commit}", logger, self.paths.v8_path)
        shell.run_cmd(f"gclient sync", logger, self.paths.v8_path)

    def _sync_v8(self) -> None:
        self.paths.ensure_v8_exists()
        logger = self.ctx.logger
        logger.info("Syncing V8")
        shell.run_cmd(f"git checkout {self.v8_commit}", logger, self.paths.v8_path)
        shell.run_cmd(f"gclient sync -D", logger, self.paths.v8_path)

    def _setup_v8_build(self, name: str, with_tsan: bool) -> None:
        self.paths.ensure_v8_exists()

        # build_dir = self.paths.v8_path / "out" / name
        # if build_dir.is_dir():
        #     return

        logger = self.ctx.logger
        logger.info(f"Setting up V8 build directory at out/{name} (with{'out' if not with_tsan else ''} tsan)")

        # Make sure the entries don't have a space in them
        gn_args = [
            "dcheck_always_on=false",
            "is_component_build=false",
            "is_debug=false",
            f"is_tsan={'true' if with_tsan else 'false'}",      # this is the stupidest code in the world
            'target_cpu="x64"',
            "v8_enable_google_benchmark=true",
            "v8_enable_test_features=true",
            "v8_enable_fast_torque=true",
            f'clang_base_path="{self.paths.v8_path.absolute()}/third_party/llvm-build/Release+Asserts/"'
        ]
        shell.run_cmd_list(
            ["gn", "gen", f"out/{name}", f"--args={' '.join(gn_args)}"],
            logger,
            self.paths.v8_path
        )

    def _patch_v8(self) -> None:
        self.paths.ensure_v8_exists()

        logger = self.ctx.logger
        logger.info(f"Patching V8 to optimize TSan builds with O3")

        def search_and_replace(path: Path, before: str, after: str) -> None:
            self.paths.ensure_path_exists(path)
            contents = open(path).read()
            if before not in contents:
                logger.error(f"'{before}' not found in {path}. Something must have changed in the V8 codebase.\
                              Cannot optimize TSan build although optimize_v8 is set in the config. Aborting!")
                sys.exit(1)
            contents = contents.replace(before, after)
            open(path, "w").write(contents)

        v8_build = self.paths.v8_path / "build"
        v8_src = self.paths.v8_path / "src"
        build_gn_path = self.paths.v8_path / "BUILD.gn"
        compiler_build_gn_path = v8_build / "config" / "compiler" / "BUILD.gn"
        macros_path = v8_src / "base" / "macros.h"

        shell.run_cmd("git checkout BUILD.gn", logger, self.paths.v8_path)
        shell.run_cmd("git checkout config/compiler/BUILD.gn", logger, v8_build)
        shell.run_cmd("git checkout base/macros.h", logger, v8_src)

        search_and_replace(build_gn_path,
                           'enabled_external_v8_defines += [ "V8_IS_TSAN" ]',
                           '# enabled_external_v8_defines += [ "V8_IS_TSAN" ]')
        search_and_replace(build_gn_path,
                           '"V8_IS_TSAN",',
                           '# "V8_IS_TSAN",')
        search_and_replace(compiler_build_gn_path,
                           'cflags = [ "-O2" ] + common_optimize_on_cflags',
                           'cflags = [ "-O3" ] + common_optimize_on_cflags')
        search_and_replace(macros_path,
                           '#define IF_TSAN(V, ...) EXPAND(V(__VA_ARGS__))',
                           '#define IF_TSAN(V, ...)')

    def _rebuild_v8(self, commit: CommitInfo) -> None:
        self.paths.ensure_v8_exists()

        logger = self.ctx.logger
        logger.info(f"Building V8")

        if self.optimize_v8:
            self._patch_v8()

        self._setup_v8_build(commit.name, commit.with_tsan)
        shell.run_cmd(f"ninja -C out/{commit.name} -t clean", logger, self.paths.v8_path)
        shell.run_cmd(f"ninja -C out/{commit.name} -j{self.build_num_cpus} d8", logger, self.paths.v8_path)

    def _maybe_download_mysql(self) -> None:
        # TODO(dwslim): implement
        pass

    def _rebuild_mysql(self, commit: CommitInfo) -> None:
        # TODO(dwslim): implement
        pass
