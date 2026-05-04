"""
GSM Demo GUI -- one-window presentation demo for the Gym Space Monitoring system.

future me: this is the demo route. don't overthink it. the dot moves through
preset stops, each stop fires an alert, alerts pop up on the staff console
and/or smart watch. clicking an alert pops a recording panel that animates
out from wherever in the gym the alert came from.

what this is NOT: a real implementation of the alert controller. it's a
visualizer. it reuses the existing controllers' data shapes (member profiles,
biometric thresholds, environmental thresholds) so the alert text on screen
matches what the SRS/SAD describes, but the actual decision making is
scripted in DEMO_SCRIPT below.

run this from inside CS460_GSM/ like:
    python gsm_gui_demo.py
"""

import os
import sys
import json
import glob

from PyQt5.QtCore import (
    Qt, QTimer, QPointF, QRectF, QPropertyAnimation, QEasingCurve,
    pyqtProperty, QSize, QUrl
)
from PyQt5.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QPainterPath, QFontMetrics
)
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QListWidget, QListWidgetItem, QFrame, QSizePolicy, QMessageBox
)

# QtMultimedia is part of PyQt5 but not always installed cleanly. handle that
# gracefully so the demo doesn't crash on a teammate's machine that's missing it.
try:
    from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent, QSoundEffect
    from PyQt5.QtMultimediaWidgets import QVideoWidget
    HAS_MEDIA = True
except ImportError:
    HAS_MEDIA = False
    print("[demo] PyQt5 multimedia not available, video panel will show placeholder text instead")


# ----------------------------------------------------------------------------
# config / constants
# ----------------------------------------------------------------------------

# yeah this is ugly but stable. layout positions are normalized 0-1 inside the
# gym floor widget so resizing kinda works. see GymFloor._abs_to_pixel.
LOCATIONS = {
    # location_id : (x_norm, y_norm, label, color)
    "entrance":         (0.10, 0.78, "Entrance / RFID",     "#5c8aa6"),
    "cardio":           (0.20, 0.18, "Cardio Area",         "#9c5c7a"),
    "weight_machines":  (0.50, 0.18, "Weight Machines",     "#5c9c6a"),
    "free_weights":     (0.80, 0.18, "Free Weights",        "#9c8a5c"),
    "env_sensor":       (0.50, 0.50, "Air Quality Sensor",  "#7a7a9c"),
}

# severity colors for the console / watch alerts
SEVERITY_COLORS = {
    "passive":  "#3d6e8c",
    "urgent":   "#c8842c",
    "critical": "#b73a3a",
    "info":     "#6a6a6a",
}

# look in a few likely places for the alert videos. first one that has files wins.
# this lets the demo work whether the user copies videos into CS460_GSM/videos/,
# leaves them in a sibling CS460/ folder, or has the test_videos/ paths from
# cctv_driver.py.
VIDEO_SEARCH_PATHS = [
    "videos",
    "../CS460",
    "test_videos",
    "../test_videos",
]


# ----------------------------------------------------------------------------
# demo script
# ----------------------------------------------------------------------------
# this is THE source of truth for what happens during the demo.
# each entry: (location_id, alert_dict)
# alert_dict tells the GUI what to display. severity decides who sees it
# (passive = watch only, urgent = both, critical = both + emergency banner).
#
# events are pulled (loosely) from the SRS use cases:
#   UC1 heart rate deviation     -> cardio
#   UC4 unsafe form              -> free_weights
#   UC5 injury during workout    -> weight_machines
#   UC6 environmental condition  -> env_sensor
#   UC7 maximum capacity         -> entrance

