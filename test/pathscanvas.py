#! /usr/bin/python
#
# pathcanvas.py -- load a paths list from json and visualize it.
#
# Requires:
#  apt-get install python-pygoocanvas
#  zypper in python-goocanvas

import sys, json, gtk, random
from goocanvas import *

numbers=False           # set to True to add node numbers to nodes.
incremental=0           # color the path, when SPACE pressed.

### window, canvas and navigation setup:

def key_press(win, ev, c):
  global incremental

  s = c.get_scale()
  key = chr(ev.keyval & 0xff)
  if   key == '+':  c.set_scale(s*1.2)
  elif key == '-':  c.set_scale(s*.8)
  elif key == ' ':
    show_poly(root, path=data['paths'][incremental], xoff=30, yoff=50, idx=incremental, color="red", width=0.3)
    if incremental < len(data['paths'])-1:
      incremental += 1
  elif ev.keyval in (65288, 65535, 65507):      # bs, del, ctrl-h
    if incremental > 0:
      incremental -= 1
    show_poly(root, path=data['paths'][incremental], xoff=30, yoff=50, idx=incremental, color="black", width=0.3)
  elif ev.keyval <= 255:
    gtk.main_quit()
  else:
    print("undefined key: " + str(ev.keyval))

def button_press(win, ev):
  win.click_x = ev.x
  win.click_y = ev.y

def button_release(win, ev):
  win.click_x = None
  win.click_y = None

def motion_notify(win, ev, c):
  try:
    # 3.79 is the right factor for units='mm'
    dx = (ev.x-win.click_x) / c.get_scale() / 3.79
    dy = (ev.y-win.click_y) / c.get_scale() / 3.79
    win.click_x = ev.x
    win.click_y = ev.y
    (x1,y1,x2,y2) = c.get_bounds()
    c.set_bounds(x1-dx,y1-dy,x2-dx,y2-dy)
  except:
    pass

win = gtk.Window()
canvas = Canvas(units='mm', scale=1)
canvas.set_size_request(1000, 600)
root = canvas.get_root_item()

win.connect("destroy", lambda x: gtk.main_quit())
win.connect("key-press-event", key_press, canvas)
win.connect("motion-notify-event", motion_notify, canvas)
win.connect("button-press-event", button_press)
win.connect("button-release-event", button_release)


### end of window canvas and navigation setup


def translate_poly(poly,xoff,yoff,scale=1):
  tuplepath=[]
  for i in poly: tuplepath.append( tuple([i[0]*scale+xoff, i[1]*scale+yoff]) )
  return tuplepath

def show_poly(canvas, path = [(0,0),(20,0),(10,20),(0,0)], xoff=0, yoff=0, idx=1, width=0.2, color="black"):
  """ default path is a downward pointing triangle.
      Both, a list of lists, and a list of tuples is accepted.
  """
  tuplepath=translate_poly(path, xoff, yoff)
  p = Points(tuplepath)         # cannot handle 2-element lists, need 2-element tuples.
  poly = Polyline(parent=canvas, points=p, line_width=width, stroke_color=color)

  if idx is not None:
    for C in path:
      text = Text(parent=canvas, text=idx, font="4", fill_color="blue")
      idx += 1
      text.translate(C[0]+xoff+random.uniform(-.5,0), C[1]+yoff+random.uniform(-.5,0))
      text.scale(.15,.15)

data = json.load(open(sys.argv[1]))
idx = 1
data['paths'] = data['mark']['paths'] + data['cut']['paths']
for path in data['mark']['paths']:
  show_poly(root, path=path, width=0.2, xoff=30, yoff=50, idx=None)
  idx += len(path)
for path in data['cut']['paths']:
  show_poly(root, path=path, width=0.4, xoff=30, yoff=50, idx=None)
  idx += len(path)

# show_poly(root, path = [(0,0),(20,0),(10,20),(0,0)], xoff=30, yoff=50)

win.add(canvas)
win.show_all()
gtk.main()

