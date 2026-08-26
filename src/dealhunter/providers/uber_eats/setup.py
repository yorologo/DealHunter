import os
import subprocess
from .runtime import USER_DATA_DIR_PATH, ChromiumRuntime

def run_setup():
    print("Starting Uber Eats Session Setup...")
    print("This will open Carbonyl (Terminal browser).")
    print("1. Accept cookies.")
    print("2. Enter your delivery address.")
    print("3. Press Ctrl+C when you see restaurants.")
    
    # Make sure background runtime is dead so it doesn't lock the profile
    rt = ChromiumRuntime()
    rt.stop()
    
    cmd = [
        "carbonyl",
        f"--user-data-dir={USER_DATA_DIR_PATH}",
        "https://www.ubereats.com/"
    ]
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        pass
    print("\nSetup complete. Profile saved.")
