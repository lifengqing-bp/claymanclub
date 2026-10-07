"""Dependency-free SVG storyboard backend, not a video or skeletal animator."""
import hashlib
import json
from html import escape
from pathlib import Path
from ..backend import Capabilities, PresentationBackend, RenderResult


class StickFigureBackend(PresentationBackend):
    name, version = 'stickfigure', '0.1'
    capabilities = Capabilities(
        frozenset({'idle', 'look_at_partner', 'look_down', 'nod'}),
        frozenset({'neutral', 'suspicious', 'guilty', 'surprised'}),
        frozenset({'wide', 'close'}), 2, 'html-svg-storyboard')

    def preflight(self, episode):
        if len(episode['cast']) > self.capabilities.max_cast:
            raise ValueError('stickfigure supports at most two actors')
        # This demo has one implemented set; actors are procedural and need no models.
        if episode['scene'] != 'robot_lounge':
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

    def frame(self, episode, shot):
        subjects = shot['framing']['subjects']
        visible = episode['cast'] if shot['framing']['size'] == 'wide' else subjects
        parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="540" height="960" viewBox="0 0 540 960">',
                 '<rect width="540" height="960" fill="#101827"/>',
                 '<rect x="35" y="120" width="470" height="650" rx="24" fill="#1b2940"/>',
                 '<path d="M35 660H505" stroke="#52647c"/>',
                 '<text x="35" y="65" fill="#e6efff" font-size="26">claymanclub · Stick figures</text>']
        by_actor = {p['actor']: p for p in shot['performances']}
        for index, actor in enumerate(visible):
            x = 270 if len(visible) == 1 else 170 + index * 200
            p = by_actor.get(actor, {'action': 'idle', 'emotion': 'neutral'})
            color = ['#64dddc', '#ffcd78'][episode['cast'].index(actor)]
            head_y = 360 if p['action'] in ('look_down', 'nod') else 345
            gaze = (6 if episode['cast'].index(actor) == 0 else -6) if p['action'] == 'look_at_partner' else 0
            parts += [f'<g transform="translate({x} 0)" stroke="{color}" stroke-width="7" stroke-linecap="round" fill="none">',
                      f'<circle cx="0" cy="{head_y}" r="40"/>',
                      '<path d="M0 395V525M0 425L-55 475M0 425L55 475M0 525L-40 635M0 525L40 635"/>',
                      f'<path d="M{-15+gaze} {head_y-5}h1M{15+gaze} {head_y-5}h1"/>']
            if p['emotion'] == 'surprised':
                parts.append(f'<circle cx="0" cy="{head_y+19}" r="8" stroke-width="3"/>')
            else:
                slope = -6 if p['emotion'] == 'suspicious' else 5 if p['emotion'] == 'guilty' else 0
                parts.append(f'<path d="M-12 {head_y+20}l24 {slope}" stroke-width="3"/>')
            parts += ['</g>', f'<text x="{x}" y="710" fill="{color}" text-anchor="middle" font-size="23">{escape(actor)}</text>']
        # Subtitle wrapping by code points is adequate for the supplied short CJK lines.
        lines = [p['actor'] + ': ' + p['line'] for p in shot['performances'] if p['line']]
        rows = [line[i:i+22] for line in lines for i in range(0, len(line), 22)]
        for i, row in enumerate(rows):
            parts.append(f'<text x="40" y="{815+i*31}" fill="#fff" font-size="23">{escape(row)}</text>')
        parts.append('</svg>')
        return ''.join(parts)

    def render(self, episode, output: Path):
        self.preflight(episode)
        output.mkdir(parents=True, exist_ok=False)
        manifest = {'backend': self.name, 'backend_version': self.version,
                    'format': self.capabilities.output_format,
                    'episode_sha256': hashlib.sha256(json.dumps(episode, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
                    'limitations': ['Static poses per shot; nod is a lowered-head key pose.',
                                    'No audio, lip sync, continuous motion or video export.'],
                    'fps': episode['fps'], 'duration_frames': episode['duration_frames'], 'shots': []}
        for i, shot in enumerate(episode['shots']):
            filename = f'shot-{i+1:03}.svg'  # Never use user IDs as output paths.
            (output / filename).write_text(self.frame(episode, shot), encoding='utf-8')
            manifest['shots'].append({'file': filename, 'start': shot['start_frame'], 'end': shot['end_frame']})
        (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        data = json.dumps({k: manifest[k] for k in ('fps', 'duration_frames', 'shots')})
        html = '''<!doctype html><meta charset="utf-8"><title>claymanclub preview</title>
<style>body{background:#101827;color:#eee;font:16px system-ui;text-align:center}img{height:75vh;max-width:95vw}button,input{margin:8px}input{width:45vw}</style>
<h2>claymanclub · 火柴人分镜预览</h2><p>静态关键姿势 · 无音频 · 非最终视频</p>
<img id="frame" alt="Storyboard frame"><div><button id="play">播放</button><input id="seek" type="range" min="0" value="0"><span id="time"></span></div>
<script>const plan=DATA;const picture=document.getElementById('frame'),seek=document.getElementById('seek'),button=document.getElementById('play');
let playing=false,t=0,last=null;seek.max=plan.duration_frames-1;
function draw(){const f=Math.min(plan.duration_frames-1,Math.floor(t));const s=plan.shots.find(s=>f>=s.start&&f<s.end);if(picture.getAttribute('src')!==s.file)picture.src=s.file;seek.value=f;document.getElementById('time').textContent=(f/plan.fps).toFixed(1)+'s';}
button.onclick=()=>{if(t>=plan.duration_frames-1)t=0;playing=!playing;last=null;button.textContent=playing?'暂停':'播放';};
seek.oninput=()=>{t=Number(seek.value);last=null;draw();};
function tick(now){if(playing&&last!==null){t+=(now-last)*plan.fps/1000;if(t>=plan.duration_frames-1){t=plan.duration_frames-1;playing=false;button.textContent='播放';}draw();}last=now;requestAnimationFrame(tick);}draw();requestAnimationFrame(tick);</script>'''.replace('DATA', data)
        (output / 'index.html').write_text(html, encoding='utf-8')
        return RenderResult(output / 'index.html', output / 'manifest.json')
