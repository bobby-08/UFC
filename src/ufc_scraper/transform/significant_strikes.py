import polars as pl

from ..utils.standardisation import standardize_dataframe
from ._common import read_staging, schema_values, write_transformation

_SCHEMA = schema_values("significant_strikes.toml")
CATEGORIES = _SCHEMA["CATEGORIES"]
METRICS = _SCHEMA["METRICS"]
FIGHTERS = _SCHEMA["FIGHTERS"]
BASE_COLS = _SCHEMA["BASE_COLS"]

def transform_significant_strikes(significant_strikes: pl.DataFrame | str | None = None) -> pl.DataFrame:
    if significant_strikes is None:
        significant_strikes = read_staging("significant_strikes")
    elif not isinstance(significant_strikes, pl.DataFrame):
        significant_strikes = pl.read_parquet(significant_strikes)
    significant_strikes = standardize_dataframe(significant_strikes, empty_to_null=True)
    exprs_values = []
    exprs_values_pct = []

    cols_to_drop = [
        f"{category}_fighter{fighter}"
        for category in CATEGORIES
        for fighter in FIGHTERS
    ]

    for category in CATEGORIES:
        for fighter in FIGHTERS:
            exprs_values.extend([
                pl.col(f"{category}_fighter{fighter}")
                .str.extract(r"(\d+) of (\d+)", 1)
                .cast(pl.Int64)
                .alias(f"{category}_landed_fighter{fighter}"),

                pl.col(f"{category}_fighter{fighter}")
                .str.extract(r"(\d+) of (\d+)", 2)
                .cast(pl.Int64)
                .alias(f"{category}_attempted_fighter{fighter}")
            ])

    for category in CATEGORIES:
        for fighter in FIGHTERS:
            exprs_values_pct.append(
                (
                    100
                    * pl.col(f"{category}_landed_fighter{fighter}")
                    / pl.col(f"{category}_attempted_fighter{fighter}")
                )
                .fill_nan(0)
                .fill_null(0)
                .round(2)
                .alias(f"{category}_pct_fighter{fighter}")
            )

    return (
        significant_strikes
        .drop("sig_str_pct_fighter1", "sig_str_pct_fighter2")
        .with_columns(*exprs_values)
        .with_columns(*exprs_values_pct)
        .drop(cols_to_drop)
        .with_columns(
            pl.col("round_label")
            .str.extract(r"(\d+)")
            .cast(pl.Int64)
            .alias("round"),

            pl.col("scraped_at")
            .str.strip_chars('"')
            .str.to_datetime(format="%Y-%m-%dT%H:%M:%S%z"),

            pl.col("ingested_at")
            .str.strip_chars('"')
            .str.to_datetime(format="%Y-%m-%dT%H:%M:%S%z"),

            pl.col("fighter1").str.strip_chars(),
            pl.col("fighter2").str.strip_chars(),
        )
        .drop("round_label")
    )
    
def build_fighter_view(df: pl.DataFrame, fighter_num: int) -> pl.DataFrame:
    other = 2 if fighter_num == 1 else 1

    exprs = [
        pl.col(f"fighter{fighter_num}").alias("fighter"),
        pl.col(f"fighter{other}").alias("opponent"),
    ]

    for category in CATEGORIES:
        for metric in METRICS:
            exprs.append(
                pl.col(f"{category}_{metric}_fighter{fighter_num}")
                .alias(f"{category}_{metric}")
            )

    return df.select(*BASE_COLS, *exprs)

def create_significant_strikes_long(
    significant_strikes: pl.DataFrame,
) -> pl.DataFrame:

    fighter1_df = build_fighter_view(significant_strikes, 1)
    fighter2_df = build_fighter_view(significant_strikes, 2)

    return pl.concat(
        [fighter1_df, fighter2_df],
        how="vertical",
    )
    
def transform_significant_strikes_from_staging(path: str | None = None) -> pl.DataFrame:
    return create_significant_strikes_long(transform_significant_strikes(read_staging("significant_strikes", path)))


def save_transformed_significant_strikes(path: str | None = None):
    return write_transformation(transform_significant_strikes_from_staging(path), "significant_strikes")


__all__ = [
    "transform_significant_strikes", "create_significant_strikes_long",
    "transform_significant_strikes_from_staging", "save_transformed_significant_strikes",
]
