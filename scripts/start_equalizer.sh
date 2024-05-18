#!/bin/bash

# Configuration
APP_DIR="/pokerPhase"
VENV_DIR="/home/ec2-user/pokerPhase/myenv"
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/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"
LOG_DIR="logs"
LOG_FILE="$LOG_DIR/equalizer_$(date +'%Y-%m-%d').log"

# Functions
send_slack_message() {
  local message=$1
  curl -X POST -H 'Content-type: application/json' --data "{\"text\":\"${message}\"}" $SLACK_WEBHOOK_URL
}

# Go to application directory
cd "$APP_DIR"

# Activate virtual environment
source "$VENV_DIR/bin/activate" || { send_slack_message "Failed to activate virtual environment"; exit 1; }

# Pull latest code from Git
git pull origin master >> "$LOG_FILE" 2>&1 || { send_slack_message "Git pull failed"; exit 1; }

# Start Flask server using gunicorn and log output
nohup gunicorn -b 0.0.0.0:5000 web:app >> "$LOG_FILE" 2>&1 &
sleep 5

# Hit login endpoint and send response headers via Slack
login_response=$(curl -i -s -X POST http://localhost:5000/login/otp)
echo "Login response: $login_response" >> "$LOG_FILE"
send_slack_message "Login Response: $login_response"

# Hit status endpoint and send response via Slack
status_response=$(curl -s http://localhost:5000/status)
echo "Status response: $status_response" >> "$LOG_FILE"
send_slack_message "Status Response: $status_response"

# Hit equalizer startup endpoint (this will keep running) and log output
nohup curl -s http://localhost:5000/equalizer/startup >> "$LOG_FILE" 2>&1 &

# Hit status endpoint and send response via Slack
status_response=$(curl -s http://localhost:5000/status)
echo "Status response: $status_response" >> "$LOG_FILE"
send_slack_message "Status Response: $status_response"

