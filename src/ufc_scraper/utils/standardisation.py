import polars as pl
def standardize_dataframe(
    df: pl.DataFrame,
    empty_to_null: bool = False,
) -> pl.DataFrame:
    """
    Standardize a Polars DataFrame.

    - Strips whitespace from column names.
    - Strips whitespace from all string values.
    - Removes surrounding double quotes from string values.
    - Optionally converts empty strings to nulls.
    """

    # Clean column names
    df = df.rename(
        {
            col: col.strip()
            for col in df.columns
        }
    )

    string_cols = [
        col
        for col, dtype in df.schema.items()
        if dtype == pl.String
    ]

    exprs = []

    for col in string_cols:
        expr = (
            pl.col(col)
            .str.strip_chars()
            .str.strip_chars('"')
        )

        if empty_to_null:
            expr = (
                pl.when(expr == "")
                .then(None)
                .otherwise(expr)
            )

        exprs.append(expr.alias(col))

    return df.with_columns(*exprs)