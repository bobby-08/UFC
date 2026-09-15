import polars as pl
from utils.standardisation import standardize_dataframe

def transform_events(
    events: pl.DataFrame,
) -> pl.DataFrame:

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

events_clean = (
    events
    .pipe(
        standardize_dataframe,
        empty_to_null=True,
    )
    .pipe(transform_events)
)