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
from numpy import median
from datetime import datetime, timedelta

from miditime.miditime import MIDITime


class Pebble(object):
    '''
    Lots of stuff cribbed from here: https://www.angio.net/personal/climb/speed

    '''

    g = 9.8
    mass_grams = 141  # 5 oz, or a baseball

    epoch = datetime(2004, 1, 1)  # Not actually necessary, but optional to specify your own
    mymidi = None

    tempo = 120

    min_velocity = 30
    max_velocity = 127

    min_impact_duration = 1
    max_impact_duration = 4

    seconds_per_year = 1

    c_major = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
    c_minor = ['C', 'D', 'Eb', 'F', 'G', 'Ab', 'Bb']
    a_minor = ['A', 'B', 'C', 'D', 'E', 'F', 'F#', 'G', 'G#']
    c_blues_minor = ['C', 'Eb', 'F', 'F#', 'G', 'Bb']
    d_minor = ['D', 'E', 'F', 'G', 'A', 'Bb', 'C']
    c_gregorian = ['C', 'D', 'Eb', 'F', 'G', 'Ab', 'A', 'Bb']

    current_key = c_major
    base_octave = 2
    octave_range = 4

    def __init__(self):
        self.csv_to_miditime()

    def get_yearly_averages(self, rows, date_var, date_format, distance_var, unit):
        years = {}
        for r in rows:
            # filter out nulls
            if r[distance_var]:
                if r[distance_var] != '':
                    # extract year
                    year = datetime.strptime(r[date_var], date_format).year
                    # make a decade
                    decade = int('%s0' % (str(year)[:-1],))

                    # convert to meters (if feet):
                    if unit == 'feet':
                        distance_meters = self.feet_to_meters(float(r[distance_var]))
                    else:
                        distance_meters = float(r[distance_var])

                    if decade not in years:
                        years[decade] = [distance_meters]
                    else:
                        years[decade].append(distance_meters)

        # now get averages
        output = []
        for year, values in years.iteritems():
            yearly_avg = {'year': year, 'median_distance_meters': median(values)}
            output.append(yearly_avg)
            print yearly_avg

        # sort them
        return sorted(output, key=lambda k: k['year'])

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
        return math.sqrt(2 * self.g * float(height_meters))

    def energy_on_impact(self, mass, velocity):  # Energy at splat time: 1/2 * mass * velocity2 = mass * g * height
        return (mass * velocity) / 2

    def energy_to_velocity(self, datapoint):
        # Where does this data point sit in the domain of your data? (I.E. the min magnitude is 3, the max in 5.6). In this case the optional 'True' means the scale is reversed, so the highest value will return the lowest percentage.
        #scale_pct = self.mymidi.linear_scale_pct(0, self.maximum, datapoint)

        # Another option: Linear scale, reverse order
        scale_pct = self.mymidi.linear_scale_pct(0, self.maximum_energy, datapoint)
        # print 10**self.maximum
        # Another option: Logarithmic scale, reverse order
        # scale_pct = self.mymidi.log_scale_pct(0, self.maximum, datapoint, True, 'log')

        velocity_range = self.max_velocity - self.min_velocity
        velocity = self.min_velocity + (scale_pct * velocity_range)
        return velocity

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
                    self.mymidi.note_to_midi_pitch("C4"),  # pitch (set manually for drop)
                    100,  # velocity
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
                    self.data_to_pitch_tuned(energy),  # pitch
                    self.energy_to_velocity(energy),  # velocity
                    self.energy_to_duration(energy)  # duration, in beats
                ],
                channel
            ])
        return note_list

    def csv_to_miditime(self):
        # raw_data = list(self.read_csv('data/groundwater_test.csv'))
        raw_data = list(self.read_csv('data/15S18E30L001M_clean.csv'))

        # yearly_data = self.get_yearly_averages(raw_data, 'Date', "%m/%d/%Y", 'wl(m)', 'meters')
        yearly_data = self.get_yearly_averages(raw_data, 'Measurement_Date', "%m-%d-%Y", 'GSWS', 'feet')

        self.mymidi = MIDITime(self.tempo, 'media_out/pebble_longterm.mid', self.seconds_per_year, self.base_octave, self.octave_range, self.epoch)

        self.minimum_depth = self.mymidi.get_data_range(yearly_data, 'median_distance_meters')[0]
        self.maximum_depth = self.mymidi.get_data_range(yearly_data, 'median_distance_meters')[1]

        self.minimum_energy = self.energy_on_impact(self.mass_grams, self.velocity_on_impact(self.mymidi.get_data_range(yearly_data, 'median_distance_meters')[0]))
        self.maximum_energy = self.energy_on_impact(self.mass_grams, self.velocity_on_impact(self.mymidi.get_data_range(yearly_data, 'median_distance_meters')[1]))

        timed_data = []

        for r in yearly_data:
            # python_date = datetime.strptime(r["Date"], "%Y-%m-%d")
            python_date = datetime.strptime('1/1/%s' % r["year"], "%m/%d/%Y")
            distance_meters = r['median_distance_meters']
            days_since_epoch = self.mymidi.days_since_epoch(python_date)
            beat = self.mymidi.beat(days_since_epoch)
            timed_data.append({
                'days_since_epoch': days_since_epoch,
                'beat': beat,
                'distance_meters': distance_meters,
                'duration_secs': self.time_to_impact(distance_meters)
            })

        falling_note_list = self.make_falling_notes(timed_data, 'duration_secs', 0)
        splashing_note_list = self.make_splashing_notes(timed_data, 'duration_secs', 1)

        # Add a track with those notes
        self.mymidi.add_track(falling_note_list)
        self.mymidi.add_track(splashing_note_list)

        # Output the .mid file
        self.mymidi.save_midi()


if __name__ == "__main__":
    pebble = Pebble()
