from util import Context, CommitInfo, Config, shell, Paths, enums
from pathlib import Path

import shutil
import sys
import os


class Builder:
    ctx: Context

    def __init__(self, ctx: Context, target: enums.Target):
        self.ctx = ctx

        self.paths = Paths(ctx)

        self.v8_commit = ctx.config.v8_commit
        self.llvm_commits = ctx.config.llvm_commits
        self.dev_llvm_commit = ctx.config.dev_llvm_commit
        if len(self.llvm_commits) == 0:
            self.ctx.logger.error("llvm_commits field in config is empty. Aborting!")
            sys.exit(1)

        self.mysql_download_link = ctx.config.mysql_download_link

        self.optimize_v8 = ctx.config.optimize_v8
        self.build_num_cpus = ctx.config.build_num_cpus

        self.build_v8 = target == enums.Target.V8 or target == enums.Target.ALL
        self.build_mysql = target == enums.Target.MYSQL or target == enums.Target.ALL

        os.environ['PATH'] = str(self.paths.depot_path.absolute()) + os.pathsep + os.environ.get('PATH', '')

    def build_one(self, name: str) -> None:
        self._prepare_build()

        commit = next(filter(lambda x: x.name == name, self.llvm_commits), None)

        logger = self.ctx.logger
        if commit is None:
            logger.error(f"No such LLVM commit for {name} in the config file. Aborting!")
            sys.exit(1)

        logger.info(f"Building benchmarks with LLVM commit {commit.commit} ({name})")
        # self._sync_and_build_llvm(commit)
        if self.build_v8:
            self._rebuild_v8(commit)
        if self.build_mysql:
            self._rebuild_mysql(commit)

    def build_all(self) -> None:
        self._prepare_build()

        for commit in self.llvm_commits:
            self._sync_and_build_llvm(commit)
            if self.build_v8:
                self._rebuild_v8(commit)
            if self.build_mysql:
                self._rebuild_mysql(commit)

    def dev_v8(self, build_or_link: enums.DevMode) -> None:
        sync_v8 = build_or_link != enums.DevMode.LINK
        self._prepare_build(sync_v8)

        self._dev_llvm(self.dev_llvm_commit)
        if build_or_link == enums.DevMode.BUILD:
            self._rebuild_v8(self.dev_llvm_commit)
        elif build_or_link == enums.DevMode.LINK:
            self._relink_v8(self.dev_llvm_commit)

        shutil.copy(self.paths.llvm_patch_path, self.paths.v8_path / "out" / self.dev_llvm_commit.name)

    def dev_mysql(self, build_or_link: enums.DevMode) -> None:
        sync_v8 = build_or_link != enums.DevMode.LINK
        self._prepare_build(sync_v8)

        self._dev_llvm(self.dev_llvm_commit)
        if build_or_link == enums.DevMode.BUILD:
            self._rebuild_mysql(self.dev_llvm_commit)
        elif build_or_link == enums.DevMode.LINK:
            self._relink_mysql(self.dev_llvm_commit)

    def dev_all(self, build_or_link: enums.DevMode) -> None:
        self.dev_v8(build_or_link)
        self.dev_mysql(build_or_link)

    # def _maybe_clone_llvm(self) -> None:
    #     if self.paths.llvm_path.exists():
    #         return

    #     self.ctx.logger.info(f"Cloning LLVM")
    #     logger = self.ctx.logger

    #     shell.run_cmd("git clone https://github.com/focs-lab/llvm-project", logger, self.paths.programs_path)
    #     shell.run_cmd("git remote add upstream https://github.com/llvm/llvm-project", logger, self.paths.llvm_path)
    #     shell.run_cmd("git fetch upstream", logger, self.paths.llvm_path)

    def _git_checkout_and_clean(self, commit: str, path: Path) -> None:
        logger = self.ctx.logger
        shell.run_cmd(f"git checkout -f {commit}", logger, path)
        shell.run_cmd(f"git clean -f .", logger, path)

    def _prepare_build(self, sync_v8: bool=True) -> None:
        self.paths.maybe_mkdir_programs()
        # We are using V8's LLVM build script so pull it regardless of whether we want to run V8.
        self._maybe_fetch_v8()
        if sync_v8:
            self._sync_v8()

        if self.build_mysql:
            self._maybe_download_mysql()

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
        self._git_checkout_and_clean(commit.commit, self.paths.llvm_path)

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

    def _dev_llvm(self, commit: CommitInfo) -> None:
        self._maybe_clone_llvm_in_v8()
        self._sync_llvm(commit)
        llvm_build_path = self.paths.v8_path / "third_party" / "llvm-build"
        if not llvm_build_path.exists():
            self._build_llvm()
        self._patch_llvm()
        shell.run_cmd(f"ninja -C third_party/llvm-build/Release+Asserts/ -j{self.build_num_cpus}", self.ctx.logger, self.paths.v8_path)

    def _patch_llvm(self) -> None:
        self.paths.ensure_llvm_exists()
        self.paths.ensure_path_exists(self.paths.llvm_patch_path)

        logger = self.ctx.logger
        logger.info(f"Patching LLVM with {self.paths.llvm_patch_path}")
        shell.run_cmd(f"git apply {self.paths.llvm_patch_path.absolute()}", logger, self.paths.llvm_path)

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
        # shell.run_cmd(f"git checkout -f {self.v8_commit}", logger, self.paths.v8_path)
        # shell.run_cmd(f"gclient sync", logger, self.paths.v8_path)

    def _sync_v8(self) -> None:
        self.paths.ensure_v8_exists()
        logger = self.ctx.logger
        logger.info("Syncing V8")
        self._git_checkout_and_clean(self.v8_commit, self.paths.v8_path)

        # these are the files that we patched
        # im not sure yet if there is a better way of keeping track, this feels error prone
        self._git_checkout_and_clean(".", self.paths.v8_path / "build")
        self._git_checkout_and_clean(".", self.paths.v8_path / "src" / "base")
        self._git_checkout_and_clean(".", self.paths.v8_path / "tools" / "clang")
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
        logger.info(f"Building V8 for {commit.name}")

        if self.optimize_v8:
            self._patch_v8()

        self._setup_v8_build(commit.name, commit.with_tsan)
        shell.run_cmd(f"ninja -C out/{commit.name} -t clean", logger, self.paths.v8_path)
        shell.run_cmd(f"ninja -C out/{commit.name} -j{self.build_num_cpus} d8", logger, self.paths.v8_path)

    def _relink_v8(self, commit: CommitInfo) -> None:
        self.paths.ensure_v8_exists()

        d8_path = self.paths.v8_path / "out" / commit.name / "d8"
        self.paths.ensure_path_exists(d8_path)

        logger = self.ctx.logger
        logger.info(f"Relinking V8 for {commit.name}")

        shell.run_cmd(f"rm out/{commit.name}/d8", logger, self.paths.v8_path)
        shell.run_cmd(f"ninja -C out/{commit.name} -j{self.build_num_cpus} d8", logger, self.paths.v8_path)

    def _maybe_download_mysql(self) -> None:
        self.paths.maybe_mkdir_programs()
        if self.paths.mysql_path.exists():
            return

        logger = self.ctx.logger
        if not self.mysql_download_link.endswith(".tar.gz"):
            logger.error("Expected mysql_download_link in config to end with '.tar.gz' but it doesn't. Aborting!")
            sys.exit(1)
        shell.run_cmd(f"wget {self.mysql_download_link} -O mysql.tar.gz", logger, self.paths.programs_path)
        shell.run_cmd(f"tar -xzvf mysql.tar.gz", logger, self.paths.programs_path)

        mysql_name = "mysql-server-" + self.mysql_download_link.split("/")[-1].split(".tar.gz")[0]
        mysql_path = self.paths.programs_path / mysql_name

        if not mysql_path.exists():
            logger.error(f"Expected to find {mysql_path} but it is missing. Aborting!")
            sys.exit(1)

        shutil.move(mysql_path, self.paths.mysql_path)

        mysql_tar_path = self.paths.programs_path / "mysql.tar.gz"
        mysql_tar_path.unlink()

    def _patch_mysql(self) -> None:
        self.paths.ensure_v8_exists()

        logger = self.ctx.logger
        logger.info(f"Patching V8 to optimize TSan builds with O3")

        def search_and_replace(path: Path, before: str, after: str) -> None:
            self.paths.ensure_path_exists(path)
            contents = open(path).read()
            if before not in contents:
                logger.error(f"'{before}' not found in {path}. Something must have changed in the MySQL codebase.\
                              Cannot optimize TSan build although optimize_mysql is set in the config. Aborting!")
                sys.exit(1)
            contents = contents.replace(before, after)
            open(path, "w").write(contents)

        cmakelists_path = self.paths.mysql_path / "CMakeLists.txt"
        search_and_replace(cmakelists_path,
                           'STRING_APPEND(CMAKE_C_FLAGS   " -O1 -fno-inline")',
                           '# STRING_APPEND(CMAKE_C_FLAGS   " -O1 -fno-inline")')
        search_and_replace(cmakelists_path,
                           'STRING_APPEND(CMAKE_CXX_FLAGS " -O1 -fno-inline")',
                           '# STRING_APPEND(CMAKE_CXX_FLAGS " -O1 -fno-inline")')

    def _rebuild_mysql(self, commit: CommitInfo) -> None:
        self.paths.ensure_path_exists(self.paths.mysql_path)

        logger = self.ctx.logger
        logger.info(f"Building MySQL with {commit.name}")

        downloads_path = self.paths.mysql_path / "downloads"
        usr_path = downloads_path / "usr"
        downloads_path.mkdir(exist_ok=True)
        usr_path.mkdir(exist_ok=True)

        def build_bison():
            bison_usr_path = usr_path / "bin" / "bison"
            if bison_usr_path.exists():
                return

            bison_dl_cmds = [
                "wget https://ftp.gnu.org/gnu/bison/bison-3.8.2.tar.gz",
                "tar -xzvf bison-3.8.2.tar.gz"
            ]
            bison_build_cmds = [
                "./configure --prefix=$(pwd)/../usr",
                "make -j`nproc`",
                "make install"
            ]
            bison_path = downloads_path / "bison-3.8.2"

            for cmd in bison_dl_cmds:
                shell.run_cmd_in_shell(cmd, logger, downloads_path)
            for cmd in bison_build_cmds:
                shell.run_cmd_in_shell(cmd, logger, bison_path)

        def build_openssl():
            openssl_usr_path = usr_path / "bin" / "openssl"
            if openssl_usr_path.exists():
                return

            openssl_dl_cmds = [
                "wget https://github.com/openssl/openssl/releases/download/openssl-3.0.13/openssl-3.0.13.tar.gz",
                "tar -xzvf openssl-3.0.13.tar.gz"
            ]
            openssl_build_cmds = [
                "./Configure --prefix=$(pwd)/../usr",
                "make -j`nproc`",
                "make install"
            ]
            openssl_path = downloads_path / "openssl-3.0.13"
            for cmd in openssl_dl_cmds:
                shell.run_cmd_in_shell(cmd, logger, downloads_path)
            for cmd in openssl_build_cmds:
                shell.run_cmd_in_shell(cmd, logger, openssl_path)

        def build_libtirpc():
            libtirpc_usr_path = usr_path / "lib" / "libtirpc.so"
            if libtirpc_usr_path.exists():
                return

            libtirpc_dl_cmds = [
                "wget -O libtirpc-1.3.5.tar.bz2 https://sourceforge.net/projects/libtirpc/files/libtirpc/1.3.5/libtirpc-1.3.5.tar.bz2/download",
                "tar -xf libtirpc-1.3.5.tar.bz2"
            ]
            libtirpc_build_cmds = [
                "./configure --prefix=$(pwd)/../usr --disable-gssapi",
                "make -j`nproc`",
                "make install"
            ]
            libtirpc_path = downloads_path / "libtirpc-1.3.5"
            for cmd in libtirpc_dl_cmds:
                shell.run_cmd_in_shell(cmd, logger, downloads_path)
            for cmd in libtirpc_build_cmds:
                shell.run_cmd_in_shell(cmd, logger, libtirpc_path)

        def build_patchelf():
            patchelf_usr_path = usr_path / "bin" / "patchelf"
            if patchelf_usr_path.exists():
                return

            patchelf_dl_cmds = [
                "wget https://github.com/NixOS/patchelf/releases/download/0.18.0/patchelf-0.18.0.tar.gz",
                "tar -xzvf patchelf-0.18.0.tar.gz"
            ]
            patchelf_build_cmds = [
                "./configure --prefix=$(pwd)/../usr",
                "make -j`nproc`",
                "make install"
            ]
            patchelf_path = downloads_path / "patchelf-0.18.0"
            for cmd in patchelf_dl_cmds:
                shell.run_cmd_in_shell(cmd, logger, downloads_path)
            for cmd in patchelf_build_cmds:
                shell.run_cmd_in_shell(cmd, logger, patchelf_path)

        build_bison()
        build_openssl()
        build_libtirpc()
        build_patchelf()

        self._patch_mysql()

        mysql_cmake = [
            "cmake",
            "-S", ".", "-B", f"build-{commit.name}",
            f"-DCMAKE_INSTALL_PREFIX=dist-{commit.name}", "-DWITH_TSAN=ON",
            f"-DCMAKE_C_COMPILER={self.paths.llvm_build_path.absolute()}/bin/clang",
            f"-DCMAKE_CXX_COMPILER={self.paths.llvm_build_path.absolute()}/bin/clang++",
            "-DDOWNLOAD_BOOST=1",
            "-DWITH_BOOST=downloads",
            "-DWITH_UNIT_TESTS=OFF",
            "-DINSTALL_MYSQLTESTDIR=",
            f"-DCMAKE_PREFIX_PATH={usr_path.absolute()}",
            f"-DWITH_SSL={usr_path.absolute()}"
        ]

        shell.run_cmd_list(mysql_cmake, logger, self.paths.mysql_path)

        mysql_cmake.extend([
            f"-DCMAKE_C_FLAGS='-I{usr_path.absolute()}/include -L{usr_path.absolute()}/lib -L{usr_path.absolute()}/lib64'",
            f"-DCMAKE_CXX_FLAGS='-I{usr_path.absolute()}/include -L{usr_path.absolute()}/lib -L{usr_path.absolute()}/lib64'"
        ])
        shell.run_cmd_list(mysql_cmake, logger, self.paths.mysql_path)

        shell.run_cmd(f"cmake --build build-{commit.name} -j {self.build_num_cpus}", logger, self.paths.mysql_path)
        shell.run_cmd(f"cmake --install build-{commit.name} --prefix dist-{commit.name}", logger, self.paths.mysql_path)

    def _relink_mysql(self, commit: CommitInfo) -> None:
        # TODO(dwslim): implement
        pass
