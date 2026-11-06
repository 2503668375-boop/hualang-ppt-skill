"""Behavioral checks against a real export, using the available artifact runtime.

Set HUALANG_NODE and HUALANG_NODE_MODULES to the discovered Node executable and
module directory. No runtime paths or generated files are stored in the repo.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'artifact-template-hualang-school'
SCRIPTS = SKILL / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import audit_sequence
import check_style_contract


class ToolBehaviorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        node = os.environ.get('HUALANG_NODE')
        modules = os.environ.get('HUALANG_NODE_MODULES')
        if not node or not modules:
            raise unittest.SkipTest('Set HUALANG_NODE and HUALANG_NODE_MODULES for the native export test.')
        cls.temp = tempfile.TemporaryDirectory(prefix='hualang-tool-behavior-')
        cls.work = Path(cls.temp.name)
        shutil.copy2(SCRIPTS / 'hualang-kit.mjs', cls.work / 'hualang-kit.mjs')
        shutil.copy2(Path(__file__).with_name('tool-behavior-fixture.mjs'), cls.work / 'fixture.mjs')
        (cls.work / 'node_modules').symlink_to(Path(modules), target_is_directory=True)
        result = subprocess.run([node, str(cls.work / 'fixture.mjs'), str(SKILL), str(cls.work)],
                                text=True, capture_output=True)
        if result.returncode:
            raise AssertionError(result.stdout + '\n' + result.stderr)
        cls.pptx = cls.work / 'tool-behavior.pptx'
        cls.pure_pptx = cls.work / 'pure-shape.pptx'
        cls.contract = json.loads((SKILL / 'assets/style-contract.json').read_text())
        # Optional retained evidence stays outside the repository.
        retain = os.environ.get('HUALANG_TEST_OUTPUT')
        if retain:
            destination = Path(retain)
            destination.mkdir(parents=True, exist_ok=True)
            shutil.copy2(cls.pptx, destination / cls.pptx.name)
            shutil.copy2(cls.pure_pptx, destination / cls.pure_pptx.name)
            shutil.copy2(cls.work / 'fixture.json', destination / 'fixture.json')

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_saved_titles_accept_subject_and_english_headings(self):
        result = check_style_contract.check(self.pptx, self.contract,
                                            '工具行为验证', '示例教师', '2026年11月6日')
        self.assertTrue(result['ok'], result)
        self.assertEqual(len(result['headings']), 4)
        self.assertIn('先秦文化', [row['title'] for row in result['headings']])
        self.assertTrue(result['warnings'], 'Long Chinese terminology should request visual review.')

    def test_table_and_body_font_profiles_survive_export(self):
        expected_tables = [1800, 1725, 2175, 1950]  # OOXML hundredths of a point.
        expected_bodies = [2100, 1875, 2325, 1875]
        with zipfile.ZipFile(self.pptx) as archive:
            parts = check_style_contract.slide_parts(archive)
            for index, part in enumerate(parts[1:-1]):
                slide = ET.fromstring(archive.read(part))
                table = slide.find('.//a:tbl', check_style_contract.NS)
                table_sizes = {int(n.get('sz')) for n in table.findall('.//a:rPr', check_style_contract.NS)
                               if n.get('sz') is not None}
                self.assertEqual(table_sizes, {expected_tables[index]})
                bodies = []
                for shape in slide.findall('.//p:sp', check_style_contract.NS):
                    name = shape.find('p:nvSpPr/p:cNvPr', check_style_contract.NS)
                    if name is not None and name.get('name') == 'fixture-body':
                        bodies.extend(int(n.get('sz')) for n in shape.findall('.//a:rPr', check_style_contract.NS)
                                      if n.get('sz') is not None)
                self.assertEqual(set(bodies), {expected_bodies[index]})

    def test_one_direct_logo_and_gold_rule_with_no_inherited_duplicates(self):
        logo_sha = hashlib.sha256((SKILL / 'assets/logo-horizontal.png').read_bytes()).hexdigest()
        ns = check_style_contract.NS

        def counts(archive, part):
            root = ET.fromstring(archive.read(part))
            rels = check_style_contract.relationships(archive, part)
            images = {rid:target for rid,kind,target in rels if kind == 'image'}
            logos = 0
            for blip in root.findall('.//a:blip', ns):
                target = images.get(blip.get('{'+ns['r']+'}embed'))
                if target and hashlib.sha256(archive.read(target)).hexdigest() == logo_sha:
                    logos += 1
            rules = 0
            for shape in root.findall('.//p:sp', ns):
                color = shape.find('p:spPr/a:ln/a:solidFill/a:srgbClr', ns)
                transform = shape.find('p:spPr/a:xfrm', ns)
                position = None
                if transform is not None:
                    offset, extent = transform.find('a:off', ns), transform.find('a:ext', ns)
                    if offset is not None and extent is not None:
                        position = [int(v)/check_style_contract.EMU for v in
                                    (offset.get('x'),offset.get('y'),extent.get('cx'),extent.get('cy'))]
                if color is not None and color.get('val','').upper() == 'BCA36D' and position:
                    if all(abs(a-b)<1 for a,b in zip(position,[48,86,1184,0])):
                        rules += 1
            return logos, rules, rels

        for fixture in (self.pptx, self.pure_pptx):
            with zipfile.ZipFile(fixture) as archive:
                for part in check_style_contract.slide_parts(archive)[1:-1]:
                    direct_logos, direct_rules, rels = counts(archive, part)
                    self.assertEqual((direct_logos,direct_rules), (1,1), (fixture.name,part))
                    inherited_logos = inherited_rules = 0
                    queue = [target for _,kind,target in rels if kind in ('slideLayout','slideMaster')]
                    visited = set()
                    while queue:
                        target = queue.pop()
                        if target in visited:
                            continue
                        visited.add(target)
                        logos, rules, links = counts(archive, target)
                        inherited_logos += logos
                        inherited_rules += rules
                        # A master lists all sibling layouts as relationships;
                        # only the owning layout -> master chain is inherited.
                        queue.extend(t for _,kind,t in links if kind == 'slideMaster')
                    self.assertEqual((inherited_logos,inherited_rules),(0,0),(fixture.name,part))

    def manifest(self, explain=False):
        rows = [{'slide':i, 'family':'same-object', 'lesson':'one', 'minutes':3}
                for i in range(2,6)]
        if explain:
            for row in rows[1:]:
                row['continuationReason'] = '同一材料的分阶段证据比较，保持对象位置。'
        return {'slides':rows}

    def test_continuous_reasoning_is_not_a_structural_failure(self):
        result = audit_sequence.audit(self.pptx, self.manifest(explain=True))
        self.assertTrue(result['ok'], result)
        self.assertFalse(result['errors'])
        self.assertEqual(result['planned_minutes_by_lesson'], {'one':12})

    def test_unexplained_repetition_requires_review_without_forcing_relayout(self):
        result = audit_sequence.audit(self.pptx, self.manifest())
        self.assertTrue(result['ok'], result)
        self.assertTrue(result['warnings'])

    def test_abab_repetition_is_a_review_warning(self):
        manifest = self.manifest()
        for row, family in zip(manifest['slides'], ['material','analysis','material','analysis']):
            row['family'] = family
        result = audit_sequence.audit(self.pptx, manifest)
        self.assertTrue(result['ok'], result)
        self.assertTrue(any('ABAB' in item for item in result['warnings']))

    def test_duplicate_manifest_page_fails(self):
        manifest = self.manifest()
        manifest['slides'].append(dict(manifest['slides'][0]))
        result = audit_sequence.audit(self.pptx, manifest)
        self.assertFalse(result['ok'])
        self.assertTrue(result['errors'])

    def test_missing_manifest_page_fails(self):
        manifest = self.manifest()
        manifest['slides'].pop()
        result = audit_sequence.audit(self.pptx, manifest)
        self.assertFalse(result['ok'])
        self.assertTrue(result['errors'])


if __name__ == '__main__':
    unittest.main()
