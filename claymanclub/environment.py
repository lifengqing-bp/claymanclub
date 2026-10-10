"""Versioned semantic weather and timed prop attachments, independent of SVG."""
WEATHER = frozenset({'sunny', 'cloudy', 'overcast', 'windy', 'rain', 'storm'})


def validate_environment(shot, version, cast):
    def require(ok, message):
        if not ok:
            raise ValueError('environment: ' + message)
    if 'weather' in shot or 'interactions' in shot:
        require(version == '0.7', 'requires schema_version 0.7')
    if 'weather' in shot:
        weather = shot['weather']
        require(isinstance(weather, dict) and set(weather) == {'kind'}, 'weather requires kind only')
        require(isinstance(weather['kind'], str) and weather['kind'] in WEATHER, 'unsupported weather')
    interactions = shot.get('interactions', [])
    require(isinstance(interactions, list), 'interactions must be a list')
    spans = {}
    for item in interactions:
        require(isinstance(item, dict) and set(item) == {'actor', 'prop', 'action', 'start_frame', 'end_frame'},
                'interaction has missing or unknown fields')
        require(isinstance(item['actor'], str) and item['actor'] in cast, 'unknown actor')
        require(item['prop'] == 'umbrella' and item['action'] == 'hold', 'unsupported prop interaction')
        start, end = item['start_frame'], item['end_frame']
        require(type(start) is int and type(end) is int and 0 <= start < end <= shot['end_frame']-shot['start_frame'],
                'invalid interaction interval')
        # One shared prop may have different owners, never simultaneously.
        spans.setdefault(item['prop'], []).append((start, end))
    for intervals in spans.values():
        intervals.sort()
        require(all(a[1] <= b[0] for a, b in zip(intervals, intervals[1:])), 'conflicting prop ownership')


def preflight_environment(episode, capabilities):
    for shot in episode['shots']:
        validate_environment(shot, episode['schema_version'], episode['cast'])
        if 'weather' in shot and shot['weather']['kind'] not in capabilities.weather:
            raise ValueError('unsupported backend weather')
        for item in shot.get('interactions', []):
            if (item['action'], item['prop']) not in capabilities.interactions:
                raise ValueError('unsupported backend prop interaction')


def holding(shot, actor, frame):
    return any(i['actor'] == actor and i['start_frame'] <= frame < i['end_frame']
               for i in shot.get('interactions', []))
