from tqdm import tqdm
from pathlib import Path
from imageio import imread, imwrite
import numpy as np

db_filename = "emoji_bw_calc.db"

png_dir = Path("png")
out_dir = Path("alpha")
pngs = [p for p in png_dir.iterdir() if p.is_file() and p.suffix == ".png"]

# Write each PNG's alpha mask ask grayscale RGB PNG
for png in tqdm(pngs):
    out_png = out_dir / png.name
    img = imread(png)
    alpha = img[:,:,3][:, :, np.newaxis].repeat(3, axis=2)
    imwrite(out_png, alpha)
