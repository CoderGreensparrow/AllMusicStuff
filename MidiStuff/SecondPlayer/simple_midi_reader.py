import mido

m = mido.Backend('mido.backends.rtmidi', load=True)

mid = mido.MidiFile(r"D:\PycharmProjects\MidiStuff\SineWavePiano\qian-ben-ying.mid")

for i, msg in enumerate(mid):
    print(msg)
    if i == 40:
        break