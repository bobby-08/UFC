"""Airflow DAG for the UFC scrape, validation, staging, and transform stages."""

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
    description="Scrape, validate, stage, transform, archive, and persist UFC datasets",
    default_args=default_args,
    schedule=None,
    catchup=False,
    max_active_runs=1,
    tags=["ufc", "scraping"],
    params={
        "backfill": Param(
            True,
            type="boolean",
            title="Historical backfill",
            description="Download all completed events from 2000-01-01 onward on the initial run.",
        )
    },
) as dag:
    restore_blob_data = BashOperator(
        task_id="restore_blob_data",
        bash_command=_script_command("blob_data_sync.py", "restore"),
        cwd=str(PROJECT_ROOT),
        env=_pipeline_env(),
        append_env=True,
    )

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

    ensure_fighters_input = BashOperator(
        task_id="ensure_fighters_input",
        bash_command=_script_command("ensure_fighters.py"),
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

    validate_events = BashOperator(
        task_id="validate_events",
        bash_command=_script_command("validate_events.py"),
        cwd=str(PROJECT_ROOT),
        env=_pipeline_env(),
        append_env=True,
    )

    validate_fighters = BashOperator(
        task_id="validate_fighters",
        bash_command=_script_command("validate_fighters.py"),
        cwd=str(PROJECT_ROOT),
        env=_pipeline_env(),
        append_env=True,
    )

    validate_fight_summary = BashOperator(
        task_id="validate_fight_summary",
        bash_command=_script_command("validate_fight_summary.py"),
        cwd=str(PROJECT_ROOT),
        env=_pipeline_env(),
        append_env=True,
    )

    validate_fight_details = BashOperator(
        task_id="validate_fight_details",
        bash_command=_script_command("validate_fight_details.py"),
        cwd=str(PROJECT_ROOT),
        env=_pipeline_env(),
        append_env=True,
    )

    stage_events = BashOperator(
        task_id="stage_events",
        bash_command=_script_command("stage_raw.py", "events"),
        cwd=str(PROJECT_ROOT),
        env=_pipeline_env(),
        append_env=True,
    )

    stage_fighters = BashOperator(
        task_id="stage_fighters",
        bash_command=_script_command("stage_raw.py", "fighters"),
        cwd=str(PROJECT_ROOT),
        env=_pipeline_env(),
        append_env=True,
    )

    stage_fight_summary = BashOperator(
        task_id="stage_fight_summary",
        bash_command=_script_command("stage_raw.py", "fight_summary"),
        cwd=str(PROJECT_ROOT),
        env=_pipeline_env(),
        append_env=True,
    )

    stage_fight_details = BashOperator(
        task_id="stage_fight_details",
        bash_command=_script_command("stage_raw.py", "fight_details"),
        cwd=str(PROJECT_ROOT),
        env=_pipeline_env(),
        append_env=True,
    )

    transform = BashOperator(
        task_id="transform",
        bash_command=_script_command("transform_data.py"),
        cwd=str(PROJECT_ROOT),
        env=_pipeline_env(),
        append_env=True,
    )

    archive_raw = BashOperator(
        task_id="archive_raw",
        bash_command=_script_command("archive_raw.py"),
        cwd=str(PROJECT_ROOT),
        env=_pipeline_env(),
        append_env=True,
    )

    processed_data_quality = BashOperator(
        task_id="processed_data_quality",
        bash_command=_script_command("quality_processed.py"),
        cwd=str(PROJECT_ROOT),
        env=_pipeline_env(),
        append_env=True,
    )

    duckdb_load = BashOperator(
        task_id="duckdb_load",
        bash_command=_script_command("load_transformed.py"),
        cwd=str(PROJECT_ROOT),
        env=_pipeline_env(),
        append_env=True,
    )

    database_quality = BashOperator(
        task_id="database_quality",
        bash_command=_script_command("quality_database.py"),
        cwd=str(PROJECT_ROOT),
        env=_pipeline_env(),
        append_env=True,
    )

    delete_staging_files = BashOperator(
        task_id="delete_staging_files",
        bash_command=_script_command("cleanup_staging.py"),
        cwd=str(PROJECT_ROOT),
        env=_pipeline_env(),
        append_env=True,
    )

    run_complete = BashOperator(
        task_id="run_complete",
        bash_command=_script_command("run_complete.py"),
        cwd=str(PROJECT_ROOT),
        env=_pipeline_env(),
        append_env=True,
    )

    publish_blob_data = BashOperator(
        task_id="publish_blob_data",
        bash_command=_script_command("blob_data_sync.py", "publish"),
        cwd=str(PROJECT_ROOT),
        env=_pipeline_env(),
        append_env=True,
        trigger_rule="all_done",
    )

    # Fight pages are discovered from the event files produced by scrape_events.
    scrape_events >> scrape_event_fights

    restore_blob_data >> scrape_events
    restore_blob_data >> ensure_fighters_input >> validate_fighters

    scrape_events >> validate_events
    scrape_event_fights >> validate_fight_summary
    scrape_event_fights >> validate_fight_details

    validate_events >> stage_events >> transform
    validate_fighters >> stage_fighters >> transform
    validate_fight_summary >> stage_fight_summary >> transform
    validate_fight_details >> stage_fight_details >> transform
    # Processed quality compares transformed outputs to staging, so cleanup
    # runs only after those checks pass and before the DuckDB load.
    transform >> archive_raw >> processed_data_quality
    processed_data_quality >> delete_staging_files >> duckdb_load
    duckdb_load >> database_quality >> run_complete
    run_complete >> publish_blob_data
