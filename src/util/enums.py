from enum import Enum

class DevMode(Enum):
    BUILD = 1
    LINK = 2

class Target(Enum):
    ALL = 1
    V8 = 2
    MYSQL = 3

class V8Suite(Enum):
    SunSpider = 1
    Octane = 2
    Kraken = 3
