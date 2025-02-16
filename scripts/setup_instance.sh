#!/bin/bash

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

# ---------------- SETUP MYSQL ----------------
sudo docker pull mysql:8
echo "MySQL image pulled successfully."
sudo docker run --name mysql-server -e MYSQL_ROOT_PASSWORD=$MYSQL_PASSWORD -d -p 3308:3306 mysql:8
echo "MySQL container started."

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

# ---------------- SCRIPT COMPLETION ----------------
echo "Setup complete! All logs are being sent to AWS CloudWatch."
