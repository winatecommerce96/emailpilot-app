
from google.cloud import firestore

def delete_client():
    """
    Deletes the abc-company client from Firestore.
    """
    db = firestore.Client(project='emailpilot-438321')
    client_ref = db.collection('clients').document('abc-company')
    client_ref.delete()
    print("Successfully deleted the abc-company client from Firestore.")

if __name__ == '__main__':
    delete_client()
