"""
Idea:
While recording something through MIDI and playing, use the pedal on a keyboard to give the metronome with one's feet.

This means that the program can deduce the actual lengths of the notes depending on:
- the number of notes between two beats.
- the length of the notes relative to each other within those two beats.
This means that even if you fumble with playing, just make sure the note's relative lengths and the number of notes between two beats are good enough.
IMPORTANT: The program will try to adapt to common note lengths, like sheet music, so human imprecision and measurement error may be less of a problem.
The program divides detected notes into 2 categories:
I. normal notes: double whole and up, whole, whole, half, half, third, quarter, sixth, eighth, sixteenth note; and the dotted versions of each, except double whole and up, third, and sixth
                 NOTE: The "third" and "sixth" notes can be found in triplets of two speed.
                 NOTE: When there is appoggiatura, the length of the note before the parent note is calcualted like so:
                       the end of the last appoggiatura note before the next normal note, their parent note, is the end of the normal note before that parent note.
II. pre-note appoggiatura notes: These have to be played very shortly before a longer note to be detected as appoggiatura.
                                 NOTE: These have to be played faster than a twenty-fourth note of the current tempo.
Detection method:
I. Pedal pressed
1. Record MIDI key down and key up with strength if available
II. Pedal released, process beat
1. detect pre-note appoggiatura: detect clusters of notes ending with a longer note.
                                 The notes before the long note, as in the above NOTE, have to be longer than a twenty-fourth note.
                                 Seperate these notes, except the long note, into the "appoggiatura notes".
2. All other notes are the "normal notes".
3. Determine the relative length of the normal notes (see second NOTE in I.) within the current beat
4. Approximate what the sheet music could look like without pre-note appoggiatura, see IMPORTANT and I.
5. Add pre-note appoggiatura
III. Go to I. until end signal

Pedal:
The pedal is a main component in this program.
It's functions:
1. Give the tempo as the user is playing.
   NOTE: If the user has to slow down, that's fine, as long as they don't do it within a beat. At the new beat, a new tempo can be used.
"""