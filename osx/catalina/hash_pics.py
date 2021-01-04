from PIL import Image
from imagehash import average_hash

pic_names = ["glyph-u1F40E.png", "horse_1f40e.png"]

def hash_emoji(img_fname):
    img = Image.open(img_fname)
    mini_img = img.resize((12,12))
    hash_val = average_hash(mini_img)
    return hash_val

h1, h2 = [hash_emoji(p) for p in pic_names]
