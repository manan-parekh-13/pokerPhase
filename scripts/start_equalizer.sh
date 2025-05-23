#!/bin/bash

# Configuration
HOME_PATH=""
APP_DIR="$HOME_PATH/pokerPhase"
VENV_DIR="$APP_DIR/myenv"
TELEGRAM_WEBHOOK_URL="https://api.telegram.org/bot7255610692:AAHSO6A4KxV9dVAhsNN1vizs1tZ97IyP48o/sendMessage"
TELEGRAM_CHAT_ID="-4694389902"
LOG_DIR="$HOME_PATH/logs"
LOG_FILE="$LOG_DIR/equalizer_$(date +'%Y-%m-%d').log"

# Functions
send_telegram_message() {
  local message="$1"
  curl -s -X POST "$TELEGRAM_WEBHOOK_URL" \
    -H 'Content-Type: application/json' \
    -d "$(jq -n --arg chat_id "$TELEGRAM_CHAT_ID" --arg text "$message" '{chat_id: $chat_id, text: $text}')"
}

# Go to application directory
cd "$APP_DIR"

# Activate virtual environment
source "/pokerPhase/myenv/bin/activate" || { send_telegram_message "Failed to activate virtual environment"; exit 1; }

sudo mkdir /logs
sudo chmod 777 /logs

# Start Flask server using flask and log output
nohup flask run --host=:: --port=5000 >> "$LOG_FILE" 2>&1 &
sleep 5

# Hit equalizer startup endpoint (this will keep running)
nohup curl -s --request POST http://[::1]:5000/equalizer/startup >> "$LOG_FILE" 2>&1 || {
  send_telegram_message "Equalizer Startup Failure"; exit 1;
}
