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

# OpenCV is the reliable cross-platform decode path. QMediaPlayer on Windows
# uses Windows Media Foundation which is allergic to half the H.264 variants
# our cameras output -- that's why the panel shows a black rectangle even
# when the file is found. cv2.VideoCapture uses its own ffmpeg pipeline and
# doesn't care about system codecs.
#
# install on a teammate's box with: pip install opencv-python
# if cv2 isn't there, we fall back to QMediaPlayer (still might work on macOS
# / Linux / a Windows box with K-Lite Codec Pack installed).
try:
    import cv2  # noqa: F401  -- used inside CvVideoPlayer
    HAS_CV2 = True
    print("[demo] OpenCV available -- using it as the primary video decoder.")
except ImportError:
    HAS_CV2 = False
    print("[demo] OpenCV not installed. recommended: pip install opencv-python")
    print("       falling back to QMediaPlayer (may show black frames if "
          "codecs are missing on Windows).")

import subprocess  # for the "Open Externally" fallback button


# ----------------------------------------------------------------------------
# config / constants
# ----------------------------------------------------------------------------

# yeah this is ugly but stable. layout positions are normalized 0-1 inside the
# gym floor widget so resizing kinda works. see GymFloor._abs_to_pixel.
#
# layout intent (top-down view of the gym):
#   row 1 (top, "workout floor"):   Cardio  |  Weight Machines  |  Free Weights
#   row 2 (middle):                          Air Quality Sensor
#   row 3 (bottom, "lobby"):        Check-In / RFID    [staff desk decoration]
LOCATIONS = {
    # location_id : (x_norm, y_norm, label, color)
    "entrance":         (0.18, 0.85, "Check-In / RFID",     "#5b8aa6"),
    "cardio":           (0.18, 0.27, "Cardio",              "#a45c7a"),
    "weight_machines":  (0.50, 0.27, "Weight Machines",     "#5c9c6a"),
    "free_weights":     (0.82, 0.27, "Free Weights",        "#a08a4c"),
    "env_sensor":       (0.50, 0.55, "Air Quality Sensor",  "#7a7a9c"),
}

# normalized rectangle size for each zone box. centered on the LOCATIONS point.
# kept separate from LOCATIONS so we don't break any of the (x,y,label,color)
# unpack sites elsewhere in the file. don't overthink it.
ZONE_BOXES = {
    # location_id : (w_norm, h_norm)
    "entrance":         (0.30, 0.14),
    "cardio":           (0.27, 0.32),
    "weight_machines":  (0.27, 0.32),
    "free_weights":     (0.27, 0.32),
    "env_sensor":       (0.18, 0.12),
}

# severity colors for the console / watch alerts
SEVERITY_COLORS = {
    "passive":  "#3d6e8c",
    "urgent":   "#c8842c",
    "critical": "#b73a3a",
    "info":     "#6a6a6a",
}

# look in a few likely places for the alert videos. we now scan ALL of them and
# union the results, instead of "first one wins", because the demo machine might
# have CS460/ at the repo root AND a videos/ override folder for backups. don't
# overthink this -- more paths checked = fewer broken demos.
#
# common extensions the team has used at various points. .mp4 is the default but
# being permissive doesn't cost anything.
VIDEO_EXTENSIONS = (".mp4", ".mov", ".avi", ".mkv", ".webm")

VIDEO_SEARCH_PATHS = [
    "videos",
    "videos/CS460-AlertVideos/CS460",   # actual nested layout in CS460_GSM/
    "videos/CS460-AlertVideos",
    "videos/CS460",
    "CS460-AlertVideos/CS460",
    "CS460-AlertVideos",
    "CS460",
    "../CS460",
    "GSM_Videos/CS460",
    "../GSM_Videos/CS460",
    "test_videos",
    "../test_videos",
]


