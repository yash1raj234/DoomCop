import time
import os
import glob
import random

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialog, QApplication, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QFont, QPainter, QPainterPath, QColor
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

from database.operations import create_session, end_session, log_doomscroll_event

BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIDEOS_DIR = os.path.join(BASE_DIR, "assets", "Videos")

try:
    import cv2
    CV2_OK = True
except ImportError:
    CV2_OK = False


# ── keep a shuffled queue so videos don't repeat until all played ──
_video_queue: list[str] = []

def _pick_video() -> str | None:
    global _video_queue
    all_mp4 = glob.glob(os.path.join(VIDEOS_DIR, "*.mp4"))
    if not all_mp4:
        return None
    if not _video_queue:
        _video_queue = all_mp4[:]
        random.shuffle(_video_queue)
    return _video_queue.pop()


def _rounded_pixmap(frame, w: int, h: int, radius: int = 16) -> QPixmap:
    """Convert BGR cv2 frame → QPixmap with rounded corners."""
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    fh, fw, ch = rgb.shape
    img = QImage(rgb.data, fw, fh, ch * fw, QImage.Format.Format_RGB888).copy()
    pix = QPixmap.fromImage(img).scaled(
        w, h,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    # Clip to size then apply rounded mask
    pix = pix.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio,
                     Qt.TransformationMode.SmoothTransformation)
    rounded = QPixmap(w, h)
    rounded.fill(Qt.GlobalColor.transparent)
    painter = QPainter(rounded)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(0, 0, w, h, radius, radius)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, pix)
    painter.end()
    return rounded


