# AWS S3 Sync Service for Raspberry Pi

This service automatically syncs a local directory to an S3-compatible storage service every 5 minutes. It's designed for Raspberry Pi OS (Debian 12) and handles intermittent network connections gracefully.

## Prerequisites

- Raspberry Pi running Raspberry Pi OS (Debian 12)
- Python 3 (comes pre-installed)
- AWS CLI version 2

## Installation

1. Install AWS CLI:
```bash
# Download and run the AWS CLI installer
curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
rm -rf aws awscliv2.zip
```

2. Configure AWS CLI:
```bash
aws configure
```
Enter your:
- AWS Access Key ID
- AWS Secret Access Key
- Default region
- Default output format (json recommended)

3. Create the service directory:
```bash
mkdir -p /home/pi/Desktop/Mothbox
```

4. Create the sync script:
```bash
nano /home/pi/Desktop/Mothbox/aws-s3-sync.py
```
Copy the Python script content into this file.

5. Make the script executable:
```bash
chmod +x /home/pi/Desktop/Mothbox/aws-s3-sync.py
```

## Service Configuration

1. Create the systemd service file:
```bash
sudo ln -s $(pwd)/aw
s-s3-sync.service  /etc/systemd/system/

2. Set your AWS configuration in the service file:
```bash
sudo nano /etc/systemd/system/aws-s3-sync.service
```
Update these environment variables:
```ini
Environment=AWS_ACCESS_KEY_ID=your_access_key
Environment=AWS_SECRET_ACCESS_KEY=your_secret_key
Environment=AWS_DEFAULT_REGION=your_region
Environment=AWS_ENDPOINT_URL=your_custom_endpoint_url
Environment=AWS_BUCKET=your-bucket-name
Environment=AWS_PREFIX=path/to/files
```

4. Enable and start the service and timer:
```bash
sudo systemctl daemon-reload
sudo systemctl enable aws-s3-sync.service
sudo systemctl enable aws-s3-sync.timer
sudo systemctl start aws-s3-sync.timer
```

## Verification and Monitoring

Check service status:
```bash
sudo systemctl status aws-s3-sync.service
```

Check timer status:
```bash
sudo systemctl status aws-s3-sync.timer
systemctl list-timers aws-s3-sync.timer
```

View logs:
```bash
sudo tail -f /var/log/aws-sync.log
```

## Adjusting the Timer

The default configuration runs every 5 minutes. To change this:

1. Edit the timer file:
```bash
sudo nano /etc/systemd/system/aws-s3-sync.timer
```

2. Modify the `OnUnitActiveSec` value (e.g., `10min` for every 10 minutes)

3. Reload the daemon:
```bash
sudo systemctl daemon-reload
sudo systemctl restart aws-s3-sync.timer
```

## Troubleshooting

### Network Issues
- The service uses systemd's network-online target
- Logs show network connectivity status
- Service will retry on network failures

### Sync Issues
Check logs for errors:
```bash
sudo tail -f /var/log/aws-sync.log
```

Common issues:
- Invalid AWS credentials
- Network connectivity problems
- Permission issues
- Invalid endpoint URL

### Service Won't Start
Check service status:
```bash
sudo systemctl status aws-s3-sync.service
journalctl -u aws-s3-sync.service
```

### Manual Testing
Run the sync script manually:
```bash
/home/pi/Desktop/Mothbox/aws-s3-sync.sh
```

## Uninstallation

To remove the service:
```bash
sudo systemctl stop aws-s3-sync.timer
sudo systemctl disable aws-s3-sync.timer
sudo systemctl disable aws-s3-sync.service
sudo rm /etc/systemd/system/aws-s3-sync.service
sudo rm /etc/systemd/system/aws-s3-sync.timer
sudo systemctl daemon-reload
```
