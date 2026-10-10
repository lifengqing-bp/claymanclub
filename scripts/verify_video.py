#!/usr/bin/env python3
"""Verify the silent One More Take deliverable before publishing it."""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess


def verify(video):
    probe = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-count_frames', '-show_streams',
        '-show_format', '-of', 'json', str(video)], text=True))
    streams = probe['streams']
    if len(streams) != 1 or streams[0]['codec_type'] != 'video':
        raise ValueError('Expected one video stream and no audio')
    stream = streams[0]
    expected = {'codec_name': 'h264', 'width': 540, 'height': 960,
                'pix_fmt': 'yuv420p', 'nb_read_frames': '1080'}
    for key, value in expected.items():
        if stream.get(key) != value:
            raise ValueError(f'{key}: expected {value}, got {stream.get(key)}')
    for key in ('r_frame_rate', 'avg_frame_rate'):
        if Fraction(stream[key]) != 30:
            raise ValueError(f'Expected 30 fps: {key}={stream[key]}')
    if abs(float(probe['format']['duration']) - 36) > 0.001:
        raise ValueError('Expected 36 seconds')
    subprocess.run(['ffmpeg', '-hide_banner', '-v', 'error', '-xerror',
                    '-err_detect', 'explode', '-i', str(video),
                    '-map', '0:v:0', '-f', 'null', '-'], check=True)
    digest = hashlib.sha256(video.read_bytes()).hexdigest()
    report = dict(file=video.name, sha256=digest, width=540, height=960,
                  fps=30, frames=1080, duration_seconds=36,
                  codec='h264', audio_streams=0, full_decode='passed')
    video.with_suffix('.verification.json').write_text(json.dumps(report, indent=2) + '\n')
    video.with_suffix('.sha256').write_text(f'{digest}  {video.name}\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('video', type=Path)
    verify(parser.parse_args().video)
