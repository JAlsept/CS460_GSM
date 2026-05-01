# Check-In Terminal Driver - Handles input and output for the member check-in terminal
import json

class CheckInTerminal_Driver:
    def __init__(self):
        self.location = "Main Entrance"


    # Returns hardcoded member profiles for testing purposes
    # Replace with a live data_store lookup when the shared data_store is ready
    def get_mock_members(self):
        with open("members_profile.json", "r") as file:
            return json.load(file)


    # Temporary - returns a scripted list of terminal events
    # Replaced by the GSM Controller when it is built
    def get_mock_events(self):
        return [
            {"event_type": "check_in", "member_id": "001"},
            {"event_type": "check_in", "member_id": "003"},
            {"event_type": "check_in", "member_id": "007"},
            {"event_type": "update_profile", "member_id": "005", "updates": {"weight": "126", "restrictions": ["mild ankle sprain"]}},
            {"event_type": "check_in", "member_id": "009"},
            {"event_type": "register", "member_id": "016"},
            {"event_type": "check_in", "member_id": "002"},
            {"event_type": "check_in", "member_id": "013"},
            {"event_type": "check_in", "member_id": "011"},
            {"event_type": "check_in", "member_id": "014"},
            {"event_type": "check_in", "member_id": "015"},
            {"event_type": "check_in", "member_id": "004"},
            {"event_type": "check_in", "member_id": "010"},
            {"event_type": "check_in", "member_id": "006"},
            {"event_type": "check_in", "member_id": "008"},
            {"event_type": "check_in", "member_id": "012"},
            {"event_type": "check_in", "member_id": "012"},
            {"event_type": "check_out", "member_id": "001"},
        ]


    # Prompts the member for biometric monitoring consent at the terminal
    def get_consent(self):
        print("\n--- LEGAL DISCLOSURE ---")
        print("Do you consent to real-time biometric monitoring for safety purposes?")
        choice = input("Enter 'Y' for Yes or 'N' for No: ").strip().upper()
        return choice == "Y"


    # Prompts staff to collect new member details at the terminal
    def get_registration_input(self):
        print()
        name = input("Enter Full Name: ").strip()
        weight = input("Enter Weight (lbs): ").strip()

        while not weight.isdigit():
            weight = input("Invalid input. Enter weight in whole numbers: ").strip()

        restrictions = input("Enter any physical restrictions (or press Enter for none): ").strip()
        restrictions = [restrictions] if restrictions else ["None"]

        return {
            "name": name,
            "weight": weight,
            "restrictions": restrictions
        }


    # Displays the welcome screen on the terminal after a successful check-in
    def display_welcome(self, profile, occupancy):
        print("\n" + "=" * 40)
        print(f"  ACCESS GRANTED: {profile['name'].upper()}")
        print(f"  Weight: {profile['weight']} lbs")
        print(f"  Restrictions: {', '.join(profile['restrictions'])}")
        print(f"  Facility Occupancy: {occupancy}/16")
        print("=" * 40)


    # Displays a general status or error message on the terminal screen
    def display_message(self, message):
        print(f"  [TERMINAL] {message}")