DEMO_SCRIPT = [
    {
        "location": "entrance",
        "alert": {
            "title":       "Maximum capacity reached",
            "severity":    "urgent",
            "source":      "CheckInTerminal Controller",
            "use_case":    "UC7",
            "to_console":  True,
            "to_watch":    False,
            "description": ("Member 014 attempted entry while occupancy is at 16/16. "
                            "Staff: deny entry until a member checks out."),
            "video_hint":  "entrance",
        },
    },
    {
        "location": "cardio",
        "alert": {
            "title":       "Heart rate deviation -- Brian Castillo (002)",
            "severity":    "urgent",
            "source":      "Biometric Controller",
            "use_case":    "UC1",
            "to_console":  True,
            "to_watch":    True,
            # numbers come straight from garmin_driver.py member 002
            "description": ("HR 155 bpm is >100% above personal baseline of 75 bpm. "
                            "Member is mid-session on the treadmill. Auto-escalates "
                            "to emergency response in 120s if unacknowledged."),
            "video_hint":  "cardio",
        },
    },
    {
        "location": "weight_machines",
        "alert": {
            "title":       "Injury detected -- Adrian Calderon (008)",
            "severity":    "critical",
            "source":      "Biometric + Camera Analysis",
            "use_case":    "UC5",
            "to_console":  True,
            "to_watch":    True,
            "description": ("Fall detected on Garmin Venu 3, simultaneous distress "
                            "event from CCTV camera on the decline squat machine. "
                            "Emergency response signal dispatched."),
            "video_hint":  "machines",  # we'll bias to the man_squatting clip
        },
    },
    {
        "location": "free_weights",
        "alert": {
            "title":       "Unsafe form -- deadlifts",
            "severity":    "passive",
            "source":      "Camera Analysis Controller",
            "use_case":    "UC4",
            "to_console":  True,
            "to_watch":    True,
            "description": ("Gemini MLLM flagged poor form on deadlift attempt. "
                            "Suggestion: keep back neutral, hinge at hips. "
                            "Logged to member profile for trainer review."),
            "video_hint":  "weights",
        },
    },
    {
        "location": "env_sensor",
        "alert": {
            "title":       "Air quality threshold exceeded",
            "severity":    "urgent",
            "source":      "Environmental Controller",
            "use_case":    "UC6",
            "to_console":  True,
            "to_watch":    True,
            # again, real number from environmental_sensor_driver.py cardio section
            "description": ("CO2 reading 1250 ppm in cardio section "
                            "(threshold 1000 ppm). Members advised to relocate. "
                            "Staff should ventilate."),
            "video_hint":  "environment",
        },
    },
    {
        "location": "cardio",  # one extra event to wrap up nicely
        "alert": {
            "title":       "Camera offline -- cardio section",
            "severity":    "passive",
            "source":      "Camera Analysis Controller",
            "use_case":    "exception",
            "to_console":  True,
            "to_watch":    False,
            "description": ("CCTV feed lost for cardio section. Form detection "
                            "suspended for this area. Technician notified."),
            "video_hint":  None,
        },
    },
]


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------

def find_videos():
    """returns a dict of location_hint -> list of mp4 paths it can use.
    we don't know which IMG_xxxx.mp4 is which event, so we just round-robin
    over whatever's available. don't overthink it."""
    found = []
    for path in VIDEO_SEARCH_PATHS:
        if os.path.isdir(path):
            mp4s = sorted(glob.glob(os.path.join(path, "*.mp4")))
            if mp4s:
                found = mp4s
                print(f"[demo] using videos from {path}/ ({len(mp4s)} files)")
                break
    if not found:
        print("[demo] no .mp4 files found in any of:", VIDEO_SEARCH_PATHS)
    return found


def find_sounds():
    """same idea but for .wav alert sounds. user said wav files are optional."""
    if os.path.isdir("sounds"):
        wavs = sorted(glob.glob("sounds/*.wav"))
        if wavs:
            print(f"[demo] using sounds from sounds/ ({len(wavs)} files)")
            return wavs
    return []


# ----------------------------------------------------------------------------
# gym floor widget -- top half of the window
# ----------------------------------------------------------------------------

