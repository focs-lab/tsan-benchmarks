# tbench

Short for ThreadSanitizer Benchmarks.

This is a tool that orchestrates the building and running of programs for comparing performance after making changes to TSan.
Currently this tool only supports building V8 and running the SunSpider, Octane and Kraken benchmarks on it.
MySQL with BenchBase is now WIP.

## Installation

Clone this repo and install.

```
pip3 install .
```

## Usage

This guide assumes that it is your first time using tbench.

### init

First, create a new folder. This will be for tbench to store all of the necessary files and generated reports.

In the folder, run `tbench init` to generate a default config file. You will most likely want to modify it.
Below are explanations of the fields:

- `name`: Just a name for this config. It's not really used anywhere, just attached in the report.
- `build_num_cpus`: Number of CPUs for building programs e.g. LLVM. It is recommended to not set this too high or your machine might hang.
- `llvm_commits`: This provides information about versions of LLVM that should be built for building the benchmark programs. `commit` is the LLVM commit hash, the length doesn't matter as long as it is accepted by `git checkout`. `name` is for identifying this LLVM version in subsequent commands and the report. `with_tsan` tells tbench whether the programs built with this LLVM build should be built with TSan or not.
- `dev_llvm_commit`: This is useful if you are modifying LLVM/TSan and want to run the benchmarks as you make changes. `commit` is the commit hash of the version that you are modifying. `name` is for identifying your modified version. `with_tsan` is for whether the programs should be built with TSan.
- `optimize_v8`: By default, V8 without TSan is not built under the same optimization level as V8 with TSan. V8 with TSan also turns on some macros that lets it run some extra code. Set this to true if you want your build of V8 to use TSan while also using the same optimizations as without TSan and also disable the extra code.
- `v8_baseline_name`: The name of the LLVM version used to build the baseline version of V8. This is for comparing the results during report generation.
- `v8_commit`: The commit hash of V8 used for the benchmarks.
- `run_v8`/`run_mysql`: Set this to false if you want V8/MySQL to be skipped while building and running benchmarks. Perhaps more useful only when we support more benchmarks.

### Build

```
$ tbench build -h
usage: tbench build [-h] (-n BUILD_NAME | -a)

options:
  -h, --help            show this help message and exit
  -n BUILD_NAME, --name BUILD_NAME
                        Name of LLVM commit to build benchmarks for, according to the config file specified by -c.
  -a, --all             Build benchmarks for all LLVM commits in the config file.
```

After confirming the fields in the config file, run `tbench build -a` to build the benchmark programs with all LLVM versions specified in the config file.

If you only want to build benchmarks for a specific LLVM version, you can specify it with `tbench build -n <name>`. This is useful when you add or modify a LLVM version in the config.

### Run

```
$ tbench run -h
usage: tbench run [-h] (-n RUN_NAME | -a) [-s]

options:
  -h, --help            show this help message and exit
  -n RUN_NAME, --name RUN_NAME
                        Name of LLVM commit to run benchmarks for, according to the config file specified by -c.
  -a, --all             Run benchmarks for all LLVM commits in the config file.
  -s, --small           Run benchmarks at smaller scale for fast testing.
```

After building the benchmark programs, you can run them with `tbench run -a`.
You can specify a specific LLVM version with `tbench run -n <name>`.
You might use this often because you might not want to run those benchmarks that have already been ran once before.

### Dev

```
tbench dev -h
usage: tbench dev [-h] (--v8 | --mysql | -a) (--build | --link)

options:
  -h, --help  show this help message and exit
  --v8        Build V8.
  --mysql     Build MySQL.
  -a, --all   Build all benchmarks.
  --build     Will rebuild the whole codebase which takes longer.
  --link      Will only relink the built files with the modified compiler-rt which just takes seconds.
```

There is also a convenient `tbench dev` command that allows very quickly rebuilding benchmarks with your changes to LLVM.
To use this mode, you need to specify the LLVM version that you are modifying, in the `dev_llvm_commit` field of the config file.
You will also need to provide a patch file containing your changes in a file named `llvm.patch`.


Here are instructions for generating the patch file in the llvm-project folder.

```
git add .
git diff --cached > llvm.patch
git restore --staged .
```

With the patch file, you can now trigger a very fast rebuild.
If you have only modified `compiler-rt`, you can specify the `--link` option so that only the final executable is relinked,
since compiler-rt is only linked to the program at the end of the build process, and doesn't affect the compilation of the rest of the program.
If you modified other parts of LLVM like the instrumentation pass itself, then you would want to specify the `--build` option to
rebuild every single source file so that your changes to the instrumentation are applied throughout the whole program.

If it is your first time building the dev version, you must specify the `--build` option, otherwise with `--link` it will fail with an error,
because the CMakeFile

TODO:
- first time running dev doesnt work because llvm might not have been setup
- run dev version if it exists, but dont error if it doesnt



## Troubleshooting

If `tbench build` times out while downloading some dependencies because it got stuck, it is better to remove everything and start over.

Remove the faulty folder and run `tbench build` again.

```
rm -r programs/v8/third_party/llvm
rm -r programs/v8/third_party/llvm-build
rm -r programs/v8/third_party/llvm-build-tools
```

