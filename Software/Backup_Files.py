#!/usr/bin/env python3
"""
Raspberry Pi Optimized Photo Backup

A script designed to efficiently transfer large photo files (~20MB each) from a Raspberry Pi's
ext4 SD card to an external exFAT SD card. The script addresses several performance issues:

Problem:
- Very slow write speeds when copying files to exFAT SD card
- Multiple Python processes running simultaneously due to cron job running too frequently
- Files getting locked during transfer
- High CPU usage causing system to slow down

Solution:
- Uses rsync with optimized parameters for Raspberry Pi and exFAT file systems
- Implements a lock file to prevent multiple instances from running simultaneously
- Bandwidth limiting to prevent CPU from being overwhelmed
- Proper logging of all operations
- Handles interruptions gracefully
- Command-line interface for flexibility
- Shows disk space and transfer progress

Recommended fstab entry for exFAT SD card:
/dev/sdb1  /media/pi/sdcard  exfat  rw,uid=1000,gid=1000,umask=000,fmask=0000,dmask=0000,nofail,noatime  0  2

Explanations of fstab options:
- rw: Mount with read/write access
- uid=1000,gid=1000: Set ownership to the Pi user (1000 is typically Pi's user/group ID)
- umask=000,fmask=0000,dmask=0000: Set full permissions for files and directories
- nofail: Skip this entry during boot if the device isn't present (prevents boot hangs)
- noatime: Don't update access time on files (improves performance)

Requirements:
- rsync must be installed on the system
- Python 3.6+

Usage:
  python3 photo_backup.py --src /path/to/source --dest /path/to/destination
  
  Optional arguments:
  --bwlimit   Set bandwidth limit in KB/s (default: 20000 KB/s)
  --log-file  Path to log file (default: ~/photo-backup.log)
  --verbose   Display verbose output
"""

import argparse
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Union, Tuple

# Constants
LOCK_FILE = "/tmp/photo_backup.lock"
DEFAULT_BANDWIDTH_LIMIT = 20000  # KB/s (20MB/s)
DEFAULT_LOG_FILE = os.path.expanduser("~/photo-backup.log")


