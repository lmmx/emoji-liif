import sqlite3
from tqdm import tqdm
from pathlib import Path
import pandas as pd
from imagehash import hex_to_hash
import warnings

result_db = "matches.db"
osx_db = Path("osx/catalina/osx_emoji_hashes.db")
emojipedia_db = Path("emojipedia/ios-14_2/emojipedia_emoji_hashes.db")

with sqlite3.connect(osx_db) as osx_conn:
    osx_sql = "SELECT * FROM osx_hashes"
    osx_df = pd.read_sql(osx_sql, con=osx_conn)

with sqlite3.connect(emojipedia_db) as ejp_conn:
    ejp_sql = "SELECT * FROM emojipedia_hashes"
    ejp_df = pd.read_sql(ejp_sql, con=ejp_conn)

# result = pd.merge(osx_df, ejp_df, how="inner", on=["a_hash", "c_hash"])
# Only 11 can be matched with this approach! Many more can be matched with hash funcs:

#glyph_dicts = {}

with sqlite3.connect(result_db) as conn:
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS top_hash_matches
    (glyph_filename tinytext, matched_filename tinytext, 
    a_hash varchar(64), c_hash varchar(42), multimatch tinyint)
    """)
    # Don't enforce primary key constraint since not yet known if will match perfectly

def write_result_to_db(glyph, glyph_dict):
    with sqlite3.connect(result_db) as conn:
        c = conn.cursor()
        is_multi = len(glyph_dict) > 1
        for matched_glyph, dist_dict in glyph_dict.items():
            a_hash, c_hash = dist_dict.get("a_dist"), dist_dict.get("c_dist")
            values_tuple = (glyph, matched_glyph, a_hash, c_hash, is_multi)
            c.execute("INSERT INTO top_hash_matches VALUES (?,?,?,?,?)", values_tuple)
        conn.commit()

for i, osx_row in tqdm(osx_df.iterrows(), total=osx_df.shape[0]):
    glyph = osx_row.filename
    glyph_dict = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        osx_a_h, osx_c_h = [hex_to_hash(v) for v in (osx_row.a_hash, osx_row.c_hash)]
    for i, ejp_row in ejp_df.iterrows():
        ejp_filename = ejp_row.filename
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ejp_a_h, ejp_c_h = [hex_to_hash(v) for v in (ejp_row.a_hash, ejp_row.c_hash)]
        oah_s, och_s = [v.hash.shape for v in (osx_a_h, osx_c_h)]
        eah_s, ech_s = [v.hash.shape for v in (ejp_a_h, ejp_c_h)]
        if oah_s != eah_s or och_s != ech_s:
            continue # hex strings are not of comparable hash shapes so don't even try
        dist_a = osx_a_h - ejp_a_h
        dist_c = osx_c_h - ejp_c_h
        if glyph_dict:
            set_to_update = False
            keys_to_delete = []
            for gly_k, gly_v in glyph_dict.items():
                gly_a, gly_c = gly_v.get("a_dist"), gly_v.get("c_dist")
                if (dist_a, dist_c) < (gly_a, gly_c):
                    # Delete any (potentially multiple same score) more distant glyphs
                    keys_to_delete.append(gly_k)
                    set_to_update = True
                elif (dist_a, dist_c) == (gly_a, gly_c):
                    # This glyph is just as good but no better so add it as well
                    set_to_update = True
            for gly_k in keys_to_delete:
                # Delete after iteration through the dict items
                #print(f"Deleting {gly_k} as {ejp_filename} scored better")
                del glyph_dict[gly_k]
            if set_to_update:
                glyph_dict.update({ejp_filename: {"a_dist": dist_a, "c_dist": dist_c}})
        else:
            glyph_dict.update({ejp_filename: {"a_dist": dist_a, "c_dist": dist_c}})
    write_result_to_db(glyph, glyph_dict)
    #result_dict = {glyph: glyph_dict}
    #print(result_dict)
    #glyph_dicts.update(result_dict)
