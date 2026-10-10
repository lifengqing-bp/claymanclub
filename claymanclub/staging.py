"""Backend-neutral actor offsets, evaluated in shot-local time."""
import math


def validate_tracks(shot, version, cast):
    if 'actor_tracks' not in shot:
        return
    def require(condition, message):
        if not condition:
            raise ValueError('actor_tracks: ' + message)
    require(version in ('0.6', '0.7'), 'requires schema_version 0.6')
    tracks = shot['actor_tracks']
    require(isinstance(tracks, list), 'must be a list')
    actors = set()
    for track in tracks:
        require(isinstance(track, dict) and set(track) == {'actor', 'space', 'interpolation', 'keyframes'},
                'unknown or missing fields')
        actor = track['actor']
        require(isinstance(actor, str) and actor in cast and actor not in actors, 'unknown or duplicate actor')
        actors.add(actor)
        require(track['space'] in ('stage_2d', 'stage_3d'), 'unknown space')
        require(track['interpolation'] == 'linear', 'unsupported interpolation')
        keys = track['keyframes']
        require(isinstance(keys, list) and keys, 'keyframes must be non-empty')
        previous = -1
        for key in keys:
            require(isinstance(key, dict) and set(key) == {'frame', 'offset'}, 'keyframe requires frame and offset only')
            frame, offset = key['frame'], key['offset']
            require(type(frame) is int and previous < frame <= shot['end_frame'] - shot['start_frame'],
                    'frames must increase strictly within shot')
            require(isinstance(offset, list) and len(offset) == 3 and
                    all(type(v) in (int, float) and abs(v) <= 1_000_000 and math.isfinite(v) for v in offset),
                    'offset must contain three bounded finite numbers')
            require(track['space'] != 'stage_2d' or offset[2] == 0, 'stage_2d requires zero z')
            previous = frame
        require(keys[0]['frame'] == 0, 'first keyframe must be frame 0')


def preflight_tracks(episode, capabilities):
    for shot in episode['shots']:
        validate_tracks(shot, episode['schema_version'], episode['cast'])
        for track in shot.get('actor_tracks', []):
            if track['space'] not in capabilities.actor_spaces:
                raise ValueError('unsupported backend actor space: ' + track['space'])


def sample_offset(track, frame):
    if track is None:
        return [0, 0, 0]
    left = right = track['keyframes'][0]
    for key in track['keyframes']:
        right = key
        if frame <= key['frame']:
            break
        left = key
    span = right['frame'] - left['frame']
    alpha = max(0, min(1, (frame - left['frame']) / span)) if span else 0
    return [(1 - alpha) * a + alpha * b for a, b in zip(left['offset'], right['offset'])]
