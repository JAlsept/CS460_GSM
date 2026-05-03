# Check-In Terminal Controller - Manages the member check-in process at the front desk terminal
# Handles member arrivals, departures, profile updates, and new registrations
# Tracks facility occupancy

from CheckInTerminal_Driver import CheckInTerminal_Driver

# Temporary stub - replace with real start_monitoring call once Biometric Controller is fully implemented
def start_monitoring(member_id):
    print(f"  [BIOMETRIC] Monitoring started for member {member_id}")


class CheckInTerminal_Controller:
    def __init__(self):
        self.current_profile = {}
        self.terminal_status = True
        self.occupancy = 0
        self.max_capacity = 16
        self.ui = CheckInTerminal_Driver()

        # Temporary - load mock members from driver
        # When data_store is ready, replace with a data_store lookup instead
        self.members = self.ui.get_mock_members()


    # Handles incoming member ID and enforces digit-only validation
    def receive_scan(self, member_id):
        if not member_id.isdigit():
            print(f"[REJECTED] '{member_id}' is not a valid member ID.")
            return
        if self.terminal_status:
            self.process_entry(member_id)


    # Enforces capacity limit and prevents duplicate check-ins
    def process_entry(self, member_id):
        if self.occupancy >= self.max_capacity:
            self.ui.display_message("Facility is at maximum capacity - entry denied")
            return

        profile = self.members.get(member_id)

        if profile and profile.get("checked_in"):
            self.ui.display_message(f"Member {member_id} is already checked in")
            return

        self.load_profile(member_id)


    # Retrieves the member profile from datastore
    # If the member is not found, pivots to registration
    def load_profile(self, member_id):
        profile = self.members.get(member_id)

        if profile:
            self.current_profile = profile
            self.finalize_session(member_id)
        else:
            self.register_profile(member_id)


    # Applies changes such as weight or restriction updates before a session
    def update_profile(self, member_id, updates):
        profile = self.members.get(member_id)

        if not profile:
            self.ui.display_message(f"No profile found for member {member_id}")
            return

        for field, value in updates.items():
            if field in profile:
                profile[field] = value
                print(f"  [UPDATE] {field} -> {value}")

        self.members[member_id] = profile
        self.current_profile = profile
        self.finalize_session(member_id)


    # Creates a new member profile from interactive terminal input
    # Consent is required- blocks registration if declined
    # Flags profile as pending until two-week baseline is established
    def register_profile(self, member_id):
        print(f"\n[NEW MEMBER] ID {member_id} not found - starting registration...")

        registration_data = self.ui.get_registration_input()
        consent = self.ui.get_consent()

        if not consent:
            print("[DENIED] Consent required for facility use - registration cancelled")
            print("[INFO] No profile or data has been created")
            return

        new_profile = {
            "member_id": member_id,
            "name": registration_data["name"],
            "weight": registration_data["weight"],
            "restrictions": registration_data["restrictions"],
            "has_consent": True,
            "baseline": None,
            "profile_complete": False,
            "checked_in": False,
            "device_id": None
        }

        self.members[member_id] = new_profile
        print(f"[INFO] Profile created for {new_profile['name']} (ID: {member_id})")
        print(f"[INFO] Generalized thresholds active until two-week baseline is established")

        self.current_profile = new_profile
        self.finalize_session(member_id)


    # Consolidates the check-in completion steps
    def finalize_session(self, member_id):
        self.occupancy += 1
        device_id = f"Venu3_{member_id}"

        self.current_profile["checked_in"] = True
        self.current_profile["device_id"] = device_id

        self.members[member_id] = self.current_profile

        self.link_device(member_id, device_id)

        self.ui.display_welcome(self.current_profile, self.occupancy)


    # Connects the Garmin Venu 3 to the active session
    # Signals the Biometric Controller to begin monitoring for this member
    def link_device(self, member_id, device_id):
        print(f"  [SIGNAL] Linking {device_id} to member {member_id}...")
        start_monitoring(member_id)


    # Handles a member leaving the facility
    def process_exit(self, member_id):
        profile = self.members.get(member_id)

        if not profile:
            self.ui.display_message(f"No profile found for member {member_id}")
            return

        self.occupancy -= 1
        profile["checked_in"] = False
        profile["device_id"] = None

        self.members[member_id] = profile


# Temporary - using mock events from the driver
# When GSM Controller is built, this will be called from there instead
if __name__ == "__main__":
    controller = CheckInTerminal_Controller()

    print("=== GYM SAFETY MONITOR: TERMINAL ACTIVE ===\n")

    for event in controller.ui.get_mock_events():
        member_id = event["member_id"]
        event_type = event["event_type"]

        print(f"\n--- Event: {event_type.upper()} | Member: {member_id} ---")

        if event_type == "check_in":
            controller.receive_scan(member_id)
        elif event_type == "check_out":
            controller.process_exit(member_id)
        elif event_type == "update_profile":
            controller.update_profile(member_id, event.get("updates", {}))
        elif event_type == "register":
            controller.receive_scan(member_id)

    print(f"\nFinal occupancy: {controller.occupancy}/16")
    print("\n=== TERMINAL SESSION COMPLETE ===")