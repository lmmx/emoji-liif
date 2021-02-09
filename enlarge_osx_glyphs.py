from subprocess import call
from pathlib import Path
from tqdm import tqdm
from random import shuffle
from sys import stderr
from batch_multiprocessing import batch_multiprocess
from functools import partial

path_to_liif_script = Path("../liif/demo.py").resolve().absolute()
path_to_model = Path("../liif/rdn-liif.pth").resolve().absolute()

USE_MULTI_CORE = True

png_dir = Path("osx/catalina/bg/").absolute()
out_dir = Path("enlarged/").absolute()
pngs = [p for p in png_dir.iterdir() if p.suffix == ".png"]
shuffle(pngs)

out_resolution = "2000,2000"

if USE_MULTI_CORE:
    liif_calls = []
    for png in pngs:
        output_png = out_dir / png.name
        if output_png.exists():
            continue
        call_liif = partial(
            call,
            [
                "python", f"{path_to_liif_script}",
                "--input", f"{png}",
                "--model", f"{path_to_model}",
                "--resolution", out_resolution,
                "--output", f"{output_png}"
            ]
        )
        liif_calls.append(call_liif)
    try:
        batch_multiprocess(liif_calls, n_cores=10)
    except KeyboardInterrupt as e:
        print(f"Exitting early...", file=stderr)
else:
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
                "--resolution", out_resolution,
                "--output", f"{output_png}"
            ])
            processed_count += 1
        print(f"Finished after processing {processed_count} PNGs", file=stderr)
    except KeyboardInterrupt as e:
        print(f"Aborted while enlarging '{png}' after processing {processed_count} PNGs",
                file=stderr)
