#!/usr/bin/env python3
"""Validate a draft shot plan; does not validate renderability or audio timing."""
import argparse
import json
from pathlib import Path
from .camera import validate_camera
from .performance import validate_performances


def require(condition, message):
    if not condition:
        raise ValueError(message)


def positive_int(value):
    return type(value) is int and value > 0


def validate(episode, catalog):
    require(isinstance(episode, dict), 'episode must be an object')
    require(episode.get('schema_version') in ('0.2', '0.3', '0.4'), 'unsupported schema_version')
    require(isinstance(episode.get('episode_id'), str) and episode['episode_id'], 'episode_id required')
    require(positive_int(episode.get('fps')), 'fps must be a positive integer')
    require(positive_int(episode.get('duration_frames')), 'duration_frames must be a positive integer')
    require(episode.get('scene') in catalog['scenes'], 'unknown scene')
    cast = episode.get('cast')
    require(isinstance(cast, list) and cast and all(isinstance(a, str) for a in cast), 'cast must contain actor IDs')
    require(len(set(cast)) == len(cast), 'duplicate cast member')
    require(all(a in catalog['actors'] for a in cast), 'unknown actor in cast')
    shots = episode.get('shots')
    require(isinstance(shots, list) and shots, 'shots must be a non-empty list')
    cursor, ids = 0, set()
    for shot in shots:
        require(isinstance(shot, dict), 'shot must be an object')
        sid = shot.get('id')
        require(isinstance(sid, str) and sid and sid not in ids, 'missing or duplicate shot ID')
        ids.add(sid)
        start, end = shot.get('start_frame'), shot.get('end_frame')
        require(type(start) is int and type(end) is int and start == cursor and end > start,
                f'{sid}: frames must be contiguous and have positive duration')
        validate_camera(shot, episode['schema_version'])
        framing = shot.get('framing')
        require(isinstance(framing, dict), f'{sid}: framing required')
        require(framing.get('size') in ('wide', 'close'), f'{sid}: unknown framing size')
        subjects = framing.get('subjects')
        require(isinstance(subjects, list) and subjects and all(isinstance(a, str) and a in cast for a in subjects), f'{sid}: invalid subjects')
        require(len(subjects) == len(set(subjects)), f'{sid}: duplicate subjects')
        require(framing['size'] != 'close' or len(subjects) == 1, f'{sid}: close requires one subject')
        performances = shot.get('performances')
        require(isinstance(performances, list) and performances, f'{sid}: performances required')
        actors = set()
        for performance in performances:
            require(isinstance(performance, dict), f'{sid}: performance must be an object')
            actor = performance.get('actor')
            require(isinstance(actor, str) and actor in cast, f'{sid}: actor must be in cast')
            require(episode['schema_version'] == '0.4' or actor not in actors,
                    f'{sid}: legacy actor must appear at most once')
            actors.add(actor)
            for field, group in [('action', 'actions'), ('emotion', 'emotions')]:
                require(performance.get(field) in catalog[group], f'{sid}: unknown {field}')
            require(isinstance(performance.get('line'), str), f'{sid}: line must be a string')
        validate_performances(shot, episode['schema_version'])
        cursor = end
    require(cursor == episode['duration_frames'], 'shots must cover duration_frames exactly')

