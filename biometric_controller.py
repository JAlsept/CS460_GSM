# Biometric Controller - Processes incoming biometric data from the Garmin Venu 3 Driver.
# Compares readings against medical thresholds and forwards flagged events to the Alert Controller.
#
# Threshold values explained:
#   heart_rate_low          - below 40 bpm is critically low
#   heart_rate_high         - above 180 bpm is critically high
#   heart_rate_baseline_pct - 30% above personal baseline triggers alert (per SAD)
#   spo2_low                - below 95% blood oxygen is concerning
#   skin_temp_high          - above 37.5C skin temperature is elevated

import gsm_data_store
from biometric_garmin_driver import get_biometric_data
# from alert_controller import receive_alert

# Temporary - for testing purposes
def receive_alert(member_id, source, description):
    print(f"[ALERT] Member: {member_id} | Source: {source} | {description}")

# Medical thresholds used to evaluate biometric readings
THRESHOLDS = {
    "heart_rate_low": 40,
    "heart_rate_high": 180,
    "heart_rate_baseline_pct": 0.30,
    "spo2_low": 95,
    "skin_temp_high": 37.5,
}


# Compares a member's current biometric readings against medical thresholds
# Pulls baseline from the GSM Data Store 
# Forwards any flagged readings to the Alert Controller and logs them to the data store
def evaluate_readings(member_id, member):
    current = member["current"]
    name = member["name"]
    alerts_found = False

    # Pull baseline from data store instead of driver
    profile = gsm_data_store.get_member(member_id)
    baseline = profile["baseline"] if profile else None

    # If no baseline exists apply generalized defaults (per SAD - new member handling)
    if baseline is None:
        print(f"[INFO] {name} ({member_id}) - no baseline established, applying generalized thresholds")
        baseline = {
            "heart_rate": 75,
            "spo2": 97,
            "skin_temp": 34.5
        }

    # Check heart rate against absolute thresholds
    hr = current["heart_rate"]
    if hr < THRESHOLDS["heart_rate_low"]:
        description = f"{name} heart rate critically low at {hr} bpm"
        receive_alert(member_id, "BiometricController", description)
        gsm_data_store.log_alert({
            "alert_id": f"BIO_HR_LOW_{member_id}",
            "source": "BiometricController",
            "member_id": member_id,
            "description": description,
            "severity": "critical",
            "acknowledged": False
        })
        alerts_found = True

    elif hr > THRESHOLDS["heart_rate_high"]:
        description = f"{name} heart rate critically high at {hr} bpm"
        receive_alert(member_id, "BiometricController", description)
        gsm_data_store.log_alert({
            "alert_id": f"BIO_HR_HIGH_{member_id}",
            "source": "BiometricController",
            "member_id": member_id,
            "description": description,
            "severity": "critical",
            "acknowledged": False
        })
        alerts_found = True

    # Check heart rate against personal baseline (30% above baseline per SAD)
    baseline_hr = baseline["heart_rate"]
    if hr > baseline_hr * (1 + THRESHOLDS["heart_rate_baseline_pct"]):
        description = (
            f"{name} heart rate {hr} bpm is more than 30% above "
            f"personal baseline of {baseline_hr} bpm"
        )
        receive_alert(member_id, "BiometricController", description)
        gsm_data_store.log_alert({
            "alert_id": f"BIO_HR_BASELINE_{member_id}",
            "source": "BiometricController",
            "member_id": member_id,
            "description": description,
            "severity": "urgent",
            "acknowledged": False
        })
        alerts_found = True

    # Check blood oxygen saturation
    spo2 = current["spo2"]
    if spo2 < THRESHOLDS["spo2_low"]:
        description = f"{name} SpO2 low at {spo2}%"
        receive_alert(member_id, "BiometricController", description)
        gsm_data_store.log_alert({
            "alert_id": f"BIO_SPO2_{member_id}",
            "source": "BiometricController",
            "member_id": member_id,
            "description": description,
            "severity": "urgent",
            "acknowledged": False
        })
        alerts_found = True

    # Check skin temperature
    skin_temp = current["skin_temp"]
    if skin_temp > THRESHOLDS["skin_temp_high"]:
        description = f"{name} skin temperature elevated at {skin_temp}C"
        receive_alert(member_id, "BiometricController", description)
        gsm_data_store.log_alert({
            "alert_id": f"BIO_TEMP_{member_id}",
            "source": "BiometricController",
            "member_id": member_id,
            "description": description,
            "severity": "urgent",
            "acknowledged": False
        })
        alerts_found = True

    # Check fall detection
    if current["fall_detected"]:
        description = f"{name} fall detected"
        receive_alert(member_id, "BiometricController", description)
        gsm_data_store.log_alert({
            "alert_id": f"BIO_FALL_{member_id}",
            "source": "BiometricController",
            "member_id": member_id,
            "description": description,
            "severity": "critical",
            "acknowledged": False
        })
        alerts_found = True

    return alerts_found


# Entry point for the Biometric Controller
# Initializes the data store, loads all member data from the Garmin driver
# and evaluates each member's readings
def run_biometric_monitoring():
    print("Biometric Controller started - scanning member readings...\n")

    gsm_data_store.initialize()

    members = get_biometric_data()

    for member_id, member in members.items():
        flagged = evaluate_readings(member_id, member)
        if flagged:
            continue
        else:
            print(f"[OK] {member['name']} ({member_id}) - all readings normal")
        

    print("\nBiometric scan complete.")
    gsm_data_store.print_store_summary()


# Temporary - for testing purposes only
# Once the Staff Monitoring Console is built this will be called from there instead
if __name__ == "__main__":
    run_biometric_monitoring()