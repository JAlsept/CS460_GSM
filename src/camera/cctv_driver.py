# CCTV Camera Driver - Simulates incoming video feeds from gym section cameras
# In the real system this driver would receive live streams from the CCTV cameras
# For the demo, this returns a dictionary of pre-recorded video file paths per section
#
# Camera sections explained:
#   free_weights    - camera covering the free weights area
#   cardio          - camera covering the cardio equipment area
#   weight_machines - camera covering the weight machines area
 
# Returns a dictionary of available camera feeds mapped to their gym section
def get_camera_feeds():
    feeds = {
        "free_weights": {
            "section": "free_weights",
            "video_path": "test_videos/free_weights.mp4",
            "camera_available": False  # no video yet, update path when ready
        },
        "cardio": {
            "section": "cardio",
            "video_path": "test_videos/cardio.mp4",
            "camera_available": False  # no video yet, update path when ready
        },
        "weight_machines": {
            "section": "weight_machines",
            "video_path": "test_videos/man_squatting.mp4",
            "camera_available": True
        }
    }
    return feeds