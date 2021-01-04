import fontforge
f = fontforge.open("Apple Color Emoji.ttf")
for name in f:
    filename = name + ".png"
    f[name].export(filename)
