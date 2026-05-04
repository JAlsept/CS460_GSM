# CS460_GSM

Gym Space Monitoring system for CS 460, Team T07. The system monitors a gym
using wearable smart watches, CCTV camera analysis, environmental sensors,
equipment sensors, RFID check-in, and a staff monitoring console. The plan
is to wire all the controllers together and run a presentation demo.

If something doesn't work, ping the group chat before going down a debugging
rabbit hole. Likely someone else hit the same thing already.

## What lives where

```
CS460_GSM/
├── biometric/
│   ├── biometric_controller.py        # processes Garmin Venu 3 readings
│   └── garmin_driver.py               # mock biometric data per member
│
├── camera/
│   ├── camera_analysis_controller.py  # sends video to Gemini, gets alerts
│   └── cctv_driver.py                 # which video file goes with which section
│
├── CheckInTerminal_Controller.py      # RFID check-in, capacity tracking
├── CheckInTerminal_Driver.py          # mock terminal events
│
├── environmental_controller.py        # temp / humidity / air quality checks
├── environmental_sensor_driver.py     # mock environmental readings
│
├── equipment_sensor_driver.py         # mock equipment usage data
│
├── gsm_data_store.py                  # central in-memory store for all controllers
├── members_profile.json               # 15 member profiles with baselines
│
├── gsm_gui_demo.py                    # the presentation GUI demo
├── GUI.py                             # empty stub, can delete
│
├── videos/                            # drop alert .mp4 files here (gitignored)
└── sounds/                            # drop alert .wav files here (gitignored)
```

The `videos/` and `sounds/` folders are optional. The demo searches a few
fallback paths so it works whether the videos are in `videos/`, in a sibling
`CS460/` folder, or missing entirely.

## Setup, three steps

1. **Install PyQt5.**

   ```bash
   pip install PyQt5
   ```

   That's the only hard dependency for the GUI. The Camera Analysis Controller
   needs `google-genai` and `python-dotenv` separately if you're running it
   live, but the demo doesn't call it.

2. **Drop the alert videos into `videos/`.** (optional but recommended for the
   presentation.) The 11 `IMG_xxxx.mp4` files from the alert videos zip can go
   straight in there. If you'd rather leave them in a sibling `CS460/` folder,
   the demo finds them there too.

3. **Run the demo.**

   ```bash
   python gsm_gui_demo.py
   ```

   The window opens with the dot at the entrance. Press **Start Demo** to
   begin.

## Running the demo

Four buttons at the bottom of the window:

- **Start Demo** -- begins the scripted run, auto-advances every 5 seconds
- **Next Event** -- step manually if you'd rather control the pacing
- **Reset Demo** -- nukes everything, dot goes back to the entrance
- **Clear Alerts** -- mimics staff acknowledging active alerts (clears
  console + watch but doesn't stop the demo)

Click any alert in the staff console list to pop the recording panel. It
animates outward from the spot on the gym floor where the alert came from
and plays the corresponding video. Close button shrinks it back.

## What the demo shows

The dot walks through six events that cover the main use cases from the SRS:

| # | Location        | Use Case                          | Severity | Console | Watch |
|---|-----------------|-----------------------------------|----------|---------|-------|
| 1 | Entrance        | UC7 Maximum capacity              | urgent   | yes     | no    |
| 2 | Cardio          | UC1 Heart rate deviation          | urgent   | yes     | yes   |
| 3 | Weight Machines | UC5 Injury during workout         | critical | yes     | yes   |
| 4 | Free Weights    | UC4 Unsafe deadlift form          | passive  | yes     | yes   |
| 5 | Air Sensor      | UC6 Air quality threshold         | urgent   | yes     | yes   |
| 6 | Cardio          | exception, CCTV camera offline    | passive  | yes     | no    |

All the numbers in the alert text (HR 155 vs baseline 75, CO2 at 1250 ppm,
fall detection on member 008, etc.) come from the existing mock data in
`garmin_driver.py` and `environmental_sensor_driver.py`. So the demo stays
consistent with what the real backend would produce.

## Things to know

**The Alert Controller is simulated inline in `gsm_gui_demo.py`.** There's no
real `alert_controller.py` in the repo yet. The demo has a `DEMO_SCRIPT`
constant near the top of the file that defines all six events. When someone
implements the actual Alert Controller per the SAD, swapping the script out
for live calls will be a small change.

**The dot is one client, not 16.** The SRS supports up to 16 members, but for
presentation clarity one moving dot is way easier to follow. The capacity
alert in step 1 simulates a 17th attempted check-in.

**Asset paths are searched, not hardcoded.** The demo looks for videos in
`videos/`, `../CS460/`, `test_videos/`, and `../test_videos/` in that order.
First folder with `.mp4` files wins. Sounds are only searched in `sounds/`.
Missing assets degrade gracefully, the demo still runs.

**Video-to-event mapping is round-robin.** The `IMG_xxxx.mp4` filenames don't
say which alert they belong to, so the demo just cycles through whatever it
finds. If you rename them to something like `cardio_hr.mp4`, `injury.mp4`,
`form.mp4` we can wire them by name -- ping the group chat.

**Wav files are optional.** None ship in the repo. If you drop
`passive.wav`, `urgent.wav`, `critical.wav` into `sounds/`, the demo plays
them based on alert severity. Otherwise it uses `QApplication.beep()` so
there's at least an audio cue for the audience.

**The empty `GUI.py` is leftover from earlier scaffolding.** Delete it
whenever, the demo doesn't use it.

## If something goes wrong

- **`ModuleNotFoundError: No module named 'PyQt5'`** -- run `pip install PyQt5`.
- **`PyQt5 multimedia not available, video panel will show placeholder text`**
  -- this prints on startup and is fine, the rest of the demo still works.
  If you want videos, install with `pip install PyQt5 PyQtMultimedia` (or
  on Windows the regular PyQt5 install usually includes it).
- **Black video panel, no playback** -- on Windows you may need codec packs
  (K-Lite or LAV) for `.mp4` to play through Qt. Not worth fighting before
  the presentation, the panel still expands and shows the alert text.
- **Demo runs too fast / too slow** -- change `setInterval(5000)` in
  `_start_demo` inside `gsm_gui_demo.py`. 5000 ms is the default time
  between events.
- **No videos found anywhere** -- the demo prints
  `[demo] no .mp4 files found in any of: [...]` on startup. Check that your
  videos are in one of the listed folders.
