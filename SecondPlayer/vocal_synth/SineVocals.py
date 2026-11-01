#  from vocal_synth import audio as a
import numpy
import csv

SAMPLING_FREQ = 48000
SAMPLE_LEN = 1 / SAMPLING_FREQ
#  audioint = a.AudioInterface(a.get_index_by_name("Microsoft hanglekĂ©pzĹ‘ - Output"), output=True, rate=SAMPLING_FREQ, record=False)

# WIKIPDIA TABLE
table = """i 	240 	2400 	2160
y 	235 	2100 	1865
e 	390 	2300 	1910
ø 	370 	1900 	1530
ɛ 	610 	1900 	1290
œ 	585 	1710 	1125
a 	850 	1610 	760
ɶ 	820 	1530 	710
ɑ 	750 	940 	190
ɒ 	700 	760 	60
ʌ 	600 	1170 	570
ɔ 	500 	700 	200
ɤ 	460 	1310 	850
o 	360 	640 	280
ɯ 	300 	1390 	1090
u 	250 	595 	345""".splitlines()
csv_table = csv.reader(table, delimiter='\t', quotechar=None)
vowel_formants = {}
"""
Vowel formants, stored as "IPA vowel" -> (F0, F1, F2 etc.)
"""
for row in csv_table:
    vowel_formants[row[0].strip()] = (125, int(row[1].strip()), int(row[2].strip()))

def generate_vowel():
    pass