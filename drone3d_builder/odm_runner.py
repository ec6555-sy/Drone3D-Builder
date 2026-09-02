"""Qt process adapter responsible for launching OpenDroneMap."""

from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, Signal

from .config import DEFAULT_ODM_FOLDER


class OdmRunner(QObject):
    """Run ODM without leaking the application's Python environment into it."""

    output_received = Signal(str)
    finished = Signal(int, object)
    error_occurred = Signal(object)

    def __init__(
        self,
        odm_folder: Path = DEFAULT_ODM_FOLDER,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.odm_folder = odm_folder
        self.run_file = odm_folder / "run.bat"

        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._process.readyReadStandardOutput.connect(self._read_output)
        self._process.finished.connect(self.finished.emit)
        self._process.errorOccurred.connect(self.error_occurred.emit)

    @property
    def is_running(self) -> bool:
        return self._process.state() != QProcess.ProcessState.NotRunning

    def start(self, project_dir: Path, options: list[str]) -> None:
        """Start an ODM reconstruction for a validated project directory."""

        environment = QProcessEnvironment.systemEnvironment()
        for variable in (
            "VIRTUAL_ENV",
            "PYTHONHOME",
            "PYTHONPATH",
            "_OLD_VIRTUAL_PATH",
            "_OLD_VIRTUAL_PROMPT",
            "_OLD_VIRTUAL_PYTHONHOME",
            "CONDA_PREFIX",
            "CONDA_DEFAULT_ENV",
            "CONDA_SHLVL",
        ):
            environment.remove(variable)

        environment.insert("ODM_NONINTERACTIVE", "1")
        self._process.setProcessEnvironment(environment)
        self._process.setWorkingDirectory(str(self.odm_folder))

        options_text = " ".join(options)
        native_arguments = (
            f'/d /s /c ""{self.run_file}" "{project_dir}" {options_text}"'
        )

        self._process.setProgram(r"C:\Windows\System32\cmd.exe")
        self._process.setNativeArguments(native_arguments)
        self._process.start()

    def _read_output(self) -> None:
        data = bytes(self._process.readAllStandardOutput())

        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("cp949", errors="replace")

        self.output_received.emit(text)
