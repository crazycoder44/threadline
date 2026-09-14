# Microsoft 365 Intelligence Layer

A Python application for building a searchable, auditable history of customer relationships and business transactions from Microsoft 365 data.

The long-term system is designed to copy and understand data from Outlook, OneDrive, and SharePoint, then expose the resulting customer and transaction history through an API. The current checkout implements the first operational slice of that work: a Microsoft Graph metadata crawler and inventory database.

## Project Status

The project is planned as three phases:

1. **Capture and inventory**
   - Discover Microsoft 365 users and SharePoint sites.
   - Create crawl jobs for mailboxes, OneDrive drives, and SharePoint sites.
   - Enumerate email and file metadata through Microsoft Graph.
   - Store the metadata in PostgreSQL.
   - Resume incremental crawls with Microsoft Graph delta links.

2. **Process and understand**
   - Read the copied or inventoried records.
   - Identify customers using internal/external domain rules and commercial-document signals.
   - Link related emails and files into transaction clusters.
   - Store customers, transactions, transaction items, extracted references, and review decisions.

3. **Serve through an API and application**
   - Provide authenticated access to customer and transaction history.
   - Return links to the stored evidence for each transaction.
   - Add application-level search, review, reporting, and audit features.

### What is implemented now

This repository currently implements the metadata-inventory portion of phase 1:

- Microsoft Graph app-only authentication using MSAL and a client secret.
- Tenant discovery for users and SharePoint sites.
- Crawl-job creation and status tracking.
- Mail metadata crawling for Inbox and Sent Items.
- OneDrive metadata crawling.
- SharePoint document-library metadata crawling.
- PostgreSQL persistence for crawl jobs and discovered items.
- Pagination, throttling handling, upsert behavior, and Graph delta-token persistence.
- A capped test slice for one user and one SharePoint site.

This version does **not** download message or file content. It also does not yet implement the processing engine, raw landing-zone storage, OCR, transaction clustering, or an API.

## Architecture

```text
Microsoft 365 / Microsoft Graph
          |
          v
  Discovery and crawl jobs
          |
          v
   Metadata inventory in PostgreSQL
          |
          v
 Future processing layer
 customer detection + transaction linkage
          |
          v
 Future API and application
```

The current crawler is intentionally metadata-only. A discovered item records information such as its Graph ID, URL, subject or filename, owner or sender, timestamps, source, and internal/external classification. The actual body, attachment, or document contents are not read in this phase.

## Repository Layout

```text
.
|-- app/
|   |-- config.py                 Environment configuration
|   |-- db/
|   |   |-- base.py               SQLAlchemy engine, session, and initialization
|   |   |-- models.py             crawl_jobs and items models
|   |-- graph/
|       |-- client.py             MSAL authentication and Graph HTTP client
|       |-- discovery.py          User/site discovery and job upserts
|       |-- domains.py            Internal/external domain classification
|       |-- item_store.py         Metadata item upserts
|       |-- runners/
|           |-- mail_runner.py
|           |-- onedrive_runner.py
|           |-- sharepoint_runner.py
|-- scripts/
|   |-- run_discovery.py          Populate crawl_jobs from tenant discovery
|   |-- run_crawler.py            Run pending and failed jobs
|   |-- run_test_slice.py         Run a capped one-user test
|-- alembic.ini                   Alembic configuration
|-- alembic/
|   |-- env.py                    Alembic model and database wiring
|   |-- versions/
|       |-- 0001_initial_schema.py
|-- requirements.txt
|-- .env.example
|-- meta_crawler_implementation_plan.md
|-- README.md
```

The local `myvenv/` directory is useful for development but is ignored by Git. Create a new environment when setting up another machine.

## Requirements

### Software

- Windows, macOS, or Linux.
- Python 3.10 or a compatible newer Python version.
- PostgreSQL.
- Network access to `graph.microsoft.com`.
- An account with permission to create and administer the required Entra ID application registration.

The development environment included with this project uses Python 3.10 and PowerShell commands are shown below.

### PostgreSQL

Create a database and a user with permission to use it. For a local PostgreSQL installation, the database can be created with `psql`:

```sql
CREATE USER m365_app WITH PASSWORD 'change-this-password';
CREATE DATABASE m365_intel OWNER m365_app;
```

Use a properly secured password in real environments. Alembic owns the schema and creates the tables when you run `alembic upgrade head`. The application entry points do not modify the schema automatically.

### Microsoft Entra ID application

Create an Entra ID app registration configured for **application permissions**, not delegated permissions. Grant admin consent for:

- `User.Read.All`
- `Mail.Read`
- `Files.Read.All`
- `Sites.Read.All`
- `Group.Read.All`

Create a client secret and record its value when it is generated. The current code uses client-secret authentication. Certificate-based authentication is a future hardening direction and is not yet wired into this checkout.

