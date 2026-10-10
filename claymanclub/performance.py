"""Shot-local performance intervals, independent of any renderer."""
import math

TIMED_VERSIONS = ('0.4', '0.5', '0.6', '0.7')
ANIMATED_VERSIONS = ('0.5', '0.6', '0.7')
ANIMATED_ACTIONS = frozenset({'nod', 'wave', 'bow', 'walk', 'run', 'jump'})


def validate_performances(shot, version):
    duration = shot['end_frame'] - shot['start_frame']
    intervals = {}
    for performance in shot['performances']:
        if performance['action'] in ('run', 'jump') and version != '0.7':
            raise ValueError('run and jump require schema_version 0.7')
        if performance['action'] == 'walk' and version not in ('0.6', '0.7'):
            raise ValueError('walk requires schema_version 0.6')
        if performance['action'] in ('wave', 'bow') and version not in ANIMATED_VERSIONS:
            raise ValueError('wave and bow require schema_version 0.5')
        if 'gaze_target' in performance and version not in ANIMATED_VERSIONS:
            raise ValueError('gaze_target requires schema_version 0.5')
        if version not in TIMED_VERSIONS:
            if 'start_frame' in performance or 'end_frame' in performance:
                raise ValueError('performance timing requires schema_version 0.4')
            continue
        start, end = performance.get('start_frame'), performance.get('end_frame')
        if not (type(start) is int and type(end) is int and 0 <= start < end <= duration):
            raise ValueError('performance interval must be integers within [0, shot duration]')
        if version in ANIMATED_VERSIONS and performance['action'] in ANIMATED_ACTIONS:
            minimum = 17 if performance['action'] in ('wave', 'walk', 'run', 'jump') else 3
            if end - start < minimum:
                raise ValueError(f'animated {performance["action"]} requires at least {minimum} frames')
        intervals.setdefault(performance['actor'], []).append((start, end))
    for spans in intervals.values():
        spans.sort()
        if any(left[1] > right[0] for left, right in zip(spans, spans[1:])):
            raise ValueError('overlapping performances for the same actor')


def preflight_performances(episode, capabilities):
    for shot in episode['shots']:
        validate_performances(shot, episode['schema_version'])
        for p in shot['performances']:
            validate_gaze(p, episode['cast'], episode['schema_version'])
            if 'gaze_target' in p and not capabilities.gaze_targets:
                raise ValueError('unsupported backend gaze targets')
            if episode['schema_version'] in ANIMATED_VERSIONS and p['action'] in ANIMATED_ACTIONS and p['action'] not in capabilities.animated_actions:
                raise ValueError('unsupported backend animated action: ' + p['action'])
    if episode['schema_version'] in TIMED_VERSIONS and not capabilities.timed_performances:
        raise ValueError('unsupported backend timed performances')


def active_performances(shot, version, frame):
    if version not in TIMED_VERSIONS:
        return shot['performances']
    return [p for p in shot['performances'] if p['start_frame'] <= frame < p['end_frame']]


def performance_boundaries(shot, version):
    if version not in TIMED_VERSIONS:
        return [0]
    duration = shot['end_frame'] - shot['start_frame']
    return sorted({0} | {p[k] for p in shot['performances'] + shot.get('interactions', [])
                         for k in ('start_frame', 'end_frame') if p[k] < duration})


def validate_gaze(performance, cast, version):
    if 'gaze_target' not in performance:
        return
    if version not in ANIMATED_VERSIONS:
        raise ValueError('gaze_target requires schema_version 0.5')
    target = performance['gaze_target']
    if not isinstance(target, str) or target not in cast or target == performance['actor']:
        raise ValueError('gaze_target must reference another cast member')
    if performance['action'] == 'look_down':
        raise ValueError('look_down conflicts with gaze_target')


def motion_envelope(performance, frame):
    """One smooth down/up cycle, with neutral first and last displayed frames."""
    if performance is None or performance['action'] not in ANIMATED_ACTIONS:
        return 0.0
    start, end = performance['start_frame'], performance['end_frame']
    if frame <= start or frame >= end - 1:
        return 0.0
    phase = (frame - start) / (end - start - 1)
    return (1 - math.cos(2 * math.pi * phase)) / 2


def nod_amount(performance, frame):
    return motion_envelope(performance, frame) if performance and performance['action'] == 'nod' else 0.0
