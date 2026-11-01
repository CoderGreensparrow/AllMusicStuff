import mido

mid = mido.MidiFile("beethoven_mond_3.mid")

with mido.open_output("Microsoft GS Wavetable Synth 0", autoreset=True) as outport:
    for msg in mid.play():
        outport.send(msg)
