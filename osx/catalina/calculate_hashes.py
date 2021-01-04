from tqdm import tqdm
from pathlib import Path
import sqlite3
from PIL import Image
from imagehash import average_hash

def hash_emoji(img_fname):
    img = Image.open(img_fname)
    mini_img = img.resize((12,12))
    hash_val = average_hash(mini_img)
    return hash_val

db_filename = "osx_emoji_hashes.db"
png_dir = Path("png")
pngs = [p for p in png_dir.iterdir() if p.is_file() and p.suffix == ".png"]

with sqlite3.connect(db_filename) as conn:
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS osx_hashes
    (filename tinytext, codepoint_part varchar(32), hash varchar(16),
    Constraint pk_fn Primary key(filename))
    """)

for png in tqdm(pngs):
    codepoint_part = png.stem[6:] # remove "glyph-" prefix and ".png" suffix
    hash_hexstr = str(hash_emoji(png))
    with sqlite3.connect(db_filename) as conn:
        c = conn.cursor()
        values_tuple = (png.name, codepoint_part, hash_hexstr)
        c.execute("INSERT INTO osx_hashes VALUES (?,?,?)", values_tuple)
        conn.commit()
