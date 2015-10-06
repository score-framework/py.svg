.. _svg_glossary:

.. glossary::

    icon element
        An HTML element that shows an svg file. The :mod:`score.svg` module can
        create such icon elements automatically with the help of global
        functions for the template formats ``html`` and ``css``. See the
        :mod:`narrative documentation <score.svg>` for details.

    sprite
        Very broadly speaking, a sprite is an image file used as a container
        for other images. If a page has ten 1 kB images, they can be combined
        into one 10 kB sprite, downloaded with a single HTTP request, and then
        positioned with CSS, reducing the number of HTTP requests the client
        needs to render the page.

        The :mod:`score.svg` module can generate sprites automatically from
        different svg files. It also provides the css necessary to position
        the files correctly in an :term:`icon element`.

