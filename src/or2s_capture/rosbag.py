"""rosbag2 import (stub)."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def import_rosbag2(bag: Path | str, out_dir: Path | str) -> Any:
    """Convert a ROS 2 bag into an or2s capture session.

    Not implemented in v0. Reconstruct Eng / capture lead will wire ROS2 CDR
    decoding here later. Synthetic sessions use foxglove protobuf only (no ROS).

    Raises:
        NotImplementedError: always, with a clear message.
    """
    bag = Path(bag)
    out_dir = Path(out_dir)
    raise NotImplementedError(
        "import_rosbag2 is not implemented in or2s-capture v0. "
        f"Refusing to convert {bag} → {out_dir}. "
        "Use `or2s write-synthetic` for foxglove-protobuf MCAP sessions; "
        "ROS2 CDR import will land in a later release."
    )
