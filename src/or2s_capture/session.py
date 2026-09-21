"""Read capture sessions from disk."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from mcap.reader import make_reader
from mcap_protobuf.decoder import DecoderFactory

TOPIC_RGB = "/or2s/rgb/image"
TOPIC_CAMERA_INFO = "/or2s/rgb/camera_info"
TOPIC_POSE = "/or2s/pose"


@dataclass
class RgbFrame:
    """One RGB image message."""

    log_time_ns: int
    publish_time_ns: int
    frame_id: str
    encoding: str  # jpeg | png | rgb8 | ...
    width: int | None
    height: int | None
    data: bytes


@dataclass
class PoseSample:
    """One pose sample (device / AR trajectory)."""

    log_time_ns: int
    publish_time_ns: int
    frame_id: str
    position_m: tuple[float, float, float]
    orientation_xyzw: tuple[float, float, float, float]


@dataclass
class StreamInfo:
    name: str
    topic: str
    message_count: int
    schema_name: str | None = None


@dataclass
class Session:
    """In-memory view of a capture session directory."""

    path: Path
    manifest: dict[str, Any]
    calibration: dict[str, Any] | None = None
    provenance: dict[str, Any] | None = None
    _streams: list[StreamInfo] = field(default_factory=list)

    @property
    def session_id(self) -> str:
        return str(self.manifest.get("session_id", ""))

    @property
    def mcap_path(self) -> Path:
        rel = self.manifest.get("mcap", "session.mcap")
        return self.path / rel

    def list_streams(self) -> list[StreamInfo]:
        return list(self._streams)

    def iter_rgb(self) -> Iterator[RgbFrame]:
        yield from _iter_rgb(self.mcap_path)

    def iter_poses(self) -> Iterator[PoseSample]:
        yield from _iter_poses(self.mcap_path)

    def iter_camera_info(self) -> Iterator[Any]:
        """Yield decoded foxglove.CameraCalibration messages."""
        for _meta, proto in _iter_topic(self.mcap_path, TOPIC_CAMERA_INFO):
            yield proto


def read_session(path: Path | str) -> Session:
    """Load session sidecars and index MCAP topics.

    ``path`` is a session directory containing ``manifest.json``.
    """
    path = Path(path)
    if path.is_file() and path.name == "manifest.json":
        path = path.parent
    if path.is_file() and path.suffix == ".mcap":
        path = path.parent

    manifest_path = path / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"manifest.json not found under {path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    calibration = None
    cal_rel = manifest.get("calibration_ref", "calibration/sensors.json")
    cal_path = path / cal_rel
    if cal_path.is_file():
        calibration = json.loads(cal_path.read_text(encoding="utf-8"))

    provenance = None
    prov_rel = manifest.get("provenance_ref", "provenance/device.json")
    prov_path = path / prov_rel
    if prov_path.is_file():
        provenance = json.loads(prov_path.read_text(encoding="utf-8"))

    session = Session(
        path=path,
        manifest=manifest,
        calibration=calibration,
        provenance=provenance,
    )
    session._streams = _index_streams(session.mcap_path)
    return session


def _schema_name(schema: Any, proto: Any) -> str:
    if schema is not None and getattr(schema, "name", None):
        return str(schema.name)
    desc = getattr(type(proto), "DESCRIPTOR", None)
    if desc is not None and getattr(desc, "full_name", None):
        return str(desc.full_name)
    return type(proto).__name__


def _index_streams(mcap_path: Path) -> list[StreamInfo]:
    if not mcap_path.is_file():
        return []
    counts: dict[str, tuple[int, str | None]] = {}
    with open(mcap_path, "rb") as f:
        reader = make_reader(f, decoder_factories=[DecoderFactory()])
        for schema, channel, _message, _proto in reader.iter_decoded_messages():
            topic = channel.topic
            schema_name = schema.name if schema else None
            n, sn = counts.get(topic, (0, None))
            counts[topic] = (n + 1, sn or schema_name)

    name_by_topic = {
        TOPIC_RGB: "rgb",
        TOPIC_CAMERA_INFO: "rgb_camera_info",
        TOPIC_POSE: "pose",
    }
    return [
        StreamInfo(
            name=name_by_topic.get(topic, topic.strip("/").replace("/", "_")),
            topic=topic,
            message_count=n,
            schema_name=sn,
        )
        for topic, (n, sn) in sorted(counts.items())
    ]


def _iter_topic(mcap_path: Path, topic: str):
    with open(mcap_path, "rb") as f:
        reader = make_reader(f, decoder_factories=[DecoderFactory()])
        for schema, channel, message, proto in reader.iter_decoded_messages(
            topics=[topic]
        ):
            yield (schema, channel, message), proto


def _iter_rgb(mcap_path: Path) -> Iterator[RgbFrame]:
    for meta, proto in _iter_topic(mcap_path, TOPIC_RGB):
        schema, _channel, message = meta
        name = _schema_name(schema, proto)
        if name.endswith("CompressedImage") or "CompressedImage" in name:
            yield RgbFrame(
                log_time_ns=message.log_time,
                publish_time_ns=message.publish_time,
                frame_id=getattr(proto, "frame_id", ""),
                encoding=getattr(proto, "format", None) or "jpeg",
                width=None,
                height=None,
                data=bytes(proto.data),
            )
        elif name.endswith("RawImage") or "RawImage" in name:
            yield RgbFrame(
                log_time_ns=message.log_time,
                publish_time_ns=message.publish_time,
                frame_id=getattr(proto, "frame_id", ""),
                encoding=getattr(proto, "encoding", None) or "rgb8",
                width=int(proto.width),
                height=int(proto.height),
                data=bytes(proto.data),
            )
        else:
            data = getattr(proto, "data", b"")
            yield RgbFrame(
                log_time_ns=message.log_time,
                publish_time_ns=message.publish_time,
                frame_id=getattr(proto, "frame_id", ""),
                encoding=getattr(
                    proto, "format", getattr(proto, "encoding", "unknown")
                ),
                width=getattr(proto, "width", None),
                height=getattr(proto, "height", None),
                data=bytes(data) if data else b"",
            )


def _iter_poses(mcap_path: Path) -> Iterator[PoseSample]:
    for meta, proto in _iter_topic(mcap_path, TOPIC_POSE):
        schema, _channel, message = meta
        name = _schema_name(schema, proto)
        if "PoseInFrame" not in name:
            continue
        pos = proto.pose.position
        ori = proto.pose.orientation
        yield PoseSample(
            log_time_ns=message.log_time,
            publish_time_ns=message.publish_time,
            frame_id=proto.frame_id,
            position_m=(float(pos.x), float(pos.y), float(pos.z)),
            orientation_xyzw=(
                float(ori.x),
                float(ori.y),
                float(ori.z),
                float(ori.w),
            ),
        )
