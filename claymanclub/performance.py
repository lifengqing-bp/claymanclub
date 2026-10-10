"""Shot-local performance intervals, independent of any renderer."""


def validate_performances(shot, version):
    duration = shot['end_frame'] - shot['start_frame']
    intervals = {}
    for performance in shot['performances']:
        if version != '0.4':
            if 'start_frame' in performance or 'end_frame' in performance:
                raise ValueError('performance timing requires schema_version 0.4')
            continue
        start, end = performance.get('start_frame'), performance.get('end_frame')
        if not (type(start) is int and type(end) is int and 0 <= start < end <= duration):
            raise ValueError('performance interval must be integers within [0, shot duration]')
        intervals.setdefault(performance['actor'], []).append((start, end))
    for spans in intervals.values():
        spans.sort()
        if any(left[1] > right[0] for left, right in zip(spans, spans[1:])):
            raise ValueError('overlapping performances for the same actor')


def preflight_performances(episode, capabilities):
    for shot in episode['shots']:
        validate_performances(shot, episode['schema_version'])
    if episode['schema_version'] == '0.4' and not capabilities.timed_performances:
        raise ValueError('unsupported backend timed performances')


def active_performances(shot, version, frame):
    if version != '0.4':
        return shot['performances']
    return [p for p in shot['performances'] if p['start_frame'] <= frame < p['end_frame']]


def performance_boundaries(shot, version):
    if version != '0.4':
        return [0]
    duration = shot['end_frame'] - shot['start_frame']
    return sorted({0} | {p[k] for p in shot['performances']
                         for k in ('start_frame', 'end_frame') if p[k] < duration})
