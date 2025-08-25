
from google.cloud import firestore

def update_secret_name():
    """
    Updates the klaviyo_secret_name for the abc-company client.
    """
    db = firestore.Client(project='emailpilot-438321')
    client_ref = db.collection('clients').document('abc-company')
    client_ref.update({
        'klaviyo_secret_name': 'klaviyo-api-key-abc-company'
    })
    print("Successfully updated the klaviyo_secret_name for abc-company to klaviyo-api-key-abc-company.")

if __name__ == '__main__':
    update_secret_name()
