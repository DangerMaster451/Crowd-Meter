import csv
import os
import subprocess
import time
from datetime import datetime
import requests

# --- CONFIGURATION ---
THRESHOLD = 4
CHECK_INTERVAL_SECONDS = 15 * 60 # 15 minutes
CSV_FILE = "data_log.csv"
HTML_FILE = "index.html"

# Notification Config (Using NTFY.sh - a free, no-signup notification service)
# Change 'my_secret_topic_123' to a unique string only you know
NTFY_TOPIC = "DangerMasterGym" 


def get_script_value():
    """Calls your existing script and returns the integer value."""
    try:
        # Replace 'your_existing_script.py' with the actual path to your script
        result = subprocess.run(['python', 'test.py'], capture_output=True, text=True, check=True)
        # Assumes your script prints just the number to the console
        return int(result.stdout.strip())
    except Exception as e:
        print(f"Error running script: {e}")
        return None


def log_data(timestamp, value):
    """Logs the timestamp and value to a CSV file."""
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, mode='a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Value"])  # Header
        writer.writerow([timestamp, value])


def send_notification(value):
    """Sends a push notification to your phone via the ntfy app."""
    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=f"Alert! Value has dropped to {value}, which is below the threshold of {THRESHOLD}.",
            headers={"Title": "Low Value Alert"}
        )
        print("Notification sent successfully.")
    except Exception as e:
        print(f"Failed to send notification: {e}")


def generate_static_site():
    """Reads the CSV and generates a clean, static HTML file."""
    if not os.path.isfile(CSV_FILE):
        return

    rows_html = ""
    with open(CSV_FILE, mode='r') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        # Read rows and reverse them so the newest data is at the top
        for row in reversed(list(reader)):
            timestamp, value = row
            # Add a visual warning color if it's below threshold
            row_class = "class='warning'" if int(value) < THRESHOLD else ""
            rows_html += f"<tr {row_class}><td>{timestamp}</td><td>{value}</td></tr>\n"

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Data Log Dashboard</title>
    <meta http-equiv="refresh" content="60"> <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f4f4f9; }}
        h2 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; max-width: 600px; background: white; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #007BFF; color: white; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        .warning {{ background-color: #ffcccc !important; color: #cc0000; font-weight: bold; }}
    </style>
</head>
<body>
    <h2>Data Log Dashboard</h2>
    <p>Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <table>
        <tr>
            <th>Timestamp</th>
            <th>Value (0-10)</th>
        </tr>
        {rows_html}
    </table>
</body>
</html>
"""
    with open(HTML_FILE, "w") as f:
        f.write(html_content)
    print("Static website updated.")


def main():
    print("Monitoring service started...")
    while True:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        value = get_script_value()
        
        if value is not None:
            print(f"[{current_time}] Fetched value: {value}")
            log_data(current_time, value)
            
            if value < THRESHOLD:
                send_notification(value)
                
            generate_static_site()
        
        # Wait for 15 minutes
        time.sleep(CHECK_INTERVAL_SECONDS)

if __name__ == "__main__":
    main()