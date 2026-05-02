# Equipment Sensor Driver - Simulates incoming usage data from gym equipment sensors.
# In the real system this driver would receive live data from sensors embedded in each machine.
# For the demo, this writes a hardcoded dictionary of mock usage records directly to the GSM Data Store.

import gsm_data_store


# Reads mock equipment sensor data and writes each record directly to the GSM Data Store
# In the real system, this would receive live data from sensors embedded in each machine
def load_equipment_data():
    data = {

        # --- Free Weights Section ---
        "EQ_FW_01": {
            "machine_id": "EQ_FW_01",
            "section": "free_weights",
            "machine_type": "bench_press",
            "in_use": True,
            "intensity_level": 3,       # weight setting (1-10 scale)
            "duration_minutes": 18
        },
        "EQ_FW_02": {
            "machine_id": "EQ_FW_02",
            "section": "free_weights",
            "machine_type": "dumbbell_rack",
            "in_use": True,
            "intensity_level": 5,
            "duration_minutes": 32
        },
        "EQ_FW_03": {
            "machine_id": "EQ_FW_03",
            "section": "free_weights",
            "machine_type": "barbell_squat_rack",
            "in_use": False,
            "intensity_level": 0,
            "duration_minutes": 0
        },

        # --- Cardio Section ---
        "EQ_CA_01": {
            "machine_id": "EQ_CA_01",
            "section": "cardio",
            "machine_type": "treadmill",
            "in_use": True,
            "intensity_level": 7,       # speed setting (1-10 scale)
            "duration_minutes": 45
        },
        "EQ_CA_02": {
            "machine_id": "EQ_CA_02",
            "section": "cardio",
            "machine_type": "treadmill",
            "in_use": True,
            "intensity_level": 4,
            "duration_minutes": 12
        },
        "EQ_CA_03": {
            "machine_id": "EQ_CA_03",
            "section": "cardio",
            "machine_type": "stationary_bike",
            "in_use": False,
            "intensity_level": 0,
            "duration_minutes": 0
        },
        "EQ_CA_04": {
            "machine_id": "EQ_CA_04",
            "section": "cardio",
            "machine_type": "elliptical",
            "in_use": True,
            "intensity_level": 6,
            "duration_minutes": 27
        },

        # --- Weight Machines Section ---
        "EQ_WM_01": {
            "machine_id": "EQ_WM_01",
            "section": "weight_machines",
            "machine_type": "lat_pulldown",
            "in_use": True,
            "intensity_level": 4,       # resistance setting (1-10 scale)
            "duration_minutes": 9
        },
        "EQ_WM_02": {
            "machine_id": "EQ_WM_02",
            "section": "weight_machines",
            "machine_type": "leg_press",
            "in_use": False,
            "intensity_level": 0,
            "duration_minutes": 0
        },
        "EQ_WM_03": {
            "machine_id": "EQ_WM_03",
            "section": "weight_machines",
            "machine_type": "decline_squat",
            "in_use": True,
            "intensity_level": 6,
            "duration_minutes": 14
        },
        "EQ_WM_04": {
            "machine_id": "EQ_WM_04",
            "section": "weight_machines",
            "machine_type": "cable_row",
            "in_use": False,
            "intensity_level": 0,
            "duration_minutes": 0
        }

    }

    for machine_id, record in data.items():
        gsm_data_store.write_equipment_usage(machine_id, record)

    print(f"[EQUIPMENT DRIVER] {len(data)} equipment records written to data store")


# Temporary - for testing purposes only
# Once GSM Controller is built this will be called from there instead
if __name__ == "__main__":
    gsm_data_store.initialize()
    load_equipment_data()
    gsm_data_store.print_store_summary()
