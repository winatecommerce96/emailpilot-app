#!/usr/bin/env python
"""
Migrate legacy Klaviyo API keys from Firestore plaintext to Secret Manager

Usage:
    python scripts/migrate_klaviyo_keys.py [--dry-run]
"""

import sys
import os
import argparse
import logging
from pathlib import Path

# Add app directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.deps.firestore import get_db
from app.services.secret_manager import get_secret_manager
from google.cloud import firestore

# Initialize secret manager service
secret_manager = get_secret_manager()

def upsert_secret(name: str, value: str):
    """Helper function to create or update a secret"""
    return secret_manager.create_secret(name, value, labels={"type": "klaviyo_key"})

def get_secret(name: str):
    """Helper function to get a secret"""
    return secret_manager.get_secret(name)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_client_keys(dry_run: bool = False):
    """Migrate all client Klaviyo keys from plaintext to Secret Manager"""
    
    db = get_db()
    migrated = 0
    skipped = 0
    errors = 0
    
    logger.info("Starting Klaviyo key migration...")
    if dry_run:
        logger.info("DRY RUN - No changes will be made")
    
    # Get all clients
    for snapshot in db.collection("clients").stream():
        client_id = snapshot.id
        data = snapshot.to_dict() or {}
        
        # Check for existing secret name (already migrated)
        if data.get("klaviyo_secret_name"):
            logger.debug(f"Client {client_id}: Already migrated")
            skipped += 1
            continue
        
        # Look for legacy plaintext keys
        legacy_key = data.get("klaviyo_api_key") or data.get("klaviyo_private_key")
        
        if not legacy_key:
            logger.debug(f"Client {client_id}: No key found")
            skipped += 1
            continue
        
        # Generate secret name
        secret_name = f"klaviyo-api-key-{client_id}"
        
        try:
            if dry_run:
                logger.info(f"Would migrate client {client_id} → {secret_name}")
            else:
                # Store in Secret Manager
                upsert_secret(secret_name, legacy_key)
                
                # Update Firestore document
                update_data = {
                    "klaviyo_secret_name": secret_name,
                    "klaviyo_api_key": firestore.DELETE_FIELD,
                    "klaviyo_private_key": firestore.DELETE_FIELD
                }
                
                snapshot.reference.update(update_data)
                logger.info(f"Migrated client {client_id} → {secret_name}")
            
            migrated += 1
            
        except Exception as e:
            logger.error(f"Failed to migrate client {client_id}: {e}")
            errors += 1
    
    # Summary
    logger.info("=" * 60)
    logger.info(f"Migration {'(DRY RUN) ' if dry_run else ''}complete:")
    logger.info(f"  Migrated: {migrated}")
    logger.info(f"  Skipped:  {skipped}")
    logger.info(f"  Errors:   {errors}")
    logger.info(f"  Total:    {migrated + skipped + errors}")
    
    return migrated, skipped, errors

def verify_migration():
    """Verify that all clients have been properly migrated"""
    
    db = get_db()
    verified = 0
    legacy = 0
    no_key = 0
    
    logger.info("Verifying migration status...")
    
    for snapshot in db.collection("clients").stream():
        client_id = snapshot.id
        data = snapshot.to_dict() or {}
        
        # Check for secret manager reference
        secret_name = data.get("klaviyo_secret_name")
        
        # Check for legacy keys
        has_legacy = bool(data.get("klaviyo_api_key") or data.get("klaviyo_private_key"))
        
        if secret_name and not has_legacy:
            # Properly migrated
            try:
                key = get_secret(secret_name)
                if key:
                    logger.debug(f"Client {client_id}: ✓ Verified (secret: {secret_name})")
                    verified += 1
                else:
                    logger.warning(f"Client {client_id}: Secret {secret_name} not found")
                    no_key += 1
            except Exception as e:
                logger.error(f"Client {client_id}: Error accessing secret {secret_name}: {e}")
                no_key += 1
        elif has_legacy:
            logger.warning(f"Client {client_id}: Still has legacy plaintext keys")
            legacy += 1
        else:
            logger.debug(f"Client {client_id}: No Klaviyo key configured")
            no_key += 1
    
    # Summary
    logger.info("=" * 60)
    logger.info("Verification complete:")
    logger.info(f"  Properly migrated: {verified}")
    logger.info(f"  Legacy keys:       {legacy}")
    logger.info(f"  No key:           {no_key}")
    logger.info(f"  Total:            {verified + legacy + no_key}")
    
    if legacy > 0:
        logger.warning(f"⚠️  {legacy} clients still have legacy plaintext keys")
        return False
    
    logger.info("✓ All clients properly migrated")
    return True

def main():
    parser = argparse.ArgumentParser(description="Migrate Klaviyo API keys to Secret Manager")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview migration without making changes"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify migration status without making changes"
    )
    
    args = parser.parse_args()
    
    # Set up environment
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "emailpilot-438321")
    
    if args.verify:
        success = verify_migration()
        sys.exit(0 if success else 1)
    else:
        migrated, skipped, errors = migrate_client_keys(dry_run=args.dry_run)
        
        if args.dry_run:
            logger.info("\nRun without --dry-run to perform actual migration")
        
        sys.exit(0 if errors == 0 else 1)

if __name__ == "__main__":
    main()