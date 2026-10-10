"""Stickfigure joint binding; angles and SVG pivots are not story protocol."""
import math
from ..performance import motion_envelope


def gesture_angles(performance, frame):
    amount = motion_envelope(performance, frame)
    bow = 30 * amount if performance and performance['action'] == 'bow' else 0.0
    wave = 0.0
    if performance and performance['action'] == 'wave' and amount:
        phase = (frame - performance['start_frame']) / (performance['end_frame'] - performance['start_frame'] - 1)
        lift = min(1, 4 * phase, 4 * (1 - phase))
        lift = lift * lift * (3 - 2 * lift)
        wave = -120 * lift + 20 * math.sin(8 * math.pi * phase) * amount
    return {'bow': bow, 'wave': wave}


def walk_swing(performance, frame):
    if not performance or performance['action'] != 'walk':
        return 0.0
    amount = motion_envelope(performance, frame)
    if not amount:
        return 0.0
    phase = (frame - performance['start_frame']) / (performance['end_frame'] - performance['start_frame'] - 1)
    return 22 * math.sin(4 * math.pi * phase) * amount
