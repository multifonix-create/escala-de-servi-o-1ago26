from dataclasses import dataclass
from datetime import time


@dataclass(frozen=True)
class ServiceTimeWindow:
    code: str
    start_time: time
    end_time: time
    crosses_midnight: bool = False


SERVICE_TIME_WINDOWS = {
    "AT1": ServiceTimeWindow("AT1", time(0, 0), time(8, 0)),
    "AT2": ServiceTimeWindow("AT2", time(8, 0), time(16, 0)),
    "AT3": ServiceTimeWindow("AT3", time(16, 0), time(0, 0), crosses_midnight=True),
    "PO1": ServiceTimeWindow("PO1", time(0, 0), time(8, 0)),
    "PO2": ServiceTimeWindow("PO2", time(8, 0), time(16, 0)),
    "PO3": ServiceTimeWindow("PO3", time(16, 0), time(0, 0), crosses_midnight=True),
}

COVERAGE_TARGETS = {
    "AT1": 1,
    "AT2": 1,
    "AT3": 1,
    "PO1": 2,
    "PO2": 2,
    "PO3": 2,
}