# ══════════════════════════════════════════════════════════════
#  Doomscroll Popup — Qt multimedia (audio + video), plays once
# ══════════════════════════════════════════════════════════════
class DoomscrollPopup(QDialog):
    dismissed = pyqtSignal()

    def __init__(self, seconds_on_phone: int = 0, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Dialog
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)

        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        self._seconds = seconds_on_phone

        # Qt Media player (handles audio + video natively)
        self._player = QMediaPlayer()
        self._audio  = QAudioOutput()
        self._audio.setVolume(1.0)           # max volume
        self._player.setAudioOutput(self._audio)

        # Enable dismiss when playback ends
        self._player.playbackStateChanged.connect(self._on_playback_state)

        # Safety dismiss timer (10 s cap in case video is very long)
        self._safety = QTimer(singleShot=True)
        self._safety.timeout.connect(self._enable_dismiss)

        self._build_ui()
        self._start_video()

    # ── UI ────────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        overlay = QWidget()
        overlay.setObjectName("popupOverlay")
        overlay.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        inner = QVBoxLayout(overlay)
        inner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner.setSpacing(20)

        skull = QLabel("💀")
        sf = QFont(); sf.setPointSize(56)
        skull.setFont(sf)
        skull.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner.addWidget(skull)

        title = QLabel("CAUGHT SLIPPING")
        title.setObjectName("popupTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner.addWidget(title)

        stats = QLabel(f"You've been doomscrolling for {self._seconds}s")
        stats.setObjectName("popupStats")
        stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner.addWidget(stats)

        # QVideoWidget embedded in the overlay
        self._video_widget = QVideoWidget()
        self._video_widget.setFixedSize(520, 292)       # 16:9
        self._video_widget.setStyleSheet("border-radius:12px; background:#000;")
        self._player.setVideoOutput(self._video_widget)
        inner.addWidget(self._video_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        self.dismiss_btn = QPushButton("OK I GET IT — DISMISS")
        self.dismiss_btn.setObjectName("dismissBtn")
        self.dismiss_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dismiss_btn.setEnabled(False)
        self.dismiss_btn.clicked.connect(self._dismiss)
        inner.addWidget(self.dismiss_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        root.addWidget(overlay)

    # ── playback ──────────────────────────────────────────────
    def _start_video(self):
        path = _pick_video()
        if not path:
            self._safety.start(5000)
            return
        self._player.setSource(QUrl.fromLocalFile(path))
        self._player.play()
        # Safety cap: 10 s max before dismiss button enables
        self._safety.start(10_000)

    def _on_playback_state(self, state):
        if state == QMediaPlayer.PlaybackState.StoppedState:
            self._enable_dismiss()

    def _enable_dismiss(self):
        self._safety.stop()
        self.dismiss_btn.setEnabled(True)

    def _dismiss(self):
        self._player.stop()
        self._safety.stop()
        self.dismissed.emit()
        self.accept()

    def closeEvent(self, event):
        self._player.stop()
        self._safety.stop()
        super().closeEvent(event)


# ══════════════════════════════════════════════════════════════
#  Session Screen
# ══════════════════════════════════════════════════════════════
class SessionScreen(QWidget):
    session_ended = pyqtSignal(dict)
    go_home       = pyqtSignal()

    def __init__(self, tracker, parent=None):
        super().__init__(parent)
        self.tracker = tracker
        self.setObjectName("sessionRoot")

        self._session_id      = None
        self._session_active  = False
        self._elapsed_seconds = 0
        self._doom_seconds    = 0.0
        self._doom_count      = 0
        self._doom_start      = None

        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)

        self._build_ui()
        self._connect_tracker()

    # ── UI ────────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Purple background
        bg = QWidget()
        bg.setObjectName("sessionBg")
        bg_l = QVBoxLayout(bg)
        bg_l.setContentsMargins(0, 0, 0, 0)
        bg_l.setSpacing(0)

        # Navbar
        navbar = QWidget()
        navbar.setObjectName("navbar")
        navbar.setFixedHeight(64)
        nl = QHBoxLayout(navbar)
        nl.setContentsMargins(24, 0, 24, 0)

        back = QPushButton("← Back")
        back.setStyleSheet(
            "background:transparent; border:none; font-size:14px; font-weight:700; color:#000;"
        )
        back.setCursor(Qt.CursorShape.PointingHandCursor)
        back.clicked.connect(self._go_home)

        logo = QLabel("⎔ DoomCop")
        logo.setObjectName("navLogo")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        nl.addWidget(back)
        nl.addStretch()
        nl.addWidget(logo)
        nl.addStretch()
        bg_l.addWidget(navbar)

        # Content
        content = QWidget()
        cl = QHBoxLayout(content)
        cl.setContentsMargins(40, 40, 40, 40)
        cl.setSpacing(64)

        # ── LEFT: camera ──────────────────────────────────────
        left = QVBoxLayout()
        left.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left.setSpacing(10)

        cam_title = QLabel("LIVE MONITORING")
        cam_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cam_title.setStyleSheet(
            "font-size:11px; font-weight:700; color:#3F3F46; letter-spacing:2px;"
        )
        left.addWidget(cam_title)

        # Camera container with rounded border
        cam_container = QWidget()
        cam_container.setFixedSize(384, 288)
        cam_container.setStyleSheet("""
            QWidget {
                background: #18181B;
                border: 3px solid #000000;
                border-radius: 16px;
            }
        """)
        cam_cl = QVBoxLayout(cam_container)
        cam_cl.setContentsMargins(0, 0, 0, 0)

        self.camera_lbl = QLabel()
        self.camera_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_lbl.setStyleSheet("background:transparent; border:none;")
        self.camera_lbl.setText("🎥")
        cam_cl.addWidget(self.camera_lbl)

        left.addWidget(cam_container)

        self.doom_status_lbl = QLabel("")
        self.doom_status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.doom_status_lbl.setStyleSheet(
            "font-size:15px; font-weight:700; color:#DC2626;"
        )
        left.addWidget(self.doom_status_lbl)
        cl.addLayout(left, 1)

        # ── RIGHT: controls ───────────────────────────────────
        right = QVBoxLayout()
        right.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right.setSpacing(20)

        brand = QLabel("⎔ DoomCop")
        brand.setStyleSheet("font-size:22px; font-weight:800; color:#000;")
        right.addWidget(brand)

        self.timer_label = QLabel("Session Timer : 00:00:00")
        self.timer_label.setObjectName("timerLabel")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right.addWidget(self.timer_label)

        sub = QLabel("We're always watching.\nScroll if you dare.")
        sub.setObjectName("sessionSub")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right.addWidget(sub)

        right.addSpacing(8)

        self.session_btn = QPushButton("START SESSION")
        self.session_btn.setObjectName("sessionBtn")
        self.session_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.session_btn.setFixedWidth(220)
        self.session_btn.clicked.connect(self._toggle_session)
        right.addWidget(self.session_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.caught_label = QLabel("TIMES CAUGHT : 0")
        self.caught_label.setObjectName("caughtLabel")
        self.caught_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right.addWidget(self.caught_label)

        cl.addLayout(right, 1)
        bg_l.addWidget(content)
        root.addWidget(bg)

    # ── Tracker signals ───────────────────────────────────────
    def _connect_tracker(self):
        if hasattr(self.tracker, 'frame_ready'):
            self.tracker.frame_ready.connect(self._update_frame)
        if hasattr(self.tracker, 'doomscroll_detected'):
            self.tracker.doomscroll_detected.connect(self._on_doomscroll)
        if hasattr(self.tracker, 'doomscroll_ended'):
            self.tracker.doomscroll_ended.connect(self._on_doomscroll_ended)

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self.tracker, 'start'):
            self.tracker.start()

    # ── Live frame → rounded pixmap ───────────────────────────
    def _update_frame(self, frame):
        if frame is None or not CV2_OK:
            return
        try:
            pix = _rounded_pixmap(frame, 378, 282, radius=14)
            self.camera_lbl.setPixmap(pix)
            self.camera_lbl.setText("")
        except Exception:
            pass

    # ── Doomscroll events ─────────────────────────────────────
    def _on_doomscroll(self, confidence):
        if not self._session_active:
            return
        self._doom_count += 1
        self._doom_start = time.time()
        self.caught_label.setText(f"TIMES CAUGHT : {self._doom_count}")
        self.doom_status_lbl.setText("🚨  DOOMSCROLL DETECTED")
        log_doomscroll_event(self._session_id)

        popup = DoomscrollPopup(seconds_on_phone=int(self._elapsed_seconds))
        popup.dismissed.connect(lambda: self.doom_status_lbl.setText(""))
        popup.exec()

    def _on_doomscroll_ended(self):
        self.doom_status_lbl.setText("")
        if self._doom_start:
            self._doom_seconds += time.time() - self._doom_start
            self._doom_start = None

    # ── Timer ─────────────────────────────────────────────────
    def _tick(self):
        self._elapsed_seconds += 1
        h = self._elapsed_seconds // 3600
        m = (self._elapsed_seconds % 3600) // 60
        s = self._elapsed_seconds % 60
        self.timer_label.setText(f"Session Timer : {h:02d}:{m:02d}:{s:02d}")

    # ── Session control ───────────────────────────────────────
    def _toggle_session(self):
        if not self._session_active:
            self._start_session()
        else:
            self._end_session()

    def _start_session(self):
        self._session_id      = create_session("Study Session")
        self._session_active  = True
        self._elapsed_seconds = 0
        self._doom_count      = 0
        self._doom_seconds    = 0.0
        self._doom_start      = None
        self._timer.start(1000)
        self.session_btn.setText("END SESSION")

    def _end_session(self):
        self._timer.stop()
        self._session_active = False
        self.session_btn.setText("START SESSION")
        if self._doom_start:
            self._doom_seconds += time.time() - self._doom_start
            self._doom_start = None
        focus_sec = max(0, self._elapsed_seconds - self._doom_seconds)
        result = end_session(
            self._session_id,
            total_seconds=self._elapsed_seconds,
            focus_seconds=focus_sec,
            doomscroll_seconds=self._doom_seconds,
            doomscroll_count=self._doom_count,
        )
        if result:
            self.session_ended.emit(result)

    def _go_home(self):
        if self._session_active:
            self._end_session()
        self.go_home.emit()
