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
from scipy.ndimage import convolve

SAVING_PLOT = True
JUPYTER = True

osx_dir = Path("osx/catalina/").absolute()
source_dir = osx_dir / "png"
preproc_dir = osx_dir / "bg/"
png_dir = Path("enlarged/").absolute()
out_dir = Path("transparent/").absolute()
png = png_dir / "glyph-u1F343.png"
osx_bw_db = osx_dir / "emoji_bw_calc.db"
NO_OVERWRITE = False

def get_neighbour_mask(arr, max_val=1, neighbour_dist=1):
    """
    Convolve a linear filter (default: 3x3, i.e. 1 neighbour on each side), reflecting
    at the boundaries (i.e. as if convolving on an image expanded by one pixel at each
    border) and then compare the result against the maximum possible value, `max_val`
    (default: 1) from the kernel (i.e. thereby report if a given pixel is completely 
    surrounded by the maximum value).
    """
    kernel_shape = np.repeat(1 + (2 * neighbour_dist), 2)
    kernel = np.ones(kernel_shape)
    kernel_max = kernel.sum() * max_val
    mask = convolve(arr, kernel) == kernel_max
    return mask

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

def plot_fig(
        scaled_source_img_sub_alpha,
        scaled_source_img_sub,
        img_sub,
        composited_grad,
        decomp_alpha,
        recomposited,
        comp_loss,
        pos_loss_mask,
        neg_loss_mask,
        first_adjustment,
        second_adjustment,
        adjusted_recomposited,
        SAVING_PLOT
    ):
    fig, ((ax0, ax1, ax2, ax3, ax4, ax5), (ax6, ax7, ax8, ax9, ax10, ax11)) = plt.subplots(2, 6, sharex=True, sharey=True)
    ax0.imshow(scaled_source_img_sub_alpha)
    ax0.set_title("LR [A]")
    #ax1.imshow(scaled_preproc_img_sub[:,:,:3])
    ax1.imshow(np.zeros_like(scaled_source_img_sub[:,:,:3]))
    ax1.imshow(scaled_source_img_sub)
    ax1.set_title("LR [RGBA]")
    ax2.imshow(img_sub)
    ax2.set_title("SR_c [RGB]")
    ax3.imshow(composited_grad)
    ax3.set_title("Δ(SR_c, LR_c) [RGB]")
    ax4.imshow(decomp_alpha)
    ax4.set_title("Estimate of Δ(SR_c, LR_c) [A]\nbased on Δ(SR_c, LR_c) [RGB]")
    ax5.imshow(recomposited)
    ax5.set_title("Estimated SR [RGB]")
    ax6.imshow(comp_loss)
    ax6.set_title("Δ(Estimated SR, SR_c) [RGB]")
    ax7.imshow(pos_loss_mask)
    ax7.set_title("+ve Δ(Estimated SR, SR_c)")
    ax8.imshow(neg_loss_mask)
    ax8.set_title("-ve Δ(Estimated SR, SR_c)")
    ax9.imshow(first_adjustment)
    ax9.set_title("First re-estimation mask")
    ax10.imshow(second_adjustment)
    ax10.set_title("Second re-estimation mask")
    ax11.imshow(adjusted_recomposited)
    ax11.set_title("Re-estimated SR [RGB]")
    fig.tight_layout()
    if SAVING_PLOT:
        fig.set_size_inches((20,14))
        fig_name = "SR_RGBA_reconstruction_comparison.png"
        fig.savefig(fig_name)
        reload_fig = imread(fig_name)
        fig_s = reload_fig.shape
        y_centre_clip_proportion = 10 # clip 10% either side mid-height
        y_centre = fig_s[0] // 2
        y_ctr_clip = fig_s[0] // y_centre_clip_proportion
        y_ctr_clip_t = y_centre - y_ctr_clip
        y_ctr_clip_b = y_centre + y_ctr_clip
        clip_y_t = fig_s[0] // 6 # ~20% top crop
        clip_y_b = -(fig_s[0] // 6) # ~20% bottom crop
        clip_x_l = fig_s[1] // 20 # ~5% left crop
        clip_x_r = -(fig_s[1] // 50) # ~ 2% right crop
        if y_centre_clip_proportion > 0:
            row_coords = (
                *np.arange(clip_y_t, y_ctr_clip_t),
                *np.arange(y_ctr_clip_b, fig_s[0] + clip_y_b) # clip_y_b is negative
            )
            cropped_fig = reload_fig[row_coords, clip_x_l:clip_x_r]
        else:
            cropped_fig = reload_fig[clip_y_t:clip_y_b, clip_x_l:clip_x_r]
        imwrite(fig_name, cropped_fig)
    else:
        return fig, (ax0, ax1, ax2, ax3, ax4)

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
# Neighbour dist must be greater or equal to half the scaling factor
scaling_factor = 2000 / 160 # 12.5
neighbour_dist = int(scaling_factor // 2 + (0 if scaling_factor % 1 == 0 else 1))
all_max_neighbours_mask = get_neighbour_mask(
    scaled_source_img_sub_alpha,
    max_val=255,
    neighbour_dist=neighbour_dist
)
composited_grad *= (0.5/min_of_previous_max_alpha)
decomp_alpha = (scaled_source_img_sub_alpha / 255)
decomp_alpha[~all_max_neighbours_mask] += composited_grad[~all_max_neighbours_mask, :].mean(axis=1)
decomp_alpha /= decomp_alpha[~all_max_neighbours_mask].max()
decomp_alpha *= 255
decomp_alpha[all_max_neighbours_mask] = 255

decomposited = np.insert(img_sub, 3, decomp_alpha, axis=2)
bg_shade = 0
recomposited = alpha_composite_bg(decomposited, bg_shade)
loss = (img_sub / 2 / 255) - (recomposited / 2 / 255) + 0.5
# The alpha values at `decomp_alpha[loss_mask]` will be changed
loss_mask = np.any(loss != 0.5, axis=2)
# If the loss is uniform across RGB then the loss is grayscale
# however this is ambiguous where the pixels themselves are grayscale
uniform_loss_mask = np.all(loss != 0.5, axis=2)
# This isn't actually uniform it's just uniformly non-zero

# This is the mask of all pixels which are equal (i.e. uniform)
uniform_equal_loss_mask = np.all(np.diff(loss, axis=2) == 0, axis=2)

#gs_pixels = decomposited[uniform_loss_mask][:, :3]
## uniform_loss_mask on grayscale pixels is ambiguous
#ambiguous_ULM = np.zeros_like(uniform_loss_mask)
#ambiguous_ULM_mask = np.diff(gs_pixels,axis=1).sum(axis=1) == 0
#ambiguous_coords_of_ULM = np.argwhere(uniform_loss_mask)[ambiguous_ULM_mask]
#ambiguous_ULM[tuple(ambiguous_coords_of_ULM.T)] = 1
#unambiguous_ULM = uniform_loss_mask & np.invert(ambiguous_ULM)
#partial_loss_mask = loss_mask & np.invert(uniform_loss_mask)
partial_loss_mask = loss_mask & np.invert(uniform_equal_loss_mask)
# 3 subsets of `loss_mask`:
# `ambiguous_ULM`     e.g. ( 10,  10,  10, 59)
# `unambiguous_ULM`   e.g. (  2,   2,   3,  0)
# `partial_loss_mask` e.g. (127, 127, 128, 255)

# (On second thoughts I don't think unambiguous/ambiguous is actually a problem!)

# Also want to see which "direction" the pixel value is in: if it's in the direction of
# the background then add more background (lower alpha) if in the direction of the pixel
# then increase alpha

if bg_shade > 0:
    pos_loss_mask = np.all((bg_shade > decomposited[:,:,:3]), axis=2) & loss_mask
else:
    pos_loss_mask = np.zeros_like(loss_mask, dtype=bool)
if bg_shade < 255:
    neg_loss_mask = np.all((bg_shade < decomposited[:,:,:3]), axis=2) & loss_mask
else:
    neg_loss_mask = np.zeros_like(loss_mask, dtype=bool)

# pos_loss_mask is where alpha is positively correlated to RGB (⇡A = ⇡RGB)
# neg_loss_mask is where alpha is negatively correlated to RGB (⇡A = ⇣RGB)

adjusted_decomposited = decomposited.copy()
adjustment = np.zeros_like(loss)
adjustment[neg_loss_mask] = ((loss[neg_loss_mask] - 0.5) * 255)
#adjustment = adjustment.astype("int")

# Firstly, do the uniform loss mask completely
# Do this by calculating the alpha adjustment needed to obtain the adjustment in RGB
first_adjustment = adjustment.copy()
first_adjustment[~uniform_equal_loss_mask] = 0
# Recall that the goal is to adjust `decomposited` (as `adjusted_decomposited`) to then
# recomposite with the unchanged background colour: so adjust the alpha channel

# Aiming to change loss which is calculated from `img_sub` minus `recomposited` and
# `recomposited` is calculated from linear combination of `decomposited` with `bg_shade`
# so we want to find the value of (R,G,B,A) that when recomposited will give (R+x,G+y,B+z)

# The equation is:
# (1/255) * (α * img + S*(255 - α)) = recomposited + adjustment
# which rearranges for α to become:
# α = (255 * (recomposited + adjustment - S)) / (img - S)
# and since we've deliberately picked parts which have uniform values we can just use
# one dimension of the 3 RGB channels as we know the rest will be the same
alpha_change1 = ((255 * (recomposited[:,:,0].astype(int) + first_adjustment[:,:,0] - bg_shade)) / (img_sub[:,:,0] - bg_shade)) - decomp_alpha
alpha_change1[~uniform_equal_loss_mask] = 0
alpha_change1[np.isnan(alpha_change1)] = 0
alpha_changed_mask1 = alpha_change1 != 0
adjusted_decomposited[alpha_changed_mask1, 3] = adjusted_decomposited[alpha_changed_mask1, 3] + alpha_change1[alpha_changed_mask1]

# Then do the partial loss mask partially
#adjusted_decomposited[uniform_equal_loss_mask] = adjusted_decomposited.astype(int) + first_adjustment
second_adjustment = adjustment.copy()
second_adjustment[~partial_loss_mask] = 0
second_adjustment_min = second_adjustment.astype(int).min(axis=2)

# This time, only go "part of the way" by targetting the minimum
alpha_change2 = ((255 * (recomposited[:,:,0].astype(int) + second_adjustment_min - bg_shade)) / (img_sub[:,:,0] - bg_shade)) - decomp_alpha
alpha_change2[~partial_loss_mask] = 0
alpha_change2[np.isnan(alpha_change2)] = 0
alpha_changed_mask2 = alpha_change2 != 0
adjusted_decomposited[alpha_changed_mask2, 3] = adjusted_decomposited[alpha_changed_mask2, 3] + alpha_change2[alpha_changed_mask2]

adjusted_recomposited = alpha_composite_bg(adjusted_decomposited, bg_shade)

fig3, f3_axes = plot_fig(
    scaled_source_img_sub_alpha,
    scaled_source_img_sub,
    img_sub,
    composited_grad,
    decomp_alpha,
    recomposited,
    loss,
    pos_loss_mask,
    neg_loss_mask,
    first_adjustment.astype(int),
    second_adjustment.astype(int),
    adjusted_recomposited,
    SAVING_PLOT
)
fig3.show()
