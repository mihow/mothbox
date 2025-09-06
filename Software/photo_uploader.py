#!/usr/bin/env python3
from typing import Optional, List
import os
import subprocess
import logging
from pathlib import Path
import time
import sys

# Configure logging - print to console, let systemd handle file logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Environment-based configuration
S3_BUCKET: str = os.environ['S3_BUCKET']
S3_PREFIX: str = os.environ['S3_PREFIX']
S3_ENDPOINT_URL: Optional[str] = os.getenv('S3_ENDPOINT_URL')
LOCAL_DIR: Path = Path(os.environ['S3_LOCAL_DIR'])

# Construct S3 URL (handle prefix with/without leading/trailing slashes)
if S3_PREFIX:
    S3_PATH: str = f"s3://{S3_BUCKET.strip('/')}/{S3_PREFIX.strip('/')}/"
else:
    S3_PATH: str = f"s3://{S3_BUCKET.strip('/')}/"

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

def test_s3_access(s3_path: str, endpoint_url: Optional[str]) -> bool:
    """
    Test if we can access the S3 bucket/path
    
    Args:
        s3_path: Full S3 path including bucket and prefix
        endpoint_url: Custom endpoint URL if any
        
    Returns:
        True if accessible, False otherwise
    """
    # Extract bucket from s3_path for testing
    bucket_path = s3_path.split('/', 3)[:3]  # s3://bucket/
    bucket_url = '/'.join(bucket_path) + '/'
    
    cmd: List[str] = ['s5cmd', 'ls', bucket_url]
    
    # Set up environment for s5cmd
    env = os.environ.copy()
    if endpoint_url:
        env['S3_ENDPOINT_URL'] = endpoint_url
        
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, env=env)
        logging.info(f"S3 bucket access verified: {bucket_url}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"S3 bucket access failed: {e.stderr}")
        return False

def run_s5cmd_sync(directory: Path, s3_path: str, endpoint_url: Optional[str]) -> bool:
    """
    Run s5cmd sync command
    
    Args:
        directory: Local directory to sync
        s3_path: Full S3 path including bucket and prefix
        endpoint_url: Custom endpoint URL if any
        
    Returns:
        True if sync successful, False otherwise
    """
    # Use directory/* to sync contents rather than the directory itself
    # This prevents creating a nested directory structure on S3
    cmd: List[str] = ['s5cmd', 'sync', f"{str(directory)}/*", s3_path]
    
    # Set up environment for s5cmd
    env = os.environ.copy()
    if endpoint_url:
        env['S3_ENDPOINT_URL'] = endpoint_url
        
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, env=env)
        logging.info(f"s5cmd sync completed successfully to {s3_path}")
        if result.stdout:
            logging.info(f"s5cmd output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"s5cmd sync failed: {e.stderr}")
        return False

def main() -> int:
    """
    Main function to sync files to S3
    
    Returns:
        0 if successful, 1 if errors occurred
    """
    # Check if running in check-only mode
    check_only = "--check-only" in sys.argv
    
    try:
        # Check for network connectivity
        if not wait_for_network():
            logging.error("No network connectivity available after retries")
            return 1
            
        # Log the configuration
        logging.info(f"Starting photo upload with configuration:")
        logging.info(f"  Local directory: {LOCAL_DIR}")
        logging.info(f"  S3 path: {S3_PATH}")
        logging.info(f"  Endpoint URL: {S3_ENDPOINT_URL or 'default'}")
        logging.info(f"  Check-only mode: {check_only}")
        
        # Verify directory exists
        if not LOCAL_DIR.exists():
            logging.error(f"Directory {LOCAL_DIR} does not exist")
            return 1
            
        # Test S3 bucket access before attempting sync
        if not test_s3_access(S3_PATH, S3_ENDPOINT_URL):
            logging.error("S3 bucket access test failed, skipping sync")
            return 1
            
        # If check-only mode, exit here after running tests
        if check_only:
            logging.info("Check-only mode, skipping sync operation")
            return 0
            
        # Run s5cmd sync
        if not run_s5cmd_sync(LOCAL_DIR, S3_PATH, S3_ENDPOINT_URL):
            return 1
        
        return 0
        
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
