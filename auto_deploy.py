#!/usr/bin/env python3
"""
Auto-deploy script: Watches for file changes and automatically commits/pushes to GitHub.
This triggers automatic redeployment on Streamlit Cloud.
"""
import time
import subprocess
import sys
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class AutoDeployHandler(FileSystemEventHandler):
    def __init__(self, cooldown=10):
        self.cooldown = cooldown
        self.last_push = 0
        self.pending_files = set()
        
    def on_modified(self, event):
        if event.is_directory:
            return
            
        # Ignore git files, cache, and database files
        path = Path(event.src_path)
        ignore_patterns = {'.git', '__pycache__', '.venv', 'tier0.db', '.pyc', '.DS_Store'}
        
        if any(pattern in str(path) for pattern in ignore_patterns):
            return
            
        print(f"📝 Detected change: {path.name}")
        self.pending_files.add(path.name)
        
        # Only push if cooldown period has passed
        current_time = time.time()
        if current_time - self.last_push >= self.cooldown:
            self.deploy()
            
    def deploy(self):
        if not self.pending_files:
            return
            
        print(f"\n🚀 Auto-deploying changes: {', '.join(self.pending_files)}")
        
        try:
            # Git add all changes
            subprocess.run(['git', 'add', '.'], check=True)
            
            # Commit with automatic message
            file_list = ', '.join(list(self.pending_files)[:3])
            if len(self.pending_files) > 3:
                file_list += f" and {len(self.pending_files) - 3} more"
            commit_msg = f"Auto-deploy: Updated {file_list}"
            
            result = subprocess.run(['git', 'commit', '-m', commit_msg], 
                                  capture_output=True, text=True)
            
            # Only push if there were actual changes to commit
            if result.returncode == 0:
                subprocess.run(['git', 'push'], check=True)
                print(f"✅ Pushed to GitHub! Streamlit Cloud will redeploy in ~2-3 minutes.\n")
            else:
                print("ℹ️  No new changes to commit.\n")
                
            self.pending_files.clear()
            self.last_push = time.time()
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Error during deploy: {e}\n")

def main():
    print("🔍 Auto-Deploy Watcher Started")
    print("=" * 50)
    print("Watching for file changes...")
    print("Changes will auto-commit and push to GitHub every 10 seconds")
    print("Press Ctrl+C to stop\n")
    
    # Check if we're in a git repo
    try:
        subprocess.run(['git', 'status'], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        print("❌ Error: Not in a git repository!")
        sys.exit(1)
    
    # Set up file watcher
    event_handler = AutoDeployHandler(cooldown=10)
    observer = Observer()
    observer.schedule(event_handler, '.', recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n👋 Stopping auto-deploy watcher...")
        observer.stop()
    
    observer.join()
    print("✅ Auto-deploy stopped.")

if __name__ == "__main__":
    main()
