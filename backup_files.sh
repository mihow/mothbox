#!/bin/bash

# Define rsync options as an array with comments
rsync_opts=(
  "-a"            # Archive mode (preserves permissions, timestamps, etc.)
  "-v"            # Verbose output
  "-h"            # Human-readable sizes
  "--size-only"   # Skip files of the same size (faster than checksum)
  "--modify-window=2"  # Allow 2-second timestamp difference (for filesystem differences)
  "--whole-file"  # Transfer whole files, don't use delta-transfer (better for Raspberry Pi CPU)
  "--no-compress" # Disable compression (photos are already compressed, saves CPU)
  # "--partial"     # Keep partially transferred files if interrupted
  "--timeout=300" # 5-minute timeout for unresponsive operations
  "--info=progress2"  # Show overall progress information
  "--stats"       # Show detailed transfer statistics
  # "--bwlimit=20000"    # Limit bandwidth to 20MB/s (reduces CPU load)
  "--max-delete=0"    # Safety feature: prevent mass deletions
  "--log-file=/home/pi/rsync-photos.log"  # Log to file instead of just stdout
  "--remove-source-files"  # Delete source files after successful transfer
)

# Log start with timestamp
echo "Starting backup at $(date)" >> /home/pi/backup-summary.log

# Source and destination paths
# SRC_DIR="/home/pi/photos/"
# DEST_DIR="/media/pi/sdcard/photos_backup/"
SRC_DIR="/media/pi/sdcard/photos_backup/photos/"
DEST_DIR="/media/pi/sdcard/photos_backup/"

# Run rsync with the defined options
rsync "${rsync_opts[@]}" "$SRC_DIR" "$DEST_DIR"

# Check exit code
if [ $? -eq 0 ]; then
  echo "Transfer completed successfully at $(date)" >> /home/pi/backup-summary.log
else
  echo "Transfer failed or had issues at $(date)" >> /home/pi/backup-summary.log
fi
