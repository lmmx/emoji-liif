from pathlib import Path
import sqlite3
import pandas as pd
from tqdm import tqdm
from sys import stderr
from imageio import imread, imwrite
import numpy as np
from skimage import transform as tf
from matplotlib import pyplot as plt
from random import shuffle

VIEWING = True

osx_dir = Path("osx/catalina/").absolute()
png_dir = Path("enlarged/").absolute()
alpha_dir = Path("enlarged_alpha/").absolute()
out_dir = Path("transparent/").absolute()
pngs = [p for p in alpha_dir.iterdir() if p.suffix == ".png"]
osx_bw_db = osx_dir / "emoji_bw_calc.db"
NO_OVERWRITE = True
shuffle(pngs)

def get_emoji_bw_bg(glyph):
    with sqlite3.connect(osx_bw_db) as conn:
        query_sql = "SELECT * FROM images WHERE filename == (?)"
        query_df = pd.read_sql(query_sql, con=conn, params=[glyph])
        shade = query_df.loc[:, "furthest_shade"].values
    return shade

try:
    for png in tqdm(pngs):
        enlarged_png = png_dir / png.name
        output_png = out_dir / png.name
        if output_png.exists() and NO_OVERWRITE:
            continue
        elif not enlarged_png.exists():
            raise NameError(f"Expected '{enlarged_png}' corresponding to input '{png.name}'")
        alpha = imread(png)[:,:,0] # Keep R, discard identical G and B channels
        img = imread(enlarged_png)
        decomposited = np.insert(img, 3, alpha, axis=2)
        bg_shade = get_emoji_bw_bg(png.name)
        alpha_mask = (alpha > 0) & (alpha < 255) # Between transparent and opaque
        # Calculate the recolouring (R′,G′,B′) based on opacity A and the bg_shade S
        # In the range [0,1] a pixel (R,G,B,A) composited onto (S,S,S) becomes:
        # (R′,G′,B′) = (A*R + (1-A)*S, A*G + (1-A)*S, A*B + (1-A)*S)
        # This can be separated into:
        #            = (A*R, A*G, A*B) + (1-A)*S
        # This then needs to be multiplied by 255, so if the pixels are left as uint8
        #            = 255 * ((A*R, A*G, A*B) + (1-A)*S)
        #            = (A*R, A*G, A*B) + (255-A)*S/255
        # e.g. if the pixel RGBA=(0,0,0,51) and the bg_shade is 255
        # The black pixel at 20% opacity on white background becomes 80% whiter (204)
        # To regain (0,0,0,51) from (204,204,204) on (255,255,255) knowing A = 51
        # (R, G, B) = ((R′,G′,B′) - (255-A)*S/255) / A
        ###px_offset = img[alpha_mask] * alpha[alpha_mask][:, None]
        bg_offset = ((255 - alpha[alpha_mask]) * (bg_shade/255)).astype(int)
        px_offset = img[alpha_mask] - bg_offset[:, None]
        ###decompositing_offset = px_offset + bg_offset[:, None]
        decomposited_copy = decomposited.copy().astype(int)
        decomposited_copy[alpha_mask, :3] += px_offset
        breakpoint() # result is rubbish
        decomposited[alpha_mask,:3] += px_offset ###decompositing_offset
        if VIEWING:
            plt.imshow(decomposited_copy)
            fig.tight_layout()
            fig.show()
        else:
            imwrite(output_png, output_img)
        break
except KeyboardInterrupt:
    print(f"Aborted while processing {png.name}")
