# ps1 file: test.ps1

# set path to python executable
$env:DB_HOST = "192.168.88.140"
$env:DB_PORT = "15432"
$env:DB_NAME = "mydatabase"
$env:DB_USER = "luyang2008"
$env:DB_PASSWORD = "Admin@123456"


# This is a batch file to run the OpenGauss library management system
# start the database
python sql.py --filename library_start.sql
# start the web UI
Write-Host "Starting Flask app (Press Ctrl+C to stop)..."
try {
    python ui.py
} finally {
    Write-Host "Cleaning up database..."
    python sql.py --filename library_end.sql
}