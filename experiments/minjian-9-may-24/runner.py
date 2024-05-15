import csv
import os
import pathlib
import statistics
import subprocess
import sys
import yaml

from dataclasses import dataclass
from typing import List, Dict


DEBUG = False
# BUILT_PROGRAMS_PATH = "../../bin"            # where the built programs are located (currently in ../bin)
HAS_PERF = True
# REPORT_FILE_PATH = "report.csv"
# TIMEOUT = 600


@dataclass
class Config:
    llvm: Dict
    runtimes: List
    shared_libs: List[str]

@dataclass
class TestStats:
    test_name: str
    test_cmd: str
    duration: int
    num_warnings: int
    context_switches: int
    migrations: int
    page_faults: int
    instructions: int
    branches: int
    branch_misses: int
    l1_loads: int
    l1_load_misses: int
    llc_loads: int
    llc_load_misses: int

@dataclass
class TestAggStats:
    test_name: str
    test_cmd: str

    duration: float
    duration_stdev: float
    duration_median: float

    num_warnings: float
    num_warnings_stdev: float
    num_warnings_median: float

    context_switches: float
    context_switches_stdev: float
    migrations: float
    migrations_stdev: float
    page_faults: float
    page_faults_stdev: float
    instructions: float
    instructions_stdev: float

    branches: float
    branches_stdev: float
    branch_misses: float
    branch_misses_stdev: float
    branch_miss_rate: float
    branch_miss_rate_stdev: float

    l1_loads: float
    l1_loads_stdev: float
    l1_load_misses: float
    l1_load_misses_stdev: float
    l1_miss_rate: float
    l1_miss_rate_stdev: float

    llc_loads: float
    llc_loads_stdev: float
    llc_load_misses: float
    llc_load_misses_stdev: float
    llc_miss_rate: float
    llc_miss_rate_stdev: float

    def header():
        return [
            "name",

            "duration",
            "duration_stdev",
            "duration_median",

            "num_warnings",
            "num_warnings_stdev",
            "num_warnings_median",

            "context_switches",
            "context_switches_stdev",
            "migrations",
            "migrations_stdev",
            "page_faults",
            "page_faults_stdev",
            "instructions",
            "instructions_stdev",

            "branches",
            "branches_stdev",
            "branch_misses",
            "branch_misses_stdev",
            "branch_miss_rate",
            "branch_miss_rate_stdev",

            "l1_loads",
            "l1_loads_stdev",
            "l1_load_misses",
            "l1_load_misses_stdev",
            "l1_miss_rate",
            "l1_miss_rate_stdev",

            "llc_loads",
            "llc_loads_stdev",
            "llc_load_misses",
            "llc_load_misses_stdev",
            "llc_miss_rate",
            "llc_miss_rate_stdev"
        ]

    def as_row(self):
        return iter(
            [
                self.test_name,

                self.duration,
                self.duration_stdev,
                self.duration_median,

                self.num_warnings,
                self.num_warnings_stdev,
                self.num_warnings_median,

                self.context_switches,
                self.context_switches_stdev,
                self.migrations,
                self.migrations_stdev,
                self.page_faults,
                self.page_faults_stdev,
                self.instructions,
                self.instructions_stdev,

                self.branches,
                self.branches_stdev,
                self.branch_misses,
                self.branch_misses_stdev,
                self.branch_miss_rate,
                self.branch_miss_rate_stdev,

                self.l1_loads,
                self.l1_loads_stdev,
                self.l1_load_misses,
                self.l1_load_misses_stdev,
                self.l1_miss_rate,
                self.l1_miss_rate_stdev,

                self.llc_loads,
                self.llc_loads_stdev,
                self.llc_load_misses,
                self.llc_load_misses_stdev,
                self.llc_miss_rate,
                self.llc_miss_rate_stdev
            ]
        )

def load_config():
    global BINS_PATH
    testcases_yaml = yaml.load(open("testcases.yml"), Loader=yaml.FullLoader)
    runtimes = testcases_yaml["runtimes"]
    llvm = testcases_yaml["llvm"]
    shared_libs = testcases_yaml["shared_libs"]
    BINS_PATH = testcases_yaml["bins"]
    return Config(llvm=llvm, runtimes=runtimes, shared_libs=shared_libs)


