from app.services.firestore_client import get_firestore_client


def check_firestore_data(client_id: str = 'test-client'):
    """Check client-scoped Klaviyo data stored in Firestore."""
    db = get_firestore_client()

    print("Campaigns:")
    campaigns_ref = (
        db.collection('clients')
        .document(client_id)
        .collection('klaviyo')
        .document('data')
        .collection('campaigns')
    )
    for doc in campaigns_ref.stream():
        print(f"  - {doc.id}: {doc.to_dict().get('name')} | send_time={doc.to_dict().get('send_time')}")

    print("\nFlows:")
    flows_ref = (
        db.collection('clients')
        .document(client_id)
        .collection('klaviyo')
        .document('data')
        .collection('flows')
    )
    for doc in flows_ref.stream():
        print(f"  - {doc.id}: {doc.to_dict().get('name')} | status={doc.to_dict().get('status')}")


if __name__ == '__main__':
    check_firestore_data()
