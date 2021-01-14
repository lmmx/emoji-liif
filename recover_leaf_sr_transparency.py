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
from compare_one_sr_alpha_mask import get_emoji_rgb_bg, alpha_composite_bg, plot_comparison

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

source_png = source_dir / png.name
preproc_png = preproc_dir / png.name
output_png = out_dir / png.name
if output_png.exists() and NO_OVERWRITE:
    raise ValueError("Cannot overwrite")
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
scaled_source_img_sub_im = scaled_source_img_sub.copy() # Retain 3 channel copy
scaled_source_img_sub = np.insert(scaled_source_img_sub, 3, scaled_source_img_sub_alpha, axis=2)
composited_grad = img_sub.astype(int) - scaled_preproc_img_sub
# Rescale from [-255,+255] to [0,1] by incrementing +255 then squashing by half
composited_grad = ((composited_grad + 255) / (255*2))
composited_grad *= scaled_source_img_sub_alpha[:,:,None]
composited_grad /= 255
# Rescale all opaque regions to 1 (and clip any above 1 now)
previous_max_alpha = scaled_source_img_sub_alpha == 255
min_of_previous_max_alpha = composited_grad[previous_max_alpha].min()
composited_grad *= (0.5/min_of_previous_max_alpha)
#composited_grad[scaled_source_img_sub_alpha == 255] = 0.5
#composited_grad /= composited_grad.max()
#breakpoint()
decomp_alpha = (scaled_source_img_sub_alpha / 255) + composited_grad.max(axis=2)
# Now rearrange to acquire the estimatable part (the "estimand")
i_in = (scaled_source_img_sub_alpha[:,:,None]/255) * (scaled_source_img_sub_im/255) # alpha_source * im_source
#breakpoint()
# If squashing composited_grad to [0,1] then don't need to divide it by 255 here
#estimand = (composited_grad/255) - (scaled_source_img_sub_alpha[:,:,None] * i_in)
estimand = composited_grad - (scaled_source_img_sub_alpha[:,:,None] * i_in)
#fig1, f1_axes = plot_comparison(
#    scaled_source_img_sub_alpha,
#    scaled_source_img_sub,
#    img_sub,
#    composited_grad,
#    decomp_alpha,
#    SAVING_PLOT
#)
#fig1.show()

decomposited = np.insert(img_sub, 3, decomp_alpha * 255, axis=2)


all_black = np.zeros_like(scaled_source_img_sub, dtype=img.dtype)
all_black[:,:,3] = 255
fig2, f2_axes = plot_comparison(
    scaled_source_img_sub_alpha,
    scaled_source_img_sub,
    img_sub,
    composited_grad,
    all_black,
    SAVING_PLOT
)
f2_axes[-1].imshow(decomposited)
#fig2.show()

recomposited = alpha_composite_bg(decomposited, 0)

fig3, f3_axes = plot_comparison(
    scaled_source_img_sub_alpha,
    scaled_source_img_sub,
    img_sub,
    composited_grad,
    recomposited,
    SAVING_PLOT
)
f3_axes[-1].imshow(recomposited)
fig3.show()
