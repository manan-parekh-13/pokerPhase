# create backup and send it
docker exec -it mysql-server /bin/bash
mysqldump -u root -p'canyouseemypassword' --verbose pokerPhase > /backup/db_backup.sql
exit
sudo pigz -k /backup/db_backup.sql
aws s3 cp /backup/db_backup.sql.gz s3://poker-phase-mysql/db_backup.sql.gz --debug