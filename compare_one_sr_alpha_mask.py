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

SAVING_PLOT = False
JUPYTER = True

osx_dir = Path("osx/catalina/").absolute()
source_dir = osx_dir / "png"
preproc_dir = osx_dir / "bg/"
png_dir = Path("enlarged/").absolute()
out_dir = Path("transparent/").absolute()
png = png_dir / "glyph-u1F343.png"
osx_bw_db = osx_dir / "emoji_bw_calc.db"
NO_OVERWRITE = False

def get_emoji_rgb_bg(glyph):
    with sqlite3.connect(osx_bw_db) as conn:
        query_sql = "SELECT * FROM images WHERE filename == (?)"
        query_df = pd.read_sql(query_sql, con=conn, params=[glyph])
        [r] = [g] = [b] = query_df.loc[:, "furthest_shade"].values
    return r, g, b

def alpha_composite_bg(img, background_shade):
    """
    Linearly composite an RGBA image against a grayscale background. Image dtype
    is preserved. Output height/width will match those of `im`, but the alpha
    channel dimension will be dropped making it only RGB.
    """
    if not isinstance(background_shade, int):
        raise TypeError("background_shade must be an integer")
    im = img.astype(float)
    bg = background_shade / 255
    im_max = im.max()
    im /= im_max # scale im to [0,1]
    im_rgb = im[:,:,:3]
    bg_rgb = np.ones_like(im_rgb) * bg
    # Scale RGB according to A
    alpha_im = im[:,:,3]
    alpha_bg = 1 - alpha_im
    im_rgb *= alpha_im[:,:,None]
    bg_rgb *= alpha_bg[:,:,None]
    composited = im_rgb + bg_rgb
    # Rescale to original range and return to original dtype
    composited *= im_max
    composited = composited.astype(img.dtype)
    return composited

def plot_comparison(
        scaled_source_img_sub_alpha,
        scaled_source_img_sub,
        img_sub,
        composited_grad,
        decomp_alpha,
        SAVING_PLOT
    ):
    fig, (ax0, ax1, ax2, ax3, ax4) = plt.subplots(1, 5, sharex=True, sharey=True)
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
    ax4.imshow(decomp_alpha)
    ax4.set_title("Difference of LIIF alpha from\nresized composite (estimated)")
    fig.tight_layout()
    if SAVING_PLOT:
        fig.set_size_inches((20,6))
        fig_name = "alpha_composite_comparison.png"
        fig.savefig(fig_name)
        reload_fig = imread(fig_name)
        fig_s = reload_fig.shape
        clip_y_t = fig_s[0] // 15 # ~7% top crop
        clip_y_b = -(fig_s[0] // 10) # ~10% bottom crop
        clip_x_l = fig_s[1] // 17 # ~6% left crop
        clip_x_r = -(fig_s[1] // 50) # ~ 2% right crop
        cropped_fig = reload_fig[clip_y_t:clip_y_b, clip_x_l:clip_x_r]
        imwrite(fig_name, cropped_fig)
    else:
        return fig, (ax0, ax1, ax2, ax3, ax4)
