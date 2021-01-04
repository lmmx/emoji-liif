# via https://gist.github.com/tai271828/6f08b24d813355585f613c0c80bd774a
"""Convert TTC font to TTF using fontforge with python extension.
**Warning** The scripts saves splitted fonts in the current working directory.

Usage:
python2 split_ttc_font_to_ttf.py

Preinstallation: apt-get install python-fontforge
"""
import sys

import fontforge

fonts = fontforge.fontsInFile("Apple Color Emoji.ttc")

for font_name in fonts:
    print(font_name)
    #font = fontforge.open('%s(%s)'%(sys.argv[1], font_name))
    #font.generate('%s.ttf'%font_name)
    #font.close()
