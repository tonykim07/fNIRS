import pandas as pd

def interleave_mode_blocks(df, mode_col="G0_Emitter"):
    # Create groups based on changes in the mode column
    df["group"] = (df[mode_col] != df[mode_col].shift()).cumsum()

    # Collect each group into a list of DataFrames
    blocks = []
    for _, block_df in df.groupby("group"):
        block_df = block_df.drop(columns="group")
        blocks.append(block_df)

    all_rows = []
    i = 0
    # Process blocks in pairs; discard any leftover block if it exists.
    while i < len(blocks) - 1:
        block1 = blocks[i].reset_index(drop=True)
        block2 = blocks[i + 1].reset_index(drop=True)

        n1, n2 = len(block1), len(block2)
        max_len = max(n1, n2)

        for j in range(max_len):
            # Get row from block1; if out of range, repeat the last row
            row1 = block1.loc[j] if j < n1 else block1.loc[n1 - 1]
            # Get row from block2; if out of range, repeat the last row
            row2 = block2.loc[j] if j < n2 else block2.loc[n2 - 1]

            all_rows.append(row1.copy())
            all_rows.append(row2.copy())

        i += 2

    final_df = pd.DataFrame(all_rows)
    if "group" in final_df.columns:
        final_df.drop(columns="group", inplace=True)
    return final_df

# ------------------ Main ------------------
if __name__ == "__main__":
    # Read CSV file
    df = pd.read_csv("all_groups.csv")

    # 1) Completely ignore the original timestamp by dropping it if it exists.
    if "Time (s)" in df.columns:
        df.drop(columns=["Time (s)"], inplace=True)

    # 2) Filter out rows with any Short/Long reading <200 or >3800.
    reading_cols = [c for c in df.columns if "Short" in c or "Long" in c]
    mask = (df[reading_cols] >= 0).all(axis=1) & (df[reading_cols] <= 4000).all(axis=1)
    df = df[mask].copy()

    # 3) Interleave the blocks based on the mode column.
    final_df = interleave_mode_blocks(df, mode_col="G0_Emitter")

    # 4) Assign new timestamps at a fixed increment (0.001 s in this example)
    increment = 0.001
    final_df.insert(0, "Time (s)", [i * increment for i in range(len(final_df))])

    # 5) Round the new timestamps to avoid floating-point artifacts.
    final_df["Time (s)"] = final_df["Time (s)"].round(3)

    # 6) Write the final DataFrame to CSV
    final_df.to_csv("interleaved_output.csv", index=False)

    # Output the resulting DataFrame.
    print(final_df.head(20))