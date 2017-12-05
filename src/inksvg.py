#! /usr/bin/python
#
# inksvg.py - parse an svg file into a plain list of paths.
# 
# (c)2017-12-04 juergen@fabmail.org, authors of eggbot and others.
#

import inkex
import simplepath
import simpletransform
import cubicsuperpath
import cspsubdiv
import bezmisc

import gettext
import re

class InkSvg():
    """
    """
    __version__ = "1.0"
    DEFAULT_WIDTH = 100
    DEFAULT_HEIGHT = 100

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
                if (not x) or (not y):
                    pass
                w = float(node.get('width', '0'))
                h = float(node.get('height', '0'))
                rx = float(node.get('rx', '0'))
                ry = float(node.get('ry', '0'))
                a = []

                if rx > 0.0 or ry > 0.0:
                    if ry < 0.0000001: ry = rx
                    if 'rounded_rect' not in self.warnings:
                        self.warnings['rounded_rect'] = 1
                        inkex.errormsg(gettext.gettext(
                            'Warning: rounded corners of rectangle ignored. Please convert object <%s> to path and try again' % node.get('id')))
                    a.append(['M ', [x, y]])
                    a.append([' l ', [w, 0]])
                    a.append([' l ', [0, h]])
                    a.append([' l ', [-w, 0]])
                    a.append([' Z', []])
                else:
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
