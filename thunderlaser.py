#! /usr/bin/python3
#
# thunderlaser.py -- driver for exporting an SVG drawing as an RDCAM file for a Thunderlaser RUIDA machine.
#
# This is an Inkscape extension to output paths in rdcam format.
# recursivelyTraverseSvg() is originally from eggbot. Thank!
# inkscape-paths2openscad and inkscape-silhouette contain copies of recursivelyTraverseSvg()
# with almost identical features, but different inmplementation details. The version used here is derived from
# inkscape-paths2openscad.
#
# python2 compatibility:
from __future__ import print_function

import sys

sys_platform = sys.platform.lower()
if sys_platform.startswith('win'):
  sys.path.append('C:\Program Files\Inkscape\share\extensions')
elif sys_platform.startswith('darwin'):
  sys.path.append('~/.config/inkscape/extensions')
else:   # Linux
  sys.path.append('/usr/share/inkscape/extensions/')


#! /usr/bin/python
#
# inksvg.py - parse an svg file into a plain list of paths.
#
# (C) 2017 juergen@fabmail.org, authors of eggbot and others.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#################
# 2017-12-04 jw, v1.0  Refactored class InkSvg from cookiecutter extension
# 2017-12-07 jw, v1.1  Added roundedRectBezier()
# 2017-12-10 jw, v1.3  Added styleDasharray() with stroke-dashoffset

import inkex
import simplepath
import simplestyle
import simpletransform
import cubicsuperpath
import cspsubdiv
import bezmisc

import gettext
import re

