import copy
import json
import subprocess
import unittest
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path
from claymanclub.validation import validate
from claymanclub.environment import preflight_environment, holding
from claymanclub.backends.stickfigure import StickFigureBackend
from claymanclub.backends.gestures import jump_height, walk_swing, joint_angles
from claymanclub.backends.weather import weather_state, umbrella_pose

ROOT=Path(__file__).resolve().parents[1]


class EnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.e=json.loads((ROOT/'examples/weather-walk.json').read_text())
        self.c=json.loads((ROOT/'examples/catalog.json').read_text())

    def test_contract_and_explicit_rejections(self):
        validate(self.e,self.c)
        StickFigureBackend().preflight(self.e)
        for mutate in [lambda e:e.update(schema_version='0.6'),
                       lambda e:e['shots'][0].update(weather={'kind':'snow'}),
                       lambda e:e['shots'][0].update(weather={'kind':'sunny','seed':2}),
                       lambda e:e['shots'][4]['interactions'][0].update(action='throw'),
                       lambda e:e['shots'][4]['interactions'][0].update(prop='table'),
                       lambda e:e['shots'][4]['interactions'][0].update(start_frame=True),
                       lambda e:e['shots'][4]['interactions'][0].update(end_frame=151),
                       lambda e:e['shots'][4]['interactions'].append(dict(e['shots'][4]['interactions'][0],actor='pixel'))]:
            e=copy.deepcopy(self.e);mutate(e)
            with self.assertRaises(ValueError):validate(e,self.c)
        for caps in [replace(StickFigureBackend.capabilities,weather=frozenset()),
                     replace(StickFigureBackend.capabilities,interactions=frozenset())]:
            with self.assertRaises(ValueError):preflight_environment(self.e,caps)
        backend=StickFigureBackend();backend.capabilities=replace(backend.capabilities,animated_actions=frozenset({'walk'}))
        with self.assertRaisesRegex(ValueError,'unsupported backend animated action'):backend.preflight(self.e)

    def test_motion_and_ownership_boundaries(self):
        p=self.e['shots'][2]['performances'][0]
        for f in [-1,0,149,150]:self.assertEqual(jump_height(p,f),0)
        self.assertGreater(jump_height(p,74),99)
        run=self.e['shots'][1]['performances'][0]
        self.assertNotEqual(walk_swing(run,50),walk_swing(dict(run,action='walk'),50))
        shot=self.e['shots'][4]
        for f,expected in [(-1,False),(0,True),(149,True),(150,False)]:self.assertEqual(holding(shot,'bolt',f),expected)
        self.assertFalse(holding(self.e['shots'][3],'bolt',100))
        for f,expected in [(34,False),(35,True),(40,True),(41,False),(185,True)]:self.assertEqual(weather_state('storm',f)['flash'],expected)

    def test_python_javascript_parity(self):
        samples=[]
        for shot in self.e['shots']:
            p=shot['performances'][0]
            for f in [0,.5,12,35,40,41,74,120,149,150]:
                samples.append(dict(p=p,f=f,kind=shot['weather']['kind'],jump=jump_height(p,f),swing=walk_swing(p,f),joints=joint_angles(p,f),weather=weather_state(shot['weather']['kind'],f)))
        source=(ROOT/'claymanclub/backends/player.js').read_text().split('const picture=document')[0]
        js=source+'''
const assert=require('node:assert/strict');
const close=(a,b)=>{if(typeof a==='number')assert.ok(Math.abs(a-b)<1e-9);else if(typeof a==='object')Object.keys(a).forEach(k=>close(a[k],b[k]));else assert.equal(a,b);};
for(const s of JSON.parse(process.argv[1])){close(jumpHeight(s.p,s.f),s.jump);close(walkSwing(s.p,s.f),s.swing);close(jointAngles(s.p,s.f),s.joints);close(weatherState(s.kind,s.f),s.weather);}
'''
        subprocess.run(['node','-e',js,json.dumps(samples)],check=True)
        for bow in [0,10,30]:
            actual=json.loads(subprocess.check_output(['node','-e',source+f'console.log(JSON.stringify(umbrellaPose({bow})))']))
            for a,b in zip(actual,umbrella_pose(bow)):self.assertAlmostEqual(a,b)

    def test_render_repeat_and_layering(self):
        backend=StickFigureBackend()
        for shot in self.e['shots']:
            a=backend.frame(self.e,shot,74);backend.frame(self.e,shot,149)
            self.assertEqual(a,backend.frame(self.e,shot,74))
            root=ET.fromstring(a);world=next(e for e in root if 'data-camera-world' in e.attrib)
            self.assertTrue(any('data-weather' in e.attrib for e in world))
            self.assertFalse(any('data-weather' in e.attrib for e in root))
            for actor in (e for e in world if 'data-actor' in e.attrib):
                prop=next(e for e in actor if 'data-held-prop' in e.attrib)
                self.assertEqual(prop.get('display')=='inline',holding(shot,actor.get('data-actor'),74))
