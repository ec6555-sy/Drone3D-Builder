"""Conversion of ODM textured OBJ output to a viewer-friendly GLB."""

from pathlib import Path


def convert_obj_to_windows_glb(obj_file: Path) -> Path:
    """Convert an ODM OBJ scene to a centered, standard GLB file."""

    try:
        import trimesh
    except ImportError as error:
        raise RuntimeError(
            "trimesh가 설치되어 있지 않습니다.\n\n"
            "VS Code 터미널에서 다음 명령을 실행하세요.\n"
            "python -m pip install trimesh pillow"
        ) from error

    scene = trimesh.load(
        str(obj_file),
        force="scene",
        process=False,
    )

    if scene is None:
        raise RuntimeError("OBJ 모델을 불러오지 못했습니다.")

    if len(scene.geometry) == 0:
        raise RuntimeError("OBJ 안에 3D geometry가 없습니다.")

    # GIS/drone coordinates can be too large for general-purpose 3D viewers.
    # This output is intended for viewing, so center it around the origin.
    bounds = scene.bounds
    if bounds is not None:
        center = (bounds[0] + bounds[1]) / 2.0
        translation = trimesh.transformations.translation_matrix(-center)
        scene.apply_transform(translation)

    output_glb = obj_file.parent / "Drone3D_Windows.glb"
    if output_glb.exists():
        output_glb.unlink()

    glb_data = scene.export(file_type="glb")
    with output_glb.open("wb") as file:
        file.write(glb_data)

    if not output_glb.exists():
        raise RuntimeError("GLB 파일 생성에 실패했습니다.")

    if output_glb.stat().st_size == 0:
        raise RuntimeError("생성된 GLB 파일의 크기가 0입니다.")

    return output_glb
