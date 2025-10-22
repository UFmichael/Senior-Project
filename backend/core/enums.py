from strenum import StrEnum 
from enum import Enum

class LogLevels(StrEnum):
    info = "INFO"
    warn = "WARN"
    error = "ERROR"
    debug = "DEBUG"

class ThreatLevels(Enum):
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    ULTRA = 4

class ThreatStatus(StrEnum):
    ACTIVE  = "ACTIVE"
    MONITORING = "MONITORING"
    CLOSED = "CLOSED"
