#!/bin/bash

SLACK_WEBHOOK_URL="https://hooks.slack.com/services/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"

# Functions
send_slack_message() {
  local message=$1
  curl -X POST -H 'Content-type: application/json' --data "{\"text\":\"${message}\"}" $SLACK_WEBHOOK_URL
}

# ---------------- SETUP LOGGING ----------------
echo "Setting up logging..."
LOG_FILE="/var/log/pokerPhase.log"

# Redirect stdout and stderr to log file while keeping it on terminal
exec > >(tee -a "$LOG_FILE") 2>&1

# Ensure CloudWatch Agent is installed and running
sudo yum install -y amazon-cloudwatch-agent

# Create CloudWatch configuration
sudo mkdir -p /opt/aws/amazon-cloudwatch-agent/etc/
cat <<EOF | sudo tee /opt/aws/amazon-cloudwatch-agent/etc/config.json
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/pokerPhase.log",
            "log_group_name": "pokerPhase-logs",
            "log_stream_name": "{instance_id}",
            "timezone": "Local"
          }
        ]
      }
    }
  }
}
EOF

# Start CloudWatch Agent
sudo amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:/opt/aws/amazon-cloudwatch-agent/etc/config.json -s
sudo systemctl enable amazon-cloudwatch-agent
sudo systemctl start amazon-cloudwatch-agent

echo "CloudWatch log setup complete."

# ---------------- INSTALL DEPENDENCIES ----------------
echo "Installing required packages..."
sudo yum install -y python3-pip gcc gcc-c++ python3-devel docker
echo "Package installation complete."

# ---------------- START DOCKER ----------------
echo "Starting Docker service..."
sudo systemctl start docker
sudo systemctl enable docker
echo "Docker service started."

# ---------------- GET ENVIRONMENT VARIABLES FROM SSM ----------------
echo "Fetching environment variables from ssm param store."
MYSQL_PASSWORD=$(aws ssm get-parameter --name "MYSQL_ROOT_PASSWORD" --with-decryption --query "Parameter.Value" --output text)
GMAIL_API_KEY=$(aws ssm get-parameter --name "GMAIL_API_KEY" --with-decryption --query "Parameter.Value" --output text)
PASSWORD=$(aws ssm get-parameter --name "PASSWORD" --with-decryption --query "Parameter.Value" --output text)
echo "Fetched environment variables."

# ---------------- ADD ENVIRONMENT VARIABLES ----------------
echo "Adding environment variables to ~/.bashrc..."
cat <<EOF >> ~/.bashrc
export PYTHONPATH=/home/ec2-user/pokerPhase:\$PYTHONPATH
export GMAIL_API_KEY=$GMAIL_API_KEY
export USER_ID=AWZ743
export MYSQL_PASSWORD=$MYSQL_PASSWORD
export PASSWORD=$PASSWORD
export FLASK_ENV=prod
export FLASK_APP=/home/ec2-user/pokerPhase/equalizer/web.py
alias stop='/home/ec2-user/pokerPhase/scripts/stop_equalizer.sh'
alias start='/home/ec2-user/pokerPhase/scripts/start_equalizer.sh'
EOF
source ~/.bashrc
echo "Environment variables added."

# ---------------- SETUP PokerPhase ENVIRONMENT ----------------
echo "Setting up PokerPhase environment..."
cd /pokerPhase
pip3 install -r requirements.txt -r dev_requirements.txt
python3 -m venv myenv
echo "PokerPhase environment setup complete."

# ---------------- CONFIGURE SSH KEEP-ALIVE ----------------
echo "Configuring SSH keep-alive..."
echo -e "\nClientAliveInterval 60\nClientAliveCountMax 3" | sudo tee -a /etc/ssh/sshd_config
sudo systemctl restart sshd
echo "SSH keep-alive configured."

# ---------------- SET TIMEZONE ----------------
echo "Setting timezone to Asia/Kolkata..."
sudo timedatectl set-timezone Asia/Kolkata
echo "Timezone set successfully."

# ---------------- INSTALL PY-SPY PROFILER ----------------
echo "Installing py-spy..."
pip3 install py-spy
echo "py-spy installed."

# ---------------- SETUP MYSQL ----------------
sudo mkdir /backup
sudo docker pull mysql:8
echo "MySQL image pulled successfully."
sudo docker run -d --name mysql-server -e MYSQL_ROOT_PASSWORD="$MYSQL_PASSWORD" -e MYSQL_DATABASE=pokerPhase -p 3308:3306 -v /backup:/backup mysql:8
echo "MySQL container started."

# --------------- INIT POKER PHASE DB -------------------
sudo aws s3 cp s3://poker-phase-mysql/db_init.sql.gz /backup/db_init.sql.gz --debug
sleep 10
send_slack_message "Downloaded init db file from s3.";
gunzip -c /backup/db_init.sql.gz | sudo tee /backup/db_init.sql > /dev/null
send_slack_message "Unzipped the file.";
sudo docker exec -i mysql-server mysql -u root -p"$MYSQL_PASSWORD" -v pokerPhase < /backup/db_init.sql
send_slack_message "Mysql db init completed.";

# ----------- REMOVE ELASTIC-IP ------------------------------------
INSTANCE_ID=$(aws ec2 describe-instances --filters Name=tag:Name,Values=active,Name=instance-state-name,Values=running --query "Reservations[*].Instances[*].InstanceId" --output text)
ELASTIC_IP=$(aws ec2 describe-addresses --filters Name=instance-id,Values="$INSTANCE_ID" --query "Addresses[*].PublicIp" --output text)
send_slack_message "$INSTANCE_ID"
send_slack_message "$ELASTIC_IP"
aws ec2 dissociate-address --public-ip "$ELASTIC_IP" --instance-id "$INSTANCE_ID"
aws ec2 release-address --public-ip "$ELASTIC_IP"
send_slack_message "Elastic IP released."

# ------------- START EQUALIZER --------------------------------
/pokerPhase/scripts/start_equalizer.sh

# ---------------- SCRIPT COMPLETION ----------------
echo "Setup complete! All logs are being sent to AWS CloudWatch."

