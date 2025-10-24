#!/bin/bash
# This is a bash script to run the OpenGauss library management system

# set path to python executable
export DB_HOST="192.168.88.140"
export DB_PORT="15432"
export DB_NAME="mydatabase"
export DB_USER="luyang2008"
export DB_PASSWORD="Admin@123456"

python sql.py --filename library_start.sql
echo "Starting Flask app (Press Ctrl+C to stop)..."
python ui.py