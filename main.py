"""Drone3D Builder launcher."""

from drone3d_builder.application import run
from drone3d_builder.main_window import Drone3DBuilder

__all__ = ["Drone3DBuilder", "run"]


if __name__ == "__main__":
    raise SystemExit(run())
