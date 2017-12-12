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

import sys
sys.path.append('/usr/share/inkscape/extensions/')

## INLINE_BLOCK_START
# for easier distribution, our Makefile can inline these imports when generating thunderlaser.py from src/rudia-laser.py
from ruida import Ruida
from inksvg import InkSvg
## INLINE_BLOCK_END

import json
import inkex
import gettext


# python2 compatibility. Inkscape runs us with python2!
if sys.version_info.major < 3:
        def bytes(tupl):
                return "".join(map(chr, tupl))


class ThunderLaser(inkex.Effect):

    __version__ = '1.4'         # >= max(src/ruida.py:__version__, src/inksvg.py:__version__)

    def __init__(self):
        inkex.localize()    # does not help for localizing my *.inx file
        inkex.Effect.__init__(self)

        self.OptionParser.add_option(
            '--device', dest='devicelist', type='string', default='/dev/ttyUSB0,/dev/ttyACM0,/tmp/thunderlaser.rd', action='store',
            help='Output device or file name to use. A comma-separated list. Default: /dev/ttyUSB0,/dev/ttyACM0,/tmp/thunderlaser.rd')

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

        self.OptionParser.add_option('-V', '--version',
          action = 'store_const', const=True, dest = 'version', default = False,
          help='Just print version number ("'+self.__version__+'") and exit.')



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

        if self.options.dummy:
                with open('/tmp/thunderlaser.json', 'w') as fd:
                        json.dump({
                                'paths_bbox': bbox,
                                'speed': self.options.speed, 'speed_unit': 'mm/s',
                                'minpower1': self.options.minpower1, 'minpower1_unit': '%',
                                'maxpower1': self.options.maxpower1, 'maxpower1_unit': '%',
                                'paths_unit': 'mm', 'svg_resolution': svg.dpi, 'svg_resolution_unit': 'dpi',
                                'freq1': self.options.freq1, 'freq1_unit': 'kHz',
                                'paths': paths_list
                                }, fd, indent=4, sort_keys=True, encoding='utf-8')
                print("/tmp/thunderlaser.json written.", file=sys.stderr)
        else:
                if bbox[0][0] < 0 or bbox[0][1] < 0:
                        inkex.errormsg(gettext.gettext('Warning: negative coordinates not implemented in class Ruida(), truncating at 0'))
                rd = Ruida()
                rd.set(speed=int(self.options.speed))
                rd.set(power=[int(self.options.minpower1),int(self.options.maxpower1)])
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
                        inkex.errormsg(gettext.gettext('Warning: no usable devices in device list: '+self.options.devicelist))


if __name__ == '__main__':
    e = ThunderLaser()
    e.affect()
