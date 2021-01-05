from tqdm import tqdm
import csv
from pathlib import Path
import sqlite3
from PIL import Image
from imagehash import average_hash, dhash, colorhash

def hash_emoji(img_fname):
    "Return average and color hashes (lengths 64 and 42 respectively)"
    img = Image.open(img_fname)
    mini_img = img.resize((32,32))
    a = average_hash(mini_img, hash_size=16)
    c = colorhash(mini_img, binbits=12)
    d = dhash(mini_img, hash_size=16)
    return str(a), str(c), str(d)

db_filename = "emoji_hashes.db"
osx_dir = Path("osx")
ejp_dir = Path("emojipedia")

with sqlite3.connect(db_filename) as conn:
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS osx_hashes
    (filename tinytext, codepoint_part varchar(32), a_hash varchar(64),
    c_hash varchar(42), d_hash varchar(64), Constraint pk_fn Primary key(filename))
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS emojipedia_hashes
    (filename tinytext, descriptor varchar(100), codepoint varchar(100),
    a_hash varchar(64), c_hash varchar(42), d_hash varchar(64),
    Constraint pk_fn Primary key(filename))
    """)

pngs = [p for p in osx_dir.iterdir() if p.is_file() and p.suffix == ".png"]
for png in tqdm(pngs):
    codepoint_part = png.stem[6:] # remove "glyph-" prefix and ".png" suffix
    a_hash, c_hash, d_hash = hash_emoji(png)
    with sqlite3.connect(db_filename) as conn:
        c = conn.cursor()
        values_tuple = (png.name, codepoint_part, a_hash, c_hash, d_hash)
        c.execute("INSERT INTO osx_hashes VALUES (?,?,?,?,?)", values_tuple)
        conn.commit()

pngs = [p for p in ejp_dir.iterdir() if p.is_file() and p.suffix == ".png"]
for png in tqdm(pngs):
    underscore_pos = png.stem.find("_")
    descriptor_part = png.stem[:underscore_pos]
    codepoint_part = png.stem[underscore_pos+1:]
    a_hash, c_hash, d_hash = hash_emoji(png)
    with sqlite3.connect(db_filename) as conn:
        c = conn.cursor()
        values_tuple = (png.name, descriptor_part, codepoint_part, a_hash, c_hash, d_hash)
        c.execute("INSERT INTO emojipedia_hashes VALUES (?,?,?,?,?,?)", values_tuple)
        conn.commit()

with sqlite3.connect(db_filename) as conn:
    c = conn.cursor()
    c.execute("SELECT * FROM emojipedia_hashes")
    rows = c.fetchall()
    tsv_out = Path(db_filename).stem + "_emojipedia.tsv"
    with open(tsv_out, "w") as tsvfile:
        tsv_writer = csv.writer(tsvfile, delimiter="\t")
        tsv_writer.writerows(rows)
    c = conn.cursor()
    c.execute("SELECT * FROM osx_hashes")
    rows = c.fetchall()
    tsv_out = Path(db_filename).stem + "_osx.tsv"
    with open(tsv_out, "w") as tsvfile:
        tsv_writer = csv.writer(tsvfile, delimiter="\t")
        tsv_writer.writerows(rows)
