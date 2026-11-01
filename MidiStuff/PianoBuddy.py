import mido

mido.set_backend('mido.backends.rtmidi', load=True)

keys_to_commands = {
    (60, 60, 60): ["print", ["YAY! IT WORKED!"]],
    (60, 64): ["press", [67, 1]]
}

def user_io_chooser():
    inputs = mido.get_input_names()
    for i, val in enumerate(inputs):
        print(f"{i+1}: {val}")
    print("Please choose one as midi input and output.")
    while True:
        chosen = input("Enter one's number: ")
        if chosen.isdecimal():
            if 0 < int(chosen) <= len(inputs):
                print("OK.")
                return inputs[int(chosen)-1]
            else:
                print("Please input the number of one of the shown midi inputs to use as a midi input and output.")
        else:
            print("Please input a decimal number, the number of one of the shown midi inputs to use as a midi input and output.")

def user_note_press_test(io):
    print("In order to know when you press and release notes, please press and release a note.")
    print("Please only press and release ONE NOTE.")
    print("Waiting...")
    down = None
    up = None
    while down is None or up is None:
        for msg in io.iter_pending():
            if msg.type.startswith("note"):
                if not down:
                    down = msg
                elif not up:
                    up = msg
    print("Done.")
    return [[down.type], [up.type, up.velocity]]

def label_msg(msg, note_press):
    if msg.type == note_press[1][0] and msg.velocity == note_press[1][1]:
        return ["release", msg]
    elif msg.type == note_press[0][0]:
        return ["press", msg]
    else:
        return ["unknown", msg]

def execute_command(io, note_press, note_press_note_msg_loop):
    found = None
    for keys, command in keys_to_commands.items():
        if list(keys) == list(reversed(list(reversed(note_press_note_msg_loop))[:len(keys)])):
            note_press_note_msg_loop.clear()
            found = command
            break
    if found:
        if found[0] == "print":
            print(*found[1])
        if found[0] == "press":
            notes = found[:-1]
            note_time = found[-1]
            for note in notes:
                msg = mido.Message("note_on")
                io.

chosen = user_io_chooser()
io = mido.open_input(chosen)
note_press = user_note_press_test(io)
note_press_note_msg_loop = []
while True:
    labeled_msg = label_msg(io.receive(), note_press)
    if labeled_msg[0] == "press":
        note_press_note_msg_loop.append(labeled_msg[1].note)
        if len(note_press_note_msg_loop) > max([len(list(keys_to_commands.keys())[i]) for i in range(len(keys_to_commands))]):
            note_press_note_msg_loop.pop(0)
    execute_command(io, note_press, note_press_note_msg_loop)

"""
    def _user_ioport_chooser(self):
        inputs = mido.get_input_names()
        for i, val in enumerate(inputs):
            print(f"{i + 1}: {val}")
        print("Please choose one as midi input and output.")
        while True:
            chosen = input("Enter one's number: ")
            if chosen.isdecimal():
                if 0 < int(chosen) <= len(inputs):
                    print("OK.")
                    return inputs[int(chosen) - 1]
                else:
                    print("Please input the number of one of the shown midi inputs to use as a midi input and output.")
            else:
                print(
                    "Please input a decimal number, the number of one of the shown midi inputs to use as a midi input and output.")

    def _user_note_type_test(self):
        print("In order to know when you press and release notes, please press and release a note.\n"
              "Please only press and release ONE NOTE.\n"
              "Waiting...")
        press = None
        release = None
        while press is None or release is None:
            for msg in self.io.iter_pending():
                if msg.type.startswith("note"):
                    if not press:
                        press = msg
                    elif not release:
                        release = msg
        print("Done.")
        return {"press":    [press.type], "release": [release.type, release.velocity]}
"""