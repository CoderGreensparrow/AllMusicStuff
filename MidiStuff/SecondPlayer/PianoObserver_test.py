import time

import mido

m = mido.Backend('mido.backends.rtmidi', load=True)
#  port = mido.ports.IOPort(m.open_input("LoopBe Internal MIDI 0"), m.open_output("LoopBe Internal MIDI 1"))
port = m.open_output("LoopBe Internal MIDI 1")

class VirtualPianoKey:
    def __init__(self):
        self.tracks_to_velocities = {}
        self.pressed = False
        """Shows if the note is pressed down at all."""
        self.pressed_this_tick = False
        """Shows if the note is pressed down at THIS TICK RIGHT NOW.
        This information is only useful in the piano roll."""
        self.max_velocity = 0
        """Shows what velocity the key gets from what track
        key = track index
        value = velocity
        Fills up as more and more tracks play on it."""

    def copy_state(self, virtualPianoKey):
        """Copies the state of another instance of virtual piano key"""
        self.tracks_to_velocities = virtualPianoKey.tracks_to_velocities
        self.pressed = virtualPianoKey.pressed
        self.pressed_this_tick = virtualPianoKey.pressed_this_tick
        self.max_velocity = virtualPianoKey.max_velocity

    def set_velocity_from_track(self, track, velocity):
        self.tracks_to_velocities[track] = velocity

        if sum(self.tracks_to_velocities.values()) > 0:
            self.pressed = True
        else:
            self.pressed = False

        self.max_velocity = max(self.tracks_to_velocities.values())

    def is_pressed(self):
        return self.pressed

    def is_pressed_this_tick(self):
        return self.pressed_this_tick

    def update_pressed_this_tick(self, value: bool):
        """INTERNAL: Must be called after every iteration of the virtual piano and set to False, once it's been saved to the piano roll.
        It sets the pressed_this_tick to the given value."""
        self.pressed_this_tick = value

    def get_velocity_with_track(self):
        pressed_tracks_to_velocities = {}
        for key, val in self.tracks_to_velocities.items():
            if val > 0:
                pressed_tracks_to_velocities[key] = val
        return pressed_tracks_to_velocities

    def get_max_velocity(self):
        return self.max_velocity

    def __str__(self):
        if self.pressed_this_tick:
            return "VirtualPianoKey (max.vel. " + str(self.max_velocity) + ") PRESSED DOWN THIS TICK"
        elif self.pressed:
            return "VirtualPianoKey (max.vel. " + str(self.max_velocity) + ") held"
        else:
            return "VirtualPianoKey (max.vel. " + str(self.max_velocity) + ") IS UP"

class PointInTimeMsg:
    def __init__(self, track, meta: bool, type_, attr: dict):
        self.track = track
        self.meta = meta
        """Specifies if a message is a midi meta message or a normal midi message."""
        self.type = type_
        self.attr = attr

    def __str__(self):
        return "PointInTimeMsg {" + "track: " + str(self.track) + ", meta: " + str(self.meta) + ", type: '" + self.type + "', attr: " + str(self.attr) + "}"


