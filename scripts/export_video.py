#!/usr/bin/env python3
"""Optional Linux demo export: actual stickfigure SVG frames -> librsvg -> FFmpeg.

Requires system librsvg-2, Cairo and ffmpeg with libx264. No browser or audio.
Core rendering stays dependency-free. Run from the repository root.
"""
import argparse
import ctypes as C
import ctypes.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claymanclub.backends.stickfigure import StickFigureBackend
from claymanclub.validation import validate


def library(name):
    path = ctypes.util.find_library(name)
    if not path:
        raise RuntimeError(f'Optional video export requires system library: {name}')
    return C.CDLL(path)


def bind(lib, name, restype, *args):
    fn = getattr(lib, name)
    fn.restype, fn.argtypes = restype, list(args)
    return fn


def export(source, output, catalog):
    if output.exists():
        raise ValueError(f'Output already exists: {output}')
    episode = json.loads(source.read_text())
    validate(episode, json.loads(catalog.read_text()))
    backend = StickFigureBackend()
    backend.preflight(episode)
    if not shutil.which('ffmpeg'):
        raise RuntimeError('Optional video export requires ffmpeg with libx264')
    rsvg, cairo, gobject = library('rsvg-2'), library('cairo'), library('gobject-2.0')
    new_svg = bind(rsvg, 'rsvg_handle_new_from_data', C.c_void_p, C.c_char_p, C.c_size_t, C.c_void_p)
    render = bind(rsvg, 'rsvg_handle_render_cairo', C.c_int, C.c_void_p, C.c_void_p)
    unref = bind(gobject, 'g_object_unref', None, C.c_void_p)
    surface_new = bind(cairo, 'cairo_image_surface_create', C.c_void_p, C.c_int, C.c_int, C.c_int)
    context_new = bind(cairo, 'cairo_create', C.c_void_p, C.c_void_p)
    context_free = bind(cairo, 'cairo_destroy', None, C.c_void_p)
    surface_free = bind(cairo, 'cairo_surface_destroy', None, C.c_void_p)
    flush = bind(cairo, 'cairo_surface_flush', None, C.c_void_p)
    data = bind(cairo, 'cairo_image_surface_get_data', C.c_void_p, C.c_void_p)
    stride = bind(cairo, 'cairo_image_surface_get_stride', C.c_int, C.c_void_p)
    status = bind(cairo, 'cairo_surface_status', C.c_int, C.c_void_p)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Cairo ARGB32 bytes are BGRA on the supported little-endian Linux host.
    if sys.byteorder != 'little':
        raise RuntimeError('This demo exporter requires a little-endian host')
    cmd = ['ffmpeg','-hide_banner','-loglevel','error','-n','-f','rawvideo',
           '-pixel_format','bgra','-video_size','540x960','-framerate',str(episode['fps']),
           '-i','pipe:0','-an','-c:v','libx264','-preset','medium','-crf','18',
           '-pix_fmt','yuv420p','-movflags','+faststart',str(output)]
    process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for shot in episode['shots']:
            for frame in range(shot['end_frame']-shot['start_frame']):
                svg = backend.frame(episode, shot, frame).encode()
                handle = new_svg(svg,len(svg),None)
                if not handle: raise RuntimeError('librsvg could not parse generated frame')
                surface = surface_new(0,540,960)
                context = context_new(surface)
                try:
                    if status(surface) or not render(handle,context):
                        raise RuntimeError('Could not rasterize generated SVG')
                    flush(surface)
                    if stride(surface) != 540*4: raise RuntimeError('Unexpected Cairo stride')
                    process.stdin.write(C.string_at(data(surface),540*960*4))
                finally:
                    context_free(context)
                    surface_free(surface)
                    unref(handle)
            print(f'Rendered {shot["id"]} through frame {shot["end_frame"]}',flush=True)
        process.stdin.close()
        if process.wait(): raise RuntimeError('FFmpeg export failed')
    except BaseException:
        process.terminate()
        process.wait()
        raise
    print(f'{output}: {episode["duration_frames"]} frames, {episode["fps"]} fps, no audio')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--catalog',type=Path,default=Path(__file__).resolve().parents[1]/'examples/catalog.json')
    args = parser.parse_args()
    export(args.source,args.output,args.catalog)
