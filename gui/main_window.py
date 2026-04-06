"""
Main application window for VocalSeparator.
"""

import os
import zipfile
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QFileDialog,
    QComboBox, QFrame, QSizePolicy, QMessageBox,
    QSlider, QStackedWidget, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer, QUrl, QSize
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QColor, QPixmap, QFont, QPainter, QPen
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from audio.loader import AudioLoader
from models.model_manager import ModelManager
from processing.separator_engine import SeparatorEngine, SeparationWorker
from utils.helpers import format_duration, format_filesize, get_output_dir


class DropZone(QFrame):
    """Drag-and-drop file upload zone."""

    file_dropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setObjectName("DropZone")
        self.setMinimumHeight(160)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        self.icon_label = QLabel("🎵")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet("font-size: 42px; background: transparent;")

        self.title_label = QLabel("Drop your audio file here")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setObjectName("DropZoneTitle")

        self.subtitle_label = QLabel("MP3 · WAV · FLAC · M4A · AAC")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setObjectName("DropZoneSubtitle")

        self.browse_btn = QPushButton("Browse Files")
        self.browse_btn.setObjectName("BrowseButton")
        self.browse_btn.setFixedWidth(140)
        self.browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_btn.clicked.connect(self._browse_file)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addWidget(self.browse_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Audio File",
            str(Path.home() / "Music"),
            "Audio Files (*.mp3 *.wav *.flac *.m4a *.aac *.ogg);;All Files (*)"
        )
        if path:
            self.file_dropped.emit(path)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setProperty("dragging", True)
            self.style().unpolish(self)
            self.style().polish(self)

    def dragLeaveEvent(self, event):
        self.setProperty("dragging", False)
        self.style().unpolish(self)
        self.style().polish(self)

    def dropEvent(self, event: QDropEvent):
        self.setProperty("dragging", False)
        self.style().unpolish(self)
        self.style().polish(self)
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            self.file_dropped.emit(path)


