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

def plot_comparison(
        scaled_source_img_sub_alpha,
        scaled_source_img_sub,
        img_sub,
        composited_grad,
        SAVING_PLOT
    ):
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
    ax3.set_title("Difference of LIIF\nfrom resized composite")
    fig.tight_layout()
    if SAVING_PLOT:
        fig.set_size_inches((20,6))
        fig_name = "alpha_composite_comparison_2x2.png"
        fig.savefig(fig_name)
        reload_fig = imread(fig_name)
        fig_s = reload_fig.shape
        clip_y_t = fig_s[0] // 17 # ~6% top crop
        clip_y_b = -(fig_s[0] // 10) # ~10% bottom crop
        clip_x_l = fig_s[1] // 20 # ~5% left crop
        clip_x_r = -(fig_s[1] // 50) # ~ 2% right crop
        cropped_fig = reload_fig[clip_y_t:clip_y_b, clip_x_l:clip_x_r]
        imwrite(fig_name, cropped_fig)
    else:
        fig.show()

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
        #offset_tlx, offset_tly, offset_brx, offset_bry = np.array([360,475,400,512]) // 12.5
        offset_tlx, offset_brx = 0, 0
        offset_tly, offset_bry = 0, 0
        box_top_l = (30+offset_tlx,144+offset_tly)
        box_bot_r = (32-offset_brx,146-offset_bry)
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
        composited_grad = img_sub.astype(int) - scaled_preproc_img_sub
        # Rescale from [-255,+255] to [0,1] by incrementing +255 then squashing by half
        composited_grad = ((composited_grad + 255) / (255*2))
        if VIEWING:
            plot_comparison(scaled_source_img_sub_alpha, scaled_source_img_sub, img_sub, composited_grad, SAVING_PLOT)
        else:
            imwrite(output_png, output_img)
        break
except KeyboardInterrupt:
    print(f"Aborted while processing {png.name}")
