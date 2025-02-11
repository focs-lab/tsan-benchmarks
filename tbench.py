from dataclasses import dataclass

import argparse
import logging
import yaml

import util
from util import Config, Context, Builder, Runner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
                        prog='tbench',
                        description='Run TSan Benchmarks')

    parser.add_argument('-c', '--config',
                        default="config.yaml",
                        help=f"Config file. Run `{parser.prog} init` to generate one in config.yaml.")

    subparsers = parser.add_subparsers(help="If none of the options are specified,\
                                             tbench will build all dependencies and benchmarks,\
                                             then run all benchmarks.",
                                       dest="cmd")
    init = subparsers.add_parser("init", help="Setup some boilerplate files e.g. config.yaml.")
    build = subparsers.add_parser("build", help="Build dependencies and benchmarks, e.g. LLVM and V8.")
    run = subparsers.add_parser("run", help="Run benchmarks.")
    
    init.set_defaults(handler=generate_config)
    build.set_defaults(handler=build_dependencies)
    run.set_defaults(handler=run_benchmarks)
    parser.set_defaults(handler=build_and_run_benchmarks)

    args = parser.parse_args()
    return args

def setup_logger(args: argparse.Namespace) -> logging.Logger:
    return util.logger.create_logger("main")

def parse_config(args: argparse.Namespace, logger: logging.Logger) -> Config:
    config_dict = yaml.safe_load(open(args.config))
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
    # TODO(dwslim): implement

def build_dependencies(ctx: Context):
    ctx.logger.info(f"Building dependencies in programs/ directory")

    builder_logger = util.logger.create_logger("builder")
    builder_ctx = Context(ctx.args, ctx.config, builder_logger)

    builder = Builder(builder_ctx)
    builder.build_all()

def run_benchmarks(ctx: Context):
    ctx.logger.info(f"Running benchmarks")

    runner_logger = util.logger.create_logger("runner")
    runner_ctx = Context(ctx.args, ctx.config, runner_logger)
    runner = Runner(runner_ctx)
    runner.run_all()

def build_and_run_benchmarks(ctx: Context):
    build_dependencies(ctx)
    run_benchmarks(ctx)

def main():
    ctx = init_context()
    ctx.args.handler(ctx)


if __name__ == "__main__":
    main()
