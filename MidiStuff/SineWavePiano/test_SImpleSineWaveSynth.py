import time
from math import pi, log10, sin

import midi as m
import mido
import numpy as np

import matplotlib.pyplot as plt

import audio as a

mint = m.MidiIO(m.MODE_IN_ONLY, ["LoopBe Internal MIDI 0"], False)
SAMPLING_FREQ = 48000
SAMPLE_LEN = 1 / SAMPLING_FREQ
audioint = a.AudioInterface(a.get_index_by_name("Microsoft hanglekĂ©pzĹ‘ - Output"), output=True, rate=SAMPLING_FREQ, record=False)

MAX_AMPLITUDE = 60000
AMPLITUDE = 20000
current_sine_waves = []

def get_note_freq(midi_note: int):
    # https://en.wikipedia.org/wiki/12_equal_temperament#Calculating_absolute_frequencies
    root = 1.0594630943592953  # math.pow(2, 1/12); twelfth root of two
    A4 = 440

    frequency = A4*(root**(midi_note-69))  # midi note A4 = 69
    return frequency

def sine_function_at_t(A, freq, t):
    return A * sin(2*pi*freq*t)

def square_function_at_t(A, freq, t):
    return A if A * sin(2*pi*freq*t) > 0 else -A

formants = [0.7, 0.3, 0, 0, 0.01, 0.01]  # normalized 0 and 1
multipliers = []
for i in range(0, len(formants)):
    multipliers.append((i+2) / (i+1))
    for j in range(i+1, 2-1, -1):
        multipliers[i-1] *= j / (j-1)
len_formants = len(formants)
def my_function_at_t(A, freq, t):
    sample = 0
    current_freq = freq
    for i in range(len_formants):
        if formants[i] != 0:
            sample += sine_function_at_t(formants[i]*A, current_freq, t)
            current_freq = freq * multipliers[i]
    return sample

samples = []

t = 0
real_formants = 0
for i in formants:
    if i > 0:
        real_formants += 1
max_note_num = 36 // real_formants - 1
# max_note_num = 7
max_note_num = 30
print("Polyphony up to", max_note_num, "notes.")

while True:
    msg = mint.get_pending_msg([m.MSG_TYPE_CLOCK])
    if msg:
        if msg.type in [m.MSG_TYPE_NOTE_ON]:
            if msg.velocity > 0:
                current_sine_waves.append((msg.note, msg.velocity, t))
                # remove too many notes
                if len(current_sine_waves) > max_note_num:
                    current_sine_waves.pop(0)
            elif msg.velocity == 0:
                for i, midi_note_start_time in enumerate(current_sine_waves):
                    if midi_note_start_time[0] == msg.note:
                        current_sine_waves.pop(i)
            number_of_waves = len(current_sine_waves)
            current_amplitude = AMPLITUDE if number_of_waves * AMPLITUDE < MAX_AMPLITUDE else MAX_AMPLITUDE / number_of_waves

    # synthesize sound
    sample = 0
    for midi_note, midi_velocity, start_time in current_sine_waves:
        freq = get_note_freq(midi_note)
        this_t = t - start_time
        A = current_amplitude * ((midi_velocity) / 127)**2 / log10(freq - 20) * (1/(this_t*10+1))
        # A = current_amplitude * ((midi_velocity) / 127)**2 / log10(freq - 20)
        sample += my_function_at_t(A, freq, this_t)
    #  samples.append(sample)
    #  sample *= 0
    audioint.write(
        [sample, sample]
    )  # apparently this thing blocks, but that's awesome, because that means that if the function is fast enough, then this replaces a time.sleep for the t increase
    t += SAMPLE_LEN

#  audioint.write(samples)
plt.plot(samples)
plt.show()