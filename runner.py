import csv
import os
import pathlib
import statistics
import subprocess
import sys
import yaml

from dataclasses import dataclass
from typing import List


DEBUG = False
BUILT_PROGRAMS_PATH = "bin"            # where the built programs are located (currently in bin)
# REPORT_FILE_PATH = "report.csv"
# TIMEOUT = 600


@dataclass
class TestStats:
    test_name: str
    test_cmd: str
    duration: float
    memory_usage: int
    tsan_num_warnings: int
    num_locks: int
    num_accesses: int
    num_copies: int
    num_monocopies: int
    num_relacq: int

@dataclass
class TestAggStats:
    test_name: str
    test_cmd: str
    duration_mean: float
    duration_stdev: float
    duration_median: float
    memory_mean: float
    memory_stdev: float
    memory_median: float
    warnings_mean: float
    warnings_stdev: float
    warnings_median: float
    num_locks_mean: float
    num_accesses_mean: float
    num_copies_mean: float
    num_monocopies_mean: float
    num_relacq_mean: float

    def header():
        return [
            "name",
            "duration mean (s)",
            "duration stdev (s)",
            "duration median (s)",
            "memory mean (MB)",
            "memory stdev (MB)",
            "memory median (MB)",
            "warnings mean",
            "warnings stdev",
            "warnings median",
            "num locks mean",
            "num accesses mean",
            "num tc copies mean",
            "num tc monocopies mean",
            "num relacqs mean"
        ]

    def as_row(self):
        return iter(
            [
                self.test_name,
                self.duration_mean,
                self.duration_stdev,
                self.duration_median,
                self.memory_mean,
                self.memory_stdev,
                self.memory_median,
                self.warnings_mean,
                self.warnings_stdev,
                self.warnings_median,
                self.num_locks_mean,
                self.num_accesses_mean,
                self.num_copies_mean,
                self.num_monocopies_mean,
                self.num_relacq_mean
            ]
        )

def load_runtimes():
    testcases_yaml = yaml.load(open("testcases.yml"), Loader=yaml.FullLoader)
    runtimes = testcases_yaml["runtimes"]
    return runtimes


def prepare_env(rt: dict):
    # LLVM_BUILD_PATH = os.getenv("CUSTOM_LLVM_BUILD_PATH")
    # if LLVM_BUILD_PATH is None:
    #     print("[!] CUSTOM_LLVM_BUILD_PATH is not set in the environment.")
    #     print('[!] Please set $CUSTOM_LLVM_BUILD_PATH to the directory of your custom LLVM build. E.g.')
    #     print('export CUSTOM_LLVM_BUILD_PATH=/home/daniel/llvm-project/build')
    #     sys.exit(1)

    LIBOMP_LIB_PATH = rt["openmp"]
    if not pathlib.Path(LIBOMP_LIB_PATH).exists():
        print(f"[!] libomp.so is not found in the path {LIBOMP_LIB_PATH}. Please ensure that it exists before proceeding.")
        print("The following cmake command builds the TSan and OpenMP components in LLVM.")
        print('cmake -S llvm -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DLLVM_ENABLE_PROJECTS="clang" -DLLVM_ENABLE_RUNTIMES="compiler-rt;openmp" -DBUILD_SHARED_LIBS=ON -DLLVM_BINUTILS_INCDIR=/usr/include')
        sys.exit(1)

    LIBCLANGRT_LIB_PATH = rt["compiler-rt"]
    if not pathlib.Path(LIBCLANGRT_LIB_PATH).exists():
        print(f"[!] libclang_r.tsan.so is not found in the path {LIBCLANGRT_LIB_PATH}. Please ensure that it exists before proceeding.")
        print("The following cmake command builds the TSan and OpenMP components in LLVM.")
        print('cmake -S llvm -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DLLVM_ENABLE_PROJECTS="clang" -DLLVM_ENABLE_RUNTIMES="compiler-rt;openmp" -DBUILD_SHARED_LIBS=ON -DLLVM_BINUTILS_INCDIR=/usr/include')
        sys.exit(1)

    ld_library_path = os.getenv("LD_LIBRARY_PATH")
    ld_library_path_new = f"{LIBCLANGRT_LIB_PATH}:{LIBOMP_LIB_PATH}" + (":"+ld_library_path if ld_library_path is not None else "")
    os.environ["LD_LIBRARY_PATH"] = ld_library_path_new

    SYMBOLIZER_PATH = rt["symbolizer"]
    os.environ["TSAN_SYMBOLIZER_PATH"] = SYMBOLIZER_PATH


