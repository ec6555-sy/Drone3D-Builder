"""Translate ODM log output into user-facing status updates."""

from dataclasses import dataclass


FATAL_KEYWORDS = (
    "traceback (most recent call last)",
    "modulenotfounderror",
    "importerror:",
    "dll load failed",
    "fatal error",
    "segmentation fault",
)


@dataclass(frozen=True)
class ProgressUpdate:
    value: int
    message: str


PROGRESS_STAGES = (
    (("detecting features", "extracting features"), 15, "사진 특징점 분석 중..."),
    (("matching",), 25, "사진 특징점 매칭 중..."),
    (("reconstruction", "opensfm"), 35, "3D 구조 계산 중..."),
    (("depthmap", "depth map"), 45, "깊이 정보 계산 중..."),
    (("point cloud", "filterpoints"), 55, "포인트 클라우드 생성 중..."),
    (("meshing", "poisson"), 70, "3D 메시 생성 중..."),
    (("texturing", "textured model"), 90, "텍스처 생성 중..."),
)


def contains_fatal_error(log_text: str) -> bool:
    """Return whether accumulated ODM output contains a fatal marker."""

    lower_log = log_text.lower()
    return any(keyword in lower_log for keyword in FATAL_KEYWORDS)


def progress_from_log(text: str) -> ProgressUpdate | None:
    """Return the latest matching progress stage in a log chunk."""

    lower_log = text.lower()
    update = None

    for keywords, value, message in PROGRESS_STAGES:
        if any(keyword in lower_log for keyword in keywords):
            update = ProgressUpdate(value, message)

    return update
