from dataclasses import dataclass
from typing import Callable, Dict

@dataclass
class Config:
    """Class for storing configuration fields."""
    name: str

    @staticmethod
    def from_dict(d: Dict) -> "Config":
        return Config(d["name"])
    
    @staticmethod
    def defaults() -> "Config":
        return Config(
            name="Default"
        )

    def print_with(self, printer: Callable[[str], None]):
        printer(f"name: {self.name}")
