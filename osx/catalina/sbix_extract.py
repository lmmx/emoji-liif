# via https://tobywf.com/2020/04/extract-emojis-from-ttf-font-png-sbix/
# https://developer.apple.com/fonts/TrueType-Reference-Manual/RM06/Chap6sbix.html
# requires fonttools lib (`pip install fonttools>=4.7.0`)
import sys
from fontTools.ttLib import TTFont

font = TTFont(sys.argv[1])
sbix = font["sbix"]

max_ppem = max(sbix.strikes.keys())
strike = sbix.strikes[max_ppem]

for bitmap in strike.glyphs.values():
    if bitmap.graphicType == "png ":
        filename = f"glyph-{bitmap.glyphName}.png"
        with open(filename, "wb") as f:
            f.write(bitmap.imageData)
