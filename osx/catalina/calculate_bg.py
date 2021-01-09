from tqdm import tqdm
from pathlib import Path
from imageio import imread
import numpy as np
import sqlite3
import pandas as pd
from enum import IntEnum

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
    has_B tinyint, has_D1 tinyint, has_D2 tinyint, has_D3 tinyint, has_G tinyint,
    has_L1 tinyint, has_L2 tinyint, has_L3 tinyint, has_W tinyint,
    dist_B tinyint, dist_D1 tinyint, dist_D2 tinyint, dist_D3 tinyint, dist_G tinyint,
    dist_L1 tinyint, dist_L2 tinyint, dist_L3 tinyint, dist_W tinyint,
    median_tone tinyint, furthest_shade tinyint, Constraint pk_fn Primary key(filename))
    """)

class ShadeEnum(IntEnum):
    B  = 0
    D1 = 32
    D2 = 64
    D3 = 96
    G  = 128
    L1 = 160
    L2 = 192
    L3 = 233 # 233 replacing 224 specifically for u1F3BC
    W  = 255

for png in tqdm(pngs):
    codepoint_part = png.stem[6:-4] # remove "glyph-" prefix and ".png" suffix
    img = imread(png)
    all_vis_rgba = img.reshape(-1, 4)[img.reshape(-1,4)[:,3] > 0]
    all_semi_vis_rgba = all_vis_rgba[all_vis_rgba[:,3] < 255]
    all_semi_vis_rgb = np.unique(np.sort(all_semi_vis_rgba[:,:3], axis=0), axis=0)
    # Take the median of the distribution of mean RGB per visible pixel
    # to use when deciding between B and W when equidistant
    median_tone = int(np.median(all_vis_rgba[:,:3].mean(axis=1)))
    shades = tuple(ShadeEnum._value2member_map_.keys())
    # B_sv, D1_sv, D2_sv, D3_sv, G_sv, L1_sv, L2_sv, L3_sv, W_sv
    shade_semi_vis_bools = [
        np.any(np.all(all_semi_vis_rgb == p, axis=1)) for p in shades
    ]
    # has_B, has_D1, has_D2, has_D3, has_G, has_L1, has_L2, has_L3, has_W
    has_shade_flags = [*map(int, shade_semi_vis_bools)]
    # All distances for each shade
    # B_d, D1_d, D2_d, D3_d, G_d, L1_d, L2_d, L3_d, W_d
    shade_distance_arrays = [
        np.array([euclidean_dist((s, s, s), c) for c in all_semi_vis_rgb])
        if not has_shade_flags[j] else np.array([-1])
        for (j,s) in enumerate(shades)
    ]
    # B_dbar, D1_dbar, D2_dbar, D3_dbar, G_dbar, L1_dbar, L2_dbar, L3_dbar, W_dbar
    all_mean_distances = [
        int(all_distances.mean().astype(int))
        for all_distances in shade_distance_arrays
    ]
    shade_idx = [
        i for (i,d) in enumerate(all_mean_distances) if d == np.max(all_mean_distances)
    ]
    if len(shade_idx) > 1:
        #assert shade_idx == [0,8] # only expect to happen when B and W are equidistant
        far_shades = np.array([shades[s] for s in shade_idx])
        furthest_shade = int(far_shades[np.abs(far_shades - median_tone).argsort()][-1])
    else:
        furthest_shade = shades[shade_idx[0]]
    with sqlite3.connect(db_filename) as conn:
        c = conn.cursor()
        e_filename = png.name
        values_tuple = (
            e_filename, *has_shade_flags, *all_mean_distances,
            median_tone, furthest_shade
        )
        c.execute(
            "INSERT INTO images VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            values_tuple
        )
        conn.commit()

with sqlite3.connect(db_filename) as conn:
    query_sql = """
    SELECT * FROM images
    """
    #WHERE has_B == 1
    #AND has_D1 == 1 AND has_D2 == 1 AND has_D3 == 1
    #AND has_G == 1
    #AND has_L1 == 1 AND has_L2 == 1 AND has_L3 == 1
    #AND has_W == 1
    #"""
    result_df = pd.read_sql(query_sql, con=conn)
