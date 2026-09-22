"""Airflow DAG for the UFC raw scraping stage.

The DAG downloads event metadata and the fight summary and fight-detail
datasets. Fighter metadata is scraped separately because it changes less often.
Validation, staging, transformation, and loading remain separate downstream
stages.
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

from airflow.sdk import DAG, Param
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
    description="Scrape UFCStats events, fight summaries, and fight details",
    default_args=default_args,
    schedule=None,
    catchup=False,
    max_active_runs=1,
    tags=["ufc", "scraping", "local"],
    params={
        "backfill": Param(
            True,
            type="boolean",
            title="Historical backfill",
            description="Download all completed events from 2000-01-01 onward on the initial run.",
        )
    },
) as dag:
    scrape_events = BashOperator(
        task_id="scrape_events",
        bash_command=(
            _script_command("scrape_events.py", "--track-pipeline")
            + " {% if params.backfill %}--backfill-from 2000-01-01{% endif %}"
        ),
        cwd=str(PROJECT_ROOT),
        env=_pipeline_env(),
        append_env=True,
    )

    scrape_event_fights = BashOperator(
        task_id="scrape_event_fights",
        bash_command=_script_command(
            "scrape_event_fights.py", "--all-events", "--track-pipeline"
        ),
        cwd=str(PROJECT_ROOT),
        env=_pipeline_env(),
        append_env=True,
    )

    # Fight pages are discovered from the event files produced by scrape_events.
    scrape_events >> scrape_event_fights