class InkSvg():
    """
    """
    __version__ = "1.3"
    DEFAULT_WIDTH = 100
    DEFAULT_HEIGHT = 100

    def styleDasharray(self, path_d, node):
        """
        Check the style of node for a stroke-dasharray, and apply it to the
        path d returning the result.  d is returned unchanged, if no
        stroke-dasharray was found.

        ## Extracted from inkscape extension convert2dashes; original
        ## comments below.
        ## Added stroke-dashoffset handling, made it a universal operator
        ## on nodes and 'd' paths.

        This extension converts a path into a dashed line using 'stroke-dasharray'
        It is a modification of the file addnodes.py

        Copyright (C) 2005,2007 Aaron Spike, aaron@ekips.org
        Copyright (C) 2009 Alvin Penner, penner@vaxxine.com
        """

        def tpoint((x1,y1), (x2,y2), t = 0.5):
            return [x1+t*(x2-x1),y1+t*(y2-y1)]
        def cspbezsplit(sp1, sp2, t = 0.5):
            m1=tpoint(sp1[1],sp1[2],t)
            m2=tpoint(sp1[2],sp2[0],t)
            m3=tpoint(sp2[0],sp2[1],t)
            m4=tpoint(m1,m2,t)
            m5=tpoint(m2,m3,t)
            m=tpoint(m4,m5,t)
            return [[sp1[0][:],sp1[1][:],m1], [m4,m,m5], [m3,sp2[1][:],sp2[2][:]]]
        def cspbezsplitatlength(sp1, sp2, l = 0.5, tolerance = 0.001):
            bez = (sp1[1][:],sp1[2][:],sp2[0][:],sp2[1][:])
            t = bezmisc.beziertatlength(bez, l, tolerance)
            return cspbezsplit(sp1, sp2, t)
        def cspseglength(sp1,sp2, tolerance = 0.001):
            bez = (sp1[1][:],sp1[2][:],sp2[0][:],sp2[1][:])
            return bezmisc.bezierlength(bez, tolerance)

        style = simplestyle.parseStyle(node.get('style'))
        if not style.has_key('stroke-dasharray'):
            return path_d
        dashes = []
        if style['stroke-dasharray'].find(',') > 0:
            dashes = [float (dash) for dash in style['stroke-dasharray'].split(',') if dash]
        if not dashes:
            return path_d

        dashoffset = 0.0
        if style.has_key('stroke-dashoffset'):
            dashoffset = float(style['stroke-dashoffset'])
            if dashoffset < 0.0: dashoffset = 0.0
            if dashoffset > dashes[0]: dashoffset = dashes[0]   # avoids a busy-loop below!

        p = cubicsuperpath.parsePath(path_d)
        new = []
        for sub in p:
            idash = 0
            dash = dashes[0]
            print("initial dash length: ", dash, dashoffset)
            dash = dash - dashoffset
            length = 0
            new.append([sub[0][:]])
            i = 1
            while i < len(sub):
                dash = dash - length
                length = cspseglength(new[-1][-1], sub[i])
                while dash < length:
                    new[-1][-1], next, sub[i] = cspbezsplitatlength(new[-1][-1], sub[i], dash/length)
                    if idash % 2:           # create a gap
                        new.append([next[:]])
                    else:                   # splice the curve
                        new[-1].append(next[:])
                    length = length - dash
                    idash = (idash + 1) % len(dashes)
                    dash = dashes[idash]
                if idash % 2:
                    new.append([sub[i]])
                else:
                    new[-1].append(sub[i])
                i+=1
        return cubicsuperpath.formatPath(new)

    def roundedRectBezier(self, x, y, w, h, rx, ry=0):
        """
        Draw a rectangle of size w x h, at start point x, y with the corners rounded by radius
        rx and ry. Each corner is a quarter of an ellipsis, where rx and ry are the horizontal
        and vertical dimenstion.
        A pathspec according to https://www.w3.org/TR/SVG/paths.html#PathDataEllipticalArcCommands
        is returned. Very similar to what inkscape would do when converting object to path.
        Inkscape seems to use a kappa value of 0.553, higher precision is used here.

        x=0, y=0, w=200, h=100, rx=50, ry=30 produces in inkscape
        d="m 50,0 h 100 c 27.7,0 50,13.38 50,30 v 40 c 0,16.62 -22.3,30 -50,30
           H 50 C 22.3,100 0,86.62 0,70 V 30 C 0,13.38 22.3,0 50,0 Z"
        It is unclear, why there is a Z, the last point is identical with the first already.
        It is unclear, why half of the commands use relative and half use absolute coordinates.
        We do it all in relative coords, except for the initial M, and we ommit the Z.
        """
        if rx < 0: rx = 0
        if rx > 0.5*w: rx = 0.5*w
        if ry < 0: ry = 0
        if ry > 0.5*h: ry = 0.5*h
        if ry < 0.0000001: ry = rx
        k = 0.5522847498307933984022516322796     # kappa, handle length for a 4-point-circle.
        d  = "M %f,%f h %f " % (x+rx, y, w-rx-rx)                      # top horizontal to right
        d += "c %f,%f %f,%f %f,%f " % (rx*k,0, rx,ry*(1-k), rx,ry)     # top right ellipse
        d += "v %f " % (h-ry-ry)                                       # right vertical down
        d += "c %f,%f %f,%f %f,%f " % (0,ry*k, rx*(k-1),ry, -rx,ry)    # bottom right ellipse
        d += "h %f " % (-w+rx+rx)                                      # bottom horizontal to left
        d += "c %f,%f %f,%f %f,%f " % (-rx*k,0, -rx,ry*(k-1), -rx,-ry) # bottom left ellipse
        d += "v %f " % (-h+ry+ry)                                      # left vertical up
        d += "c %f,%f %f,%f %f,%f" % (0,-ry*k, rx*(1-k),-ry, rx,-ry)   # top left ellipse
        return d


    def subdivideCubicPath(self, sp, flat, i=1):
        '''
        [ Lifted from eggbot.py with impunity ]

        Break up a bezier curve into smaller curves, each of which
        is approximately a straight line within a given tolerance
        (the "smoothness" defined by [flat]).

        This is a modified version of cspsubdiv.cspsubdiv(): rewritten
        because recursion-depth errors on complicated line segments
        could occur with cspsubdiv.cspsubdiv().
        '''

        while True:
            while True:
                if i >= len(sp):
                    return

                p0 = sp[i - 1][1]
                p1 = sp[i - 1][2]
                p2 = sp[i][0]
                p3 = sp[i][1]

                b = (p0, p1, p2, p3)

                if cspsubdiv.maxdist(b) > flat:
                    break

                i += 1

            one, two = bezmisc.beziersplitatt(b, 0.5)
            sp[i - 1][2] = one[1]
            sp[i][0] = two[2]
            p = [one[2], one[3], two[1]]
            sp[i:1] = [p]

    def parseLengthWithUnits(self, str, default_unit='px'):
        '''
        Parse an SVG value which may or may not have units attached
        This version is greatly simplified in that it only allows: no units,
        units of px, and units of %.  Everything else, it returns None for.
        There is a more general routine to consider in scour.py if more
        generality is ever needed.
        With inkscape 0.91 we need other units too: e.g. svg:width="400mm"
        '''

        u = default_unit
        s = str.strip()
        if s[-2:] in ('px', 'pt', 'pc', 'mm', 'cm', 'in', 'ft'):
            u = s[-2:]
            s = s[:-2]
        elif s[-1:] in ('m', '%'):
            u = s[-1:]
            s = s[:-1]

        try:
            v = float(s)
        except:
            return None, None

        return v, u


    def __init__(self, document, smoothness=0.0):
        self.dpi = 90.0                 # factored out for inkscape-0.92
        self.px_used = False            # raw px unit depends on correct dpi.
        self.xmin, self.xmax = (1.0E70, -1.0E70)
        self.ymin, self.ymax = (1.0E70, -1.0E70)

        self.document = document        # from  inkex.Effect.parse()
        self.smoothness = smoothness    # 0.0001 .. 5.0

        # Dictionary of paths we will construct.  It's keyed by the SVG node
        # it came from.  Such keying isn't too useful in this specific case,
        # but it can be useful in other applications when you actually want
        # to go back and update the SVG document
        self.paths = {}

        # For handling an SVG viewbox attribute, we will need to know the
        # values of the document's <svg> width and height attributes as well
        # as establishing a transform from the viewbox to the display.

        self.docWidth = float(self.DEFAULT_WIDTH)
        self.docHeight = float(self.DEFAULT_HEIGHT)
        self.docTransform = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]

        # Dictionary of warnings issued.  This to prevent from warning
        # multiple times about the same problem
        self.warnings = {}

    def getLength(self, name, default):

        '''
        Get the <svg> attribute with name "name" and default value "default"
        Parse the attribute into a value and associated units.  Then, accept
        units of cm, ft, in, m, mm, pc, or pt.  Convert to pixels.

        Note that SVG defines 90 px = 1 in = 25.4 mm.
        Note: Since inkscape 0.92 we use the CSS standard of 96 px = 1 in.
        '''
        str = self.document.getroot().get(name)
        if str:
            return self.LengthWithUnit(str)
        else:
            # No width specified; assume the default value
            return float(default)

    def LengthWithUnit(self, strn, default_unit='px'):
        v, u = self.parseLengthWithUnits(strn, default_unit)
        if v is None:
            # Couldn't parse the value
            return None
        elif (u == 'mm'):
            return float(v) * (self.dpi / 25.4)
        elif (u == 'cm'):
            return float(v) * (self.dpi * 10.0 / 25.4)
        elif (u == 'm'):
            return float(v) * (self.dpi * 1000.0 / 25.4)
        elif (u == 'in'):
            return float(v) * self.dpi
        elif (u == 'ft'):
            return float(v) * 12.0 * self.dpi
        elif (u == 'pt'):
            # Use modern "Postscript" points of 72 pt = 1 in instead
            # of the traditional 72.27 pt = 1 in
            return float(v) * (self.dpi / 72.0)
        elif (u == 'pc'):
            return float(v) * (self.dpi / 6.0)
        elif (u == 'px'):
            self.px_used = True
            return float(v)
        else:
            # Unsupported units
            return None

    def getDocProps(self):

        '''
        Get the document's height and width attributes from the <svg> tag.
        Use a default value in case the property is not present or is
        expressed in units of percentages.
        '''

        inkscape_version = self.document.getroot().get(
            "{http://www.inkscape.org/namespaces/inkscape}version")
        sodipodi_docname = self.document.getroot().get(
            "{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}docname")
        if sodipodi_docname is None:
            sodipodi_docname = "inkscape"
        self.basename = re.sub(r"\.SVG", "", sodipodi_docname, flags=re.I)
        # a simple 'inkscape:version' does not work here. sigh....
        #
        # BUG:
        # inkscape 0.92 uses 96 dpi, inkscape 0.91 uses 90 dpi.
        # From inkscape 0.92 we receive an svg document that has
        # both inkscape:version and sodipodi:docname if the document
        # was ever saved before. If not, both elements are missing.
        #
        import lxml.etree
        # inkex.errormsg(lxml.etree.tostring(self.document.getroot()))
        if inkscape_version:
            '''
            inkscape:version="0.91 r"
            inkscape:version="0.92.0 ..."
           See also https://github.com/fablabnbg/paths2openscad/issues/1
            '''
            # inkex.errormsg("inkscape:version="+inkscape_version)
            m = re.match(r"(\d+)\.(\d+)", inkscape_version)
            if m:
                if int(m.group(1)) > 0 or int(m.group(2)) > 91:
                    self.dpi = 96                # 96dpi since inkscape 0.92
                    # inkex.errormsg("switching to 96 dpi")

        # BUGFIX https://github.com/fablabnbg/inkscape-paths2openscad/issues/1
        # get height and width after dpi. This is needed for e.g. mm units.
        self.docHeight = self.getLength('height', self.DEFAULT_HEIGHT)
        self.docWidth = self.getLength('width', self.DEFAULT_WIDTH)

        if (self.docHeight is None) or (self.docWidth is None):
            return False
        else:
            return True

    def handleViewBox(self):

        '''
        Set up the document-wide transform in the event that the document has
        an SVG viewbox
        '''

        if self.getDocProps():
            viewbox = self.document.getroot().get('viewBox')
            if viewbox:
                vinfo = viewbox.strip().replace(',', ' ').split(' ')
                if (vinfo[2] != 0) and (vinfo[3] != 0):
                    sx = self.docWidth  / float(vinfo[2])
                    sy = self.docHeight / float(vinfo[3])
                    self.docTransform = simpletransform.parseTransform('scale(%f,%f)' % (sx, sy))

    def getPathVertices(self, path, node=None, transform=None):

        '''
        Decompose the path data from an SVG element into individual
        subpaths, each subpath consisting of absolute move to and line
        to coordinates.  Place these coordinates into a list of polygon
        vertices.
        '''

        if (not path) or (len(path) == 0):
            # Nothing to do
            return None

        if node is not None:
            path = self.styleDasharray(path, node)

        # parsePath() may raise an exception.  This is okay
        sp = simplepath.parsePath(path)
        if (not sp) or (len(sp) == 0):
            # Path must have been devoid of any real content
            return None

        # Get a cubic super path
        p = cubicsuperpath.CubicSuperPath(sp)
        if (not p) or (len(p) == 0):
            # Probably never happens, but...
            return None

        if transform:
            simpletransform.applyTransformToPath(transform, p)

        # Now traverse the cubic super path
        subpath_list = []
        subpath_vertices = []

        for sp in p:

            # We've started a new subpath
            # See if there is a prior subpath and whether we should keep it
            if len(subpath_vertices):
                subpath_list.append([subpath_vertices, [sp_xmin, sp_xmax, sp_ymin, sp_ymax]])

            subpath_vertices = []
            self.subdivideCubicPath(sp, float(self.smoothness))

            # Note the first point of the subpath
            first_point = sp[0][1]
            subpath_vertices.append(first_point)
            sp_xmin = first_point[0]
            sp_xmax = first_point[0]
            sp_ymin = first_point[1]
            sp_ymax = first_point[1]

            n = len(sp)

            # Traverse each point of the subpath
            for csp in sp[1:n]:

                # Append the vertex to our list of vertices
                pt = csp[1]
                subpath_vertices.append(pt)

                # Track the bounding box of this subpath
                if pt[0] < sp_xmin:
                    sp_xmin = pt[0]
                elif pt[0] > sp_xmax:
                    sp_xmax = pt[0]
                if pt[1] < sp_ymin:
                    sp_ymin = pt[1]
                elif pt[1] > sp_ymax:
                    sp_ymax = pt[1]

            # Track the bounding box of the overall drawing
            # This is used for centering the polygons in OpenSCAD around the
            # (x,y) origin
            if sp_xmin < self.xmin:
                self.xmin = sp_xmin
            if sp_xmax > self.xmax:
                self.xmax = sp_xmax
            if sp_ymin < self.ymin:
                self.ymin = sp_ymin
            if sp_ymax > self.ymax:
                self.ymax = sp_ymax

        # Handle the final subpath
        if len(subpath_vertices):
            subpath_list.append([subpath_vertices, [sp_xmin, sp_xmax, sp_ymin, sp_ymax]])

        if len(subpath_list) > 0:
            self.paths[node] = subpath_list


    def recursivelyTraverseSvg(self, aNodeList, matCurrent=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
                               parent_visibility='visible'):

        '''
        [ This too is largely lifted from eggbot.py ]

        Recursively walk the SVG document, building polygon vertex lists
        for each graphical element we support.

        Rendered SVG elements:
            <circle>, <ellipse>, <line>, <path>, <polygon>, <polyline>, <rect>

        Supported SVG elements:
            <group>, <use>

        Ignored SVG elements:
            <defs>, <eggbot>, <metadata>, <namedview>, <pattern>,
            processing directives

        All other SVG elements trigger an error (including <text>)
        '''

        for node in aNodeList:

            # Ignore invisible nodes
            v = node.get('visibility', parent_visibility)
            if v == 'inherit':
                v = parent_visibility
            if v == 'hidden' or v == 'collapse':
                continue

            s = node.get('style', '')
            if s == 'display:none':
                continue

            # First apply the current matrix transform to this node's tranform
            matNew = simpletransform.composeTransform(
                matCurrent, simpletransform.parseTransform(node.get("transform")))

            if node.tag == inkex.addNS('g', 'svg') or node.tag == 'g':

                self.recursivelyTraverseSvg(node, matNew, v)

            elif node.tag == inkex.addNS('use', 'svg') or node.tag == 'use':

                # A <use> element refers to another SVG element via an
                # xlink:href="#blah" attribute.  We will handle the element by
                # doing an XPath search through the document, looking for the
                # element with the matching id="blah" attribute.  We then
                # recursively process that element after applying any necessary
                # (x,y) translation.
                #
                # Notes:
                #  1. We ignore the height and width attributes as they do not
                #     apply to path-like elements, and
                #  2. Even if the use element has visibility="hidden", SVG
                #     still calls for processing the referenced element.  The
                #     referenced element is hidden only if its visibility is
                #     "inherit" or "hidden".

                refid = node.get(inkex.addNS('href', 'xlink'))
                if not refid:
                    continue

                # [1:] to ignore leading '#' in reference
                path = '//*[@id="%s"]' % refid[1:]
                refnode = node.xpath(path)
                if refnode:
                    x = float(node.get('x', '0'))
                    y = float(node.get('y', '0'))
                    # Note: the transform has already been applied
                    if (x != 0) or (y != 0):
                        matNew2 = composeTransform(matNew, parseTransform('translate(%f,%f)' % (x, y)))
                    else:
                        matNew2 = matNew
                    v = node.get('visibility', v)
                    self.recursivelyTraverseSvg(refnode, matNew2, v)

            elif node.tag == inkex.addNS('path', 'svg'):

                path_data = node.get('d')
                if path_data:
                    self.getPathVertices(path_data, node, matNew)

            elif node.tag == inkex.addNS('rect', 'svg') or node.tag == 'rect':

                # Manually transform
                #
                #    <rect x="X" y="Y" width="W" height="H"/>
                #
                # into
                #
                #    <path d="MX,Y lW,0 l0,H l-W,0 z"/>
                #
                # I.e., explicitly draw three sides of the rectangle and the
                # fourth side implicitly

                # Create a path with the outline of the rectangle
                x = float(node.get('x'))
                y = float(node.get('y'))
                w = float(node.get('width', '0'))
                h = float(node.get('height', '0'))
                rx = float(node.get('rx', '0'))
                ry = float(node.get('ry', '0'))

                if rx > 0.0 or ry > 0.0:
                    if   ry < 0.0000001: ry = rx
                    elif rx < 0.0000001: rx = ry
                    d = self.roundedRectBezier(x, y, w, h, rx, ry)
                    self.getPathVertices(d, node, matNew)
                else:
                    a = []
                    a.append(['M ', [x, y]])
                    a.append([' l ', [w, 0]])
                    a.append([' l ', [0, h]])
                    a.append([' l ', [-w, 0]])
                    a.append([' Z', []])
                    self.getPathVertices(simplepath.formatPath(a), node, matNew)

            elif node.tag == inkex.addNS('line', 'svg') or node.tag == 'line':

                # Convert
                #
                #   <line x1="X1" y1="Y1" x2="X2" y2="Y2/>
                #
                # to
                #
                #   <path d="MX1,Y1 LX2,Y2"/>

                x1 = float(node.get('x1'))
                y1 = float(node.get('y1'))
                x2 = float(node.get('x2'))
                y2 = float(node.get('y2'))
                if (not x1) or (not y1) or (not x2) or (not y2):
                    continue
                a = []
                a.append(['M ', [x1, y1]])
                a.append([' L ', [x2, y2]])
                self.getPathVertices(simplepath.formatPath(a), node, matNew)

            elif node.tag == inkex.addNS('polyline', 'svg') or node.tag == 'polyline':

                # Convert
                #
                #  <polyline points="x1,y1 x2,y2 x3,y3 [...]"/>
                #
                # to
                #
                #   <path d="Mx1,y1 Lx2,y2 Lx3,y3 [...]"/>
                #
                # Note: we ignore polylines with no points

                pl = node.get('points', '').strip()
                if pl == '':
                    continue

                pa = pl.split()
                d = "".join(["M " + pa[i] if i == 0 else " L " + pa[i] for i in range(0, len(pa))])
                self.getPathVertices(d, node, matNew)

            elif node.tag == inkex.addNS('polygon', 'svg') or node.tag == 'polygon':

                # Convert
                #
                #  <polygon points="x1,y1 x2,y2 x3,y3 [...]"/>
                #
                # to
                #
                #   <path d="Mx1,y1 Lx2,y2 Lx3,y3 [...] Z"/>
                #
                # Note: we ignore polygons with no points

                pl = node.get('points', '').strip()
                if pl == '':
                    continue

                pa = pl.split()
                d = "".join(["M " + pa[i] if i == 0 else " L " + pa[i] for i in range(0, len(pa))])
                d += " Z"
                self.getPathVertices(d, node, matNew)

            elif node.tag == inkex.addNS('ellipse', 'svg') or node.tag == 'ellipse' or \
                 node.tag == inkex.addNS('circle', 'svg')  or node.tag == 'circle':

                # Convert circles and ellipses to a path with two 180 degree
                # arcs. In general (an ellipse), we convert
                #
                #   <ellipse rx="RX" ry="RY" cx="X" cy="Y"/>
                #
                # to
                #
                #   <path d="MX1,CY A RX,RY 0 1 0 X2,CY A RX,RY 0 1 0 X1,CY"/>
                #
                # where
                #
                #   X1 = CX - RX
                #   X2 = CX + RX
                #
                # Note: ellipses or circles with a radius attribute of value 0
                # are ignored

                if node.tag == inkex.addNS('ellipse', 'svg') or node.tag == 'ellipse':
                    rx = float(node.get('rx', '0'))
                    ry = float(node.get('ry', '0'))
                else:
                    rx = float(node.get('r', '0'))
                    ry = rx
                if rx == 0 or ry == 0:
                    continue

                cx = float(node.get('cx', '0'))
                cy = float(node.get('cy', '0'))
                x1 = cx - rx
                x2 = cx + rx
                d = 'M %f,%f '     % (x1, cy) + \
                    'A %f,%f '     % (rx, ry) + \
                    '0 1 0 %f,%f ' % (x2, cy) + \
                    'A %f,%f '     % (rx, ry) + \
                    '0 1 0 %f,%f'  % (x1, cy)
                self.getPathVertices(d, node, matNew)

            elif node.tag == inkex.addNS('pattern', 'svg') or node.tag == 'pattern':
                pass

            elif node.tag == inkex.addNS('metadata', 'svg') or node.tag == 'metadata':
                pass

            elif node.tag == inkex.addNS('defs', 'svg') or node.tag == 'defs':
                pass

            elif node.tag == inkex.addNS('desc', 'svg') or node.tag == 'desc':
                pass

            elif node.tag == inkex.addNS('namedview', 'sodipodi') or node.tag == 'namedview':
                pass

            elif node.tag == inkex.addNS('eggbot', 'svg') or node.tag == 'eggbot':
                pass

            elif node.tag == inkex.addNS('text', 'svg') or node.tag == 'text':
                texts = []
                plaintext = ''
                for tnode in node.iterfind('.//'):  # all subtree
                    if tnode is not None and tnode.text is not None:
                        texts.append(tnode.text)
                if len(texts):
                    plaintext = "', '".join(texts).encode('latin-1')
                    inkex.errormsg('Warning: text "%s"' % plaintext)
                    inkex.errormsg('Warning: unable to draw text, please convert it to a path first.')

            elif node.tag == inkex.addNS('title', 'svg') or node.tag == 'title':
                pass

            elif node.tag == inkex.addNS('image', 'svg') or node.tag == 'image':
                if 'image' not in self.warnings:
                    inkex.errormsg(
                        gettext.gettext(
                            'Warning: unable to draw bitmap images; please convert them to line art first.  '
                            'Consider using the "Trace bitmap..." tool of the "Path" menu.  Mac users please '
                            'note that some X11 settings may cause cut-and-paste operations to paste in bitmap copies.'))
                    self.warnings['image'] = 1

            elif node.tag == inkex.addNS('pattern', 'svg') or node.tag == 'pattern':
                pass

            elif node.tag == inkex.addNS('radialGradient', 'svg') or node.tag == 'radialGradient':
                # Similar to pattern
                pass

            elif node.tag == inkex.addNS('linearGradient', 'svg') or node.tag == 'linearGradient':
                # Similar in pattern
                pass

            elif node.tag == inkex.addNS('style', 'svg') or node.tag == 'style':
                # This is a reference to an external style sheet and not the
                # value of a style attribute to be inherited by child elements
                pass

            elif node.tag == inkex.addNS('cursor', 'svg') or node.tag == 'cursor':
                pass

            elif node.tag == inkex.addNS('color-profile', 'svg') or node.tag == 'color-profile':
                # Gamma curves, color temp, etc. are not relevant to single
                # color output
                pass

            elif not isinstance(node.tag, basestring):
                # This is likely an XML processing instruction such as an XML
                # comment.  lxml uses a function reference for such node tags
                # and as such the node tag is likely not a printable string.
                # Further, converting it to a printable string likely won't
                # be very useful.
                pass

            else:
                inkex.errormsg('Warning: unable to draw object <%s>, please convert it to a path first.' % node.tag)
                pass

    def recursivelyGetEnclosingTransform(self, node):

        '''
        Determine the cumulative transform which node inherits from
        its chain of ancestors.
        '''
        node = node.getparent()
        if node is not None:
            parent_transform = self.recursivelyGetEnclosingTransform(node)
            node_transform = node.get('transform', None)
            if node_transform is None:
                return parent_transform
            else:
                tr = simpletransform.parseTransform(node_transform)
                if parent_transform is None:
                    return tr
                else:
                    return simpletransform.composeTransform(parent_transform, tr)
        else:
            return self.docTransform

