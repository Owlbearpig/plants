import matplotlib.pyplot as plt
from paths import leermessung_dir, messung_dir
import numpy as np
from numpy import fft, mean
import re
from datetime import datetime

"""
20 positions (not all are with plants)
value of a measurement is yf_sam / yf_ref with eg. yf_sam = mean(abs(FFT(sample)[f_min:f_max])).

1. Since we don't have a 1:1 ratio between measurement count and empties count we
calculate average value of all the empty measurements (measurements taken over 1 day) and use that, perhaps?

2. val_sample / val_empties, where val empties is averaged over the day.

"""


class DP:
    """
    Datapoint class, stores info about a measurement point in a single object
    """

    def __init__(self, filepath):
        self.filepath = filepath

        # meta data attributes
        self.date = None  # datetime (time of measurement)
        self.measurement_type = None  # ref or meas
        self.pos_label = None  # eg. 01
        self.coordinates = (None, None)  # stage_pos_1, stage_pos_2
        self.plant = None  # plant name, mais, tomate, gurke, grass etc.
        self.tk = None  # trockenstress or kontrolle ??
        self.some_number = None  # secret number

        self.reference_dp = None  # associated reference

        self.set_metadata() # gets all the stuff from the filename

        # calculate single value based on data
        self.value = self.calc_value()

        # last step is to calculate sample.value / reference.value and set time since first measurement
        self.referenced_value, self.dt = None, None

    def set_metadata(self):
        # match filename
        file_pattern = '^.*([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}-[0-9]{2}-[0-9]{2}.[0-9]{6})(.*?)$'
        file_match = re.match(file_pattern, self.filepath.stem)
        date_group, info_group = file_match[1], file_match[2]

        # set date
        self.date = datetime.strptime(date_group, '%Y-%m-%dT%H-%M-%S.%f')

        # split info part of filename
        str_splits = info_group.split('-')

        # I don't know what these 2 values are
        if len(str_splits) == 7:
            self.tk, self.some_number = str_splits[3], str_splits[4]

        # set pos and plant name
        pos_pattern = '^.*([0-9]{2})(_*)([a-z]*?)$'
        info_match = re.match(pos_pattern, str_splits[2])
        self.pos_label = info_match[1]
        try:
            self.plant = info_match[3]
        except IndexError:
            self.plant = None

        # set measurement type
        self.measurement_type = 'ref' if ('ref' in str_splits[2]) else 'meas'

        # set stage coordinates
        x, y = float(str_splits[-2].replace(' mm', '')), float(str_splits[-1].replace(' mm', ''))
        self.coordinates = (x, y)

    def calc_value(self):
        f_min, f_max = 0.1, 0.2  # range of freq. slice

        data = np.loadtxt(self.filepath)
        data[:, 1] -= mean(data[:100, 1])  # offset correction

        t, yt = data[:, 0], data[:, 1]  # more readable

        yf = fft.rfft(yt)  # fft

        dt = float(np.mean(np.diff(t)))  # sample spacing
        freq = fft.rfftfreq(len(yt), dt)  # freqs

        slice_ = (freq >= f_min) & (freq <= f_max)  # selected frequency range (THz)

        value = np.mean(np.abs(yf[slice_]))  # res = mean(spectrum slice)

        return value


def evaluate(dps):
    # 1. sort dps by date
    sorted_dps = sorted(dps, key=lambda dp: dp.date)

    t0 = sorted_dps[0].date

    # 2. match dps assuming before each measurement comes a reference and set sample.value / reference.value
    matched_dps = []
    for i, dp in enumerate(sorted_dps):
        if dp.measurement_type == 'ref':
            continue

        dp.reference_dp = sorted_dps[i-1]
        matched_dps.append(dp)

        dp.referenced_value = dp.value / sorted_dps[i - 1].value  # sample / ref
        dp.dt = (dp.date - t0).seconds / 60 + (dp.date - t0).days * 1440  # seconds / 60 + days * 24 * 60

    return matched_dps


if __name__ == '__main__':
    # find all txt files
    empties = [file for file in leermessung_dir.glob('**/*.txt')]
    samples = [file for file in messung_dir.glob('**/*.txt')]

    empty_dps = [DP(empty_meas) for empty_meas in empties]
    sample_dps = [DP(sample) for sample in samples]

    empties_evaluated = evaluate(empty_dps)
    samples_evaluated = evaluate(sample_dps)

    positions = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10',
                 '11', '12', '13', '14', '15', '16', '17', '18', '19', '20']

    # average of all the empties measurements for each position
    empties_averages = {}
    for pos_label in positions:
        empties_averages[pos_label] = mean([x.referenced_value for x in empties_evaluated if (x.pos_label == pos_label)])

    # this plots the referenced_value / empties average at that position
    # (theres a 44 min gap at 2022-02-15T12-33-38.060184-data-pos13_weizen-kontrolle-2-98.000 mm-1110.000 mm)
    for pos_label in positions:
        t, y = [], []
        for dp in samples_evaluated:
            if dp.pos_label == pos_label:
                t.append(dp.dt)
                val = dp.referenced_value / empties_averages[pos_label]
                y.append(val)

        plt.scatter(t, y, label='pos_' + pos_label)
    plt.ylabel('avg(sam)/avg(ref_s) / avg(empty)/avg(ref_e)')
    plt.xlabel('Time in minutes')
    plt.title('Empties, pos 1-20 with time. Range: 0.2-1.2 THz')
    plt.legend()
    plt.show()
