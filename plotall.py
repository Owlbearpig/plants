import glob
import re
import numpy as np
from numpy import fft
import time
from matplotlib import pyplot as plt
import cachedfunction
from pathlib import Path

emptyfolder = Path.cwd() / Path('Cprimus')
samplefolder = Path.cwd() / Path('Cprimus')

fmin = 0.1e12
fmax = 0.2e12


def findnametags(folder):
    filenames = [str(file) for file in folder.glob('**/*.txt')]

    pattern = "^.*[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}-[0-9]{2}-[0-9]{2}.[0-9]{6}-data-(.*?).txt$"

    nametags = []
    for filename in filenames:

        res = re.match(pattern, filename)

        if res:
            if not (res.group(1) in nametags):
                nametags.append(res.group(1))

    return (nametags)


def readFromFile(filename):
    t = []
    I = []
    import csv
    with open(filename, 'r', newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            t.append(float(row[0]))
            I.append(float(row[1]))
    return (t, I)


def THzFFT(t, I):
    dt = np.mean(np.diff(t))
    FD = fft.rfft(I)
    freq = fft.rfftfreq(len(I), dt)
    return (freq, FD)


def meanInRange(freq, FD, fmin, fmax):
    range = (freq >= fmin) & (freq <= fmax)
    FD = FD[range]
    return (np.mean(FD))


def meanFromFile(filename, fmin, fmax):
    (t, I) = readFromFile(filename)
    (freq, FD) = THzFFT(t, I)
    return meanInRange(freq, np.absolute(FD), fmin, fmax)


meanFromFileC = cachedfunction.cachedfunction(meanFromFile, 'funccache')


def dateFromFilename(filename):
    tmp = re.findall('[d{0-9}]{4}-[d{0-9}]{2}-[d{0-9}]{2}_[d{0-9}]{2}-[d{0-9}]{2}-[d{0-9}]{2}', filename)
    timetmp = time.strptime(tmp[0], '%Y-%m-%d_%H-%M-%S')
    return timetmp


def times2days(times):
    tmp = time.mktime((times[0].tm_year, times[0].tm_mon, times[0].tm_mday, 0, 0, 0, times[0].tm_wday, times[0].tm_yday,
                       times[0].tm_isdst))

    timestamps = []
    for t in times:
        timestamps.append(time.mktime(t))

    days = (np.array(timestamps) - tmp) / (24 * 60 * 60)

    return (days)


def getValues(datafolder, nametag):
    datafolder = str(datafolder)
    sample_files = glob.glob(datafolder + '*' + nametag + '.txt')
    sample_files = sample_files + glob.glob(datafolder + '*' + nametag + '_error.txt')
    ref_files = glob.glob(datafolder + '*' + nametag + '_ref.txt')
    ref_files = ref_files + glob.glob(datafolder + '*' + nametag + '_ref_error.txt')

    sample_files.sort()
    ref_files.sort()

    if len(sample_files) != len(ref_files):
        print('Error: Number of reference and sample files not equal!')
        print(len(sample_files))
        print(len(ref_files))

    sample_values = []
    sample_times = []
    ref_values = []

    for (ref_file, sample_file) in zip(ref_files, sample_files):
        sample_values.append(meanFromFileC(sample_file, fmin, fmax))
        ref_values.append(meanFromFileC(ref_file, fmin, fmax))
        sample_times.append(dateFromFilename(sample_file))

    return (np.array(sample_values) / np.array(ref_values), sample_times)


empties = findnametags(emptyfolder)
samples = findnametags(samplefolder)

# empties = empties[3:4]
# samples = samples[3:4]


for (empty, sample) in zip(empties, samples):
    emptyvalues, emptytimes = getValues(emptyfolder, empty)
    samplevalues, sampletimes = getValues(samplefolder, sample)

    values = samplevalues / np.mean(emptyvalues)
    days = times2days(sampletimes)

    plt.figure()
    ax = plt.gca()
    plt.title(sample)
    plt.plot(days, values, '.')
    plt.ylim((0.2, 1.4))
    ax.set_facecolor((0.8, 0.8, 0.8))
    for k in range(int(np.floor(np.min(days))), int(np.ceil(np.max(days)))):
        ax.axvspan(k + 8 / 24, k + 20 / 24, facecolor=(1, 1, 1), alpha=1, linewidth=0)

    plt.draw()
    plt.savefig('./savefigs/' + sample + '.png')
    plt.show()

del (meanFromFileC)
