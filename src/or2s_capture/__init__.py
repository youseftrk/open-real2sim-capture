"""or2s_capture — Open Real2Sim capture bag (MCAP) stub."""

from __future__ import annotations

from or2s_capture.rosbag import import_rosbag2
from or2s_capture.session import Session, read_session
from or2s_capture.validate import Report, validate
from or2s_capture.write import write_synthetic_session

__all__ = [
    "Report",
    "Session",
    "import_rosbag2",
    "read_session",
    "validate",
    "write_synthetic_session",
]

__version__ = "0.1.0"