def find_zsh():
    global ZSH_PATH
    try:
        ZSH_PATH = subprocess.check_output(["which", "zsh"]).decode().strip()
    except subprocess.CalledProcessError:
        print("[!] zsh is not found on the system. It is needed for its more powerful `time` command that provide stats on memory usage.")
        print("[!] Please install it with `sudo apt install -y zsh` to proceed.")
        sys.exit(1)

def prepare_report_file(rt_name: str):
    global REPORT_FILE_PATH
    REPORT_FILE_PATH = f"report-{rt_name}.csv"

    with open(REPORT_FILE_PATH, "w") as f:
        writer = csv.writer(f)
        writer.writerow(TestAggStats.header())

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

def run_test(test, test_set_name, timeout):
    global ZSH_PATH
    assert ZSH_PATH is not None

    test_name = test["name"]
    test_cmd = test["cmd"]
    test_cleanup = test["cleanup"] if "cleanup" in test.keys() else ""
    # print(test_name, test_set_name, test_cmd)

    with subprocess.Popen(ZSH_PATH, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        # https://superuser.com/questions/480928/is-there-any-command-like-time-but-for-memory-usage
        time_report_format = b"\
TIMEFMT='=== REPORT\n'\
'%J   %U  user %S system %P cpu %E total\n'\
'real duration:             %E\n'\
'user-mode duration:        %U\n'\
'kernel duration:           %S\n'\
'cpu usage:                 %P\n'\
'avg shared (code):         %X KB\n'\
'avg unshared (data/stack): %D KB\n'\
'total (sum):               %K KB\n'\
'max memory:                %M 'MB'\n'\
'page faults from disk:     %F\n'\
'other page faults:         %R'\n"
        time_report_num_lines = time_report_format.count(b'\n') - 1

        process.stdin.write(time_report_format)
        process.stdin.write(f"cd {BUILT_PROGRAMS_PATH}/{test_set_name}\n".encode())
        process.stdin.write(f"time timeout --signal=SIGINT {timeout} {test_cmd}\n{test_cleanup}\nexit\n".encode())
        process.stdin.write(b"exit\n")
        process.stdin.close()

        output = process.stderr.read().splitlines()
        if DEBUG:
            print(b"\n".join(output).decode())
        # print(output)
        # time_report_start = output.index(b"=== REPORT")
        time_report_start = output.index(next(filter(lambda line: b"=== REPORT" in line, reversed(output))))
        time_report_lines = output[time_report_start+1:time_report_start+time_report_num_lines]
        real_duration = float(time_report_lines[1].split()[2][:-1].decode())
        # user_duration = time_report_lines[2].split()[2][:-1]
        # kernel_duration = time_report_lines[3].split()[2][:-1]
        memory_usage = int(time_report_lines[8].split()[2].decode())

        TSAN_REPORT_PREFIX = "ThreadSanitizer: reported "
        tsan_num_warnings = parse_extra_stats(TSAN_REPORT_PREFIX, output)

        num_locks = parse_extra_stats("Num Locks: ", output)
        num_accesses = parse_extra_stats("Num Accesses: ", output)
        num_copies = parse_extra_stats("Num Copies: ", output)
        num_monocopies = parse_extra_stats("Num MonoCopies: ", output)
        num_relacq = parse_extra_stats("Num relacq: ", output)

        # print("Sampling Counter:", sampling_counter)
        print("Duration:", real_duration)

        # print(b"\n".join(time_report_lines).decode())
        # print("Duration:", real_duration, "s")
        # print("Memory Usage:", memory_usage, "MB")
        # print("TSAN num warnings:", tsan_num_warnings)

        return TestStats(test_name=test_name,
                         test_cmd=test_cmd,
                         duration=real_duration,
                         memory_usage=memory_usage,
                         tsan_num_warnings=tsan_num_warnings,
                         num_locks=num_locks,
                         num_accesses=num_accesses,
                         num_copies=num_copies,
                         num_monocopies=num_monocopies,
                         num_relacq=num_relacq)

# aggregates the stats after running a test case N times
def aggregate_test_stats(tests_stats: List[TestStats]):
    duration_list = list(map(lambda ts: ts.duration, tests_stats))
    memory_usage_list = list(map(lambda ts: ts.memory_usage, tests_stats))
    tsan_num_warnings_list = list(map(lambda ts: ts.tsan_num_warnings, tests_stats))

    duration_mean = statistics.mean(duration_list)
    duration_stdev = statistics.stdev(duration_list)
    duration_median = statistics.median(duration_list)

    memory_mean = statistics.mean(memory_usage_list)
    memory_stdev = statistics.stdev(memory_usage_list)
    memory_median = statistics.median(memory_usage_list)

    warnings_mean = statistics.mean(tsan_num_warnings_list)
    warnings_stdev = statistics.stdev(tsan_num_warnings_list)
    warnings_median = statistics.median(tsan_num_warnings_list)

    num_locks_list = list(map(lambda ts: ts.num_locks, tests_stats))
    num_accesses_list = list(map(lambda ts: ts.num_accesses, tests_stats))
    num_copies_list = list(map(lambda ts: ts.num_copies, tests_stats))
    num_monocopies_list = list(map(lambda ts: ts.num_monocopies, tests_stats))
    num_relacq_list = list(map(lambda ts: ts.num_relacq, tests_stats))
    num_locks_mean = statistics.mean(num_locks_list)
    num_accesses_mean = statistics.mean(num_accesses_list)
    num_copies_mean = statistics.mean(num_copies_list)
    num_monocopies_mean = statistics.mean(num_monocopies_list)
    num_relacq_mean = statistics.mean(num_relacq_list)

    return TestAggStats(tests_stats[0].test_name,
                        tests_stats[0].test_cmd,
                        duration_mean,
                        duration_stdev,
                        duration_median,
                        memory_mean,
                        memory_stdev,
                        memory_median,
                        warnings_mean,
                        warnings_stdev,
                        warnings_median,
                        num_locks_mean,
                        num_accesses_mean,
                        num_copies_mean,
                        num_monocopies_mean,
                        num_relacq_mean)

def output_aggregate_stats(test_agg_stats: TestAggStats):
    global REPORT_FILE_PATH
    with open(REPORT_FILE_PATH, "a") as f:
        writer = csv.writer(f)
        writer.writerow(test_agg_stats.as_row())


def run_tests():
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
                test_stats = run_test(test, test_set_name, timeout)
                tests_stats.append(test_stats)

            test_agg_stats = aggregate_test_stats(tests_stats)
            output_aggregate_stats(test_agg_stats)


def main():
    find_zsh()

    runtimes = load_runtimes()
    for rt in runtimes:
        print(f"=== Using runtime [{rt['name']}] for benchmarks ===")
        print(f"OpenMP: {rt['openmp']}")
        print(f"libclang_rt: {rt['compiler-rt']}")
        print(f"llvm-symbolizer: {rt['symbolizer']}")

        prepare_env(rt)
        prepare_report_file(rt["name"])
        run_tests()

        print("=== Finished running benchmarks for this runtime ===")


if __name__ == "__main__":
    main()
