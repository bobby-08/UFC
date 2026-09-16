# Local Airflow with Docker

This setup runs Airflow with PostgreSQL metadata storage and LocalExecutor.
The UFC source code, DAGs, scripts, data, and application logs are mounted
from the project directory.

## First run

1. Copy `.env.example` to `.env` and change the admin password.
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

6. Open http://localhost:8080 and sign in with the credentials from `.env`.

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
