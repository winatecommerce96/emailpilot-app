# Deploying and Running the Klaviyo Data Sync on Google Cloud

This document provides instructions for deploying and running the Klaviyo data sync service on Google Cloud.

## Prerequisites

1.  **Google Cloud SDK:** Make sure you have the `gcloud` command-line tool installed and configured.
2.  **Project and Permissions:** You need a Google Cloud project with the following APIs enabled:
    *   Cloud Run API
    *   Cloud Build API
    *   Cloud Scheduler API
    *   Secret Manager API
    *   Firestore API

    You also need a service account with the following roles:
    *   Cloud Run Admin
    *   Cloud Build Editor
    *   Cloud Scheduler Admin
    *   Secret Manager Secret Accessor
    *   Cloud Datastore User

## Deployment

1.  **Build and Deploy the Service:**

    You can deploy the application to Cloud Run using the existing `cloudbuild.yaml` file. This will build the Docker image and deploy it as a Cloud Run service.

    ```bash
    gcloud builds submit --config cloudbuild.yaml .
    ```

2.  **Create a Cloud Scheduler Job for Daily Sync:**

    To run the daily sync automatically, you can create a Cloud Scheduler job that sends a `POST` request to the `/api/admin/klaviyo/sync` endpoint.

    ```bash
    gcloud scheduler jobs create http daily-klaviyo-sync \
        --schedule="0 2 * * *" \
        --uri="$(gcloud run services describe emailpilot-app --platform managed --region us-central1 --format 'value(status.url)')/api/admin/klaviyo/sync" \
        --http-method=POST \
        --time-zone="America/New_York"
    ```

    This will create a job that runs every day at 2:00 AM New York time.

## Manual Sync and Backfill

You can also trigger the sync and backfill manually through the Admin UI. The following sections describe how to add the necessary buttons to the UI.

### Admin UI Buttons

To add the manual sync and backfill buttons to the Admin UI, you need to modify the `admin.html` file. Here's the HTML and JavaScript code you'll need to add.

**HTML:**

```html
<div class="bg-white p-4 rounded-lg shadow-md">
    <h2 class="text-lg font-semibold mb-4">Klaviyo Data Sync</h2>
    <div class="flex space-x-4">
        <button id="run-daily-sync" class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
            Run Daily Sync
        </button>
        <div>
            <input type="text" id="backfill-client-id" placeholder="Client ID for Backfill" class="border border-gray-300 rounded-l-md py-2 px-4">
            <button id="run-backfill" class="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded-r-md">
                Run Backfill
            </button>
        </div>
    </div>
</div>
```

**JavaScript:**

```javascript
document.getElementById('run-daily-sync').addEventListener('click', () => {
    fetch('/api/admin/klaviyo/sync', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        alert(data.message);
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while triggering the daily sync.');
    });
});

document.getElementById('run-backfill').addEventListener('click', () => {
    const clientId = document.getElementById('backfill-client-id').value;
    if (!clientId) {
        alert('Please enter a client ID for the backfill.');
        return;
    }

    fetch(`/api/admin/klaviyo/backfill/${clientId}` , {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        alert(data.message);
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while triggering the backfill.');
    });
});
```

**Instructions:**

1.  Open the `admin.html` file in your project.
2.  Find a suitable location in the `<body>` of the file to add the HTML code. A good place would be within the main content area of the admin panel.
3.  Add the JavaScript code to a `<script>` tag at the bottom of the `<body>` of the `admin.html` file, or include it in your existing JavaScript files.

Once you've added the code, the Admin UI will have a new section for triggering the Klaviyo data sync and backfill.
