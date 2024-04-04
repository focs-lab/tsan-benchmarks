Scripts for building and running benchmarks with programs that run on multiple threads and may contain data races.

### Usage

1. Run `./setup.sh` to build all the benchmark programs.
    - Before running the script, set the `CUSTOM_LLVM_BUILD_PATH` environment variable to the path to your custom LLVM build.
    - E.g. `export CUSTOM_LLVM_BUILD_PATH=/home/daniel/llvm-project/build`
    - It should take less than 5 minutes to build everything.

2. Run `python3 runner.py` to run the test cases. It loads a list of test cases from testcases.yml.
    - You may provide arguments to choose the test set and number of iterations for each test case.
    - Usage: `python3 runner.py [test set name] [number of iterations]`
    - E.g. `python3 runner.py mini 20`

3. Results are in report.csv.
4. Modify `testcases.yml` if you want to add/remove test cases.
