import time

import mido

m = mido.Backend('mido.backends.rtmidi', load=True)
#  port = mido.ports.IOPort(m.open_input("LoopBe Internal MIDI 0"), m.open_output("LoopBe Internal MIDI 1"))
port = m.open_output("Microsoft GS Wavetable Synth 0")

"""class MidiEvent:
    def __init__(self,
                 messages: Container[mido.Message|mido.MetaMessage|mido.UnknownMetaMessage|mido.frozen.FrozenMessage|mido.frozen.FrozenMetaMessage|mido.frozen.FrozenUnknownMetaMessage],):
        A high-level class for representing a MIDI event.
        A "MIDI event" (not official term, I made it up), is a group of MIDI messages that accomplish one task.
        They can have custom parameters as well. (It's kinda like an SQL query to the piano.)
        But it can also be just a single MIDI event. (Though abstracting away messages too much can be bad to performance).
"""  # TODO this is a good idea for later, but too complex for now

class TrackedMessage:
    def __init__(self, track: int, msg: mido.Message|mido.MetaMessage):
        """
        A class that connects a track with a message.
        :param track: The track ID of the message. (Any integer.)
        :param msg: The mido.(Meta)Message.
        """
        self.track = track
        self.msg = msg

    def __repr__(self):
        return "TrMsg <in track " + str(self.track) + " -> '" + str(self.msg) + "'>"

class MidiMessages:
    def __init__(self):
        """A class for storing all MIDI messages (potentially from multiple files).
        ONLY SINGLE FILES FOR NOW.
        MIDI messages are stored in a dictionary:
        event T time (counted in MIDI ticks from the start of the song) -> [list of messages at that point in time]
        All messages have a track ID associated with them. The order of tracks is as listen in the MIDI file.
        (When loading multiple files, the tracks are continuously numbered as they are added.)
        TODO multi-file loading
        TODO tick discrepancies between multi-file loading"""
        self.tmsgs = {}
        """Short for TrackedMessages."""
        self.num_tracks = 0
        self.length = 0
        """Length of the whole song measured in ticks.
        Therefore, it marks the T absolute time of the last message(s)."""
        self.ticks_per_beat = None

    def load_midi_file(self, mid: mido.MidiFile):
        self.tmsgs.clear()  # DELETE LINE FOR MULTI-FILE LOADING!

        self.ticks_per_beat = mid.ticks_per_beat

        tracks = mid.tracks
        for i, track in enumerate(tracks):
            T = 0  # playback cursor (absolute time in file)
            for msg in track:
                if msg.time > 0:
                    T += msg.time
                if self.tmsgs.get(T) is None: self.tmsgs[T] = []  # add
                self.tmsgs[T].append(TrackedMessage(self.num_tracks, msg))
            if T > self.length:
                self.length = T

            self.num_tracks += 1

    def get(self, T):
        """Get messages at absolute T playback time (or playhead or playback cursor, all names are good.)"""
        return self.tmsgs.get(T)

    def get_length(self):
        """The length of the entire song, in ticks."""
        return self.length


