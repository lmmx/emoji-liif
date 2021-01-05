import sqlite3
from tqdm import tqdm
from pathlib import Path
import pandas as pd
from imagehash import hex_to_hash
import warnings
from operator import and_ as bitwise_and
from functools import reduce
from sys import stderr

result_db = "matches.db"
osx_db = Path("osx/catalina/osx_emoji_hashes.db")
emojipedia_db = Path("emojipedia/ios-14_2/emojipedia_emoji_hashes.db")

with sqlite3.connect(osx_db) as osx_conn:
    osx_sql = "SELECT * FROM osx_hashes"
    osx_df = pd.read_sql(osx_sql, con=osx_conn)

with sqlite3.connect(emojipedia_db) as ejp_conn:
    ejp_sql = "SELECT * FROM emojipedia_hashes"
    ejp_df = pd.read_sql(ejp_sql, con=ejp_conn)

with sqlite3.connect(result_db) as conn:
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS top_hash_matches
    (glyph_filename tinytext, matched_filename tinytext, 
    a_hash varchar(64), c_hash varchar(42), d_hash varchar(64), multimatch tinyint)
    """)
    # Don't enforce primary key constraint since not yet known if will match perfectly

def write_result_to_db(glyph, glyph_dict):
    with sqlite3.connect(result_db) as conn:
        c = conn.cursor()
        is_multi = len(glyph_dict) > 1
        for matched_glyph, dist_dict in glyph_dict.items():
            a_hash, c_hash, d_hash = [dist_dict.get(f"{L}_dist") for L in "acd"]
            values = (glyph, matched_glyph, a_hash, c_hash, d_hash, is_multi)
            c.execute("INSERT INTO top_hash_matches VALUES (?,?,?,?,?,?)", values)
        conn.commit()

def fetch_sql_query(conn, sql_query, query_variable):
    c = conn.cursor()
    c.execute(sql_query, query_variable)
    return c.fetchone() # `None` if no matching result or a single row tuple

def record_match(hit, glyph, glyph_dict):
    "Store and then write to database in next pass through `osx_df` rows"
    ejp_filename = hit[0]
    codepoint_matched_ejp_filenames.append(ejp_filename)
    glyph_dict.update({ejp_filename: {f"{L}_dist": -1 for L in "acd"}})
    codepoint_matched_glyphs.update({glyph: glyph_dict})

codepoint_matched_glyphs = {}
codepoint_matched_ejp_filenames = []
for i, osx_row in tqdm(osx_df.iterrows(), total=osx_df.shape[0]):
    glyph = osx_row.filename
    glyph_dict = {}
    with sqlite3.connect(emojipedia_db) as ejp_conn:
        variable_codepoint_part = (osx_row.codepoint_part,)
        hit = fetch_sql_query(ejp_conn, """
        SELECT * FROM emojipedia_hashes
        WHERE LOWER(REPLACE(REPLACE(?, "_u", "-"), "u", "")) == codepoint
        """, variable_codepoint_part)
        if hit:
            record_match(hit, glyph, glyph_dict)
            continue
        # Otherwise try again with the ".0" suffix for skin tone variant emojis
        hit = fetch_sql_query(ejp_conn, """
        SELECT * FROM emojipedia_hashes
        WHERE LOWER(REPLACE(REPLACE(?, "_u", "-"), "u", "")) == REPLACE(codepoint || ".0", "-fe0f.0", ".0")
        """, variable_codepoint_part)
        if hit:
            record_match(hit, glyph, glyph_dict)
            continue
        # Otherwise try again with the "-200d" zero width joiner
        hit = fetch_sql_query(ejp_conn, """
        SELECT * FROM emojipedia_hashes
        WHERE LOWER(REPLACE(REPLACE(?, "_u", "-200d-"), "u", "")) == codepoint
        """, variable_codepoint_part)
        if hit:
            record_match(hit, glyph, glyph_dict)
            continue
        # Otherwise try again with both the ZWJ and the ".0" suffix
        hit = fetch_sql_query(ejp_conn, """
        SELECT * FROM emojipedia_hashes
        WHERE LOWER(REPLACE(REPLACE(?, "_u", "-200d-"), "u", "")) == REPLACE(codepoint || ".0", "-fe0f.0", ".0")
        """, variable_codepoint_part)
        if hit:
            record_match(hit, glyph, glyph_dict)
            continue

with open("codepoint_matched_ejp_filenames.txt", "w") as f:
    f.writelines([f"{l}\n" for l in codepoint_matched_ejp_filenames])

n_rows = osx_df.shape[0]
pbar = tqdm(total=n_rows + 1)
i = 0
#for i, osx_row in tqdm(osx_df.iterrows(), total=osx_df.shape[0]):
while i < n_rows:
    osx_row = osx_df.iloc[i]
    glyph = osx_row.filename
    if glyph == "glyph-hiddenglyph.png":
        continue # not a real glyph, will not get a match, skip it
    if glyph in codepoint_matched_glyphs:
        glyph_dict = codepoint_matched_glyphs.get(glyph)
    else:
        glyph_dict = {}
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            oah, och, odh = [hex_to_hash(osx_row.get(f"{L}_hash")) for L in "acd"]
        glyph_codepoints = glyph[glyph.find("u"):glyph.find(".")].split("_")
        if glyph == "glyph-u1F468_u1F3ED.5.png":
            pass # breakpoint()
        matchable_codepts = [x.lstrip("u").lower() for x in glyph_codepoints]
        partial_matchers = [ejp_df.filename.str.contains(x) for x in matchable_codepts]
        row_filter = reduce(bitwise_and, partial_matchers)
        if row_filter.any():
            idx_filter = row_filter
        else:
            retry_row_filter = ejp_df.filename.str.contains(matchable_codepts[0])
            if retry_row_filter.any():
                idx_filter = retry_row_filter
                breakpoint()
            else:
                if matchable_codepts[0] == "27a1":
                    breakpoint()
                print(f"Retry failed with {matchable_codepts[0]}", file=stderr)
                # Iterate over all rows (the following line is similar to np.ones_like)
                idx_filter = pd.Series(1, ejp_df.index, dtype="bool")
        for i, ejp_row in ejp_df[idx_filter].iterrows():
            ejp_filename = ejp_row.filename
            if ejp_filename in codepoint_matched_ejp_filenames:
                continue # do not score emojipedia icons already matched by codepoint
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                eah, ech, edh = [hex_to_hash(ejp_row.get(f"{L}_hash")) for L in "acd"]
            oah_s, och_s, odh_s = [v.hash.shape for v in (oah, och, odh)]
            eah_s, ech_s, edh_s = [v.hash.shape for v in (eah, ech, edh)]
            if oah_s != eah_s or och_s != ech_s or odh_s != edh_s:
                continue # hex strings are not of comparable hash shapes so don't even try
            dist_a = oah - eah
            dist_c = och - ech
            dist_d = odh - edh
            if glyph_dict:
                set_to_update = False
                keys_to_delete = []
                for gly_k, gly_v in glyph_dict.items():
                    gly_a, gly_c, gly_d = [gly_v.get(f"{L}_dist") for L in "acd"]
                    if (dist_d, dist_c, dist_a) < (gly_d, gly_c, gly_a):
                        # Delete any (potentially multiple same score) more distant glyphs
                        keys_to_delete.append(gly_k)
                        set_to_update = True
                    elif (dist_d, dist_c, dist_a) == (gly_d, gly_c, gly_a):
                        # This glyph is just as good but no better so add it as well
                        set_to_update = True
                # Delete and update if needed, after iteration through the dict items
                for gly_k in keys_to_delete:
                    #print(f"Deleting {gly_k} as {ejp_filename} scored better")
                    del glyph_dict[gly_k]
                if set_to_update:
                    dist_dict = {"a_dist": dist_a, "c_dist": dist_c, "d_dist": dist_d}
                    glyph_dict.update({ejp_filename: dist_dict})
            else:
                dist_dict = {"a_dist": dist_a, "c_dist": dist_c, "d_dist": dist_d}
                glyph_dict.update({ejp_filename: dist_dict})
        if glyph_dict:
            write_result_to_db(glyph, glyph_dict)
            retry_with_all_rows = False
            i += 1
        elif retry_with_all_rows:
            # Already retried, give up and just print an error message
            print(f"Warning: no match was found for '{glyph}'", file=stderr)
            retry_with_all_rows = False
            i += 1
        else:
            retry_with_all_rows = True
            # Do not increment i