class GymFloor(QWidget):
    """top-down view of the gym. draws the rooms/zones, the moving dot,
    and serves as the "stage" that the video panel animates out of.

    the dot is moved by an external animation on the dot_x / dot_y properties.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(700, 380)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # dot starts at the entrance
        ex, ey, _, _ = LOCATIONS["entrance"]
        self._dot_x = ex
        self._dot_y = ey
        # which location is currently flashing (highlighted as alert source)
        self._flash_location = None
        # flashing toggle, blinks via timer
        self._flash_on = False
        self._flash_timer = QTimer(self)
        self._flash_timer.setInterval(400)
        self._flash_timer.timeout.connect(self._toggle_flash)
        # cache the current member name floating next to the dot
        self.dot_label = "(no member)"

    # qt properties so QPropertyAnimation can tween the dot
    def get_dot_x(self):
        return self._dot_x

    def set_dot_x(self, v):
        self._dot_x = v
        self.update()

    dot_x = pyqtProperty(float, get_dot_x, set_dot_x)

    def get_dot_y(self):
        return self._dot_y

    def set_dot_y(self, v):
        self._dot_y = v
        self.update()

    dot_y = pyqtProperty(float, get_dot_y, set_dot_y)

    def flash_location(self, location_id):
        """start a 6-blink flash on the given location to draw the eye."""
        self._flash_location = location_id
        self._flash_on = True
        self._flash_timer.start()
        # auto-stop after a few seconds, presentation friendly
        QTimer.singleShot(2800, self._stop_flash)
        self.update()

    def _toggle_flash(self):
        self._flash_on = not self._flash_on
        self.update()

    def _stop_flash(self):
        self._flash_timer.stop()
        self._flash_location = None
        self.update()

    def location_pixel(self, location_id):
        """convert a normalized location to absolute pixel coordinates.
        used by the video-panel animation so it can launch from the right spot."""
        x_norm, y_norm, _, _ = LOCATIONS[location_id]
        return self._abs_to_pixel(x_norm, y_norm)

    def _abs_to_pixel(self, x_norm, y_norm):
        # leave a bit of padding so labels don't kiss the edge
        pad = 24
        w = self.width() - 2 * pad
        h = self.height() - 2 * pad
        return QPointF(pad + x_norm * w, pad + y_norm * h)

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # gym floor background, slightly off-white
        p.fillRect(self.rect(), QColor("#f4f1ea"))

        # outer wall
        p.setPen(QPen(QColor("#3a3a3a"), 3))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(self.rect().adjusted(8, 8, -8, -8), 8, 8)

        # title-ish header
        p.setPen(QColor("#3a3a3a"))
        p.setFont(QFont("Arial", 11, QFont.Bold))
        p.drawText(20, 26, "Lobo Community Center -- Gym Floor (top-down view)")

        # draw each location as a labeled box
        for loc_id, (x_norm, y_norm, label, color) in LOCATIONS.items():
            center = self._abs_to_pixel(x_norm, y_norm)
            box_w, box_h = 150, 60
            box = QRectF(center.x() - box_w / 2, center.y() - box_h / 2, box_w, box_h)

            # flash effect
            if loc_id == self._flash_location and self._flash_on:
                p.setBrush(QBrush(QColor("#ffd166")))
                p.setPen(QPen(QColor("#b73a3a"), 3))
            else:
                p.setBrush(QBrush(QColor(color).lighter(170)))
                p.setPen(QPen(QColor(color), 2))

            p.drawRoundedRect(box, 6, 6)

            p.setPen(QColor("#222222"))
            p.setFont(QFont("Arial", 9, QFont.Bold))
            p.drawText(box, Qt.AlignCenter, label)

        # the dot (the member)
        dot_center = self._abs_to_pixel(self._dot_x, self._dot_y)
        # outer glow ring
        p.setBrush(QBrush(QColor(255, 80, 80, 80)))
        p.setPen(Qt.NoPen)
        p.drawEllipse(dot_center, 18, 18)
        # solid dot
        p.setBrush(QBrush(QColor("#d63838")))
        p.setPen(QPen(QColor("#5a1414"), 2))
        p.drawEllipse(dot_center, 10, 10)

        # tiny label under the dot
        p.setPen(QColor("#3a3a3a"))
        p.setFont(QFont("Arial", 8))
        fm = QFontMetrics(p.font())
        text_w = fm.horizontalAdvance(self.dot_label)
        p.drawText(int(dot_center.x() - text_w / 2),
                   int(dot_center.y() + 32), self.dot_label)

        p.end()


# ----------------------------------------------------------------------------
# staff console widget -- styled to look like a wall-mounted monitor
# ----------------------------------------------------------------------------

class StaffConsole(QFrame):
    """staff monitoring console panel. just a list of alerts that grows
    as events fire. clicking an alert tells the parent demo to show the
    related recording. nothing fancy, this is the demo not the real product."""

    def __init__(self, on_alert_click, parent=None):
        super().__init__(parent)
        self._on_alert_click = on_alert_click

        self.setObjectName("StaffConsole")
        self.setStyleSheet("""
            #StaffConsole {
                background-color: #1f1f24;
                border: 4px solid #2a2a30;
                border-radius: 6px;
            }
            QLabel#consoleHeader {
                color: #f0f0f0;
                font-weight: bold;
                padding: 6px;
            }
            QListWidget {
                background-color: #15151a;
                color: #e0e0e0;
                border: none;
                font-family: "Consolas", "Courier New", monospace;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 6px;
                border-bottom: 1px solid #2a2a30;
            }
            QListWidget::item:selected {
                background-color: #303040;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        header = QLabel("STAFF MONITORING CONSOLE")
        header.setObjectName("consoleHeader")
        layout.addWidget(header)

        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self._handle_click)
        layout.addWidget(self.list_widget, stretch=1)

        # remember which alert payload goes with which list item
        self._alert_payloads = {}

    def add_alert(self, alert):
        """drop a new alert into the console. severity drives color."""
        sev = alert["severity"]
        prefix = f"[{sev.upper():<8}]"
        text = f"{prefix} {alert['title']}\n   src: {alert['source']}  ({alert['use_case']})"
        item = QListWidgetItem(text)
        item.setForeground(QColor(SEVERITY_COLORS.get(sev, "#cccccc")))
        if sev == "critical":
            f = item.font()
            f.setBold(True)
            item.setFont(f)
        self.list_widget.addItem(item)
        self.list_widget.scrollToBottom()
        self._alert_payloads[id(item)] = alert

    def clear_alerts(self):
        self.list_widget.clear()
        self._alert_payloads.clear()

    def _handle_click(self, item):
        alert = self._alert_payloads.get(id(item))
        if alert is not None:
            self._on_alert_click(alert)