#! /usr/bin/python3
#
# (c) 2017 Patrick Himmelmann et.al.
# 2017-05-21
#
# (c) 2017-11-24, juergen@fabmail.org
#
# The code is fully compatible with python 2.7 and 3.5
#
# High level methods:
#  set(paths=[[..]], speed=.., power=[..], ...)
#  write(fd)
#
# Intermediate methods:
#  header(), body(), trailer()
#
# Low level methods:
#  encode_hex(), encode_relcoord(), encode_percent()
#  encode_number() for e.g.: # Bottom_Right_E7_51 452.84mm 126.8mm           e7 51 00 00 1b 51 68 00 00 07 5e 50
#  scramble()
#
# Some, but not all unscramble() decode_..() methods are also included.
# A self test example (cutting the triange in a square) is included at the end.
#
# 2017-12-03, jw@fabmail.org
#     v1.0 -- The test code produces a valid square_tri_test.rd, according to
#             githb.com/kkaempf/rudida/bin/decode
# 2017-12-11, jw@fabmail.org
#     v1.2 -- Correct maxrel 8.191 found.
#             Implemented Cut_Horiz, Cut_Vert, Move_Horiz, Move_Vert
#             Updated encode_relcoord() to use encode_number(2)
# 2017-12-13, jw@fabmail.org
#     v1.3 -- added _forceabs = 100. Limit possible precision loss.
# 2017-12-14, jw@fabmail.org
#     v1.4 -- added bbox2moves() and paths2moves()

