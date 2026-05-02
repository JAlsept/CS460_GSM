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
            "temperature": 71.8,
            "air_quality": 870.0,
            "humidity": 45.0
        },

        "cardio": {
            "section": "cardio",
            "sensor_available": True,
            "temperature": 81.3,
            "air_quality": 1250.0,
            "humidity": 68.2
        },

        "weight_machines": {
            "section": "weight_machines",
            "sensor_available": False,
            "temperature": None,
            "humidity": None,
            "air_quality": None
        }

    }
    return data
