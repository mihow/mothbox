#!/usr/bin/env python3
from typing import Optional, List
import os
import subprocess
import logging
from pathlib import Path
import time

LOG_DIR: Path = Path("/home/pi/Desktop/Mothbox/logs/aws-sync.log")
# LOG_DIR: Path = Path("/var/log/aws-sync.log")
# Configure logging
logging.basicConfig(
    filename=LOG_DIR,
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

# Environment-based configuration
AWS_BUCKET: str = os.getenv('AWS_BUCKET', '')
AWS_PREFIX: str = os.getenv('AWS_PREFIX', '')
ENDPOINT_URL: Optional[str] = os.getenv('AWS_ENDPOINT_URL')
LOCAL_DIR: Path = Path("/home/pi/Desktop/Mothbox/photos")

# Validate required environment variables
if not AWS_BUCKET:
    logging.error("AWS_BUCKET environment variable is required")
    exit(1)

# Construct S3 URL (handle prefix with/without leading/trailing slashes)
S3_PATH: str = f"s3://{AWS_BUCKET.strip('/')}/{AWS_PREFIX.strip('/')}".rstrip('/')

def check_network() -> bool:
    """
    Check for network connectivity using multiple methods
    
    Returns:
        bool: True if network is available, False otherwise
    """
    def ping_test() -> bool:
        try:
            subprocess.run(['ping', '-c', '1', '-W', '3', '8.8.8.8'],
                         check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def wifi_status() -> bool:
        try:
            output = subprocess.check_output(['iwgetid']).decode('utf-8')
            return bool(output.strip())
        except subprocess.CalledProcessError:
            return False
    
    return wifi_status() and ping_test()

def wait_for_network(max_attempts: int = 3, delay: int = 5) -> bool:
    """
    Wait for network connectivity with retries
    
    Args:
        max_attempts: Maximum number of connection attempts
        delay: Delay between attempts in seconds
    
    Returns:
        bool: True if network becomes available, False if all attempts fail
    """
    for attempt in range(max_attempts):
        if check_network():
            return True
        if attempt < max_attempts - 1:
            logging.info(f"Network not available, waiting {delay} seconds... "
                        f"(attempt {attempt + 1}/{max_attempts})")
            time.sleep(delay)
    return False

def run_aws_sync(directory: Path, s3_path: str, endpoint_url: Optional[str]) -> bool:
    """
    Run AWS S3 sync command
    
    Args:
        directory: Local directory to sync
        s3_path: Full S3 path including bucket and prefix
        endpoint_url: Custom endpoint URL if any
        
    Returns:
        True if sync successful, False otherwise
    """
    cmd: List[str] = ['aws', 's3', 'sync', str(directory), s3_path]
    if endpoint_url:
        cmd.extend(['--endpoint-url', endpoint_url])
        
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        logging.info(f"S3 sync completed successfully to {s3_path}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"S3 sync failed: {e.stderr}")
        return False

def main() -> int:
    """
    Main function to sync files to S3
    
    Returns:
        0 if successful, 1 if errors occurred
    """
    try:
        # Check for network connectivity
        if not wait_for_network():
            logging.error("No network connectivity available after retries")
            return 1
            
        # Log the configuration
        logging.info(f"Starting sync with configuration:")
        logging.info(f"  Local directory: {LOCAL_DIR}")
        logging.info(f"  S3 path: {S3_PATH}")
        logging.info(f"  Endpoint URL: {ENDPOINT_URL or 'default'}")
        
        # Verify directory exists
        if not LOCAL_DIR.exists():
            logging.error(f"Directory {LOCAL_DIR} does not exist")
            return 1
            
        # Run AWS sync
        if not run_aws_sync(LOCAL_DIR, S3_PATH, ENDPOINT_URL):
            return 1
        
        return 0
        
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
