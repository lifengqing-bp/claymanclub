"""Engine-independent camera contract and absolute-time sampling."""
import math


def _require(condition, message):
    if not condition:
        raise ValueError('camera: ' + message)


def _number(value):
    return type(value) in (int, float) and abs(value) <= 1_000_000 and math.isfinite(value)


def validate_camera(shot, schema_version):
    if 'camera' not in shot:
        return
    _require(schema_version in ('0.3', '0.4', '0.5', '0.6'), 'requires schema_version 0.3, 0.4 or 0.5')
    camera = shot['camera']
    _require(isinstance(camera, dict), 'must be an object')
    _require(set(camera) == {'space', 'interpolation', 'keyframes'}, 'unknown or missing fields')
    _require(camera['space'] in ('framing_2d', 'framing_3d'), 'unknown space')
    _require(camera['interpolation'] == 'linear', 'unsupported interpolation')
    keys = camera['keyframes']
    _require(isinstance(keys, list) and keys, 'keyframes must be non-empty')
    previous = -1
    for key in keys:
        _require(isinstance(key, dict) and set(key) == {'frame', 'position', 'rotation', 'zoom'},
                 'keyframe requires frame, position, rotation, zoom only')
        frame = key['frame']
        _require(type(frame) is int and previous < frame <= shot['end_frame'] - shot['start_frame'],
                 'frames must increase strictly within [0, shot duration]')
        for field in ('position', 'rotation'):
            vector = key[field]
            _require(isinstance(vector, list) and len(vector) == 3 and all(_number(v) for v in vector),
                     field + ' must contain three finite numbers in [-1000000, 1000000]')
        _require(_number(key['zoom']) and key['zoom'] >= 0.000001, 'zoom must be finite and within [0.000001, 1000000]')
        if camera['space'] == 'framing_2d':
            _require(key['position'][2] == 0 and key['rotation'][:2] == [0, 0],
                     'framing_2d requires position.z and rotation.x/y to be zero')
        previous = frame
    _require(keys[0]['frame'] == 0, 'first keyframe must be at frame 0')


def preflight_camera(episode, capabilities):
    for shot in episode['shots']:
        validate_camera(shot, episode['schema_version'])
        camera = shot.get('camera')
        if camera:
            _require(camera['space'] in capabilities.camera_spaces,
                     'unsupported backend space: ' + camera['space'])
            _require(camera['interpolation'] in capabilities.camera_interpolations,
                     'unsupported backend interpolation: ' + camera['interpolation'])


def sample_camera(camera, frame):
    """Sample a validated trajectory without history; hold beyond either endpoint."""
    if camera is None:
        return {'position': [0, 0, 0], 'rotation': [0, 0, 0], 'zoom': 1}
    keys = camera['keyframes']
    left = right = keys[0]
    for key in keys:
        right = key
        if frame <= key['frame']:
            break
        left = key
    span = right['frame'] - left['frame']
    alpha = max(0, min(1, (frame - left['frame']) / span)) if span else 0
    def lerp(a, b):
        return (1 - alpha) * a + alpha * b
    return {'position': [lerp(a, b) for a, b in zip(left['position'], right['position'])],
            'rotation': [lerp(a, b) for a, b in zip(left['rotation'], right['rotation'])],
            'zoom': lerp(left['zoom'], right['zoom'])}
