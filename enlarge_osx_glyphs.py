from subprocess import call
from pathlib import Path
from tqdm import tqdm
from random import shuffle
from sys import stderr

path_to_liif_script = Path("../liif/demo.py").resolve().absolute()
path_to_model = Path("../liif/rdn-liif.pth").resolve().absolute()

png_dir = Path("osx/catalina/bg/").absolute()
out_dir = Path("enlarged/").absolute()
pngs = [p for p in png_dir.iterdir() if p.suffix == ".png"]
shuffle(pngs)

processed_count = 0
try:
    for png in tqdm(pngs):
        output_png = out_dir / png.name
        if output_png.exists():
            continue
        call([
            "python", f"{path_to_liif_script}",
            "--input", f"{png}",
            "--model", f"{path_to_model}",
            "--resolution", "2000,2000",
            "--output", f"{output_png}"
        ])
        processed_count += 1
    print(f"Finished after processing {processed_count} PNGs", file=stderr)
except KeyboardInterrupt as e:
    print(f"Aborted while enlarging '{png}' after processing {processed_count} PNGs",
            file=stderr)
