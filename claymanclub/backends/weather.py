"""Deterministic line weather. All coordinates live inside the camera world."""
import math


def weather_state(kind, frame):
    return {'cloud_x': (frame * .22) % 620 - 80,
            'wind_x': (frame * 3) % 720 - 120,
            'rain': [((i * 73 + frame * 4) % 600 - 30,
                      180 + (i * 97 + frame * 13) % 580) for i in range(38)],
            'flash': kind == 'storm' and 35 <= frame % 150 < 41}


def weather_svg(kind, frame):
    s = weather_state(kind, frame)
    parts = [f'<g data-weather="{kind}" fill="none" stroke-linecap="round">']
    if kind == 'sunny':
        parts += ['<g stroke="#ffdc89" stroke-width="3"><path d="M407 175a28 28 0 1 0 56 0a28 28 0 1 0 -56 0"/>']
        for i in range(12):
            a = i * math.pi / 6
            parts.append(f'<path d="M{435+38*math.cos(a)} {175+38*math.sin(a)}L{435+49*math.cos(a)} {175+49*math.sin(a)}"/>')
        parts.append('</g>')
    if kind in ('cloudy', 'overcast', 'rain', 'storm'):
        count = 2 if kind == 'cloudy' else 5
        color = '#aec5d4' if kind == 'cloudy' else '#64788e'
        parts.append(f'<g data-clouds="" transform="translate({s["cloud_x"]} 0)" stroke="{color}" stroke-width="3">')
        for i in range(count):
            # Wrap duplicate silhouettes cover the viewport during drift.
            for shift in (0, -620):
                parts.append(f'<path transform="translate({i*140+shift} {155+(i%2)*40})" fill="#24354a" d="M0 35Q-10 5 20 5Q40 -30 65 0Q100 -15 112 15Q145 12 140 35Z"/>')
        parts.append('</g>')
    if kind in ('windy', 'storm'):
        parts.append(f'<g data-wind="" transform="translate({s["wind_x"]} 0)" stroke="#b8d6df" stroke-width="2" opacity=".7">')
        for i in range(7):
            parts.append(f'<path d="M{i*55-350} {270+i*57}h130q30 0 24 -17q-7 -12 -18 -3"/>')
        parts.append('</g>')
    if kind in ('rain', 'storm'):
        parts.append('<g stroke="#86c9ea" stroke-width="2" opacity=".7">')
        for i, (x, y) in enumerate(s['rain']):
            parts.append(f'<path data-rain="{i}" d="M{x} {y}l-10 24"/>')
        parts.append('</g>')
    if kind == 'storm':
        parts.append(f'<g data-lightning="" opacity="{1 if s["flash"] else 0}"><rect x="15" y="110" width="510" height="660" fill="#bdcbe5" opacity=".12"/><path d="M345 185L308 254H345L294 345L365 238H333L374 185" stroke="#fff2bc" stroke-width="4"/></g>')
    return ''.join(parts) + '</g>'


def umbrella_pose(bow):
    # Forward kinematics of right hand, shoulder -65°, elbow -25°.
    a, b = math.radians(-65), math.radians(-90)
    x = 27.5*math.cos(a)-25*math.sin(a)+27.5*math.cos(b)-25*math.sin(b)
    y = 425+27.5*math.sin(a)+25*math.cos(a)+27.5*math.sin(b)+25*math.cos(b)
    c = math.radians(bow)
    return [x*math.cos(c)-(y-525)*math.sin(c), 525+x*math.sin(c)+(y-525)*math.cos(c)]


def umbrella_svg(bow, visible):
    x, y = umbrella_pose(bow)
    return (f'<g data-held-prop="umbrella" display="{"inline" if visible else "none"}" transform="translate({x} {y})" stroke="#d9ebf6" stroke-width="3">'
            '<path d="M0 0V-165M-90 -135Q0 -240 90 -135Q60 -149 30 -135Q0 -149 -30 -135Q-60 -149 -90 -135Z" fill="#24354a"/>'
            '<path d="M-30 -135Q-25 -180 0 -188Q25 -180 30 -135"/></g>')
