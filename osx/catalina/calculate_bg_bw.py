from tqdm import tqdm
from pathlib import Path
from imageio import imread
import numpy as np
import sqlite3
import pandas as pd

db_filename = "emoji_bw_calc.db"

def euclidean_dist(v1, v2):
    "Returns the Euclidean distance between vectors 'v1' and 'v2'."
    return np.linalg.norm(v1 - v2)

png_dir = Path("png")
pngs = [p for p in png_dir.iterdir() if p.is_file() and p.suffix == ".png"]

with sqlite3.connect(db_filename) as conn:
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS images
    (filename tinytext,
    has_B tinyint, has_D1 tinyint, has_D2 tinyint, has_G1 tinyint, has_G2 tinyint,
    has_L1 tinyint, has_L2 tinyint, has_W tinyint,
    dist_B tinyint, dist_D1 tinyint, dist_D2 tinyint, dist_G1 tinyint, dist_G2 tinyint,
    dist_L1 tinyint, dist_L2 tinyint, dist_W tinyint,
    Constraint pk_fn Primary key(filename))
    """)

for png in tqdm(pngs):
    #if png not in [
    #    "glyph-u1F689.png",
    #    "glyph-u1F3BC.png",
    #    "glyph-u2615.png"
    #]:
    #    continue
    codepoint_part = png.stem[6:-4] # remove "glyph-" prefix and ".png" suffix
    img = imread(png)
    all_vis_rgba = img.reshape(-1, 4)[img.reshape(-1,4)[:,3] > 0]
    all_semi_vis_rgba = all_vis_rgba[all_vis_rgba[:,3] < 255]
    all_semi_vis_rgb = np.unique(np.sort(all_semi_vis_rgba[:,:3], axis=0), axis=0)
    shades = (0, 36, 72, 108, 144, 180, 216, 255)
    # b_sv, d1_sv, d2_sv, g1_sv, g2_sv, l1_sv, l2_sv, w_sv
    shade_semi_vis_bools = [
        np.any(np.all(all_semi_vis_rgb == p, axis=1)) for p in shades
    ]
    # All distances for each shade
    # b_d, d1_d, d2_d, g1_d, g2_d, l1_d, l2_d, w_d
    shade_distance_arrays = [
        np.array([euclidean_dist((s, s, s), c) for c in all_semi_vis_rgb])
        for s in shades
    ]
    # b_dbar, d1_dbar, d2_dbar, g1_dbar, g2_dbar, l1_dbar, l2_dbar, w_dbar
    all_mean_distances = [
        int(all_distances.mean().astype(int))
        for all_distances in shade_distance_arrays
    ]
    # has_b, has_d1, has_d2, has_g1, has_g2, has_l1, has_l2, has_w 
    has_shade_flags = map(int, shade_semi_vis_bools)
    with sqlite3.connect(db_filename) as conn:
        c = conn.cursor()
        e_filename = png.name
        values_tuple = (
            e_filename, *has_shade_flags, *all_mean_distances
        )
        c.execute(
            "INSERT INTO images VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            values_tuple
        )
        conn.commit()

with sqlite3.connect(db_filename) as conn:
    query_sql = """
    SELECT * FROM images
    WHERE has_B == 1 AND has_G1 == 1 AND has_G2 == 1 AND has_W == 1
    """
    lucky_df = pd.read_sql(query_sql, con=conn)
