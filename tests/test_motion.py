import copy
import json
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path
from claymanclub.performance import nod_amount
from claymanclub.validation import validate
from claymanclub.pipeline import render_episode
from claymanclub.backends.stickfigure import StickFigureBackend

ROOT=Path(__file__).resolve().parents[1]

class MotionTests(unittest.TestCase):
    def setUp(self):
        self.episode=json.loads((ROOT/'examples/gaze-and-nod.json').read_text())
        self.catalog=json.loads((ROOT/'examples/catalog.json').read_text())
        self.shot=self.episode['shots'][0]
        self.nod=self.shot['performances'][0]

    def test_nod_cycle_endpoints_and_symmetry(self):
        validate(self.episode,self.catalog)
        for frame,amount in [(19,0),(20,0),(45,.5),(70,1),(95,.5),(120,0),(121,0)]:
            self.assertAlmostEqual(nod_amount(self.nod,frame),amount)
        for f in range(20,121):
            self.assertAlmostEqual(nod_amount(self.nod,f),nod_amount(self.nod,140-f))
        self.nod['end_frame']=23
        self.assertEqual(nod_amount(self.nod,21),1)
        for duration in (1,2):
            self.nod['end_frame']=20+duration
            with self.assertRaisesRegex(ValueError,'at least 3'):
                validate(self.episode,self.catalog)

    def test_gaze_references_and_legacy_versions(self):
        for target in ('bolt','missing',None,True,{},[]):
            self.nod['gaze_target']=target
            with self.subTest(target=target),self.assertRaisesRegex(ValueError,'gaze_target'):
                validate(self.episode,self.catalog)
        self.nod['gaze_target']='pixel'
        self.nod['action']='look_down'
        with self.assertRaisesRegex(ValueError,'conflicts'):
            validate(self.episode,self.catalog)
        self.nod['action']='nod'
        for version in ('0.2','0.3','0.4'):
            self.episode['schema_version']=version
            with self.subTest(version=version),self.assertRaises(ValueError):
                validate(self.episode,self.catalog)

    def test_capability_failure_before_output(self):
        for setting in ({'gaze_targets':False},{'animated_actions':frozenset()}):
            backend=StickFigureBackend()
            backend.capabilities=replace(backend.capabilities,**setting)
            with tempfile.TemporaryDirectory() as d:
                out=Path(d)/'out'
                for call in (lambda:render_episode(self.episode,self.catalog,backend,out),lambda:backend.render(self.episode,out)):
                    with self.assertRaisesRegex(ValueError,'unsupported backend'):
                        call()
                    self.assertFalse(out.exists())

    def test_svg_head_gaze_and_legacy_pose(self):
        backend=StickFigureBackend()
        original=copy.deepcopy(self.episode)
        def head(frame):
            root=ET.fromstring(backend.frame(self.episode,self.shot,frame))
            return next(e for e in root.iter() if e.get('data-head')=='bolt')
        self.assertEqual(head(20).get('transform'),'translate(0 0.0)')
        self.assertEqual(head(70).get('transform'),'translate(0 15.0)')
        self.assertEqual(head(120).get('transform'),'translate(0 0.0)')
        self.assertEqual(head(121).get('transform'),'translate(0 0.0)')
        self.assertEqual(list(head(70))[1].get('d'),'M-9 340h1M21 340h1')
        root=ET.fromstring(backend.frame(self.episode,self.shot,70))
        other=next(e for e in root.iter() if e.get('data-head')=='pixel')
        self.assertEqual(list(other)[1].get('d'),'M-21 340h1M9 340h1')
        self.assertEqual(self.episode,original)
        self.episode['schema_version']='0.4'
        for p in self.shot['performances']: p.pop('gaze_target',None)
        self.assertEqual(list(head(70))[0].get('cy'),'360')
        self.assertEqual(head(70).get('transform'),'translate(0 0)')

    def test_javascript_sampler_matches_python(self):
        if not shutil.which('node'): self.skipTest('Node unavailable')
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'render'
            render_episode(self.episode,self.catalog,StickFigureBackend(),out)
            samples=[{'frame':f/2,'amount':nod_amount(self.nod,f/2)} for f in range(-2,250)]
            data=Path(d)/'samples.json'
            data.write_text(json.dumps({'performance':self.nod,'samples':samples}))
            subprocess.run(['node',str(ROOT/'tests/motion_test.cjs'),str(out/'index.html'),str(data)],check=True)
