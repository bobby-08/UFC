import polars as pl
from utils.standardisation import standardize_dataframe

def transform_fight_summary(
    fight_summary: pl.DataFrame,
) -> pl.DataFrame:

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

fight_summary_long = (
    fight_summary
    .pipe(standardize_dataframe, empty_to_null=True)
    .pipe(transform_fight_summary)
    .pipe(create_fight_summary_long)
)
