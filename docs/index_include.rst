.. module:: score.svg
.. role:: faint
.. role:: confkey

*********
score.svg
*********

Introduction
============

This module manages the scalable vector graphics file :term:`format <template
format>` ``svg`` in :mod:`score.tpl`. It provides three main features:

- converting svg images to png,
- generating :term:`icon elements <icon element>` and
- creating :term:`sprites <sprite>`.


.. _svg_png_conversion:

PNG conversion
--------------

The assets managed by this module can either be rendered as usual (via the
configured :class:`score.tpl.Renderer`) or as ``png`` files. The
:class:`configuration <.ConfiguredSvgModule>` provides all necessary functions
for both uses.

All functions that can render Portable Network Graphics accept an optional
*size* parameter, that allows using a different size than the original image.
Valid values for this parameter are:

- ``auto``: Does not change the size of the image.
- ``100x200``: Scales the image to the given dimensions (width, height),
  ignoring the original aspect ratio.
- ``150%``: Keeps the aspect ratio of the original image and increases both
  dimensions (width, height) to given value.


.. _svg_icons:

Icons
-----

The :mod:`score.svg` module provides various convenience functions for
displaying svg images in web pages.


HTML
````

The module will :meth:`register a function <score.tpl.Renderer.add_function>`
called ``icon`` for html assets with the following signature::

    icon(path, size=None)

Assuming there is an svg file with the :term:`path <asset path>`
``arrow.svg`` and the dimensions 10x20, this function generates the following
HTML code if size is left at its default value::

    <span class="icon icon-arrow"></span>

The module will further register a :term:`virtual css file <virtual asset>`
that provides the following style sheets for the above node::

    .icon {
        display: inline-block;
    }

    .icon-arrow {
        width: 10px;
        height: 20px;
        background:url(/url/to/png-version) no-repeat;
        background-image:url(/url/to/svg-version), none;
    }

These css statements will render the svg file in the background of the node
and will provide a png-fallback for browsers which do not support svg images.

If the size parameter is set, the generated HTML-node will contain all
required style declarations inline, as described below.

CSS
```

Another function with the same name and signature as the HTML version is
available in ``css`` assets::

    icon(path, size=None)

This function will generate the CSS string found in the ``.icon-arrow``
declaration, above:: 

    width: 10px;
    height: 20px;
    background: url(/url/to/arrow.png) no-repeat;
    background-image: url(/url/to/arrow.svg), none;

If the size parameter is set to 20x20, for example, the generated css will
instead look like the following::

    width: 20px;
    height: 20px;
    background: url(/url/to/resized/arrow.png) no-repeat;
    background-image: url(/url/to/arrow.svg), none;
    background-size: 20px 20px;


.. _svg_sprites:

Sprite generation
-----------------

In order to provide a faster experience for users, this module can generate
a :term:`sprite` containing all available svg images. The registered functions
for the :term:`icon elements <icon element>` will then generate different
style sheet declarations. Although the HTML will stay the same, the css
example might look like the following when using sprites::

    .icon {
        display: inline-block;
        background: url(/url/to/sprite.png) no-repeat;
        background-image: url(/url/to/sprite.svg), none;
    }

    .icon-arrow {
        width: 10px;
        height: 20px;
        background-position: -140px 0;
    }


.. _svg_init:

Configuration
=============

.. autofunction:: score.svg.init

.. autoclass:: score.svg.ConfiguredSvgModule
    :members:
        rootdir,
        cachedir,
        paths,
        render_svg,
        render_png,
        render_svg_sprite,
        render_png_sprite
