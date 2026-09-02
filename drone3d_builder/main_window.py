"""Main Qt window and user-interaction orchestration."""

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .config import DEFAULT_QUALITY, QUALITY_PRESETS, get_odm_options
from .glb_converter import convert_obj_to_windows_glb
from .odm_runner import OdmRunner
from .progress import contains_fatal_error, progress_from_log
from .project import count_source_images, find_images_directory, find_project_directory


class Drone3DBuilder(QMainWindow):
    """Coordinate the UI, ODM runner, and model conversion services."""

    def __init__(self) -> None:
        super().__init__()

        self.current_project_dir: Path | None = None
        self.generated_model: Path | None = None
        self.odm_had_fatal_error = False
        self.odm_log_text = ""

        self.odm_runner = OdmRunner(parent=self)
        self.odm_runner.output_received.connect(self._read_odm_output)
        self.odm_runner.finished.connect(self._odm_finished)
        self.odm_runner.error_occurred.connect(self._odm_error)

        self._build_ui()

    def _build_ui(self) -> None:
        self.setWindowTitle("Drone3D Builder")
        self.resize(1000, 800)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        title = QLabel("Drone3D Builder")
        title.setStyleSheet("font-size: 26px; font-weight: bold;")
        layout.addWidget(title)
        layout.addWidget(QLabel("드론 사진을 이용하여 3D 모델을 자동 생성하고 확인합니다."))

        layout.addWidget(QLabel("드론 사진 폴더"))
        folder_layout = QHBoxLayout()
        self.folder_input = QLineEdit()
        self.folder_input.setPlaceholderText(
            "ODM 프로젝트 폴더 또는 images 폴더를 선택하세요."
        )
        folder_button = QPushButton("폴더 선택")
        folder_button.clicked.connect(self._select_folder)
        folder_layout.addWidget(self.folder_input)
        folder_layout.addWidget(folder_button)
        layout.addLayout(folder_layout)

        self.image_count_label = QLabel("사진: 0장")
        layout.addWidget(self.image_count_label)

        layout.addWidget(QLabel("3D 생성 품질"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(list(QUALITY_PRESETS))
        self.quality_combo.setCurrentText(DEFAULT_QUALITY)
        layout.addWidget(self.quality_combo)

        self.start_button = QPushButton("3D 생성 시작")
        self.start_button.setMinimumHeight(45)
        self.start_button.clicked.connect(self._start_generation)
        layout.addWidget(self.start_button)

        layout.addWidget(QLabel("진행률"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("대기 중")
        layout.addWidget(self.status_label)

        layout.addWidget(QLabel("ODM 작업 로그"))
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(270)
        layout.addWidget(self.log_view)

        layout.addWidget(QLabel("3D 모델 파일"))
        model_layout = QHBoxLayout()
        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText("생성된 GLB 또는 OBJ 파일")
        self.model_input.setReadOnly(True)
        model_select_button = QPushButton("3D 모델 선택")
        model_select_button.clicked.connect(self._select_model)
        model_layout.addWidget(self.model_input)
        model_layout.addWidget(model_select_button)
        layout.addLayout(model_layout)

        self.open_model_button = QPushButton("3D 모델 열기")
        self.open_model_button.setMinimumHeight(45)
        self.open_model_button.clicked.connect(self._open_model)
        layout.addWidget(self.open_model_button)

    def _select_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "드론 사진 폴더 선택")
        if not folder:
            return

        selected_folder = Path(folder)
        self.folder_input.setText(str(selected_folder))
        images_folder = find_images_directory(selected_folder)

        try:
            image_count = count_source_images(images_folder)
        except Exception as error:
            QMessageBox.critical(self, "폴더 오류", str(error))
            return

        self.image_count_label.setText(f"사진: {image_count}장")
        self.status_label.setText("사진 폴더 선택 완료")

    def _selected_project_directory(self) -> Path | None:
        folder_text = self.folder_input.text().strip()
        if not folder_text:
            return None

        return find_project_directory(Path(folder_text))

    def _start_generation(self) -> None:
        if self.odm_runner.is_running:
            QMessageBox.warning(self, "작업 중", "현재 3D 생성 작업이 진행 중입니다.")
            return

        if not self.odm_runner.run_file.exists():
            QMessageBox.critical(
                self,
                "ODM 없음",
                f"{self.odm_runner.run_file} 파일을 찾을 수 없습니다.",
            )
            return

        project_dir = self._selected_project_directory()
        if project_dir is None:
            QMessageBox.warning(
                self,
                "폴더 구조 확인",
                "ODM 프로젝트 구조가 아닙니다.\n\n"
                "예:\n"
                "ODM-TEST-SMALL\n"
                "└─ images\n"
                "   ├─ DJI_0001.JPG\n"
                "   └─ DJI_0002.JPG",
            )
            return

        self.current_project_dir = project_dir
        self.generated_model = None
        self.odm_had_fatal_error = False
        self.odm_log_text = ""

        self.log_view.clear()
        self.progress_bar.setValue(5)
        self.status_label.setText("ODM 시작 준비 중...")
        self.start_button.setEnabled(False)

        quality = self.quality_combo.currentText()
        self.log_view.append("========== ODM 실행 시작 ==========")
        self.log_view.append(f"프로젝트: {project_dir}")
        self.log_view.append(f"품질: {quality}")
        self.log_view.append("")

        self.odm_runner.start(project_dir, get_odm_options(quality))
        self.status_label.setText("ODM 실행 중...")

    def _read_odm_output(self, text: str) -> None:
        self.odm_log_text += text
        self.log_view.insertPlainText(text)

        scrollbar = self.log_view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

        if contains_fatal_error(self.odm_log_text):
            self.odm_had_fatal_error = True
            self.status_label.setText("3D 생성 오류 발생")
            return

        update = progress_from_log(text)
        if update is not None:
            self._set_progress(update.value, update.message)

    def _set_progress(self, value: int, message: str) -> None:
        if value > self.progress_bar.value():
            self.progress_bar.setValue(value)
        self.status_label.setText(message)

    def _odm_finished(self, exit_code: int, exit_status: object) -> None:
        del exit_status  # The numeric exit code carries the result used by the UI.
        self.start_button.setEnabled(True)

        if self.odm_had_fatal_error:
            self.status_label.setText("3D 생성 실패")
            QMessageBox.critical(self, "ODM 작업 실패", "ODM 실행 중 오류가 발생했습니다.")
            return

        if exit_code != 0:
            self.status_label.setText("3D 생성 실패")
            QMessageBox.critical(self, "ODM 작업 실패", f"ODM 종료 코드: {exit_code}")
            return

        if self.current_project_dir is None:
            self.status_label.setText("프로젝트 폴더 없음")
            QMessageBox.critical(self, "ODM 작업 실패", "프로젝트 폴더 정보를 찾지 못했습니다.")
            return

        obj_file = (
            self.current_project_dir
            / "odm_texturing"
            / "odm_textured_model_geo.obj"
        )
        if not obj_file.exists():
            self.status_label.setText("OBJ 파일 없음")
            QMessageBox.warning(
                self,
                "OBJ 파일 없음",
                "ODM 작업은 끝났지만 텍스처 OBJ 파일을 찾지 못했습니다.\n\n"
                f"예상 경로:\n{obj_file}",
            )
            return

        self.log_view.append("")
        self.log_view.append("========== Windows GLB 변환 시작 ==========")
        self.log_view.append(f"OBJ: {obj_file}")
        self.status_label.setText("Windows 호환 GLB 변환 중...")
        self.progress_bar.setValue(96)

        try:
            windows_glb = convert_obj_to_windows_glb(obj_file)
        except Exception as error:
            self.generated_model = obj_file
            self.model_input.setText(str(obj_file))
            self.progress_bar.setValue(95)
            self.status_label.setText("GLB 변환 실패 - OBJ 사용 가능")
            QMessageBox.warning(
                self,
                "GLB 변환 실패",
                "ODM 3D 모델은 생성됐지만 Windows용 GLB 변환에 실패했습니다.\n\n"
                f"{error}\n\n"
                "OBJ 파일은 사용할 수 있습니다.",
            )
            return

        self.log_view.append(f"Windows GLB 생성 완료: {windows_glb}")
        self.generated_model = windows_glb
        self.model_input.setText(str(windows_glb))
        self.progress_bar.setValue(100)
        self.status_label.setText("3D 생성 완료")
        self.log_view.append("")
        self.log_view.append("========== 전체 작업 완료 ==========")
        self.log_view.append(f"최종 GLB: {windows_glb}")
        QMessageBox.information(
            self,
            "3D 생성 완료",
            "3D 모델 생성과 Windows용 GLB 변환이 완료됐습니다.\n\n"
            f"최종 파일:\n{windows_glb}\n\n"
            "'3D 모델 열기' 버튼으로 확인해주세요.",
        )

    def _odm_error(self, error: object) -> None:
        self.start_button.setEnabled(True)
        self.status_label.setText("ODM 실행 오류")
        QMessageBox.critical(self, "ODM 실행 오류", f"오류 코드: {error}")

    def _select_model(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "3D 모델 선택",
            "",
            "3D Model (*.glb *.gltf *.obj);;모든 파일 (*.*)",
        )
        if not file_path:
            return

        self.model_input.setText(file_path)
        self.status_label.setText("3D 모델 선택 완료")

    def _open_model(self) -> None:
        model_path = self.model_input.text().strip()
        if not model_path:
            QMessageBox.warning(self, "3D 모델 없음", "먼저 3D 모델을 선택해주세요.")
            return

        path = Path(model_path)
        if not path.exists():
            QMessageBox.critical(self, "파일 없음", "3D 모델 파일을 찾을 수 없습니다.")
            return

        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
            QMessageBox.critical(self, "실행 실패", "3D 모델을 열 수 없습니다.")
            return

        self.status_label.setText("3D 모델 열기 완료")
