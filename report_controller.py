# Report Controller - Creates reports for gym management.
# Receives environmental readings from the Environmental Controller
# Retrieves equipment usage and alert data from the GSM Data Store at report generation time.
# Sends the final report to the Staff Monitoring Console

import gsm_data_store
from datetime import datetime


# Temporary - will connect with the GUI
def display_on_console(report_text):
    print(report_text)


class ReportController:

    def __init__(self):
        self.event_log = []
        self.environmental_log = []


    # Receives environmental readings from the Environmental Controller
    # Called by the Environmental Controller after each sensor evaluation
    def log_environmental(self, sensor_id, value):
        entry = {
            "sensor_id": sensor_id,
            "value": value,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.environmental_log.append(entry)
        print(f"  [Report] Environmental reading logged: {sensor_id} = {value}")


    # Receives occupancy events from the Check-In Terminal Controller
    # Called on each member check-in or check-out
    # def log_occupancy(self, member_id, count):
    #     entry = {
    #         "member_id": member_id,
    #         "count": count,
    #         "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    #     }
    #     self.occupancy_log.append(entry)
    #     print(f"  [Report] Occupancy event logged: member {member_id}, count: {count}")


    # Retrieves equipment usage for a single machine from the GSM Data Store
    # Called at report generation time for each machine
    def log_equipment(self, equipment_id):
        record = gsm_data_store.get_equipment_usage(equipment_id)
        if record:
            print(f"  [Report] Equipment record retrieved: {equipment_id}")
        return record


    def log_alert(self, event_id, description, severity, source="AlertController"):
        entry = {
            "type": "alert",
            "event_id": event_id,
            "description": description,
            "severity": severity,
            "source": source,
            "acknowledged": False,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.event_log.append(entry)
        gsm_data_store.log_alert({
            "alert_id": event_id,
            "source": source,
            "member_id": "N/A",
            "description": description,
            "severity": severity,
            "acknowledged": False
        })
        print(f"  [Report] Alert logged: {severity.upper()} - {description}")


    # Aggregates data into a report
    # Reads alert history and equipment usage from the GSM Data Store
    # Sends the final report to the Staff Monitoring Console GUI thing
    def generate_report(self):
        report_lines = []
        report_lines.append(" === GSM OBSERVATIONAL REPORT ===")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Pull equipment usage from the GSM Data Store
        equipment_data = gsm_data_store.get_all_equipment_usage()
        report_lines.append(f"\nEQUIPMENT USAGE SUMMARY ({len(equipment_data)} machines tracked)")
        report_lines.append("-" * 40)
        for machine_id, record in equipment_data.items():
            status = "IN USE" if record["in_use"] else "IDLE"
            report_lines.append(
                f"  {machine_id} | {record['machine_type']} | {record['section']} | "
                f"{status} | {record['duration_minutes']} min | intensity: {record['intensity_level']}/10"
            )

        # Pull environmental readings from local log
        report_lines.append(f"\nENVIRONMENTAL READINGS ({len(self.environmental_log)} total)")
        report_lines.append("-" * 40)
        for e in self.environmental_log:
            report_lines.append(
                f"  [{e['timestamp']}] {e['sensor_id']}: {e['value']}"
            )

        # # Pull occupancy events from local log
        # report_lines.append(f"\nOCCUPANCY EVENTS ({len(self.occupancy_log)} total)")
        # report_lines.append("-" * 40)
        # for o in self.occupancy_log:
        #     report_lines.append(
        #         f"  [{o['timestamp']}] Member {o['member_id']} - Count: {o['count']}"
        #     )

        # Pull alert history from the GSM Data Store
        alert_log = gsm_data_store.get_alert_log()
        report_lines.append(f"\nALERT HISTORY ({len(alert_log)} total)")
        report_lines.append("-" * 40)
        for a in alert_log:
            report_lines.append(
                f"  [{a['timestamp']}] {a['severity'].upper()} | {a['source']} | {a['description']}"
            )

        report_lines.append("\n" + "=" * 60)
        report_text = "\n".join(report_lines)

        # Send to Staff Monitoring Console Driver
        display_on_console(report_text)

        # Save to file
        filename = f"gsm_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, "w") as f:
            f.write(report_text)
        print(f"\n[Report] Report saved to {filename}")

        return report_text