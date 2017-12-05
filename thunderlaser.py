#! /usr/bin/python3
#
# thunderlaser.py -- minimalistic driver for exporting an RDCAM fie for a Thunderlaser RUIDA machine.
#
# This is an Inkscape extension to output paths in rdcam format.
# recursivelyTraverseSvg() is originally from eggbot. Thank!
# inkscape-paths2openscad and inkscape-silhouette contain copies of recursivelyTraverseSvg() 
# with almost identical features, but different inmplementation details. The version used here is derived from 
# inkscape-paths2openscad.
#
# python2 compatibility:
from __future__ import print_function

from ruida import Ruida
from inksvg import InkSvg

import sys
import json
import inkex


# python2 compatibility. Inkscape runs us with python2!
if sys.version_info.major < 3:
        def bytes(tupl):
                return "".join(map(chr, tupl))


class ThunderLaser(inkex.Effect):
    def __init__(self):
        inkex.localize()    # does not help for localizing my *.inx file
        inkex.Effect.__init__(self)

        self.OptionParser.add_option(
            '--speed', dest='speed', type='string', default='30', action='store',
            help='Laser movement speed [mm/s]. Default: 30 mm/s')

        self.OptionParser.add_option(
            '--maxpower1', dest='maxpower1', type='string', default='70', action='store',
            help='Laser1 maximum power [%]. Default: 70 %')

        self.OptionParser.add_option(
            '--minpower1', dest='minpower1', type='string', default='50', action='store',
            help='Laser1 minimum power [%]. Default: 50 %')

        self.OptionParser.add_option(
            "--tab",  # NOTE: value is not used.
            action="store", type="string", dest="tab", default="thunderlaser",
            help="The active tab when Apply was pressed")

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
            "--dummy", action="store", type="inkbool", dest="dummy", default=False,
            help="Dummy device: Send to /tmp/thunderlaser.rd . Default: False")

    def effect(self):

        svg = InkSvg(document=self.document, smoothness=float(self.options.smoothness))
        # Viewbox handling
        svg.handleViewBox()

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


        # First simplification: remove the bounding boxes from paths. Replace the object with its id.
        # from {<Element {http://www.w3.org/2000/svg}path at 0x7fc446a583b0>: [[[[207, 744], [264, 801]], [207, 264, 744, 801]], [[[207, 801], [264, 744]], [207, 264, 744, 801]]]}
        # to   {"path4490": [[[207, 744], [264, 801]], [[207, 801], [264, 744]]] }
        paths_dict = {}
        for k in svg.paths:
                kk = k.get('id', str(k))
                ll = []
                for e in svg.paths[k]:
                        ll.append(e[0])
                paths_dict[kk] = ll

        if not self.options.dummy:
                inkex.errormsg('Warning: rdcam generator not implemented. Please activate Dummy output.')
        else:
                fd = open('/tmp/thunderlaser.json', 'w')
                json.dump({
                        'bbox': [[svg.xmin, svg.ymin], [svg.xmax, svg.ymax]],
                        'speed': self.options.speed, 'speed_unit': 'mm/s',
                        'minpower1': self.options.minpower1, 'minpower1_unit': '%',
                        'maxpower1': self.options.maxpower1, 'maxpower1_unit': '%',
                        'resolution': svg.dpi, 'resolution_unit': 'dpi',
                        'freq1': self.options.freq1, 'freq1_unit': 'kHz',
                        'paths': paths_dict
                        }, fd, indent=4, encoding='utf-8')
                fd.close()
                print("/tmp/thunderlaser.json written.", file=sys.stderr)


if __name__ == '__main__':
    e = ThunderLaser()
    e.affect()
