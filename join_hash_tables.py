import sqlite3
from tqdm import tqdm
from pathlib import Path
import pandas as pd
from imagehash import hex_to_hash
import warnings
from operator import and_ as bitwise_and
from functools import reduce
from sys import stderr
from enum import Enum

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

class ToneSigns(Enum):
    light        = "1"
    medium_light = "2"
    medium       = "3"
    medium_dark  = "4"
    dark         = "5"

class GenderSigns(Enum):
    M = "man"
    W = "woman"

class CustomGenders(Enum):
    M_u1F9DC = "merman"
    W_u1F9DC = "mermaid"
    _u1F9DC = "merperson"
    M_u1F46F = "men"
    W_u1F46F = "women"
    _u1F46F = "people"
    M_u1F93C = "men"
    W_u1F93C = "women"
    _u1F93C = "people"
    #_u1F468_u1F91D_u1F468 = "men"
    _u1F469_u1F91D_u1F468 = "woman-and-man"
    #_u1F9D1_u1F91D_u1F9D1 = "people"
    #_u1F9D1 = "person"
    #_u1F468 = "man"

def attempt_singular_assignment(glyph, glyph_dict):
    "Attempt to whittle down multiple options from filename hints"
    glyph_stem = Path(glyph).stem
    glyph_codepoint_part = glyph[glyph.find("u"):glyph.find(".")]
    dot_signs = glyph_stem[glyph_stem.find(".")+1:].split(".")
    numeric_dot_signs = [d for d in dot_signs if d.isnumeric() and len(d) == 1]
    numpair_dot_signs = [d for d in dot_signs if d.isnumeric() and len(d) == 2]
    alphabetic_dot_signs = [d for d in dot_signs if d.isalpha() and len(d) == 1]
    for idx_p, p in enumerate(numpair_dot_signs):
        if len({*p}) == 1:
            twin_pair = numpair_dot_signs.pop(idx_p)
            numeric_dot_signs.append(twin_pair[0])
            #if glyph.startswith("glyph-u1F469_u1F91D_u1F468"):
            #    breakpoint()
    if len(numeric_dot_signs) == 1:
        # There's a single numeric tone sign
        nds = numeric_dot_signs[0]
        if nds == "0":
            # Ignore keys with "skin tone" in them
            excl_str = "skin-tone"
            proposed_dict = {k: v for (k,v) in glyph_dict.items() if excl_str not in k}
            if len(proposed_dict) < len(glyph_dict):
                glyph_dict.clear()
                glyph_dict.update(proposed_dict)
        elif nds in ToneSigns._value2member_map_:
            tone_str = ToneSigns(nds).name.replace("_", "-")
            other_tone_strings = [
                s.replace("_", "-") for s in ToneSigns._member_map_
                if s.replace("_", "-") != tone_str
            ]
            match_str = f"{tone_str}-skin-tone"
            excl_str_list = [f"{tone_str}-skin-tone" for tone_str in other_tone_strings]
            proposed_dict = {
                k: v for (k,v) in glyph_dict.items() if match_str in k
                if not any(
                    excl_str in k for excl_str in excl_str_list
                    if excl_str not in match_str
                )
            }
            if len(proposed_dict) < len(glyph_dict):
                glyph_dict.clear()
                glyph_dict.update(proposed_dict)
        else:
            # Should never happen (but print it if it does)
            print(f"Unexpected numeric sign '{nds}' in '{glyph}'", file=stderr)
    elif len(numpair_dot_signs) == 1:
        # There's a single numeric paired tone sign (i.e. two tone signs together)
        nds = tuple(numpair_dot_signs[0])
        if all(s in ToneSigns._value2member_map_ for s in nds):
            tone_strings = tuple(ToneSigns(s).name.replace("_", "-") for s in nds)
            other_tone_strings = [
                s for s in [x.replace("_", "-") for x in ToneSigns._member_map_]
                if s not in tone_strings
            ]
            match_strings = tuple(f"{tone_str}-skin-tone" for tone_str in tone_strings)
            n_light, n_med, n_dark = [
                len([m for m in match_strings if x in m])
                for x in ("light", "medium", "dark")
            ]
            excl_str_list = [f"{tone_str}-skin-tone" for tone_str in other_tone_strings]
            ms1, ms2 = match_strings
            matched_glyph_names = [
                k for k in glyph_dict if k.find(ms1) > -1
                if k[k.find(ms1)+len(ms1)+1:].find(ms2) > -1
            ]
            proposed_dict = {
                k: v for (k,v) in glyph_dict.items()
                if k in matched_glyph_names
                if not any(
                    excl_str in k for excl_str in excl_str_list
                    if all(excl_str not in match_str for match_str in match_strings)
                )
                if k.count("light") == n_light
                if k.count("medium") == n_med
                if k.count("dark") == n_dark
            }
            if len(proposed_dict) < len(glyph_dict):
                glyph_dict.clear()
                glyph_dict.update(proposed_dict)
        else:
            # Should never happen (but print it if it does)
            print(f"Unexpected numeric sign '{nds}' in '{glyph}'", file=stderr)
    if len(glyph_dict) > 1:
        # The results still need to be whittled down, try gender assignment
        if len(alphabetic_dot_signs) == 1:
            # There's a single alphabetic gender sign
            ads = alphabetic_dot_signs[0]
            gendered_codepoint = f"{ads}_{glyph_codepoint_part}"
            if gendered_codepoint in CustomGenders._member_map_:
                gender_str = CustomGenders[gendered_codepoint].value
            elif ads in "MW":
                gender_str = GenderSigns[ads].value
            else:
                print(f"Got an unrecognised gender '{ads}', ignoring", file=stderr)
                return
        else:
            # May be implied_gender in codepoints e.g. "man and woman" or "men"
            gendered_codepoint = "f_{glyph_codepoint_part}"
            if gendered_codepoint in CustomGenders._member_map_:
                gender_str = CustomGenders[gendered_codepoint].value
            elif len([d for d in dot_signs if d.isalpha()]) == 0:
                gender_str = "person" # or gender may just not be stated
            else:
                print(f"'{glyph}' may contain a multipart gender sign, ignoring", file=stderr)
                return # this could be a MM/MW multi-part string, skip
        other_genders = [g for g in ("man", "woman", "person") if g != gender_str]
        proposed_dict = {
            k: v for (k,v) in glyph_dict.items()
            if gender_str in k.replace("_", "-").split("-")
            if not any(excl_str in k.split("-") for excl_str in other_genders)
        }
        if len(proposed_dict) == 0 and gender_str == "person":
            # The gender may be distinguished by a lack of gendered noun instead
            # so remove the condition matching on the word "person"
            proposed_dict = {
                k: v for (k,v) in glyph_dict.items()
                if not any(excl_str in k.split("-") for excl_str in other_genders)
            }
        if len(proposed_dict) < len(glyph_dict):
            glyph_dict.clear()
            glyph_dict.update(proposed_dict)

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
pbar = tqdm(total=n_rows)
idx_row = 0
while idx_row < n_rows:
    osx_row = osx_df.iloc[idx_row]
    glyph = osx_row.filename
    if glyph == "glyph-hiddenglyph.png":
        idx_row += 1
        pbar.update(1)
        continue # not a real glyph, will not get a match, skip it
    if glyph in codepoint_matched_glyphs:
        glyph_dict = codepoint_matched_glyphs.get(glyph)
    else:
        glyph_dict = {}
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            oah, och, odh = [hex_to_hash(osx_row.get(f"{L}_hash")) for L in "acd"]
        glyph_codepoints = glyph[glyph.find("u"):glyph.find(".")].split("_")
        matchable_codepts = [
            p[3:].lower() if p.startswith("u00") else p.lstrip("u").lower()
            for p in glyph_codepoints
        ]
        if glyph.startswith("glyph-u1F469_u1F91D_u1F468"):
            post_dot = glyph.split(".")[1]
            if len(post_dot) == 2 and len({*tuple(post_dot)}) == 1:
                matchable_codepts = ["1f46b"]
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
                if retry_with_all_rows:
                    # Iterate over all rows (the following line is similar to np.ones_like)
                    idx_filter = pd.Series(1, ejp_df.index, dtype="bool")
        # Attempt to match without even considering the hashes, from filename alone
        if ejp_df[idx_filter].shape[0] < 50: # probably too high a threshold who knows
            v = {f"{L}_dist": -1 for L in "acd"}
            pre_hash_glyph_dict = {k: v for k in ejp_df[idx_filter].filename}
            attempt_singular_assignment(glyph, pre_hash_glyph_dict)
            if len(pre_hash_glyph_dict) == 1:
                glyph_dict = pre_hash_glyph_dict
                #print(f"Pre-hash singular assignment for '{glyph}': {glyph_dict}")
                write_result_to_db(glyph, glyph_dict)
                retry_with_all_rows = False
                idx_row += 1
                pbar.update(1)
                continue
        for i, ejp_row in ejp_df[idx_filter].iterrows():
            ejp_filename = ejp_row.filename
            if ejp_filename in codepoint_matched_ejp_filenames:
                continue # do not score emojipedia icons already matched by codepoint
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                eah, ech, edh = [hex_to_hash(ejp_row.get(f"{L}_hash")) for L in "acd"]
                #ech = hex_to_flathash(ejp_row.get("c_hash")) # unsure if needed yet
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
        if len(glyph_dict) > 1:
            attempt_singular_assignment(glyph, glyph_dict)
        write_result_to_db(glyph, glyph_dict)
        retry_with_all_rows = False
        idx_row += 1
        pbar.update(1)
    elif retry_with_all_rows:
        # Already retried, give up and just print an error message
        # Possibly due to the true match having incompatible hash sizes (can happen)
        print(f"Warning: no match was found for '{glyph}'", file=stderr)
        retry_with_all_rows = False
        idx_row += 1
    else:
        retry_with_all_rows = True
        # Do not increment idx_row (or update pbar) so loop will retry same row
