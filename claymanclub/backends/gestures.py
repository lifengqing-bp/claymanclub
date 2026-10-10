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
        wave = -55 * lift
    return {'bow': bow, 'wave': wave}


def walk_swing(performance, frame):
    if not performance or performance['action'] != 'walk':
        return 0.0
    amount = motion_envelope(performance, frame)
    if not amount:
        return 0.0
    phase = (frame - performance['start_frame']) / (performance['end_frame'] - performance['start_frame'] - 1)
    return 22 * math.sin(4 * math.pi * phase) * amount



def joint_angles(performance, frame):
    """Four local hinge angles; zero means a straight limb."""
    result = dict(elbow_left=0.0, elbow_right=0.0, knee_left=0.0, knee_right=0.0)
    amount = motion_envelope(performance, frame)
    if not amount:
        return result
    phase = (frame - performance['start_frame']) / (performance['end_frame'] - performance['start_frame'] - 1)
    if performance['action'] == 'wave':
        lift = min(1, 4 * phase, 4 * (1 - phase))
        lift = lift * lift * (3 - 2 * lift)
        result['elbow_right'] = -85 * lift + 20 * math.sin(8 * math.pi * phase) * amount
    elif performance['action'] == 'walk':
        stride = math.sin(4 * math.pi * phase)
        result['elbow_left'] = 35 * amount
        result['elbow_right'] = -35 * amount
        result['knee_left'] = 70 * max(0, -stride) * amount
        result['knee_right'] = -70 * max(0, stride) * amount
    return result


def walk_leg_points(performance, frame, side):
    """Local knee and foot after knee rotation; thigh remains rigid."""
    direction = -1 if side == 'left' else 1
    angle = math.radians(joint_angles(performance, frame)['knee_' + side])
    dx, dy = direction * 20, 55
    return [dx, 580, dx + dx * math.cos(angle) - dy * math.sin(angle),
            580 + dx * math.sin(angle) + dy * math.cos(angle)]