# filename keyword classifier. each filename gets bucketed into one of these
# categories by checking which keyword group matches first. order matters --
# more specific buckets come first so e.g. "Hack_Squat_Rerack" goes to
# equipment_usage instead of weight_machines_injury.
#
# don't overthink this, it just maps filenames to alerts.
VIDEO_CATEGORY_KEYWORDS = [
    # camera/system offline -- check before "camera" lands in cardio etc.
    ("camera_offline", [
        "camera_offline", "offline", "unavailable", "no_signal", "feed_lost",
    ]),
    # equipment usage / rerack -- specific words first so we don't grab these
    # for the generic "machines" bucket.
    ("equipment_usage", [
        "rerack", "re_rack", "ab_cable", "ab_cable_equipment", "equipment",
        "leg_press", "cable", "machine_usage",
    ]),
    # unsafe form on free weights. RDL = romanian deadlift, our use case 4.
    # poor_form / bad_form / unsafe_form / proper_form all live here so the
    # whole RDL family resolves to the free-weights alert.
    ("free_weights_unsafe_form", [
        "poor_form", "bad_form", "unsafe_form", "proper_form", "form_correction",
        "deadlift", "rdl", "free_weight", "free_weights",
    ]),
    # injury / fall on the weight machines. fall is the strongest signal --
    # the SRS use case 5 alert literally says "fall detected" so we want a
    # fall video to be the primary clip here. hack_squat is the renamed
    # "decline squat" machine so it also belongs to this bucket.
    ("weight_machines_injury", [
        "fall", "injury", "distress", "collapse",
        "hack_squat", "decline_squat", "squat",
    ]),
    # heart rate / cardio
    ("cardio_heart_rate", [
        "treadmill", "cardio", "running", "elliptical", "stationary_bike",
        "heart_rate", "hr_spike",
    ]),
    # environmental sensor
    ("environmental", [
        "air_quality", "co2", "humidity", "temperature", "environment",
        "env_sensor", "air",
    ]),
    # entrance / RFID / capacity
    ("entrance_capacity", [
        "entrance", "rfid", "checkin", "check_in", "capacity", "lobby",
        "front_desk",
    ]),
]


# how each demo event ties to a video category. we look at the event's
# video_hint first (already set per-event in DEMO_SCRIPT), and fall back to
# location_id if hint is missing. critical: order of (hint, category) tuples
# matches more-specific to less-specific.
HINT_TO_CATEGORY = {
    "cardio":        "cardio_heart_rate",
    "weights":       "free_weights_unsafe_form",
    "free_weights":  "free_weights_unsafe_form",
    "machines":      "weight_machines_injury",
    "weight_machines": "weight_machines_injury",
    "injury":        "weight_machines_injury",
    "environment":   "environmental",
    "env_sensor":    "environmental",
    "entrance":      "entrance_capacity",
    "capacity":      "entrance_capacity",
    "rfid":          "entrance_capacity",
    "camera_offline": "camera_offline",
    "equipment":     "equipment_usage",
    "equipment_usage": "equipment_usage",
}


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

# module-level diagnostics so the GUI placeholder can show "where we looked"
# without having to read the terminal. updated by discover_videos().
DISCOVERY_DIAGNOSTICS = {
    "bases":      [],
    "rel_paths":  [],
    "found":      [],
    "did_recurse": False,
    "env_dir":    None,
}


