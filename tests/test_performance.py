import copy
import json
import tempfile
import unittest
from pathlib import Path
from dataclasses import replace
from claymanclub.validation import validate
from claymanclub.performance import active_performances, performance_boundaries
from claymanclub.pipeline import render_episode
from claymanclub.backends.stickfigure import StickFigureBackend

ROOT = Path(__file__).resolve().parents[1]

class PerformanceTests(unittest.TestCase):
    def setUp(self):
        self.episode = json.loads((ROOT/'examples/timed-performances.json').read_text())
        self.catalog = json.loads((ROOT/'examples/catalog.json').read_text())

    def test_boundaries_gaps_and_simultaneous_actors(self):
        shot = self.episode['shots'][0]
        shot['performances'].append(dict(shot['performances'][0], actor='pixel'))
        validate(self.episode, self.catalog)
        for frame, count in [(19,0),(20,2),(119,2),(120,1),(169,1),(170,0)]:
            self.assertEqual(len(active_performances(shot,'0.4',frame)),count)
        self.assertEqual(performance_boundaries(shot,'0.4'),[0,20,120,170])
        shot['performances'].reverse()
        validate(self.episode, self.catalog)  # list need not be chronological

    def test_reject_invalid_intervals_and_overlap(self):
        for start,end in [(True,120),(-1,120),(0,181),(20,20),(21,20),(0,1.5),(None,120)]:
            episode=copy.deepcopy(self.episode)
            episode['shots'][0]['performances'][0].update(start_frame=start,end_frame=end)
            with self.subTest(start=start,end=end), self.assertRaises(ValueError):
                validate(episode,self.catalog)
        self.episode['shots'][0]['performances'][1]['start_frame']=119
        with self.assertRaisesRegex(ValueError,'overlapping'):
            validate(self.episode,self.catalog)

    def test_missing_timing_and_legacy_rejection(self):
        del self.episode['shots'][0]['performances'][0]['end_frame']
        with self.assertRaisesRegex(ValueError,'interval'):
            validate(self.episode,self.catalog)
        for version in ('0.2','0.3'):
            episode=json.loads((ROOT/'tests/fixtures/episode-001-v02.json').read_text())
            episode['schema_version']=version
            validate(episode,self.catalog)
            episode['shots'][0]['performances'][0]['start_frame']=0
            with self.assertRaisesRegex(ValueError,'requires schema_version'):
                validate(episode,self.catalog)

    def test_capability_rejection_before_output(self):
        backend=StickFigureBackend()
        backend.capabilities=replace(backend.capabilities,timed_performances=False)
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'out'
            for render in (lambda:render_episode(self.episode,self.catalog,backend,target),
                           lambda:backend.render(self.episode,target)):
                with self.assertRaisesRegex(ValueError,'unsupported backend timed'):
                    render()
                self.assertFalse(target.exists())

    def test_snapshot_and_output_determinism(self):
        shot=self.episode['shots'][0]
        backend=StickFigureBackend()
        before=copy.deepcopy(self.episode)
        for frame,text in [(0,None),(20,'我的充电器'),(120,'等等'),(170,None)]:
            svg=backend.frame(self.episode,shot,frame)
            if text: self.assertIn(text,svg)
            else:
                self.assertNotIn('我的充电器',svg)
                self.assertNotIn('等等',svg)
        with tempfile.TemporaryDirectory() as d:
            for name in ('a','b'):
                render_episode(self.episode,self.catalog,backend,Path(d)/name)
            for p in (Path(d)/'a').iterdir():
                self.assertEqual(p.read_bytes(),(Path(d)/'b'/p.name).read_bytes())
        self.assertEqual(self.episode,before)