class FileInfoCard(QFrame):
    """Displays loaded file metadata."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("InfoCard")
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        self.file_icon = QLabel("🎧")
        self.file_icon.setStyleSheet("font-size: 28px; background: transparent;")

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        self.name_label = QLabel("—")
        self.name_label.setObjectName("FileNameLabel")

        self.meta_label = QLabel("—")
        self.meta_label.setObjectName("FileMetaLabel")

        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.meta_label)

        self.clear_btn = QPushButton("✕")
        self.clear_btn.setObjectName("ClearButton")
        self.clear_btn.setFixedSize(28, 28)
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        layout.addWidget(self.file_icon)
        layout.addLayout(info_layout, stretch=1)
        layout.addWidget(self.clear_btn, alignment=Qt.AlignmentFlag.AlignVCenter)

    def update_info(self, name: str, duration: float, size: int):
        self.name_label.setText(name)
        self.meta_label.setText(f"{format_duration(duration)}  ·  {format_filesize(size)}")

    def clear(self):
        self.name_label.setText("—")
        self.meta_label.setText("—")


class AudioPlayerBar(QFrame):
    """Mini audio player for previewing stems."""

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self.setObjectName("PlayerBar")
        self._label = label
        self._player = QMediaPlayer()
        self._audio_out = QAudioOutput()
        self._player.setAudioOutput(self._audio_out)
        self._audio_out.setVolume(1.0)
        self._player.playbackStateChanged.connect(self._on_state_changed)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        icon = "🎤" if "Vocal" in self._label else "🎸"
        lbl = QLabel(f"{icon}  {self._label}")
        lbl.setObjectName("PlayerLabel")
        lbl.setFixedWidth(140)

        self.play_btn = QPushButton("▶")
        self.play_btn.setObjectName("PlayButton")
        self.play_btn.setFixedSize(36, 36)
        self.play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.play_btn.clicked.connect(self._toggle_play)

        self.stop_btn = QPushButton("■")
        self.stop_btn.setObjectName("StopButton")
        self.stop_btn.setFixedSize(36, 36)
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.clicked.connect(self._stop)

        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(100)
        self.vol_slider.setFixedWidth(80)
        self.vol_slider.valueChanged.connect(lambda v: self._audio_out.setVolume(v / 100))

        layout.addWidget(lbl)
        layout.addWidget(self.play_btn)
        layout.addWidget(self.stop_btn)
        layout.addStretch()
        layout.addWidget(QLabel("🔊"))
        layout.addWidget(self.vol_slider)

    def set_source(self, path: str):
        self._player.setSource(QUrl.fromLocalFile(path))
        self.play_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)

    def _toggle_play(self):
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def _stop(self):
        self._player.stop()

    def _on_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_btn.setText("⏸")
        else:
            self.play_btn.setText("▶")

    def clear(self):
        self._player.stop()
        self._player.setSource(QUrl())
        self.play_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)


class MainWindow(QMainWindow):
    """Primary application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("VocalSeparator")
        self.setMinimumSize(760, 820)
        self.resize(820, 900)

        self._audio_path: Optional[str] = None
        self._vocals_path: Optional[str] = None
        self._instrumental_path: Optional[str] = None
        self._worker: Optional[SeparationWorker] = None
        self._thread: Optional[QThread] = None

        self._model_manager = ModelManager()
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(20)

        # ── Header ──────────────────────────────────────────────
        header = QHBoxLayout()
        logo = QLabel("🎙 VocalSeparator")
        logo.setObjectName("AppLogo")
        tagline = QLabel("Studio-grade AI stem separation")
        tagline.setObjectName("Tagline")
        header.addWidget(logo)
        header.addStretch()
        header.addWidget(tagline, alignment=Qt.AlignmentFlag.AlignBottom)
        root.addLayout(header)

        # ── Divider ─────────────────────────────────────────────
        root.addWidget(self._make_divider())

        # ── Drop zone ───────────────────────────────────────────
        self.drop_zone = DropZone()
        self.drop_zone.file_dropped.connect(self._load_file)
        root.addWidget(self.drop_zone)

        # ── File info ───────────────────────────────────────────
        self.file_card = FileInfoCard()
        self.file_card.clear_btn.clicked.connect(self._clear_file)
        self.file_card.hide()
        root.addWidget(self.file_card)

        # ── Settings row ────────────────────────────────────────
        settings_row = QHBoxLayout()
        settings_row.setSpacing(16)

        model_lbl = QLabel("Model:")
        model_lbl.setObjectName("SettingsLabel")
        self.model_combo = QComboBox()
        self.model_combo.setObjectName("SettingsCombo")
        self.model_combo.addItems([
            "Hybrid Demucs v4  (Best Quality)",
            "Hybrid Demucs  (Fast)",
            "Demucs htdemucs  (Balanced)",
        ])
        self.model_combo.setMinimumWidth(220)

        fmt_lbl = QLabel("Output:")
        fmt_lbl.setObjectName("SettingsLabel")
        self.fmt_combo = QComboBox()
        self.fmt_combo.setObjectName("SettingsCombo")
        self.fmt_combo.addItems(["WAV (Lossless)", "MP3 320kbps"])

        settings_row.addWidget(model_lbl)
        settings_row.addWidget(self.model_combo)
        settings_row.addSpacing(16)
        settings_row.addWidget(fmt_lbl)
        settings_row.addWidget(self.fmt_combo)
        settings_row.addStretch()
        root.addLayout(settings_row)

        # ── Separate button ─────────────────────────────────────
        self.separate_btn = QPushButton("✦  Separate Stems")
        self.separate_btn.setObjectName("SeparateButton")
        self.separate_btn.setMinimumHeight(52)
        self.separate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.separate_btn.setEnabled(False)
        self.separate_btn.clicked.connect(self._start_separation)
        root.addWidget(self.separate_btn)

        # ── Progress ────────────────────────────────────────────
        self.progress_frame = QFrame()
        self.progress_frame.setObjectName("ProgressFrame")
        prog_layout = QVBoxLayout(self.progress_frame)
        prog_layout.setContentsMargins(16, 14, 16, 14)
        prog_layout.setSpacing(8)

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("StatusLabel")

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("MainProgress")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMinimumHeight(8)

        self.eta_label = QLabel("")
        self.eta_label.setObjectName("EtaLabel")

        prog_layout.addWidget(self.status_label)
        prog_layout.addWidget(self.progress_bar)
        prog_layout.addWidget(self.eta_label)
        self.progress_frame.hide()
        root.addWidget(self.progress_frame)

        # ── Results ─────────────────────────────────────────────
        self.results_frame = QFrame()
        self.results_frame.setObjectName("ResultsFrame")
        res_layout = QVBoxLayout(self.results_frame)
        res_layout.setContentsMargins(0, 0, 0, 0)
        res_layout.setSpacing(10)

        res_title = QLabel("Separated Stems")
        res_title.setObjectName("SectionTitle")
        res_layout.addWidget(res_title)

        self.vocals_player = AudioPlayerBar("Vocals")
        self.vocals_player.play_btn.setEnabled(False)
        self.vocals_player.stop_btn.setEnabled(False)
        res_layout.addWidget(self.vocals_player)

        self.instrumental_player = AudioPlayerBar("Instrumental")
        self.instrumental_player.play_btn.setEnabled(False)
        self.instrumental_player.stop_btn.setEnabled(False)
        res_layout.addWidget(self.instrumental_player)

        root.addWidget(self.results_frame)
        self.results_frame.hide()

        # ── Download buttons ─────────────────────────────────────
        self.download_frame = QFrame()
        dl_layout = QHBoxLayout(self.download_frame)
        dl_layout.setSpacing(12)

        self.dl_vocals_btn = QPushButton("⬇  Download Vocals")
        self.dl_vocals_btn.setObjectName("DownloadButton")
        self.dl_vocals_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dl_vocals_btn.clicked.connect(lambda: self._download_file(self._vocals_path, "vocals"))

        self.dl_instr_btn = QPushButton("⬇  Download Instrumental")
        self.dl_instr_btn.setObjectName("DownloadButton")
        self.dl_instr_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dl_instr_btn.clicked.connect(lambda: self._download_file(self._instrumental_path, "instrumental"))

        self.dl_both_btn = QPushButton("⬇  Download Both (ZIP)")
        self.dl_both_btn.setObjectName("DownloadBothButton")
        self.dl_both_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dl_both_btn.clicked.connect(self._download_both)

        dl_layout.addWidget(self.dl_vocals_btn)
        dl_layout.addWidget(self.dl_instr_btn)
        dl_layout.addWidget(self.dl_both_btn)

        root.addWidget(self.download_frame)
        self.download_frame.hide()

        root.addStretch()

    def _connect_signals(self):
        pass

    def _make_divider(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("Divider")
        return line

    # ── File loading ────────────────────────────────────────────

    def _load_file(self, path: str):
        loader = AudioLoader()
        if not loader.is_supported(path):
            QMessageBox.warning(self, "Unsupported Format",
                "This file format is not supported.\n\nSupported: MP3, WAV, FLAC, M4A, AAC")
            return

        info = loader.get_info(path)
        if info is None:
            QMessageBox.critical(self, "Error", "Could not read audio file. It may be corrupted.")
            return

        self._audio_path = path
        self._vocals_path = None
        self._instrumental_path = None

        self.file_card.update_info(
            Path(path).name,
            info["duration"],
            info["size"]
        )
        self.file_card.show()
        self.drop_zone.hide()
        self.separate_btn.setEnabled(True)
        self.results_frame.hide()
        self.download_frame.hide()
        self.vocals_player.clear()
        self.instrumental_player.clear()

    def _clear_file(self):
        self._audio_path = None
        self._vocals_path = None
        self._instrumental_path = None
        self.file_card.hide()
        self.drop_zone.show()
        self.separate_btn.setEnabled(False)
        self.progress_frame.hide()
        self.results_frame.hide()
        self.download_frame.hide()
        self.vocals_player.clear()
        self.instrumental_player.clear()
        if self._worker and self._thread and self._thread.isRunning():
            self._worker.cancel()

    # ── Separation ──────────────────────────────────────────────

    def _get_model_key(self) -> str:
        idx = self.model_combo.currentIndex()
        return ["htdemucs_ft", "htdemucs", "htdemucs_ft"][idx]

    def _get_output_format(self) -> str:
        return "wav" if self.fmt_combo.currentIndex() == 0 else "mp3"

    def _start_separation(self):
        if not self._audio_path:
            return

        self.separate_btn.setEnabled(False)
        self.progress_frame.show()
        self.results_frame.hide()
        self.download_frame.hide()
        self.progress_bar.setValue(0)
        self.status_label.setText("Initializing…")
        self.eta_label.setText("")

        model_key = self._get_model_key()
        output_fmt = self._get_output_format()
        output_dir = get_output_dir()

        engine = SeparatorEngine(
            model_name=model_key,
            model_manager=self._model_manager,
            output_format=output_fmt
        )

        self._worker = SeparationWorker(engine, self._audio_path, output_dir)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.status.connect(self._on_status)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_progress(self, value: int):
        self.progress_bar.setValue(value)

    def _on_status(self, msg: str):
        self.status_label.setText(msg)

    def _on_finished(self, vocals: str, instrumental: str):
        self._vocals_path = vocals
        self._instrumental_path = instrumental

        self.progress_bar.setValue(100)
        self.status_label.setText("✓  Separation complete!")
        self.eta_label.setText("")

        self.vocals_player.set_source(vocals)
        self.instrumental_player.set_source(instrumental)
        self.results_frame.show()
        self.download_frame.show()
        self.separate_btn.setEnabled(True)

    def _on_error(self, msg: str):
        self.progress_frame.show()
        self.status_label.setText("Error during separation")
        self.progress_bar.setValue(0)
        self.separate_btn.setEnabled(True)
        QMessageBox.critical(self, "Separation Failed", msg)

    # ── Downloads ───────────────────────────────────────────────

    def _download_file(self, source: Optional[str], kind: str):
        if not source or not os.path.exists(source):
            QMessageBox.warning(self, "File Not Found", "Output file not found.")
            return
        ext = Path(source).suffix
        original_stem = Path(self._audio_path).stem if self._audio_path else Path(source).stem
        label = "vocals" if kind == "vocals" else "music"
        default_name = f"{original_stem} ({label}){ext}"
        dest, _ = QFileDialog.getSaveFileName(
            self, f"Save {kind.title()}", str(Path.home() / "Desktop" / default_name),
            f"Audio (*{ext})"
        )
        if dest:
            import shutil
            shutil.copy2(source, dest)
            QMessageBox.information(self, "Saved", f"Saved to:\n{dest}")

    def _download_both(self):
        if not self._vocals_path or not self._instrumental_path:
            return
        stem = Path(self._audio_path).stem if self._audio_path else "output"
        dest, _ = QFileDialog.getSaveFileName(
            self, "Save ZIP Archive", str(Path.home() / "Desktop" / f"{stem} (stems).zip"),
            "ZIP Archive (*.zip)"
        )
        if dest:
            ext = Path(self._vocals_path).suffix
            with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(self._vocals_path,       f"{stem} (vocals){ext}")
                zf.write(self._instrumental_path, f"{stem} (music){ext}")
            QMessageBox.information(self, "Saved", f"Saved archive to:\n{dest}")

    def closeEvent(self, event):
        try:
            if self._worker and self._thread and self._thread.isRunning():
                self._worker.cancel()
                self._thread.quit()
                self._thread.wait(3000)
        except RuntimeError:
            pass
        event.accept()