def prepare_env(rt: Dict, llvm: Dict, shared_libs: List[str]):
    # LLVM_BUILD_PATH = os.getenv("CUSTOM_LLVM_BUILD_PATH")
    # if LLVM_BUILD_PATH is None:
    #     print("[!] CUSTOM_LLVM_BUILD_PATH is not set in the environment.")
    #     print('[!] Please set $CUSTOM_LLVM_BUILD_PATH to the directory of your custom LLVM build. E.g.')
    #     print('export CUSTOM_LLVM_BUILD_PATH=/home/daniel/llvm-project/build')
    #     sys.exit(1)

    LIBOMP_LIB_PATH = rt["openmp"]
    if not pathlib.Path(LIBOMP_LIB_PATH).joinpath("libomp.so").exists():
        print(f"[!] libomp.so is not found in the path {LIBOMP_LIB_PATH}. Please ensure that it exists before proceeding.")
        print("The following cmake command builds the TSan and OpenMP components in LLVM.")
        print('cmake -S llvm -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DLLVM_ENABLE_PROJECTS="clang" -DLLVM_ENABLE_RUNTIMES="compiler-rt;openmp" -DBUILD_SHARED_LIBS=ON -DLLVM_BINUTILS_INCDIR=/usr/include')
        sys.exit(1)

    LIBCLANGRT_LIB_PATH = rt["compiler-rt"]
    if not pathlib.Path(LIBCLANGRT_LIB_PATH).joinpath("libclang_rt.tsan.so").exists():
        print(f"[!] libclang_rt.tsan.so is not found in the path {LIBCLANGRT_LIB_PATH}. Please ensure that it exists before proceeding.")
        print("The following cmake command builds the TSan and OpenMP components in LLVM.")
        print('cmake -S llvm -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DLLVM_ENABLE_PROJECTS="clang" -DLLVM_ENABLE_RUNTIMES="compiler-rt;openmp" -DBUILD_SHARED_LIBS=ON -DLLVM_BINUTILS_INCDIR=/usr/include')
        sys.exit(1)

    LLVM_LIB_PATH = llvm["lib"]
    if not pathlib.Path(LLVM_LIB_PATH).joinpath("libLLVMOption.so.18.1").exists():
        print(f"[!] libLLVMOption.so.18.1 is not found in the path {LLVM_LIB_PATH}. llvm-symbolizer will fail with an error.")
        sys.exit(1)

    ld_library_path = os.getenv("LD_LIBRARY_PATH")
    ld_library_path_new = f"{LIBCLANGRT_LIB_PATH}:{LIBOMP_LIB_PATH}:{LLVM_LIB_PATH}:{':'.join(shared_libs)}" + (":"+ld_library_path if ld_library_path is not None else "")
    os.environ["LD_LIBRARY_PATH"] = ld_library_path_new

    SYMBOLIZER_PATH = llvm["symbolizer"]
    os.environ["TSAN_SYMBOLIZER_PATH"] = SYMBOLIZER_PATH

    # os.environ["TSAN_OPTIONS"] = "report_bugs=0 ignore_noninstrumented_modules=1"
    os.environ["TSAN_OPTIONS"] = "ignore_noninstrumented_modules=1"

def prepare_report_file(rt_name: str):
    global REPORT_FILE_PATH
    REPORT_FILE_PATH = f"report-{rt_name}.csv"

    with open(REPORT_FILE_PATH, "w") as f:
        writer = csv.writer(f)
        writer.writerow(TestAggStats.header())

def parse_perf_stats(keyword: str, output: str):
    if not HAS_PERF:
        return 1            # instead of 0 to prevent division by 0 for miss rate

    start = len(output) - 1
    while start >= 0:
        if keyword in output[start].decode():
            break
        start -= 1

    if start >= 0:
        line: str = output[start].decode()
        num = line.split()[0].replace(",", "")
        if "." in num:
            return int(float(num) * 1000)
        stat = int(num)
    else:
        stat = 0

    return stat

