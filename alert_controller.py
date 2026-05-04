from datetime import datetime
import threading


# Receives events from other controllers and determines the severity
# and routes alerts to the appropriate recipients.
# Called by: Biometric Controller, Camera Analysis Controller,
# Environmental Controller
class AlertController:

    def __init__(self,report_controller):
        self.active_alerts = {}
        self.escalation_timers = {}
        self.alert_escalation = 15 # For testing 15 seconds
        self.alert_counter = 0
        self.report_controller = report_controller
        self.on_escalation = None # alert escalation
        self.on_alert = None # new alert

    # Keywords that trigger a critical alert
    # Immediate emergency response
    CRITICAL_KEYWORDS = [
        "critically low",
        "critically high",
        "fall detected",
        "collapsed",
        "motionless",
        "on the floor",
        "serious injury"
    ]

    # Keywords that trigger an urgent alert
    # Immediate staff response
    URGENT_KEYWORDS = [
        "more than 30% above",
        "spo2 low",
        "skin temperature elevated",
        "temperature elevated",
        "temperature too low",
        "air quality elevated",
        "humidity elevated",
        "humidity too low",
        "camera feed offline",
    ]


    # Gets alerts from other controllers
    # Determines severity based on keywords in the description
    # Routes to the appropriate recipients 
    def receive_alert(self, member_id, source, description):
        self.alert_counter += 1
        alert_id = f"{member_id}_A{self.alert_counter:03d}"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        desc = description.lower()

        if any(keyword in desc for keyword in self.CRITICAL_KEYWORDS):
            severity = "critical"
            self.send_critical(member_id, alert_id, description)
        elif any(keyword in desc for keyword in self.URGENT_KEYWORDS):
            severity = "urgent"
            self.send_urgent(member_id, alert_id, description)
        else:
            severity = "passive"
            self.send_passive(member_id, alert_id, description)

        # Store in active alerts
        self.active_alerts[alert_id] = {
            "member_id": member_id,
            "source": source,
            "description": description,
            "severity": severity,
            "acknowledged": False,
            "timestamp": timestamp
        }

        # Write alert to report controller to then send to GSM Data Store
        self.report_controller.log_alert(alert_id, description, severity, source)


    # Sends a low priority passive alert to the member's Garmin Venu 3
    # Starts escalation timer - if not acknowledged escalates to urgent
    def send_passive(self, member_id, alert_id, message):
        print(f"\n[Passive Alert] Member {member_id}: {message}")
        print("[Alert] Notification sent to Garmin Venu 3")

        # Tell GUI
        if self.on_alert:
            self.on_alert(member_id, alert_id, message, "passive")

        # Start timer
        timer = threading.Timer(
            self.alert_escalation,
            self._escalate_to_urgent,
            args=[member_id, alert_id, message]
        )
        timer.start()
        self.escalation_timers[alert_id] = timer


    # Sends an urgent alert to the member's Garmin Venu 3 and the Staff Monitoring Console
    # Starts timer - if not acknowledged escalates to critical
    def send_urgent(self, member_id, alert_id, message):
        print(f"\n[Urgent Alert] Member {member_id}: {message}")
        print("[Alert] Notification sent to Garmin Venu 3")
        print("[Alert] Notification sent to Staff Monitoring Console")

        # Tell GUI 
        if self.on_alert:
            self.on_alert(member_id, alert_id, message, "urgent")

        # Start timer
        timer = threading.Timer(
            self.alert_escalation,
            self._escalate_to_critical,
            args=[member_id, alert_id, message]
        )
        timer.start()
        self.escalation_timers[alert_id] = timer


    # Sends a critical alert to Garmin Venu 3, Staff Monitoring Console, and emergency services
    # No escalation timer needed 
    def send_critical(self, member_id, alert_id, message):
        print(f"\n[Critical Alert] Member {member_id}: {message}")
        print("[Alert] Notification sent to Garmin Venu 3")
        print("[Alert] Notification sent to Staff Monitoring Console")
        print("[Alert] Emergency response signal sent to emergency services")

        # Tell GUI 
        if self.on_escalation:
            self.on_escalation(member_id, alert_id, message)

    # Dismisses an active alert and cancels the escalation timer
    # Called when a member or staff member acknowledges the alert
    def acknowledge_alert(self, alert_id, source):
        if alert_id in self.active_alerts:
            # Cancel timer 
            if alert_id in self.escalation_timers:
                self.escalation_timers[alert_id].cancel()
                del self.escalation_timers[alert_id]

            # Mark the alert as acknowledged
            self.active_alerts[alert_id]["acknowledged"] = True
            print(f"\n[Alert] Alert {alert_id} acknowledged by {source}")
        else:
            print(f"[Alert] Alert {alert_id} not found")


    # Called when a passive alert is not acknowledged within 120s and escalates to urgent
    def _escalate_to_urgent(self, member_id, alert_id, message):
        if alert_id in self.active_alerts and not self.active_alerts[alert_id]["acknowledged"]:
            print("\n[Alert] Passive alert not acknowledged, escalating to URGENT")
            self.active_alerts[alert_id]["severity"] = "urgent"
            self.send_urgent(member_id, alert_id, message)


    # Called when an urgent alert is not acknowledged within 120s and escalates to critical
    def _escalate_to_critical(self, member_id, alert_id, message):
        if alert_id in self.active_alerts and not self.active_alerts[alert_id]["acknowledged"]:
            print("\n[Alert] Urgent alert not acknowledged, escalating to CRITICAL")
            self.active_alerts[alert_id]["severity"] = "critical"
            self.send_critical(member_id, alert_id, message)