class VirtualPiano:
    KEYBOARD_CHANGE_MARKER_PRESSED = 1
    KEYBOARD_CHANGE_MARKER_UNCHANGED = 0
    KEYBOARD_CHANGE_MARKER_RELEASED = -1

    def __init__(self, midi_messages: MidiMessages):
        """
        A virtual piano capable of simulating (kinda like "playing") the MIDI file tick-by-tick, forwards or backwards.
        For internal use.
        Initially, it is playing nothing. Calling next() the first time starts the song.
        :param midi_messages: The MidiMessages object containing MIDI data.
        :var T: The position of the playhead/playing cursor/absolute time in the MIDI playback. Measured in MIDI TICKS.
        :var mm: A MidiMessages object containing MIDI data.
        :var keyboard: A simulated keyboard. Every index in the list represents a MIDI note (0..127). At each index the value can be None (the note is
        :var keyboard_extra_messages: Any other MIDI messages that the keyboard gets at the moment. (Control change, program change, even meta-messages are included.)
        """
        self.T = -1
        self.mm = midi_messages
        self.keyboard = [None] * 128
        self.keyboard_change_marker = [self.KEYBOARD_CHANGE_MARKER_UNCHANGED] * 128
        """Marks at each tick if there was a change in keyboard notes.
        If the value at a note is KEYBOARD_CHANGE_MARKER_PRESSED (=1), then the note was just pressed.
        K_C_M_UNCHANGED (=0) means it's being held or not held at this tick at the spcified note.
        K_C_M_RELEASED (=-1) means it's being released at this tick."""
        self.keyboard_extra_msgs = []

    def reset(self):
        """Reset the whole keyboard to the start of the song."""
        self.T = -1
        self.keyboard = [None] * 128
        self.keyboard_change_marker = [self.KEYBOARD_CHANGE_MARKER_UNCHANGED] * 128
        self.keyboard_extra_msgs = []

    def _reset_keyboard_change_marker(self):
        self.keyboard_change_marker = [self.KEYBOARD_CHANGE_MARKER_UNCHANGED] * 128

    def _reset_keyboard_extra_msgs(self):
        self.keyboard_extra_msgs.clear()

    def is_playing(self):
        """Returns if there is still more of the piece left. (At the last tick, it returns True still.)"""
        if self.T > self.mm.get_length():
            return False
        return True

    def _test_midi_out(self, msg):
        """INTERNAL: As the piano progresses, send the signals to the port variable's midi device."""
        global port
        port.send(msg)

    def next(self):
        """Advance one tick forward in the MidiMessages. Calling it the first time starts the song.
        :return: If True, then that means there is more of the song left (or at least, it's the last note playing. If False, then the song has ended."""

        self._reset_keyboard_change_marker()
        self._reset_keyboard_extra_msgs()

        if self.T > self.mm.get_length():
            self.keyboard = [None] * 128
            return False

        self.T += 1

        tmsgs = self.mm.get(self.T)
        if tmsgs:
            for tmsg in tmsgs:
                msg = tmsg.msg
                if msg.type == "note_on":
                    if msg.velocity > 0:
                        self.keyboard[msg.note] = tmsg
                        self.keyboard_change_marker[msg.note] = self.KEYBOARD_CHANGE_MARKER_PRESSED
                        self._test_midi_out(tmsg.msg)  # TODO REMOVE
                    else:
                        self.keyboard[msg.note] = None
                        self.keyboard_change_marker[msg.note] = self.KEYBOARD_CHANGE_MARKER_RELEASED
                        self._test_midi_out(tmsg.msg)  # TODO REMOVE
                elif msg.type == "note_off":
                    self.keyboard[msg.note] = None
                    self.keyboard_change_marker[msg.note] = self.KEYBOARD_CHANGE_MARKER_RELEASED
                    self._test_midi_out(tmsg.msg)  # TODO REMOVE
                else:
                    self.keyboard_extra_msgs.append(tmsg)
                    if not tmsg.msg.is_meta:
                        self._test_midi_out(tmsg.msg)  # TODO REMOVE

        return True

    def get_keyboard(self):
        return self.keyboard

    def get_keyboard_extra_messages(self):
        return self.keyboard_extra_msgs

    def get_keyboard_copy(self):
        copy_keyboard = []
        for tmsg in self.keyboard:
            if tmsg is not None:
                copy_keyboard.append(TrackedMessage(tmsg.track, tmsg.msg))
            else:
                copy_keyboard.append(None)
        return copy_keyboard

    def get_keyboard_extra_messages_copy(self):
        copy_keyboard_extra_messages = self.keyboard_extra_msgs[::-1][::-1]
        return copy_keyboard_extra_messages

