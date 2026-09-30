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

The `postgres-data` volume contains Airflow metadata. Project data and DuckDB
remain under the mounted `data/` directory.
