# piano_roll_realtime.py
# Requirements: pip install mido python-rtmidi pygame

import mido
import pygame
import time
import math

# ---------- Config ----------
MIDI_LOW = 21       # A0
MIDI_HIGH = 108     # C8
NUM_KEYS = MIDI_HIGH - MIDI_LOW + 1

WIN_W = 1200
WIN_H = 600
FPS = 60

PX_PER_SEC = 300.0    # horizontal speed: pixels per second
NOTE_PADDING = 1      # pixel gap between notes vertically
KEYBOARD_WIDTH = 80   # reserve a left column to draw keys

# colors
BG = (10, 10, 10)
WHITE_KEY = (40, 40, 40)
BLACK_KEY = (30, 30, 30)
NOTE_COLOR = (0, 200, 255)
ACTIVE_NOTE_COLOR = (255, 180, 0)
GRID_COLOR = (50, 50, 50)
TEXT_COLOR = (200, 200, 200)

# ---------- Helpers ----------
def note_to_index(n):
    return n - MIDI_LOW  # 0..NUM_KEYS-1

def index_to_y(idx):
    # map index 0 (lowest) -> bottom of area
    area_h = WIN_H
    key_h = area_h / NUM_KEYS
    # bottom-aligned: highest index at top
    return WIN_H - (idx + 1) * key_h

def note_height():
    return WIN_H / NUM_KEYS

# ---------- Data stores ----------
# active_notes: note -> (start_time, velocity)
active_notes = {}

# finished_notes: list of dicts with keys: note, start, end, vel
finished_notes = []

# ---------- Open MIDI input ----------
try:
    inport = mido.open_input("Digital Piano 1")  # default system MIDI input
except Exception as e:
    print("Could not open a MIDI input port.")
    print("Available ports:", mido.get_input_names())
    raise

# ---------- Pygame init ----------
pygame.init()
screen = pygame.display.set_mode((WIN_W, WIN_H))
pygame.display.set_caption("Real-time Piano Roll")
font = pygame.font.SysFont(None, 18)
clock = pygame.time.Clock()

start_time_offset = time.perf_counter()  # reference time

running = True
while running:
    now = time.perf_counter()

    # ------ handle pygame events ------
    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            running = False
        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                running = False

    # ------ read pending MIDI messages ------
    for msg in inport.iter_pending():
        if msg.type == 'note_on' and getattr(msg, 'velocity', 0) > 0:
            active_notes[msg.note] = (time.perf_counter(), msg.velocity)
        elif msg.type == 'note_off' or (msg.type == 'note_on' and getattr(msg, 'velocity', 0) == 0):
            if msg.note in active_notes:
                s, v = active_notes.pop(msg.note)
                finished_notes.append({'note': msg.note, 'start': s, 'end': time.perf_counter(), 'vel': v})

    # ------ clean old finished notes that scrolled off screen ------
    # if note's rightmost x < 0 then remove
    def x_for_time(t):
        # x coordinate where time t is drawn.
        # newest time (now) is at right edge WIN_W.
        return WIN_W - (now - t) * PX_PER_SEC

    finished_notes = [n for n in finished_notes if x_for_time(n['end']) + 50 > 0]  # keep a little buffer

    # ------ draw background and grid ------
    screen.fill(BG)

    # vertical keyboard area left
    pygame.draw.rect(screen, (18, 18, 18), (0, 0, KEYBOARD_WIDTH, WIN_H))

    # draw horizontal grid lines (one per key)
    key_h = note_height()
    for i in range(NUM_KEYS):
        y = index_to_y(i)
        pygame.draw.line(screen, GRID_COLOR, (KEYBOARD_WIDTH, y), (WIN_W, y))

    # draw time marker (vertical line at right edge)
    pygame.draw.line(screen, (80, 80, 80), (WIN_W - 0.5, 0), (WIN_W - 0.5, WIN_H))

    # draw finished notes
    for n in finished_notes:
        idx = note_to_index(n['note'])
        y = index_to_y(idx) + NOTE_PADDING
        h = key_h - NOTE_PADDING * 2

        x_start = x_for_time(n['start'])
        x_end = x_for_time(n['end'])
        w = max(2, x_end - x_start)
        rect = pygame.Rect(x_start, y, w, h)
        # color scaled by velocity
        vel_scale = min(1.0, n['vel'] / 127.0)
        color = tuple(min(255, int(c * (0.3 + 0.7 * vel_scale))) for c in NOTE_COLOR)
        pygame.draw.rect(screen, color, rect)

    # draw active notes (not yet released). draw as if end = now
    for note, (s, v) in active_notes.items():
        idx = note_to_index(note)
        y = index_to_y(idx) + NOTE_PADDING
        h = key_h - NOTE_PADDING * 2
        x_start = x_for_time(s)
        x_end = x_for_time(now)
        w = max(2, x_end - x_start)
        rect = pygame.Rect(x_start, y, w, h)
        vel_scale = min(1.0, v / 127.0)
        color = tuple(min(255, int(c * (0.3 + 0.7 * vel_scale))) for c in ACTIVE_NOTE_COLOR)
        pygame.draw.rect(screen, color, rect)

    # draw piano key labels in left column
    for n in range(MIDI_LOW, MIDI_HIGH + 1):
        idx = note_to_index(n)
        y = index_to_y(idx)
        h = key_h
        key_rect = pygame.Rect(0, y, KEYBOARD_WIDTH, h)
        # alternate shading for white/black keys by simple pattern on midi note
        # quick heuristic: black keys are those with semitone offsets 1,3,6,8,10 from C
        semitone = (n - 0) % 12
        if semitone in (1, 3, 6, 8, 10):
            pygame.draw.rect(screen, BLACK_KEY, key_rect)
        else:
            pygame.draw.rect(screen, WHITE_KEY, key_rect)
        # label every octave C
        if semitone == 0:
            lbl = font.render(f"{n}", True, TEXT_COLOR)
            screen.blit(lbl, (4, y + 2))

    # draw overlay text
    info = f"Input: {inport.name}   Active notes: {len(active_notes)}   FPS: {int(clock.get_fps())}"
    info_surf = font.render(info, True, TEXT_COLOR)
    screen.blit(info_surf, (KEYBOARD_WIDTH + 6, 6))

    # draw time scale at top (stable, no jitter)
    seconds_shown = WIN_W / PX_PER_SEC
    step = 0.1  # tick spacing in seconds
    t_end = now
    t_start = now - seconds_shown

    # compute integer tick indices to avoid floating-point accumulation
    inv_step = int(round(1.0 / step))  # e.g. 10 for 0.1s
    first_idx = math.floor(t_start / step)
    last_idx = math.ceil(t_end / step)

    for k in range(first_idx, last_idx + 1):
        t_tick = k * step
        x = WIN_W - (t_end - t_tick) * PX_PER_SEC
        if x <= KEYBOARD_WIDTH:
            continue
        # small tick
        pygame.draw.line(screen, GRID_COLOR, (x, 0), (x, 10))
        # label whole seconds only (k divisible by inv_step)
        if (k % inv_step) == 0:
            sec_label = int(round(t_tick))
            lbl = font.render(f"{sec_label}s", True, TEXT_COLOR)
            screen.blit(lbl, (x - 10, 12))

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
inport.close()
