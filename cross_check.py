import sqlite3
import pandas as pd
from pathlib import Path

result_db = "matches.db"
osx_db = "osx/catalina/osx_emoji_hashes.db"
with sqlite3.connect(result_db) as conn:
    result_sql = "SELECT * FROM top_hash_matches"
    match_df = pd.read_sql(result_sql, con=conn)

with sqlite3.connect(osx_db) as conn:
    result_sql = "SELECT * FROM osx_hashes"
    glyph_df = pd.read_sql(result_sql, con=conn)

cross_df = glyph_df[~glyph_df.filename.isin(match_df.glyph_filename)].dropna()
