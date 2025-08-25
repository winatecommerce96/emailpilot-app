#!/usr/bin/env python3
"""
Script to add affinity segments to clients in Firestore for testing
dynamic calendar segments.
"""

from google.cloud import firestore
import os

# Initialize Firestore
db = firestore.Client()

# Sample affinity segments for different clients
client_segments = {
    "Consumer Law Attorneys": ["Legal Newsletter", "Case Updates", "Webinar Invites"],
    "Colorado Hemp Honey": ["CBD Products", "Honey Lovers", "Wellness Tips"],
    "Christopher Bean Coffee": ["Coffee Connoisseurs", "Morning Brew", "Seasonal Blends"],
    "Rogue Creamery": ["Cheese Enthusiasts", "Wine Pairing", "Artisan Products"],
    "Milagro Mushrooms": ["Fungi Lovers", "Health Benefits", "Recipe Ideas"],
    "First Aid Supplies Online": ["Safety Products", "Emergency Prep", "Healthcare Pros"],
    "Vlasic Labs": ["Tech Innovation", "Product Testing", "Early Adopters"],
    "Wheelchair Getaways": ["Accessibility Travel", "Van Rentals", "Vacation Planning"],
    "ABC Company": ["B2B Solutions", "Industry Updates", "Partner Network"]
}

def update_client_segments():
    """Update clients with affinity segments."""
    clients_ref = db.collection('clients')
    
    for client_name, segments in client_segments.items():
        # Find client by name
        query = clients_ref.where('name', '==', client_name).limit(1)
        docs = list(query.get())
        
        if docs:
            doc = docs[0]
            client_id = doc.id
            
            # Update with affinity segments
            clients_ref.document(client_id).update({
                'affinity_segments': segments[:3]  # Store up to 3 segments
            })
            
            print(f"✅ Updated {client_name} with segments: {segments[:3]}")
        else:
            print(f"⚠️  Client '{client_name}' not found")

if __name__ == "__main__":
    print("Updating client affinity segments...")
    update_client_segments()
    print("\nDone! Clients now have affinity segments for dynamic calendar display.")