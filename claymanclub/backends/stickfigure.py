"""Dependency-free SVG storyboard backend, not a video or skeletal animator."""
import hashlib
import json
from html import escape
from pathlib import Path
from ..camera import preflight_camera, sample_camera
from ..performance import active_performances, performance_boundaries, preflight_performances, nod_amount, TIMED_VERSIONS, ANIMATED_ACTIONS, ANIMATED_VERSIONS
from .gestures import gesture_angles, walk_swing, joint_angles, jump_height
from .weather import weather_svg, umbrella_svg
from ..environment import WEATHER, preflight_environment, holding
from ..staging import preflight_tracks, sample_offset
from .scenes import SCENES, scene_svg
from ..backend import Capabilities, PresentationBackend, RenderResult


def limb_svg(actor, side, kind, rotation, bend):
    """Two rigid segments, with one local elbow/knee hinge under the root pivot."""
    direction = -1 if side == 'left' else 1
    if kind == 'arm':
        root_y, joint_x, joint_y, end_x, end_y = 425, direction * 27.5, 450, direction * 55, 475
        parent = f'data-wave="{escape(actor, quote=True)}"' if side == 'right' else 'data-walk-arm=""'
        joint = 'elbow'
    else:
        root_y, joint_x, joint_y, end_x, end_y = 525, direction * 20, 580, direction * 40, 635
        parent = f'data-walk-leg="{side}"'
        joint = 'knee'
    return (f'<g {parent} data-limb="{kind}" data-side="{side}" transform="rotate({rotation} 0 {root_y})">'
            f'<path data-proximal="" d="M0 {root_y}L{joint_x} {joint_y}"/>'
            f'<g data-bend="{joint}" data-side="{side}" data-joint-x="{joint_x}" data-joint-y="{joint_y}" '
            f'transform="rotate({bend} {joint_x} {joint_y})">'
            f'<path data-distal="" d="M{joint_x} {joint_y}L{end_x} {end_y}"/>'
            '</g>'
            f'<circle data-joint-marker="{joint}" cx="{joint_x}" cy="{joint_y}" r="4" stroke-width="3" fill="#1b2940"/>'
            '</g>')


