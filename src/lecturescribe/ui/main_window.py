"""Main window for the LectureScribe desktop application."""

from __future__ import annotations

from PySide6.QtCore import QObject, QSize, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from lecturescribe import __app_name__
from lecturescribe.audio import AudioDevice, AudioSource, list_audio_devices
from lecturescribe.transcription import TranscriptEvent
from lecturescribe.transcription.realtime_client import TranscriptEventType
from lecturescribe.transcription.session import TranscriptionSession

WINDOW_STYLESHEET = """
QMainWindow {
    background-color: #101828;
}
QLabel {
    color: #d0d5dd;
    font-size: 14px;
}
QLabel#TitleLabel {
    color: #f9fafb;
    font-size: 28px;
    font-weight: 700;
}
QLabel#SubtitleLabel {
    color: #98a2b3;
    font-size: 14px;
}
QLabel#TimerLabel {
    color: #f9fafb;
    font-size: 24px;
    font-weight: 700;
}
QFrame#Panel {
    background-color: #182230;
    border: 1px solid #344054;
    border-radius: 18px;
}
QFrame#StatusDot {
    background-color: #667085;
    border-radius: 7px;
    min-width: 14px;
    max-width: 14px;
    min-height: 14px;
    max-height: 14px;
}
QFrame#StatusDot[recording="true"] {
    background-color: #f04438;
}
QComboBox, QTextEdit {
    background-color: #0c111d;
    border: 1px solid #344054;
    border-radius: 10px;
    color: #f9fafb;
    padding: 10px;
    selection-background-color: #175cd3;
}
QComboBox::drop-down {
    border: 0;
    width: 28px;
}
QTextEdit {
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 15px;
}
QPushButton {
    border: 0;
    border-radius: 10px;
    color: #ffffff;
    font-size: 14px;
    font-weight: 700;
    padding: 11px 18px;
}
QPushButton#StartButton {
    background-color: #1570ef;
}
QPushButton#StartButton:hover {
    background-color: #175cd3;
}
QPushButton#StopButton {
    background-color: #d92d20;
}
QPushButton#StopButton:hover {
    background-color: #b42318;
}
QPushButton#SecondaryButton {
    background-color: #344054;
}
QPushButton#SecondaryButton:hover {
    background-color: #475467;
}
QPushButton:disabled {
    background-color: #263241;
    color: #667085;
}
"""


class _TranscriptionSignals(QObject):
    transcript = Signal(object)
    error = Signal(object)


