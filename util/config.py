from dataclasses import dataclass, asdict
from typing import Callable, Dict

@dataclass
class Config:
    """Class for storing configuration fields."""
    name: str
    llvm_commit: str
    v8_commit: str
    run_mysql: bool
    run_v8: bool
    build_num_cpus: int

    @staticmethod
    def to_dict(config: "Config") -> Dict:
        return asdict(config)

    @staticmethod
    def from_dict(d: Dict) -> "Config":
        return Config(
            name=d["name"],
            llvm_commit=d["llvm_commit"],
            v8_commit=d["v8_commit"],
            run_mysql=d["run_mysql"],
            run_v8=d["run_v8"],
            build_num_cpus=d["build_num_cpus"])

    @staticmethod
    def defaults() -> "Config":
        return Config(
            name="Default",
            llvm_commit="29ed6000d21e",
            v8_commit="b595bf35aca",
            run_mysql=True,
            run_v8=True,
            build_num_cpus=64
        )

    def print_with(self, printer: Callable[[str], None]):
        printer(f"Name: {self.name}")
        printer(f"LLVM Commit: {self.llvm_commit}")
        printer(f"V8 Commit: {self.v8_commit}")
