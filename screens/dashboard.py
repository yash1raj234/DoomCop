import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from database.operations import get_total_stats

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _sec_to_hm(s):
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    return f"{h}h {m}m" if h > 0 else f"{m}m"


def _load_pixmap(name, w, h):
    path = os.path.join(BASE_DIR, "assets", "icons", name)
    pix = QPixmap(path)
    if not pix.isNull():
        return pix.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio,
                          Qt.TransformationMode.SmoothTransformation)
    return None


class _StatRow(QWidget):
    def __init__(self, label, value, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(6)

        row = QHBoxLayout()
        lbl = QLabel(label.upper())
        lbl.setObjectName("statLabel")
        val = QLabel(value)
        val.setObjectName("statValue")
        self.value_label = val
        row.addWidget(lbl)
        row.addStretch()
        row.addWidget(val)
        layout.addLayout(row)

        div = QFrame()
        div.setObjectName("statDivider")
        div.setFrameShape(QFrame.Shape.HLine)
        div.setFixedHeight(1)
        layout.addWidget(div)


class DashboardScreen(QWidget):
    start_session_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dashRoot")
        self._build_ui()
        self.refresh_stats()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── NAVBAR ──────────────────────────────────────────────
        navbar = QWidget()
        navbar.setObjectName("navbar")
        navbar.setFixedHeight(64)
        nl = QHBoxLayout(navbar)
        nl.setContentsMargins(24, 0, 24, 0)
        logo = QLabel("⎔ DoomCop")
        logo.setObjectName("navLogo")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nl.addStretch()
        nl.addWidget(logo)
        nl.addStretch()
        root.addWidget(navbar)

        # ── HERO ─────────────────────────────────────────────────
        hero = QWidget()
        hero.setObjectName("heroWidget")
        swoosh_path = os.path.join(BASE_DIR, "assets", "icons", "swoosh.png").replace("\\", "/")
        if os.path.exists(swoosh_path):
            hero.setStyleSheet(f"""
                #heroWidget {{
                    background-image: url('{swoosh_path}');
                    background-repeat: no-repeat;
                    background-position: center;
                    background-color: transparent;
                }}
            """)

        hl = QVBoxLayout(hero)
        hl.setContentsMargins(40, 80, 40, 80)
        hl.setSpacing(24)
        hl.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        title = QLabel("Your screen time called.\nIt's embarrassing.")
        title.setObjectName("heroTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setWordWrap(True)
        hl.addWidget(title)

        cta = QPushButton("LETS GET STARTED")
        cta.setObjectName("ctaBtn")
        cta.setCursor(Qt.CursorShape.PointingHandCursor)
        cta.setFixedWidth(240)
        cta.clicked.connect(self.start_session_clicked.emit)
        cta_wrap = QHBoxLayout()
        cta_wrap.addStretch()
        cta_wrap.addWidget(cta)
        cta_wrap.addStretch()
        hl.addLayout(cta_wrap)
        root.addWidget(hero)

        # ── STATS SECTION ────────────────────────────────────────
        stats_section = QWidget()
        stats_section.setObjectName("statsSection")
        sl = QHBoxLayout(stats_section)
        sl.setContentsMargins(48, 48, 48, 24)
        sl.setSpacing(64)

        # Left: welcome + phone image
        left = QVBoxLayout()
        left.setSpacing(8)
        left.setAlignment(Qt.AlignmentFlag.AlignTop)

        wh = QLabel("Welcome")
        wh.setObjectName("welcomeHeading")
        ws = QLabel("Stop Yourself From BrainRot\nFocus up.")
        ws.setObjectName("welcomeSub")
        left.addWidget(wh)
        left.addWidget(ws)
        left.addSpacing(20)

        phone_pix = _load_pixmap("phone_hand.png", 200, 200)
        if phone_pix:
            img_lbl = QLabel()
            img_lbl.setPixmap(phone_pix)
            img_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
            left.addWidget(img_lbl)

        left.addStretch()
        sl.addLayout(left, 1)

        # Right: stat rows
        right = QVBoxLayout()
        right.setSpacing(0)
        right.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.row_focus   = _StatRow("Focus Time",          "0m")
        self.row_sess    = _StatRow("Sessions",             "0")
        self.row_caught  = _StatRow("Caught Doomscrolling", "0")
        self.row_status  = _StatRow("Status",               "—")

        for r in [self.row_focus, self.row_sess, self.row_caught, self.row_status]:
            right.addWidget(r)
        right.addStretch()
        sl.addLayout(right, 1)
        root.addWidget(stats_section)

        # ── JUMP BUTTON ──────────────────────────────────────────
        footer = QWidget()
        footer.setObjectName("statsSection")   # same bg as stats
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(0, 0, 0, 40)
        fl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        jump = QPushButton("JUMP INTO NEW SESSION")
        jump.setObjectName("ctaBtn")
        jump.setCursor(Qt.CursorShape.PointingHandCursor)
        jump.setFixedWidth(260)
        jump.clicked.connect(self.start_session_clicked.emit)
        fl.addWidget(jump)
        root.addWidget(footer)

    def refresh_stats(self):
        try:
            s = get_total_stats()
            self.row_focus.value_label.setText(_sec_to_hm(s["total_focus_seconds"]))
            self.row_sess.value_label.setText(str(s["total_sessions"]))
            self.row_caught.value_label.setText(str(s["total_caught"]))
            dm = s["total_doom_seconds"] / 60
            if dm < 30:
                status = "You're actually doing great 🌱"
            elif dm < 60:
                status = "Could be better tbh"
            else:
                status = "Get your life together 💀"
            self.row_status.value_label.setText(status)
        except Exception:
            pass
