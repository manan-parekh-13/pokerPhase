#!/bin/bash

# Configuration
HOME_PATH="/home/ec2-user"
APP_DIR="$HOME_PATH/pokerPhase"
VENV_DIR="$APP_DIR/myenv"
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/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"
LOG_DIR="$HOME_PATH/logs"
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

# Create cython build
cd "$APP_DIR/cython" && python setup.py build_ext --inplace || { send_slack_message "Failed to build cython"; exit 1; }

# Start mysql docker container
sudo docker start mysql-server;

# Start Flask server using flask and log output
nohup flask run --host=0.0.0.0 --port=5000 >> "$LOG_FILE" 2>&1 &
sleep 5

# Hit equalizer startup endpoint (this will keep running)
nohup curl -s --request POST http://localhost:5000/equalizer/startup >> "$LOG_FILE" 2>&1 || {
  send_slack_message "Equalizer Startup Failure"; exit 1;
}
