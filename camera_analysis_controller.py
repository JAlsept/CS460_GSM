# Camera Analysis Controller - Processes video feeds from the CCTV Camera Driver
# Sends video to the Gemini MLLM for analysis and forwards classified events to the Alert Controller
#
# SAD variables:
#   camera_section   - identifies which gym section the camera feed belongs to
#   camera_available - tracks whether the camera feed is currently active
#   api_connected    - tracks whether the Gemini API is reachable and key is valid
#   camera_events    - stores event type and severity results per section

import os
import json
import time
import gsm_data_store
from dotenv import load_dotenv
from google import genai
from google.genai import types
from camera_cctv_driver import get_free_weights_feed, get_cardio_feed, get_weight_machines_feed
from alert_controller import AlertController
from report_controller import ReportController

load_dotenv()

# Initialize Report and Alert Controllers
report_controller = ReportController()
alert_controller = AlertController(report_controller)

# Controller state variables (per SAD)
camera_section = None
camera_available = False
api_connected = False

# Stores event results per section so no data is overwritten between videos
# Can also be read by Jake's Report Controller for logging
camera_events = {}

# Initialize Gemini client using API key from .env
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


# Verifies the Gemini API is reachable before any video analysis is attempted
def test_connection():
    global api_connected
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents="Say 'GSM connection successful' and nothing else."
    )
    print("API Status:", response.text)
    api_connected = True


# Verifies the camera feed for the assigned section is available and readable
def check_camera(video_path):
    if os.path.exists(video_path):
        print(f"[OK] Camera check passed: {video_path} is available")
        return True
    else:
        print(f"[OFFLINE] Camera feed unavailable - {video_path} not found")
        return False


# Notifies the Alert Controller that the camera feed for the specified section is unavailable
def report_camera_offline(section):
    description = f"Camera feed offline for section: {section}"
    alert_controller.receive_alert("N/A", "CameraAnalysisController", description)


# Parses the JSON response from Gemini and stores event type and severity per section
def parse_response(response_text, section):
    global camera_events
    parsed = json.loads(response_text)
    camera_events[section] = {
        "event_type": parsed.get("event_type", "none"),
        "severity": parsed.get("severity", "none")
    }
    return parsed


# Submits the video feed to the Gemini MLLM and forwards the classified event to the Alert Controller
def analyze_frame(video_path, section):
    with open(video_path, 'rb') as f:
        video_bytes = f.read()

    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=types.Content(
            parts=[
                types.Part(
                    inline_data=types.Blob(
                        data=video_bytes,
                        mime_type='video/mp4'
                    )
                ),
                types.Part(text="""Analyze this video and detect any safety or form related events.
Respond ONLY in JSON format with no extra text or markdown backticks.
Use this exact structure:
{
    "event_detected": true or false,
    "event_type": "fall" or "poor_form" or "distress" or "none",
    "severity": "critical" or "urgent" or "passive" or "none",
    "section": "free_weights" or "cardio" or "weight_machines",
    "description": "describe in detail what is happening in this video"
}

Guidelines:
- fall: person loses balance, collapses, or is motionless on the floor
- poor_form: unsafe exercise technique that could cause injury
- distress: signs of physical pain or injury during exercise
- severity critical: fall or serious injury requiring immediate emergency response
- severity urgent: potentially dangerous condition requiring immediate staff response
- severity passive: form correction or minor concern
- severity none: normal activity detected
""")
            ]
        )
    )

    parsed = parse_response(response.text, section)

    # Forward to Alert Controller and log to data store if an event was detected
    if parsed.get("event_detected"):
        description = f"[{section.upper()}] {parsed.get('description')}"
        receive_alert("N/A", "CameraAnalysisController", description)
        gsm_data_store.log_alert({
            "alert_id": f"CAM_{parsed.get('event_type', 'EVENT').upper()}_{section.upper()}",
            "source": "CameraAnalysisController",
            "member_id": "N/A",
            "description": description,
            "severity": parsed.get("severity", "none"),
            "acknowledged": False
        })
    else:
        print(f"[OK] No events detected in {section} section - {parsed.get('description')}")


# Determines which driver method to call based on the section being entered
# Called by the GUI when a demo person enters a specific gym section
def analyze_section(section):
    print(f"\nProcessing section: {section}")
    if section == "free_weights":
        video_path = get_free_weights_feed()
    elif section == "cardio":
        video_path = get_cardio_feed()
    elif section == "weight_machines":
        video_path = get_weight_machines_feed()
    else:
        print(f"[ERROR] Unknown section: {section}")
        return

    if check_camera(video_path):
        analyze_frame(video_path, section)
    else:
        report_camera_offline(section)


# Entry point for the Camera Analysis Controller
# For testing purposes cycles through all three sections
# In the full demo the GUI will call analyze_section() directly
def run_camera_analysis():
    print("Camera Analysis Controller started - scanning video feeds...\n")

    gsm_data_store.initialize()
    test_connection()

    for section in ["free_weights", "cardio", "weight_machines"]:
        analyze_section(section)
        print("Waiting before next API call...")
        time.sleep(3)

    print("\nCamera analysis complete.")
    gsm_data_store.print_store_summary()


# Temporary - for testing purposes only
# Once the Staff Monitoring Console is built this will be called from there instead
if __name__ == "__main__":
    run_camera_analysis()