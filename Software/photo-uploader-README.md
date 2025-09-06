# Photo Uploader Service

A simple, reliable photo upload service using s5cmd for S3-compatible object storage.

## Prerequisites

- s5cmd installed on the system
- Network connectivity
- Valid S3-compatible storage credentials

## Installation

1. **Install s5cmd** (if not already installed):
```bash
# Download and install s5cmd
curl -L https://github.com/peak/s5cmd/releases/latest/download/s5cmd_2.2.2_Linux-64bit.tar.gz | tar -xz
sudo mv s5cmd /usr/local/bin/
```

2. **Configure credentials**:

   s5cmd uses the standard AWS credentials file. Create `~/.aws/credentials`:
   ```bash
   mkdir -p ~/.aws
   cat > ~/.aws/credentials << EOF
   [default]
   aws_access_key_id = your_access_key
   aws_secret_access_key = your_secret_key
   EOF
   ```

   **Optional: Use AWS profiles** for multiple configurations:
   ```bash
   cat > ~/.aws/credentials << EOF
   [default]
   aws_access_key_id = your_default_key
   aws_secret_access_key = your_default_secret

   [mothbox]
   aws_access_key_id = your_mothbox_key
   aws_secret_access_key = your_mothbox_secret
   EOF
   ```
   
   Then specify the profile in `photo-uploader.service`:
   ```ini
   Environment=AWS_PROFILE=mothbox
   ```

3. **Update configuration** in `photo-uploader.service`:
   ```ini
   Environment=S3_ENDPOINT_URL=https://your-endpoint.com
   Environment=S3_BUCKET=your-bucket-name
   Environment=S3_PREFIX=your/path/prefix
   ```

4. **Create photos directory**:
   ```bash
   mkdir -p /home/pi/Desktop/mothbox-mihow/photos
   ```

5. **Install and start the service**:
   ```bash
   sudo cp photo-uploader.service /etc/systemd/system/
   sudo cp photo-uploader.timer /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable photo-uploader.timer
   sudo systemctl start photo-uploader.timer
   ```

## Usage

### Check Status
```bash
# Check timer status
sudo systemctl status photo-uploader.timer
systemctl list-timers photo-uploader.timer

# Check service status
sudo systemctl status photo-uploader.service
```

### View Logs
```bash
# View systemd logs (when running as service)
journalctl -u photo-uploader.service -f

# When running manually, logs print to console
```

### Manual Upload
```bash
# Run upload manually
/home/pi/Desktop/mothbox-mihow/Software/photo_uploader.py
```

### Stop/Start Service
```bash
# Stop uploads
sudo systemctl stop photo-uploader.timer

# Start uploads
sudo systemctl start photo-uploader.timer
```

## Configuration

The service uploads files from `/home/pi/Desktop/mothbox-mihow/photos/` to your configured S3 bucket every 5 minutes.

Key settings in `photo-uploader.service`:
- `S3_ENDPOINT_URL`: Your S3-compatible storage endpoint
- `S3_BUCKET`: Target bucket name
- `S3_PREFIX`: Path prefix in the bucket (optional)

## Features

- **S3 Access Verification**: Tests bucket access before attempting sync
- **Network Resilience**: Waits for connectivity and handles network failures
- **Comprehensive Logging**: Detailed logs for monitoring and troubleshooting
- **Standard AWS Credentials**: Uses ~/.aws/credentials like all AWS tools
- **Profile Support**: Can use different AWS profiles for multiple configurations

## Troubleshooting

### Service won't start
```bash
# Check service status and logs
sudo systemctl status photo-uploader.service
journalctl -u photo-uploader.service

# Test s5cmd manually
s5cmd --endpoint-url https://your-endpoint.com ls s3://your-bucket/
```

### Network issues
The service automatically waits for network connectivity and retries failed uploads.

### Permission issues
Ensure the pi user has read access to the photos directory and write access to the log directory.

## Uninstall

```bash
sudo systemctl stop photo-uploader.timer
sudo systemctl disable photo-uploader.timer
sudo rm /etc/systemd/system/photo-uploader.service
sudo rm /etc/systemd/system/photo-uploader.timer
sudo systemctl daemon-reload
