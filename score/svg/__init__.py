# Copyright © 2015 STRG.AT GmbH, Vienna, Austria
#
# This file is part of the The SCORE Framework.
#
# The SCORE Framework and all its parts are free software: you can redistribute
# them and/or modify them under the terms of the GNU Lesser General Public
# License version 3 as published by the Free Software Foundation which is in the
# file named COPYING.LESSER.txt.
#
# The SCORE Framework and all its parts are distributed without any WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. For more details see the GNU Lesser General Public
# License.
#
# If you have not received a copy of the GNU Lesser General Public License see
# http://www.gnu.org/licenses/.
#
# The License-Agreement realised between you as Licensee and STRG.AT GmbH as
# Licenser including the issue of its valid conclusion and its pre- and
# post-contractual effects is governed by the laws of Austria. Any disputes
# concerning this License-Agreement including the issue of its valid conclusion
# and its pre- and post-contractual effects are exclusively decided by the
# competent court, in whose district STRG.AT GmbH has its registered seat, at
# the discretion of STRG.AT GmbH also the competent court, in whose district the
# Licensee has his registered seat, an establishment or assets.

"""
This module manages the scalable vector graphics file :term:`format <template
format>` ``svg`` in :mod:`score.tpl`. It provides three main features:

- converting svg images to png,
- generating :term:`icon element`s and
- creating :term:`sprite`s.

See the :ref:`narrative documentation <svg_toplevel>` for a more in-depth
documentation of each feature.
"""

import io
import json
import logging
import os
import re
import xml.etree.ElementTree as ET

from score.init import init_cache_folder, ConfiguredModule
from score.tpl import TemplateConverter
from score.webassets import VirtualAssets


log = logging.getLogger(__name__)


defaults = {
    'rootdir': None,
    'cachedir': None,
    'combine': False,
}


def init(confdict, webassets_conf, tpl_conf, css_conf):
    """
    Initializes this module acoording to :ref:`our module initialization
    guidelines <module_initialization>` with the following configuration keys:

    :confkey:`rootdir` :faint:`[default=None]`
        Denotes the root folder containing all svg files. Will fall back to a
        sub-folder of the folder in :mod:`score.tpl`'s configuration, as
        described in :func:`score.tpl.init`.

    :confkey:`cachedir` :faint:`[default=None]`
        A dedicated cache folder for this module. It is generally sufficient
        to provide a ``cachedir`` for :mod:`score.tpl`, as this module will
        use a sub-folder of that by default.
    """
    conf = dict(defaults.items())
    conf.update(confdict)
    if not conf['cachedir'] and webassets_conf.cachedir:
        conf['cachedir'] = os.path.join(webassets_conf.cachedir, 'svg')
    if conf['cachedir']:
        init_cache_folder(conf, 'cachedir', autopurge=True)
    return ConfiguredSvgModule(tpl_conf, conf['rootdir'], conf['cachedir'])


class ConfiguredSvgModule(ConfiguredModule, TemplateConverter):
    """
    This module's :class:`configuration object
    <score.init.ConfiguredModule>`.
    """

    def __init__(self, tpl_conf, rootdir, cachedir):
        super().__init__(__package__)
        self.tpl_conf = tpl_conf
        tpl_conf.renderer.register_format('svg', rootdir, cachedir, self)
        self.virtfiles = VirtualAssets()
        self.virtsvg = self.virtfiles.decorator('svg')

    @property
    def rootdir(self):
        """
        The configured root folder of svg files.
        """
        return self.tpl_conf.renderer.format_rootdir('svg')

    @property
    def cachedir(self):
        """
        The configured root folder of svg files.
        """
        return self.tpl_conf.renderer.format_cachedir('svg')

    def paths(self, includehidden=False):
        """
        Provides a list of all svg files found in the js root folder as
        :term:`paths <asset path>`, as well as the paths of all :term:`virtual
        svg files <virtual asset>`.
        """
        return self.tpl_conf.renderer.paths('svg', self.virtfiles,
                                            includehidden)

    @property
    def sprite(self):
        """
        Provides the :class:`.Sprite` object for this configuration.
        """
        return Sprite(self)

    def svg(self, path):
        """
        Provides an :class:`.Svg` object for given path. Caching behaviour is
        the same as in :attr:`.sprite`.
        """
        if path.endswith('.svg'):
            return Svg(path, file=os.path.join(self.rootdir, path))
        return Svg(path, string=self.tpl_conf.renderer.render_file(path))

    def render_svg(self, path):
        """
        Retuns the content of the file denoted by :term:`path <asset path>`.
        """
        return self.svg(path).content

    def render_png(self, path, size=None):
        """
        Renders the svg file with given :term:`path <asset path>` in the
        Portable Network Graphics (png) file format.
        """
        return svg2png(self.svg(path), size)

    def render_svg_sprite(self):
        """
        Renders the :term:`sprite` of this configuration in the svg file
        format.
        """
        return self.sprite.content

    def render_png_sprite(self, size=None):
        """
        Same as :meth:`.render_svg_sprite`, but returns a png, thus a `bytes`
        object.
        """
        return svg2png(self.sprite, size)

    convert_file = render_svg