class PhotoBackup:
    """
    Manages the efficient transfer of photos from source to destination using rsync
    with optimized parameters for Raspberry Pi and exFAT file systems.
    """
    
    def __init__(
        self,
        source_dir: str,
        dest_dir: str,
        bandwidth_limit: int = DEFAULT_BANDWIDTH_LIMIT,
        log_file: str = DEFAULT_LOG_FILE,
        verbose: bool = False
    ) -> None:
        """
        Initialize the backup manager with source and destination directories.
        
        Args:
            source_dir: Source directory containing photos to back up
            dest_dir: Destination directory where photos will be copied
            bandwidth_limit: Maximum bandwidth to use in KB/s
            log_file: Path to log file
            verbose: Whether to display verbose output
        """
        self.source_dir = self._ensure_trailing_slash(source_dir)
        self.dest_dir = self._ensure_trailing_slash(dest_dir)
        self.bandwidth_limit = bandwidth_limit
        self.log_file = log_file
        self.verbose = verbose
        
        # Set up logging
        self._setup_logging()
        
    def _ensure_trailing_slash(self, path: str) -> str:
        """Ensure the path ends with a trailing slash."""
        if not path.endswith('/'):
            return path + '/'
        return path
    
    def _setup_logging(self) -> None:
        """Configure the logging system."""
        # Reset any existing handlers
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
            
        # Configure logging with custom formatting
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        
        # Create a file handler
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setFormatter(logging.Formatter(log_format))
        file_handler.setLevel(logging.DEBUG if self.verbose else logging.INFO)
        
        # Create a console handler that only shows INFO and above
        # This ensures important messages show up in headless mode
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(log_format))
        console_handler.setLevel(logging.INFO)
        
        # Configure root logger
        logging.root.setLevel(logging.DEBUG if self.verbose else logging.INFO)
        logging.root.addHandler(file_handler)
        logging.root.addHandler(console_handler)
    
    def _create_lock(self) -> bool:
        """
        Create a lock file to prevent multiple instances from running.
        
        Returns:
            True if lock was created successfully, False if another instance is running
        """
        if os.path.exists(LOCK_FILE):
            # Check if the lock file is stale (older than 3 hours)
            lock_time = os.path.getmtime(LOCK_FILE)
            current_time = time.time()
            if current_time - lock_time > 10800:  # 3 hours in seconds
                logging.warning("Found stale lock file. Removing and continuing.")
                os.remove(LOCK_FILE)
            else:
                logging.warning("Another backup process is already running. Exiting.")
                return False
        
        try:
            with open(LOCK_FILE, 'w') as f:
                f.write(str(os.getpid()))
            return True
        except Exception as e:
            logging.error(f"Failed to create lock file: {e}")
            return False
    
    def _remove_lock(self) -> None:
        """Remove the lock file if it exists."""
        if os.path.exists(LOCK_FILE):
            try:
                os.remove(LOCK_FILE)
            except Exception as e:
                logging.error(f"Failed to remove lock file: {e}")
    
    def _validate_directories(self) -> bool:
        """
        Validate source and destination directories exist.
        
        Returns:
            True if both directories exist, False otherwise
        """
        if not os.path.isdir(self.source_dir):
            logging.error(f"Source directory does not exist: {self.source_dir}")
            return False
        
        if not os.path.isdir(self.dest_dir):
            try:
                logging.info(f"Destination directory does not exist. Creating: {self.dest_dir}")
                os.makedirs(self.dest_dir, exist_ok=True)
            except Exception as e:
                logging.error(f"Failed to create destination directory: {e}")
                return False
        
        return True
    
    def _build_rsync_command(self) -> List[str]:
        """
        Build the rsync command with optimized parameters.
        
        Returns:
            List of command arguments for subprocess
        """
        rsync_cmd = [
            "rsync",
            "-avh",              # Archive mode, verbose, human-readable sizes
            "--size-only",       # Skip files of the same size (faster than checksum)
            "--modify-window=2", # Allow 2-second timestamp difference
            "--whole-file",      # Transfer whole files, don't use delta-transfer
            "--no-compress",     # Disable compression (photos are already compressed)
            "--partial",         # Keep partially transferred files if interrupted
            "--timeout=300",     # 5-minute timeout for unresponsive operations
            "--info=progress2",  # Show overall progress information
            "--stats",           # Show detailed transfer statistics
            f"--bwlimit={self.bandwidth_limit}",  # Limit bandwidth
            "--max-delete=0",    # Safety feature: prevent mass deletions
            f"--log-file={self.log_file}",  # Log to file
            "--remove-source-files",  # Delete source files after successful transfer
            self.source_dir,     # Source directory
            self.dest_dir        # Destination directory
        ]
        return rsync_cmd
    
    def _get_disk_space(self, path: str) -> Dict[str, Union[int, float, str]]:
        """
        Get disk space information for a given path.
        
        Args:
            path: Directory path to check
            
        Returns:
            Dictionary with total, used, free space in bytes and human-readable format
        """
        try:
            total, used, free = shutil.disk_usage(path)
            return {
                'total_bytes': total,
                'used_bytes': used,
                'free_bytes': free,
                'total_human': self._format_size(total),
                'used_human': self._format_size(used),
                'free_human': self._format_size(free),
                'used_percent': round(used / total * 100, 1)
            }
        except Exception as e:
            logging.error(f"Error getting disk space for {path}: {e}")
            return {
                'total_bytes': 0,
                'used_bytes': 0,
                'free_bytes': 0,
                'total_human': '0B',
                'used_human': '0B',
                'free_human': '0B',
                'used_percent': 0
            }
    
    def _format_size(self, size_bytes: int) -> str:
        """Format bytes to human-readable size."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024 or unit == 'TB':
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024
    
    def _get_dir_size(self, path: str) -> Dict[str, Union[int, str]]:
        """
        Get the size of a directory and count of files.
        
        Args:
            path: Directory path to check
            
        Returns:
            Dictionary with size in bytes, human-readable format, and file count
        """
        try:
            total_size = 0
            file_count = 0
            
            for dirpath, _, filenames in os.walk(path):
                file_count += len(filenames)
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if os.path.isfile(fp) and not os.path.islink(fp):
                        total_size += os.path.getsize(fp)
            
            return {
                'size_bytes': total_size,
                'size_human': self._format_size(total_size),
                'file_count': file_count
            }
        except Exception as e:
            logging.error(f"Error getting directory size for {path}: {e}")
            return {
                'size_bytes': 0,
                'size_human': '0B',
                'file_count': 0
            }
    
    def _display_progress(self, process, stop_event):
        """
        Display progress information periodically.
        
        Args:
            process: The subprocess running rsync
            stop_event: Threading event to signal when to stop
        """
        # Track progress
        transferred_bytes = 0
        last_update_time = time.time()
        speed = 0
        
        # Progress parsing regex patterns
        progress_pattern = re.compile(r'(\d+)%')
        speed_pattern = re.compile(r'(\d+\.\d+\w+/s)')
        file_pattern = re.compile(r'to-chk=(\d+)/(\d+)')
        
        try:
            while not stop_event.is_set():
                # Display disk space every 30 seconds
                if time.time() - last_update_time >= 30:
                    src_space = self._get_disk_space(self.source_dir)
                    dest_space = self._get_disk_space(self.dest_dir)
                    src_size = self._get_dir_size(self.source_dir)
                    dest_size = self._get_dir_size(self.dest_dir)
                    
                    logging.info(
                        f"Source: {src_size['file_count']} files, "
                        f"{src_size['size_human']} | "
                        f"Dest: {dest_size['file_count']} files, "
                        f"{dest_size['size_human']}"
                    )
                    logging.info(
                        f"Disk space - Source: {src_space['used_human']}/{src_space['total_human']} "
                        f"({src_space['used_percent']}%) | "
                        f"Destination: {dest_space['used_human']}/{dest_space['total_human']} "
                        f"({dest_space['used_percent']}%)"
                    )
                    
                    last_update_time = time.time()
                
                time.sleep(5)
                
        except Exception as e:
            logging.error(f"Error in progress display: {e}")
    
    def run(self) -> int:
        """
        Run the backup process.
        
        Returns:
            0 for success, non-zero for failure
        """
        start_time = datetime.now()
        logging.info(f"Starting backup at {start_time}")
        logging.info(f"Source: {self.source_dir}")
        logging.info(f"Destination: {self.dest_dir}")
        
        # Create lock file
        if not self._create_lock():
            return 1
        
        try:
            # Validate directories
            if not self._validate_directories():
                return 2
            
            # Display initial disk space
            src_space = self._get_disk_space(self.source_dir)
            dest_space = self._get_disk_space(self.dest_dir)
            src_size = self._get_dir_size(self.source_dir)
            dest_size = self._get_dir_size(self.dest_dir)
            
            logging.info(
                f"Source: {src_size['file_count']} files, {src_size['size_human']} | "
                f"Destination: {dest_size['file_count']} files, {dest_size['size_human']}"
            )
            logging.info(
                f"Disk space - Source: {src_space['used_human']}/{src_space['total_human']} "
                f"({src_space['used_percent']}%) | "
                f"Destination: {dest_space['used_human']}/{dest_space['total_human']} "
                f"({dest_space['used_percent']}%)"
            )
            
            # Build and execute rsync command
            cmd = self._build_rsync_command()
            logging.info(f"Running rsync command: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1  # Line buffered
            )
            
            # Start progress display thread
            stop_event = threading.Event()
            progress_thread = threading.Thread(
                target=self._display_progress,
                args=(process, stop_event)
            )
            progress_thread.daemon = True
            progress_thread.start()
            
            # Monitor the process and log progress
            for line in process.stdout:
                line = line.strip()
                if line:
                    if "to-chk=" in line or "%" in line:
                        # This is a progress line, print to console and log as info
                        print(line, flush=True)
                        logging.info(line)
                    else:
                        # Regular output, log as debug
                        logging.debug(line)
            
            # Wait for process to complete
            return_code = process.wait()
            
            # Stop progress display thread
            stop_event.set()
            if progress_thread.is_alive():
                progress_thread.join(timeout=2)
            
            # Display final disk space
            src_space = self._get_disk_space(self.source_dir)
            dest_space = self._get_disk_space(self.dest_dir)
            src_size = self._get_dir_size(self.source_dir)
            dest_size = self._get_dir_size(self.dest_dir)
            
            logging.info(
                f"Final state - Source: {src_size['file_count']} files, {src_size['size_human']} | "
                f"Destination: {dest_size['file_count']} files, {dest_size['size_human']}"
            )
            
            # Log the result
            if return_code == 0:
                end_time = datetime.now()
                duration = end_time - start_time
                logging.info(f"Backup completed successfully at {end_time} (Duration: {duration})")
                return 0
            else:
                error_output = process.stderr.read()
                logging.error(f"Backup failed with return code {return_code}")
                logging.error(f"Error output: {error_output}")
                return return_code
            
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            return 3
        finally:
            # Always remove the lock file
            self._remove_lock()


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Optimized photo backup for Raspberry Pi with exFAT SD card'
    )
    
    parser.add_argument(
        '--src',
        required=True,
        help='Source directory containing photos to back up'
    )
    
    parser.add_argument(
        '--dest',
        required=True,
        help='Destination directory where photos will be copied'
    )
    
    parser.add_argument(
        '--bwlimit',
        type=int,
        default=DEFAULT_BANDWIDTH_LIMIT,
        help=f'Bandwidth limit in KB/s (default: {DEFAULT_BANDWIDTH_LIMIT})'
    )
    
    parser.add_argument(
        '--log-file',
        default=DEFAULT_LOG_FILE,
        help=f'Path to log file (default: {DEFAULT_LOG_FILE})'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Display verbose output'
    )
    
    return parser.parse_args()


def main() -> int:
    """Main entry point for the script."""
    args = parse_arguments()
    
    backup = PhotoBackup(
        source_dir=args.src,
        dest_dir=args.dest,
        bandwidth_limit=args.bwlimit,
        log_file=args.log_file,
        verbose=args.verbose
    )
    
    return backup.run()


if __name__ == "__main__":
    sys.exit(main())
