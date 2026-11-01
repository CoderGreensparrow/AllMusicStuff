import mido, time, random, math

def clamp(val, min_, max_):
    if val < min_:
        return min_
    elif val > max_:
        return max_
    else:
        return val

mido.set_backend('mido.backends.rtmidi', load=True)

def user_input_chooser():
    inputs = mido.get_input_names()
    for i, val in enumerate(inputs):
        print(f"{i+1}: {val}")
    print("Please choose one as midi input.")
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

def user_output_chooser():
    outputs = mido.get_output_names()
    for i, val in enumerate(outputs):
        print(f"{i+1}: {val}")
    print("Please choose one as output input.")
    while True:
        chosen = input("Enter one's number: ")
        if chosen.isdecimal():
            if 0 < int(chosen) <= len(outputs):
                print("OK.")
                return outputs[int(chosen)-1]
            else:
                print("Please input the number of one of the shown midi inputs to use as a midi input and output.")
        else:
            print("Please input a decimal number, the number of one of the shown midi inputs to use as a midi input and output.")

def main():
    inport = mido..open_input(user_input_chooser())
    outport = mido.open_output(user_output_chooser())
    in_msgs = []
    out_msgs = []
    #  random_shift = random.randint(-20, 20)
    #  countdown = 0
    while True:
        for in_msg in inport.iter_pending():
            if in_msg.type != "clock":
                in_msgs.append(in_msg)
                print("IN:", in_msg)
        for in_msg in in_msgs:
            out_msgs.append(
                [in_msg.copy(note=clamp(in_msg.note, 0, 127)),
                 time.perf_counter() + 10 + random.randint(-5, 5) / 100]
            )
            """countdown = 100
        if countdown > 0:
            countdown -= 0.1
        else:
            countdown = 0"""
        for out_msg in out_msgs:
            if out_msg[1] <= time.perf_counter():
                outport.send(out_msg[0])
                out_msgs.remove(out_msg)
                print("OUT:", out_msg)
        in_msgs.clear()
        """if len(out_msgs) == 0 and countdown == 0:
            #  random_shift = random.randint(-20, 20)
            outport.reset()"""
        """time.sleep(random.random())"""

if __name__ == '__main__':
    main()