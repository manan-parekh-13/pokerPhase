#!/bin/bash

# Configuration
HOME_PATH=""
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
source "/pokerPhase/myenv/bin/activate" || { send_slack_message "Failed to activate virtual environment"; exit 1; }

# Pull latest code from Git
#git pull origin master >> "$LOG_FILE" 2>&1 || { send_slack_message "Git pull failed"; exit 1; }

# Create cython build - do this on t4g.medium and save snapshot to s3 to be used by next launched instance
cd "$APP_DIR/cython" && sudo python3 setup.py build_ext --inplace -v -j $(nproc) || { send_slack_message "Failed to build cython"; exit 1; }
sudo pigz -k /cython
aws s3 cp cython.zip s3://poker-phase-code/

# Start mysql docker container
#sudo docker start mysql-server;
#sleep 10

sudo mkdir /logs
sudo chmod 777 /logs

# Start Flask server using flask and log output
nohup flask run --host=0.0.0.0 --port=5000 >> "$LOG_FILE" 2>&1 &
sleep 5

# Hit equalizer startup endpoint (this will keep running)
nohup curl -s --request POST http://localhost:5000/equalizer/startup >> "$LOG_FILE" 2>&1 || {
  send_slack_message "Equalizer Startup Failure"; exit 1;
}