The effective access granted by Microsoft Graph and tenant policy can be narrower than the permission list. In particular, SharePoint access policies, mailbox restrictions, consent state, and tenant configuration can affect what the crawler can enumerate.

## Installation

Clone the repository and change into its root directory:

```powershell
git clone <repository-url>
Set-Location first_project
```

Create and activate a virtual environment:

```powershell
py -3.10 -m venv myvenv
.\myvenv\Scripts\Activate.ps1
```

If PowerShell blocks activation for the current process, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\myvenv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The dependencies currently include:

- `msal==1.38.0` for Microsoft Entra ID authentication.
- `requests==2.34.2` for Microsoft Graph HTTP requests.
- `sqlalchemy==2.0.52` for database access and models.
- `psycopg2-binary==2.9.12` for PostgreSQL connectivity.
- `python-dotenv==1.2.3` for loading `.env` configuration.
- `alembic==1.19.2` for versioned database schema migrations.

## Logging

The application writes operational logs to this structure:

```text
logs/
|-- metacrawler/
|   |-- metacrawler.log
|   |-- jobs/
|       |-- mail_<target>.log
|       |-- onedrive_<target>.log
|       |-- sharepoint_<target>.log
|-- processor/
|-- api/
```

The `processor/` and `api/` directories are created now as placeholders for the later phases. They will receive phase-specific loggers when those components are implemented.

The metacrawler logs discovery events, job starts and completions, periodic item-count progress, Graph throttling retries, test-slice activity, and failures. Successful items are not logged individually by default. Progress is logged every 1,000 items, while retries, failures, and exceptional events include useful individual details.

The main log and per-job logs use rotating files. The main log keeps up to five 10 MB files; each job log keeps up to three 10 MB files. Console output remains enabled for interactive runs. Set `LOG_ROOT` to store logs outside the repository, for example `LOG_ROOT=D:\m365-logs` on Windows.

## Database Migrations

Alembic is the source of truth for the database schema. After creating the empty PostgreSQL database and configuring `.env`, run the migration before running any crawler command:

```powershell
python -m alembic upgrade head
```

This creates the current `crawl_jobs` and `items` tables, their constraints, and the Alembic version-tracking table. If the database is recreated, run the same command again; no application command needs to create the tables.

When the SQLAlchemy models change, create and review a migration, then apply it:

```powershell
python -m alembic revision --autogenerate -m "describe the schema change"
python -m alembic upgrade head
```

Always inspect autogenerated migrations before applying them, especially for renamed columns, data transformations, PostgreSQL enum changes, and destructive operations.

In production, run migrations as a separate one-off container job before starting the scheduled crawler job. The same image supports migration mode:

```powershell
docker run --rm --env-file .env first-project migrate
```

The normal image command does not run migrations; it waits for database connectivity and starts the metacrawler. This prevents every crawler startup from attempting schema changes.

The database wait defaults to 60 attempts with a 5-second pause between attempts, or about 5 minutes total. Override these values with `DB_CONNECT_MAX_ATTEMPTS` and `DB_CONNECT_RETRY_SECONDS` when the deployment needs a different startup window.

## Configuration

Copy the example configuration file:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and provide the following values:

```dotenv
# Microsoft Entra ID app registration
GRAPH_TENANT_ID=your-tenant-id
GRAPH_CLIENT_ID=your-application-client-id
GRAPH_CLIENT_SECRET=your-client-secret

# Comma-separated domains belonging to your organization
INTERNAL_DOMAINS=example.com,example.co.uk

# PostgreSQL SQLAlchemy URL
DATABASE_URL=postgresql+psycopg2://m365_app:change-this-password@localhost:5432/m365_intel
```

### Configuration reference

| Variable | Required | Description |
| --- | --- | --- |
| `GRAPH_TENANT_ID` | Yes | Microsoft Entra tenant ID, usually a GUID or verified tenant domain. |
| `GRAPH_CLIENT_ID` | Yes | Application/client ID of the Entra ID app registration. |
| `GRAPH_CLIENT_SECRET` | Yes | Client secret value for the app registration. |
| `INTERNAL_DOMAINS` | Yes for useful classification | Comma-separated organization email domains. Domains are normalized to lowercase. |
| `DATABASE_URL` | Yes | SQLAlchemy PostgreSQL connection URL. |

Never commit `.env`, client secrets, database passwords, or other credentials. The repository `.gitignore` excludes `.env`, the local virtual environment, and project planning documents containing internal design information.

## Running the Application

Run all commands from the repository root. Using module execution ensures the `app` package resolves correctly.

### 1. Discover crawl targets

```powershell
python -m scripts.run_discovery
```

This command:

