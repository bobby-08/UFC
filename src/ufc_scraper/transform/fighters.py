import polars as pl
from utils.standardisation import standardize_dataframe

def transform_fighters(
    fighters: pl.DataFrame,
) -> pl.DataFrame:

    return (
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
        .select(FIGHTER_COLS)
    )
    
fighters_clean = (
    fighters
    .pipe(
        standardize_dataframe,
        empty_to_null=True,
    )
    .pipe(transform_fighters)
)