# ----------------------------------------------------------------------------
# smart watch widget -- styled to look like a Garmin Venu 3 sitting on the desk
# ----------------------------------------------------------------------------

class SmartWatch(QFrame):
    """tiny widget that mimics a watch face. only displays the most recent
    alert. urgent alerts make the bezel turn orange, critical turns red."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(180, 220)
        self._severity = "info"
        self._title = "All clear"
        self._description = "(no active alerts)"

    def show_alert(self, alert):
        self._severity = alert["severity"]
        self._title = alert["title"]
        self._description = alert["description"]
        self.update()

    def clear(self):
        self._severity = "info"
        self._title = "All clear"
        self._description = "(no active alerts)"
        self.update()

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        bezel_color = QColor(SEVERITY_COLORS.get(self._severity, "#444444"))

        # band, kind of a hack, just two strips above and below the watch face
        p.setBrush(QColor("#2a2a2a"))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(20, 0, self.width() - 40, 30, 8, 8)
        p.drawRoundedRect(20, self.height() - 30, self.width() - 40, 30, 8, 8)

        # watch body
        body_rect = QRectF(0, 20, self.width(), self.height() - 40)
        p.setBrush(bezel_color)
        p.drawRoundedRect(body_rect, 28, 28)

        # screen
        screen_rect = body_rect.adjusted(10, 10, -10, -10)
        p.setBrush(QColor("#0a0a0f"))
        p.drawRoundedRect(screen_rect, 18, 18)

        # text on the screen
        p.setPen(QColor("#f0f0f0"))
        p.setFont(QFont("Arial", 8, QFont.Bold))
        p.drawText(screen_rect.adjusted(8, 8, -8, -8),
                   Qt.AlignTop | Qt.AlignHCenter,
                   self._severity.upper())

        p.setFont(QFont("Arial", 8))
        p.drawText(screen_rect.adjusted(8, 28, -8, -8),
                   Qt.TextWordWrap | Qt.AlignTop | Qt.AlignHCenter,
                   self._title)


# ----------------------------------------------------------------------------
# video / recording panel -- this is the thing that animates outward
# ----------------------------------------------------------------------------

class RecordingPanel(QFrame):
    """when an alert is clicked (or auto-shown), this panel animates from
    the source location on the gym floor outward to a viewable size, then
    plays the related video. close button shrinks it back.

    don't overthink the animation, it's QPropertyAnimation on geometry.
    """

    def __init__(self, gym_floor, parent=None):
        super().__init__(parent)
        self._gym_floor = gym_floor
        self.setVisible(False)
        self.setStyleSheet("""
            QFrame {
                background-color: #15151a;
                border: 3px solid #c8842c;
                border-radius: 8px;
            }
            QLabel {
                color: #f0f0f0;
                background: transparent;
                border: none;
                padding: 4px;
            }
            QPushButton {
                background-color: #c8842c;
                color: white;
                font-weight: bold;
                padding: 4px 12px;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover { background-color: #d99a40; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        header_row = QHBoxLayout()
        self.header_label = QLabel("RECORDING")
        font = QFont("Arial", 10, QFont.Bold)
        self.header_label.setFont(font)
        header_row.addWidget(self.header_label, stretch=1)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.collapse_and_hide)
        header_row.addWidget(close_btn)
        layout.addLayout(header_row)

        # video widget if available, else a placeholder
        if HAS_MEDIA:
            self.video_widget = QVideoWidget(self)
            self.video_widget.setStyleSheet("background-color: black;")
            layout.addWidget(self.video_widget, stretch=1)
            self.player = QMediaPlayer(self)
            self.player.setVideoOutput(self.video_widget)
        else:
            self.video_widget = QLabel("(video playback not available -- "
                                       "PyQt5.QtMultimedia missing)")
            self.video_widget.setAlignment(Qt.AlignCenter)
            self.video_widget.setStyleSheet(
                "background-color: black; color: white;")
            layout.addWidget(self.video_widget, stretch=1)
            self.player = None

        self.subtitle = QLabel("")
        self.subtitle.setWordWrap(True)
        self.subtitle.setStyleSheet("color: #c0c0c0; font-size: 11px;")
        layout.addWidget(self.subtitle)

        # animation handle stored so we can stop it mid-flight
        self._anim = None

    def open_for_alert(self, alert, source_location_id, video_path=None):
        """expand outward from the source location and start the video."""
        self.header_label.setText(f"RECORDING -- {alert['title']}")
        self.subtitle.setText(f"{alert['description']}\nfile: "
                              f"{video_path or '(no video available)'}")

        # figure out start and end geometry for the animation
        start_pt = self._gym_floor.location_pixel(source_location_id)
        # start_pt is in gym-floor coords, translate to our parent's coords
        global_pt = self._gym_floor.mapTo(self.parentWidget(), start_pt.toPoint())

        start_size = QSize(20, 20)
        # end size, big enough to actually see the video
        parent = self.parentWidget()
        end_w = min(560, parent.width() - 80)
        end_h = min(360, parent.height() - 100)
        # center in the parent for the final position
        end_x = (parent.width() - end_w) // 2
        end_y = (parent.height() - end_h) // 2

        from PyQt5.QtCore import QRect
        start_rect = QRect(global_pt.x(), global_pt.y(),
                           start_size.width(), start_size.height())
        end_rect = QRect(end_x, end_y, end_w, end_h)

        self.setGeometry(start_rect)
        self.raise_()
        self.show()

        if self._anim is not None:
            self._anim.stop()
        # parent the anim to self so qt cleans it up properly with the panel
        self._anim = QPropertyAnimation(self, b"geometry", self)
        self._anim.setDuration(550)
        self._anim.setStartValue(start_rect)
        self._anim.setEndValue(end_rect)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.start()

        # kick off video playback
        if HAS_MEDIA and self.player is not None and video_path:
            url = QUrl.fromLocalFile(os.path.abspath(video_path))
            self.player.setMedia(QMediaContent(url))
            self.player.play()

    def collapse_and_hide(self):
        # stop video before shrinking
        if HAS_MEDIA and self.player is not None:
            self.player.stop()

        if self._anim is not None:
            self._anim.stop()
        # just shrink to current top-left then hide. simple.
        from PyQt5.QtCore import QRect
        cur = self.geometry()
        end_rect = QRect(cur.x() + cur.width() // 2,
                         cur.y() + cur.height() // 2, 10, 10)
        self._anim = QPropertyAnimation(self, b"geometry", self)
        self._anim.setDuration(300)
        self._anim.setStartValue(cur)
        self._anim.setEndValue(end_rect)
        self._anim.setEasingCurve(QEasingCurve.InCubic)
        self._anim.finished.connect(self.hide)
        self._anim.start()


# ----------------------------------------------------------------------------
# event log -- bottom strip showing what just happened
# ----------------------------------------------------------------------------

class EventLog(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame { background-color: #fafafa; border: 1px solid #cccccc; }
            QListWidget { background-color: #fafafa; border: none;
                          font-family: Consolas, monospace; font-size: 11px; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        layout.addWidget(QLabel("Event Log"))
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

    def log(self, msg):
        item = QListWidgetItem(msg)
        self.list_widget.addItem(item)
        self.list_widget.scrollToBottom()

    def clear(self):
        self.list_widget.clear()


# ----------------------------------------------------------------------------
# main window glues everything together
# ----------------------------------------------------------------------------

class GSMDemoWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GSM Demo -- Gym Space Monitoring (Team T07)")
        self.resize(1180, 820)

        # try to load member profiles for nicer dot labels. if it fails
        # (e.g. running from wrong cwd), just fall back to fake names.
        self.members = {}
        try:
            with open("members_profile.json", "r") as f:
                self.members = json.load(f)
        except Exception as e:
            print(f"[demo] couldn't load members_profile.json ({e}), using fake names")

        # find videos / sounds once
        self.videos = find_videos()
        self.sounds = find_sounds()

        # demo state
        self.script_idx = 0  # which event in DEMO_SCRIPT we're on next
        self.is_running = False

        self._build_ui()
        self._reset_dot_to_entrance()

    # ---- UI construction -------------------------------------------------

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(8)

        # top: gym floor (the recording panel will be a child of this so
        # the animation looks like it grows out of the gym)
        self.gym_floor = GymFloor()
        outer.addWidget(self.gym_floor, stretch=3)

        self.recording_panel = RecordingPanel(self.gym_floor, parent=central)

        # middle row: console + smart watch + event log
        middle = QHBoxLayout()
        middle.setSpacing(8)

        self.console = StaffConsole(on_alert_click=self._on_alert_clicked)
        middle.addWidget(self.console, stretch=3)

        # the watch sits in a "countertop" frame so it visually reads as
        # being on the desk next to the console. cosmetic only.
        watch_frame = QFrame()
        watch_frame.setStyleSheet("""
            QFrame { background-color: #c9b08a; border-radius: 6px; }
        """)
        watch_box = QVBoxLayout(watch_frame)
        watch_box.setAlignment(Qt.AlignCenter)
        watch_label = QLabel("Smart Watch (countertop)")
        watch_label.setAlignment(Qt.AlignCenter)
        watch_box.addWidget(watch_label)
        self.smart_watch = SmartWatch()
        watch_box.addWidget(self.smart_watch, alignment=Qt.AlignCenter)
        middle.addWidget(watch_frame, stretch=1)

        self.event_log = EventLog()
        middle.addWidget(self.event_log, stretch=2)

        outer.addLayout(middle, stretch=2)

        # bottom: control buttons
        controls = QHBoxLayout()
        controls.setSpacing(8)
        self.btn_start  = QPushButton("Start Demo")
        self.btn_next   = QPushButton("Next Event")
        self.btn_reset  = QPushButton("Reset Demo")
        self.btn_clear  = QPushButton("Clear Alerts")
        for b in (self.btn_start, self.btn_next, self.btn_reset, self.btn_clear):
            b.setMinimumHeight(36)
            controls.addWidget(b)
        outer.addLayout(controls)

        self.btn_start.clicked.connect(self._start_demo)
        self.btn_next.clicked.connect(self._next_event)
        self.btn_reset.clicked.connect(self._reset_demo)
        self.btn_clear.clicked.connect(self._clear_alerts)

        # status line
        self.status_label = QLabel("ready. press Start Demo to begin.")
        self.status_label.setStyleSheet(
            "color: #555; font-style: italic; padding: 2px;")
        outer.addWidget(self.status_label)

    # ---- demo controls ---------------------------------------------------

    def _start_demo(self):
        if self.is_running:
            return
        self.is_running = True
        self.script_idx = 0
        self.event_log.log("=== demo started ===")
        # auto-advance through events on a timer so it plays itself, but
        # still let the user step manually if they want
        self._auto_timer = QTimer(self)
        self._auto_timer.setInterval(5000)  # 5s between events, room to talk
        self._auto_timer.timeout.connect(self._next_event)
        # do the first event right away then start the timer
        self._next_event()
        self._auto_timer.start()
        self.status_label.setText("demo running. (next event in 5s, or click Next Event)")

    def _next_event(self):
        if self.script_idx >= len(DEMO_SCRIPT):
            # all done
            self.event_log.log("=== demo complete ===")
            self.status_label.setText("demo complete. press Reset to run again.")
            if hasattr(self, "_auto_timer"):
                self._auto_timer.stop()
            self.is_running = False
            return

        step = DEMO_SCRIPT[self.script_idx]
        self.script_idx += 1
        self._run_step(step)

    def _reset_demo(self):
        if hasattr(self, "_auto_timer"):
            self._auto_timer.stop()
        self.is_running = False
        self.script_idx = 0
        self.console.clear_alerts()
        self.smart_watch.clear()
        self.event_log.clear()
        self.recording_panel.hide()
        self._reset_dot_to_entrance()
        self.status_label.setText("reset. press Start Demo to begin again.")

    def _clear_alerts(self):
        self.console.clear_alerts()
        self.smart_watch.clear()
        self.event_log.log("alerts cleared by staff")

    # ---- per-step execution ---------------------------------------------

    def _run_step(self, step):
        loc_id = step["location"]
        alert = step["alert"]

        # 1. animate the dot to the location
        self._move_dot_to(loc_id)

        # 2. update the dot label with a member name (cosmetic, just makes
        #    the demo feel more concrete during presentation)
        self._set_dot_label_for(alert)

        # 3. flash the location, fire alerts on console + watch, log the event
        # delay slightly so the dot has visibly arrived first. small thing
        # but it reads way better in front of an audience.
        QTimer.singleShot(500, lambda: self._dispatch_alert(loc_id, alert))

    def _dispatch_alert(self, loc_id, alert):
        self.gym_floor.flash_location(loc_id)

        if alert.get("to_console"):
            self.console.add_alert(alert)
        if alert.get("to_watch"):
            self.smart_watch.show_alert(alert)
            # try to play a wav if any are present, else just system beep
            self._play_alert_sound(alert)

        self.event_log.log(
            f"[{alert['use_case']:<10}] {alert['severity']:<8} "
            f"{loc_id} -- {alert['title']}"
        )
        self.status_label.setText(
            f"event {self.script_idx}/{len(DEMO_SCRIPT)}: {alert['title']}"
        )

    def _on_alert_clicked(self, alert):
        # find the location this alert came from by walking the script.
        # this is kind of a hack but the script is short so whatever.
        loc_id = "entrance"
        for step in DEMO_SCRIPT:
            if step["alert"]["title"] == alert["title"]:
                loc_id = step["location"]
                break

        video_path = self._video_for_alert(alert)
        self.recording_panel.open_for_alert(alert, loc_id, video_path)
        self.event_log.log(f"opened recording for: {alert['title']}")

    # ---- dot movement / labels ------------------------------------------

    def _reset_dot_to_entrance(self):
        ex, ey, _, _ = LOCATIONS["entrance"]
        self.gym_floor.set_dot_x(ex)
        self.gym_floor.set_dot_y(ey)
        self.gym_floor.dot_label = "(no member)"
        self.gym_floor.update()

    def _move_dot_to(self, location_id):
        ex, ey, _, _ = LOCATIONS[location_id]
        # animate x and y in parallel using two animations. yes this is
        # two animations not one, but doing it through a path requires more
        # ceremony. don't overthink it.
        anim_x = QPropertyAnimation(self.gym_floor, b"dot_x", self)
        anim_x.setDuration(1200)
        anim_x.setStartValue(self.gym_floor.dot_x)
        anim_x.setEndValue(ex)
        anim_x.setEasingCurve(QEasingCurve.InOutQuad)
        anim_x.start()

        anim_y = QPropertyAnimation(self.gym_floor, b"dot_y", self)
        anim_y.setDuration(1200)
        anim_y.setStartValue(self.gym_floor.dot_y)
        anim_y.setEndValue(ey)
        anim_y.setEasingCurve(QEasingCurve.InOutQuad)
        anim_y.start()

        # keep refs alive, otherwise gc nukes them mid-animation
        self._last_anims = (anim_x, anim_y)

    def _set_dot_label_for(self, alert):
        # try to extract a member name from the alert title if it's there,
        # otherwise just show the use case
        if "--" in alert["title"]:
            # e.g. "Heart rate deviation -- Brian Castillo (002)"
            name_chunk = alert["title"].split("--", 1)[1].strip()
            self.gym_floor.dot_label = name_chunk
        else:
            self.gym_floor.dot_label = f"member ({alert['use_case']})"
        self.gym_floor.update()

    # ---- assets ----------------------------------------------------------

    def _video_for_alert(self, alert):
        if not self.videos:
            return None
        # we don't actually know which video matches which event, so just
        # round-robin through whatever's in the folder. for the demo this
        # is fine -- presenter can talk over it.
        idx = (DEMO_SCRIPT.index(
            next(s for s in DEMO_SCRIPT if s["alert"]["title"] == alert["title"])
        )) % len(self.videos)
        return self.videos[idx]

    def _play_alert_sound(self, alert):
        # if .wav files exist, play one. otherwise system beep so there's at
        # least an audio cue for the audience.
        if HAS_MEDIA and self.sounds:
            sev = alert["severity"]
            # match severity to file index if possible
            idx = {"passive": 0, "urgent": 1, "critical": 2}.get(sev, 0)
            if idx >= len(self.sounds):
                idx = 0
            try:
                effect = QSoundEffect(self)
                effect.setSource(QUrl.fromLocalFile(
                    os.path.abspath(self.sounds[idx])))
                effect.setVolume(0.6)
                effect.play()
                # keep ref alive
                self._last_sound = effect
                return
            except Exception:
                pass
        # fallback
        QApplication.beep()


# ----------------------------------------------------------------------------
# entry point
# ----------------------------------------------------------------------------

def main():
    app = QApplication(sys.argv)
    win = GSMDemoWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
