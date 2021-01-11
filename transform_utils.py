import numpy as np
from sys import stderr

def scale_pixel_box_coordinates(box, scale, allow_rounding=False):
    """
    Given the `box` of two pairs of `(x,y)` indicating the top-left and
    bottom-right coordinates of a box in the image, along with a uniform scaling
    `scale` (i.e. applied to both x and y axes).

    """
    #(left_x, top_y), (right_x, bottom_y) = box
    #from_shape = np.array(box).shape
    scaled = box * np.array(scale)
    int_scaled = scaled.astype(int)
    if (int_scaled < scaled).any():
        if allow_rounding:
            w = "rounding down occurred"
            print(f"Warning: {w}", file=stderr)
        else:
            raise ValueError(f"{scale=} for {box=} gives a rounding error:\n{scaled}")
    return int_scaled

def crop_image(img, box):
    (x0, y0), (x1,y1) = box
    return img[y0:y1, x0:x1]
