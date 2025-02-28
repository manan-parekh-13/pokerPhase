# create backup and send it
current_datetime=$(date +"%Y-%m-%d_%H:%M:%S")
sudo docker exec -i mysql-server mysqldump -u root -p"$MYSQL_PASSWORD" --verbose --no-create-info pokerPhase arbitrage_opportunities order_info raw_ticker_data | sudo tee "/backup/db_backup_${current_datetime}.sql" > /dev/null
sudo pigz -k "/backup/db_backup_${current_datetime}.sql"
aws s3 cp "/backup/db_backup_${current_datetime}.sql.gz" "s3://poker-phase-mysql/db_backup_${current_datetime}.sql.gz" --debug