def svg2png(svg, size=None):
    """
    Converts an :class:`.Svg` or :class:`.Sprite` object to the png file
    format. The return value is thus `bytes`.

    It is possible to render the image in a different *size*.
    See the :ref:`narrative documentation <svg_png_conversion>` for a list
    of implemented *size* formats.
    """
    from cairosvg import svg2png
    from PIL import Image
    import io
    png = svg2png(bytestring=svg.content.encode('ASCII'))
    if not size or size == 'auto':
        return png
    wh_match = Svg.wh_regex.match(size)
    percent_match = Svg.percent_regex.match(size)
    if wh_match:
        w, h = list(map(int, wh_match.group(1, 2)))
    elif percent_match:
        percent = float(percent_match.group(1))
        w, h = svg.width * percent / 100, svg.height * percent / 100
    else:
        raise ValueError('Unsupported size string: ' + size)
    img = Image.open(io.BytesIO(png))
    img.thumbnail((w, h))
    output = io.BytesIO()
    img.save(output, format='PNG')
    return output.getvalue()


class Svg:
    """
    X
    """

    wh_regex = re.compile(r'(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)$')
    percent_regex = re.compile(r'(\d+(?:\.\d+)?)%$')

    common_css = '.icon{display:inline-block}'

    @staticmethod
    def path2css(path):
        return path[:path.find('.')].replace('/', '-')

    def __init__(self, path, *, file=None, string=None):
        assert file or string
        assert not (file and string)
        self.file = file
        self.string = string
        self.path = path
        self._wh = None

    @property
    def content(self):
        """
        The actual ``svg`` content.
        """
        if self.string:
            return self.string
        return open(self.file, 'r').read()

    @property
    def width(self):
        """
        Width of this image.
        """
        w, _ = self._width_height
        return w

    @property
    def height(self):
        """
        Height of this image.
        """
        _, h = self._width_height
        return h

    @property
    def _width_height(self):
        if self._wh:
            return self._wh
        root = self.xml_root()
        try:
            x, y, w, h = re.split(r'\s+', root.attrib['viewBox'])
            width = float(w) - float(x)
            height = float(h) - float(y)
        except KeyError:
            width, height = root.attrib['width'], root.attrib['height']
            width = float(width.replace('px', ''))
            height = float(height.replace('px', ''))
        self._wh = width, height
        return width, height

    def xml_root(self):
        """
        Provides an :class:`xml.etree.ElementTree.Element` to the root node of
        this svg file.
        """
        if self.string:
            return ET.fromstring(self.string)
        return ET.parse(self.file).getroot()

    @property
    def css_class(self):
        return Svg.path2css(self.path)

    def wh_multipliers(self, size):
        """
        Given a *size* specification, this function will return multipliers
        for the width and height of this image to meet the target size as a
        2-tuple.

        if this, for example, a 10x20 image, a call to wh_multipliers(20x10)
        will return ``(2, 0.5)``.

        See the :ref:`narrative documentation <svg_png_conversion>` for a list
        of implemented *size* formats.
        """
        if not size or size == 'auto':
            return 1, 1
        match = Svg.wh_regex.match(size)
        if match:
            w, h = match.group(1, 2)
            widthmult = (float(w) / self.width)
            heightmult = (float(h) / self.height)
            return widthmult, heightmult
        match = Svg.percent_regex.match(size)
        if match:
            widthmult = 1 + float(match.group(1)) / 100
            heightmult = 1 + float(match.group(1)) / 100
            return widthmult, heightmult
        raise ValueError('Unsupported size string: ' + size)

    def css(self, svgurl, pngurl):
        """
        Provides cascading stylesheets for rendering this image inside a
        dedicated HTML node.

        .. todo::
            Describe the whole css thing somewhere.
        """
        css = 'width:%dpx;height:%dpx;' % (self.width, self.height)
        css += 'background:url(%s)no-repeat;' % pngurl
        css += 'background-image:url(%s),none;' % svgurl
        return css

    def css_resized(self, svgurl, pngurl, size):
        widthmult, heightmult = self.wh_multipliers(size)
        wh = (self.width * widthmult, self.height * heightmult)
        css = "width:{0}px;height:{1}px;".format(*wh)
        css += 'background:url(%s)no-repeat;' % pngurl
        css += 'background-image:url(%s),none;' % svgurl
        css += "background-size:{0}px {1}px;".format(*wh)
        return css


