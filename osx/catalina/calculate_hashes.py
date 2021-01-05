from tqdm import tqdm
from pathlib import Path
import sqlite3
from PIL import Image
from imagehash import average_hash, colorhash, dhash

def hash_emoji(img_fname):
    "Return average and color hashes (lengths 64 and 42 respectively)"
    img = Image.open(img_fname)
    mini_img = img.resize((32,32))
    a = average_hash(mini_img, hash_size=16)
    c = colorhash(mini_img, binbits=12)
    d = dhash(mini_img, hash_size=16)
    return str(a), str(c), str(d)

db_filename = "osx_emoji_hashes.db"
png_dir = Path("png")
pngs = [p for p in png_dir.iterdir() if p.is_file() and p.suffix == ".png"]

with sqlite3.connect(db_filename) as conn:
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS osx_hashes
    (filename tinytext, codepoint_part varchar(32), a_hash varchar(64),
    c_hash varchar(42), d_hash varchar(64), Constraint pk_fn Primary key(filename))
    """)

for png in tqdm(pngs):
    codepoint_part = png.stem[6:] # remove "glyph-" prefix and ".png" suffix
    a_hash, c_hash, d_hash = hash_emoji(png)
    with sqlite3.connect(db_filename) as conn:
        c = conn.cursor()
        values = (png.name, codepoint_part, a_hash, c_hash, d_hash)
        c.execute("INSERT INTO osx_hashes VALUES (?,?,?,?,?)", values)
        conn.commit()
