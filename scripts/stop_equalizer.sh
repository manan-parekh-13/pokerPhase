#!/bin/bash

# Configuration
HOME_PATH="/home/ec2-user"
LOG_DIR="$HOME_PATH/logs"
LOG_FILE="$LOG_DIR/equalizer_$(date +'%Y-%m-%d').log"
SLACK_WEBHOOK_URL="https://hooks.slack.com/services/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"

# Functions
send_slack_message() {
  local message=$1
  curl -X POST -H 'Content-type: application/json' --data "{\"text\":\"${message}\"}" $SLACK_WEBHOOK_URL
}

nohup curl -s --request GET http://localhost:5000/orders >> "$LOG_FILE" 2>&1 && {
  send_slack_message "Orders Fetched";
} || {
  send_slack_message "Order Fetch Failure";
}

pkill -f "flask"

send_slack_message "Stopped the flask server";
