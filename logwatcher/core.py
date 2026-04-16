```python
import os
import time
import threading
import logging
from pathlib import Path
from typing import Optional, Callable, List, Dict, Any

logger = logging.getLogger(__name__)


class LogWatcher:
    """
    A lightweight log file watcher that monitors files for new lines and triggers callbacks.
    
    This class provides basic functionality to watch one or more log files for changes,
    detect new lines added to the end of files, and invoke user-defined handlers.
    
    Features:
    - Watch single or multiple log files
    - Handle file rotation (detects when file is truncated or replaced)
    - Thread-safe operation with configurable polling interval
    - Callback-based event handling
    - Basic state persistence (last read position)
    """

    def __init__(
        self,
        paths: List[str],
        callback: Callable[[str, str], None],
        poll_interval: float = 1.0,
        encoding: str = "utf-8",
        follow_symlinks: bool = True,
        buffer_size: int = 8192,
        auto_start: bool = True,
    ):
        """
        Initialize the LogWatcher instance.

        Args:
            paths: List of file paths to monitor
            callback: Function to call when new log lines are detected.
                     Signature: callback(file_path: str, line: str)
            poll_interval: Time in seconds between file checks
            encoding: Text encoding to use when reading files
            follow_symlinks: Whether to follow symbolic links
            buffer_size: Buffer size for reading files
            auto_start: Whether to start watching immediately
        """
        self.paths = [Path(p) for p in paths]
        self.callback = callback
        self.poll_interval = max(0.1, poll_interval)  # Minimum 100ms
        self.encoding = encoding
        self.follow_symlinks = follow_symlinks
        self.buffer_size = buffer_size
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._file_positions: Dict[Path, int] = {}
        self._file_inodes: Dict[Path, Optional[int]] = {}

        # Validate paths
        for path in self.paths:
            if not path.exists():
                logger.warning(f"Log file does not exist: {path}")
            elif not path.is_file():
                logger.warning(f"Path is not a file: {path}")

        if auto_start:
            self.start()

    def start(self) -> None:
        """Start watching log files."""
        if self._running:
            logger.warning("LogWatcher is already running")
            return

        # Initialize file positions and inodes
        self._initialize_file_state()

        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
        logger.info(f"Started LogWatcher for {len(self.paths)} file(s)")

    def stop(self) -> None:
        """Stop watching log files."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("Stopped LogWatcher")

    def _initialize_file_state(self) -> None:
        """Initialize tracking state for each file."""
        for path in self.paths:
            try:
                # Get current file size
                size = path.stat().st_size
                self._file_positions[path] = size

                # Get inode for rotation detection
                try:
                    stat = path.stat(follow_symlinks=self.follow_symlinks)
                    self._file_inodes[path] = stat.st_ino
                except OSError:
                    self._file_inodes[path] = None
                    logger.debug(f"Could not get inode for {path}")
            except OSError as e:
                logger.error(f"Error initializing state for {path}: {e}")
                self._file_positions[path] = 0
                self._file_inodes[path] = None

    def _watch_loop(self) -> None:
        """Main watching loop."""
        while self._running:
            try:
                self._check_files()
            except Exception as e:
                logger.error(f"Error in watch loop: {e}")
            
            time.sleep(self.poll_interval)

    def _check_files(self) -> None:
        """Check all watched files for new content."""
        for path in self.paths:
            if not path.exists():
                continue

            try:
                self._check_file(path)
            except Exception as e:
                logger.error(f"Error checking file {path}: {e}")

    def _check_file(self, path: Path) -> None:
        """Check a single file for new content."""
        try:
            # Check for file rotation or replacement
            current_inode = None
            try:
                stat = path.stat(follow_symlinks=self.follow_symlinks)
                current_inode = stat.st_ino
            except OSError:
                pass

            # If inode changed or file was truncated, reset position
            if (current_inode != self._file_inodes.get(path) or
                path.stat().st_size < self._file_positions.get(path, 0)):
                logger.info(f"File rotation detected for {path}, resetting position")
                self._file_positions[path] = 0
                if current_inode is not None:
                    self._file_inodes[path] = current_inode

            # Read new content
            current_size = path.stat().st_size
            last_pos = self._file_positions.get(path, 0)

            if current_size > last_pos:
                # Read new content
                with open(path, 'rb') as f:
                    f.seek(last_pos)
                    new_content = f.read(current_size - last_pos)
                
                # Decode and split into lines
                try:
                    text_content = new_content.decode(self.encoding)
                    lines = text_content.splitlines(keepends=True)
                    
                    # Process each line
                    for line in lines:
                        # Remove trailing newlines for consistency
                        clean_line = line.rstrip('\n\r')
                        try:
                            self.callback(str(path), clean_line)
                        except Exception as e:
                            logger.error(f"Error in callback for {path}: {e}")
                    
                    # Update position
                    self._file_positions[path] = current_size
                except UnicodeDecodeError as e:
                    logger.warning(f"Unicode decode error in {path}: {e}")
                    # Update position anyway to avoid reprocessing
                    self._file_positions[path] = current_size

        except OSError as e:
            logger.debug(f"Could not read {path}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error checking {path}: {e}")

    def is_running(self) -> bool:
        """Check if the watcher is currently running."""
        return self._running

    def get_status(self) -> Dict[str, Any]:
        """Get current status information."""
        return {
            "running": self._running,
            "paths": [str(p) for p in self.paths],
            "file_positions": {str(p): pos for p, pos in self._file_positions.items()},
            "poll_interval": self.poll_interval,
            "encoding": self.encoding,
        }

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
```