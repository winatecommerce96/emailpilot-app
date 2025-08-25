#!/usr/bin/env python3
"""
Debug Mode Enabler for EmailPilot
Enables comprehensive debugging across all components
"""
import os
import sys
import logging
from pathlib import Path

def enable_debug_mode():
    """Enable debug mode for the EmailPilot application"""
    
    print("🔍 Enabling Debug Mode for EmailPilot...")
    print("=" * 60)
    
    # 1. Set environment variables
    debug_vars = {
        "DEBUG": "True",
        "LOG_LEVEL": "DEBUG", 
        "PYTHONDEBUG": "1",
        "WATCHFILES_DEBUG": "True",  # For file watcher
        "EMAILPILOT_DEBUG": "True",  # Custom debug flag
        "FIRESTORE_EMULATOR_HOST": "",  # Clear to use real Firestore
        "UVICORN_LOG_LEVEL": "debug"
    }
    
    for key, value in debug_vars.items():
        os.environ[key] = value
        print(f"✅ Set {key}={value}")
    
    # 2. Configure Python logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('debug.log')
        ]
    )
    
    print("\n📝 Debug Configuration:")
    print("  - Console output: ENABLED (stdout)")
    print("  - File logging: debug.log")
    print("  - Log level: DEBUG")
    
    # 3. Create debug .env file
    env_path = Path(".env.debug")
    with open(env_path, "w") as f:
        f.write("# Debug Environment Configuration\n")
        for key, value in debug_vars.items():
            f.write(f"{key}={value}\n")
    
    print(f"\n💾 Debug config saved to: {env_path}")
    
    # 4. Show debug commands
    print("\n🚀 Run EmailPilot in Debug Mode:")
    print("-" * 60)
    print("Option 1 - Direct debug:")
    print("  python enable_debug.py && uvicorn main_firestore:app --port 8000 --host localhost --reload --log-level debug")
    print("\nOption 2 - With env file:")
    print("  source .env.debug && uvicorn main_firestore:app --port 8000 --host localhost --reload")
    print("\nOption 3 - Python debug:")
    print("  python -m pdb -c 'import main_firestore; main_firestore.app'")
    
    # 5. Test logging
    logger = logging.getLogger("debug_test")
    logger.debug("Debug mode is active!")
    logger.info("Info level message")
    logger.warning("Warning level message")
    
    print("\n✅ Debug mode is now ACTIVE!")
    print("=" * 60)
    
    return True

def check_debug_status():
    """Check current debug status"""
    print("\n📊 Current Debug Status:")
    print("-" * 40)
    
    debug_indicators = {
        "DEBUG env": os.environ.get("DEBUG", "False"),
        "LOG_LEVEL env": os.environ.get("LOG_LEVEL", "INFO"),
        "Python logging": logging.getLevelName(logging.getLogger().level),
        "PYTHONDEBUG": os.environ.get("PYTHONDEBUG", "0"),
        "EMAILPILOT_DEBUG": os.environ.get("EMAILPILOT_DEBUG", "False")
    }
    
    for key, value in debug_indicators.items():
        status = "🟢" if value in ["True", "DEBUG", "1"] else "🔴"
        print(f"{status} {key}: {value}")
    
    # Check for debug files
    debug_files = [".env.debug", "debug.log", "logs/emailpilot_app.log"]
    print("\n📁 Debug Files:")
    for file in debug_files:
        exists = "✅" if Path(file).exists() else "❌"
        print(f"{exists} {file}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="EmailPilot Debug Mode Manager")
    parser.add_argument("--check", action="store_true", help="Check debug status")
    parser.add_argument("--disable", action="store_true", help="Disable debug mode")
    
    args = parser.parse_args()
    
    if args.check:
        check_debug_status()
    elif args.disable:
        print("🔴 Disabling debug mode...")
        os.environ["DEBUG"] = "False"
        os.environ["LOG_LEVEL"] = "INFO"
        print("✅ Debug mode disabled")
    else:
        enable_debug_mode()
        
        # Import and run the app in debug mode if requested
        if "--run" in sys.argv:
            print("\n🚀 Starting EmailPilot in debug mode...")
            import uvicorn
            uvicorn.run(
                "main_firestore:app",
                host="localhost",
                port=8000,
                reload=True,
                log_level="debug"
            )