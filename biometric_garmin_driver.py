# Garmin Venu 3 Driver - Simulates incoming biometric data from member smartwatches.
# In the real system this driver would receive live data from the Garmin Venu 3 devices.
# For the demo, this returns a hardcoded dictionary of mock member readings and baselines
#
# Biometric fields explained:
#   heart_rate    - beats per minute (bpm)
#   spo2          - blood oxygen saturation percentage (normal range: 95-100%)
#   skin_temp     - skin surface temperature in Celsius
#   motion        - current activity state of the member ("active" or "stationary")
#   fall_detected - whether the watch has detected a fall event (True/False)
#
# Demo alert breakdown:
#   Flagged (5): 003 Thomas - low SpO2, 008 Adrian - fall, 009 Jacob - critical,
#                013 Mia - critical, 015 Joshua - fall
#   Normal (10): 001, 002, 004, 005, 006, 007, 010, 011, 012, 014

# Returns a dictionary of mock biometric readings for active gym members
def get_biometric_data():
    data = {

        "001": {
            "member_id": "001",
            "name": "Alice Monroe",
            "current": {
                "heart_rate": 72,
                "spo2": 98,
                "skin_temp": 34.1,
                "motion": "active",
                "fall_detected": False
            }
        },
        "002": {
            "member_id": "002",
            "name": "Brian Castillo",
            "current": {
                "heart_rate": 80,
                "spo2": 97,
                "skin_temp": 34.5,
                "motion": "active",
                "fall_detected": False
            }
        },
        "003": {
            "member_id": "003",
            "name": "Thomas Reyes",
            "current": {
                "heart_rate": 88,
                "spo2": 91,
                "skin_temp": 34.8,
                "motion": "active",
                "fall_detected": False
            }
        },
        "004": {
            "member_id": "004",
            "name": "David Lucero",
            "current": {
                "heart_rate": 65,
                "spo2": 99,
                "skin_temp": 33.8,
                "motion": "stationary",
                "fall_detected": False
            }
        },
        "005": {
            "member_id": "005",
            "name": "Elena Sanchez",
            "current": {
                "heart_rate": 82,
                "spo2": 97,
                "skin_temp": 34.7,
                "motion": "active",
                "fall_detected": False
            }
        },
        "006": {
            "member_id": "006",
            "name": "Frank Allen",
            "current": {
                "heart_rate": 80,
                "spo2": 98,
                "skin_temp": 34.3,
                "motion": "active",
                "fall_detected": False
            }
        },
        "007": {
            "member_id": "007",
            "name": "Isabell Garcia",
            "current": {
                "heart_rate": 75,
                "spo2": 97,
                "skin_temp": 34.4,
                "motion": "active",
                "fall_detected": False
            }
        },
        "008": {
            "member_id": "008",
            "name": "Adrian Calderon",
            "current": {
                "heart_rate": 68,
                "spo2": 97,
                "skin_temp": 34.0,
                "motion": "stationary",
                "fall_detected": True
            }
        },
        "009": {
            "member_id": "009",
            "name": "Jacob Torres",
            "current": {
                "heart_rate": 175,
                "spo2": 89,
                "skin_temp": 37.8,
                "motion": "active",
                "fall_detected": False
            }
        },
        "010": {
            "member_id": "010",
            "name": "James Carmody",
            "current": {
                "heart_rate": 77,
                "spo2": 98,
                "skin_temp": 34.6,
                "motion": "active",
                "fall_detected": False
            }
        },
        "011": {
            "member_id": "011",
            "name": "Karen Johnson",
            "current": {
                "heart_rate": 79,
                "spo2": 97,
                "skin_temp": 34.3,
                "motion": "active",
                "fall_detected": False
            }
        },
        "012": {
            "member_id": "012",
            "name": "Katherine Jones",
            "current": {
                "heart_rate": 71,
                "spo2": 99,
                "skin_temp": 33.7,
                "motion": "stationary",
                "fall_detected": False
            }
        },
        "013": {
            "member_id": "013",
            "name": "Mia Gonzales",
            "current": {
                "heart_rate": 160,
                "spo2": 88,
                "skin_temp": 38.2,
                "motion": "active",
                "fall_detected": False
            }
        },
        "014": {
            "member_id": "014",
            "name": "Jesse Sandoval",
            "current": {
                "heart_rate": 85,
                "spo2": 96,
                "skin_temp": 34.8,
                "motion": "active",
                "fall_detected": False
            }
        },
        "015": {
            "member_id": "015",
            "name": "Joshua Potter",
            "current": {
                "heart_rate": 55,
                "spo2": 98,
                "skin_temp": 34.2,
                "motion": "stationary",
                "fall_detected": True
            }
        }
    }
    return data