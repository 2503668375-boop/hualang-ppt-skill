"""Check native text roles, usable content space and saved chart data.

These are export/geometry checks, not aesthetic scores. Supply the discovered
HUALANG_NODE and HUALANG_NODE_MODULES; an absent runtime is explicitly skipped.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'artifact-template-hualang-school'
NS = {
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart',
}


class TextRoleExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        node = os.environ.get('HUALANG_NODE')
        modules = os.environ.get('HUALANG_NODE_MODULES')
        if not node or not modules:
            raise unittest.SkipTest('Set discovered HUALANG_NODE and HUALANG_NODE_MODULES.')
        if not Path(node).is_file() or not (Path(modules) / '@oai/artifact-tool').is_dir():
            raise unittest.SkipTest('The supplied native export runtime is unavailable.')
        cls.temp = tempfile.TemporaryDirectory(prefix='hualang-v10-text-roles-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.work = Path(cls.temp.name)
        shutil.copy2(SKILL / 'scripts/hualang-kit.mjs', cls.work / 'hualang-kit.mjs')
        shutil.copy2(Path(__file__).with_name('v10-text-roles-fixture.mjs'), cls.work / 'fixture.mjs')
        (cls.work / 'node_modules').symlink_to(Path(modules), target_is_directory=True)
        run = subprocess.run([node, str(cls.work / 'fixture.mjs'), str(SKILL), str(cls.work)],
                             capture_output=True, text=True, timeout=180)
        if run.returncode:
            raise AssertionError(run.stdout + '\n' + run.stderr)
        cls.result = json.loads((cls.work / 'result.json').read_text())
        with zipfile.ZipFile(cls.work / 'v10-text-roles.pptx') as archive:
            cls.slides = [ET.fromstring(archive.read(f'ppt/slides/slide{n}.xml')) for n in (2, 3, 4, 5)]
            cls.charts = [ET.fromstring(archive.read(n)) for n in archive.namelist()
                          if n.endswith('.xml') and '/charts/' in n and '/_rels/' not in n]
        retain = os.environ.get('HUALANG_TEST_OUTPUT')
        if retain:
            dest = Path(retain) / 'v10-text-roles'
            shutil.copytree(cls.work, dest, ignore=shutil.ignore_patterns('node_modules'), dirs_exist_ok=True)
            def relocate(value):
                if isinstance(value, dict):
                    return {k: relocate(v) for k, v in value.items()}
                if isinstance(value, list):
                    return [relocate(v) for v in value]
                if isinstance(value, str) and value.startswith(str(cls.work) + os.sep):
                    return str(dest / value[len(str(cls.work)) + 1:])
                return value
            for record in [dest / 'result.json', *dest.rglob('render-manifest.json')]:
                record.write_text(json.dumps(relocate(json.loads(record.read_text())), ensure_ascii=False, indent=2))

    def named(self, index, name):
        matches = [shape for shape in self.slides[index].findall('.//p:sp', NS)
                   if shape.find('p:nvSpPr/p:cNvPr', NS).get('name') == name]
        self.assertEqual(len(matches), 1, (index, name))
        return matches[0]

    @staticmethod
    def box(shape):
        transform = shape.find('p:spPr/a:xfrm', NS)
        offset, extent = transform.find('a:off', NS), transform.find('a:ext', NS)
        return tuple(int(v) / 9525 for v in
                     (offset.get('x'), offset.get('y'), extent.get('cx'), extent.get('cy')))

    @staticmethod
    def styles(shape):
        return shape.findall('.//a:rPr', NS)

    def test_core_lead_and_context_are_distinct_saved_text_roles(self):
        lead = self.styles(self.named(0, 'lead'))
        context = self.styles(self.named(0, 'context'))
        body = self.styles(self.named(0, 'fixture-body'))
        self.assertTrue(lead and context and body)
        self.assertTrue(all(style.get('b') == '1' for style in lead))
        self.assertTrue(all(style.find('a:solidFill/a:srgbClr', NS).get('val') == '222222' for style in lead))
        self.assertTrue(all(style.find('a:solidFill/a:srgbClr', NS).get('val') == '666666' for style in context))
        self.assertEqual({int(style.get('sz')) for style in context}, {19 * 75})
        self.assertGreater(min(int(style.get('sz')) for style in lead),
                           max(int(style.get('sz')) for style in body))

    def test_two_line_lead_moves_usable_content_below_the_actual_box(self):
        areas = self.result['areas']
        self.assertGreater(areas['multiline']['area']['y'], areas['single']['area']['y'])
        self.assertGreater(areas['single']['area']['y'], areas['withoutLead']['area']['y'])
        for index, key in enumerate(('single', 'multiline', 'legacy')):
            area = areas[key]['area']
            lead_box = self.box(self.named(index, 'summary' if key == 'legacy' else 'lead'))
            context_box = self.box(self.named(index, 'context'))
            body_box = self.box(self.named(index, 'fixture-body'))
            self.assertLess(lead_box[1] + lead_box[3], context_box[1])
            self.assertLess(context_box[1] + context_box[3], body_box[1])
            self.assertAlmostEqual(context_box[1], area['y'])
            self.assertLessEqual(body_box[1] + body_box[3], area['y'] + area['h'])
        double = self.named(1, 'lead')
        line_count = len(double.findall('p:txBody/a:p', NS))
        self.assertEqual(line_count, 2)
        size_px = max(int(s.get('sz')) / 75 for s in self.styles(double))
        self.assertGreaterEqual(self.box(double)[3], line_count * size_px * 1.2)

    def test_legacy_summary_keeps_lead_hierarchy_and_exposes_the_same_content_area(self):
        self.assertEqual(self.result['areas']['legacy']['area'],
                         self.result['areas']['legacy']['queriedArea'])
        lead, summary = self.styles(self.named(0, 'lead')), self.styles(self.named(2, 'summary'))
        self.assertEqual({int(s.get('sz')) for s in summary}, {int(s.get('sz')) for s in lead})
        self.assertTrue(all(s.get('b') == '1' for s in summary))
        self.assertTrue(all(s.find('a:solidFill/a:srgbClr', NS).get('val') == '222222' for s in summary))

    def test_chart_categories_and_values_match_after_save_and_reload(self):
        expected = [('B场', 119.05), ('A场', 125.0)]
        self.assertEqual(len(self.charts), 1)
        series = self.charts[0].findall('.//c:ser', NS)
        self.assertEqual(len(series), 1)
        categories = [n.text for n in series[0].findall('c:cat//c:pt/c:v', NS)]
        values = [float(n.text) for n in series[0].findall('c:val//c:pt/c:v', NS)]
        self.assertEqual(list(zip(categories, values)), expected)
        saved = self.result['chartAfterReload']
        # Imports may normalize category data into the native series only.
        if saved['categories']:
            self.assertEqual(saved['categories'], saved['seriesCategories'])
        self.assertEqual(list(zip(saved['seriesCategories'], saved['values'])), expected)


if __name__ == '__main__':
    unittest.main()
