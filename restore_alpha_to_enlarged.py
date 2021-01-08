from pathlib import Path
import sqlite3
import pandas as pd
from tqdm import tqdm
from sys import stderr
from imageio import imread, imwrite
import numpy as np
from skimage import transform as tf
from matplotlib import pyplot as plt

VIEWING = False

path_to_liif_script = Path("../liif/demo.py").resolve().absolute()
path_to_model = Path("../liif/rdn-liif.pth").resolve().absolute()

osx_dir = Path("osx/catalina/").absolute()
source_dir = osx_dir / "png"
preproc_dir = osx_dir / "bg/"
png_dir = Path("enlarged/").absolute()
out_dir = Path("transparent/").absolute()
pngs = [p for p in png_dir.iterdir() if p.suffix == ".png"]
osx_rgb_db = osx_dir / "emoji_rgb_calc.db"
NO_OVERWRITE = False

def get_emoji_rgb_bg(glyph):
    with sqlite3.connect(osx_rgb_db) as conn:
        query_sql = "SELECT * FROM images WHERE filename == (?)"
        query_df = pd.read_sql(query_sql, con=conn, params=[glyph])
        r, g, b = query_df.loc[:,[*"RGB"]].values.ravel()
    return r, g, b

try:
    for png in tqdm(pngs):
        source_png = source_dir / png.name
        preproc_png = preproc_dir / png.name
        output_png = out_dir / png.name
        if output_png.exists() and NO_OVERWRITE:
            continue
        elif not source_png.exists():
            raise NameError(f"Expected '{source_png}' corresponding to input '{png.name}'")
        # Remove the mask and show the result
        img = imread(png)
        source_img = imread(source_png)
        source_alpha = source_img[:,:,3]
        # If order is 0 then won't blend, I think blending is desirable to smooth sharp edge
        output_alpha = (
            tf.resize(source_alpha, img.shape[:2], order=1, preserve_range=True)
        ).astype(img.dtype)
        preproc_img = imread(preproc_png)
        preproc_img_original = preproc_img.copy()
        source_mask = source_img[:,:,3] == 0
        # Make copies of the coloured background images to restore alpha channel on
        preproc_masked = preproc_img.copy()
        bg_rgb = get_emoji_rgb_bg(png.name)
        preproc_masked[source_mask, 3] = 0
        preproc_recolouring = preproc_img.astype(int) - source_img.astype(int)
        preproc_recolouring[source_mask] = 0
        preproc_recolouring[:,:,3] = 0 # only want to consider RGB change
        preproc_masked_pre_recolor = preproc_masked.copy()
        # recolour the semitransparent pixels
        preproc_masked = (preproc_masked - preproc_recolouring).astype(img.dtype)
        output_img = np.insert(img, 3, output_alpha, axis=2)
        # Also want to recolour the semitransparent pixels
        output_semimask = (output_alpha > 0) & (output_alpha < 255)
        # If order is 0 then won't blend, I think blending is undesirable to smooth sharp
        # colour transitions (as long as it's just as effective? Not sure it will be...)
        output_img_no_recolour = output_img.copy()
        # Since the recolouring vector has (potentially) negative elements, normalise to
        # range (0,1) then restore
        recolouring_vec_min = preproc_recolouring.min()
        recolouring_vec_max = preproc_recolouring.max()
        recolouring_vec_range = preproc_recolouring.ptp()
        # Normalise the recolouring vector between 0 and 1 (as a float)
        recolouring_vec_normalised = (
            (preproc_recolouring - recolouring_vec_min) / recolouring_vec_range
        )
        recolouring_vector = (
            (tf.resize(recolouring_vec_normalised, img.shape[:2], order=0)
             * recolouring_vec_range) + recolouring_vec_min
        ).astype(int)
        # Naively resize the image to use when the recolouring differs from expectation
        # drastically (only used when overflow totally messes up any usable colour)
        naive_replacement = (
            tf.resize(source_img, img.shape[:2], order=1, preserve_range=True)
        ).astype(img.dtype)
        naive_alpha = naive_replacement[:,:,3]
        naive_mask = naive_alpha == 0
        naive_semimask = (naive_alpha > 0) & (naive_alpha < 255)
        naive_replacement[~naive_semimask] = 0
        output_img_pre_edit = output_img.copy()
        output_img = (output_img.astype(int) - recolouring_vector.astype(int))#.astype(img.dtype)
        output_mask = output_img[:,:,3] == 0
        n_overflow_mask = np.any(output_img < 0, axis=2)
        p_overflow_mask = np.any(output_img > 255, axis=2)
        uint8_overflow_mask = n_overflow_mask & p_overflow_mask
        output_img[uint8_overflow_mask] = naive_replacement[uint8_overflow_mask]
        output_img = output_img.astype(img.dtype)
        delta_expect = naive_replacement.astype(int) - output_img.astype(int)
        delta_min_per_pix = np.min(delta_expect[:,:,:3], axis=2)
        delta_max_per_pix = np.max(delta_expect[:,:,:3], axis=2)
        delta_threshold = 20
        sig_diff = (delta_min_per_pix < -delta_threshold) | (delta_max_per_pix > delta_threshold)
        sig_diff[~output_semimask] = False
        output_img[sig_diff] = naive_replacement[sig_diff]
        if VIEWING:
            plt.imshow(preproc_masked - preproc_recolouring)
            plt.show()
            plt.imshow(img)
            plt.show()
            plt.imshow(output_img)
            plt.show()
        else:
            imwrite(output_png, output_img)
except KeyboardInterrupt:
    print(f"Aborted while processing {png.name}")
