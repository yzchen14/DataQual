import os
import time
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import hashlib
import logging
from pathlib import Path

# Load configuration
CONFIG_FILE = 'config.json'

def load_config():
    """Load configuration from JSON file"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load config: {str(e)}")
        raise

# Load and configure logging
config = load_config()
logging.basicConfig(
    level=config['logging']['level'],
    format=config['logging']['format']
)

# Store config globally for easy access
global_config = config

class MockFTPSync:
    def __init__(self, local_path, remote_path):
        self.local_path = Path(local_path)
        self.remote_path = remote_path
        self.operations = []  # Store operations for testing
        self.connect_ftp()

    def connect_ftp(self):
        """Mock FTP connection"""
        logging.info("Mock FTP connection established")

    def upload_file(self, local_file):
        """Mock file upload"""
        # Convert string path to Path object if needed
        if isinstance(local_file, str):
            local_file = Path(local_file)
        remote_file = str(local_file.relative_to(self.local_path))
        self.operations.append({
            'type': 'upload',
            'local': str(local_file),  # Store as string for consistency
            'remote': remote_file
        })
        logging.info(f"Mock uploaded: {local_file}")

    def delete_file(self, remote_file):
        """Mock file deletion"""
        # Convert string path to Path object if needed
        if isinstance(remote_file, str):
            remote_file = Path(remote_file)
        remote_file = str(remote_file.relative_to(self.local_path))
        self.operations.append({
            'type': 'delete',
            'remote': remote_file
        })
        logging.info(f"Mock deleted: {remote_file}")

    def create_remote_directory(self, remote_dir):
        """Mock directory creation"""
        # Convert string path to Path object if needed
        if isinstance(remote_dir, str):
            remote_dir = Path(remote_dir)
        remote_dir = str(remote_dir.relative_to(self.local_path))
        self.operations.append({
            'type': 'create_dir',
            'remote': remote_dir
        })
        logging.info(f"Mock created directory: {remote_dir}")

    def delete_file(self, remote_file):
        """Mock file deletion"""
        self.operations.append({
            'type': 'delete',
            'remote': remote_file
        })
        logging.info(f"Mock deleted: {remote_file}")

    def create_remote_directory(self, remote_dir):
        """Mock directory creation"""
        self.operations.append({
            'type': 'create_dir',
            'remote': remote_dir
        })
        logging.info(f"Mock created directory: {remote_dir}")

    def get_operations(self):
        """Get all recorded operations"""
        return self.operations

    def clear_operations(self):
        """Clear recorded operations"""
        self.operations = []

class SyncHandler(FileSystemEventHandler):
    def __init__(self, ftp_sync):
        self.ftp_sync = ftp_sync

    def on_created(self, event):
        """Called when a file or directory is created"""
        if event.is_directory:
            relative_path = str(Path(event.src_path).relative_to(self.ftp_sync.local_path))
            self.ftp_sync.create_remote_directory(relative_path)
        else:
            self.ftp_sync.upload_file(event.src_path)

    def on_modified(self, event):
        """Called when a file is modified"""
        if not event.is_directory:
            self.ftp_sync.upload_file(event.src_path)

    def on_deleted(self, event):
        """Called when a file or directory is deleted"""
        if event.is_directory:
            # Directory deletion is more complex and requires recursive deletion
            pass
        else:
            relative_path = str(Path(event.src_path).relative_to(self.ftp_sync.local_path))
            self.ftp_sync.delete_file(relative_path)

    def on_moved(self, event):
        """Called when a file or directory is moved/renamed"""
        src_relative = str(Path(event.src_path).relative_to(self.ftp_sync.local_path))
        dest_relative = str(Path(event.dest_path).relative_to(self.ftp_sync.local_path))
        
        if event.is_directory:
            # Delete old directory structure
            self.ftp_sync.delete_file(src_relative)
            # Create new directory structure
            self.ftp_sync.create_remote_directory(dest_relative)
        else:
            # Delete old file
            self.ftp_sync.delete_file(src_relative)
            # Upload new file
            self.ftp_sync.upload_file(event.dest_path)

def main():
    # Get configuration from config file
    ftp_config = global_config['ftp']
    local_config = global_config['local']
    
    # Initialize FTP sync
    ftp_sync = FTPSync(
        local_path=local_config['path'],
        remote_path=ftp_config['remote_path']
    )
    
    # Initialize observer
    observer = Observer()
    event_handler = SyncHandler(ftp_sync)
    observer.schedule(
        event_handler,
        local_config['path'],
        recursive=local_config.get('recursive', True)
    )
    
    # Start monitoring
    observer.start()
    logging.info(f"Monitoring started for {local_config['path']}")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logging.info("Monitoring stopped")
    observer.join()

def test_sync_handler():
    """Test the SyncHandler with MockFTPSync"""
    # Create a temporary test directory
    import tempfile
    import shutil
    import time
    
    # Create test files and directories
    with tempfile.TemporaryDirectory() as temp_dir:
        local_path = Path(temp_dir)
        remote_path = '/remote/path'
        
        # Create mock FTP sync
        mock_sync = MockFTPSync(local_path, remote_path)
        handler = SyncHandler(mock_sync)
        
        # Create observer
        observer = Observer()
        observer.schedule(handler, local_path, recursive=True)
        observer.start()
        
        print(f"Monitoring {local_path} for changes...")
        print("Try creating, modifying, moving, or deleting files in this directory.")
        print("Press Ctrl+C to stop monitoring.")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            print("\nMonitoring stopped")
        
        observer.join()

if __name__ == "__main__":
    test_sync_handler()