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
import os
import csv
import math
from datetime import datetime, timedelta

from miditime.miditime import MIDITime


class Pebble(object):
    '''
    Lots of stuff cribbed from here: https://www.angio.net/personal/climb/speed

    TODO: Terminal velocity
    '''

    g = 9.8
    mass_grams = 141  # 5 oz, or a baseball

    epoch = datetime(2004, 1, 1)  # Not actually necessary, but optional to specify your own
    mymidi = None

    # min_value = 0
    # max_value = 5.7

    tempo = 120

    min_attack = 30
    max_attack = 255

    min_impact_duration = 1
    max_impact_duration = 4

    # min_duration = 1
    # max_duration = 5

    seconds_per_year = 10

    c_major = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
    c_minor = ['C', 'D', 'Eb', 'F', 'G', 'Ab', 'Bb']
    a_minor = ['A', 'B', 'C', 'D', 'E', 'F', 'F#', 'G', 'G#']
    c_blues_minor = ['C', 'Eb', 'F', 'F#', 'G', 'Bb']
    d_minor = ['D', 'E', 'F', 'G', 'A', 'Bb', 'C']
    c_gregorian = ['C', 'D', 'Eb', 'F', 'G', 'Ab', 'A', 'Bb']

    current_key = c_major
    base_octave = 2
    octave_range = 2

    def __init__(self):
        self.csv_to_miditime()

    def feet_to_meters(self, feet):
        return float(feet) * 0.3048

    def time_to_impact(self, height_meters):
        return math.sqrt(2 * float(height_meters) / self.g)

    def seconds_to_beats(self, seconds):  # Just for manually setting seconds
        return seconds * (self.tempo / 60)

    def read_csv(self, filepath):
        csv_file = open(filepath, 'rU')
        return csv.DictReader(csv_file, delimiter=',', quotechar='"')
    #
    # def round_to_quarter_beat(self, input):
    #     return round(input * 4) / 4

    def velocity_on_impact(self, height_meters):  # sqrt( 2 * g * height )
        return math.sqrt(2 * self.g * height_meters)

    def energy_on_impact(self, mass, velocity):  # Energy at splat time: 1/2 * mass * velocity2 = mass * g * height
        return (mass * velocity) / 2

    def energy_to_attack(self, datapoint):
        # Where does this data point sit in the domain of your data? (I.E. the min magnitude is 3, the max in 5.6). In this case the optional 'True' means the scale is reversed, so the highest value will return the lowest percentage.
        #scale_pct = self.mymidi.linear_scale_pct(0, self.maximum, datapoint)

        # Another option: Linear scale, reverse order
        scale_pct = self.mymidi.linear_scale_pct(0, self.maximum_energy, datapoint)
        # print 10**self.maximum
        # Another option: Logarithmic scale, reverse order
        # scale_pct = self.mymidi.log_scale_pct(0, self.maximum, datapoint, True, 'log')

        attack_range = self.max_attack - self.min_attack
        attack = self.min_attack + (scale_pct * attack_range)
        return attack

    def data_to_pitch_tuned(self, datapoint):
        # Where does this data point sit in the domain of your data? (I.E. the min magnitude is 3, the max in 5.6). In this case the optional 'True' means the scale is reversed, so the highest value will return the lowest percentage.
        #scale_pct = self.mymidi.linear_scale_pct(0, self.maximum, datapoint)

        # Another option: Linear scale, reverse order
        scale_pct = self.mymidi.linear_scale_pct(0, self.maximum_energy, datapoint, True)
        # print 10**self.maximum
        # Another option: Logarithmic scale, reverse order
        # scale_pct = self.mymidi.log_scale_pct(0, self.maximum, datapoint, True, 'log')

        # Pick a range of notes. This allows you to play in a key.
        mode = self.current_key

        #Find the note that matches your data point
        note = self.mymidi.scale_to_note(scale_pct, mode)

        #Translate that note to a MIDI pitch
        midi_pitch = self.mymidi.note_to_midi_pitch(note)
        print scale_pct, note

        return midi_pitch

    def energy_to_duration(self, datapoint):  # For impact duration, not fall
        scale_pct = self.mymidi.linear_scale_pct(self.minimum_energy, self.maximum_energy, datapoint)

        duration_range = self.max_impact_duration - self.min_impact_duration
        duration = self.min_impact_duration + (scale_pct * duration_range)
        return duration

    def make_falling_notes(self, data_timed, data_key, channel):
        note_list = []

        start_time = data_timed[0]['beat']

        for d in data_timed:
            note_list.append([
                [
                    d['beat'] - start_time,
                    self.mymidi.note_to_midi_pitch("C4"),  # pitch
                    100,  # attack
                    self.seconds_to_beats(d['duration_secs'])  # duration, in beats
                ],
                channel
            ])
        return note_list

    def make_splashing_notes(self, data_timed, data_key, channel):
        note_list = []

        start_time = data_timed[0]['beat']

        for d in data_timed:
            velocity = self.velocity_on_impact(d['distance_meters'])
            energy = self.energy_on_impact(self.mass_grams, velocity)
            note_list.append([
                [
                    d['beat'] - start_time + self.seconds_to_beats(d[data_key]),  # falling start plus duration of fall
                    # self.mymidi.note_to_midi_pitch("C4"),  # pitch
                    self.data_to_pitch_tuned(energy),  # pitch
                    self.energy_to_attack(energy),  # attack
                    self.energy_to_duration(energy)  # duration, in beats
                ],
                channel
            ])
            # print note_list
        return note_list

    def csv_to_miditime(self):
        raw_data = list(self.read_csv('data/groundwater_test.csv'))
        # filtered_data = self.remove_weeks(raw_data)
        #
        self.mymidi = MIDITime(self.tempo, 'media_out/pebble_test.mid', self.seconds_per_year, self.base_octave, self.octave_range, self.epoch)

        self.minimum_depth = self.feet_to_meters(self.mymidi.get_data_range(raw_data, 'depth_to_water_feet')[0])
        self.maximum_depth = self.feet_to_meters(self.mymidi.get_data_range(raw_data, 'depth_to_water_feet')[1])

        self.minimum_energy = self.energy_on_impact(self.mass_grams, self.velocity_on_impact(self.feet_to_meters(self.mymidi.get_data_range(raw_data, 'depth_to_water_feet')[0])))
        self.maximum_energy = self.energy_on_impact(self.mass_grams, self.velocity_on_impact(self.feet_to_meters(self.mymidi.get_data_range(raw_data, 'depth_to_water_feet')[1])))

        timed_data = []

        for r in raw_data:
            python_date = datetime.strptime(r["date"], "%Y-%m-%d")
            distance_meters = self.feet_to_meters(r['depth_to_water_feet'])
            days_since_epoch = self.mymidi.days_since_epoch(python_date)
            beat = self.mymidi.beat(days_since_epoch)
            timed_data.append({
                'days_since_epoch': days_since_epoch,
                'beat': beat,
                'distance_meters': distance_meters,
                'duration_secs': self.time_to_impact(distance_meters)
            })

        falling_note_list = self.make_falling_notes(timed_data, 'duration_secs', 1)
        splashing_note_list = self.make_splashing_notes(timed_data, 'duration_secs', 2)
        note_list = falling_note_list + splashing_note_list
        # Add a track with those notes
        self.mymidi.add_track(note_list)

        # Output the .mid file
        self.mymidi.save_midi()


if __name__ == "__main__":
    pebble = Pebble()
