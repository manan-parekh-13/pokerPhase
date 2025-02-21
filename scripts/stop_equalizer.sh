#!/bin/bash

# Configuration
HOME_PATH="/home/ec2-user"
LOG_DIR="$HOME_PATH/logs"
LOG_FILE="$LOG_DIR/equalizer_$(date +'%Y-%m-%d').log"
TELEGRAM_WEBHOOK_URL="https://api.telegram.org/bot7255610692:AAHSO6A4KxV9dVAhsNN1vizs1tZ97IyP48o/sendMessage"

# Functions
send_telegram_message() {
  local message=$1
  curl -X POST -H 'Content-type: application/json' -d "{\"chat_id\": \"-4694389902\", \"text\": \"${message}\"}" $TELEGRAM_WEBHOOK_URL
}

nohup curl -s --request GET http://localhost:5000/orders.json >> "$LOG_FILE" 2>&1 && {
  send_telegram_message "Orders Fetched";
} || {
  send_telegram_message "Order Fetch Failure";
}

pkill -f "flask"

send_telegram_message "Stopped the flask server";

sudo docker stop mysql-server;
