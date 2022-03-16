import matplotlib.pyplot as plt
#from paths import leermessung_dir, messung_dir
from pathlib import Path
import numpy as np
from numpy import fft, mean
import re
from datetime import datetime
import time

"""
20 positions (not all are with plants)
value of a measurement is yf_sam / yf_ref with eg. yf_sam = mean(abs(FFT(sample)[f_min:f_max])).

1. Since we don't have a 1:1 ratio between measurement count and empties count we
calculate average value of all the empty measurements (measurements taken over 1 day) and use that, perhaps?

2. val_sample / val_empties, where val empties is averaged over the day.

"""

########## HINWEIS: Im Messordner darf keine WEITERE Datei außer den Messdaten sein! Zum Beispiel nicht die Datei mit den Messpositionen. ##########

### Set path of measurement data ###
#data_dir = Path('/home/ladakh/Promotion/Pflanzenmessdaten/Linea/Fundecundo/')
data_dir = Path('E:\measurementdata\PlantData\Messung_Linea')

# full path to leermessung and measurement
leermessung_dir, messung_dir = data_dir / "empty", data_dir / "measurement"
# full path to Results folder (which is created if not existent)
results_dir = data_dir / 'results'
results_dir.mkdir(parents=True, exist_ok=True)

print(f'Pfad der Leermessung: {str(leermessung_dir)}')
print(f'Pfad der Pflanzenmessdaten: {str(messung_dir)}')


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
        self.plant = None  # plant name, mais, tomate, gurke, grass etc.
        self.tk = None  # trockenstress or kontrolle ??
        self.plant_idx = None  # plant number label

        self.reference_dp = None  # associated reference

        self.set_metadata() # gets all the stuff from the filename

        # calculate single value based on data
        self.value = self.calc_value()

        # last step is to calculate sample.value / reference.value and set time since first measurement
        self.referenced_value, self.dt = None, None

    def __repr__(self):
        return f"Measurement date: {self.date}, type: {self.measurement_type}, pos: {self.pos_label}, " \
               f"plant: {self.plant}, plant_idx: {self.plant_idx}"

    """ example file names
    empties:
    2022-03-09T10-14-10.290682-data-pos01-88.000 mm-30.000 mm.txt
    2022-03-09T10-15-09.410776-data-ref02-88.000 mm-80.000 mm.txt
    
    fulls:
    2022-03-11T11-55-37.771313-data-ref01-88.000 mm-1.000 mm.txt
    2022-03-11T11-56-15.030344-data-pos01_weizen_kontrolle4-88.000 mm-30.000 mm.txt
    """

    def set_metadata(self):
        # match filename
        file_pattern = '^.*([0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}-[0-9]{2}-[0-9]{2}.[0-9]{6})(.*?)$'
        file_match = re.match(file_pattern, self.filepath.stem)
        date_group, info_group = file_match[1], file_match[2]

        # set date
        self.date = datetime.strptime(date_group, '%Y-%m-%dT%H-%M-%S.%f')

        match_expr = r"^.{6}([a-z]*)([0-9]*)_*([a-z]*)_*([a-z0-9]*)(.*)$"
        match = re.match(match_expr, info_group)
        self.pos_label = match[2]
        self.plant = match[3]
        try:
            self.tk, self.plant_idx = match[4][:-1], match[4][-1]
        except IndexError:
            pass

        if "ref" in match[1]:
            self.measurement_type = "ref"
        else:
            self.measurement_type = "meas"

        print(self)

    def calc_value(self):
        f_min, f_max = 0.1, 0.3  # range of freq. slice

        data = np.loadtxt(self.filepath)
        data[:, 1] -= mean(data[:10, 1])  # offset correction

        t, yt = data[:, 0], data[:, 1]  # more readable

        yf = fft.rfft(yt)  # fft

        dt = float(np.mean(np.diff(t)))  # sample spacing
        freq = fft.rfftfreq(len(yt), dt)  # freqs

        slice_ = (freq >= f_min) & (freq <= f_max)  # selected frequency range (THz)

        value = np.mean(np.abs(yf[slice_]))  # res = mean(spectrum slice)

        return value

