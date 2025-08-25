#!/usr/bin/env bash
set -euo pipefail

# Deploy EmailPilot to Cloud Run (build + deploy)

SERVICE_NAME=${SERVICE_NAME:-emailpilot-app}
PROJECT_ID=${PROJECT_ID:-${GOOGLE_CLOUD_PROJECT:-}}
REGION=${REGION:-us-central1}
IMAGE_NAME=${IMAGE_NAME:-gcr.io/$PROJECT_ID/$SERVICE_NAME:latest}

usage() {
  cat <<EOF
Deploy to Cloud Run

Usage: PROJECT_ID=your-project REGION=us-central1 SERVICE_NAME=emailpilot-app \
       ./scripts/deploy_cloud_run.sh [--no-build]

Environment variables:
  PROJECT_ID     GCP project ID (required if GOOGLE_CLOUD_PROJECT not set)
  REGION         Cloud Run region (default: us-central1)
  SERVICE_NAME   Service name (default: emailpilot-app)
  IMAGE_NAME     Full image name (default: gcr.io/
                 $PROJECT_ID/$SERVICE_NAME:latest)

Flags:
  --no-build     Skip Cloud Build (use existing IMAGE_NAME)

Examples:
  PROJECT_ID=emailpilot-438321 ./scripts/deploy_cloud_run.sh
  PROJECT_ID=emailpilot-438321 REGION=us-west1 SERVICE_NAME=emailpilot ./scripts/deploy_cloud_run.sh
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage; exit 0
fi

if [[ -z "$PROJECT_ID" ]]; then
  echo "PROJECT_ID (or GOOGLE_CLOUD_PROJECT) must be set" >&2; exit 1
fi

echo "Project: $PROJECT_ID"
echo "Region:  $REGION"
echo "Service: $SERVICE_NAME"
echo "Image:   $IMAGE_NAME"

if [[ "${1:-}" != "--no-build" ]]; then
  echo "\n==> Building image with Cloud Build"
  gcloud builds submit --project "$PROJECT_ID" --tag "$IMAGE_NAME"
fi

echo "\n==> Deploying to Cloud Run"
gcloud run deploy "$SERVICE_NAME" \
  --project "$PROJECT_ID" \
  --image "$IMAGE_NAME" \
  --platform managed \
  --region "$REGION" \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=$PROJECT_ID" \
  --port 8080

echo "\n✅ Deployed. Service URL:"
gcloud run services describe "$SERVICE_NAME" --project "$PROJECT_ID" --region "$REGION" --format='value(status.url)'

cat <<'NOTE'

When to deploy to Cloud Run
- Backend code changes (Python FastAPI app, routers, auth logic)
- Service changes (Revenue/Performance APIs) that the frontend depends on
- Configuration changes that affect server behavior

When not to deploy
- Pure frontend static tweaks served by your existing CDN without backend impact
- Local-only experiments (use `make dev` and local smoke tests)

Local readiness checklist before deploy
- `make test-smoke` passes
- `/health` returns {"status":"ok"} locally (uvicorn or docker)
- Ops panel shows green for critical components or safe fallbacks
NOTE