class MainWindow(QMainWindow):
    """Primary LectureScribe application window."""

    def __init__(self) -> None:
        super().__init__()
        self._elapsed_seconds = 0
        self._recording = False
        self._devices: list[AudioDevice] = []
        self._session: TranscriptionSession | None = None
        self._signals = _TranscriptionSignals()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_elapsed_time)

        self.setWindowTitle(__app_name__)
        self.setMinimumSize(QSize(1040, 720))
        self.setStyleSheet(WINDOW_STYLESHEET)

        self._build_ui()
        self._connect_signals()
        self._set_recording_state(False)
        self._load_audio_devices()

    def _build_ui(self) -> None:
        root = QWidget(self)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(32, 28, 32, 32)
        root_layout.setSpacing(24)

        title = QLabel(__app_name__)
        title.setObjectName("TitleLabel")
        subtitle = QLabel("Realtime lecture transcription workspace")
        subtitle.setObjectName("SubtitleLabel")

        header = QVBoxLayout()
        header.setSpacing(4)
        header.addWidget(title)
        header.addWidget(subtitle)
        root_layout.addLayout(header)

        controls_panel = self._create_panel()
        controls_layout = QGridLayout(controls_panel)
        controls_layout.setContentsMargins(22, 22, 22, 22)
        controls_layout.setHorizontalSpacing(18)
        controls_layout.setVerticalSpacing(14)

        self.audio_source_selector = QComboBox()
        self.audio_source_selector.addItem("Microphone", AudioSource.MICROPHONE.value)
        self.audio_source_selector.addItem("System Audio (Loopback)", AudioSource.LOOPBACK.value)
        self.audio_device_selector = QComboBox()

        controls_layout.addWidget(QLabel("Audio source"), 0, 0)
        controls_layout.addWidget(QLabel("Audio device"), 0, 1)
        controls_layout.addWidget(self.audio_source_selector, 1, 0)
        controls_layout.addWidget(self.audio_device_selector, 1, 1)

        self.start_button = QPushButton("Start")
        self.start_button.setObjectName("StartButton")
        self.stop_button = QPushButton("Stop")
        self.stop_button.setObjectName("StopButton")
        button_row = QHBoxLayout()
        button_row.setSpacing(10)
        button_row.addWidget(self.start_button)
        button_row.addWidget(self.stop_button)
        controls_layout.addLayout(button_row, 1, 2)

        self.status_dot = QFrame()
        self.status_dot.setObjectName("StatusDot")
        self.status_label = QLabel("Ready")
        self.timer_label = QLabel("00:00:00")
        self.timer_label.setObjectName("TimerLabel")

        status_row = QHBoxLayout()
        status_row.setSpacing(10)
        status_row.addWidget(self.status_dot)
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        status_row.addWidget(QLabel("Recording time"))
        status_row.addWidget(self.timer_label)
        controls_layout.addLayout(status_row, 2, 0, 1, 3)

        controls_layout.setColumnStretch(0, 1)
        controls_layout.setColumnStretch(1, 1)
        controls_layout.setColumnStretch(2, 0)
        root_layout.addWidget(controls_panel)

        transcript_panel = self._create_panel()
        transcript_layout = QVBoxLayout(transcript_panel)
        transcript_layout.setContentsMargins(22, 22, 22, 22)
        transcript_layout.setSpacing(14)

        transcript_header = QHBoxLayout()
        transcript_title = QLabel("Transcript")
        transcript_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.export_button = QPushButton("Export")
        self.export_button.setObjectName("SecondaryButton")
        self.clear_button = QPushButton("Clear")
        self.clear_button.setObjectName("SecondaryButton")
        transcript_header.addWidget(transcript_title)
        transcript_header.addStretch()
        transcript_header.addWidget(self.export_button)
        transcript_header.addWidget(self.clear_button)

        self.transcript_area = QTextEdit()
        self.transcript_area.setPlaceholderText(
            "Transcript text will appear here once audio capture and transcription are implemented."
        )
        self.transcript_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        transcript_layout.addLayout(transcript_header)
        transcript_layout.addWidget(self.transcript_area)
        root_layout.addWidget(transcript_panel, stretch=1)

        self.setCentralWidget(root)

    def _connect_signals(self) -> None:
        self.start_button.clicked.connect(self._start_transcription)
        self.stop_button.clicked.connect(self._stop_transcription)
        self.audio_source_selector.currentIndexChanged.connect(self._refresh_device_selector)
        self._signals.transcript.connect(self._handle_transcript)
        self._signals.error.connect(self._handle_error)
        self.clear_button.clicked.connect(self.transcript_area.clear)
        self.export_button.clicked.connect(self._export_placeholder)

    def _start_transcription(self) -> None:
        device = self._selected_device()
        if device is None:
            self.status_label.setText("Select an audio device before starting")
            return

        self._elapsed_seconds = 0
        self.timer_label.setText("00:00:00")
        self.transcript_area.clear()
        self._session = TranscriptionSession(
            device=device,
            on_transcript=self._signals.transcript.emit,
            on_error=self._signals.error.emit,
        )
        self._session.start()
        self._set_recording_state(True)
        self._timer.start(1_000)

    def _stop_transcription(self) -> None:
        self._timer.stop()
        if self._session is not None:
            self._session.stop()
            self._session = None
        self._set_recording_state(False)
        self._load_audio_devices()

    def _export_placeholder(self) -> None:
        self.status_label.setText("Export persistence is not implemented yet")

    def _load_audio_devices(self) -> None:
        try:
            self._devices = list_audio_devices()
        except Exception as exc:
            self._devices = []
            self.status_label.setText(f"Audio device detection failed: {exc}")
        self._refresh_device_selector()

    def _refresh_device_selector(self) -> None:
        selected_source = AudioSource(self.audio_source_selector.currentData())
        self.audio_device_selector.clear()
        for device in self._devices:
            if device.source == selected_source:
                self.audio_device_selector.addItem(device.display_name, device.id)
        if self.audio_device_selector.count() == 0:
            self.audio_device_selector.addItem("No devices detected", None)

    def _selected_device(self) -> AudioDevice | None:
        selected_source = AudioSource(self.audio_source_selector.currentData())
        selected_id = self.audio_device_selector.currentData()
        for device in self._devices:
            if device.source == selected_source and device.id == selected_id:
                return device
        return None

    def _handle_transcript(self, event: TranscriptEvent) -> None:
        if event.type == TranscriptEventType.PARTIAL:
            self.status_label.setText(f"Listening… {event.text}")
        elif event.type == TranscriptEventType.FINAL:
            self.transcript_area.append(event.text)
            self.status_label.setText("Recording")
        elif event.type == TranscriptEventType.ERROR:
            self.status_label.setText(event.text)

    def _handle_error(self, error: Exception) -> None:
        self._timer.stop()
        self._set_recording_state(False)
        self.status_label.setText(f"Error: {error}")

    def _set_recording_state(self, recording: bool) -> None:
        self._recording = recording
        self.start_button.setEnabled(not recording)
        self.stop_button.setEnabled(recording)
        self.status_label.setText("Recording" if recording else "Ready")
        self.status_dot.setProperty("recording", recording)
        self.status_dot.style().unpolish(self.status_dot)
        self.status_dot.style().polish(self.status_dot)

    def _update_elapsed_time(self) -> None:
        self._elapsed_seconds += 1
        hours = self._elapsed_seconds // 3_600
        minutes = self._elapsed_seconds % 3_600 // 60
        seconds = self._elapsed_seconds % 60
        self.timer_label.setText(f"{hours:02}:{minutes:02}:{seconds:02}")

    @staticmethod
    def _create_panel() -> QFrame:
        panel = QFrame()
        panel.setObjectName("Panel")
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        return panel
