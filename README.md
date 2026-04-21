# ⎔ DoomCop

**DoomCop** is a modern, aggressive productivity assistant designed to break your doomscrolling habits using real-time AI tracking. It watches your posture and gaze to detect when you've slipped into brain-rot behavior and snaps you back to reality.



https://github.com/user-attachments/assets/bc262996-c526-4da0-a773-8b165b64f1aa



## 🚀 How It Works

DoomCop uses your webcam and state-of-the-art computer vision to monitor your focus session:

1.  **Eye & Posture Tracking**: Using **MediaPipe Face Mesh**, the app calculates your head pitch and gaze direction in real-time.
2.  **Detection logic**: If your head remains tilted down (typical "phone posture") for more than 3 seconds while a session is active, DoomCop triggers a violation.
3.  **Aggressive Intervention**: Upon detection, a full-screen, unskippable "Roast Popup" appears. It plays a random high-energy/insulting video and audio clip from your assets to shame you into putting your phone away.
4.  **Session Analytics**: Every session is logged. You can track your Focus Time vs. Doomscroll Time on the dashboard to see your improvement over time.

## 🛠 Tech Stack

*   **GUI**: [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) for a sleek, hardware-accelerated desktop interface.
*   **AI/Vision**: [Google MediaPipe](https://google.github.io/mediapipe/) for high-fidelity face landmarking and head pose estimation.
*   **Video Processing**: [OpenCV](https://opencv.org/) for camera stream handling and real-time frame manipulation.
*   **Multimedia**: [Qt Multimedia](https://doc.qt.io/qt-6/qtmultimedia-index.html) for native audio and video playback during interventions.
*   **Database**: SQLite for lightweight, local-first storage of session history and statistics.
*   **Styling**: Custom QSS with a modern, minimalist Zinc/Indigo/Pink aesthetic.

## 🏃 Getting Started

### Prerequisites

*   Python 3.9+ 
*   A working webcam.

### Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/yash1raj234/DoomCop.git
    cd DoomCop
    ```

2.  **Set up a virtual environment** (Recommended):
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

### Running the App

Simply run the startup script or the main Python file:

```bash
python main.py
```
*Or, if on macOS/Linux:*
```bash
./run.sh
```

## 📂 Project Structure

*   `screens/`: Contains the logic for Dashboard, Active Session, and Summary views.
*   `detection/`: The core `EyeTracker` engine powered by MediaPipe.
*   `database/`: SQLite operations for logging session data.
*   `assets/`: Icons, custom illustrations, and the "Roast" video library.
*   `styles/`: The `main.qss` global stylesheet.

## ⚖️ License

MIT License - feel free to use and improve it!
