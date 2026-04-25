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
            },
            "baseline": {
                "heart_rate": 70,
                "spo2": 98,
                "skin_temp": 34.0
            }
        },
        "002": {
            "member_id": "002",
            "name": "Brian Castillo",
            "current": {
                "heart_rate": 155,
                "spo2": 97,
                "skin_temp": 35.2,
                "motion": "active",
                "fall_detected": False
            },
            "baseline": {
                "heart_rate": 75,
                "spo2": 97,
                "skin_temp": 34.5
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
            },
            "baseline": {
                "heart_rate": 85,
                "spo2": 97,
                "skin_temp": 34.6
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
            },
            "baseline": {
                "heart_rate": 63,
                "spo2": 99,
                "skin_temp": 33.9
            }
        },
        "005": {
            "member_id": "005",
            "name": "Elena Sanchez",
            "current": {
                "heart_rate": 110,
                "spo2": 96,
                "skin_temp": 35.5,
                "motion": "active",
                "fall_detected": False
            },
            "baseline": {
                "heart_rate": 78,
                "spo2": 97,
                "skin_temp": 34.7
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
            },
            "baseline": {
                "heart_rate": 78,
                "spo2": 98,
                "skin_temp": 34.2
            }
        },
        "007": {
            "member_id": "007",
            "name": "Isabell Garcia",
            "current": {
                "heart_rate": 95,
                "spo2": 93,
                "skin_temp": 36.1,
                "motion": "active",
                "fall_detected": False
            },
            "baseline": {
                "heart_rate": 72,
                "spo2": 98,
                "skin_temp": 34.4
            }
        },
        "008": {
            "member_id": "008",
            "name": "Adrian Calderon ",
            "current": {
                "heart_rate": 68,
                "spo2": 97,
                "skin_temp": 34.0,
                "motion": "stationary",
                "fall_detected": True
            },
            "baseline": {
                "heart_rate": 66,
                "spo2": 97,
                "skin_temp": 34.1
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
            },
            "baseline": {
                "heart_rate": 80,
                "spo2": 97,
                "skin_temp": 34.9
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
            },
            "baseline": {
                "heart_rate": 74,
                "spo2": 98,
                "skin_temp": 34.5
            }
        },
        "011": {
            "member_id": "011",
            "name": "Karen Johnson",
            "current": {
                "heart_rate": 102,
                "spo2": 95,
                "skin_temp": 35.9,
                "motion": "active",
                "fall_detected": False
            },
            "baseline": {
                "heart_rate": 76,
                "spo2": 97,
                "skin_temp": 34.3
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
            },
            "baseline": {
                "heart_rate": 69,
                "spo2": 99,
                "skin_temp": 33.8
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
            },
            "baseline": {
                "heart_rate": 82,
                "spo2": 97,
                "skin_temp": 35.0
            }
        },
        "014": {
            "member_id": "014",
            "name": "Jesse Sandoval",
            "current": {
                "heart_rate": 85,
                "spo2": 96,
                "skin_temp": 35.1,
                "motion": "active",
                "fall_detected": False
            },
            "baseline": {
                "heart_rate": 82,
                "spo2": 97,
                "skin_temp": 34.8
            }
        },
        "015": {
            "member_id": "015",
            "name": "Johua Potter",
            "current": {
                "heart_rate": 55,
                "spo2": 98,
                "skin_temp": 34.2,
                "motion": "stationary",
                "fall_detected": True
            },
            "baseline": {
                "heart_rate": 68,
                "spo2": 98,
                "skin_temp": 34.1
            }
        }
    }
    return data
   
