import csv
import sqlite3
from pathlib import Path

db_filename = "matches.db"

with sqlite3.connect(db_filename) as conn:
    c = conn.cursor()
    c.execute("SELECT * FROM top_hash_matches")
    rows = c.fetchall()
    tsv_out = Path(db_filename).stem + ".tsv"
    with open(tsv_out, "w") as tsvfile:
        tsv_writer = csv.writer(tsvfile, delimiter="\t")
        tsv_writer.writerows(rows)
