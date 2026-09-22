import polars as pl
from ..utils.standardisation import standardize_dataframe
from ._common import read_staging, schema_values, write_transformation

_SCHEMA = schema_values("totals.toml")
TOTALS_VALUE_CATEGORIES = _SCHEMA["TOTALS_VALUE_CATEGORIES"]
TOTALS_PCT_CATEGORIES = _SCHEMA["TOTALS_PCT_CATEGORIES"]
TOTALS_INTEGER_CATEGORIES = _SCHEMA["TOTALS_INTEGER_CATEGORIES"]
FIGHTERS = _SCHEMA["FIGHTERS"]
BASE_COLS = _SCHEMA["BASE_COLS"]

def transform_totals(totals: pl.DataFrame | str | None = None) -> pl.DataFrame:
    if totals is None:
        totals = read_staging("totals")
    elif not isinstance(totals, pl.DataFrame):
        totals = pl.read_parquet(totals)
    totals = standardize_dataframe(totals, empty_to_null=True)

    exprs_values = []
    exprs_pct = []
    exprs_int = []
    exprs_values_pct = []

    cols_to_drop = (
        [
            f"{category}_fighter{fighter}"
            for category in TOTALS_VALUE_CATEGORIES
            for fighter in FIGHTERS
        ]

        + [
            f"ctrl_fighter{fighter}"
            for fighter in FIGHTERS
        ]
    )
    

    for category in TOTALS_VALUE_CATEGORIES:
        for fighter in FIGHTERS:
            exprs_values_pct.append(
                (
                    pl.when(
                        pl.col(f"{category}_attempted_fighter{fighter}") > 0
                    )
                    .then(
                        100
                        * pl.col(f"{category}_landed_fighter{fighter}")
                        / pl.col(f"{category}_attempted_fighter{fighter}")
                    )
                    .otherwise(0)
                    .round(2)
                    .alias(f"{category}_pct_fighter{fighter}")
                )
            )

    # "X of Y" columns
    for category in TOTALS_VALUE_CATEGORIES:
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

    for category in TOTALS_PCT_CATEGORIES:
        for fighter in FIGHTERS:

            exprs_pct.append(
                pl.col(f"{category}_fighter{fighter}")
                .str.replace("%", "")
                .cast(pl.Float64, strict=False)
                .fill_null(0)
                .alias(f"{category}_fighter{fighter}")
            )

    # integer columns
    for category in TOTALS_INTEGER_CATEGORIES:
        for fighter in FIGHTERS:

            exprs_int.append(
                pl.col(f"{category}_fighter{fighter}")
                .cast(pl.Int64)
                .alias(f"{category}_fighter{fighter}")
            )

    return (
        totals
        .drop("sig_str_pct_fighter1","sig_str_pct_fighter2"
              ,"td_pct_fighter1","td_pct_fighter2")
        .with_columns(*exprs_values)
        .with_columns(*exprs_int)
        .with_columns(*exprs_values_pct)
        .with_columns(

            # round
            pl.col("round_label")
            .str.extract(r"(\d+)")
            .cast(pl.Int64)
            .alias("round"),

            # control time -> seconds
            (
                pl.col("ctrl_fighter1")
                .str.extract(r"(\d+):(\d+)", 1)
                .cast(pl.Int64)
                * 60
                +
                pl.col("ctrl_fighter1")
                .str.extract(r"(\d+):(\d+)", 2)
                .cast(pl.Int64)
            ).alias("ctrl_seconds_fighter1"),

            (
                pl.col("ctrl_fighter2")
                .str.extract(r"(\d+):(\d+)", 1)
                .cast(pl.Int64)
                * 60
                +
                pl.col("ctrl_fighter2")
                .str.extract(r"(\d+):(\d+)", 2)
                .cast(pl.Int64)
            ).alias("ctrl_seconds_fighter2"),

            pl.col("scraped_at")
            .str.to_datetime(format="%Y-%m-%dT%H:%M:%S%z"),

            pl.col("ingested_at")
            .str.to_datetime(format="%Y-%m-%dT%H:%M:%S%z"),

            pl.col("fighter1").str.strip_chars(),
            pl.col("fighter2").str.strip_chars(),
        )
        .drop("round_label")
        .drop(cols_to_drop)
    )


def build_totals_fighter_view(
    df: pl.DataFrame,
    fighter_num: int,
) -> pl.DataFrame:
    
    other = 2 if fighter_num == 1 else 1

    exprs = [
        pl.col(f"fighter{fighter_num}").alias("fighter"),
        pl.col(f"fighter{other}").alias("opponent"),
    ]

    for category in TOTALS_VALUE_CATEGORIES:
        exprs.extend([
            pl.col(f"{category}_landed_fighter{fighter_num}")
            .alias(f"{category}_landed"),

            pl.col(f"{category}_attempted_fighter{fighter_num}")
            .alias(f"{category}_attempted"),
        ])

    for category in TOTALS_PCT_CATEGORIES:
        exprs.append(
            pl.col(f"{category}_fighter{fighter_num}")
            .alias(category)
        )

    for category in TOTALS_INTEGER_CATEGORIES:
        exprs.append(
            pl.col(f"{category}_fighter{fighter_num}")
            .alias(category)
        )

    exprs.append(
        pl.col(f"ctrl_seconds_fighter{fighter_num}")
        .alias("ctrl_seconds")
    )

    return df.select(*BASE_COLS, *exprs)

def create_totals_long(
    totals: pl.DataFrame,
) -> pl.DataFrame:

    fighter1_df = build_totals_fighter_view(totals, 1)
    fighter2_df = build_totals_fighter_view(totals, 2)

    return pl.concat(
        [fighter1_df, fighter2_df],
        how="vertical",
    )

def transform_totals_from_staging(path: str | None = None) -> pl.DataFrame:
    return create_totals_long(transform_totals(read_staging("totals", path)))


def save_transformed_totals(path: str | None = None):
    return write_transformation(transform_totals_from_staging(path), "totals")


__all__ = ["transform_totals", "create_totals_long", "transform_totals_from_staging", "save_transformed_totals"]
