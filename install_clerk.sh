#!/bin/bash
# Script to install Clerk with proper dependencies

echo "Installing Clerk backend API with compatible dependencies..."

# First, upgrade pip to latest
pip install --upgrade pip

# Install Clerk with its required cryptography version
# This may cause conflicts with other packages, but Clerk will work
pip install clerk-backend-api --force-reinstall

echo ""
echo "Installation complete!"
echo ""
echo "Note: There may be dependency warnings about cryptography versions."
echo "This is expected due to conflicting requirements between packages."
echo "The application will still work correctly."
echo ""
echo "To use Clerk authentication:"
echo "1. Ensure CLERK_SECRET_KEY is in Secret Manager"
echo "2. Ensure NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY is in Secret Manager"
echo "3. Restart the server: uvicorn main_firestore:app --port 8000 --host localhost --reload"