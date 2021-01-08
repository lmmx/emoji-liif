import csv
import sqlite3
from pathlib import Path

db_filename = "emoji_bw_calc.db"

with sqlite3.connect(db_filename) as conn:
    c = conn.cursor()
    c.execute("SELECT * FROM images")
    rows = c.fetchall()
    tsv_out = Path(db_filename).stem + ".tsv"
    with open(tsv_out, "w") as tsvfile:
        tsv_writer = csv.writer(tsvfile, delimiter="\t")
        tsv_writer.writerows(rows)
