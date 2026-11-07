"""Review decisions use file evidence and unresolved findings, not a score."""
import base64
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as E
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT/'artifact-template-hualang-school'/'scripts'
sys.path.insert(0, str(SCRIPTS))
import review_gate as gate

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aOLsAAAAASUVORK5CYII=')
PKG = 'http://schemas.openxmlformats.org/package/2006/relationships'


class ReviewGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hualang-review-')
        self.directory = Path(self.temp.name)
        self.deck = self.directory/'deck.pptx'
        presentation = E.Element('{'+gate.P+'}presentation')
        ids = E.SubElement(presentation, '{'+gate.P+'}sldIdLst')
        relations = E.Element('{'+PKG+'}Relationships')
        with zipfile.ZipFile(self.deck, 'w') as archive:
            for number in (1, 2):
                E.SubElement(ids, '{'+gate.P+'}sldId', {'id': str(255+number),
                             '{'+gate.R+'}id': 'rId'+str(number)})
                E.SubElement(relations, '{'+PKG+'}Relationship', {
                    'Id': 'rId'+str(number), 'Type': gate.R+'/slide',
                    'Target': 'slides/slide'+str(number)+'.xml'})
                slide = E.Element('{'+gate.P+'}sld')
                E.SubElement(E.SubElement(slide, '{'+gate.P+'}cSld'), '{'+gate.P+'}spTree')
                archive.writestr('ppt/slides/slide'+str(number)+'.xml', E.tostring(slide))
            archive.writestr('ppt/presentation.xml', E.tostring(presentation))
            archive.writestr('ppt/_rels/presentation.xml.rels', E.tostring(relations))
        self.images = [self.directory/'page-1.png', self.directory/'page-2.png']
        for image in self.images:
            image.write_bytes(PNG)
        self.record = {
            'schemaVersion': 1,
            'artifact': {'path': 'deck.pptx', 'sha256': gate.digest(self.deck)},
            'renderSourceSha256': gate.digest(self.deck),
            'renderEvidence': {'kind': 'saved_file_render', 'engine': 'test renderer',
                               'entryPoint': 'import final deck.pptx and export page PNGs'},
            'pages': [{'slide': number, 'render': image.name,
                       'renderSha256': gate.digest(image), 'scene': 'report',
                       'subject': subject, 'verdict': 'pass'}
                      for number, image, subject in zip((1, 2), self.images, ('共同数轴比较', '资源投入及条件'))],
            'gates': {area: {'verdict': 'pass', 'evidence': [
                {'slides': [1, 2], 'observation': '第1页对照目标差额，第2页将费用与时间分别读取。'}]}
                for area in gate.AREAS},
            'issues': []}
        self.review = self.directory/'review.json'

    def tearDown(self):
        self.temp.cleanup()

    def run_record(self, record=None):
        self.review.write_text(json.dumps(self.record if record is None else record), encoding='utf-8')
        return gate.check(self.review)

    def assert_returns(self, record=None):
        outcome = self.run_record(record)
        self.assertEqual(outcome['decision'], 'return_for_revision')
        self.assertTrue(outcome['errors'])
        return outcome

    def issue(self, **updates):
        value = {'id': 'V1', 'slide': 2, 'area': 'visual',
                 'problem': '正文越过底框', 'status': 'open'}
        value.update(updates)
        self.record['issues'] = [value]

    def test_current_full_review_is_ready_only_for_human_signoff(self):
        outcome = self.run_record()
        self.assertEqual(outcome['decision'], 'ready_for_human_signoff')
        self.assertTrue(outcome['coversWholeDeck'])
        self.assertEqual(outcome['slideCount'], 2)
        self.assertEqual(outcome['errors'], [])

    def test_content_failure_is_not_offset_by_file_success(self):
        self.record['gates']['content']['verdict'] = 'revise'
        self.assert_returns()
        self.assertEqual(self.record['gates']['file']['verdict'], 'pass')

    def test_structural_mirror_cannot_claim_final_page_review(self):
        self.record['renderEvidence']['kind'] = 'structural_mirror'
        outcome = self.assert_returns()
        self.assertEqual(outcome['renderEvidenceKind'], 'structural_mirror')
        self.assertTrue(any('结构镜像' in e for e in outcome['errors']))

    def test_legacy_unknown_and_missing_render_provenance_require_declaration(self):
        for evidence in (None, {}, {'kind': 'unknown'}, {'kind': 'not-a-kind'}):
            with self.subTest(evidence=evidence):
                self.record['renderEvidence'] = evidence
                self.assert_returns()

    def test_real_render_requires_engine_and_final_file_entry_point(self):
        original = copy.deepcopy(self.record['renderEvidence'])
        for key in ('engine', 'entryPoint'):
            self.record['renderEvidence'] = copy.deepcopy(original)
            self.record['renderEvidence'][key] = ' '
            self.assert_returns()

    def test_application_export_is_valid_evidence_without_claiming_playback(self):
        self.record['renderEvidence'] = {'kind': 'application_export',
                                        'engine': 'presentation application',
                                        'entryPoint': 'open final deck.pptx and export PDF, then rasterize'}
        outcome = self.run_record()
        self.assertEqual(outcome['decision'], 'ready_for_human_signoff')
        self.assertEqual(outcome['renderEvidenceKind'], 'application_export')

    def test_open_problem_overrides_all_pass_verdicts(self):
        self.issue()
        self.assert_returns()

    def test_fixed_problem_needs_resolution_and_current_render(self):
        self.issue(status='fixed')
        self.assert_returns()
        self.record['issues'][0]['resolution'] = '缩短复述并重新分配正文区域'
        self.record['issues'][0]['checkedRenderSha256'] = '0'*64
        self.assert_returns()
        self.record['issues'][0]['checkedRenderSha256'] = gate.digest(self.images[1])
        self.assertEqual(self.run_record()['decision'], 'ready_for_human_signoff')

    def test_fixed_problem_cannot_use_hash_of_an_old_image(self):
        self.issue(status='fixed', resolution='重新排版',
                   checkedRenderSha256=gate.digest(self.images[1]))
        self.images[1].write_bytes(PNG+b'changed render')
        self.record['pages'][1]['renderSha256'] = gate.digest(self.images[1])
        self.assert_returns()

    def test_missing_and_duplicate_page_records_return(self):
        original = copy.deepcopy(self.record['pages'])
        self.record['pages'].pop()
        self.assert_returns()
        self.record['pages'] = original+[copy.deepcopy(original[0])]
        self.assert_returns()

    def test_file_change_requires_new_deck_and_render_source_hashes(self):
        with zipfile.ZipFile(self.deck, 'a') as archive:
            archive.comment = b'a revised saved artifact'
        self.assert_returns()
        self.record['artifact']['sha256'] = gate.digest(self.deck)
        self.assert_returns()
        self.record['renderSourceSha256'] = gate.digest(self.deck)
        self.assertEqual(self.run_record()['decision'], 'ready_for_human_signoff')

    def test_missing_wrong_format_and_stale_render_files_return(self):
        self.images[0].unlink()
        self.assert_returns()
        self.images[0].write_bytes(b'not an image')
        self.record['pages'][0]['renderSha256'] = gate.digest(self.images[0])
        self.assert_returns()
        self.images[0].write_bytes(PNG)
        self.assert_returns()

    def test_unverified_page_and_missing_observation_return(self):
        self.record['pages'][0]['verdict'] = 'unverified'
        self.assert_returns()
        self.record['pages'][0]['verdict'] = 'pass'
        self.record['gates']['visual']['evidence'] = []
        self.assert_returns()

    def test_full_review_cannot_mark_a_required_gate_not_applicable(self):
        self.record['gates']['expression']['verdict'] = 'not_applicable'
        self.assert_returns()

    def test_partial_review_has_explicit_scope_and_requires_observation(self):
        self.record['scope'] = [2]
        self.record['pages'] = self.record['pages'][1:]
        for value in self.record['gates'].values():
            value['evidence'][0]['slides'] = [2]
        self.record['gates']['expression']['verdict'] = 'not_applicable'
        self.record['gates']['expression']['evidence'][0]['observation'] = '仅修改第2页字距，主体及阅读路径未变化。'
        outcome = self.run_record()
        self.assertEqual(outcome['decision'], 'ready_for_human_signoff')
        self.assertFalse(outcome['coversWholeDeck'])
        self.assertEqual(outcome['scope'], [2])
        self.record['gates']['expression']['evidence'] = []
        self.assert_returns()

    def test_invalid_scope_and_out_of_scope_evidence_return(self):
        for scope in ([], [3], [True], [1, 1, 2]):
            with self.subTest(scope=scope):
                self.record['scope'] = scope
                self.assert_returns()
        self.record['scope'] = [1, 2]
        self.record['gates']['content']['evidence'][0]['slides'] = [3]
        self.assert_returns()

    def test_malformed_values_return_instead_of_crashing(self):
        self.record['schemaVersion'] = True
        self.assert_returns()
        self.record['schemaVersion'] = 1
        self.record['gates']['visual']['verdict'] = ['pass']
        self.assert_returns()
        self.assert_returns(['not', 'a', 'review'])

    def test_actual_slide_part_must_exist(self):
        replacement = self.directory/'broken.pptx'
        with zipfile.ZipFile(self.deck) as source, zipfile.ZipFile(replacement, 'w') as out:
            for name in source.namelist():
                if name != 'ppt/slides/slide2.xml':
                    out.writestr(name, source.read(name))
        self.record['artifact'] = {'path': replacement.name, 'sha256': gate.digest(replacement)}
        self.record['renderSourceSha256'] = gate.digest(replacement)
        self.assert_returns()

    def test_cli_writes_result_and_refuses_to_overwrite_review_input(self):
        self.run_record()
        out = self.directory/'results'/'gate.json'
        command = [sys.executable, str(SCRIPTS/'review_gate.py'), str(self.review)]
        run = subprocess.run(command+['--output', str(out)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(out.read_text())['decision'], 'ready_for_human_signoff')
        before = self.review.read_bytes()
        run = subprocess.run(command+['--output', str(self.review)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertEqual(self.review.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
