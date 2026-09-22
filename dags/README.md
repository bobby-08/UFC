# Airflow DAGs

Place Airflow DAG definitions in this directory. DAGs should orchestrate the
reusable functions in `src/ufc_scraper` rather than duplicate scraping,
validation, staging, transformation, or database logic.

The initial deployment target is a local Airflow environment. Once the
pipeline is stable, the project will be containerized with Docker.