def parse_extra_stats(prefix: str, output: str):
    start = len(output) - 1
    while start >= 0:
        if prefix in output[start].decode():
            break
        start -= 1

    if start >= 0:
        line = output[start].decode()
        prefix_start = line.index(prefix)
        stat = int(line[prefix_start+len(prefix):].split(" ")[0])
    else:
        stat = 0

    return stat

def run_test(test, test_set_name, timeout, report_bugs=True):
    global BINS_PATH
    BASH_PATH = "/usr/bin/bash"
    # PERF_EVENTS = "{L1-dcache-loads,L1-dcache-load-misses,LLC-loads,LLC-load-misses},{branches,branch-misses},instructions,context-switches,migrations,page-faults"
    PERF_EVENTS = "instructions,context-switches"

    test_name = test["name"]
    test_cmd = test["cmd"]
    test_cmd_before = test["before"] if "before" in test.keys() else ""
    test_cleanup = test["cleanup"] if "cleanup" in test.keys() else ""

    test_env = os.environ.copy()
    if "env" in test.keys():
        for e in test["env"]:
            test_env[e["name"]] = str(e["value"])

    if "lib_paths" in test.keys():
        test_lib_paths = test["lib_paths"]
        ld_library_path = test_env["LD_LIBRARY_PATH"]
        for path in test_lib_paths:
            ld_library_path = f"{ld_library_path}:{path}"
        test_env["LD_LIBRARY_PATH"] = ld_library_path

    if not report_bugs:
        if "TSAN_OPTIONS" in test_env.keys():
            test_env["TSAN_OPTIONS"] += " report_bugs=0"
        else:
            test_env["TSAN_OPTIONS"] = "report_bugs=0"

    with subprocess.Popen(BASH_PATH, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=test_env) as process:
        perf_prefix = f"~/perf stat -e \"{PERF_EVENTS}\" " if HAS_PERF else ""

        process.stdin.write(f"cd {BINS_PATH}/{test_set_name}\n".encode())
        process.stdin.write(f"{test_cmd_before}\n".encode())
        process.stdin.write(f"{perf_prefix}timeout --signal=SIGINT {timeout} {test_cmd}\n{test_cleanup}\nexit\n".encode())
        process.stdin.write(b"exit\n")
        process.stdin.close()

        output = process.stderr.read().splitlines()
        if DEBUG:
            print(b"\n".join(output).decode())
        print(b"\n".join(output).decode())

        duration = parse_perf_stats("seconds time elapsed", output)
        context_switches = parse_perf_stats("context-switches", output)
        migrations = parse_perf_stats("migrations", output)
        page_faults = parse_perf_stats("page-faults", output)
        instructions = parse_perf_stats("instructions", output)
        branches = 1 # parse_perf_stats("  branches", output)
        branch_misses = 1 # parse_perf_stats("branch-misses", output)
        l1_loads = 1 # parse_perf_stats("L1-dcache-loads", output)
        l1_load_misses = 1 # parse_perf_stats("L1-dcache-load-misses", output)
        llc_loads = 1 # parse_perf_stats("LLC-loads", output)
        llc_load_misses = 1 # parse_perf_stats("LLC-load-misses", output)

        tsan_num_warnings = parse_extra_stats("ThreadSanitizer: reported ", output)

        print("Branches:", branches, branch_misses, branch_misses/branches)
        print("L1:", l1_loads, l1_load_misses, l1_load_misses/l1_loads)
        print("LLC:", llc_loads, llc_load_misses/llc_loads)

        return TestStats(test_name=test_name,
                         test_cmd=test_cmd,
                         duration=duration,
                         num_warnings=tsan_num_warnings,
                         context_switches=context_switches,
                         migrations=migrations,
                         page_faults=page_faults,
                         instructions=instructions,
                         branches=branches,
                         branch_misses=branch_misses,
                         l1_loads=l1_loads,
                         l1_load_misses=l1_load_misses,
                         llc_loads=llc_loads,
                         llc_load_misses=llc_load_misses)

