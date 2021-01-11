from pathlib import Path
import sqlite3
import pandas as pd
from tqdm import tqdm
from sys import stderr
from imageio import imread, imwrite
import numpy as np
from skimage import transform as tf
from matplotlib import pyplot as plt
from transform_utils import scale_pixel_box_coordinates, crop_image

VIEWING = True
SAVING_PLOT = True

osx_dir = Path("osx/catalina/").absolute()
source_dir = osx_dir / "png"
preproc_dir = osx_dir / "bg/"
png_dir = Path("enlarged/").absolute()
out_dir = Path("transparent/").absolute()
pngs = [p for p in png_dir.iterdir() if p.suffix == ".png"]
osx_bw_db = osx_dir / "emoji_bw_calc.db"
NO_OVERWRITE = False

def get_emoji_rgb_bg(glyph):
    with sqlite3.connect(osx_bw_db) as conn:
        query_sql = "SELECT * FROM images WHERE filename == (?)"
        query_df = pd.read_sql(query_sql, con=conn, params=[glyph])
        [r] = [g] = [b] = query_df.loc[:, "furthest_shade"].values
    return r, g, b

try:
    for png in tqdm(pngs):
        if png.name != "glyph-u1F343.png":
            continue
        source_png = source_dir / png.name
        preproc_png = preproc_dir / png.name
        output_png = out_dir / png.name
        if output_png.exists() and NO_OVERWRITE:
            continue
        elif not source_png.exists():
            raise NameError(f"Expected '{source_png}' corresponding to input '{png.name}'")
        # Store (x,y) coordinates of the box of interest
        box_top_l = (0,104)
        box_bot_r = (56,160)
        box = [box_top_l, box_bot_r]
        # Remove the mask and show the result
        img = imread(png)
        source_img = imread(source_png)
        preproc_img = imread(preproc_png)
        scale = img.shape[0] / source_img.shape[0]
        scaled_box = scale_pixel_box_coordinates(box, scale)
        source_img_sub = crop_image(source_img, box)
        preproc_img_sub = crop_image(preproc_img, box)
        source_img_sub_alpha = source_img_sub[:,:,3]
        img_sub = crop_image(img, scaled_box)
        scaled_preproc_img_sub = tf.resize(
            preproc_img_sub[:,:,:3], img_sub.shape, order=0
        )
        scaled_source_img_sub = tf.resize(
            source_img_sub[:,:,:3], img_sub.shape, order=0
        )
        scaled_source_img_sub_alpha = tf.resize(
            source_img_sub_alpha, img_sub[:,:,0].shape, order=0
        )
        scaled_preproc_img_sub *= (1/scaled_preproc_img_sub.max()) * 255
        scaled_preproc_img_sub = scaled_preproc_img_sub.astype(int)#img.dtype)
        scaled_source_img_sub *= (1/scaled_source_img_sub.max()) * 255
        scaled_source_img_sub = scaled_source_img_sub.astype(int)#img.dtype)
        scaled_source_img_sub_alpha *= (1/scaled_source_img_sub_alpha.max()) * 255
        scaled_source_img_sub_alpha = scaled_source_img_sub_alpha.astype(int)#img.dtype)
        scaled_source_img_sub = np.insert(scaled_source_img_sub, 3, scaled_source_img_sub_alpha, axis=2)
        #grad = scaled_source_img_sub[:,:,:3] - img_sub
        #grad[scaled_source_img_sub[:,:,3] == 0] = 0
        composited_grad = scaled_preproc_img_sub - img_sub
        source_alpha = source_img[:,:,3]
        # If order is 0 then won't blend, I think blending is desirable to smooth sharp edge
        output_alpha = (
            tf.resize(source_alpha, img.shape[:2], order=1, preserve_range=True)
        ).astype(img.dtype)
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
            fig, (ax0, ax1, ax2, ax3) = plt.subplots(1, 4, sharex=True, sharey=True)
            ax0.imshow(scaled_source_img_sub_alpha)
            ax0.set_title("Alpha")
            #ax1.imshow(scaled_preproc_img_sub[:,:,:3])
            ax1.imshow(np.zeros_like(scaled_source_img_sub[:,:,:3]))
            ax1.imshow(scaled_source_img_sub)
            ax1.set_title("Source image (resize: nearest neighbour)")
            ax2.imshow(img_sub)
            ax2.set_title("LIIF superresolution")
            ax3.imshow(composited_grad)
            ax3.set_title("Difference of LIIF from resized composite")
            fig.tight_layout()
            if SAVING_PLOT:
                fig.set_size_inches((20,6))
                fig_name = "alpha_composite_comparison.png"
                fig.savefig(fig_name)
                reload_fig = imread(fig_name)
                fig_s = reload_fig.shape
                clip_y_t = fig_s[0] // 10 # ~10% top crop
                clip_y_b = -(fig_s[0] // 10) # ~10% bottom crop
                clip_x_l = fig_s[1] // 17 # ~6% left crop
                clip_x_r = -(fig_s[1] // 50) # ~ 2% right crop
                cropped_fig = reload_fig[clip_y_t:clip_y_b, clip_x_l:clip_x_r]
                imwrite(fig_name, cropped_fig)
            else:
                fig.show()
        else:
            imwrite(output_png, output_img)
        break
except KeyboardInterrupt:
    print(f"Aborted while processing {png.name}")
