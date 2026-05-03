# CCTV Camera Driver - Simulates incoming video feeds from gym section cameras
# In the real system this driver would receive live streams from the CCTV cameras
# For the demo, each method returns the file path for a specific gym section
#
# Camera sections explained:
#   free_weights    - camera covering the free weights area
#   cardio          - camera covering the cardio equipment area
#   weight_machines - camera covering the weight machines area

# Returns the video feed path for the free weights section
def get_free_weights_feed():
    return "test_videos/free_weights.mp4"

# Returns the video feed path for the cardio section
def get_cardio_feed():
    return "test_videos/cardio.mp4"

# Returns the video feed path for the weight machines section
def get_weight_machines_feed():
    return "test_videos/man_squatting.mp4"