def startofthisday(zeitangabe): #wandelt die gegebene Zeitangabe in genau den gleichen Tag um, aber setzt die Uhrzeit auf 00:00
    a_t0=time.gmtime(datetime.timestamp(zeitangabe))
    tmp=time.mktime((a_t0.tm_year, a_t0.tm_mon, a_t0.tm_mday, 0,0,0, a_t0.tm_wday, a_t0.tm_yday,  a_t0.tm_isdst))
    startofthisday_zeitangabe = datetime.fromtimestamp(tmp)
    return(startofthisday_zeitangabe)
    
def evaluate(dps):
    # 1. sort dps by date
    sorted_dps = sorted(dps, key=lambda dp: dp.date)

    t0 = sorted_dps[0].date #dies ist der Startzeitpunkt, an dem die erste Messung stattgefunden hat
    t0startofday = startofthisday(sorted_dps[0].date) #nimmt statt dem exakten Messbeginn den gleichen Tag, aber zur Uhrzeit 00:00

    # 2. match dps assuming before each measurement comes a reference and set sample.value / reference.value
    matched_dps = []
    ###matched_dps_startingpoint = []
    for i, dp in enumerate(sorted_dps):
        if dp.measurement_type == 'ref':
            continue

        dp.reference_dp = sorted_dps[i-1]
        matched_dps.append(dp)
        dp.referenced_value = dp.value / sorted_dps[i - 1].value  # sample / ref
        dp.dt = (dp.date - t0).seconds / 60 + (dp.date - t0).days * 1440  # seconds / 60 + days * 24 * 60 #dies ist der Originalcode von Alex, bei dem der Zeitpunkt "0" exakt dem Zeitpunkt der ersten Messung entspricht
        #dp.dt = ((dp.date - t0startofday).seconds / 60 + (dp.date - t0startofday).days * 1440) / (60*24) # seconds / 60 + days * 24 * 60 # und dann noch durch (60+24), um von Minuten in Tage umzurechnen

    return matched_dps


if __name__ == '__main__':
    # find all txt files
    empties = [file for file in leermessung_dir.glob('**/*.txt')]
    samples = [file for file in messung_dir.glob('**/*.txt')]
    #dp0 = DP(empties[0])
    empty_dps = [DP(empty_meas) for empty_meas in empties]
    sample_dps = [DP(sample) for sample in samples]

    empties_evaluated = evaluate(empty_dps)
    samples_evaluated = evaluate(sample_dps)

    """positions = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10',
                 '11', '12', '13', '14', '15', '16', '17', '18', '19', '20']"""
    """positions = ['01', '02', '03', '05', '06', '08', '09', '10',
                 '11', '13', '14', '15', '16', '18', '19', '20']"""
    #positions = ['01', '05', '09', '13', '15', '19'] #nur Weizen
    #positions = ['02', '08', '10', '14', '18', '20'] #nur Mais
    #positions = ['03', '06', '11', '16'] #nur leere Halter
    positions = ['06', '02']

    # average of all the empties measurements for each position
    empties_averages = {}
    for pos_label in positions:
        empties_averages[pos_label] = mean([x.referenced_value for x in empties_evaluated if (x.pos_label == pos_label)])

    # this plots the referenced_value / empties average at that position

    for pos_label in positions:
        t, y = [], []
        for dp in samples_evaluated:
            if dp.pos_label == pos_label:
                t.append(dp.dt)
                val = dp.referenced_value / empties_averages[pos_label]
                #print(dp.filepath.stem)
                #print(pos_label)
                y.append(val)
        
        plt.plot(t, y, 'o', markersize=1, label='pos' + pos_label)
        
        #plottet Tag-Nacht-Rythmus
        ax=plt.gca()
        ax.set_facecolor((0.8, 0.8, 0.8))
        #ax.axes.xaxis.set_visible(False) #blendet die x-Achse aus
        for k in range(int(np.floor(np.min(t))), int(np.ceil(np.max(t)))):
                ax.axvspan(((k+8/24)), ((k+22/24)), facecolor=(1,1,1), alpha=1, linewidth=0) #Licht an von 8 Uhr bis 22 Uhr
        
    plt.ylabel('Transmission')
    plt.xlabel('Time (d)')
    plt.title('Measured THz data')
    #plt.xlim(xmin=0) #lässt das Diagramm immer bei x=0 beginnen
    plt.legend()
    plt.savefig(str(results_dir)+'/result'+'.png',dpi=500)
    plt.show()
    print("Das Diagramm wurde geplottet.")

