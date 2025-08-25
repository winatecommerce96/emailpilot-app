
import sys
from google.cloud import firestore
from app.services.client_key_resolver import ClientKeyResolver

def compare_secrets():
    """
    Compares the generated secret names with the actual secret names in Secret Manager.
    """
    db = firestore.Client(project='emailpilot-438321')
    key_resolver = ClientKeyResolver()

    print("Generated Secret Names:")
    clients_ref = db.collection('clients')
    docs = list(clients_ref.stream())

    for doc in docs:
        if doc.exists:
            data = doc.to_dict()
            client_name = data.get("name", "Unknown")
            client_id = doc.id
            generated_name = key_resolver.generate_secret_name(client_name, client_id)
            print(f"  - Client: {client_name} (ID: {client_id})")
            print(f"    Generated Name: {generated_name}")

if __name__ == '__main__':
    compare_secrets()
