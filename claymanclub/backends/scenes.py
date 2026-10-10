"""Procedural scene bindings. Line geometry belongs to this backend, not stories."""
from html import escape


def _prop(identity, kind, paths):
    return (f'<g data-prop="{escape(identity, quote=True)}" data-prop-kind="{kind}" '
            'fill="none" stroke="#88a5b6" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round">'
            + ''.join(f'<path d="{path}"/>' for path in paths) + '</g>')


def robot_lounge():
    return ('<rect x="35" y="120" width="470" height="650" rx="24" fill="#1b2940"/>'
            '<path d="M35 660H505" stroke="#52647c"/>')


def wireframe_lounge():
    """A fixed line-perspective set; the existing 2D camera moves the whole set."""
    room = ('<rect x="35" y="120" width="470" height="650" rx="24" fill="#1b2940"/>'
            '<g data-room-wireframe="" fill="none" stroke="#587487" stroke-width="1.5">'
            '<path d="M35 140L78 188H462L505 140M78 188V520H462V188M35 770L78 520M462 520L505 770"/>'
            '<g data-floor-grid="" stroke="#40596d" stroke-width="1">'
            '<path d="M76 544H466M67 582H473M54 644H485M41 724H500"/>'
            '<path d="M139 520L88 770M205 520L184 770M270 520V770M335 520L356 770M401 520L453 770"/>'
            '</g></g>')
    window = _prop('rear-window', 'window', [
        'M103 220H235V342H103Z', 'M111 228H227V334H111Z',
        'M169 228V334M111 280H227', 'M96 342H241L247 350H101Z'])
    shelf = _prop('book-shelf', 'shelf', [
        'M366 238L352 226H422L436 238V454H366ZM352 226V440L366 454',
        'M366 238H436M366 306H436M366 376H436',
        'M374 299V256H384V299M389 299V267H397V299M403 299L397 257L407 255L413 299',
        'M378 369V332H411V369ZM378 342H411',
        'M375 444V399H385V444M389 444V405H399V444M405 444V395H416V444'])
    table = _prop('coffee-table', 'table', [
        'M210 483H300L331 507H238ZM210 483V491L238 516H331V507M238 507V516',
        'M218 498V561M245 516V590M322 516V586',
        'M260 484V470H277V484M277 473H283V480H277'])
    chair = _prop('side-chair', 'chair', [
        'M425 456H468V525H425ZM430 461H463V494H430Z',
        'M425 506L405 533H451L468 506M405 533V541H451V533',
        'M409 541V598M447 541V604M465 514V573M425 525V568'])
    plant = _prop('corner-plant', 'plant', [
        'M91 492H122L118 524H96ZM92 498H122',
        'M107 492V419M107 463Q81 464 83 445Q103 439 107 463',
        'M107 451Q131 449 130 429Q111 429 107 451',
        'M107 431Q88 424 96 407Q113 414 107 431'])
    return room + window + shelf + table + chair + plant


SCENES = {'robot_lounge': robot_lounge, 'wireframe_lounge': wireframe_lounge}


def scene_svg(scene):
    if scene not in SCENES:
        raise ValueError('stickfigure has no scene binding: ' + scene)
    return f'<g data-scene="{escape(scene, quote=True)}">{SCENES[scene]()}</g>'


def wireframe_park():
    return ('<rect x="15" y="110" width="510" height="660" rx="16" fill="#1b2940"/>'
            '<g fill="none" stroke="#718c9e" stroke-width="2">'
            '<path d="M20 555H520M240 555L40 770M300 555L500 770M160 640H370M100 710H440"/>'
            '<path d="M20 480H520M20 510H520M40 465V545M110 465V545M180 465V545M250 465V545M320 465V545M390 465V545M460 465V545"/>'
            '<path data-prop="bench" d="M350 580H490L475 550H360ZM360 550V518H475V550M365 580V615M480 580V615"/>'
            '<path data-prop="tree" d="M65 520V360M80 520V360M72 350Q-5 390 30 315Q-5 270 40 260Q60 210 95 258Q150 250 120 307Q160 365 72 350"/>'
            '</g>')


SCENES['wireframe_park'] = wireframe_park
