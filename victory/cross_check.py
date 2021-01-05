from imagehash import hex_to_hash
import pandas as pd

osx_df = pd.read_csv("emoji_hashes_osx.tsv", sep="\t", header=None)
ejp_df = pd.read_csv("emoji_hashes_emojipedia.tsv", sep="\t", header=None)

for i, o_row in osx_df.sort_values(0).iterrows():
    o_fn, *_, o_a, o_c, o_d = o_row
    o_a, o_c, o_d = [hex_to_hash(hexstr) for hexstr in (o_a, o_c, o_d)]
    o_a_s, o_c_s, o_d_s = o_a.hash.shape, o_c.hash.shape, o_d.hash.shape
    for j, e_row in ejp_df.iterrows():
        e_fn, *_, e_a, e_c, e_d = e_row
        e_a, e_c, e_d = [hex_to_hash(hexstr) for hexstr in (e_a, e_c, e_d)]
        e_a_s, e_c_s, e_d_s = e_a.hash.shape, e_c.hash.shape, e_d.hash.shape
        if (e_a_s, e_c_s, e_d_s) != (o_a_s, o_c_s, o_d_s):
            continue
        dist_a, dist_c, dist_d = o_a - e_a, o_c - e_c, o_d - e_d
        print(f"{o_fn}\t{e_fn}\t{dist_a}\t{dist_c}\t{dist_d}")