class StickFigureBackend(PresentationBackend):
    name, version = 'stickfigure', '0.9'
    capabilities = Capabilities(
        frozenset({'idle', 'look_at_partner', 'look_down', 'nod', 'wave', 'bow', 'walk', 'run', 'jump'}),
        frozenset({'neutral', 'suspicious', 'guilty', 'surprised'}),
        frozenset({'wide', 'close'}), 2, 'html-svg-storyboard',
        frozenset({'framing_2d'}), frozenset({'linear'}), timed_performances=True,
        actor_spaces=frozenset({'stage_2d'}), gaze_targets=True, animated_actions=ANIMATED_ACTIONS, weather=WEATHER, interactions=frozenset({('hold', 'umbrella')}))

    def preflight(self, episode):
        preflight_environment(episode, self.capabilities)
        preflight_camera(episode, self.capabilities)
        preflight_tracks(episode, self.capabilities)
        preflight_performances(episode, self.capabilities)
        if len(episode['cast']) > self.capabilities.max_cast:
            raise ValueError('stickfigure supports at most two actors')
        # Scene IDs remain semantic; each backend owns its procedural bindings.
        if episode['scene'] not in SCENES:
            raise ValueError('stickfigure has no scene binding: ' + episode['scene'])
        for shot in episode['shots']:
            if shot['framing']['size'] not in self.capabilities.framing:
                raise ValueError('unsupported framing')
            for p in shot['performances']:
                if p['action'] not in self.capabilities.actions:
                    raise ValueError('unsupported action: ' + p['action'])
                if p['emotion'] not in self.capabilities.emotions:
                    raise ValueError('unsupported emotion: ' + p['emotion'])
                if p['action'] == 'look_at_partner' and len(episode['cast']) != 2:
                    raise ValueError('look_at_partner requires two actors')

    def frame(self, episode, shot, local_frame=0):
        animated = episode['schema_version'] in ANIMATED_VERSIONS
        performances = active_performances(shot, episode['schema_version'], local_frame)
        subjects = shot['framing']['subjects']
        visible = episode['cast'] if shot['framing']['size'] == 'wide' else subjects
        state = sample_camera(shot.get('camera'), local_frame)
        x, y, _ = state['position']
        transform = (f'translate(270 480) scale({state["zoom"]}) '
                     f'rotate({state["rotation"][2]}) translate({-270-x*960} {-480+y*960})')
        parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="540" height="960" viewBox="0 0 540 960">',
                 '<rect width="540" height="960" fill="#101827"/>',
                 f'<g data-camera-world="" transform="{transform}">',
                 scene_svg(episode['scene'])]
        if 'weather' in shot:
            parts.append(weather_svg(shot['weather']['kind'], local_frame))
        by_actor = {p['actor']: p for p in performances}
        spatial = episode['schema_version'] in ('0.6', '0.7')
        tracks = {track['actor']: track for track in shot.get('actor_tracks', [])}
        offsets = {a: sample_offset(tracks.get(a), local_frame) for a in episode['cast']}
        stage_x = {a: (270 if len(episode['cast']) == 1 else 170 + i * 200) + offsets[a][0] * 960
                   for i, a in enumerate(episode['cast'])}
        for index, actor in enumerate(visible):
            x = 270 if len(visible) == 1 else 170 + index * 200
            p = by_actor.get(actor, {'action': 'idle', 'emotion': 'neutral'})
            color = ['#64dddc', '#ffcd78'][episode['cast'].index(actor)]
            head_fill = '#1b2940' if episode['scene'] in ('wireframe_lounge', 'wireframe_park') else 'none'
            head_y = 360 if p['action'] == 'look_down' or (p['action'] == 'nod' and not animated) else 345
            gaze = (6 if episode['cast'].index(actor) == 0 else -6) if p['action'] == 'look_at_partner' else 0
            if 'gaze_target' in p:
                gaze = 6 if episode['cast'].index(p['gaze_target']) > episode['cast'].index(actor) else -6
            target = p.get('gaze_target')
            if spatial and p['action'] == 'look_at_partner' and target is None:
                target = next(a for a in episode['cast'] if a != actor)
            if spatial and target is not None:
                delta = stage_x[target] - stage_x[actor]
                gaze = 6 if delta > 0 else -6 if delta < 0 else 0
            dx, dy, _ = offsets[actor]
            if p['action'] == 'jump':
                dy += jump_height(p, local_frame) / 960
            held = holding(shot, actor, local_frame)
            swing = walk_swing(p, local_frame) if spatial else 0
            bends = joint_angles(p, local_frame) if animated else joint_angles(None, 0)
            if held:
                bends['elbow_right'] = -25
            head_offset = 15 * nod_amount(p, local_frame) if animated else 0
            joints = gesture_angles(p, local_frame) if animated else {'bow': 0, 'wave': 0}
            parts += [f'<g data-actor="{escape(actor, quote=True)}" data-base-x="{x}" transform="translate({x+dx*960} {-dy*960})" stroke="{color}" stroke-width="7" stroke-linecap="round" fill="none">',
                      f'<g data-upper="{escape(actor, quote=True)}" transform="rotate({joints["bow"]} 0 525)">',
                      f'<g data-head="{escape(actor, quote=True)}" transform="translate(0 {head_offset})">',
                      f'<circle cx="0" cy="{head_y}" r="40" fill="{head_fill}"/>',
                      f'<path data-eyes="{escape(actor, quote=True)}" data-head-y="{head_y}" d="M{-15+gaze} {head_y-5}h1M{15+gaze} {head_y-5}h1"/>']
            if p['emotion'] == 'surprised':
                parts.append(f'<circle cx="0" cy="{head_y+19}" r="8" stroke-width="3"/>')
            else:
                slope = -6 if p['emotion'] == 'suspicious' else 5 if p['emotion'] == 'guilty' else 0
                parts.append(f'<path d="M-12 {head_y+20}l24 {slope}" stroke-width="3"/>')
            parts += ['</g>', '<path d="M0 395V525"/>',
                      limb_svg(actor, 'left', 'arm', -swing, bends['elbow_left']),
                      limb_svg(actor, 'right', 'arm', -65 if held else joints['wave'] + swing, bends['elbow_right']),
                      '</g>',
                      limb_svg(actor, 'left', 'leg', swing, bends['knee_left']),
                      limb_svg(actor, 'right', 'leg', -swing, bends['knee_right']),
                      umbrella_svg(joints['bow'], held) if episode['schema_version'] == '0.7' else '',
                      '</g>', f'<text text-rendering="geometricPrecision" data-name="{escape(actor, quote=True)}" data-base-x="{x}" transform="translate({dx*960} {-dy*960})" x="{x}" y="710" fill="{color}" text-anchor="middle" font-size="23">{escape(actor)}</text>']
        parts += ['</g>', '<rect width="540" height="100" fill="#101827"/>',
                  '<rect y="780" width="540" height="180" fill="#101827"/>', '<text x="35" y="65" fill="#e6efff" font-size="26">claymanclub · Stick figures</text>']
        # Subtitle wrapping by code points is adequate for the supplied short CJK lines.
        lines = [p['actor'] + ': ' + p['line'] for p in performances if p['line']]
        rows = [line[i:i+22] for line in lines for i in range(0, len(line), 22)]
        for i, row in enumerate(rows):
            parts.append(f'<text x="40" y="{815+i*31}" fill="#fff" font-size="23">{escape(row)}</text>')
        parts.append('</svg>')
        return ''.join(parts)

    def render(self, episode, output: Path):
        self.preflight(episode)
        output.mkdir(parents=True, exist_ok=False)
        manifest = {'backend': self.name, 'backend_version': self.version,
                    'format': self.capabilities.output_format, 'scene': episode['scene'],
                    'episode_sha256': hashlib.sha256(json.dumps(episode, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
                    'limitations': ['v0.5 supports procedural nod, wave and bow; older versions retain key poses.',
                                    'v0.6 adds actor offsets and walking; v0.7 adds run/jump, held umbrella and visual weather.',
                                    'No pickup/drop, collision, foot locking, depth sorting, audio or lip sync.'],
                    'fps': episode['fps'], 'duration_frames': episode['duration_frames'], 'shots': []}
        preview_shots = []
        for i, shot in enumerate(episode['shots']):
            filename = f'shot-{i+1:03}.svg'  # Never use user IDs as output paths.
            svg = self.frame(episode, shot)
            (output / filename).write_text(svg, encoding='utf-8')
            preview = {'camera': shot.get('camera'),
                       'start': shot['start_frame'], 'end': shot['end_frame']}
            if episode['schema_version'] in TIMED_VERSIONS:
                preview['poses'] = [{'start': f, 'svg': svg if f == 0 else self.frame(episode, shot, f)}
                                    for f in performance_boundaries(shot, episode['schema_version'])]
            else:
                preview['svg'] = svg
            if episode['schema_version'] in ANIMATED_VERSIONS:
                preview['motions'] = [p for p in shot['performances'] if p['action'] in ANIMATED_ACTIONS]
            if episode['schema_version'] in ('0.6', '0.7'):
                preview['actor_tracks'] = shot.get('actor_tracks', [])
                preview['performances'] = shot['performances']
                preview['cast'] = episode['cast']
            if episode['schema_version'] == '0.7':
                preview['weather'] = shot.get('weather')
                preview['interactions'] = shot.get('interactions', [])
            preview_shots.append(preview)
            manifest['shots'].append({'file': filename, 'start': shot['start_frame'], 'end': shot['end_frame'],
                                      'camera': shot.get('camera'), 'performances': shot['performances'],
                                      'actor_tracks': shot.get('actor_tracks', []),
                                      'weather': shot.get('weather'), 'interactions': shot.get('interactions', [])})
        (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        data = json.dumps({'fps': episode['fps'], 'duration_frames': episode['duration_frames'],
                           'shots': preview_shots}).replace('<', '\\u003c')
        player = Path(__file__).with_name('player.js').read_text(encoding='utf-8')
        html = '''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>claymanclub preview</title>
<style>body{background:#101827;color:#eee;font:16px system-ui;text-align:center}svg{display:block;margin:auto;width:min(95vw,42.1875vh);height:auto;overflow:hidden}button,input{margin:8px}input{width:45vw}</style>
<h2>claymanclub · 火柴人分镜预览</h2><p>定时表演 · 二维运镜 · 无音频 · 非最终视频</p>
<div id="frame" role="img" aria-label="Storyboard frame"></div><div><button id="play">播放</button><input id="seek" aria-label="Frame" type="range" min="0" value="0"><span id="time"></span></div>
<script>const plan=''' + data + ';\n' + player + '</script>'
        (output / 'index.html').write_text(html, encoding='utf-8')
        return RenderResult(output / 'index.html', output / 'manifest.json')
