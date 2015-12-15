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
This package :ref:`integrates <framework_integration>` the module with
pyramid.
"""

import os
from pyramid.request import Request
from score.svg import ConfiguredSvgModule, Svg
from score.init import parse_bool


def init(confdict, configurator, webassets_conf,
         tpl_conf, css_conf, html_conf=None):
    """
    Apart from calling the :func:`basic initializer <score.svg.init>`, this
    function interprets the following *confdict* keys:

    :confkey:`combine` :faint:`[default=False]`
        Whether svg files should be delivered as a single file. If this
        value is `true` (as defined by :func:`score.init.parse_bool`), the
        default url will point to the combined svg sprite.

    :confkey:`dummy_request` :faint:`[default=None]`
        An optional request object to use for creating urls. Will fall back to
        the request object of the :func:`webassets configuration
        <score.webassets.pyramid.init>`.
    """
    import score.svg
    svgconf = score.svg.init(confdict, webassets_conf, tpl_conf, css_conf)
    try:
        combine = parse_bool(confdict['combine'])
    except KeyError:
        combine = False
    try:
        assert isinstance(confdict['dummy_request'], Request)
        dummy_request = confdict['dummy_request']
        webassets_conf.dummy_request.registry = configurator.registry
    except KeyError:
        dummy_request = webassets_conf.dummy_request
    return ConfiguredSvgPyramidModule(configurator, webassets_conf, tpl_conf,
                                      css_conf, svgconf, combine, dummy_request)


class ConfiguredSvgPyramidModule(ConfiguredSvgModule):
    """
    Pyramid-specific configuration of this module.
    """

    def __init__(self, configurator, webconf, tplconf,
                 cssconf, svgconf, combine, dummy_request):
        self.webconf = webconf
        self.tplconf = tplconf
        self.cssconf = cssconf
        self.svgconf = svgconf
        self.combine = combine
        self.dummy_request = dummy_request
        tplconf.renderer.add_function('scss', 'icon',
                                      self.icon_css, escape_output=False)
        tplconf.renderer.add_function('css', 'icon',
                                      self.icon_css, escape_output=False)
        if 'html' in tplconf.renderer.formats:
            tplconf.renderer.add_function('html', 'icon',
                                          self.icon, escape_output=False)
        configurator.add_route('score.svg:single/svg',
                               '/svg/{path:.*\.svg$}')
        configurator.add_route('score.svg:single/png/resized',
                               '/svg/{size}/{path:.*\.png$}')
        configurator.add_route('score.svg:single/png',
                               '/svg/{path:.*\.png$}')
        configurator.add_route('score.svg:combined/svg',
                               '/combined.svg')
        configurator.add_route('score.svg:combined/png',
                               '/combined.png')
        configurator.add_view(self.svg_single,
                              route_name='score.svg:single/svg')
        configurator.add_view(self.png_single,
                              route_name='score.svg:single/png')
        configurator.add_view(self.png_single_resized,
                              route_name='score.svg:single/png/resized')
        configurator.add_view(self.svg_combined,
                              route_name='score.svg:combined/svg')
        configurator.add_view(self.png_combined,
                              route_name='score.svg:combined/png')
        if self.combine:
            @self.cssconf.virtcss
            def icons():
                svgurl = self.url_sprite_svg()
                pngurl = self.url_sprite_png()
                return self.sprite.css(svgurl, pngurl)
        else:
            @self.cssconf.virtcss
            def icons():
                styles = [Svg.common_css]
                for path in self.paths():
                    svg = self.svg(path)
                    svgurl = self.url_single_svg(path)
                    pngurl = self.url_single_png(path)
                    styles.append('.icon-%s{%s}' %
                                  (svg.css_class, svg.css(svgurl, pngurl)))
                return '\n'.join(styles)

    def __getattr__(self, attr):
        return getattr(self.svgconf, attr)

    def svg_response(self, request, svg=None):
        """
        Returns a pyramid response object with the optional *svg* string as its
        body. Will only set the headers, if *svg* is `None`.
        """
        request.response.content_type = 'image/svg+xml; charset=UTF-8'
        if svg:
            request.response.text = svg
        return request.response

    def png_response(self, request, png=None):
        request.response.content_type = 'image/png'
        if png:
            request.response.body = png
        return request.response

    def path2urlpath(self, path):
        """
        Converts a :term:`path <asset path>` to the corresponding path to use
        in URLs.
        """
        urlpath = path
        if not urlpath.endswith('.svg'):
            urlpath = urlpath[:urlpath.rindex('.')]
        assert urlpath.endswith('.svg')
        return urlpath

    def urlpath2path(self, urlpath):
        """
        Converts a *urlpath*, as passed in via the URL, into the actual
        :term:`asset path`.
        """
        assert urlpath.endswith('.svg')
        svgpath = urlpath
        if svgpath in self.virtfiles.paths():
            return svgpath
        if os.path.isfile(os.path.join(self.rootdir, svgpath)):
            return svgpath
        for ext in self.tplconf.renderer.engines:
            file = os.path.join(self.rootdir, svgpath + '.' + ext)
            if os.path.isfile(file):
                return svgpath + '.' + ext
        raise ValueError('Could not determine path for url "%s"' % urlpath)

    def svg_single(self, request):
        """
        Pyramid :term:`route <pyramid:route configuration>` that generates the
        response for a single svg asset.
        """
        urlpath = request.matchdict['path']
        versionmanager = self.webconf.versionmanager
        if versionmanager.handle_pyramid_request('svg', urlpath, request):
            return self.svg_response(request)
        path = self.urlpath2path(urlpath)
        svg = self.render_svg(path)
        return self.svg_response(request, svg)

    def png_single(self, request):
        """
        Pyramid :term:`route <pyramid:route configuration>` that generates the
        response for the png version of a single svg asset.
        """
        urlpath = request.matchdict['path']
        versionmanager = self.webconf.versionmanager
        if versionmanager.handle_pyramid_request('png', os.path.join('auto', urlpath), request):
            return self.png_response(request)
        path = self.urlpath2path(urlpath[:-3] + 'svg')
        png = self.render_png(path)
        return self.png_response(request, png)

    def png_single_resized(self, request):
        """
        Pyramid :term:`route <pyramid:route configuration>` that generates the
        response for the png version of a single svg asset.
        """
        urlpath = request.matchdict['path']
        size = request.matchdict['size']
        versionmanager = self.webconf.versionmanager
        if versionmanager.handle_pyramid_request('png', os.path.join(size, urlpath), request):
            return self.png_response(request)
        path = self.urlpath2path(urlpath[:-3] + 'svg')
        png = self.render_png(path, size)
        return self.png_response(request, png)

    def svg_combined(self, request):
        """
        Pyramid :term:`route <pyramid:route configuration>` that generets the
        response for the combined svg file.
        """
        versionmanager = self.webconf.versionmanager
        if versionmanager.handle_pyramid_request('svg', '__combined__', request):
            return self.svg_response(request)
        return self.svg_response(request, self.render_svg_sprite())

    def png_combined(self, request):
        """
        Pyramid :term:`route <pyramid:route configuration>` that generets the
        response for the combined svg file.
        """
        versionmanager = self.webconf.versionmanager
        if versionmanager.handle_pyramid_request('png', '__combined__', request):
            return self.png_response(request)
        return self.png_response(request, self.render_png_sprite())

    def url_single_svg(self, path):
        """
        Generates the url to a single svg :term:`path <asset path>`.
        """
        urlpath = self.path2urlpath(path)
        renderer = lambda: self.render_svg(path).encode('UTF-8')
        versionmanager = self.webconf.versionmanager
        if path in self.virtfiles.paths():
            hasher = lambda: self.virtfiles.hash(path)
        else:
            file = os.path.join(self.rootdir, path)
            hasher = versionmanager.create_file_hasher(file)
        hash_ = versionmanager.store('svg', urlpath, hasher, renderer)
        _query = {'_v': hash_} if hash_ else None
        genurl = self.dummy_request.route_url
        return genurl('score.svg:single/svg', path=urlpath, _query=_query)

    def url_single_png(self, path):
        """
        Same as :meth:`.url_single_svg`, but will return the url to the png
        version.
        """
        urlpath = self.path2urlpath(path)
        urlpath = urlpath[:-3] + 'png'
        renderer = lambda: self.render_png(path)
        versionmanager = self.webconf.versionmanager
        if path in self.virtfiles.paths():
            hasher = lambda: self.virtfiles.hash(path)
        else:
            file = os.path.join(self.rootdir, path)
            hasher = versionmanager.create_file_hasher(file)
        hash_ = versionmanager.store('png', os.path.join('auto', urlpath),
                                     hasher, renderer)
        _query = {'_v': hash_} if hash_ else None
        genurl = self.dummy_request.route_url
        return genurl('score.svg:single/png', path=urlpath, _query=_query)

    def url_single_png_resized(self, path, size):
        """
        Works very much like :meth:`.url_single_png`, but the returned URL
        will provide a resized png version of the image.
        """
        urlpath = self.path2urlpath(path)
        urlpath = urlpath[:-3] + 'png'
        renderer = lambda: self.render_png(path, size)
        versionmanager = self.webconf.versionmanager
        if path in self.virtfiles.paths():
            hasher = lambda: self.virtfiles.hash(path)
        else:
            file = os.path.join(self.rootdir, path)
            hasher = versionmanager.create_file_hasher(file)
        hash_ = versionmanager.store('png', os.path.join(size, urlpath),
                                     hasher, renderer)
        _query = {'_v': hash_} if hash_ else None
        genurl = self.dummy_request.route_url
        return genurl('score.svg:single/png/resized',
                      path=urlpath, size=size, _query=_query)

    def url_sprite_svg(self):
        """
        Generates the url to the combined svg :term:`sprite`.
        """
        files = []
        vfiles = []
        for path in self.paths():
            if path in self.virtfiles.paths():
                vfiles.append(path)
            else:
                files.append(os.path.join(self.rootdir, path))
        versionmanager = self.webconf.versionmanager
        hashers = [versionmanager.create_file_hasher(files)]
        hashers += [lambda path: self.virtfiles.hash(path) for path in vfiles]
        hash_ = versionmanager.store(
            'svg', '__combined__', hashers,
            lambda: self.render_svg_sprite().encode('UTF-8'))
        _query = {'_v': hash_} if hash_ else None
        genurl = self.dummy_request.route_url
        return genurl('score.svg:combined/svg', _query=_query)

    def url_sprite_png(self):
        """
        Same as :meth:`.url_sprite_svg`, but will return the url to the png
        version.
        """
        files = []
        vfiles = []
        for path in self.paths():
            if path in self.virtfiles.paths():
                vfiles.append(path)
            else:
                files.append(os.path.join(self.rootdir, path))
        versionmanager = self.webconf.versionmanager
        hashers = [versionmanager.create_file_hasher(files)]
        hashers += [lambda path: self.virtfiles.hash(path) for path in vfiles]
        hash_ = versionmanager.store(
            'svg', '__combined__', hashers,
            lambda: self.render_png_sprite().encode('UTF-8'))
        _query = {'_v': hash_} if hash_ else None
        genurl = self.dummy_request.route_url
        return genurl('score.svg:combined/png', _query=_query)

    def icon(self, path, size=None):
        if '.' not in path:
            path += '.svg'
        if self.combine:
            styles = self.sprite.svg_css(path, size)
            return '<span class="icon icon-%s" style="%s"></span>' % \
                (Svg.path2css(path), styles)
        if path in self.virtfiles.paths():
            svg = Svg(path, string=self.virtfiles.render(path))
        else:
            svg = Svg(path, string=self.render_svg(path))
        if not size:
            return '<span class="icon icon-%s"></span>' % svg.css_class
        svgurl = self.url_single_svg(path)
        pngurl = self.url_single_png_resized(path, size)
        styles = svg.css_resized(svgurl, pngurl, size)
        return '<span class="icon icon-%s" style="%s"></span>' % \
            (Svg.path2css(path), styles)

    def icon_css(self, path, size=None):
        if '.' not in path:
            path += '.svg'
        if self.combine and not size:
            svgurl = self.url_sprite_svg()
            pngurl = self.url_sprite_png()
            css = self.sprite.svg_css(path)
            css += 'background:url(%s)no-repeat;' % pngurl
            css += 'background-image:url(%s),none;' % svgurl
            css += 'display:inline-block;'
        else:
            svgurl = self.url_single_svg(path)
            pngurl = self.url_single_png(path)
            if path in self.virtfiles.paths():
                svg = Svg(path, string=self.virtfiles.render(path))
            else:
                svg = Svg(path, string=self.render_svg(path))
            if size:
                return svg.css_resized(svgurl, pngurl, size)
            else:
                return svg.css(svgurl, pngurl)
        return css
