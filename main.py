import sys
import os

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontDatabase, QFont

from detection.eye_tracker import EyeTracker
from screens.dashboard import DashboardScreen
from screens.session import SessionScreen
from screens.summary import SummaryScreen
from database.models import init_db

SCREEN_DASHBOARD = 0
SCREEN_SESSION = 1
SCREEN_SUMMARY = 2


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DoomCop")
        self.setMinimumSize(900, 700)
        self.resize(1100, 780)

        init_db()

        self.tracker = EyeTracker()

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.dashboard = DashboardScreen()
        self.session_screen = SessionScreen(self.tracker)
        self.summary_screen = SummaryScreen()

        self.stack.addWidget(self.dashboard)       # index 0
        self.stack.addWidget(self.session_screen)  # index 1
        self.stack.addWidget(self.summary_screen)  # index 2

        # Connections
        self.dashboard.start_session_clicked.connect(self._go_to_session)
        self.session_screen.session_ended.connect(self._go_to_summary)
        self.session_screen.go_home.connect(self._go_to_dashboard)
        self.summary_screen.go_home.connect(self._go_to_dashboard)
        self.summary_screen.start_new_session.connect(self._go_to_session)

        self._apply_stylesheet()
        self.stack.setCurrentIndex(SCREEN_DASHBOARD)

    def _apply_stylesheet(self):
        qss_path = os.path.join(os.path.dirname(__file__), "styles", "main.qss")
        try:
            with open(qss_path, "r") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            pass

    def _go_to_session(self):
        self.stack.setCurrentIndex(SCREEN_SESSION)

    def _go_to_dashboard(self):
        self.dashboard.refresh_stats()
        self.stack.setCurrentIndex(SCREEN_DASHBOARD)

    def _go_to_summary(self, session_data):
        self.summary_screen.set_session_data(session_data)
        self.stack.setCurrentIndex(SCREEN_SUMMARY)

    def closeEvent(self, event):
        self.tracker.stop()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("DoomCop")


    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
