from enum import Enum

class DevMode(Enum):
    BUILD = 1
    LINK = 2

class V8Suite(Enum):
    SunSpider = 1
    Octane = 2
    Kraken = 3
