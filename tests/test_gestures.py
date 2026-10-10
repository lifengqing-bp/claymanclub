import copy
import json
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path
from claymanclub.backends.gestures import gesture_angles
from claymanclub.backends.stickfigure import StickFigureBackend
from claymanclub.pipeline import render_episode
from claymanclub.validation import validate

ROOT=Path(__file__).resolve().parents[1]

class GestureTests(unittest.TestCase):
    def setUp(self):
        self.episode=json.loads((ROOT/'examples/gestures.json').read_text())
        self.catalog=json.loads((ROOT/'examples/catalog.json').read_text())
        self.shot=self.episode['shots'][0]

    def test_endpoints_peaks_and_wave_direction_changes(self):
        wave,bow=self.shot['performances']
        validate(self.episode,self.catalog)
        for frame in (-1,20,120,121):
            self.assertEqual(gesture_angles(wave,frame),{'wave':0,'bow':0})
            self.assertEqual(gesture_angles(bow,frame),{'wave':0,'bow':0})
        self.assertAlmostEqual(gesture_angles(wave,70)['wave'],-120)
        self.assertEqual(gesture_angles(bow,70)['bow'],30)
        # The raised hand reverses direction during the greeting, rather than only lifting.
        angles=[gesture_angles(wave,f)['wave'] for f in range(20,121)]
        slopes=[b-a for a,b in zip(angles,angles[1:])]
        self.assertGreaterEqual(sum(a*b<0 for a,b in zip(slopes,slopes[1:])),3)

    def test_version_duration_and_capability_rejection(self):
        for action,minimum in [('wave',17),('bow',3)]:
            episode=copy.deepcopy(self.episode)
            p=episode['shots'][0]['performances'][0]
            p['action']=action
            p['end_frame']=p['start_frame']+minimum-1
            with self.assertRaisesRegex(ValueError,'at least'):
                validate(episode,self.catalog)
            p['end_frame']+=1
            validate(episode,self.catalog)
            for version in ('0.2','0.3','0.4'):
                episode['schema_version']=version
                with self.assertRaises(ValueError):validate(episode,self.catalog)
            episode['schema_version']='0.5'
            backend=StickFigureBackend()
            backend.capabilities=replace(backend.capabilities,animated_actions=frozenset({'nod'}))
            with tempfile.TemporaryDirectory() as d:
                out=Path(d)/'out'
                for call in (lambda:render_episode(episode,self.catalog,backend,out),lambda:backend.render(episode,out)):
                    with self.assertRaisesRegex(ValueError,'unsupported backend animated'):
                        call()
                    self.assertFalse(out.exists())

    def test_svg_joint_hierarchy_and_no_mutation(self):
        original=copy.deepcopy(self.episode)
        backend=StickFigureBackend()
        root=ET.fromstring(backend.frame(self.episode,self.shot,70))
        upper=next(e for e in root.iter() if e.get('data-upper')=='pixel')
        self.assertEqual(upper.get('transform'),'rotate(30.0 0 525)')
        self.assertFalse(any('data-legs' in e.attrib for e in upper.iter()))
        arm=next(e for e in root.iter() if e.get('data-wave')=='bolt')
        self.assertAlmostEqual(float(arm.get('transform').split()[0][7:]),-120)
        self.assertEqual(self.episode,original)
        self.assertEqual(backend.frame(self.episode,self.shot,70),backend.frame(self.episode,self.shot,70))

    def test_python_javascript_gesture_parity(self):
        if not shutil.which('node'):self.skipTest('Node unavailable')
        with tempfile.TemporaryDirectory() as d:
            result=render_episode(self.episode,self.catalog,StickFigureBackend(),Path(d)/'out')
            for p in self.shot['performances']:
                data=Path(d)/'samples.json'
                data.write_text(json.dumps({'performance':p,'gestures':True,'samples':[
                    {'frame':f/2,'angles':gesture_angles(p,f/2)} for f in range(-2,250)]}))
                subprocess.run(['node',str(ROOT/'tests/motion_test.cjs'),str(result.entrypoint),str(data)],check=True)
