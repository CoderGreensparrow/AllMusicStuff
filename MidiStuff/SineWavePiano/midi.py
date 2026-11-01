"""
Simplified midi backend
"""
from typing import Literal
import re

import mido
import mido.frozen

MODE_IN_ONLY = "InOnly"
MODE_OUT_ONLY = "OutOnly"
MODE_INPORT_AND_OUTPORT_SEPARATE = "InOutSeparate"
MODE_IOPORT = "InOutSame"

MSG_TYPE_NOTE_OFF = "note_off"
MSG_TYPE_NOTE_ON = "note_on"
MSG_TYPE_CONTROL_CHANGE = "control_change"
MSG_TYPE_PROGRAM_CHANGE = "program_change"
MSG_TYPE_SYSEX = "sysex"
MSG_TYPE_CLOCK = "clock"

mido.set_backend('mido.backends.rtmidi', load=True)

class MidiIO:
    def __init__(self, mode: Literal["InOnly", "OutOnly", "InOutSeparate", "InOutSame"], port_names: list[str], strict_name_matching: bool = True):
        """
        Initialize simplified midi io interface.
        :param mode: Decides how to connect to the MIDI instrument.
        If the MIDI instrument has a separate port for input and output, it can use those two ports.
        If the MIDI instrument has a port identified as an IOPort by mido, then it can use that one port.
        This class also support input or output only.
        This class should make it simpler to connect to the MIDI instrument required.
        :param port_names: The names to look for.
        :param strict_name_matching: Whether to use strict name matching or not.
        Disabled by default. When disabled, the names of BOTH the input and output ports don't have to match from beginning to end, but at least some string of characters must match.
        This is useful if the input and output channels of one instrument are not as one IOPort, but as an Inport and Outport with a slightly different name.
        E.g. if a piano's input is "Digital Piano 2" and the output is "Digital Piano 1", supplying the name "Digital Piano" should be enough for this function if strict name matching if off.
        When enabled, all names must be provided exactly. If there are separate ports for input and output, both of the channel names must be provided, IN THE ORDER INPUT, OUTPUT TO THE PORT_NAMES ARGUMENT.

        This also means that you may only supply one or two port names to port_names.
        Supply one port name if:
        - You will only have an input OR an output port. (One port)
        - You will have an IOPort (a port that is both input and output)
        - You have a separate input and output port for one instrument, but you have strict_name_matching turned off, so you only need to supply part of the string, which should be the same in both of the port names.
        Supply two port names if:
        - You have separate input and output ports, and the names are different so much that even non strict name matching needs help.
        """
        self.mode = mode
        if mode == MODE_IN_ONLY:
            self.port = mido.open_input(self._get_port_name("in", strict_name_matching, port_names[0]))
        elif mode == MODE_OUT_ONLY:
            self.port = mido.open_output(self._get_port_name("out", strict_name_matching, port_names[0]))
        elif mode == MODE_IOPORT:
            self.port = mido.open_ioport(self._get_port_name("io", strict_name_matching, port_names[0]))
        elif mode == MODE_INPORT_AND_OUTPORT_SEPARATE:
            self.inport = mido.open_input(self._get_port_name("in", strict_name_matching, port_names[0]))
            self.outport = mido.open_output(self._get_port_name("out", strict_name_matching, port_names[0] if len(port_names) == 1 else port_names[1]))
            self.port = mido.ports.IOPort(self.inport, self.outport)


    def _get_port_name(self, type_: Literal["in", "out", "io"], strict_name_matching: bool, name: str):
        if strict_name_matching:
            if type_ == "in" and name in mido.get_input_names():
                return name
            elif type_ == "out" and name in mido.get_output_names():
                return name
            elif type_ == "io" and name in mido.get_ioport_names():
                return name
            else:
                return None
        else:
            return self._regex_port_matching(type_, name)

    def _regex_port_matching(self, type_: Literal["in", "out", "io"], name: str):
        exp = re.compile(f"^.*{name}.*$")
        if type_ == "in":
            for input_name in mido.get_input_names():
                if exp.match(input_name):
                    return input_name
        elif type_ == "out":
            for output_name in mido.get_output_names():
                if exp.match(output_name):
                    return output_name
        elif type_ == "io":
            for ioport_name in mido.get_ioport_names():
                if exp.match(ioport_name):
                    return ioport_name
        return None


    def get_pending_msg(self, ignored_msg_types: list[str]):
        msg = self.port.receive(block=False)
        if msg:
            if msg.type not in ignored_msg_types:
                return msg
        return None

    def send_msg(self, msg: mido.Message):
        self.port.send(msg)

    def send_new_msg_parameterized(self, type_: str, **kwargs):
        self.port.send(mido.frozen.FrozenMessage(type_, **kwargs))

    def send_note_off(self, channel: int, note: int, velocity: int):
        self.send_new_msg_parameterized("note_off", channel=channel, note=note, velocity=velocity)
    def send_note_on(self, channel: int, note: int, velocity: int):
        self.send_new_msg_parameterized("note_on", channel=channel, note=note, velocity=velocity)