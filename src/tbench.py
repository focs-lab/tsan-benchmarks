from dataclasses import dataclass
from pathlib import Path

import argparse
import logging
import sys
import yaml

import util
from util import Config, Context, Builder, Runner, Paths, enums


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
                        prog='tbench',
                        description='Run TSan Benchmarks')

    parser.add_argument('-c', '--config',
                        default=Paths.config_path,
                        help=f"Config file. Run `{parser.prog} init` to generate one in {Paths.config_path}.")

    subparsers = parser.add_subparsers(help="If none of the options are specified,\
                                             tbench will build all dependencies and benchmarks,\
                                             then run all benchmarks.",
                                       dest="cmd",
                                       required=True)
    init = subparsers.add_parser("init", help=f"Setup some boilerplate files e.g. {Paths.config_path}.")
    build = subparsers.add_parser("build", help="Build dependencies and benchmarks, e.g. LLVM and V8.")
    run = subparsers.add_parser("run", help="Run benchmarks.")
    dev = subparsers.add_parser("dev", help=f"Build benchmarks with LLVM code under development.\
                                              LLVM will be built with the chromium plugins, i.e. using the V8 toolchain.\
                                              Create a patch file with git patch, and then copy it here as {Paths.llvm_patch_path}.\
                                              Specify the LLVM version that your changes are based on in the 'dev_llvm_path' config field.")

    build_ex = build.add_mutually_exclusive_group(required=True)
    build_ex.add_argument("-n", "--name", help="Name of LLVM commit to build benchmarks for, according to the config file specified by -c.",
                          dest="build_name")
    build_ex.add_argument("-a", "--all", action="store_true", help="Build benchmarks for all LLVM commits in the config file.",
                          dest="build_all")

    run_ex = run.add_mutually_exclusive_group(required=True)
    run_ex.add_argument("-n", "--name", help="Name of LLVM commit to run benchmarks for, according to the config file specified by -c.",
                          dest="run_name")
    run_ex.add_argument("-a", "--all", action="store_true", help="Run benchmarks for all LLVM commits in the config file.",
                          dest="run_all")

    run.add_argument("-s", "--small", action="store_true", help="Run benchmarks at smaller scale for fast testing.",
                     dest="run_small")

    dev_ex = dev.add_mutually_exclusive_group(required=True)
    dev_ex.add_argument("--v8", help="Build V8.", action="store_true", dest="dev_v8")
    dev_ex.add_argument("--mysql", help="Build MySQL.", action="store_true", dest="dev_mysql")
    dev_ex.add_argument("-a", "--all", action="store_true", help="Build all benchmarks.",
                          dest="dev_all")

    dev_ex2 = dev.add_mutually_exclusive_group(required=True)
    dev_ex2.add_argument("--build", help="Will rebuild the whole codebase which takes longer.",
                         action="store_true", dest="dev_build")
    dev_ex2.add_argument("--link", help="Will only relink the built files with the modified compiler-rt which just takes seconds.",
                         action="store_true", dest="dev_link")

    init.set_defaults(handler=generate_config)
    build.set_defaults(handler=build_dependencies)
    dev.set_defaults(handler=build_dev)
    run.set_defaults(handler=run_benchmarks)
    # parser.set_defaults(handler=run_benchmarks)

    args = parser.parse_args()
    return args

def setup_logger(args: argparse.Namespace) -> logging.Logger:
    return util.logger.create_logger("main")

def parse_config(args: argparse.Namespace, logger: logging.Logger) -> Config:
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Config file {config_path} not found. Aborting!")
        sys.exit(1)
    config_dict = yaml.safe_load(open(config_path))
    config = Config.from_dict(config_dict)
    logger.info(f"Loaded configuration from {args.config}")
    config.print_with(logger.info)
    return config

def init_context() -> Context:
    args = parse_args()
    logger = setup_logger(args)
    config = parse_config(args, logger) if args.cmd != "init" else Config.defaults()
    return Context(args, config, logger)

def generate_config(ctx: Context) -> None:
    ctx.logger.info(f"Generating and saving config to {ctx.args.config}")
    config = Config.to_dict(Config.defaults())
    yaml.safe_dump(config, open(ctx.args.config, "w"))

def build_dependencies(ctx: Context):
    ctx.logger.info(f"Building dependencies in programs/ directory")

    builder_logger = util.logger.create_logger("builder")
    builder_ctx = Context(ctx.args, ctx.config, builder_logger)

    builder = Builder(builder_ctx)
    if ctx.args.build_all:
        builder.build_all()
    else:
        builder.build_one(ctx.args.build_name)

def build_dev(ctx: Context):
    ctx.logger.info(f"Building dependencies in programs/ directory using LLVM after applying patch in {Paths.llvm_patch_path}.")

    builder_logger = util.logger.create_logger("builder")
    builder_ctx = Context(ctx.args, ctx.config, builder_logger)

    builder = Builder(builder_ctx)
    build_or_link = enums.DevMode.BUILD if ctx.args.dev_build else enums.DevMode.LINK
    if ctx.args.dev_all:
        builder.dev_all(build_or_link)
    elif ctx.args.dev_v8:
        builder.dev_v8(build_or_link)
    elif ctx.args.dev_mysql:
        builder.dev_mysql(build_or_link)

def run_benchmarks(ctx: Context):
    ctx.logger.info(f"Running benchmarks")

    runner_logger = util.logger.create_logger("runner")
    runner_ctx = Context(ctx.args, ctx.config, runner_logger)
    runner = Runner(runner_ctx, ctx.args.run_small)
    if ctx.args.run_all:
        runner.run_all()
    else:
        runner.run_one(ctx.args.run_name)

def build_and_run_benchmarks(ctx: Context):
    build_dependencies(ctx)
    run_benchmarks(ctx)

def main():
    ctx = init_context()
    ctx.args.handler(ctx)


if __name__ == "__main__":
    main()