import sys, re, math

# python2 has a completely useless alias bytes = str. Fix this:
if sys.version_info.major < 3:
        def bytes(tupl):
                "Minimalistic python3 compatible implementation used in python2."
                return "".join(map(chr, tupl))


class Ruida():
  """
   Assemble a valid *.rd file from the following parameters:

   paths = [
            [[0,0], [50,0], [50,50], [0,50], [0,0]],
            [[12,10], [38,25], [12,40], [12,10]]
           ]
        This example is a 50 mm square, with a 30 mm triangle inside.

   speed = 30
   speed = [ 1000, 30 ]
        Movement speed in mm/sec.
        Can be scalar or sequence. A scalar NUMBER is the same as a
        sequence of [1000, NUMBER]. The first value of the sequence is
        used for travelling with lasers off.
        The second value is with laser1 on.

   power = [ 50, 70 ]
        Values in percent. The first value is the minimum power used near
        corners or start and end of lines.
        The second value is the maximum power used in the middle of long
        straight lines, this compensates for accellerated machine
        movements.  Additional pairs can be specified for a second, third,
        and fourth laser.

   bbox = [[0,0], [50,50]]
        Must span the rectangle that contains all points in the paths.
        Can also be ommited and/or computed by the boundingbox() method.
        The first point ([xmin, ymin] aka "top left") of the bounding
        box is ususally [0,0] so that the start position can be easily
        adjusted at the machine.
  """

  __version__ = "1.4"

  def __init__(self, paths=None, speed=None, power=None, bbox=None, freq=20.0):
    self._paths = paths

    self._bbox = bbox
    self._speed = speed
    self._power = power
    self._freq = freq

    self._odo = None

    self._header = None
    self._body = None
    self._trailer = None

    # Must do an absolute mov/cut every now and then to avoid precision loss.
    # Worst case estimation: A deviation of 0.1mm is acceptable, this is circa the
    # diameter of the laser beam. Precision loss can occur due to rounding of the last decimal,
    # Which can contribute less than 0.001 mm each time. Thus a helpful value should be around
    # 100. We want the value as high as possible to safe code size, but slow enough to keep the
    # precision loss invisible.
    #
    # Set to 1, to disable relative moves.
    # Set to 0, to never force an absolute move. Allows potentially infinite precision loss.
    self._forceabs = 100

  def set(self, paths=None, speed=None, power=None, bbox=None, freq=None, odo=None, forceabs=None):
    if forceabs is not None: self._forceabs = forceabs
    if paths    is not None: self._paths    = paths
    if speed    is not None: self._speed    = speed
    if power    is not None: self._power    = power
    if bbox     is not None: self._bbox     = bbox
    if freq     is not None: self._freq     = freq
    if odo      is not None: self._odo      = odo

  def write(self, fd, scramble=True):
    """
    Write a fully prepared object into a file (or raise ValueError()s
    for missing attributes). The object must be prepared by passing
    parameters to __init__ or set().

    The filedescriptor should be opened in "wb" mode.

    The file format is normally scrambled. Files written with
    scramble=False are not understood by the machine, but may be
    helpful for debugging.
    """

    if not self._header:
      if not self._freq: self._freq = 20.0    # kHz   (unused?)
      if not self._bbox and self._paths: self._bbox = self.boundingbox(self._paths)
      if self._bbox and self._speed and self._power and self._freq:
        self._header = self.header(self._bbox, self._speed, self._power, self._freq)
    if not self._body:
      if self._paths:
        self._body = self.body(self._paths)
    if not self._odo:
      if self._paths:
        self._odo = self.odometer(self._paths)
    if not self._trailer: self._trailer = self.trailer(self._odo)

    if not self._header:  raise ValueError("header(_bbox,_speed,_power,_freq) not initialized")
    if not self._body:    raise ValueError("body(_paths) not initialized")
    if not self._trailer: raise ValueError("trailer() not initialized")

    contents = self._header + self._body + self._trailer
    if scramble: contents = self.scramble_bytes(contents)
    fd.write(contents)

  def odometer(self, paths=None, init=[0,0], return_home=False):
    """
    Returns a list of two values: [ cut_distance, travel_distance ]
    Note that these distances are subject to path ordering.
    Call this after all optimizations.
    """
    if paths is None: paths = self._paths
    if paths is None: raise ValueError("no paths")

    def dist_xy(p1, p2):
      dx = p2[0] - p1[0]
      dy = p2[1] - p1[1]
      return math.sqrt(dx*dx+dy*dy)

    cut_d = 0
    trav_d = 0
    xy = init
    for path in paths:
      traveling=True
      for point in path:
        if traveling:
          trav_d += dist_xy(xy, point)
          xy = point
          traveling = False
        else:
          cut_d += dist_xy(xy, point)
          xy = point
    if return_home:
      trav_d += dist_xy(xy, init)
    return [ cut_d, trav_d ]

  def paths2moves(self, paths=None):
    """
    Returns a list of one-element-lists, each point in any of the
    sub-paths as a its own list. This is technique generates
    only move instructions in the rd output (laser inactive).
    """
    if paths is None: paths = self._paths
    if paths is None: raise ValueError("no paths")
    moves = []
    for path in paths:
      for point in path:
        moves.append([[point[0], point[1]]])
    return moves

  def boundingbox(self, paths=None):
    """
    Returns a list of two pairs [[xmin, ymin], [xmax, ymax]]
    that spans the rectangle containing all points found in paths.
    If no parameter is given, the _paths of the object are examined.
    """
    if paths is None: paths = self._paths
    if paths is None: raise ValueError("no paths")
    xmin = xmax = paths[0][0][0]
    ymin = ymax = paths[0][0][1]
    for path in paths:
      for point in path:
        if point[0] > xmax: xmax = point[0]
        if point[0] < xmin: xmin = point[0]
        if point[1] > ymax: ymax = point[1]
        if point[1] < ymin: ymin = point[1]
    return [[xmin, ymin], [xmax, ymax]]

  def bbox2moves(self, bbox):
    """
    bbox = [[x0, y0], [x1, y1]]
    """
    x0 = bbox[0][0]
    y0 = bbox[0][1]
    x1 = bbox[1][0]
    y1 = bbox[1][1]
    return [[[x0,y0]], [[x1,y0]], [[x1,y1]], [[x0,y1]], [[x0, y0]]]

  def body(self, paths):
    """
    Convert a set of paths into lasercut instructions.
    Returns the binary instruction data.

    maxrel is the limit in mm, for relative moves and cuts.
    The theoretical limit is assumed to be between 5 and 10 mm,

    FIXME: As of 2017-12-04 the encoding of enc('r', ...) is broken.
           We always use absolute moves and cuts.
    """

    def relok(last, point):
      """
      Determine, if we can emit a relative move or cut command.
      An absolute move or cut costs 11 bytes,
      a relative one costs 5 bytes.
      """
      maxrel = 8.191     # 8.191 encodes as 3f 7f. -8.191 encodes as 40 01

      if last is None: return False
      dx = abs(point[0]-last[0])
      dy = abs(point[1]-last[1])
      return max(dx, dy) <= maxrel

    data = bytes([])
    relcounter = 0

    lp = None
    for path in paths:
      travel = True
      for p in path:
        if relok(lp, p) and (self._forceabs == 0 or relcounter < self._forceabs):

          if self._forceabs > 0: relcounter += 1

          if p[1] == lp[1]:     # horizontal rel
            if travel:
              data += self.enc('-r', ['8a', p[0]-lp[0]])   # Move_Horiz 6.213mm
            else:
              data += self.enc('-r', ['aa', p[0]-lp[0]])   # Cut_Horiz -6.008mm
          elif p[0] == lp[0]:   # vertical rel
            if travel:
              data += self.enc('-r', ['8b', p[1]-lp[1]])   # Move_Vert 17.1mm
            else:
              data += self.enc('-r', ['ab', p[1]-lp[1]])   # Cut_Vert 2.987mm
          else:                 # other rel
            if travel:
              data += self.enc('-rr', ['89', p[0]-lp[0], p[1]-lp[1]])   # Move_To_Rel 3.091mm 0.025mm
            else:
              data += self.enc('-rr', ['a9', p[0]-lp[0], p[1]-lp[1]])   # Cut_Rel 0.015mm -1.127mm

        else:

          relcounter = 0

          if travel:
            data += self.enc('-nn', ['88', p[0], p[1]])               # Move_To_Abs 0.0mm 0.0mm
          else:
            data += self.enc('-nn', ['a8', p[0], p[1]])               # Cut_Abs_a8 17.415mm 7.521mm

        lp = p
        travel = False
    return data

  def scramble_bytes(self, data):
    if sys.version_info.major < 3:
      return bytes([self.scramble(ord(b)) for b in data])
    else:
      return bytes([self.scramble(b) for b in data])

  def unscramble_bytes(self, data):
    if sys.version_info.major < 3:
      return bytes([self.unscramble(ord(b)) for b in data])
    else:
      return bytes([self.unscramble(b) for b in data])

  def unscramble(self, b):
    """ unscramble a single byte for reading from *.rd files """
    res_b=b-1
    if res_b<0: res_b+=0x100
    res_b^=0x88
    fb=res_b&0x80
    lb=res_b&1
    res_b=res_b-fb-lb
    res_b|=lb<<7
    res_b|=fb>>7
    return res_b

  def scramble(self, b):
    """ scramble a single byte for writing into *.rd files """
    fb=b&0x80
    lb=b&1
    res_b=b-fb-lb
    res_b|=lb<<7
    res_b|=fb>>7
    res_b^=0x88
    res_b+=1
    if res_b>0xff:res_b-=0x100
    return res_b

  def header(self, bbox, speed, power, freq):
    """
    Generate machine initialization instructions, to be sent before geometry.

    The bounding box bbox is expected in
    [[xmin, ymin], [xmax, ymax]] format, as returned by the boundingbox()
    method. Note: all test data seen had xmin=0, ymin=0.

    The power is expected as list of 2 to 8 elements, [min1, max1, ...]
    missing elements are added by repetition.
    Only one layer is currently initialized and used for all data.

    Units: Lengths in mm, power in percent [0..100],
           speed in mm/sec, freq in khz.

    Returns the binary instruction data.
    """

    if len(power) % 2: raise ValueError("Even number of elements needed in power[]")
    while len(power) < 8: power += power[-2:]
    (xmin, ymin) = bbox[0]
    (xmax, ymax) = bbox[1]

    if type(speed) == float or type(speed) == int: speed = [1000, speed]
    travelspeed = speed[0]
    laser1speed = speed[1]

    data = self.encode_hex("""
        d8 12           # Red Light on ?
        f0 f1 02 00     # file type ?
        d8 00           # Green Light off ?
        """)
    data += self.enc('-nn', ["e7 06", 0, 0])              # Feeding
    data += self.enc('-nn', ["e7 03", xmin, ymin])        # Top_Left_E7_07
    data += self.enc('-nn', ["e7 07", xmax, ymax])        # Bottom_Right_E7_07
    data += self.enc('-nn', ["e7 50", xmin, ymin])        # Top_Left_E7_50
    data += self.enc('-nn', ["e7 51", xmax, ymax])        # Bottom_Right_E7_51
    data += self.enc('-nn', ["e7 04 00 01 00 01", 0, 0])  # E7 04 ???
    data += self.enc('-n',  ["e7 05 00 c9 04 00", laser1speed]) # Speed_E7_05

    data += self.enc('-p-p', ["c6 31 00", power[0], "c6 32 00", power[1]]) # Laser_1_Min/Max_Pow Layer:0
    data += self.enc('-p-p', ["c6 41 00", power[2], "c6 42 00", power[3]]) # Laser_2_Min/Max_Pow Layer:0
    data += self.enc('-p-p', ["c6 35 00", power[4], "c6 36 00", power[5]]) # Laser_3_Min/Max_Pow Layer:0
    data += self.enc('-p-p', ["c6 37 00", power[6], "c6 38 00", power[7]]) # Laser_3_Min/Max_Pow Layer:0
    data += self.enc('-nn-nn-nn-nn-', ["""
        ca 06 00 00 00 00 00 00         # Layer_CA_06 Layer:0 00 00 00 00 00
        ca 41 00 00                     # ??
        e7 52 00""", xmin, ymin, """    # E7 52 Layer:0 top left?
        e7 53 00""", xmax, xmin, """    # Bottom_Right_E7_53 Layer:0
        e7 61 00""", xmin, ymin, """    # E7 61 Layer:0 top left?
        e7 62 00""", xmax, ymax, """    # Bottom_Right_E7_62 Layer:0
        ca 22 00                        # ??
        e7 54 00 00 00 00 00 00         # Pen_Draw_Y 00 0.0mm
        e7 54 01 00 00 00 00 00         # Pen_Draw_Y 01 0.0mm
        """])
    data += self.enc('-nn-nn-nn-nn-nn-nn-nn-nn-', ["""
        e7 55 00 00 00 00 00 00                         # Laser2_Y_Offset False 0.0mm
        e7 55 01 00 00 00 00 00                         # Laser2_Y_Offset True 0.0mm
        f1 03 00 00 00 00 00 00 00 00 00 00             # Laser2_Offset 0.0mm 0.0mm
        f1 00 00                                        # Start0 00
        f1 01 00                                        # Start1 00
        f2 00 00                                        # F2 00 00
        f2 01 00                                        # F2 01 00
        f2 02 05 2a 39 1c 41 04 6a 15 08 20             # F2 02 05 2a 39 1c 41 04 6a 15 08 20
        f2 03 """, xmin, ymin, """                      # F2 03 0.0mm 0.0mm
        f2 04 """, xmax, ymax, """                      # Bottom_Right_F2_04 17.414mm 24.868mm
        f2 06 """, xmin, ymin, """                      # F2 06 0.0mm 0.0mm
        f2 07 00                                        # F2 07 00
        f2 05 00 01 00 01 """, xmax, ymax, """          # Bottom_Right_F2_05 00 01 00 01 17.414mm 24.868mm
        ea 00                                           # EA 00
        e7 60 00                                        # E7 60 00
        e7 13 """, xmin, ymin, """                      # E7 13 0.0mm 0.0mm
        e7 17 """, xmax, ymax, """                      # Bottom_Right_E7_17 17.414mm 24.868mm
        e7 23 """, xmin, ymin, """                      # E7 23 0.0mm 0.0mm
        e7 24 00                                        # E7 24 00
        e7 08 00 01 00 01 """, xmax, ymax, """          # Bottom_Right_E7_08 00 01 00 01 17.414mm 24.868mm
        ca 01 00                                        # Flags_CA_01 00
        ca 02 00                                        # CA 02 Layer:0
        ca 01 30                                        # Flags_CA_01 30
        ca 01 10                                        # Flags_CA_01 10
        ca 01 13                                        # Blow_on
        """])
    data += self.enc('-n-p-p-p-p-p-p-p-p-p-p-p-p-', ["""
        c9 02 """, laser1speed, """     # Speed_C9 30.0mm/s
        c6 12 00 00 00 00 00            # Cut_Open_delay_12 0.0 ms
        c6 13 00 00 00 00 00            # Cut_Close_delay_13 0.0 ms
        c6 50 """, 100, """             # Cut_through_power1 100%
        c6 51 """, 100, """             # Cut_through_power2 100%
        c6 55 """, 100, """             # Cut_through_power3 100%
        c6 56 """, 100, """             # Cut_through_power4 100%
        c6 01 """, power[0], """        # Laser_1_Min_Pow_C6_01 0%
        c6 02 """, power[1], """        # Laser_1_Max_Pow_C6_02 0%
        c6 21 """, power[2], """        # Laser_2_Min_Pow_C6_21 0%
        c6 22 """, power[3], """        # Laser_2_Max_Pow_C6_22 0%
        c6 05 """, power[4], """        # Laser_3_Min_Pow_C6_05 1%
        c6 06 """, power[5], """        # Laser_3_Max_Pow_C6_06 0%
        c6 07 """, power[6], """        # Laser_4_Min_Pow_C6_07 0%
        c6 08 """, power[7], """        # Laser_4_Max_Pow_C6_08 0%
        ca 03 0f                        # Layer_CA_03 0f
        ca 10 00                        # CA 10 00
        """])
    return data


  def trailer(self, odo=[0.0, 0.0]):
    """
    Generate machine trailer instructions. To be sent after geometry instructions.

    Initialize a trailer with the cut distance in m, not mm.
    Note, that RDworks8 uses the cut distance twice here, and does not send the
    the travel distance. Is this a bug?

    Returns the binary instruction data.
    """
    data = self.enc("-nn-", ["""
        eb e7 00
        da 01 06 20""", odo[0]*0.001, odo[0]*0.001, """
        d7 """])
    return data


  def encode_number(self, num, length=5, scale=1000):
    """
    The number n is expected in floating point format with unit mm.
    A bytes() array of size length is returned.
    The default scale converts to micrometers.
    length=5 and scale=1000 are the expected machine format.
    """
    res = []
    nn = int(num * scale)
    while nn > 0:
      res.append(nn & 0x7f)
      nn >>= 7
    while len(res) < length:
      res.append(0)
    res.reverse()
    return bytes(res)

  def enc(self, fmt, tupl):
    """
    Encode the elements of tupl according to the format string.
    Each character in fmt consumes the corresponds element from tupl
    as a parameter to an encoding method:
    '-'       encode_hex()
    'n'       encode_number()
    'p'       encode_percent()
    'r'       encode_relcoord()
    """
    if len(fmt) != len(tupl): raise ValueError("format '"+fmt+"' length differs from len(tupl)="+str(len(tupl)))

    ret = b''
    for i in range(len(fmt)):
      if   fmt[i] == '-': ret += self.encode_hex(tupl[i])
      elif fmt[i] == 'n': ret += self.encode_number(tupl[i])
      elif fmt[i] == 'p': ret += self.encode_percent(tupl[i])
      elif fmt[i] == 'r': ret += self.encode_relcoord(tupl[i])
      else: raise ValueError("unknown character in fmt: "+fmt)
    return ret

  def decode_number(self, x):
    "used with a bytes() array of length 5"
    fak=1
    res=0
    for b in reversed(x):
      res+=fak*b
      fak*=0x80
    return 0.0001 * res

  def encode_relcoord(self, n):
    """
    Relative position in mm;
    Returns a bytes array of two elements.
    """
    nn = int(n*1000)
    if nn > 8191 or nn < -8191:
      raise ValueError("relcoord "+str(n)+" mm is out of range. Use abscoords!")
    if nn < 0: nn += 16384
    return self.encode_number(nn, length=2, scale=1)

  def decode_relcoord(self, x):
    """
    using the first two elements of array x
    relative position in micrometer; signed (2s complement)
    """
    r = x[0] << 8
    r += x[1]
    if r > 16383 or r < 0:
      raise ValueError("Not a rel coord: " + repr(x[0:2]))
    if r > 8191: return 0.001 * (r-16384)
    else:        return 0.001 * r

  def encode_percent(self, n):
    """
    returns two bytes, used with laser and layer percentages.
    The magic constant 163.83 is 1/100 of 14bit all 1s.
    """
    a = int(n*0x3fff*0.01)    # n * 163.83
    return bytes([a>>7, a&0x7f])      # 7-bit encoding

  def encode_hex(self, str):
    """
    Assemble a string from hexadecimal digits. Binary safe.
    Example: "48 65 6c 6c f8  # with a smorrebrod o\n    21" -> b'Hell\xf7!'
    """
    str = re.sub('#.*$','', str, flags=re.MULTILINE)    # weed out comments.
    l = map(lambda x: int(x, base=16), str.split())     # locale.atoi() is to be avoided!
    return bytes(l)


