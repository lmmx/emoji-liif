First, you need the file "Apple Color Emoji.ttc" which is a collection of TTF fonts named:

- `Apple Color Emoji`
- `.Apple Color Emoji UI`

(or if this isn't their names it was something quite similar)

Extract them by running

```sh
python ttc2ttf.py Apple\ Color\ Emoji.ttc
```

This will ignore the names of the fonts (which `fontforge` can see, but that requires Python 2
and doesn't read colour glyphs so it's not worth going there TBH), instead you'll just get files

- `Apple Color Emoji0.ttf`
- `Apple Color Emoji1.ttf`

These are the fonts named above, and the `.` at the start of the name of the 2nd one (extracted
as a file ending in `1.ttf`), the one whose name ends in UI, means that it's a hidden file,
so I presume the other is the "main" one in some way and the latter is to be ignored...

- I'm not sure what the UI stands for but you see it in Segoe UI etc., and both of these
  TTF files have 3241 glyphs (open with the Linux font inspector to see more info).

Now that the TTF files have been extracted, I went ahead and renamed them

```sh
mv "Apple Color Emoji0.ttf" "Apple Color Emoji.ttf"
mv "Apple Color Emoji1.ttf" ".Apple Color Emoji UI.ttf"
```

Then you simply extract the [sbix](https://developer.apple.com/fonts/TrueType-Reference-Manual/RM06/Chap6sbix.html) table
by running `python sbix_extract.py "Apple Color Emoji.ttf"` (which it turns out was written for the
same font file I'm trying to extract!) and all the PNG files will be written to the current
directory.

Then simply

```sh
mkdir png
mv *.png png/
```

and all the extracted PNG files will be stored there.

(The next step is to match these to the ones in the emojipedia directory)
