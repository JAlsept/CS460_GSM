# GSM Data Store - Centralized in-memory data store for the Gym Space Monitoring system.
# Holds member profiles, equipment usage records, alert summaries, occupancy data, and session logs.
# All controllers read from and write to this module in place of their current mock/stub setups.
#
# Wiring instructions per controller:
#   CheckInTerminal_Controller  - replace self.members = self.ui.get_mock_members() with get_all_members()
#                               - replace self.members[member_id] writes with update_member()
#   BiometricController         - replace get_biometric_data() baseline lookups with get_member()
#                               - replace session data writes with update_member()
#   AlertController             - use log_alert() to store alert summaries
#   ReportController            - use get_alert_log(), get_equipment_usage(), get_occupancy_log()

import json
from datetime import datetime

# Returns the current time as a formatted string - used internally to stamp all log entries
def _timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


_store = {
    "members":       {},  # member_id -> member profile dict
    "equipment":     {},  # machine_id -> equipment usage dict
    "alerts":        [],  # list of alert summary dicts
    "occupancy_log": [],  # list of occupancy event dicts
    "session_log":   [],  # list of session event dicts
}


# Seeds the data store with member profiles from the JSON file
# Call this once at system startup before any controllers begin running
def initialize(members_json_path="members_profile.json"):
    with open(members_json_path, "r") as f:
        members = json.load(f)
    _store["members"] = members
    print(f"[DATA STORE] Initialized with {len(members)} member profiles")


# Returns the profile dict for a single member, or None if not found
def get_member(member_id):
    return _store["members"].get(member_id)


# Returns all member profiles as a dict keyed by member_id
def get_all_members():
    return _store["members"]


# Creates or overwrites a member profile in the store
def update_member(member_id, profile):
    _store["members"][member_id] = profile


# Writes a single equipment usage record to the store
def write_equipment_usage(machine_id, record):
    _store["equipment"][machine_id] = record


# Returns the usage record for a single machine, or None if not found
def get_equipment_usage(machine_id):
    return _store["equipment"].get(machine_id)


# Returns all equipment usage records as a dict keyed by machine_id
def get_all_equipment_usage():
    return _store["equipment"]


# Appends an alert summary to the alert log
# Expected fields: alert_id, source, member_id, description, severity, acknowledged
def log_alert(alert_summary):
    alert_summary["timestamp"] = _timestamp()
    _store["alerts"].append(alert_summary)


# Returns the full alert log as a list
def get_alert_log():
    return _store["alerts"]


# Appends an occupancy event to the occupancy log
# Expected fields: member_id, event_type ("check_in" or "check_out"), occupancy_count
def log_occupancy(member_id, event_type, occupancy_count):
    entry = {
        "member_id":       member_id,
        "event_type":      event_type,
        "occupancy_count": occupancy_count,
        "timestamp":       _timestamp(),
    }
    _store["occupancy_log"].append(entry)


# Returns the full occupancy log as a list
def get_occupancy_log():
    return _store["occupancy_log"]


# Appends a session event to the session log
# Expected fields: member_id, event_type ("session_start" or "session_end"), device_id
def log_session(member_id, event_type, device_id):
    entry = {
        "member_id":  member_id,
        "event_type": event_type,
        "device_id":  device_id,
        "timestamp":  _timestamp(),
    }
    _store["session_log"].append(entry)


# Returns the full session log as a list
def get_session_log():
    return _store["session_log"]


# Prints a summary of current store contents - useful for debugging during integration
def print_store_summary():
    print("\n=== GSM DATA STORE SUMMARY ===")
    print(f"  Members:       {len(_store['members'])}")
    print(f"  Equipment:     {len(_store['equipment'])}")
    print(f"  Alerts logged: {len(_store['alerts'])}")
    print(f"  Occupancy log: {len(_store['occupancy_log'])} events")
    print(f"  Session log:   {len(_store['session_log'])} events")
    print("==============================\n")
