from tqdm import tqdm
from pathlib import Path
from imageio import imread
import numpy as np
#from pprint import pprint
import sqlite3

db_filename = "emoji_rgb_calc.db"

def euclidean_dist(v1, v2):
    "Returns the Euclidean distance between vectors 'v1' and 'v2'."
    return np.linalg.norm(v1 - v2)

def cartesian_product(arrays):
    "Courtesy of https://stackoverflow.com/a/11146645/2668831"
    la = len(arrays)
    dtype = np.result_type(*arrays)
    arr = np.empty([la] + [len(a) for a in arrays], dtype=dtype)
    for i, a in enumerate(np.ix_(*arrays)):
        arr[i, ...] = a
    return arr.reshape(la, -1).T

png_dir = Path("png")
pngs = [p for p in png_dir.iterdir() if p.is_file() and p.suffix == ".png"]

shades = np.linspace(0, 255, 5, dtype=np.uint8)
colour_cloud = cartesian_product([shades] * 3) # 125 values to choose from

with sqlite3.connect(db_filename) as conn:
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS images
    (filename tinytext, R tinyint, G tinyint, B tinyint, min_d smallint,
    Constraint pk_fn Primary key(filename))
    """)

for png in tqdm(pngs):
    codepoint_part = png.stem[6:-4] # remove "glyph-" prefix and ".png" suffix
    recorded_distances = {tuple(rgb): () for rgb in colour_cloud}
    img = imread(png)
    all_vis_rgba = img.reshape(-1, 4)[img.reshape(-1,4)[:,3] > 0]
    all_semi_vis_rgba = all_vis_rgba[all_vis_rgba[:,3] < 255]
    all_semi_vis_rgb = np.unique(np.sort(all_semi_vis_rgba[:,:3], axis=0), axis=0)
    
    # Find the distance between each of the points and the colour cloud
    for p in colour_cloud:
        colour_tup = tuple(p)
        all_distances = np.array([euclidean_dist(p,q) for q in all_semi_vis_rgb])
        if not np.isin(0, all_distances):
            # Store the distances for later comparison
            recorded_distances.update({
                colour_tup: (
                    all_distances.min().astype(int),
                    all_distances.max().astype(int),
                    all_distances.mean().astype(int)
                )
            })
    # We do not want to use a background colour that will erase or blend with any
    # semi-visible pixel's colour: we want one as distant as possible from these
    sorted_dict = dict(sorted(recorded_distances.items(), key=lambda v: v[1]))
    #pprint(sorted_dict, sort_dicts=False)
    result_rgb, result_dists = list(sorted_dict.items())[-1]
    r,g,b = [int(v) for v in result_rgb]
    #print(f"RGB: {result_rgb} @ {result_dists}")
    min_dist, max_dist, mean_dist = [int(v) for v in result_dists]
    with sqlite3.connect(db_filename) as conn:
        c = conn.cursor()
        e_filename = png.name
        values_tuple = (e_filename, r, g, b, min_dist)
        c.execute("INSERT INTO images VALUES (?,?,?,?,?)", values_tuple)
        conn.commit()
