import os
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _fmt(s):
    s = int(s)
    h = s // 3600
    m = (s % 3600) // 60
    sec = s % 60
    if h > 0:
        return f"{h}h {m}m {sec}s"
    return f"{m}m {sec}s"


def _load_pix(name, w, h):
    path = os.path.join(BASE_DIR, "assets", "icons", name)
    pix = QPixmap(path)
    if not pix.isNull():
        return pix.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio,
                          Qt.TransformationMode.SmoothTransformation)
    return None


class SummaryScreen(QWidget):
    start_new_session = pyqtSignal()
    go_home = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("summaryRoot")
        self._stat_rows = {}
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Background ────────────────────────────────────────
        bg = QWidget()
        bg.setObjectName("summaryBg")
        bg_layout = QVBoxLayout(bg)
        bg_layout.setContentsMargins(0, 0, 0, 0)
        bg_layout.setSpacing(0)

        # ── Navbar ────────────────────────────────────────────
        navbar = QWidget()
        navbar.setObjectName("navbar")
        navbar.setFixedHeight(64)
        nl = QHBoxLayout(navbar)
        nl.setContentsMargins(24, 0, 24, 0)

        back_btn = QPushButton("← Home")
        back_btn.setStyleSheet(
            "background: transparent; border: none; "
            "font-size: 14px; font-weight: 700; color: #000000;"
        )
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(self.go_home.emit)

        logo = QLabel("⎔ DoomCop")
        logo.setObjectName("navLogo")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        nl.addWidget(back_btn)
        nl.addStretch()
        nl.addWidget(logo)
        nl.addStretch()
        bg_layout.addWidget(navbar)

        # ── Content row ───────────────────────────────────────
        content = QWidget()
        cl = QHBoxLayout(content)
        cl.setContentsMargins(0, 48, 0, 48)
        cl.setSpacing(0)

        # Left skater
        left_char = QLabel()
        left_char.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_char.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        pix_b = _load_pix("skater_boy.png", 260, 260)
        if pix_b:
            left_char.setPixmap(pix_b)
        cl.addWidget(left_char, 1)

        # Center pink card
        card = QWidget()
        card.setObjectName("summaryCard")
        card.setFixedWidth(420)
        card_l = QVBoxLayout(card)
        card_l.setContentsMargins(32, 28, 32, 28)
        card_l.setSpacing(0)

        # Top divider
        top_div = QFrame()
        top_div.setFrameShape(QFrame.Shape.HLine)
        top_div.setStyleSheet("background-color: #000000; max-height: 1px; border: none;")
        card_l.addWidget(top_div)
        card_l.addSpacing(16)

        # Title
        title_lbl = QLabel("Session Completed")
        title_lbl.setObjectName("summaryCardTitle")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_l.addWidget(title_lbl)
        card_l.addSpacing(16)

        # Stat rows
        for key, default in [
            ("Study Session", "—"),
            ("Total Time",    "—"),
            ("Focused Time",  "—"),
            ("Times Caught",  "—"),
            ("Focus Score",   "—"),
        ]:
            row_w = QHBoxLayout()
            k = QLabel(key)
            k.setObjectName("summaryKey")
            v = QLabel(default)
            v.setObjectName("summaryVal")
            v.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._stat_rows[key] = v
            row_w.addWidget(k)
            row_w.addStretch()
            row_w.addWidget(v)
            card_l.addLayout(row_w)
            card_l.addSpacing(6)

            div = QFrame()
            div.setFrameShape(QFrame.Shape.HLine)
            div.setStyleSheet("background-color: #000000; max-height: 1px; border: none;")
            card_l.addWidget(div)
            card_l.addSpacing(6)

        card_l.addSpacing(12)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        save_btn = QPushButton("Save Session")
        save_btn.setObjectName("saveBtn")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self.go_home.emit)

        new_btn = QPushButton("Start New Session")
        new_btn.setObjectName("newSessionBtn")
        new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_btn.clicked.connect(self.start_new_session.emit)

        btn_row.addWidget(save_btn)
        btn_row.addWidget(new_btn)
        card_l.addLayout(btn_row)

        cl.addWidget(card, 0, Qt.AlignmentFlag.AlignVCenter)

        # Right skater
        right_char = QLabel()
        right_char.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_char.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        pix_g = _load_pix("skater_girl.png", 260, 260)
        if pix_g:
            right_char.setPixmap(pix_g)
        cl.addWidget(right_char, 1)

        bg_layout.addWidget(content)
        bg_layout.addStretch()
        root.addWidget(bg)

    def set_session_data(self, data):
        start = data.get("start_time")
        if start and hasattr(start, "strftime"):
            date_str = start.strftime("%b %d %Y")
        else:
            date_str = datetime.now().strftime("%b %d %Y")

        self._stat_rows["Study Session"].setText(date_str)
        self._stat_rows["Total Time"].setText(_fmt(data.get("total_seconds", 0)))
        self._stat_rows["Focused Time"].setText(_fmt(data.get("focus_seconds", 0)))
        caught = data.get("doomscroll_count", 0)
        self._stat_rows["Times Caught"].setText(f"{caught} times")
        score = data.get("focus_score", 100.0)
        emoji = "🔥" if score >= 90 else ("😐" if score >= 60 else "💀")
        self._stat_rows["Focus Score"].setText(f"{score:.1f}% {emoji}")
