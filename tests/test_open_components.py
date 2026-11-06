"""Check new open components against an actual saved native export.

Use HUALANG_NODE and HUALANG_NODE_MODULES from runtime discovery. Missing
runtime explicitly skips this class; no machine paths or generated files enter
this repository. All fixture values are simulated.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as E
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT/'artifact-template-hualang-school'
SCRIPTS = SKILL/'scripts'
sys.path.insert(0, str(SCRIPTS))
from check_style_contract import EMU, NS, slide_parts


class OpenComponentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        node = os.environ.get('HUALANG_NODE')
        modules = os.environ.get('HUALANG_NODE_MODULES')
        if not node or not modules:
            raise unittest.SkipTest('Set HUALANG_NODE and HUALANG_NODE_MODULES for the native export test.')
        cls.temp = tempfile.TemporaryDirectory(prefix='hualang-open-components-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.work = Path(cls.temp.name)
        shutil.copy2(SCRIPTS/'hualang-kit.mjs', cls.work/'hualang-kit.mjs')
        shutil.copy2(Path(__file__).with_name('open-components-fixture.mjs'), cls.work/'fixture.mjs')
        (cls.work/'node_modules').symlink_to(Path(modules), target_is_directory=True)
        result = subprocess.run([node, str(cls.work/'fixture.mjs'), str(SKILL), str(cls.work)],
                                text=True, capture_output=True, timeout=120)
        if result.returncode:
            raise AssertionError(result.stdout+'\n'+result.stderr)
        cls.pptx = cls.work/'open-components.pptx'
        cls.metadata = json.loads((cls.work/'open-components.json').read_text())
        cls.objects = []
        with zipfile.ZipFile(cls.pptx) as archive:
            for page, part in enumerate(slide_parts(archive), 1):
                root = E.fromstring(archive.read(part))
                for shape in root.findall('.//p:sp', NS):
                    name = shape.find('p:nvSpPr/p:cNvPr', NS)
                    name = name.get('name', '') if name is not None else ''
                    if not name.startswith('fixture-'):
                        continue
                    prop = shape.find('p:spPr', NS)
                    transform = prop.find('a:xfrm', NS)
                    off, extent = transform.find('a:off', NS), transform.find('a:ext', NS)
                    box = [int(value)/EMU for value in
                           (off.get('x'),off.get('y'),extent.get('cx'),extent.get('cy'))]
                    geometry = prop.find('a:prstGeom', NS)
                    cls.objects.append({'page':page, 'name':name, 'box':box,
                                        'text':''.join(n.text or '' for n in shape.findall('.//a:t', NS)),
                                        'geometry':geometry.get('prst') if geometry is not None else 'custom',
                                        'prop':prop})
        retain = os.environ.get('HUALANG_TEST_OUTPUT')
        if retain:
            destination = Path(retain)
            destination.mkdir(parents=True, exist_ok=True)
            for name in ('open-components.pptx', 'open-components.json'):
                shutil.copy2(cls.work/name, destination/name)

    def selected(self, prefix, geometry=None):
        return [obj for obj in self.objects if obj['name'].startswith(prefix)
                and (geometry is None or obj['geometry'] == geometry)]

    def endpoints(self, obj):
        path = obj['prop'].find('a:custGeom/a:pathLst/a:path', NS)
        self.assertIsNotNone(path)
        width, height = int(path.get('w')), int(path.get('h'))
        x, y, w, h = obj['box']
        return [(x+int(point.get('x'))/width*w, y+int(point.get('y'))/height*h)
                for point in path.findall('.//a:pt', NS)]

    def assertPoint(self, actual, expected):
        self.assertEqual(len(actual), len(expected))
        for a, b in zip(actual, expected):
            self.assertAlmostEqual(a, b, places=3)

    def test_metric_exports_only_editable_text_without_background(self):
        objects = self.selected('fixture-metric-')
        self.assertEqual(len(objects), 3)
        self.assertEqual({obj['text'] for obj in objects}, {'36 项', '课程完成', '模拟数字'})
        for obj in objects:
            self.assertIsNotNone(obj['prop'].find('a:noFill', NS))
            self.assertIsNone(obj['prop'].find('a:solidFill', NS))
            self.assertTrue(obj['text'])

    def test_dot_coordinates_share_numeric_domain_and_keep_signed_differences(self):
        points = self.selected('fixture-dot-', 'ellipse')
        centers = sorted((obj['box'][0]+obj['box'][2]/2, obj['box'][1]+obj['box'][3]/2) for obj in points)
        expected = [(240,302.25),(430,414.75),(620,414.75),(1000,302.25)]
        self.assertEqual(len(centers), 4)
        for actual, want in zip(centers, expected):
            self.assertPoint(actual, want)
        texts = {obj['text'] for obj in self.selected('fixture-dot-')}
        self.assertTrue({'+40','-10','差额'}.issubset(texts))
        self.assertAlmostEqual((centers[1][0]-240)/(1000-240), .25)
        self.assertAlmostEqual((centers[2][0]-240)/(1000-240), .5)

    def test_timeline_uses_elapsed_date_proportions(self):
        points = self.selected('fixture-timeline-', 'ellipse')
        centers = sorted((obj['box'][0]+obj['box'][2]/2, obj['box'][1]+obj['box'][3]/2) for obj in points)
        for actual, want in zip(centers, [(130,341),(318,341),(1070,341)]):
            self.assertPoint(actual, want)
        self.assertEqual(len(centers), 3)
        self.assertAlmostEqual((centers[1][0]-centers[0][0])/(centers[2][0]-centers[0][0]), 2/10)

    def test_timeline_leaders_follow_actual_label_side_and_avoid_text(self):
        leaders = sorted(self.selected('fixture-timeline-', 'custom'), key=lambda obj: obj['box'][0])
        expected = [[(130,384),(130,422)], [(318,333),(318,313)], [(1070,333),(1070,242)]]
        self.assertEqual(len(leaders), 3)
        for leader, pair in zip(leaders, expected):
            ends = self.endpoints(leader)
            self.assertEqual(len(ends), 2)
            for actual, want in zip(ends, pair):
                self.assertPoint(actual, want)

    def test_evidence_leaders_stop_outside_all_four_text_edges(self):
        expected = {'above':[(400,100),(400,292)], 'below':[(400,550),(400,408)],
                    'left':[(100,350),(290,350)], 'right':[(700,350),(510,350)]}
        for side, want in expected.items():
            with self.subTest(side=side):
                leaders = self.selected('fixture-note-'+side+'-', 'custom')
                self.assertEqual(len(leaders), 1)
                ends = self.endpoints(leaders[0])
                for actual, point in zip(ends, want):
                    self.assertPoint(actual, point)

    def test_report_content_area_expands_and_legacy_areas_remain(self):
        areas = self.metadata['areas']
        self.assertEqual(areas['withoutSummary']['content'], {'x':48,'y':108,'w':1184,'h':544})
        self.assertEqual(areas['withSummary']['content'], {'x':48,'y':196,'w':1184,'h':456})
        for group in areas.values():
            self.assertEqual(group['evidence'], {'x':48,'y':196,'w':1184,'h':356})
            self.assertEqual(group['note'], {'x':48,'y':572,'w':1184,'h':80})
        self.assertEqual(self.metadata['slideCount'], 11)

    def assertRejected(self, prefix, expected_count):
        results = {name: result for name, result in self.metadata['rejected'].items() if name.startswith(prefix)}
        self.assertEqual(len(results), expected_count)
        self.assertTrue(all(results.values()), results)

    def test_invalid_numeric_domains_values_and_capacity_are_rejected(self):
        self.assertRejected('dot-', 5)

    def test_invalid_dates_domains_and_empty_events_are_rejected(self):
        self.assertRejected('timeline-', 5)

    def test_internal_and_nonfinite_note_anchors_are_rejected(self):
        self.assertRejected('note-', 2)


if __name__ == '__main__':
    unittest.main()
