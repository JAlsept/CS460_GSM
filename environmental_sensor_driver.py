# Environmental Sensor Driver - Simulates incoming readings from gym environmental sensors.
# In the real system this driver would receive live data from physical sensors in the facility.
# For the demo, this returns a hardcoded dictionary of mock readings per gym section.
#
# Sensor types explained:
#   temperature   - ambient air temperature in Fahrenheit (safe range: 61-75F)
#   air_quality   - CO2 concentration in parts per million (safe range: below 1000 ppm)
#   humidity      - relative humidity percentage (safe range: 30-60%)


# Returns a dictionary of mock environmental readings per gym section
def get_environmental_data():
    data = {

        "free_weights": {
            "section": "free_weights",
            "sensor_available": True,
            "temperature": 71.8,    # normal
            "air_quality": 870.0,   # normal
            "humidity": 45.0        # normal
        },

        "cardio": {
            "section": "cardio",
            "sensor_available": True,
            "temperature": 81.3,    # above threshold - elevated from heavy cardio use
            "air_quality": 1250.0,  # above threshold - CO2 elevated from exertion
            "humidity": 68.2        # above threshold - high moisture from activity
        },

        "weight_machines": {
            "section": "weight_machines",
            "sensor_available": False,  # sensor offline - triggers report_sensor_offline
            "temperature": None,
            "humidity": None,
            "air_quality": None
        }

    }
    return data