class Sprite:
    """
    X
    """

    def __init__(self, conf):
        self.conf = conf
        if self._load_cache():
            return
        self.svg_dimensions = {}
        self.svg_offsets = {}
        offset = 0
        self.height = 0
        for path in self.conf.paths():
            svg = Svg(path, file=os.path.join(conf.rootdir, path))
            self.svg_dimensions[path] = (svg.height, svg.width)
            self.svg_offsets[path] = offset
            offset -= svg.width
            self.height = max(self.height, svg.height)
        self.width = -offset
        self._write_cache()

    def _write_cache(self):
        if not self.conf.cachedir:
            return False
        meta = os.path.join(self.conf.cachedir, '__sprite__.meta')
        js = (self.width, self.height), self.svg_dimensions, self.svg_offsets
        open(meta, 'w').write(json.dumps(js))
        cachefile = os.path.join(self.conf.cachedir, '__sprite__.svg')
        open(cachefile, 'w').write(self._generate_content())
        return True

    def _load_cache(self):
        if not self.conf.cachedir:
            return False
        meta = os.path.join(self.conf.cachedir, '__sprite__.meta')
        if not os.path.isfile(meta):
            return False
        my_dimensions, svg_dimensions, svg_offsets = \
            json.loads(open(meta, 'r').read())
        if set(svg_dimensions.keys()) != set(self.conf.paths()):
            return False
        cachemtime = os.path.getmtime(meta)
        for path in svg_dimensions:
            file = os.path.join(self.conf.rootdir, path)
            if os.path.getmtime(file) >= cachemtime:
                return False
        self.height, self.width = my_dimensions[0], my_dimensions[1]
        self.svg_dimensions = svg_dimensions
        self.svg_offsets = svg_offsets
        return True

    def css(self, svgurl, pngurl):
        css = '.icon{'
        css += 'display:inline-block;'
        css += 'background:url(%s)no-repeat;' % pngurl
        css += 'background-image:url(%s),none}\n' % svgurl
        for path in self.conf.paths():
            css += '.icon-%s{%s}\n' % (Svg.path2css(path), self.svg_css(path))
        return css

    def svg_css(self, path, size=None):
        wmult, hmult = 1, 1
        if size:
            svg = Svg(path, file=os.path.join(self.conf.rootdir, path))
            wmult, hmult = svg.wh_multipliers(size)
        dim = self.svg_dimensions[path]
        w, h = dim[1] * wmult, dim[0] * hmult
        offset = self.svg_offsets[path] * wmult
        css = 'width:%dpx;height:%dpx;' % (w, h)
        css += 'background-position:%dpx 0;' % offset
        if size:
            css += 'background-size:%dpx %dpx' % (self.width * wmult,
                                                  self.height * hmult)
        return css

    @property
    def content(self):
        if self.conf.cachedir:
            cachefile = os.path.join(self.conf.cachedir, '__sprite__.svg')
            try:
                return open(cachefile, 'r').read()
            except FileNotFoundError:
                pass
        return self._generate_content()

    def _generate_content(self):
        result = ET.Element('svg', {
            'version': '1.1',
        })
        result.set('width', str(self.width))
        result.set('height', str(self.height))
        for path in self.conf.paths():
            svg = self.conf.tpl_conf.renderer.render_file(path)
            svg = Svg(path, string=svg)
            root = svg.xml_root()
            root.attrib['id'] = svg.css_class
            if self.svg_offsets[path]:
                translate = 'translate(%d)' % -self.svg_offsets[path]
                try:
                    transform = root.attrib['transform']
                    root.attrib['transform'] = translate + ' ' + transform
                except KeyError:
                    root.attrib['transform'] = translate
            result.append(root)
        result = ET.ElementTree(result)
        ET.register_namespace('', 'http://www.w3.org/2000/svg')
        with io.StringIO() as buf:
            buf.write(
                '<?xml version="1.0" standalone="no"?>\n'
                '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" \n'
                '  "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">\n'
            )
            result.write(buf, encoding='unicode', xml_declaration=False)
            return buf.getvalue()
