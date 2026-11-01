"""
Module for managing the audio interface for outputting audio. Can be used to save output to file.
This is a modification of the code from oscparrow.
"""

import logging
import os
import wave
import numpy as np
import pyaudio

pa = pyaudio.PyAudio()

def get_all_device_info(filter_function=None) -> tuple:
    """
    Get info of all devices, optionally filtered with filter().
    :param filter_function: The function provided to filter(), if None then there is no filtering.
    :return: All the info in a tuple.
    """
    count = pa.get_device_count()
    info = []
    for i in range(count):
        info.append(pa.get_device_info_by_index(i))
    if filter_function:
        info = filter(filter_function, info)
    return tuple(info)

def get_index_by_name(channel_name: str):
    """
    Get channel index by name.
    :param channel_name: The channel name.
    :return:
    """
    for channel in get_all_device_info():
        if channel["name"] == channel_name:
            return channel["index"]

def comb_left_right(left: list, right: list) -> list:
    """
    Combs together the left and right channel contents. Code from oscdraw.draw.
    :param left: The left channel contents in a list.
    :param right: The right channel contents in a list.
    :return: The frames.
    """
    frames = []
    for i in range(len(left)):
        frames.append(left[i])
        frames.append(right[i])
    return frames


class AudioInterface:
    """
    Universal, simplified audio backend.
    Supports saving to a wav file, too.
    The number of channels is always 2.
    The format is always pyaudio.paInt16.
    :param device_index: The index of the device used. If None, the default output or input device is used.
    :param output: Whether the new audio stream is an output stream. Default is True.
    :param rate: Sample rate of the stream. Default is 192000.
    :param record: Whether to store the given frames of audio without saving it to a file.
                   This way you can save the audio frames later. Default is False.
    :var s: The pyaudio stream.
    """
    def __init__(self, device_index: int = None, output: bool = True, rate: int = 192000, record: bool = False):
        # REFERENCE FOR SELF: https://stackoverflow.com/questions/35970282/what-are-chunks-samples-and-frames-when-using-pyaudio
        self.is_output = output
        if output:
            self.s = pa.open(rate=rate, channels=2, format=pyaudio.paInt16, output=True,
                             output_device_index=device_index if device_index else pa.get_default_output_device_info()["index"])
        else:
            self.s = pa.open(rate=rate, channels=2, format=pyaudio.paInt16, input=True,
                             input_device_index=device_index if device_index else pa.get_default_input_device_info()["index"])

        self.does_record = record
        if record:
            self.record = bytes()

        self.rate = rate

        logging.debug(pa.get_device_info_by_index(device_index if device_index else
                                                  pa.get_default_output_device_info()["index"] if output else
                                                  pa.get_default_input_device_info()["index"]))

    def get_rate(self) -> int:
        return self.rate

    def write(self, frames: tuple | list, no_output: bool = False) -> None:
        """
        Write frames of audio to the stream.
        :param frames: Frames of audio, as numbers in an iterable, not in a buffer.
        :param no_output: Don't output the audio, only record it if recording is enabled. UPDATED FOR MIDIIO.
        :return: None
        """
        if not self.is_output:
            raise RuntimeError(
                "Cannot write to input stream."
            )
        frames = np.asarray(frames, "int16").tobytes()
        if self.does_record:
            self.record += frames
        if not no_output:
            self.s.write(frames)

    def read(self, frames: int = 192000//60):
        """
        Read frames of audio.
        :param frames: The number of frames. Default is 1/60th of a second amount.
        :return: The frames in a tuple, as numbers, not in a buffer.
        """
        if self.is_output:
            raise RuntimeError(
                "Cannot read from output stream."
            )
        frames = self.s.read(frames)
        if self.does_record:
            self.record += frames
        frames = np.frombuffer(frames, "int16").tolist()
        return tuple(frames)

    def save(self, file: str = "temp.wav"):
        """
        Saves the recorded frames in a wave file.
        :param file: The path to the file. Default is "temp.wav".
        :return: None
        """
        if not self.does_record:
            raise RuntimeError(
                "Cannot save, if didn't record."
            )
        if os.path.exists(file):
            with wave.open(file, "rb") as wav:
                prev_record = wav.readframes(wav.getnframes())
            record = prev_record + self.record
        else:
            record = self.record
        with wave.open(file, "wb") as wav:
            wav.setframerate(self.rate)
            wav.setsampwidth(pyaudio.get_sample_size(pyaudio.paInt16))
            wav.setnchannels(2)
            wav.writeframesraw(record)
        self.record = bytes()


def test():
    logging.basicConfig(level=logging.DEBUG)
    i = AudioInterface(output=False)
    o = AudioInterface(5, record=True)
    for j in range(3):
        for ii in range(180):
            o.write(i.read())
        o.save()

if __name__ == '__main__':
    print("This is a module. Please write your own Python file.")