1. Calls Microsoft Graph to enumerate `/users`.
2. Calls Microsoft Graph to enumerate SharePoint sites.
3. Creates or reuses one `crawl_jobs` row for each:
   - user mailbox (`mail`)
   - user OneDrive (`onedrive`)
   - SharePoint site (`sharepoint`)

Discovery is safe to run again. Existing jobs are upserted using their source type and account/site ID.

### 2. Run the full metadata crawler

```powershell
python -m scripts.run_crawler
```

The dispatcher selects jobs whose status is `pending` or `error` and runs them one at a time. A failure is printed and the dispatcher continues to the next job. Failed jobs remain available for a later retry.

Run `python -m alembic upgrade head` before discovery, then run discovery before the full crawler unless `crawl_jobs` has already been populated.

### 3. Run it as a scheduled Azure container job

The crawler is a batch process: it performs one discovery-and-crawl run, then exits. It does not need an HTTP endpoint or a permanently running web service. Azure Container Apps Jobs can start this container on a schedule and create a separate execution for each run.

Use two jobs with the same image:

1. A one-off migration job runs the container with the `migrate` argument and must succeed before the crawler job is enabled.
2. A scheduled crawler job runs the default command. Configure its schedule with a cron expression, such as `0 2 * * *` for 02:00 UTC daily.

Each scheduled execution starts a fresh container, waits for Azure Database for PostgreSQL Flexible Server, runs `run_metacrawler.py`, and exits. Azure records the execution status and logs. Configure `DATABASE_URL`, `GRAPH_TENANT_ID`, `GRAPH_CLIENT_ID`, `GRAPH_CLIENT_SECRET`, and `INTERNAL_DOMAINS` as job environment variables or secret references. The database is external to the container.

For Azure PostgreSQL Flexible Server, use a URL similar to:

```text
postgresql+psycopg2://USER:PASSWORD@SERVER.postgres.database.azure.com:5432/DATABASE?sslmode=require
```

### 4. Run a small test slice

Use this before opening the crawler to the whole tenant:

```powershell
python -m scripts.run_test_slice --user someone@example.com --max-items 50
```

Arguments:

| Argument | Required | Description |
| --- | --- | --- |
| `--user` | Yes | User email address or UPN whose mail and OneDrive will be crawled. |
| `--site` | No | SharePoint site ID. If omitted, the first site returned by tenant discovery is selected; if no site is returned, the script falls back to `/sites/root`. |
| `--max-items` | No | Maximum number of items per source. Defaults to `50`. |

To choose a specific site:

```powershell
python -m scripts.run_test_slice `
  --user someone@example.com `
  --site 'your-sharepoint-site-id' `
  --max-items 50
```

The test slice creates jobs for the selected mailbox, OneDrive, and SharePoint site, then crawls each source. It is intentionally non-resumable: it does not save delta cursors and is intended for validation rather than production ingestion.

## Data Model

The current database contains two tables.

### `crawl_jobs`

Tracks one crawl target and its execution state.

Important fields include:

- `source_type`: `mail`, `onedrive`, or `sharepoint`.
- `account_or_site_id`: Graph user ID or SharePoint site ID.
- `delta_token`: the saved Graph delta link or a JSON object containing multiple cursors.
- `status`: `pending`, `running`, `done`, or `error`.
- `last_run_at`: time of the most recent run.
- `last_item_count`: number of items discovered in the most recent run.
- `last_error`: latest failure message, if any.

A unique constraint prevents duplicate jobs for the same source type and account/site ID.

### `items`

Stores one row per discovered email or file. It is metadata-only.

Important fields include:

- `source_type`: `email` or `file`.
- `graph_id`: Microsoft Graph item ID.
- `graph_url`: Graph web URL when supplied.
- `parent_ref`: mailbox user ID, site ID, or drive-related parent reference.
- `sender_or_owner`: sender or creator/owner email when Graph provides it.
- `classification`: `internal` or `external`, based on `INTERNAL_DOMAINS`.
- `subject_or_filename`: email subject or file name.
- `item_type`: Graph item type.
- `created_at` and `modified_at`: source timestamps.
- `discovered_at`: local inventory timestamp.
- `processing_status`: currently initialized as `discovered` for future processing.

A unique constraint on `(source_type, parent_ref, graph_id)` makes repeated discovery an update rather than a duplicate insert.

## Crawl Behavior

### Mail

The mail runner crawls the user's Inbox and Sent Items delta endpoints. It records message metadata but does not read message bodies or download attachments.

### OneDrive

The OneDrive runner uses the user's drive root delta endpoint and skips folder entries. File metadata is stored in `items`.

### SharePoint

The SharePoint runner enumerates the document libraries/drives under a site and crawls each drive's delta endpoint. Folder entries are skipped and file metadata is stored in `items`.

### Pagination and throttling

- Microsoft Graph `@odata.nextLink` pagination is followed automatically.
- HTTP `429` responses honor the `Retry-After` header.
- Throttled requests are retried up to five times.

### Delta and resumability

After a successful full or incremental job, the final Graph `@odata.deltaLink` is stored in `crawl_jobs.delta_token`. A later full-crawler run can use that cursor to request changes rather than starting from the beginning.

Mail and SharePoint jobs can contain multiple cursors, so the stored value may be a JSON object rather than one plain URL.

If a job fails, its previous delta token is retained and its status is set to `error`. Running the dispatcher again retries the job.

## Checking Results

Connect to PostgreSQL and inspect the inventory:

```sql
SELECT source_type, classification, COUNT(*)
FROM items
GROUP BY source_type, classification
ORDER BY source_type, classification;

