import mido

mid = mido.MidiFile("mixed-nuts.mid")

with mido.open_output("LoopBe Internal MIDI 1", autoreset=True) as outport:
    for msg in mid.play():
        outport.send(msg)
