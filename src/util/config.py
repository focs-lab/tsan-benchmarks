from dataclasses import dataclass, asdict
from typing import Callable, Dict, List, Tuple


@dataclass
class CommitInfo:
    name: str
    commit: str
    with_tsan: bool

    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class Config:
    """Class for storing configuration fields."""
    name: str

    dev_llvm_commit: CommitInfo
    llvm_commits: List[CommitInfo]
    v8_commit: str
    v8_baseline_name: str

    optimize_v8: bool
    optimize_mysql: bool

    build_num_cpus: int

    mysql_download_link: str

    @staticmethod
    def to_dict(config: "Config") -> Dict:
        return asdict(config)

    @staticmethod
    def from_dict(d: Dict) -> "Config":
        def parse_commit_info(entry: Dict) -> CommitInfo:
            return CommitInfo(entry["name"], entry["commit"], entry["with_tsan"])

        def get_llvm_commits() -> List[CommitInfo]:
            commit_infos = []
            for entry in d["llvm_commits"]:
                commit_infos.append(parse_commit_info(entry))
            return commit_infos

        return Config(
            name=d["name"],

            dev_llvm_commit=parse_commit_info(d["dev_llvm_commit"]),
            llvm_commits=get_llvm_commits(),

            v8_commit=d["v8_commit"],
            v8_baseline_name=d["v8_baseline_name"],

            optimize_v8=d["optimize_v8"],
            optimize_mysql=d["optimize_mysql"],

            build_num_cpus=d["build_num_cpus"],
            mysql_download_link=d["mysql_download_link"])

    @staticmethod
    def defaults() -> "Config":
        return Config(
            name="Default",

            dev_llvm_commit=CommitInfo("dev", "29ed6000d21e", True),
            llvm_commits=[
                CommitInfo("llvm1", "29ed6000d21e", False),
                CommitInfo("llvm2", "20621e2", True),
            ],
            v8_commit="b595bf35aca",
            v8_baseline_name="llvm1",

            optimize_v8=True,
            optimize_mysql=True,

            build_num_cpus=64,

            mysql_download_link="https://github.com/mysql/mysql-server/archive/refs/tags/mysql-8.0.39.tar.gz"
        )

    def print_with(self, printer: Callable[[str], None]):
        printer(f"Name: {self.name}")
        # printer(f"LLVM Commit: {self.llvm_commit}")
        printer(f"V8 Commit: {self.v8_commit}")