import json
import inkex
import gettext


# python2 compatibility. Inkscape runs us with python2!
if sys.version_info.major < 3:
        def bytes(tupl):
                return "".join(map(chr, tupl))


class ThunderLaser(inkex.Effect):

    __version__ = '1.6'         # >= max(src/ruida.py:__version__, src/inksvg.py:__version__); Keep in sync with thunderlaser-ruida.inx

    def __init__(self):
        """
Option parser example:

'thunderlaser.py', '--tab="thunderlaser"', '--cut_group="cut_plastics"', '--cut_wood=30,50,65', '--cut_plastics=25,55,70', '--cut_other=300,26,65', '--cut_manual_speed=68', '--cut_manual_minpow=60', '--cut_manual_maxpow=70', '--cut_color=any', '--mark_group="mark_material"', '--mark_material=1000,8,25', '--mark_manual_speed=30', '--mark_manual_minpow=50', '--mark_manual_maxpow=70', '--mark_color=none', '--smoothness=0.20000000298023224', '--maxwidth=900', '--maxheight=600', '--bbox_only=false', '--device=/dev/ttyUSB0,/tmp/hannes.rd', '--dummy=true', '/tmp/ink_ext_XXXXXX.svgDTI8AZ']

        """
        inkex.localize()    # does not help for localizing my *.inx file
        inkex.Effect.__init__(self)

        self.OptionParser.add_option(
            "--tab",  # NOTE: value is not used.
            action="store", type="string", dest="tab", default="thunderlaser",
            help="The active tab when Apply was pressed")

        self.OptionParser.add_option(
            "--cut_group", action="store", type="string", dest="cut_group", default="cut_wood",
            help="The active cut_group tab when Apply was pressed")

        self.OptionParser.add_option(
            "--mark_group", action="store", type="string", dest="mark_group", default="mark_material",
            help="The active mark_group tab when Apply was pressed")

        self.OptionParser.add_option(
            "--cut_color", action="store", type="string", dest="cut_color", default="any",
            help="The color setting for cutting. Default: any")

        self.OptionParser.add_option(
            "--mark_color", action="store", type="string", dest="mark_color", default="none",
            help="The color setting for cutting. Default: none")



        self.OptionParser.add_option(
            '--cut_wood', dest='cut_wood', type='string', default='30,50,65', action='store',
            help='Speed,MinPower,MaxPower Setting when cutting wood is selected.')

        self.OptionParser.add_option(
            '--cut_plastics', dest='cut_plastics', type='string', default='', action='store',
            help='Speed,MinPower,MaxPower Setting when cutting plastics is selected.')

        self.OptionParser.add_option(
            '--cut_other', dest='cut_other', type='string', default='', action='store',
            help='Speed,MinPower,MaxPower Setting when cutting other is selected.')

        self.OptionParser.add_option(
            '--cut_manual_speed', dest='cut_manual_speed', type='int', default=30, action='store',
            help='Speed Setting when cutting with manual entry is selected.')

        self.OptionParser.add_option(
            '--cut_manual_minpow', dest='cut_manual_minpow', type='int', default=30, action='store',
            help='MinPower1 Setting when cutting with manual entry is selected.')

        self.OptionParser.add_option(
            '--cut_manual_maxpow', dest='cut_manual_maxpow', type='int', default=30, action='store',
            help='MaxPower1 Setting when cutting with manual entry is selected.')




        self.OptionParser.add_option(
            '--mark_material', dest='mark_material', type='string', default='1000,7,18', action='store',
            help='Speed,MinPower,MaxPower Setting when marking by material is selected.')

        self.OptionParser.add_option(
            '--mark_manual_speed', dest='mark_manual_speed', type='int', default=1000, action='store',
            help='Speed Setting when marking with manual entry is selected.')

        self.OptionParser.add_option(
            '--mark_manual_minpow', dest='mark_manual_minpow', type='int', default=7, action='store',
            help='MinPower1 Setting when marking with manual entry is selected.')

        self.OptionParser.add_option(
            '--mark_manual_maxpow', dest='mark_manual_maxpow', type='int', default=18, action='store',
            help='MaxPower1 Setting when marking with manual entry is selected.')



        self.OptionParser.add_option(
            '--smoothness', dest='smoothness', type='float', default=float(0.2), action='store',
            help='Curve smoothing (less for more [0.0001 .. 5]). Default: 0.2')

        self.OptionParser.add_option(
            '--freq1', dest='freq1', type='float', default=float(20.0), action='store',
            help='Laser1 frequency [kHz]. Default: 20.0')

        self.OptionParser.add_option(
            '--maxheight', dest='maxheight', type='string', default='600', action='store',
            help='Height of laser area [mm]. Default: 600 mm')

        self.OptionParser.add_option(
            '--maxwidth', dest='maxwidth', type='string', default='900', action='store',
            help='Width of laser area [mm]. Default: 900 mm')

        self.OptionParser.add_option(
            "--bbox_only", action="store", type="inkbool", dest="bbox_only", default=False,
            help="Cut bounding box only. Default: False")

        self.OptionParser.add_option(
            "--move_only", action="store", type="inkbool", dest="move_only", default=False,
            help="Move only, instead of cutting and moving. Default: False")

        self.OptionParser.add_option(
            "--dummy", action="store", type="inkbool", dest="dummy", default=False,
            help="Dummy device: Send to /tmp/thunderlaser.rd . Default: False")

        self.OptionParser.add_option(
            '--device', dest='devicelist', type='string', default='/dev/ttyUSB0,/dev/ttyACM0,/tmp/thunderlaser.rd', action='store',
            help='Output device or file name to use. A comma-separated list. Default: /dev/ttyUSB0,/dev/ttyACM0,/tmp/thunderlaser.rd')

        self.OptionParser.add_option('-V', '--version',
          action = 'store_const', const=True, dest = 'version', default = False,
          help='Just print version number ("'+self.__version__+'") and exit.')


    def cut_options(self):
        """
        returns None, if deactivated or
        returns [ 'speed':1000, 'minpow':50, 'maxpow':70, 'color':"any" ] otherwise.
        """
        group=self.options.cut_group.strip('"')         # passed into the option with surrounding double-quotes. yacc.
        color = self.options.cut_color
        if color == 'none': return None

        parse_str = None
        if   group == "cut_wood":     parse_str = self.options.cut_wood
        elif group == "cut_plastics": parse_str = self.options.cut_plastics
        elif group == "cut_other":    parse_str = self.options.cut_other
        if parse_str is None:
          return {
                'speed': int(self.options.cut_manual_speed),
                'minpow':int(self.options.cut_manual_minpow),
                'maxpow':int(self.options.cut_manual_maxpow),
                'color':color, 'group':group }
        else:
          v = parse_str.split(',')
          return { 'speed':int(v[0]), 'minpow':int(v[1]), 'maxpow':int(v[2]), 'color':color, 'group':group }

    def mark_options(self):
        """
        returns None, if self.options.mark_color=='none'
        returns [ 'speed':1000, 'minpow':50, 'maxpow':70, 'color':"green" ] otherwise.
        """
        group=self.options.mark_group.strip('"')
        color = self.options.mark_color
        if color == 'none': return None

        parse_str = None
        if group == "mark_material": parse_str = self.options.mark_material
        if parse_str is None:
          return {
                'speed': int(self.options.mark_manual_speed),
                'minpow':int(self.options.mark_manual_minpow),
                'maxpow':int(self.options.mark_manual_maxpow),
                'color':color, 'group':group }
        else:
          v = parse_str.split(',')
          return { 'speed':int(v[0]), 'minpow':int(v[1]), 'maxpow':int(v[2]), 'color':color, 'group':group }


    def effect(self):
        svg = InkSvg(document=self.document, smoothness=float(self.options.smoothness))

        # Viewbox handling
        svg.handleViewBox()

        if self.options.version:
            print("Version "+self.__version__)
            sys.exit(0)

        # First traverse the document (or selected items), reducing
        # everything to line segments.  If working on a selection,
        # then determine the selection's bounding box in the process.
        # (Actually, we just need to know it's extrema on the x-axis.)

        if self.options.ids:
            # Traverse the selected objects
            for id in self.options.ids:
                transform = svg.recursivelyGetEnclosingTransform(self.selected[id])
                svg.recursivelyTraverseSvg([self.selected[id]], transform)
        else:
            # Traverse the entire document building new, transformed paths
            svg.recursivelyTraverseSvg(self.document.getroot(), svg.docTransform)


        ## First simplification: paths_dict[]
        ## Remove the bounding boxes from paths. Replace the object with its id. We can still access color and style attributes through the id.
        ## from {<Element {http://www.w3.org/2000/svg}path at 0x7fc446a583b0>:
        ##                  [[[[207, 744], [264, 801]], [207, 264, 744, 801]], [[[207, 801], [264, 744]], [207, 264, 744, 801]]], ... }
        ## to   {"path4490": [[[207, 744], [264, 801]],                         [[207, 801], [264, 744]]], ... }
        ##
        paths_dict = {}
        for k in svg.paths:
                kk = k.get('id', str(k))
                ll = []
                for e in svg.paths[k]:
                        ll.append(e[0])
                paths_dict[kk] = ll

        ## Second simplification: paths_list[]
        ## Remove the keys. Leaving a simple list of lists, without color or other style attributes.
        ## to                [[[207, 744], [264, 801]],                         [[207, 801], [264, 744]], [...] ]
        ##
        ## Also reposition the graphics, so that a corner or the center becomes origin [0,0]
        ## and convert from dots-per-inch to mm.
        paths_list = []
        dpi2mm = 25.4 / svg.dpi

        (xoff,yoff) = (svg.xmin, svg.ymin)                      # top left corner is origin
        # (xoff,yoff) = (svg.xmax, svg.ymax)                      # bottom right corner is origin
        # (xoff,yoff) = ((svg.xmax+svg.xmin)/2.0, (svg.ymax+svg.ymin)/2.0)       # center is origin

        for paths in paths_dict.values():
                for path in paths:
                        newpath = []
                        for point in path:
                                newpath.append([(point[0]-xoff) * dpi2mm, (point[1]-yoff) * dpi2mm])
                        paths_list.append(newpath)
        bbox = [[(svg.xmin-xoff)*dpi2mm, (svg.ymin-yoff)*dpi2mm], [(svg.xmax-xoff)*dpi2mm, (svg.ymax-yoff)*dpi2mm]]

        rd = Ruida()
        # bbox = rd.boundingbox(paths_list)     # same as above.

        if self.options.bbox_only:
                paths_list = [[ [bbox[0][0],bbox[0][1]], [bbox[1][0],bbox[0][1]], [bbox[1][0],bbox[1][1]],
                                [bbox[0][0],bbox[1][1]], [bbox[0][0],bbox[0][1]] ]]
        if self.options.move_only:
                paths_list = rd.paths2moves(paths_list)

        cut_opt  = self.cut_options()
        mark_opt = self.mark_options()                  # FIXME: unused
        if cut_opt is None and mark_opt is None:
          inkex.errormsg(gettext.gettext('ERROR: Enable Cut or Mark or both.'))
          sys.exit(1)
        if cut_opt is not None and mark_opt is not None and cut_opt['color'] == mark_opt['color']:
          inkex.errormsg(gettext.gettext('ERROR: Choose different color settings for Cut and Mark. Both are "'+mark_opt['color']+'"'))
          sys.exit(1)

        if cut_opt is None: cut_opt = mark_opt          # so that we have at least something to do.

        if self.options.dummy:
                with open('/tmp/thunderlaser.json', 'w') as fd:
                        json.dump({
                                'paths_bbox': bbox,
                                'cut_opt': cut_opt, 'mark_opt': mark_opt,
                                'paths_unit': 'mm', 'svg_resolution': svg.dpi, 'svg_resolution_unit': 'dpi',
                                'freq1': self.options.freq1, 'freq1_unit': 'kHz',
                                'paths': paths_list
                                }, fd, indent=4, sort_keys=True, encoding='utf-8')
                print("/tmp/thunderlaser.json written.", file=sys.stderr)
        else:
                if bbox[0][0] < 0 or bbox[0][1] < 0:
                        inkex.errormsg(gettext.gettext('Warning: negative coordinates not implemented in class Ruida(), truncating at 0'))
                rd.set(speed=cut_opt['speed'])
                rd.set(power=[cut_opt['minpow'], cut_opt['maxpow']])
                rd.set(paths=paths_list, bbox=bbox)
                device_used = None
                for device in self.options.devicelist.split(','):
                    try:
                        with open(device, 'wb') as fd:
                            rd.write(fd)
                        print(device+" written.", file=sys.stderr)
                        device_used = device
                        break
                    except:
                        pass
                if device_used is None:
                        inkex.errormsg(gettext.gettext('Warning: no usable devices in device list (or bad directoy): '+self.options.devicelist))


if __name__ == '__main__':
    e = ThunderLaser()
    e.affect()
