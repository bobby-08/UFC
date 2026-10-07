# Local Airflow with Docker

This setup runs Airflow with PostgreSQL metadata storage and LocalExecutor.
The UFC source code, DAGs, scripts, data, and application logs are mounted
from the project directory.

## First run

1. Copy `.env.example` to `.env` and replace `POSTGRES_PASSWORD` and
   `AIRFLOW_JWT_SECRET` with random values. On a Linux VM, set `AIRFLOW_UID`
   to the output of `id -u` so mounted project folders are writable.
2. Ensure Docker Desktop is running in Linux-container mode.
3. From the project root, build the custom image:

```powershell
docker compose build
```

4. Initialize the Airflow metadata database and admin user:

```powershell
docker compose run --rm airflow-init
```

5. Start Airflow:

```powershell
docker compose up -d
```

6. Open http://localhost:8080. The Simple auth manager generates the Airflow
   password on first startup; retrieve it with:

```powershell
docker compose exec airflow-api-server cat /opt/airflow/simple_auth_manager_passwords.json.generated
```

The admin username is set by `AIRFLOW_ADMIN_USERNAME` (default `admin`). The
password is not read from `.env`; Airflow generates and stores it in the API
server container. This auth manager is intended for development and testing,
so do not expose the UI directly to the public internet.

For a VM, the UI port is bound to `127.0.0.1`; connect through an SSH tunnel
instead of opening port 8080 in the Azure network security group.

## Useful commands

```powershell
docker compose ps
docker compose logs -f airflow-scheduler
docker compose logs -f airflow-api-server
docker compose run --rm airflow-scheduler airflow dags list
docker compose down
```

The `postgres-data` volume contains Airflow metadata. In local mode, project
data and DuckDB stay under the mounted `data/` directory.

## Azure Blob data backend

For the Azure VM deployment, set these values in the VM's private `.env` file:

```dotenv
UFC_DATA_BACKEND=azure_blob
AZURE_STORAGE_ACCOUNT_NAME=ufcdatasets
AZURE_STORAGE_CONTAINER=ufc-data
```

The VM must have a system-assigned managed identity with the **Storage Blob
Data Contributor** role on the `ufc-data` container. The application uses that
identity; no storage key or connection string is needed.

With `UFC_DATA_BACKEND=azure_blob`, each DAG run restores existing project data
from Blob to its working directory, runs the existing filesystem-based
pipeline, publishes the data and DuckDB file back to Blob, then removes those
local working copies after upload succeeds. Blob object paths mirror the
project data paths: `raw/`, `archive/raw/`, `processed/`, and `db/`. Staging
files are temporary and are not copied to Blob. Files under `archive/raw/` are
uploaded with the Cool access tier.

VM-local temporary data is required while this pipeline processes files.
Airflow's Postgres metadata volume and application logs remain on the VM; the
project DuckDB file is copied to and restored from Blob between DAG runs.
If publishing fails, the local working files are left in place for recovery.
When `UFC_DATA_BACKEND` is `local` (the default), Blob synchronization is
skipped and data stays in the local `data/` directory.

After pulling these changes on the VM, edit `.env`, then rebuild and restart:

```bash
sudo docker compose up -d --build
```