# aggregates the stats after running a test case N times
def aggregate_test_stats(tests_stats: List[TestStats]):
    duration_list = list(map(lambda ts: ts.duration, tests_stats))
    num_warnings_list = list(map(lambda ts: ts.num_warnings, tests_stats))

    context_switches_list = list(map(lambda ts: ts.context_switches, tests_stats))
    migrations_list = list(map(lambda ts: ts.migrations, tests_stats))
    page_faults_list = list(map(lambda ts: ts.page_faults, tests_stats))
    instructions_list = list(map(lambda ts: ts.instructions, tests_stats))

    branches_list = list(map(lambda ts: ts.branches, tests_stats))
    branch_misses_list = list(map(lambda ts: ts.branch_misses, tests_stats))
    l1_loads_list = list(map(lambda ts: ts.l1_loads, tests_stats))
    l1_load_misses_list = list(map(lambda ts: ts.l1_load_misses, tests_stats))
    llc_loads_list = list(map(lambda ts: ts.llc_loads, tests_stats))
    llc_load_misses_list = list(map(lambda ts: ts.llc_load_misses, tests_stats))

    duration_mean = statistics.mean(duration_list)
    duration_stdev = statistics.stdev(duration_list)
    duration_median = statistics.median(duration_list)

    num_warnings_mean = statistics.mean(num_warnings_list)
    num_warnings_stdev = statistics.stdev(num_warnings_list)
    num_warnings_median = statistics.median(num_warnings_list)

    context_switches_mean = statistics.mean(context_switches_list)
    context_switches_stdev = statistics.stdev(context_switches_list)
    migrations_mean = statistics.mean(migrations_list)
    migrations_stdev = statistics.stdev(migrations_list)
    page_faults_mean = statistics.mean(page_faults_list)
    page_faults_stdev = statistics.stdev(page_faults_list)
    instructions_mean = statistics.mean(instructions_list)
    instructions_stdev = statistics.stdev(instructions_list)

    branches_mean = statistics.mean(branches_list)
    branches_stdev = statistics.stdev(branches_list)
    branch_misses_mean = statistics.mean(branch_misses_list)
    branch_misses_stdev = statistics.stdev(branch_misses_list)
    branch_miss_rates_list = [miss/full for full,miss in zip(branches_list, branch_misses_list)]
    branch_miss_rates_mean = statistics.mean(branch_miss_rates_list)
    branch_miss_rates_stdev = statistics.stdev(branch_miss_rates_list)

    l1_loads_mean = statistics.mean(l1_loads_list)
    l1_loads_stdev = statistics.stdev(l1_loads_list)
    l1_misses_mean = statistics.mean(l1_load_misses_list)
    l1_misses_stdev = statistics.stdev(l1_load_misses_list)
    l1_miss_rates_list = [miss/full for full,miss in zip(l1_loads_list, l1_load_misses_list)]
    l1_miss_rates_mean = statistics.mean(l1_miss_rates_list)
    l1_miss_rates_stdev = statistics.stdev(l1_miss_rates_list)

    llc_loads_mean = statistics.mean(llc_loads_list)
    llc_loads_stdev = statistics.stdev(llc_loads_list)
    llc_misses_mean = statistics.mean(llc_load_misses_list)
    llc_misses_stdev = statistics.stdev(llc_load_misses_list)
    llc_miss_rates_list = [miss/full for full,miss in zip(llc_loads_list, llc_load_misses_list)]
    llc_miss_rates_mean = statistics.mean(llc_miss_rates_list)
    llc_miss_rates_stdev = statistics.stdev(llc_miss_rates_list)


    return TestAggStats(tests_stats[0].test_name,
                        tests_stats[0].test_cmd,
                        duration=duration_mean,
                        duration_stdev=duration_stdev,
                        duration_median=duration_median,

                        num_warnings=num_warnings_mean,
                        num_warnings_stdev=num_warnings_stdev,
                        num_warnings_median=num_warnings_median,

                        context_switches=context_switches_mean,
                        context_switches_stdev=context_switches_stdev,
                        migrations=migrations_mean,
                        migrations_stdev=migrations_stdev,
                        page_faults=page_faults_mean,
                        page_faults_stdev=page_faults_stdev,
                        instructions=instructions_mean,
                        instructions_stdev=instructions_stdev,

                        branches=branches_mean,
                        branches_stdev=branches_stdev,
                        branch_misses=branch_misses_mean,
                        branch_misses_stdev=branch_misses_stdev,
                        branch_miss_rate=branch_miss_rates_mean,
                        branch_miss_rate_stdev=branch_miss_rates_stdev,

                        l1_loads=l1_loads_mean,
                        l1_loads_stdev=l1_loads_stdev,
                        l1_load_misses=l1_misses_mean,
                        l1_load_misses_stdev=l1_misses_stdev,
                        l1_miss_rate=l1_miss_rates_mean,
                        l1_miss_rate_stdev=l1_miss_rates_stdev,

                        llc_loads=llc_loads_mean,
                        llc_loads_stdev=llc_loads_stdev,
                        llc_load_misses=llc_misses_mean,
                        llc_load_misses_stdev=llc_misses_stdev,
                        llc_miss_rate=llc_miss_rates_mean,
                        llc_miss_rate_stdev=llc_miss_rates_stdev)

