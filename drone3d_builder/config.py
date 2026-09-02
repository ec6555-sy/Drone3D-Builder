"""Application-wide constants and ODM quality presets."""

from pathlib import Path


DEFAULT_ODM_FOLDER = Path(r"C:\ODM")

IMAGE_EXTENSIONS = frozenset(
    {
        ".jpg",
        ".jpeg",
        ".png",
        ".tif",
        ".tiff",
        ".dng",
    }
)

QUALITY_PRESETS = {
    "빠른 생성": (
        "--feature-quality",
        "lowest",
        "--pc-quality",
        "lowest",
        "--mesh-size",
        "100000",
        "--skip-orthophoto",
    ),
    "표준": (
        "--feature-quality",
        "medium",
        "--pc-quality",
        "medium",
        "--mesh-size",
        "200000",
        "--skip-orthophoto",
    ),
    "고품질": (
        "--feature-quality",
        "high",
        "--pc-quality",
        "high",
        "--mesh-size",
        "500000",
        "--skip-orthophoto",
    ),
}

DEFAULT_QUALITY = "빠른 생성"


def get_odm_options(quality: str) -> list[str]:
    """Return a mutable ODM argument list for a named quality preset."""

    preset = QUALITY_PRESETS.get(quality, QUALITY_PRESETS["표준"])
    return list(preset)
