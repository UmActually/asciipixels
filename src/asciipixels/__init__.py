"""
:Authors: Leonardo Corona Garza
:Version: 0.1.0
:Dedication: To my grandpa.

asciipixels
===========

Generate dynamic ASCII art with images and videos. By Leonardo - UmActually

`asciipixels` is a quick-and-easy library for converting **images** and **videos** to highly customizable ASCII art.

What Is 'Dynamic'
-----------------

What really sets the asciipixels library apart is the **dynamic** functionality. In the functions
``image.dynamic_asciify()`` and ``video.dynamic_asciify()`` some parameters can change over time.
The user can pass **callables** (such as functions and lambdas) that receive the frame number and
return the parameter value.

Basic Usage
-----------

Use the corresponding function depending on your use case:

- ``image.asciify()`` converts image to image. The generated ASCII art is returned as a string and optionally saved in
  a txt.

- ``image.dynamic_asciify()`` converts image to gif or mp4 video. Supports dynamic parameters.

- ``video.asciify()`` converts video to video.

- ``video.dynamic_asciify()`` converts video to video. Supports dynamic parameters.

All four have the **path** of the input file as the first argument. The rest of the arguments all have
**default values**. Something along these lines is enough to get you started:

    >>> import asciipixels as ap
    >>> ap.image.asciify('foo.png')

This will generate a new asciified image named "foo2.png".

It is important to note that **all functions** except ``image.asciify()`` **require** a ``if __name__ == '__main__'``
check in the top level of the user code (_unless_ you are using interactive python on the command line). This is
because the library uses **multiprocessing** to speed up frame generation.

The most important **parameter** to play around with is the ``definition``. It is simply the number of characters in
the **horizontal** axis. Defaults to 100 in all functions.

Also, keep in mind that you can set the **output resolution** of the image/video. The output dimensions approximate
the input dimensions by default, but you can change that with the ``out_width`` argument.

Lastly, if you decide to work with **dark text** on a **light background**, remember to set ``reverse_chars``
to ``True`` in order to correct the pixel-to-ASCII mapping.

The complete list of parameters/arguments of a given primary function can be found in its documentation.
"""

from . import image, video
from .core import *


__version__ = '0.1.0'
