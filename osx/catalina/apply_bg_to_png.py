import sqlite3
import pandas as pd
from subprocess import call
from tqdm import tqdm

db_filename = "emoji_bw_calc.db"
with sqlite3.connect(db_filename) as conn:
    bg_sql = "SELECT * FROM images WHERE filename != 'glyph-hiddenglyph.png'"
    bg_df = pd.read_sql(bg_sql, con=conn)

for row_idx, row in tqdm(bg_df.iterrows(), total=bg_df.shape[0]):
    ejp_filename, shade = row.loc[["filename", "furthest_shade"]]
    call([
        "convert", f"png/{ejp_filename}",
        "-background", f"rgb({shade},{shade},{shade})",
        "-flatten", f"bg/{ejp_filename}"
    ])