class PianoRoll:
    def __init__(self, midiMessages: MidiMessages, piano_roll_rolling_window = 0):
        """
        A virtual piano roll containing what keys are pressed down and when at any tick in time.
        :param midiMessages: The MidiMessages object containing MIDI data.
        :param piano_roll_rolling_window: The rolling window (aka. max length) of the piano roll. If the piano roll would get longer than this value, the oldest items will be deleted to make the roll have the right length. This makes the piano roll function like a 'rolling window of the MidiMessages'. VALUES: 0 means there is no restriction on the piano roll's length. Otherwise it shows how many TICKS LONG the piano roll can be.
        """
        self.mm = midiMessages
        self.vp = VirtualPiano(self.mm)
        self.piano_roll = []
        self.piano_roll_extra_msgs = []
        self.piano_roll_shift = 0
        """Essential for the rolling window to work correctly.
        If the first N items are deleted by the rolling window, we have to mark the absolute T of the first item to be able to identify the index of all of them."""
        self.piano_roll_rolling_window = piano_roll_rolling_window
        """The rolling window (aka. max length) of the piano roll. If the piano roll would get longer than this value,
        the oldest items will be deleted to make the roll have the right length.
        This makes the piano roll function like a 'rolling window of the MidiMessages'.
        VALUES: 0 means there is no restriction on the piano roll's length. Otherwise it shows how many TICKS LONG the piano roll can be."""

    def _correct_for_rolling_window(self):
        """INTERNAL: Corrects for the rolling window (aka. pops unneeded old elements."""
        if self.piano_roll_rolling_window > 0:
            while len(self.piano_roll) > self.piano_roll_rolling_window:
                self.piano_roll.pop(0)
                self.piano_roll_shift += 1

    def record_piano_roll(self, ticks=0):
        """Record all/some the possible states of the virtual piano to the "piano roll" (a list of virtual keyboard states each tick) by playing through the piece.
        :param ticks: The number of ticks to record. If it's greater than 0, then that many ticks will be recorded. If it's 0, the whole song will be recorded.
        :return: The VirtualPiano's is_playing() function's value, which marks if there was a new tick to be handled this tick or the song has ended."""

        if ticks == 0:
            while playing := self.next_tick_piano_roll():
                pass
        else:
            while (playing := self.next_tick_piano_roll()) and ticks > 1:
                ticks -= 1
        return playing

    def next_tick_piano_roll(self):
        """Record the next tick of piano roll.
        :return: The VirtualPiano's is_playing() function's value, which marks if there was a new tick to be handled this tick or the song has ended."""
        playing = self.vp.next()
        if playing:
            self.piano_roll.append(self.vp.get_keyboard_copy())
            self.piano_roll_extra_msgs.append(self.vp.get_keyboard_extra_messages_copy())
        return playing

    def get_rolling_window(self):
        """Gets the width of the rolling window."""
        return self.piano_roll_rolling_window

    def set_rolling_window(self, piano_roll_rolling_window):
        """Sets the width of the rolling window."""
        self.piano_roll_rolling_window = piano_roll_rolling_window

    def get_piano_roll_length(self):
        """Gets the true length of the piano roll."""
        return len(self.piano_roll)

    def get_piano_roll(self):
        return self.piano_roll

    def get_piano_roll_extra_msgs(self):
        return self.piano_roll_extra_msgs

    def get_tick(self, T):
        """
        Get a tick from the piano roll using absolute T ticks.
        :param T: The absolute T time ("playhead position in ticks") of the tick.
        :return: The virtual keyboard state at that tick.
        """
        return self.piano_roll[self.piano_roll_shift + T]

    def get_tick_extra_msgs(self, T):
        """
        Get a tick's extra messages from the piano roll using absolute T ticks.
        :param T: The absolute T time ("playhead position in ticks") of the tick.
        :return: The virtual keyboard's extra messages at that tick.
        """
        return self.piano_roll_extra_msgs[self.piano_roll_shift + T]


