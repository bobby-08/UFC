import polars as pl
from ..utils.standardisation import standardize_dataframe
from ._common import read_staging, schema_values, write_transformation

_SCHEMA = schema_values("summary.toml")
FIGHT_SUMMARY_COLS = _SCHEMA["FIGHT_SUMMARY_COLS"]
FIGHT_SUMMARY_BASE_COLS = _SCHEMA["FIGHT_SUMMARY_BASE_COLS"]

def transform_fight_summary(
    fight_summary: pl.DataFrame | str | None = None,
) -> pl.DataFrame:

    if fight_summary is None:
        fight_summary = read_staging("fight_summary")
    elif not isinstance(fight_summary, pl.DataFrame):
        fight_summary = pl.read_parquet(fight_summary)
    fight_summary = standardize_dataframe(fight_summary, empty_to_null=True)

    return (
        fight_summary
        .with_columns(

            pl.col("round")
            .cast(pl.Int64),

            (
                pl.col("time")
                .str.extract(r"(\d+):(\d+)", 1)
                .cast(pl.Int64)
                * 60
                +
                pl.col("time")
                .str.extract(r"(\d+):(\d+)", 2)
                .cast(pl.Int64)
            ).alias("time_seconds"),

            pl.col("scraped_at")
            .str.to_datetime(format="%Y-%m-%dT%H:%M:%S%z"),

            pl.col("ingested_at")
            .str.to_datetime(format="%Y-%m-%dT%H:%M:%S%z"),

            pl.col("fighter_1").str.strip_chars(),
            pl.col("fighter_2").str.strip_chars(),

            pl.col("fighter_1_nickname")
            .str.strip_chars('"'),

            pl.col("fighter_2_nickname")
            .str.strip_chars('"'),
        )
    )

def build_fight_summary_fighter_view(
    df: pl.DataFrame,
    fighter_num: int,
) -> pl.DataFrame:

    other = 2 if fighter_num == 1 else 1

    exprs = [
        pl.col(f"fighter_{fighter_num}").alias("fighter"),
        pl.col(f"fighter_{other}").alias("opponent"),

        pl.col(f"fighter_{fighter_num}_result")
        .alias("fighter_result"),

        pl.col(f"fighter_{fighter_num}_nickname")
        .alias("nickname"),
    ]

    return df.select(
        *FIGHT_SUMMARY_BASE_COLS,
        "winner",
        "loser",
        *exprs,
    )

def create_fight_summary_long(
    fight_summary: pl.DataFrame,
) -> pl.DataFrame:

    fighter1_df = build_fight_summary_fighter_view(
        fight_summary,
        1,
    )

    fighter2_df = build_fight_summary_fighter_view(
        fight_summary,
        2,
    )

    return pl.concat(
        [fighter1_df, fighter2_df],
        how="vertical",
    )

def transform_fight_summary_from_staging(path: str | None = None) -> pl.DataFrame:
    return create_fight_summary_long(transform_fight_summary(read_staging("fight_summary", path)))


def save_transformed_fight_summary(path: str | None = None):
    return write_transformation(transform_fight_summary_from_staging(path), "fight_summary")


__all__ = ["transform_fight_summary", "create_fight_summary_long", "transform_fight_summary_from_staging", "save_transformed_fight_summary"]
