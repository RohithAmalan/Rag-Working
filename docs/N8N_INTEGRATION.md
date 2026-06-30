# n8n Integration Guide

n8n is the workflow layer for the RAG stack. In this project it is used to accept webhook-driven actions, call the FastAPI backend, and write audit/report records into MongoDB.

This guide reflects the current setup in the repository and the current runtime behavior that was verified locally.

---

## Current Status

### Verified working now

- n8n is running on `http://localhost:5678`
- `GET /healthz` returns `{"status":"ok"}`
- [x] **01 - Auto Document Ingestion**: Webhook-based file upload pipeline
- [x] **02 - Scheduled RAG Report**: Daily summary of RAG usage and queries
- [x] **03 - Error Alert Webhook**: Slack/Teams notification for system errors
- [x] **04 - Google Drive Knowledge Sync**: Daily cron job to sync modified documents from Google Drive into the RAG vector DB

The container startup auto-publishes workflows 1, 2, and 3 through the n8n CLI so ingest, scheduled report, and alert flows stay active after restart

### Present in repo and active by default

- No core workflow is intentionally left inactive in the default demo setup

### Important setup notes

- The current Compose setup disables n8n user management with `N8N_USER_MANAGEMENT_DISABLED=true`
- That means the local demo setup may open directly without an n8n login screen
- Workflow JSON files are stored in `n8n/workflows/`, but they are not automatically mounted into the n8n container as importable runtime files
- In practice, the running workflows come from what has already been imported into the persistent `n8n_data` volume

---

## Quick Start

### 1. Start n8n

```bash
docker-compose up -d n8n
```

### 2. Open the UI

Open `http://localhost:5678`

If user management remains disabled, the UI opens directly. If you later enable n8n auth, add those credentials to this guide after configuring them in Compose.

If n8n is already running, restart that container once so the startup publish command runs.

### 3. Check health

```bash
curl http://localhost:5678/healthz
```

Expected response:

```json
{"status":"ok"}
```

### 4. Configure MongoDB credential in n8n if needed

Some workflows expect a MongoDB credential named `RAG MongoDB`.

Use these values:

- Connection string: `mongodb://admin:password123@mongodb:27017`
- Database: `rag_db`
- Credential name: `RAG MongoDB`

---

## Workflow Files

Repo workflow sources are here:

- [n8n/workflows/01_auto_document_ingestion.json](/Users/rohith/RAG/n8n/workflows/01_auto_document_ingestion.json)
- [n8n/workflows/02_scheduled_rag_report.json](/Users/rohith/RAG/n8n/workflows/02_scheduled_rag_report.json)
- [n8n/workflows/03_error_alert_webhook.json](/Users/rohith/RAG/n8n/workflows/03_error_alert_webhook.json)

If you want to load or reload them manually:

1. Open n8n UI
2. Create a new workflow
3. Import from file
4. Select the JSON from `n8n/workflows/`
5. Attach credentials if prompted
6. Activate the workflow toggle

---

## Workflow Reference

### Workflow 1 — Auto Document Ingestion

Source file: [n8n/workflows/01_auto_document_ingestion.json](/Users/rohith/RAG/n8n/workflows/01_auto_document_ingestion.json)

Production webhook:

```text
POST /webhook/ingest-document
```

What it does:

1. Receives a file through an n8n webhook
2. Calls FastAPI `/auth/login` using the configured admin credentials
3. Calls FastAPI `/upload` with the uploaded file
4. Writes a success or error record into MongoDB `audit_events`

Verified result from local runtime:

- A POST to `/webhook/ingest-document` succeeded
- The sample file `test_employees.csv` was added to the backend document list
- A success audit record was written to MongoDB

Trigger command:

```bash
curl -X POST http://localhost:5678/webhook/ingest-document \
    -F "data=@/Users/rohith/RAG/n8n/test_employees.csv"
```

Expected response shape:

```json
{
    "status": "success",
    "event": "document_ingested",
    "processed_files": 1,
    "total_chunks": 10,
    "timestamp": "...",
    "source": "n8n-workflow-01"
}
```

Collections touched:

- `audit_events`

### Workflow 2 — Scheduled RAG Health Report

Source file: [n8n/workflows/02_scheduled_rag_report.json](/Users/rohith/RAG/n8n/workflows/02_scheduled_rag_report.json)

Current state:

- Present in repo
- Published automatically at n8n startup via CLI (`publish:workflow --id=2`)

What the current JSON actually does:

1. Runs on a weekday cron schedule
2. Calls FastAPI `/health`
3. Logs into FastAPI
4. Calls FastAPI `/documents`
5. Writes a summarized record to MongoDB `n8n_daily_reports`

Important note:

- The current workflow JSON does not call `/query`
- If you want a richer demo, that step needs to be added explicitly

How it is automated now:

1. n8n container starts
2. Startup command publishes workflow IDs 1, 2, and 3
3. Workflow 2 stays scheduled without a manual toggle
4. At 9am weekdays (Asia/Kolkata), n8n runs health check, login, documents list, and Mongo report write automatically

Collections touched:

- `n8n_daily_reports`

How to test Workflow 2 now:

1. Restart n8n so the startup publish command runs:

```bash
docker compose up -d --force-recreate n8n
```

2. Confirm n8n is healthy:

```bash
curl http://localhost:5678/healthz
```

3. Run workflow 2 immediately (no need to wait for 9am):

