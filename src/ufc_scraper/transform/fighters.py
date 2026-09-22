from datetime import datetime, timezone

import polars as pl
from ..utils.standardisation import standardize_dataframe
from ._common import read_staging, schema_values, write_transformation

_SCHEMA = schema_values("fighters.toml")
FIGHTER_COLS = _SCHEMA["FIGHTER_COLS"]
FIGHTER_STATS_COLS = _SCHEMA["FIGHTER_STATS_COLS"]

def transform_fighters(
    fighters: pl.DataFrame | str | None = None,
) -> pl.DataFrame:

    if fighters is None:
        fighters = read_staging("fighters")
    elif not isinstance(fighters, pl.DataFrame):
        fighters = pl.read_parquet(fighters)
    fighters = standardize_dataframe(fighters, empty_to_null=True)

    transformed = (
        fighters
        .with_columns(

            # Fighter name
            pl.concat_str(
                [
                    pl.col("first_name"),
                    pl.col("last_name"),
                ],
                separator=" ",
            )
            .str.strip_chars()
            .alias("fighter_name"),

            # Height: 5' 11" -> 71
            
            (
                pl.col("height")
                .str.extract(r"(\d+)'", 1)
                .cast(pl.Int64)
                * 12
                +
                pl.col("height")
                .str.extract(r"'\s*(\d+)", 1)
                .cast(pl.Float64)
            ).alias("height_inches"),

            # Weight: 155 lbs. -> 155
            pl.col("weight")
            .str.extract(r"(\d+)", 1)
            .cast(pl.Float64, strict=False)
            .alias("weight_lbs"),

            # Reach: 66.0" -> 66.0
            pl.col("reach")
            .str.extract(r"(\d+(?:\.\d+)?)", 1)
            .cast(pl.Float64, strict=False)
            .alias("reach_inches"),

            # Record columns
            pl.col("wins")
            .cast(pl.Int64, strict=False),

            pl.col("losses")
            .cast(pl.Int64, strict=False),

            pl.col("draws")
            .cast(pl.Int64, strict=False),

            # Belt flag
            pl.col("belt")
            .str.len_chars()
            .gt(0)
            .alias("belt"),

            # Clean text columns
            pl.col("fighter_id")
            .str.strip_chars(),

            pl.col("nickname")
            .str.strip_chars(),

            pl.col("stance")
            .str.strip_chars(),

            # Datetime columns
            pl.col("scraped_at")
            .str.to_datetime(
                format="%Y-%m-%dT%H:%M:%S%z"
            ),

            pl.col("ingested_at")
            .str.to_datetime(
                format="%Y-%m-%dT%H:%M:%S%z"
            ),
        )
    )

    return transformed.select(FIGHTER_COLS)


def transform_fighter_stats(fighters: pl.DataFrame | str | None = None) -> pl.DataFrame:
    """Return cumulative fighter records separately from descriptive attributes."""
    if fighters is None:
        fighters = read_staging("fighters")
    elif not isinstance(fighters, pl.DataFrame):
        fighters = pl.read_parquet(fighters)

    # Rebuild the derived cumulative columns from the standardized input because
    # transform_fighters intentionally returns only descriptive columns.
    source = standardize_dataframe(fighters, empty_to_null=True)
    return (
        source
        .with_columns(
            pl.col("wins").cast(pl.Int64, strict=False),
            pl.col("losses").cast(pl.Int64, strict=False),
            pl.col("draws").cast(pl.Int64, strict=False),
            pl.col("belt").str.len_chars().gt(0).alias("belt"),
            pl.col("fighter_id").str.strip_chars(),
            pl.col("scraped_at").str.to_datetime(format="%Y-%m-%dT%H:%M:%S%z"),
            pl.col("ingested_at").str.to_datetime(format="%Y-%m-%dT%H:%M:%S%z"),
        )
        .select(FIGHTER_STATS_COLS)
    )

def transform_fighters_from_staging(path: str | None = None) -> pl.DataFrame:
    return transform_fighters(read_staging("fighters", path))


def transform_fighter_outputs_from_staging(path: str | None = None) -> dict[str, pl.DataFrame]:
    fighters = read_staging("fighters", path)
    return {
        "fighters": transform_fighters(fighters),
        "fighter_stats": transform_fighter_stats(fighters),
    }


def save_transformed_fighters(path: str | None = None):
    outputs = transform_fighter_outputs_from_staging(path)
    transformed_at = datetime.now(timezone.utc)
    return {
        name: write_transformation(frame, name, transformed_at=transformed_at)
        for name, frame in outputs.items()
    }


__all__ = [
    "transform_fighters", "transform_fighter_stats", "transform_fighters_from_staging",
    "transform_fighter_outputs_from_staging", "save_transformed_fighters",
]
