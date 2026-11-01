import mido

mido.set_backend('mido.backends.rtmidi', load=True)

def user_note_type_test(io, *, start_message: str = None):
    """
    Test how the midi device sends key presses and releases.
    (For example, my piano sends on note press type note_on with some velocity,
    but on key release it sends note_on with 0 velocity. It's wierd, but needed.)
    :param io: The io (or input) port to test on.
    :param start_message: The message to prompt to the user. There is a built-in one.
    :return: The "note type". (Dict: {"press": [press.type], "release": [release.type, release.velocity]} where press and release are midi messages)
    """
    print("In order to know when you press and release notes, please press and release a note.\n"
          "Please only press and release one note.\n"
          "Waiting..." if not start_message else start_message)
    press = None
    release = None
    while press is None or release is None:
        for msg in io.iter_pending():
            if msg.type.startswith("note"):
                if not press:
                    press = msg
                elif not release:
                    release = msg
    print("Done.")
    return {"press": [press.type], "release": [release.type, release.velocity]}

class EasyMidiNotes:

    def _msg_note_parser(self, msg: mido.Message):
        if msg.type == self.note_type[1][0] and msg.velocity == self.note_type[1][1]:
            return ["release", msg]
        elif msg.type == self.note_type[0][0]:
            return ["press", msg]
        else:
            return ["other", msg]

    def __init__(self, port_name, note_type="self_test"):
        """
        Use for easier midi io access. Uses
        :param port_name:
        :param note_type:
        """
        self.io = mido.open_ioport(port_name)
        self.note_type = note_type if note_type != "self_test" else user_note_type_test(self.io)

    def