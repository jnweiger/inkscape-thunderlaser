class Ruida
===========

The Rudia class is imported as a github submodule from https://github.com/jnweiger/ruida-laser and is used as follows:

```rd=Ruida()```
Generate a Ruida Object called `rd`. This object is used to store laser metadata, like speed and power settings, and the cut path data.
The exact interface is shown in src/thunderlaser-ruida.py -- currently it only implements one type of cutting. Either mark or cut. 
Colors, linewidth or other attributes are irrelevant.

class InkSvg
============

The InkSvg class is implemented in src/inksvg.py and implements converting an SVG file with almost all features into a correct paths list.
Known limitations are:

* Text rendering. Text elements are not represented in the output, but a warning is generated **"Warning: unable to draw text, please convert it to a path first."**
* Dotted or dashed lines. They are rendered as solid lines. inkscape-silhouette has code to support this.

class ThunderLaser
==================

This is the main class. It contains option parsing and the interface code to inkscape, the `effect()` method. It calls the `recursivelyTraverseSvg()` method from InkSvg to generate a path list.
The path list is converted in a format understood by the `rd.body()` method from Ruida. The contens can be saved as a json file ("dummy device" option) or formatted as a proper `*.rd` file including all
needed `header()` and `trailer()`. This can be either sent to a USB device or stored as a file.