```bash
docker compose exec -T n8n n8n execute --id=2
```

4. Verify a report row was created in MongoDB:

```bash
docker compose exec -T mongodb mongosh "mongodb://admin:password123@localhost:27017/rag_db?authSource=admin" --quiet --eval "db.n8n_daily_reports.find().sort({generated_at:-1}).limit(1).toArray()"
```

Expected test result:

- `execute --id=2` finishes without node failures
- One new document appears in `n8n_daily_reports` with `backend_status`, `total_documents`, `total_chunks`, and `generated_at`

### Workflow 3 — Error Alert And Audit Logger

### Workflow 3 — Error Alert And Audit Logger

Source file: [n8n/workflows/03_error_alert_webhook.json](/Users/rohith/RAG/n8n/workflows/03_error_alert_webhook.json)

Listens for system error webhooks from the RAG backend and formats them into actionable Slack/Teams notifications for the administration team.

### Workflow 4 — Google Drive Knowledge Sync

Source file: [n8n/workflows/04_google_drive_knowledge_sync.json](/Users/rohith/RAG/n8n/workflows/04_google_drive_knowledge_sync.json)

Ensures the vector database is always up-to-date with company documents.
- **Schedule Trigger**: Runs every night at 2:00 AM.
- **Search**: Scans Google Drive for any files modified in the last 24 hours.
- **Ingestion**: Downloads the modified files and `POST`s them to the FastAPI `/upload` endpoint.
- **Notification**: Sends a Slack message summarizing how many files were synced, or alerts if no files were found.

- A direct POST to `/webhook/rag-event` should now be accepted once the n8n container has restarted with the new command

What it is intended to do:

1. Receive application event payloads
2. Enrich them with severity metadata
3. Write all events into `audit_events`
4. Write warnings and critical events into `audit_alerts`

How it works end to end:

1. The backend emits a JSON event when login succeeds, login fails, or upload validation fails
2. The event goes to the n8n webhook at `/webhook/rag-event`
3. Workflow 3 enriches the payload with severity and metadata
4. MongoDB receives the audit row
5. If severity is warning or critical, the workflow also creates an alert row

Collections touched:

- `audit_events`
- `audit_alerts`

---

## Demo Script

This is the cleanest demo path for the current setup because it uses the one workflow that is already proven working.

### Demo goal

Show that n8n can orchestrate a business workflow by receiving a file, calling the RAG backend, and recording the result in MongoDB.

### Demo steps

1. Open `http://localhost:5678`
2. Show that n8n is healthy and accessible
3. Open the active ingestion workflow or the Executions page
4. Trigger the workflow with the sample file:

```bash
curl -X POST http://localhost:5678/webhook/ingest-document \
    -F "data=@/Users/rohith/RAG/n8n/test_employees.csv"
```

5. Show the success response in terminal
6. In n8n, show the execution graph step by step
7. In MongoDB, show the new `audit_events` entry
8. In the RAG app or backend document list, show that `test_employees.csv` now exists as an indexed document

### What to say during the demo

Use this explanation:

1. "n8n is acting as the orchestration layer. It is not storing embeddings itself; it coordinates the flow."
2. "The webhook is the entry point. A file comes in from a user, script, or another system."
3. "n8n authenticates against the FastAPI backend, then hands the file to the RAG upload endpoint."
4. "The backend does the real ingestion work: chunking, embedding, and persistence."
5. "n8n then records an audit trail in MongoDB so we can monitor what happened."
6. "This pattern is useful because it lets us automate business processes around the RAG system without changing core backend logic every time."

### Short version for executives

"A new file arrives, n8n triggers the workflow, the RAG backend ingests it, and we get both searchable data and an audit trail automatically."

---

## Optional Inbox Demo

You can also demo the file-drop flow using the watcher:

Source file: [watch_inbox.py](/Users/rohith/RAG/watch_inbox.py)

Run:

```bash
python watch_inbox.py
```

Then drop a file into:

```text
/Users/rohith/RAG/inbox
```

What happens:

1. The watcher detects the file
2. It POSTs the file to n8n `/webhook/ingest-document`
3. n8n calls the backend upload flow
4. The watcher deletes the file from the inbox after handoff

This is a better visual demo if you want to show automation without using curl.

---

## Service Addresses Inside Docker

These are the internal service URLs used by n8n workflows:

- FastAPI backend: `http://rag-backend:8000`
- MongoDB: `mongodb://admin:password123@mongodb:27017`
- Redis: `redis://redis:6379`
- MinIO: `http://minio:9000`
- Keycloak: `http://keycloak:8080`

---

## Monitoring Checklist

- n8n health: `http://localhost:5678/healthz`
- n8n executions: n8n UI `Executions`
- backend documents: FastAPI `/documents`
- workflow audit trail: MongoDB `audit_events`
- scheduled reports: MongoDB `n8n_daily_reports`
- alerts: MongoDB `audit_alerts`

---

## Should We Upgrade It?

For the immediate demo, no n8n version upgrade is required.

The bigger need is setup hardening, not a feature upgrade:

1. Pin `n8n` to a fixed version instead of `latest`
2. Make repo workflows importable in a repeatable way
3. Activate and verify Workflow 2 and Workflow 3
4. Remove hard-coded backend credentials from workflow JSON
5. Re-enable proper n8n authentication for shared demo or production environments

For today's demo, Workflow 1 is sufficient and already validated.
