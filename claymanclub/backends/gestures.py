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


def walk_leg_points(performance, frame, side):
    """Small procedural knee/foot lift; no skeleton or planted-foot solver."""
    direction = -1 if side == 'left' else 1
    swing = walk_swing(performance, frame)
    lift = max(0, direction * swing / 22)
    return [direction * (20 + 18 * lift), 580 - 14 * lift,
            direction * 40, 635 - 28 * lift]


def walk_leg_path(performance, frame, side):
    if not performance or performance['action'] != 'walk':
        return 'M0 525L-40 635' if side == 'left' else 'M0 525L40 635'
    kx, ky, fx, fy = walk_leg_points(performance, frame, side)
    return f'M0 525L{kx} {ky}L{fx} {fy}'
