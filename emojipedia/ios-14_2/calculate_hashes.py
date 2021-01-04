from tqdm import tqdm
from pathlib import Path
import sqlite3
from PIL import Image
from imagehash import average_hash, colorhash

def hash_emoji(img_fname):
    "Return average and color hashes (lengths 64 and 42 respectively)"
    img = Image.open(img_fname)
    mini_img = img.resize((32,32))
    a = average_hash(mini_img, hash_size=16)
    c = colorhash(mini_img, binbits=12)
    return str(a), str(c)

db_filename = "emojipedia_emoji_hashes.db"
png_dir = Path("png")
pngs = [p for p in png_dir.iterdir() if p.is_file() and p.suffix == ".png"]

with sqlite3.connect(db_filename) as conn:
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS emojipedia_hashes
    (filename tinytext, descriptor varchar(100), codepoint varchar(100),
    a_hash varchar(64), c_hash varchar(42), Constraint pk_fn Primary key(filename))
    """)

for png in tqdm(pngs):
    underscore_pos = png.stem.find("_")
    descriptor_part = png.stem[:underscore_pos]
    codepoint_part = png.stem[underscore_pos+1:]
    a_hash, c_hash = hash_emoji(png)
    with sqlite3.connect(db_filename) as conn:
        c = conn.cursor()
        values_tuple = (png.name, descriptor_part, codepoint_part, a_hash, c_hash)
        c.execute("INSERT INTO emojipedia_hashes VALUES (?,?,?,?,?)", values_tuple)
        conn.commit()
