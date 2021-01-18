# emoji-liif

Emoji upsampling workflow using LIIF

## Preprocessing

All TTF glyphs were matched to the emojipedia reference images (excluding one 'hidden' glyph),
with the assistance of image hashing functions (however these are not used in the final version,
instead name matching rules were used to correspond icons to the original glyphs).

## Results

The results are nice from 160x160 PNGs extracted from the font TTF.

![](emoji-liif-twitter-thread.png)

> See [this thread](https://twitter.com/permutans/status/1345484017609691136) on Twitter for some examples

However, to call this complete I'd want to recover equivalent PNGs, including transparency,
and for this alpha decomposition is required.

This turned out to be tricky!

Attempting to run the alpha channel through LIIF failed to recover a mask matching the
superresolved glyph (RGB channels) so instead I'm planning to estimate it from the RGB:

![](alpha_composite_comparison.png)

> Figure generated from 🍃 ([`U+1F343`](osx/catalina/glyph-u1F343.png))
> by [`restore_alpha_to_enlarged_subview.py`](restore_alpha_to_enlarged_subview.py)

![](alpha_composite_comparison_2x2.png)

> Closer up generated by [`restore_alpha_to_enlarged_2x2_subview.py`](restore_alpha_to_enlarged_2x2_subview.py)

The [alpha channel estimation](Bad_SR_transparency_estimate.ipynb) results were pretty poor (TODO)

![](nb/SR_transparency_estimate.png)

After doing a fair bit of closer inspection I still can't figure out precisely how to "pull up" the
pixels that get given an alpha too low (and guessing too naively would degrade the result).
Perhaps 50% of the way there after restating the problem as minimising the loss after re-alpha compositing,
and carrying out the re-estimation in 2 passes (once for pixels with a "uniform loss" e.g. pixel RGB
differences of `(10,10,10)`, and a second for pixels with a "partial loss" e.g. RGB difference of
`(11,12,13)` for which only the minimum (11) would be re-calibrated -- as all backgrounds are
grayscale).

![](SR_RGBA_reconstruction_comparison.png)

> A further attempt to recover the SR image generated by [`reestimate_leaf_sr_transparency.py`](reestimate_leaf_sr_transparency.py)
> resulting in an improvement but not a perfect fix (yet)

![](SR_RGBA_further_reconstruction_comparison.png)

> Here's the beginning of a second pass (from which it can be seen that the first pass didn't fully
> resolve the pixels in the loss mask, _bottom left_, which is less intense but still not uniformly grey).
> Generated by [`further_reestimate_leaf_sr_transparency.py`](further_reestimate_leaf_sr_transparency.py)

Yinbo Chen, first author of the LIIF paper,
[says](https://github.com/yinboc/liif/issues/12#issuecomment-761765468):

> I am not very familiar with the processing of alpha channel. Since the model is only trained for
> RGB images, the alpha channel will make it an out-of-distribution task. If there are a large
> amount of LR-HR pairs of images with alpha channel, a straight-forward method is to modify the
> code to work on 4-channel images (since all the code assume 3-channel, there can be many necessary
> modifications such as the encoder model part and the data normalization part) and train a
> 4-channel SR model.

TODO...

## Workflow

- Image thumbnails (transparent PNGs) are converted to nontransparent by selecting a colour not used
  in the image and flattening with this as a background colour (either in Python, or imagemagick `convert`)
  - Upon calculation, the RGB value of this alpha colour is stored in a database
- Image thumbnails are upsampled (i.e. enlarged) using LIIF
- The resulting large (2000x2000) 'high resolution' images are restored to transparency by removing
  the alpha colour [retrieved from the database]

## TODO

- [#2:](https://github.com/lmmx/emoji-liif/issues/2) add background info on the LIIF method

## Source image provenance

The two emoji image sets are sourced from:

- Emojipedia (iOS 14.2) 72x72 PNG
- OSX 10.15 (Catalina) 160x160 PNG

## Copyright

All credit and copyright belongs to Apple for the iOS/OSX emoji character images, reproduced here
under fair use and for noncommercial purposes.

Emojipedia's _[Emoji Image Licensing](https://emojipedia.org/licensing/)_ page states:

> To the best of our knowledge, specific information about licensing emojis from Apple... is not publicly available.
> 
> Unless otherwise stated, emoji images are © copyright, and enquiries about commercial
> licensing of emoji images should be directed to their respective font vendors.

They also link to [a 2017 blog post, _“Who Owns Emoji?”_](https://blog.emojipedia.org/who-owns-emoji/), which states:

> Apple has not made licensing options publicly available for Apple Color Emoji.
> 
> As such, those wanting to use Apple’s emoji images may be restricted to using these images in a way
> that could be considered fair use.

[Conventional reading](https://guides.nyu.edu/fairuse) of fair use includes such purposes as:

> "limited use of copyrighted material without permission for purposes such as criticism,
> parody, news reporting, research and scholarship, and teaching."
