"""ODM project-folder and source-image helpers."""

from pathlib import Path

from .config import IMAGE_EXTENSIONS


def find_images_directory(selected_folder: Path) -> Path:
    """Resolve the folder whose images should be counted in the UI."""

    if selected_folder.name.lower() == "images":
        return selected_folder

    images_folder = selected_folder / "images"
    return images_folder if images_folder.is_dir() else selected_folder


def find_project_directory(selected_folder: Path) -> Path | None:
    """Resolve an ODM project root from a project or images directory."""

    if selected_folder.name.lower() == "images":
        return selected_folder.parent

    if (selected_folder / "images").is_dir():
        return selected_folder

    return None


def count_source_images(images_folder: Path) -> int:
    """Count supported image files directly inside a directory."""

    return sum(
        1
        for file in images_folder.iterdir()
        if file.is_file() and file.suffix.lower() in IMAGE_EXTENSIONS
    )
