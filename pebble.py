#!/usr/bin/env python

#-----------------------------------------------------------------------------
# Name:        pebble.py
# Purpose:     Convert time-series data to a .mid file.
#
# Author:      Michael Corey <mcorey) at (cironline . org>
#
# Created:     2016/09/20
# Copyright:   (c) 2016 Michael Corey
# License:     Please see README for the terms under which this
#              software is distributed.
#-----------------------------------------------------------------------------
import math

from miditime.miditime import MIDITime


class Pebble(object):
    '''
    Lots of stuff cribbed from here: https://www.angio.net/personal/climb/speed

    TODO: Terminal velocity
    '''

    g = 9.8
    mass_grams = 141  # 5 oz, or a baseball

    def __init__(self):
        pass

    def time_to_splat(self, height_meters):
        return math.sqrt(2 * height_meters / self.g)


if __name__ == "__main__":
    pebble = Pebble()