SELECT source_type, status, COUNT(*)
FROM crawl_jobs
GROUP BY source_type, status
ORDER BY source_type, status;

SELECT source_type, subject_or_filename, sender_or_owner, graph_url
FROM items
ORDER BY discovered_at DESC
LIMIT 20;
```

The test slice prints `Done - check the items table.` after all three selected source jobs complete.

## Troubleshooting

### `ModuleNotFoundError: No module named 'app'`

Run the command from the repository root and use module syntax:

```powershell
python -m scripts.run_discovery
```

Confirm that the intended virtual environment is active or call its interpreter directly:

```powershell
.\myvenv\Scripts\python.exe -m scripts.run_discovery
```

### Database connection errors

Check that:

- PostgreSQL is running.
- The database exists.
- The username and password in `DATABASE_URL` are correct.
- The URL uses the installed driver, normally `postgresql+psycopg2://`.
- The database host and port are reachable.

### Microsoft Graph `401 Unauthorized`

Check the tenant ID, client ID, and client secret. Confirm that the secret value, rather than the secret's identifier, is in `.env`. Also verify that the secret has not expired.

### Microsoft Graph `403 Forbidden`

A `403` generally means the token was accepted but the app is not authorized for that resource. Check that:

- The required **application** permissions were added.
- Admin consent was granted after adding or changing permissions.
- The app registration belongs to the tenant being queried.
- Exchange, SharePoint, or tenant access policies do not restrict the requested resource.
- The endpoint is valid for the resource being tested.

The `/sites` search endpoint can be restricted by tenant configuration or permissions. The test slice also attempts `/sites/root` when site search returns no result.

### No SharePoint sites found

A tenant may use the root SharePoint site, or the app may not be allowed to enumerate sites. Test with an explicit site ID using `--site`, confirm `Sites.Read.All` admin consent, and verify SharePoint access in the tenant.

### Items are not duplicated after rerunning

This is expected. Items are upserted using `(source_type, parent_ref, graph_id)`. A rerun updates matching metadata instead of inserting a second copy.

## Current Limitations

These are known boundaries of the current implementation:

- No message body, attachment, or document-content download.
- No raw landing-zone storage or immutable copy layer yet.
- No OCR or text extraction.
- No customer table or customer-detection pipeline.
- No transaction clustering or extracted-reference persistence.
- No review queue for uncertain matches.
- No API or user-facing application.
- Mail scope is currently Inbox and Sent Items only.
- Jobs run sequentially; there is no worker pool or distributed dispatcher.
- Graph deletions/removals are not yet handled explicitly.
- Network timeouts and general transient network failures do not have dedicated retry handling.
- Graph timestamps may require normalization for all PostgreSQL driver/database configurations.
- Owner extraction can be incomplete when Graph omits `createdBy.user.email`.
- The capped test slice does not persist delta cursors.
   - The database must be migrated explicitly with Alembic before application commands run.
- Storage destination, exclusions, retention, and production deployment decisions remain open.

## Development Notes

The implementation plan for the metadata crawler is maintained in `meta_crawler_implementation_plan.md`. The broader Microsoft 365 intelligence design is maintained separately in `M365_Intelligence_Layer_Development_Flow.docx`. Both planning documents are intentionally ignored by Git in this repository because they may contain internal project information.

When extending this project, preserve the separation between:

1. Microsoft Graph acquisition.
2. Local inventory and storage.
3. Customer and transaction processing.
4. API/application access.

The eventual application should query the project database or processed storage rather than repeatedly querying Microsoft Graph during normal user requests.

## Security Checklist

Before using the crawler against production data:

- Store `.env` outside source control and use a secret manager where possible.
- Use a dedicated Entra ID application with only the permissions required by the approved scope.
- Obtain and document tenant admin consent.
- Restrict PostgreSQL network access and use a strong database password.
- Decide retention, encryption, backup, and deletion policies for copied metadata and future content.
- Add structured logging without writing access tokens or client secrets.
- Replace client-secret authentication with certificate or managed-identity authentication where the deployment environment supports it.
- Add migrations, operational monitoring, and a controlled retry/worker strategy before production use.

## License

No license has been defined for this project yet.
