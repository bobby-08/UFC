"""Airflow DAG for the UFC scraping stage.

This DAG currently stops after raw JSON has been scraped. Validation, staging,
transformation, and DuckDB loading will be added as later pipeline stages.
"""

from __future__ import annotations

import shlex
import sys
from pathlib import Path

# try:  # Airflow 3
#     from airflow.sdk import DAG
# except ImportError:  # Airflow 2 compatibility
#     from airflow import DAG

# try:  # Airflow 3's standard provider
#     from airflow.providers.standard.operators.bash import BashOperator
# except ImportError:  # Airflow 2 compatibility
#     from airflow.operators.bash import BashOperator

from airflow.sdk import DAG
from airflow.providers.standard.operators.bash import BashOperator



PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _script_command(script_name: str, *arguments: str) -> str:
    """Build a portable command for an existing project script."""

    command = [sys.executable, f"scripts/{script_name}", *arguments]
    return " ".join(shlex.quote(str(part)) for part in command)


def _pipeline_env() -> dict[str, str]:
    """Provide the source package path to every Bash task."""

    return {
        "PYTHONPATH": str(PROJECT_ROOT / "src"),
        "PYTHONUNBUFFERED": "1",
    }


default_args = {
    "owner": "ufc_data_engineering",
    "retries": 2,
}


with DAG(
    dag_id="ufc_pipeline",
    description="Scrape the latest UFCStats event",
    default_args=default_args,
    schedule=None,
    catchup=False,
    max_active_runs=1,
    tags=["ufc", "scraping", "local"],
) as dag:
    scrape_latest_event = BashOperator(
        task_id="scrape_latest_event",
        bash_command=_script_command("scrape_latest_event.py"),
        cwd=str(PROJECT_ROOT),
        env=_pipeline_env(),
        append_env=True,
    )
