#!/bin/sh

label=$(date +%Y%m%d%H%M%S)

output='/home/backup/'
database_path=$output$label'-database.sql'
code_path=$output$label'-code.zip'

cd $output 
ls -tp | grep -v '/$' | tail -n +3 | xargs -I {} rm -- {}

/usr/bin/docker exec -i timescaledb pg_dump -U evalai evalai > $database_path

/usr/bin/zip -r $code_path /home/evalai/

scp $database_path root@172.20.81.218:/home/evalai_backup
scp $code_path root@172.20.81.218:/home/evalai_backup