def output_aggregate_stats(test_agg_stats: TestAggStats):
    global REPORT_FILE_PATH
    with open(REPORT_FILE_PATH, "a") as f:
        writer = csv.writer(f)
        writer.writerow(test_agg_stats.as_row())


def run_tests(report_bugs=True):
    testcases_yaml = yaml.load(open("testcases.yml"), Loader=yaml.FullLoader)
    testcases = testcases_yaml["tests"]
    testcases_categories = list(testcases.keys())
    print("[*] Loaded testcases from testcases.yml")

    # choose test category (small, medium, large, etc)
    if len(testcases_categories) == 0:
        print('[!] Testcases are either empty or malformed. Please check!')
        sys.exit(1)

    if len(sys.argv) < 2:
        category = testcases_categories[0]
    elif sys.argv[1] in testcases_categories:
        category = sys.argv[1]
    elif sys.argv[1].isdigit():
        category = testcases_categories[int(sys.argv[1])]
    else:
        print(f"[!] Unknown category specified: {sys.argv[1]}.")
        sys.exit(1)

    # choose number of iterations for each test case
    if len(sys.argv) < 3:
        test_num_iters = 10
    else:
        try:
            test_num_iters = int(sys.argv[2])
        except ValueError:
            print(f"[!] Invalid number of test iterations: {sys.argv[2]}")
            sys.exit(1)

    timeout = int(testcases[category]["timeout"])
    print(f"[*] Running **{category}** test cases")
    print(f"[*] Running each test case {test_num_iters} times")
    print(f"[*] Timeout: {timeout}s")
    testcases = testcases[category]["tests"]
    for test_set in testcases:
        test_set_name = test_set["name"]
        tests = test_set["tests"]

        print(f"[**] Running tests under {test_set_name}")
        for test in tests:
            tests_stats: List[TestStats] = []
            for _ in range(test_num_iters):
                test_stats = run_test(test, test_set_name, timeout, report_bugs)
                tests_stats.append(test_stats)

            test_agg_stats = aggregate_test_stats(tests_stats)
            output_aggregate_stats(test_agg_stats)


def main():
    config = load_config()
    for rt in config.runtimes:
        print(f"=== Using runtime [{rt['name']}] for benchmarks ===")
        print(f"OpenMP: {rt['openmp']}")
        print(f"libclang_rt: {rt['compiler-rt']}")
        print(f"llvm-symbolizer: {config.llvm['symbolizer']}")

        prepare_env(rt, config.llvm, config.shared_libs)
        prepare_report_file(rt["name"])
        run_tests()
        prepare_report_file(rt["name"]+"-no-report-bugs")
        run_tests(False)

        print("=== Finished running benchmarks for this runtime ===")


if __name__ == "__main__":
    main()
