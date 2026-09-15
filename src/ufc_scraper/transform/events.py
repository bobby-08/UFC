import polars as pl
from ..utils.standardisation import standardize_dataframe
from ._common import read_staging, schema_values, write_transformation

EVENT_COLS = schema_values("events.toml")["EVENT_COLS"]

def transform_events(
    events: pl.DataFrame | str | None = None,
) -> pl.DataFrame:

    if events is None or isinstance(events, (str, bytes)):
        events = read_staging("events", events)
    elif not isinstance(events, pl.DataFrame):
        events = pl.read_parquet(events)
    events = standardize_dataframe(events, empty_to_null=True)

    return (
        events
        .with_columns(

            # Event date
            pl.col("event_date")
            .str.to_date(
                format="%B %d, %Y"
            ),

            # Datetime columns
            pl.col("scraped_at")
            .str.to_datetime(
                format="%Y-%m-%dT%H:%M:%S%z"
            ),

            pl.col("ingested_at")
            .str.to_datetime(
                format="%Y-%m-%dT%H:%M:%S%z"
            ),

            # Clean text
            pl.col("event_id")
            .str.strip_chars(),

            pl.col("event_name")
            .str.strip_chars(),

            pl.col("event_location")
            .str.strip_chars(),
        )
        .select(EVENT_COLS)
    )

def transform_events_from_staging(path: str | None = None) -> pl.DataFrame:
    return transform_events(path)


def save_transformed_events(path: str | None = None):
    return write_transformation(transform_events_from_staging(path), "events")


__all__ = ["transform_events", "transform_events_from_staging", "save_transformed_events"]