class PianoObserver:
    def __init__(self, midi_file, user_track_indices, machine_track_indices):
        """
        :param midi_file: Path to the MIDI file.
        """
        self.mid = mido.MidiFile(midi_file)
        self.tracks = self.mid.tracks
        self.ticks_per_beat = self.mid.ticks_per_beat
        self.T = 0
        """The current position of the (imaginary) playback cursor in the song relative to the start of the song.
        Measured in TICKS since the start of the song.
        It's always adjusted by the v_T variable.
        But the v_T variable is adjusted by how the user plays.
        And how much the user's tempo is payed attention to is adjusted by Lt ('leeway of tempo')."""
        self.v_T = 0
        """The speed of the change of the playback cursor (T). UNIT OF TEMPO: MICROSECONDS PER QUARTER NOTE."""
        self.Lt = 0
        """Leeway of tempo: Shows the level at which the computer pays attention to the tempo dictated by the user.
        If Lt is greater, the user's tempo matters more.
        If Lt is lesser, the MIDI file's original tempo matters more.
        It's a value between 0 and 1. (The ends mark situations in which only one or the other's tempo matters, as expected.)

        This value determines how v_T is changed.
        
        DETAILS LATER."""
        self._virtual_piano_T = 0
        """INTERNAL: The current playback cursor of the virtual piano IN TICKS."""
        self._virtual_piano_track_msg_index_per_track = []
        """INTERNAL: Where are we in reading through the msgs of each track (machine or user)?
        INITIALIZED IN initialize_piano_roll."""
        self._virtual_piano_msg_countdown_per_track = []
        """INTERNAL: The remaining time in ticks until the current message (as per the index var. above) is played per track."""
        self._virtual_piano_track_end_reached = []
        """Turns True one-by-one as the last MIDI messages per track are reached."""
        self.virtual_piano = []
        for i in range(128):
            self.virtual_piano.append(VirtualPianoKey())
        """INTERNAL: The virtual piano. Each key stores """
        self.virtual_piano_point_in_time = []
        """Every non-note message."""
        self.piano_roll_buffer_shift = 0
        self.piano_roll_buffer_window_width = self.mid.ticks_per_beat * 20
        self.piano_roll_buffer = []
        """Stores what notes are pressed down at each point in time. "Point in time" means some amount of ticks away from the start of the song.
        So it's an "associative array" of values where the keys are T values, and the values are tuples of notes which are down at that point in time.
        ACTUALLY, instead of an "associative array", it's a simple array, but there is another variable which shows the T tick of the first element.
        This way, the whole buffer can be "shifted in time", aka. all other element's real T time can be calculated from FIRST_ELEMENT_T + SOME_ELEMENT_INDEX.
        The variable used to do this is piano_roll_buffer_shift.
        
        The buffer contains elements into the future, since it shows all pressed notes AROUND THE PLAYBACK CURSOR.
        The piano_roll_buffer_window_width shows the full width of the buffer, from past to future.
        """
        self.piano_roll_buffer_point_in_time = []
        """A counterpart to the main piano roll that contains point-in-time events (like control change, sysex etc.)."""
        self.piano_roll_buffer_end = None
        """A number showing length of the piano buffer using the absolute position of the playback cursor.
        (Essentially the last tick's time that exists in the buffer + 1)
        A value of None means the piano buffer still has more data to load and we don't know (and don't need to care) about the end of the data."""

        self.user_track_indices = user_track_indices
        """Tracks played by the user."""
        self.machine_tracks_indices = machine_track_indices
        """Tracks played by the machine."""

    def _initialize_virtual_piano(self):
        self._virtual_piano_track_msg_index_per_track = [0] * len(self.tracks)

        self._virtual_piano_msg_countdown_per_track.clear()
        for track in self.tracks:
            self._virtual_piano_msg_countdown_per_track.append(track[0].time)

        self._virtual_piano_track_end_reached = [False] * len(self.tracks)

        # e.g.
        # indexes: [0, 0, 0]
        # countdown: [480, 480, 480]
        # next iteration:
        # indexes same
        # countdown: [479, 479, 479]

    def _progress_virtual_piano(self):
        """Returns True if it could progress, returns false if it's the midi EOF."""
        if self._is_eof_reached_by_virtual_piano():
            return False  # exit if there is nothing more

        self.virtual_piano_point_in_time.clear()  # clear last point in time messages

        for i, track in enumerate(self.tracks):
            if self._virtual_piano_track_end_reached[i] is True:  # this is the mark that the end of the track was reached, there are no more notes
                continue ### END OF TRACK TERMINATE

            eot_terminate = False
            """end of track terminate"""
            msg_countdown = self._virtual_piano_msg_countdown_per_track[i]
            while msg_countdown == 0 and not eot_terminate:  # we need to process potentially multiple messages at a single time
                msg_i = self._virtual_piano_track_msg_index_per_track[i]
                msg = track[msg_i]
                if msg.type == "note_on" and msg.velocity > 0:
                    self.virtual_piano[msg.note].set_velocity_from_track(i, msg.velocity)
                    self.virtual_piano[msg.note].update_pressed_this_tick(True)
                elif (msg.type == "note_on" and msg.velocity == 0) or (msg.type == "note_off"):
                    self.virtual_piano[msg.note].set_velocity_from_track(i, 0)
                else:
                    self.virtual_piano_point_in_time.append(PointInTimeMsg(i, msg.is_meta, msg.type, msg.dict()))

                # PROGRESS ON
                self._virtual_piano_track_msg_index_per_track[i] += 1
                msg_i = self._virtual_piano_track_msg_index_per_track[i]
                if msg_i < len(track):
                    msg = track[msg_i]
                    self._virtual_piano_msg_countdown_per_track[i] = msg.time
                    msg_countdown = self._virtual_piano_msg_countdown_per_track[i]
                else:
                    """IN THIS CASE, WE ARE OUT OF NOTES"""
                    self._panic_track_virtual_piano(i)
                    self._virtual_piano_track_end_reached[i] = True  # Mark the track msg index as None to show that we reached the end
                    eot_terminate = True
            else:
                self._virtual_piano_msg_countdown_per_track[i] -= 1  # == "msg_countdown -= 1"

        return True

    def _reset_pressed_this_tick_on_virtual_piano(self):
        """Resets the 'pressed_this_tick' values of all VirtualPianoKeys.
        This value shows if the key was pressed this tick or is being held down.
        It's only really useful in the piano roll, since there we can see it horizontally change in time like so:
        pressed: T, T, T, T, T, F, F, T, T, T
        pr_th_t: T, F, F, F, F, F, F, T, F, F
        The only job of this function is to set this variable to false in all keys AFTER THE VIRTUAL PIANO HAS BEEN SAVED TO THE PIANO ROLL.
        Therefore, it's called in progress_piano_roll."""
        for note in self.virtual_piano:
            note.update_pressed_this_tick(False)

    def _panic_track_virtual_piano(self, track):
        """Like MIDI panic, it stops all notes of the virtual piano. But only on a specific track index."""
        for note in self.virtual_piano:
            velocity = note.tracks_to_velocities.get(track)
            velocity = 0 if velocity is None else velocity
            if velocity > 0:
                note.tracks_to_velocities[track] = 0

    def _is_eof_reached_by_virtual_piano(self):
        """Did the virtual piano reach the end of the MIDI?
        This happens when all tracks reach their end."""
        return all(self._virtual_piano_track_end_reached)

    def initialize_piano_roll(self):
        """
        Used on the first call.
        Fills up the piano roll with the next window_width ticks of info.
        :return: Returns if it already reached the EOF or not. Returns False if it did, returns True if it didn't. (Same as progress_piano_roll)
        """
        # I. Initialize index storage of _VP_midi_msg_indices_per_track.
        self._initialize_virtual_piano()
        self.piano_roll_buffer_end = None

        # II. Initialize piano roll
        eof_terminate = False
        """end of midi file terminate"""
        while len(self.piano_roll_buffer) < self.piano_roll_buffer_window_width and not eof_terminate:
            if not self.progress_piano_roll():  # if it's EOF (if piano roll couldn't progress)
                eof_terminate = True
        return not eof_terminate

    def progress_piano_roll(self):
        """
        Play the next tick on the virtual piano and append the currently played notes to the piano_roll_buffer.
        Also delete old notes if piano roll is too long (outside window width), and update the shift in that case.*
        *NOTE: This is not checked for, since it will always be the case (NOTE: END OF SONG???).

        ON THE FIRST CALL:
        Call the initialize_piano_roll function instead.
        :return: If it could progress on with the song, or in other words, it's not midi EOF yet.
        Returns True if it is not end-of-file. Returns False if it is.
        """
        if self._progress_virtual_piano():  # if it's not EOF (if VP could progress)
            # TODO: There is probably a better way to copy a list of objects.
            copy_virtual_piano = []
            for key in self.virtual_piano:
                copy_key = VirtualPianoKey()
                copy_key.copy_state(key)
                copy_virtual_piano.append(copy_key)
            self.piano_roll_buffer.append(copy_virtual_piano)  # save the virtual piano to the piano roll

            copy_virtual_piano_point_in_time = []
            for msg in self.virtual_piano_point_in_time:
                copy_pointInTimeMsg = PointInTimeMsg(msg.track, msg.meta, msg.type, msg.attr)
                copy_virtual_piano_point_in_time.append(copy_pointInTimeMsg)
            self.piano_roll_buffer_point_in_time.append(copy_virtual_piano_point_in_time)

            self._reset_pressed_this_tick_on_virtual_piano()
            """This above is important. It resets the 'pressed_this_tick' values of all VirtualPianoKeys. This way, we can get this info as well."""

            if len(self.piano_roll_buffer) > self.piano_roll_buffer_window_width:
                self.piano_roll_buffer.pop(0)
                self.piano_roll_buffer_point_in_time.pop(0)
                self.piano_roll_buffer_shift += 1
            return True
        else:  # if it's EOF
            if self.piano_roll_buffer_end is None:
                self.piano_roll_buffer_end = self.piano_roll_buffer_shift + len(self.piano_roll_buffer)
            return False


    def test_piano_roll(self):
        real_virtual_piano = [False] * 128
        tempo = 140

        self.initialize_piano_roll()
        for i, tick in enumerate(self.piano_roll_buffer):
            if i % 120 != 0:
                continue
            """for key in tick:
                if key.is_pressed():
                    print("|", end="")
                else:
                    print(" ", end="")
            print()"""
        not_eof = True
        #  i = -1
        while not_eof:
            next = time.perf_counter() + (mido.tick2second(1, self.ticks_per_beat, mido.bpm2tempo(tempo)))
            #  i += 1
            #  if i % 30 != 0:
            if False:
                continue
            else:
                # HANDLE ANYTHING ELSE
                if len(self.piano_roll_buffer_point_in_time[0]):
                    for obj in self.piano_roll_buffer_point_in_time[0]:
                        print(obj)
                        if obj.meta:  # MetaMessages are for the software
                            if obj.type == "set_tempo":
                                tempo = mido.tempo2bpm(obj.attr['tempo'])
                                print("NEW TEMPO:", tempo)
                        else:  # Messages are for the hardware
                            kwargs = obj.attr
                            msg = mido.Message(**kwargs)
                            port.send(msg)
                    print("-----")

                tick = self.piano_roll_buffer[0]
                for i, key in enumerate(tick):
                    if key.is_pressed():
                        #  print("|", end="")
                        if not real_virtual_piano[i] or key.is_pressed_this_tick():
                            real_virtual_piano[i] = True
                            port.send(mido.Message(type="note_on", note=i, velocity=key.get_max_velocity()))
                    else:
                        #  print(" ", end="")
                        if real_virtual_piano[i]:
                            real_virtual_piano[i] = False
                            port.send(mido.Message(type="note_on", note=i, velocity=key.get_max_velocity()))
                #  print()
                ### PROGRESS PIANO ROLL
                not_eof = self.progress_piano_roll()

                while time.perf_counter() <= next:
                    pass


    def start_following(self, test_play_beats=True):
        pass


if __name__ == "__main__":
    p = PianoObserver(r"D:\PycharmProjects\MidiStuff\SineWavePiano\qian-ben-ying.mid", [], [])
    p.test_piano_roll()
