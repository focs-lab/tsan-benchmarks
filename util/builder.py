from util import Context, Config, shell
from pathlib import Path

import sys
import os


class Builder:
    ctx: Context

    def __init__(self, ctx: Context):
        self.ctx = ctx
        self.programs_path = Path("programs")
        self.depot_path = self.programs_path / "depot_tools"
        self.v8_path = self.programs_path / "v8"
        self.v8_commit = ctx.config.v8_commit
        self.llvm_path = self.v8_path / "third_party" / "llvm"
        self.llvm_commit = ctx.config.llvm_commit
        self.run_mysql = ctx.config.run_mysql
        self.run_v8 = ctx.config.run_v8
        self.build_num_cpus = ctx.config.build_num_cpus

        os.environ['PATH'] = str(self.depot_path.absolute()) + os.pathsep + os.environ.get('PATH', '')

    def build_all(self) -> None:
        # We are using V8's LLVM build script so pull it regardless of whether we want to run V8.
        self._maybe_fetch_v8()
        self._sync_and_build_llvm()
        if self.run_mysql:
            self._rebuild_mysql()
        if self.run_v8:
            self._rebuild_v8()

    def _maybe_mkdir_programs(self) -> None:
        path = self.programs_path
        if path.exists():
            return
        path.mkdir()

    def _ensure_v8_exists(self) -> None:
        if not self.v8_path.is_dir():
            self.ctx.logger.error("v8/ not found in programs/. Aborting!")
            sys.exit(1)

    def _ensure_llvm_exists(self) -> None:
        self._ensure_v8_exists()
        if not self.llvm_path.is_dir():
            self.ctx.logger.error("llvm/ not found in programs/v8/third_party/. Aborting!")
            sys.exit(1)

    # def _maybe_clone_llvm(self) -> None:
    #     self._maybe_mkdir_programs()
    #     if self.llvm_path.exists():
    #         return

    #     self.ctx.logger.info(f"Cloning LLVM")
    #     logger = self.ctx.logger

    #     shell.run_cmd_with_error_handling("git clone https://github.com/focs-lab/llvm-project", logger, self.programs_path)
    #     shell.run_cmd_with_error_handling("git remote add upstream https://github.com/llvm/llvm-project", logger, self.llvm_path)
    #     shell.run_cmd_with_error_handling("git fetch upstream", logger, self.llvm_path)

    def _maybe_clone_llvm_in_v8(self) -> None:
        self._ensure_v8_exists()

        if self.llvm_path.is_dir():
            return

        logger = self.ctx.logger
        logger.info(f"Cloning Chromium's LLVM")
        shell.run_cmd_with_error_handling("./tools/clang/scripts/build.py --without-android --without-fuchsia --with-ccache --skip-build", logger, self.v8_path)

    def _sync_llvm(self) -> None:
        self._ensure_llvm_exists()

        logger = self.ctx.logger
        logger.info(f"Syncing LLVM")
        shell.run_cmd_with_error_handling(f"git fetch", logger, self.llvm_path)
        shell.run_cmd_with_error_handling(f"git checkout {self.llvm_commit}", logger, self.llvm_path)

    def _build_llvm(self) -> None:
        self._ensure_llvm_exists()

        def reset_build_script():
            shell.run_cmd_with_error_handling("git checkout build.py", self.ctx.logger, self.v8_path / "tools" / "clang" / "scripts")

        def replace_ninja_jobs():
            script_path = self.v8_path / "tools" / "clang" / "scripts" / "build.py"
            script_contents = open(script_path).read()
            script_contents = script_contents.replace("'ninja'", f"'ninja', '-j{self.build_num_cpus}'")
            open(script_path, "w").write(script_contents)

        logger = self.ctx.logger
        logger.info(f"Building LLVM")
        # Build LLVM that was configured inside V8. Before that, change the number of jobs spawned by ninja.
        reset_build_script()
        replace_ninja_jobs()
        shell.run_cmd_with_error_handling(f"./tools/clang/scripts/build.py --without-android --without-fuchsia --with-ccache --skip-checkout", logger, self.v8_path)

    def _sync_and_build_llvm(self) -> None:
        self._maybe_clone_llvm_in_v8()
        self._sync_llvm()
        self._build_llvm()
    
    def _maybe_clone_depot_tools(self) -> None:
        if self.depot_path.is_dir():
            return
        
        self.ctx.logger.info("Cloning depot tools")
        shell.run_cmd_with_error_handling("git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git",
                                          self.ctx.logger,
                                          self.programs_path)

    def _maybe_fetch_v8(self) -> None:
        if self.v8_path.is_dir():
            return

        logger = self.ctx.logger
        logger.info("Fetching V8")
        self._maybe_clone_depot_tools()
        shell.run_cmd_with_error_handling("gclient", logger)
        shell.run_cmd_with_error_handling("fetch v8", logger, self.programs_path)
        shell.run_cmd_with_error_handling(f"git checkout {self.v8_commit}", logger, self.v8_path)
        shell.run_cmd_with_error_handling(f"gclient sync", logger, self.v8_path)

    def _sync_v8(self) -> None:
        # TODO(dwslim): implement
        pass

    def _rebuild_v8(self) -> None:
        logger = self.ctx.logger
        logger.info(f"Building V8")

        # shell.run_cmd_with_error_handling(
        #     """gn gen out/foo --args='is_debug=false target_cpu="x64" v8_target_cpu="arm64" use_goma=true'"""
        # )
        # TODO(dwslim): implement

    def _maybe_download_mysql(self) -> None:
        # TODO(dwslim): implement
        pass

    def _rebuild_mysql(self) -> None:
        # TODO(dwslim): implement
        pass
