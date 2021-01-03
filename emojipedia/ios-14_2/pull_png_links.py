from bs4 import BeautifulSoup as BS
import requests
from pathlib import Path
from tqdm import tqdm

fn = "index.html"
# index.html is the fully loaded page at https://emojipedia.org/apple/ios-14.2/
with open(fn, "r") as f:
    soup = BS(f, "html5lib")

emoji_images = soup.select("ul.emoji-grid > li > a > img")
for e in tqdm(emoji_images):
    e_url = e.get("src")
    e_path = Path(e_url)
    e_fn = e_path.name
    r = requests.get(e_url)
    with open(e_fn, "wb") as f:
        f.write(r.content)
    #print(f"Saved {e_fn}")
