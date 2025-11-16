#!/usr/bin/env python3
import sys
import signal

def timeout_handler(signum, frame):
    print("TIMEOUT: Import took too long!")
    sys.exit(1)

# Set 15 second timeout
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(15)

try:
    print("Starting import...")
    from main_firestore import app
    print("SUCCESS: Import completed!")
    signal.alarm(0)  # Cancel alarm
except Exception as e:
    print(f"ERROR during import: {e}")
    import traceback
    traceback.print_exc()
    signal.alarm(0)
    sys.exit(1)
