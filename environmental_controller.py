# Environmental Controller - Processes incoming readings from the Environmental Sensor Driver.
# Compares readings against safe operating thresholds and forwards violations to the Alert Controller.
#
# Threshold values explained:
#   temperature_low  - below 61F is too cold
#   temperature_high - above 75F is too warm
#   air_quality_high - above 1000 ppm CO2 is unsafe
#   humidity_low     - below 30% is too dry
#   humidity_high    - above 60% is too humid

import gsm_data_store
from environmental_sensor_driver import get_environmental_data
# from alert_controller import receive_alert

# Temporary - for testing purposes
def receive_alert(source, description):
    print(f"  [ALERT] Source: {source} | {description}")

# Temporary - for testing purposes
def report_log_readings(section, readings):
    print(f"  [REPORT] Readings logged for section: {section} | {readings}")

# Safe operating thresholds for each environmental reading type
THRESHOLDS = {
    "temperature_low":  61.0,
    "temperature_high": 75.0,
    "air_quality_high": 1000.0,
    "humidity_low":     30.0,
    "humidity_high":    60.0,
}


class EnvironmentalController:
    def __init__(self):
        self.temperature      = None
        self.air_quality      = None
        self.humidity         = None
        self.sensor_available = False


    # Updates stored readings with the latest data from the sensor driver
    def receive_sensor_data(self, data):
        self.sensor_available = data.get("sensor_available", False)
        self.temperature      = data.get("temperature")
        self.air_quality      = data.get("air_quality")
        self.humidity         = data.get("humidity")


    # Checks each reading against thresholds and forwards any violations to the Alert Controller
    def evaluate_conditions(self, section):
        alerts_found = False

        # Check temperature
        if self.temperature is not None:
            if self.temperature > THRESHOLDS["temperature_high"]:
                description = f"[{section.upper()}] Temperature elevated at {self.temperature}F (threshold: {THRESHOLDS['temperature_high']}F)"
                receive_alert("EnvironmentalController", description)
                gsm_data_store.log_alert({
                    "alert_id": f"ENV_TEMP_{section.upper()}",
                    "source": "EnvironmentalController",
                    "member_id": "N/A",
                    "description": description,
                    "severity": "urgent",
                    "acknowledged": False
                })
                alerts_found = True

            elif self.temperature < THRESHOLDS["temperature_low"]:
                description = f"[{section.upper()}] Temperature too low at {self.temperature}F (threshold: {THRESHOLDS['temperature_low']}F)"
                receive_alert("EnvironmentalController", description)
                gsm_data_store.log_alert({
                    "alert_id": f"ENV_TEMP_{section.upper()}",
                    "source": "EnvironmentalController",
                    "member_id": "N/A",
                    "description": description,
                    "severity": "urgent",
                    "acknowledged": False
                })
                alerts_found = True

        # Check air quality
        if self.air_quality is not None:
            if self.air_quality > THRESHOLDS["air_quality_high"]:
                description = f"[{section.upper()}] Air quality elevated at {self.air_quality} ppm CO2 (threshold: {THRESHOLDS['air_quality_high']} ppm)"
                receive_alert("EnvironmentalController", description)
                gsm_data_store.log_alert({
                    "alert_id": f"ENV_AQ_{section.upper()}",
                    "source": "EnvironmentalController",
                    "member_id": "N/A",
                    "description": description,
                    "severity": "urgent",
                    "acknowledged": False
                })
                alerts_found = True

        # Check humidity
        if self.humidity is not None:
            if self.humidity > THRESHOLDS["humidity_high"]:
                description = f"[{section.upper()}] Humidity elevated at {self.humidity}% (threshold: {THRESHOLDS['humidity_high']}%)"
                receive_alert("EnvironmentalController", description)
                gsm_data_store.log_alert({
                    "alert_id": f"ENV_HUM_{section.upper()}",
                    "source": "EnvironmentalController",
                    "member_id": "N/A",
                    "description": description,
                    "severity": "urgent",
                    "acknowledged": False
                })
                alerts_found = True

            elif self.humidity < THRESHOLDS["humidity_low"]:
                description = f"[{section.upper()}] Humidity too low at {self.humidity}% (threshold: {THRESHOLDS['humidity_low']}%)"
                receive_alert("EnvironmentalController", description)
                gsm_data_store.log_alert({
                    "alert_id": f"ENV_HUM_{section.upper()}",
                    "source": "EnvironmentalController",
                    "member_id": "N/A",
                    "description": description,
                    "severity": "urgent",
                    "acknowledged": False
                })
                alerts_found = True

        return alerts_found


    # Notifies the Alert Controller that the sensor for the specified section is offline
    def report_sensor_offline(self, section):
        description = f"Environmental sensor offline for section: {section}"
        receive_alert("EnvironmentalController", description)
        gsm_data_store.log_alert({
            "alert_id": f"ENV_OFFLINE_{section.upper()}",
            "source": "EnvironmentalController",
            "member_id": "N/A",
            "description": description,
            "severity": "passive",
            "acknowledged": False
        })


    # Forwards current readings to the Report Controller for logging
    def log_readings(self, section):
        readings = {
            "section":     section,
            "temperature": self.temperature,
            "air_quality": self.air_quality,
            "humidity":    self.humidity,
        }
        report_log_readings(section, readings)


# Entry point for the Environmental Controller
# Loads all sensor data from the driver and evaluates each section
def run_environmental_monitoring():
    print("Environmental Controller started - scanning sensor readings...\n")

    gsm_data_store.initialize()

    controller = EnvironmentalController()
    sections = get_environmental_data()

    for section, data in sections.items():
        print(f"\n--- Section: {section.upper()} ---")
        controller.receive_sensor_data(data)

        if not controller.sensor_available:
            controller.report_sensor_offline(section)
            continue

        flagged = controller.evaluate_conditions(section)
        controller.log_readings(section)

        if not flagged:
            print(f"  [OK] All readings normal in {section}")

    print("\nEnvironmental scan complete.")
    gsm_data_store.print_store_summary()


# Temporary - for testing purposes only
# Once GSM Controller is built this will be called from there instead
if __name__ == "__main__":
    run_environmental_monitoring()
