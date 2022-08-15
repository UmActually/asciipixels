# asciipixels

### Generate dynamic ASCII art with images and videos.

By Leonardo - UmActually

`asciipixels` is a quick-and-easy library for converting **images** and **videos** to highly customizable [**ASCII art**](#cool-but-what-is-ascii-art). The library has four primary functions that do all the asciification work, and save the result as an image, gif, or video: `image.asciify()`, `image.dynamic_asciify()`, `video.asciify()` and `video.dynamic_asciify()`.

For a more granular control of what the program should do, the `CoreAsciifier` class (the class behind the primary asciipixels functions) and wrapper functions for both ImageMagick and FFmpeg are also available.

### What Is 'Dynamic' 

What really sets the asciipixels library apart is the _dynamic_ functionality. In the functions `image.dynamic_asciify()` and `video.dynamic_asciify()` some parameters can change over time. The user can pass **callables** that receive the frame number and return the parameter value, rather than passing the hard-coded value itself. In the example below, the `definition` parameter increases by 16 units every frame. It is modeled by a very simple `lambda` expression.

![Bigweld ASCII Art](https://github.com/UmActually/asciipixels/raw/main/src/asciipixels/resources/example.gif)

### Basic Usage

_Note: asciipixels **depends** on two particular command-line software: **ImageMagick** and **FFmpeg**. If you're a CLI nerd and already have these installed, then go ahead with this guide. If not, go to the [Installation](#installation) section._

Use the corresponding function depending on your use case:

- `image.asciify()` converts image to image. The generated ASCII art is returned as a string and optionally saved in a txt.

- `image.dynamic_asciify()` converts image to gif or mp4 video. Supports dynamic parameters.

- `video.asciify()` converts video to video.

- `video.dynamic_asciify()` converts video to video. Supports dynamic parameters.

All four have the `path` of the input file as the first argument. The rest of the arguments all have **default values**. Something along these lines is enough to get you started:

```python
import asciipixels as ap
ap.image.asciify('foo.png')
```

This will generate a new asciified image named `foo2.png`.

It is important to note that **all functions** except `image.asciify()` **require** a `if __name__ == '__main__'` check in the top level of the user code (_unless_ you are using interactive python on the command line). This is because the library uses **multiprocessing** to speed up frame generation. So, in order to asciify a video, for example, you can do the following:

```python
import asciipixels as ap
if __name__ == '__main__':
    ap.video.asciify('foo.mp4')
```

The most important **parameter** to play around with is the `definition`. It is simply the number of characters in the **horizontal** axis. Defaults to 100 in all functions. Set it too high and the ASCII art will just look like art. Set it too low and it will just look like ASCII.

Also, keep in mind that you can set the **output resolution** of the image/video. The output dimensions approximate the input dimensions by default, but you can change that with the `out_width` argument.

Lastly, if you decide to work with **dark text** on a **light background**, remember to set `reverse_chars` to `True` in order to correct the pixel-to-ASCII mapping.

As a final example, I made the Bigweld gif in the [What Is 'Dynamic'](#what-is-dynamic) section with the following code:

```python
import asciipixels as ap

if __name__ == '__main__':
    ap.image.dynamic_asciify(
        'ceo.png',
        bg_color=255,
        txt_color=0,
        definition=lambda f: f * 16,
        fps=2,
        frame_count=7,
        out_width=1000,
        reverse_chars=True
    )
```

The complete list of parameters/arguments of a given primary function can be found in its documentation.

---

## Installation

To install asciipixels, use **pip** in the terminal:

**Windows**
```commandline
pip install asciipixels
```

**macOS / Linux**
```commandline
python3 -m pip install asciipixels
```

Asciipixels has two **dependencies** that aren't installed automatically. These are **ImageMagick**, for image manipulation, and **FFmpeg**, for video and audio manipulation. You can download them from their **official sites** or by using **Homebrew** (if applicable).

[Install ImageMagick Here](https://imagemagick.org/script/download.php)

[Install FFmpeg Here](https://ffmpeg.org/download.html)

---

## Cool, But What Is ASCII Art

ASCII art is simply the representation of images (or video) with **characters** and letters. This art can be composed by using characters that match either the **brightness** or **contour** of a part of an image. This library works with the brightness aspect.