def discover_videos():
    """walk every search path, collect every supported video file, dedupe by
    absolute path, return a sorted list.

    discovery rules, in priority order:
      1. GSM_VIDEO_DIR env var, if set -- bulletproof escape hatch.
      2. each VIDEO_SEARCH_PATHS entry resolved against cwd, the script dir,
         and a few parents of each. handles 'I ran it from the wrong folder'.
      3. shallow recursive walk from the script dir and one parent up, capped
         at depth 4. catches videos in unusual subfolders.

    future me: if videos still don't show up, set
        GSM_VIDEO_DIR=/full/path/to/your/videos
    before running. that beats every heuristic.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # build a wider net of bases: cwd + script_dir + a few parents of each.
    # someone always runs this from the wrong folder during a demo.
    bases = []
    for d in [os.getcwd(), script_dir]:
        cur = os.path.abspath(d)
        for _ in range(4):  # current + 3 parents
            if cur not in bases:
                bases.append(cur)
            parent = os.path.dirname(cur)
            if parent == cur:  # filesystem root
                break
            cur = parent

    seen = set()
    found = []

    # phase 0: explicit GSM_VIDEO_DIR override
    env_dir = os.environ.get("GSM_VIDEO_DIR")
    DISCOVERY_DIAGNOSTICS["env_dir"] = env_dir
    if env_dir:
        env_dir_abs = os.path.abspath(os.path.expanduser(env_dir))
        if os.path.isdir(env_dir_abs):
            print(f"[demo] GSM_VIDEO_DIR override active: {env_dir_abs}")
            for entry in sorted(os.listdir(env_dir_abs)):
                full = os.path.join(env_dir_abs, entry)
                if os.path.isfile(full) and entry.lower().endswith(VIDEO_EXTENSIONS):
                    key = os.path.abspath(full)
                    if key not in seen:
                        seen.add(key)
                        found.append(key)
        else:
            print(f"[demo] GSM_VIDEO_DIR set to '{env_dir}' but that path is "
                  f"not a directory. ignoring.")

    # phase 1: explicit path candidates, each base x each relative path
    for base in bases:
        for rel in VIDEO_SEARCH_PATHS:
            candidate = os.path.normpath(os.path.join(base, rel))
            if not os.path.isdir(candidate):
                continue
            for entry in sorted(os.listdir(candidate)):
                full = os.path.join(candidate, entry)
                if not os.path.isfile(full):
                    continue
                if not entry.lower().endswith(VIDEO_EXTENSIONS):
                    continue
                key = os.path.abspath(full)
                if key in seen:
                    continue
                seen.add(key)
                found.append(key)

    # phase 2: recursive fallback, only if we still have nothing.
    # cheap because we cap depth and skip obvious junk dirs.
    did_recurse = False
    if not found:
        print("[demo] no videos via explicit paths, doing shallow recursive search...")
        did_recurse = True
        max_depth = 4
        SKIP_DIRS = {".git", ".idea", ".vscode", "__pycache__", "node_modules",
                     "venv", ".venv", "env", ".env", "build", "dist", ".tox"}
        walk_roots = [script_dir, os.path.dirname(script_dir)]
        seen_roots = set()
        for walk_root in walk_roots:
            walk_root = os.path.abspath(walk_root)
            if walk_root in seen_roots:
                continue
            seen_roots.add(walk_root)
            if not os.path.isdir(walk_root):
                continue
            base_depth = walk_root.rstrip(os.sep).count(os.sep)
            for root, dirs, files in os.walk(walk_root):
                cur_depth = root.rstrip(os.sep).count(os.sep) - base_depth
                if cur_depth >= max_depth:
                    dirs[:] = []
                    continue
                dirs[:] = [d for d in dirs
                           if not d.startswith(".") and d not in SKIP_DIRS]
                for entry in files:
                    if not entry.lower().endswith(VIDEO_EXTENSIONS):
                        continue
                    full = os.path.join(root, entry)
                    key = os.path.abspath(full)
                    if key in seen:
                        continue
                    seen.add(key)
                    found.append(key)

    found.sort()

    DISCOVERY_DIAGNOSTICS["bases"] = bases
    DISCOVERY_DIAGNOSTICS["rel_paths"] = list(VIDEO_SEARCH_PATHS)
    DISCOVERY_DIAGNOSTICS["found"] = found
    DISCOVERY_DIAGNOSTICS["did_recurse"] = did_recurse

    if found:
        print(f"[demo] discovered {len(found)} video file(s):")
        for f in found:
            print(f"        {os.path.basename(f)}  ({f})")
    else:
        print("[demo] *** STILL no video files found. ***")
        print("[demo] checked these bases:")
        for b in bases:
            print(f"        {b}")
        print(f"[demo] with these relative paths: {VIDEO_SEARCH_PATHS}")
        print("[demo] also did a recursive walk under script_dir + parent.")
        print("[demo] FIX: drop the CS460/ folder next to gsm_gui_demo.py, OR set")
        print("[demo]      GSM_VIDEO_DIR=/full/path/to/videos before launching.")
    return found


def classify_video(path):
    """guess which alert category a video belongs to from its filename.
    returns category id (a key in VIDEO_CATEGORY_KEYWORDS) or 'unknown'.

    this is the whole point of the rename: filenames describe the content,
    so the keyword list maps content to alert types. nothing magical.
    """
    name = os.path.basename(path).lower()
    # normalize: strip extension, replace spaces/dashes with underscores so
    # the keyword "ab_cable" matches "Ab Cable Equipment.mp4" too.
    stem, _ = os.path.splitext(name)
    norm = stem.replace(" ", "_").replace("-", "_")
    for category, keywords in VIDEO_CATEGORY_KEYWORDS:
        for kw in keywords:
            if kw in norm:
                return category
    return "unknown"


def build_video_mapping(video_paths):
    """produce {category: [path, path, ...]} for every discovered video.
    multi-camera angles of the same event end up in the same bucket and we
    pick the first one when an alert fires. unknowns are kept around so we
    can still play SOMETHING if all else fails."""
    mapping = {}
    unmapped = []
    for v in video_paths:
        cat = classify_video(v)
        if cat == "unknown":
            unmapped.append(v)
        mapping.setdefault(cat, []).append(v)

    # log it out -- this is the debug line the team wants for demo prep
    print("[demo] video -> category mapping:")
    if not mapping:
        print("        (nothing to map)")
    for cat in sorted(mapping):
        names = [os.path.basename(p) for p in mapping[cat]]
        print(f"        {cat:<28} -> {names}")
    if unmapped:
        print("[demo] WARNING: could not classify these videos by filename:")
        for u in unmapped:
            print(f"        {os.path.basename(u)}")
    return mapping


def video_for_event(mapping, event_or_alert, location_id=None):
    """given the mapping and either a full demo step or just an alert dict,
    pick the best video path. returns None if nothing is a match -- caller
    has to handle that gracefully (we show a placeholder panel)."""
    if not mapping:
        return None

    # accept either a step dict (has 'alert' + 'location') or just the alert
    if "alert" in event_or_alert and "location" in event_or_alert:
        alert = event_or_alert["alert"]
        loc = event_or_alert["location"]
    else:
        alert = event_or_alert
        loc = location_id

    # explicit "no video" marker. the demo script can flag an event as
    # non-visual (e.g. "Camera offline") by setting video_hint=None. without
    # this check we'd fall back to the location and play whatever clip
    # matches that zone, which would be the WRONG video for the alert.
    if alert and ("video_hint" in alert) and (alert["video_hint"] is None):
        return None

    # 1) prefer the explicit video_hint set in DEMO_SCRIPT
    hint = (alert or {}).get("video_hint")
    if hint:
        cat = HINT_TO_CATEGORY.get(hint.lower())
        if cat and mapping.get(cat):
            return mapping[cat][0]

    # 2) fall back to location_id if hint missed
    if loc:
        cat = HINT_TO_CATEGORY.get(loc.lower())
        if cat and mapping.get(cat):
            return mapping[cat][0]

    # 3) last-ditch: scan the alert title for any keyword we know
    title = (alert or {}).get("title", "").lower()
    for category, keywords in VIDEO_CATEGORY_KEYWORDS:
        if any(kw.replace("_", " ") in title or kw in title for kw in keywords):
            if mapping.get(category):
                return mapping[category][0]

    # nothing matched. caller will show the fallback panel.
    return None


# kept for backwards compat with anything that imports the old name
def find_videos():
    return discover_videos()


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

        # outer wall -- the "room" the gym is in
        wall = self.rect().adjusted(8, 8, -8, -8)
        p.setPen(QPen(QColor("#3a3a3a"), 3))
        p.setBrush(QBrush(QColor("#fbfaf6")))
        p.drawRoundedRect(wall, 8, 8)

        # subtle floor dividers -- not load-bearing, just helps the eye group
        # the workout floor (top) from the lobby/check-in area (bottom).
        p.setPen(QPen(QColor("#e2decd"), 1, Qt.DashLine))
        # horizontal divider between the workout floor and the lobby strip
        div_y = int(wall.top() + wall.height() * 0.66)
        p.drawLine(wall.left() + 16, div_y, wall.right() - 16, div_y)

        # title-ish header
        p.setPen(QColor("#3a3a3a"))
        p.setFont(QFont("Arial", 11, QFont.Bold))
        p.drawText(wall.left() + 12, wall.top() + 22,
                   "Lobo Community Center -- Gym Floor (top-down view)")

        # tiny lobby tag below the divider so the bottom strip reads as
        # front-of-house, not just empty space.
        p.setPen(QColor("#a39b80"))
        f_italic = QFont("Arial", 8)
        f_italic.setItalic(True)
        p.setFont(f_italic)
        p.drawText(wall.left() + 12, div_y + 14, "LOBBY / FRONT DESK")

        # a decorative staff desk to the right of the entrance. cosmetic only,
        # but it visually anchors the staff console + smart watch (which live
        # in the bottom row of the window) to a spot inside the gym.
        desk_rect = QRectF(
            wall.left() + wall.width() * 0.55,
            wall.top() + wall.height() * 0.78,
            wall.width() * 0.34,
            wall.height() * 0.14,
        )
        p.setBrush(QBrush(QColor("#d6c19a")))
        p.setPen(QPen(QColor("#8a7656"), 2))
        p.drawRoundedRect(desk_rect, 6, 6)
        p.setPen(QColor("#5a4a30"))
        p.setFont(QFont("Arial", 9, QFont.Bold))
        p.drawText(desk_rect, Qt.AlignCenter, "STAFF DESK  (console + watch)")

        # draw each zone as a labeled rectangle. sizes come from ZONE_BOXES.
        floor_w = self.width() - 48
        floor_h = self.height() - 48
        for loc_id, (x_norm, y_norm, label, color) in LOCATIONS.items():
            zone_w_norm, zone_h_norm = ZONE_BOXES.get(loc_id, (0.20, 0.18))
            center = self._abs_to_pixel(x_norm, y_norm)
            box_w = int(zone_w_norm * floor_w)
            box_h = int(zone_h_norm * floor_h)
            box = QRectF(center.x() - box_w / 2,
                         center.y() - box_h / 2,
                         box_w, box_h)

            # flash effect when this zone is the source of an active alert
            if loc_id == self._flash_location and self._flash_on:
                fill = QColor("#ffd166")
                border = QColor("#b73a3a")
                border_w = 3
            else:
                fill = QColor(color).lighter(180)
                border = QColor(color)
                border_w = 2

            p.setBrush(QBrush(fill))
            p.setPen(QPen(border, border_w))
            p.drawRoundedRect(box, 8, 8)

            # zone label, uppercase, centered. presentation-friendly.
            p.setPen(QColor("#222222"))
            p.setFont(QFont("Arial", 10, QFont.Bold))
            p.drawText(box, Qt.AlignCenter, label.upper())

        # the dot (the member) -- slightly bigger than before so it's still
        # the most obvious thing on screen even with the larger zone boxes.
        dot_center = self._abs_to_pixel(self._dot_x, self._dot_y)
        # outer glow ring
        p.setBrush(QBrush(QColor(255, 80, 80, 80)))
        p.setPen(Qt.NoPen)
        p.drawEllipse(dot_center, 20, 20)
        # solid dot
        p.setBrush(QBrush(QColor("#d63838")))
        p.setPen(QPen(QColor("#5a1414"), 2))
        p.drawEllipse(dot_center, 11, 11)

        # tiny label under the dot
        p.setPen(QColor("#3a3a3a"))
        p.setFont(QFont("Arial", 8))
        fm = QFontMetrics(p.font())
        text_w = fm.horizontalAdvance(self.dot_label)
        p.drawText(int(dot_center.x() - text_w / 2),
                   int(dot_center.y() + 34), self.dot_label)

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
# OpenCV-based video player widget -- the reliable fallback for codec-less boxes
# ----------------------------------------------------------------------------

class CvVideoPlayer(QFrame):
    """tiny opencv-backed video player. plays a file in a loop, scaled to fit.

    why this exists: QMediaPlayer on Windows is hostile to certain H.264
    encodings -- the panel just stays black even though the file loaded.
    cv2.VideoCapture brings its own ffmpeg, so it bypasses the system codec
    mess entirely. the tradeoff is no audio, but our demo videos are
    surveillance clips so that's fine.

    don't overthink it: cv2 reads frames, we draw them into a QLabel as
    QPixmaps on a QTimer. that's the whole player.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: black;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._label = QLabel("(no video loaded)")
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setStyleSheet("background-color: black; color: #888888;")
        layout.addWidget(self._label)

        self._cap = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._current_path = None

    def play(self, path):
        """open the file and start spitting frames into the label."""
        self.stop()
        if not HAS_CV2:
            self._label.setText("(OpenCV not installed)")
            return False
        # late-import so the file still parses cleanly when cv2 is missing
        import cv2
        self._cap = cv2.VideoCapture(path)
        if not self._cap.isOpened():
            print(f"[demo] cv2 failed to open: {path}")
            self._label.setText("(cv2 could not open this file)")
            self._cap = None
            return False
        fps = self._cap.get(cv2.CAP_PROP_FPS) or 30.0
        # clamp to sane bounds, some videos report 0 or nonsense
        if fps <= 0 or fps > 120:
            fps = 30.0
        interval_ms = max(15, int(1000 / fps))
        self._current_path = path
        self._timer.start(interval_ms)
        print(f"[demo] cv2 playing {os.path.basename(path)} @ ~{fps:.0f} fps")
        return True

    def stop(self):
        self._timer.stop()
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None
        self._label.clear()
        self._label.setText("")

    def _tick(self):
        if self._cap is None:
            return
        import cv2
        ok, frame = self._cap.read()
        if not ok:
            # hit end of file -- loop back so the demo doesn't go dark mid-talk
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            return
        # cv2 hands us BGR, Qt wants RGB
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, _ = rgb.shape
        # bytes(...) copies the buffer so Qt doesn't hold a stale numpy ptr
        from PyQt5.QtGui import QImage, QPixmap
        img = QImage(bytes(rgb.data), w, h, w * 3, QImage.Format_RGB888)
        if self._label.size().width() > 0 and self._label.size().height() > 0:
            pix = QPixmap.fromImage(img).scaled(
                self._label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self._label.setPixmap(pix)


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

        # last-resort fallback: open the video in whatever the system uses
        # for video files. clicking this is guaranteed to work on stage as
        # long as a video player is installed (Windows Media Player, VLC,
        # etc). the in-app playback might or might not, depending on codecs.
        self._open_ext_btn = QPushButton("Open Externally")
        self._open_ext_btn.clicked.connect(self._open_externally)
        self._open_ext_btn.setEnabled(False)
        header_row.addWidget(self._open_ext_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.collapse_and_hide)
        header_row.addWidget(close_btn)
        layout.addLayout(header_row)

        # pick the best available video decoder. cv2 first because it doesn't
        # care about Windows codec drama; QMediaPlayer second; static label
        # last. self._playback_mode tells the rest of the methods which
        # branch they're in.
        self._current_video_path = None  # tracked for the external-open btn
        self.player = None               # only set in 'qt' mode

        if HAS_CV2:
            self.video_widget = CvVideoPlayer(self)
            layout.addWidget(self.video_widget, stretch=1)
            self._playback_mode = "cv2"
            print("[demo] RecordingPanel using cv2 playback mode")
        elif HAS_MEDIA:
            self.video_widget = QVideoWidget(self)
            self.video_widget.setStyleSheet("background-color: black;")
            layout.addWidget(self.video_widget, stretch=1)
            self.player = QMediaPlayer(self)
            self.player.setVideoOutput(self.video_widget)
            # log playback errors so a missing codec doesn't silently kill the
            # demo. QMediaPlayer goes 'No error' until something actually breaks.
            def _on_media_error(*_):
                msg = self.player.errorString() or "(empty error)"
                print(f"[demo] QMediaPlayer error: {msg}")
            self.player.error.connect(_on_media_error)
            # also log media status changes -- useful when stuck on black
            def _on_status_changed(status):
                names = {0: "Unknown", 1: "NoMedia", 2: "Loading",
                         3: "Loaded", 4: "Stalled", 5: "Buffering",
                         6: "Buffered", 7: "EndOfMedia", 8: "InvalidMedia"}
                print(f"[demo] QMediaPlayer status: {names.get(status, status)}")
            self.player.mediaStatusChanged.connect(_on_status_changed)
            self._playback_mode = "qt"
            print("[demo] RecordingPanel using QMediaPlayer playback mode "
                  "(install opencv-python if videos render as black)")
        else:
            self.video_widget = QLabel("(video playback not available -- "
                                       "neither cv2 nor PyQt5.QtMultimedia "
                                       "is installed)")
            self.video_widget.setAlignment(Qt.AlignCenter)
            self.video_widget.setStyleSheet(
                "background-color: black; color: white;")
            layout.addWidget(self.video_widget, stretch=1)
            self._playback_mode = "placeholder"
            print("[demo] RecordingPanel using placeholder mode -- no decoder")

        self.subtitle = QLabel("")
        self.subtitle.setWordWrap(True)
        self.subtitle.setStyleSheet("color: #c0c0c0; font-size: 11px;")
        layout.addWidget(self.subtitle)

        # animation handle stored so we can stop it mid-flight
        self._anim = None

    def open_for_alert(self, alert, source_location_id, video_path=None):
        """expand outward from the source location and start the video.

        if video_path is None or unreadable, we still open the panel and
        show the alert details on a placeholder background. the demo never
        crashes because of a missing/broken video file.
        """
        # resolve to an absolute path if we got something usable
        resolved = None
        if video_path:
            try:
                cand = os.path.abspath(video_path)
                if os.path.isfile(cand):
                    resolved = cand
                else:
                    print(f"[demo] video path does not exist: {cand}")
            except Exception as e:
                print(f"[demo] could not resolve video path '{video_path}': {e}")

        self.header_label.setText(f"RECORDING -- {alert['title']}")
        if resolved:
            file_line = f"file: {os.path.basename(resolved)}"
        else:
            # if video playback breaks, at least show the filename so we
            # don't look lost on stage. include diagnostics so the demo
            # operator can see WHY the lookup failed without checking the
            # terminal.
            n_found = len(DISCOVERY_DIAGNOSTICS.get("found", []))
            if n_found == 0:
                bases = DISCOVERY_DIAGNOSTICS.get("bases", [])
                rels  = DISCOVERY_DIAGNOSTICS.get("rel_paths", [])
                env   = DISCOVERY_DIAGNOSTICS.get("env_dir")
                hint = ""
                if env:
                    hint = f"\nGSM_VIDEO_DIR was set to: {env} (not a valid dir)"
                file_line = ("file: NO VIDEOS DISCOVERED on this machine. "
                             "set GSM_VIDEO_DIR=/path/to/videos and relaunch."
                             f"\nlooked under: {', '.join(bases[:3])}..."
                             f"\nfor subfolders: {rels}" + hint)
            else:
                file_line = (f"file: (no recording mapped for this alert -- "
                             f"{n_found} video(s) discovered, none matched "
                             f"this alert's category)")
        self.subtitle.setText(f"{alert['description']}\n{file_line}")

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

        # remember which file is showing so the Open Externally button works,
        # and toggle that button's enabled state based on whether we have a
        # file to hand off.
        self._current_video_path = resolved
        self._open_ext_btn.setEnabled(bool(resolved))

        # kick off playback in whichever mode the panel was built with.
        if self._playback_mode == "cv2":
            if resolved:
                ok = self.video_widget.play(resolved)
                if not ok:
                    print(f"[demo] cv2 playback failed for {resolved} -- "
                          "try the Open Externally button.")
            else:
                self.video_widget.stop()
        elif self._playback_mode == "qt":
            # always stop any previous media first -- otherwise QMediaPlayer
            # sometimes refuses to load a new file while the old one is still
            # playing, especially on Windows.
            try:
                self.player.stop()
                if resolved:
                    url = QUrl.fromLocalFile(resolved)
                    self.player.setMedia(QMediaContent(url))
                    self.player.play()
                    print(f"[demo] QMediaPlayer playing: {resolved}")
                else:
                    # blank out the video surface so the previous frame
                    # doesn't linger behind the placeholder text
                    self.player.setMedia(QMediaContent())
            except Exception as e:
                print(f"[demo] playback error for '{resolved}': {e}")
        else:  # placeholder mode
            n_found = len(DISCOVERY_DIAGNOSTICS.get("found", []))
            placeholder = (f"(in-app video playback unavailable)\n\n"
                           f"{alert['title']}\n"
                           f"file: {os.path.basename(resolved) if resolved else 'none'}\n"
                           f"({n_found} video(s) discovered total)\n\n"
                           f"click 'Open Externally' to launch in your default "
                           f"video player.")
            self.video_widget.setText(placeholder)

    def _open_externally(self):
        """hand the current video off to the OS default player. this is the
        guaranteed-to-work playback path -- if K-Lite/VLC/Quicktime is
        installed, this just works no matter what's wrong with QMediaPlayer.
        """
        path = self._current_video_path
        if not path or not os.path.isfile(path):
            print("[demo] Open Externally clicked but no current video path")
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
            print(f"[demo] opened externally: {path}")
        except Exception as e:
            print(f"[demo] failed to open externally: {e}")

    def collapse_and_hide(self):
        # stop video before shrinking, depending on which player we built
        if self._playback_mode == "cv2" and isinstance(self.video_widget, CvVideoPlayer):
            self.video_widget.stop()
        elif self._playback_mode == "qt" and self.player is not None:
            self.player.stop()
        # external-open button has nothing to disable here; user can still
        # click it after closing if they want the file in another window.

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
        self.videos = discover_videos()
        self.video_mapping = build_video_mapping(self.videos)
        self.sounds = find_sounds()

        # precompute and log the per-event mapping so during demo prep we
        # can see exactly which clip each alert will play. super useful when
        # debugging at 2am the night before the presentation.
        print("[demo] resolved per-event video assignments:")
        for step in DEMO_SCRIPT:
            v = video_for_event(self.video_mapping, step)
            v_name = os.path.basename(v) if v else "(none -- placeholder will show)"
            print(f"        {step['location']:<18} {step['alert']['title'][:48]:<48} -> {v_name}")

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
        """pick the right video for an alert by walking the demo script back
        to its location, then asking video_for_event for a content-aware match.

        future me: if you click an alert and the wrong video plays, the issue
        is almost always either (a) a filename keyword that's missing from
        VIDEO_CATEGORY_KEYWORDS, or (b) a video_hint typo in DEMO_SCRIPT.
        the resolved mapping is printed at startup, just check that first.
        """
        if not self.video_mapping:
            return None
        # find the matching demo step so we can pass location too
        matching_step = None
        for step in DEMO_SCRIPT:
            if step["alert"]["title"] == alert["title"]:
                matching_step = step
                break
        if matching_step is None:
            # no script match, just try the alert by itself
            return video_for_event(self.video_mapping, alert)
        return video_for_event(self.video_mapping, matching_step)

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
