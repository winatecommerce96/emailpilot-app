
from google.cloud import firestore

def add_test_client():
    """
    Adds a test client to the clients collection in Firestore.
    """
    db = firestore.Client(project='emailpilot-438321')
    client_ref = db.collection('clients').document('test-client')
    client_ref.set({
        'name': 'Test Client',
        'klaviyo_secret_name': 'klaviyo-api-key-test-client'
    })
    print("Successfully added the test client to Firestore.")

if __name__ == '__main__':
    add_test_client()
