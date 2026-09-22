# Logging guide

The project uses the standard-library `logging` package through
`ufc_scraper.logging`.

## Log locations

Each stage writes to its own directory under `logs/`:

```text
logs/
├── scrape/
├── validation/
├── staging/
├── transform/
├── database/
└── pipeline/
```

Files are named with a UTC start timestamp, for example
`logs/transform/transform_20260915T153000Z.log`. Files rotate when they reach
10 MiB. Five backup files are retained by default.

The log directory and levels can be configured for scheduled jobs:

```text
UFC_LOG_LEVEL=INFO
UFC_CONSOLE_LOG_LEVEL=WARNING
UFC_LOG_DIR=D:/path/to/logs
UFC_LOG_MAX_BYTES=10485760
UFC_LOG_BACKUP_COUNT=5
```

## Basic usage

```python
from ufc_scraper.logging import get_logger

LOGGER = get_logger(__name__, stage="transform")
LOGGER.info("Starting dataset=%s", dataset_name)
```

Use parameterized messages rather than f-strings so expensive values are only
formatted when the log level is enabled.

## Timing operations

Use the decorator for functions:

```python
from ufc_scraper.logging import timed

@timed
def transform_dataset():
    ...
```

Use the context manager for a block:

```python
from ufc_scraper.logging import timed_operation

with timed_operation("write processed parquet", logger=LOGGER):
    write_output()
```

Both forms log start, successful completion, elapsed seconds, and exceptions.

## Recommended log levels

* `DEBUG`: row samples, configuration values, SQL/file details, and diagnostic
  information useful during development.
* `INFO`: stage start/end, input and output paths, row counts, run IDs, and
  successful checkpoint events.
* `WARNING`: recoverable data-quality issues, skipped records, missing optional
  fields, retries, and suspicious row-count changes.
* `ERROR`: failed files, validation failures, failed database transactions, and
  exceptions that terminate a stage. Use `LOGGER.exception(...)` inside an
  exception handler to include the traceback.

## Where to log in the pipeline

* Scrape: log source URL, dataset, request/retry events, output path, and row
  count. Log response or parser failures with a traceback.
* Validation: log the file being checked, valid/invalid result, issue counts,
  and each warning/error category.
* Staging: log dataset, number of raw input files, output paths, row counts,
  and metadata-resolution warnings.
* Transformation: log source staging paths, output paths, row counts, schema
  changes, and execution duration.
* Database: log connection path, pipeline run ID, transaction boundaries,
  loaded row counts, checksums, and rollback exceptions.
* Pipeline orchestration: log the overall run ID, stage boundaries, elapsed
  time, final status, and failure traceback.

Avoid secrets, full HTML responses, credentials, and unnecessarily large raw
payloads in logs. Use `LOGGER.debug` for small samples only.
