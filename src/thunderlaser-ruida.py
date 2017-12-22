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
# 1.5a - cut/mark color filtering implemented via colorname2rgb() and svg.matchStrokeColor().
#        Works with dummy device. TODO: ruida output using Layers.
# 1.5b - using class Ruida through the new layer interface.
#        TODO: ruida output using multiple layers, currently only layer 0 is used.
# 1.5c - _removed _before _tags and _attributes in *.inx, to disable false automatic translations.
#        That does not seem to work. Strings are still subject to automatic translations.
#        Replaced all empty gui-text="" with repetitive noise, to avoid 0.91
#        translating "" into a 16 lines boiler plate text.
# 1.6  - juergen@fabmail.org
#        multi layer support added. Can now mark and cut in one job.
# 1.6b - bugfix release: [ ] bbox, [ ] move only, did always cut.
#        Updated InkSvg() class preserves native order of SVG elements.
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

    # CAUTION: Keep in sync with thunderlaser-ruida.inx and thunderlaser-ruida_de.inx
    __version__ = '1.6b'         # >= max(src/ruida.py:__version__, src/inksvg.py:__version__)

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

    def colorname2rgb(self, name):
        if name is None:      return None
        if name == 'none':    return False
        if name == 'any':     return True
        if name == 'red':     return [ 255, 0, 0]
        if name == 'green':   return [ 0, 255, 0]
        if name == 'blue':    return [ 0, 0, 255]
        if name == 'black':   return [ 0, 0, 0]
        if name == 'white':   return [ 255, 255, 255]
        if name == 'cyan':    return [ 0, 255, 255]
        if name == 'magenta': return [ 255, 0, 255]
        if name == 'yellow':  return [ 255, 255, 0]
        raise ValueError("unknown colorname: "+name)


    def effect(self):
        svg = InkSvg(document=self.document, smoothness=float(self.options.smoothness))

        # Viewbox handling
        svg.handleViewBox()

        if self.options.version:
            print("Version "+self.__version__)
            sys.exit(0)

        cut_opt  = self.cut_options()
        mark_opt = self.mark_options()                  # FIXME: unused
        if cut_opt is None and mark_opt is None:
          inkex.errormsg(gettext.gettext('ERROR: Enable Cut or Mark or both.'))
          sys.exit(1)
        if cut_opt is not None and mark_opt is not None and cut_opt['color'] == mark_opt['color']:
          inkex.errormsg(gettext.gettext('ERROR: Choose different color settings for Cut and Mark. Both are "'+mark_opt['color']+'"'))
          sys.exit(1)
        mark_color = self.colorname2rgb(None if mark_opt is None else mark_opt['color'])
        cut_color  = self.colorname2rgb(None if  cut_opt is None else  cut_opt['color'])

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


        ## First simplification: paths_tupls[]
        ## Remove the bounding boxes from paths. Replace the object with its id. We can still access color and style attributes through the id.
        ## from (<Element {http://www.w3.org/2000/svg}path at 0x7fc446a583b0>,
        ##                  [[[[207, 744], [264, 801]], [207, 264, 744, 801]], [[[207, 801], [264, 744]], [207, 264, 744, 801]], ...])
        ## to   (<Element {http://www.w3.org/2000/svg}path at 0x7fc446a583b0>,
        ##                  [[[207, 744], [264, 801]],                         [[207, 801], [264, 744]]], ... ]
        ##
        paths_tupls = []
        for tup in svg.paths:
                node = tup[0]
                ll = []
                for e in tup[1]:
                        ll.append(e[0])
                paths_tupls.append( (node, ll) )
        self.paths = None       # free some memory

        ## Reposition the graphics, so that a corner or the center becomes origin [0,0]
        ## Convert from dots-per-inch to mm.
        ## Separate into Cut and Mark lists based on element style.
        paths_list = []
        paths_list_cut = []
        paths_list_mark = []
        dpi2mm = 25.4 / svg.dpi

        (xoff,yoff) = (svg.xmin, svg.ymin)                      # top left corner is origin
        # (xoff,yoff) = (svg.xmax, svg.ymax)                      # bottom right corner is origin
        # (xoff,yoff) = ((svg.xmax+svg.xmin)/2.0, (svg.ymax+svg.ymin)/2.0)       # center is origin

        for tupl in paths_tupls:
                (elem,paths) = tupl
                for path in paths:
                        newpath = []
                        for point in path:
                                newpath.append([(point[0]-xoff) * dpi2mm, (point[1]-yoff) * dpi2mm])
                        paths_list.append(newpath)
                        is_mark = svg.matchStrokeColor(elem, mark_color)
                        is_cut  = svg.matchStrokeColor(elem,  cut_color)
                        if is_cut and is_mark:          # never both. Named colors win over 'any'
                                if mark_opt['color'] == 'any':
                                        is_mark = False
                                else:                   # cut_opt['color'] == 'any'
                                        is_cut = False
                        if is_cut:  paths_list_cut.append(newpath)
                        if is_mark: paths_list_mark.append(newpath)
        paths_tupls = None      # save some memory
        bbox = [[(svg.xmin-xoff)*dpi2mm, (svg.ymin-yoff)*dpi2mm], [(svg.xmax-xoff)*dpi2mm, (svg.ymax-yoff)*dpi2mm]]

        rd = Ruida()
        # bbox = rd.boundingbox(paths_list)     # same as above.

        if self.options.bbox_only:
                paths_list = [[ [bbox[0][0],bbox[0][1]], [bbox[1][0],bbox[0][1]], [bbox[1][0],bbox[1][1]],
                                [bbox[0][0],bbox[1][1]], [bbox[0][0],bbox[0][1]] ]]
                paths_list_cut = paths_list
                paths_list_mark = paths_list
                if cut_opt is not None and mark_opt is not None:
                        mark_opt = None         # once is enough.
        if self.options.move_only:
                paths_list      = rd.paths2moves(paths_list)
                paths_list_cut  = rd.paths2moves(paths_list_cut)
                paths_list_mark = rd.paths2moves(paths_list_mark)
        if cut_opt is None: cut_opt = mark_opt          # so that we have at least something to do.

        if self.options.dummy:
                with open('/tmp/thunderlaser.json', 'w') as fd:
                        json.dump({
                                'paths_bbox': bbox,
                                'cut_opt': cut_opt, 'mark_opt': mark_opt,
                                'paths_unit': 'mm', 'svg_resolution': svg.dpi, 'svg_resolution_unit': 'dpi',
                                'freq1': self.options.freq1, 'freq1_unit': 'kHz',
                                'paths': paths_list,
                                'cut':  { 'paths':paths_list_cut,  'color': cut_color  },
                                'mark': { 'paths':paths_list_mark, 'color': mark_color },
                                }, fd, indent=4, sort_keys=True, encoding='utf-8')
                print("/tmp/thunderlaser.json written.", file=sys.stderr)
        else:
                if cut_opt is None and mark_opt is None:
                  inkex.errormsg(gettext.gettext('ERROR: Both, Mark and Cut are disabled. Nothing todo.'))
                  sys.exit(0)
                if cut_opt is not None and mark_opt is not None:
                  nlay=2
                else:
                  nlay=1

                if bbox[0][0] < 0 or bbox[0][1] < 0:
                        inkex.errormsg(gettext.gettext('Warning: negative coordinates not implemented in class Ruida(), truncating at 0'))
                # rd.set(globalbbox=bbox)       # Not needed. Even slightly wrong.
                rd.set(nlayers=nlay)

                l=0
                if mark_opt is not None:
                  if len(paths_list_mark) == 0:
                    inkex.errormsg(gettext.gettext('ERROR: mark line color "'+mark_opt['color']+'": nothing found.'))
                    sys.exit(0)
                  cc = mark_color if type(mark_color) == list else [128,0,64]
                  rd.set(layer=l, speed=mark_opt['speed'], color=cc)
                  rd.set(layer=l, power=[mark_opt['minpow'], mark_opt['maxpow']])
                  rd.set(layer=l, paths=paths_list_mark)
                  l += 1

                if cut_opt is not None:
                  if len(paths_list_cut) == 0:
                    inkex.errormsg(gettext.gettext('ERROR: cut line color "'+cut_opt['color']+'": nothing found.'))
                    sys.exit(0)
                  cc = cut_color if type(cut_color) == list else [128,0,64]
                  rd.set(layer=l, speed=cut_opt['speed'], color=cc)
                  rd.set(layer=l, power=[cut_opt['minpow'], cut_opt['maxpow']])
                  rd.set(layer=l, paths=paths_list_cut)
                  l += 1

                device_used = None
                for device in self.options.devicelist.split(','):
                    fd = None
                    try:
                        fd = open(device, 'wb')
                    except:
                        pass
                    if fd is not None:
                        rd.write(fd)
                        print(device+" written.", file=sys.stderr)
                        device_used = device
                        break
                if device_used is None:
                        inkex.errormsg(gettext.gettext('Warning: no usable devices in device list (or bad directoy): '+self.options.devicelist))


if __name__ == '__main__':
    e = ThunderLaser()
    e.affect()