class Clock:
    def __init__(self, tempo=1000, N=10**5):
        """An implementation of a 'clock' that can keep all the cycles of a loop in a synchronized manner.
        :param tempo: The tempo to synchronize the cycle lengths to. Given in [seconds/N cycles]. Default is 1000.
        :param N: The N in the unit above. It shows how many cycles should pass per the given amount of seconds. Default is 10^5.
        """
        self.N = N
        self.start_time_of_N_cycles = 0
        self.next_cycle_time = 0
        self.end_time_of_N_cycles = 0
        self.next_cycle_index = 1  # the index of the next cycle
        self.tempo = tempo  # UNIT: [sec/100 cycles]

    def _start_next_N_cycles(self):
        self.next_cycle_index = 1
        self.start_time_of_N_cycles = time.perf_counter()
        self.end_time_of_N_cycles = self.start_time_of_N_cycles + self.tempo
        self.next_cycle_time = self.start_time_of_N_cycles + (self.tempo * self.next_cycle_index) / self.N

    def start_play(self, tempo=None):
        """
        Put before the loop. It starts the clock based on the given tempo.
        :param tempo: Set the tempo here, if you want to. Optional.
        :return: None
        """
        if tempo: self.tempo = tempo
        self._start_next_N_cycles()

    def end_of_loop_sleep(self):
        """
        Pan out the time of the loop (if needed) until the desired loop length is reached.
        :return: None
        """
        while time.perf_counter() <= self.next_cycle_time:
            pass
        self.next_cycle_index += 1
        if self.next_cycle_index == self.N + 1:
            self._start_next_N_cycles()
        self.next_cycle_time = self.start_time_of_N_cycles + (self.tempo * self.next_cycle_index) / self.N

    def set_tempo(self, tempo, N=None):
        """Set the tempo of the clock.
        :param tempo: Tempo. UNIT: [seconds/N cycles], which means how many seconds should pass every N cycles. The value of N can be set by this function as well or when initializing the class."""
        self.tempo = tempo
        if N: self.N = N
        self._start_next_N_cycles()
        #  print("Clock tempo: ", self.tempo, " seconds/", self.N, " cycles", sep="")

    def get_tempo(self):
        """Gets the tempo in [seconds/N cycles]. You can get the value of N using get_N(). To set both of them, use set_tempo(tempo, N)."""
        return self.tempo

    def get_N(self):
        """Gets the value of N in the unit used for the tempo here: [seconds/N cycles]."""
        return self.N


mm = MidiMessages()
mm.load_midi_file(mido.MidiFile(r"D:\PycharmProjects\MidiStuff\SineWavePiano\qian-ben-ying.mid"))
pr = PianoRoll(mm)
tempo = 300
c = Clock()
c.start_play(mido.tick2second(c.get_N(), mm.ticks_per_beat, mido.bpm2tempo(tempo)))
T = 0
playing = True
measured_tempo = 0
while playing:
    start = time.perf_counter()
    tempo = 120 + (T / (mm.ticks_per_beat * 4))
    c.set_tempo(mido.tick2second(c.get_N(), mm.ticks_per_beat, mido.bpm2tempo(tempo)))

    playing = pr.next_tick_piano_roll()
    if playing:
        for tmsg in pr.get_tick_extra_msgs(T):
            if tmsg.msg.type == "set_tempo":
                #  c.set_tempo(mido.tick2second(c.get_N(), mm.ticks_per_beat, tmsg.msg.tempo))
                pass
        if T % 120 == 0:
            for key in pr.get_tick(T):
                if key is not None:
                    print(key.track, end="")
                else:
                    print(" ", end="")
            print(pr.get_piano_roll_length(), tempo, measured_tempo)
        T += 1
        c.end_of_loop_sleep()
    end = time.perf_counter()
    measured_tempo = 1 / (((end - start) * mm.ticks_per_beat) / 60)
