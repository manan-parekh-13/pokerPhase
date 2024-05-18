import subprocess
import time
import requests
import json
from datetime import datetime
import os


def send_slack_message(message):
    webhook_url = 'https://hooks.slack.com/services/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'
    data = {'text': message}
    headers = {'Content-Type': 'application/json'}
    response = requests.post(webhook_url, data=json.dumps(data), headers=headers)
    if response.status_code != 200:
        print(f"Failed to send Slack message: {response.text}")


def get_log_file_path():
    current_date = datetime.now().strftime("%Y-%m-%d")
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    return f"{log_dir}/equalizer_{current_date}.log"


def log_to_file(log_file, message):
    timestamp = datetime.now().strftime("%H:%M:%S %f")[:-3]
    log_message = f"{timestamp} - {message}"
    log_file.write(log_message + "\n")  # Write to log file


def main():
    subprocess.run(['cd', 'pokerPhase'])

    subprocess.run(['source', '/home/ec2-user/pokerPhase/myenv/bin/activate'])

    # Step 1: Git pull
    git_pull = subprocess.run(['git', 'pull', 'origin', 'master'], capture_output=True, text=True)
    print("Git pull output:", git_pull.stdout)

    # Step 2: Get log file path
    log_file_path = get_log_file_path()
    log_file = open(log_file_path, 'a')  # Open log file in append mode

    # Step 3: Start Flask web server
    log_to_file(log_file, "Starting Flask server")
    print("Starting Flask server")
    flask_server = subprocess.Popen(['flask', 'run', '--host=0.0.0.0', '--port=5000'], stdout=log_file,
                                    stderr=subprocess.STDOUT)

    # Step 4: Wait for Flask server to start
    time.sleep(5)

    # Step 5: Hit equalizer startup curl
    log_to_file(log_file, "Hitting equalizer startup curl")
    print("Hitting equalizer startup curl")
    equalizer_startup_response = subprocess.run(['curl', 'equalizer_startup_url'], capture_output=True, text=True)
    session_id = equalizer_startup_response.headers.get('session_id')

    if not session_id:
        # Error handling: No session ID received
        error_message = "Error: Failed to get session ID"
        print(error_message)
        log_to_file(log_file, error_message)
        send_slack_message(error_message)

        # Terminate Flask server process
        log_to_file(log_file, "Terminating Flask server process")
        print("Terminating Flask server process")
        flask_server.terminate()
        log_file.close()  # Close log file
        return

    # Step 6: Hit the status curl with session ID
    log_to_file(log_file, "Hitting the status curl")
    print("Hitting the status curl")
    status_curl_headers = {'Cookie': f'session_id={session_id}'}
    status_curl = subprocess.run(['curl', 'status_curl_url', '-H', json.dumps(status_curl_headers)], capture_output=True, text=True)
    status_response = status_curl.stdout

    log_to_file(log_file, log_to_file)
    print(status_response)
    send_slack_message(status_response)


if __name__ == "__main__":
    main()
