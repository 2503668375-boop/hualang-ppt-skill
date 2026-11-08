"""Behavior checks for V11 export: preserve input, signed data and usable space."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'artifact-template-hualang-school'
sys.path.insert(0, str(SKILL / 'scripts'))
try:
    from pptx import Presentation
    from hualang_build import build_deck
except ImportError as exc:
    raise unittest.SkipTest('python-pptx and Pillow are required for builder checks') from exc


class BuilderExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hualang-v11-builder-')
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def build(self, slide, scenario='internal_report', name='output'):
        path = self.directory / (name + '.pptx')
        report = build_deck({'title': '生成验证', 'scenario': scenario,
                             'content_only': True, 'slides': [slide]}, path)
        return Presentation(path), report, path

    @staticmethod
    def text(prs):
        return '\n'.join(shape.text for slide in prs.slides
                         for shape in slide.shapes if shape.has_text_frame)

    def test_unsupported_capacity_is_rejected_without_silent_data_loss(self):
        cases = [
            {'layout': 'statement', 'items': [{'title': str(i)} for i in range(4)]},
            {'layout': 'metrics', 'metrics': [{'value': i, 'label': str(i)} for i in range(5)]},
            {'layout': 'bars', 'series': [{'value': i, 'label': str(i)} for i in range(8)]},
            {'layout': 'evidence', 'items': [{'title': str(i)} for i in range(5)]},
            {'layout': 'lesson', 'task': '任务', 'prompts': ['提示'] * 5},
            {'layout': 'lesson', 'task': '任务', 'feedback_items': [{'body': str(i)} for i in range(4)]},
            {'layout': 'comparison', 'left': {'items': ['说明'] * 4}},
        ]
        for i, case in enumerate(cases):
            with self.subTest(layout=case['layout'], case=i):
                case['title'] = '容量验证'
                with self.assertRaisesRegex(ValueError, '第 1 页.*续页'):
                    self.build(case, name=str(i))
                self.assertFalse((self.directory / (str(i) + '.pptx')).exists())

    def test_full_bleed_cannot_silently_drop_observation_items(self):
        with self.assertRaisesRegex(ValueError, '第 1 页.*items.*续页'):
            self.build({'layout': 'statement', 'title': '公开展示',
                        'items': [{'title': '必须保留', 'body': '观察内容'}]},
                       scenario='admissions')

    def test_read_and_near_image_layouts_retain_supplied_image(self):
        for tier in ('read', 'near'):
            with self.subTest(tier=tier):
                prs, _, _ = self.build({'layout': 'image', 'title': '真实校园',
                                        'tier': tier, 'image': 'assets/campus.jpg',
                                        'body': '观察到的真实场景'}, name=tier)
                pictures = [shape for slide in prs.slides for shape in slide.shapes
                            if shape.name == 'evidence-image']
                self.assertEqual(len(pictures), 1)
                self.assertEqual(pictures[0].image.blob, (SKILL / 'assets/campus.jpg').read_bytes())
                self.assertIn('观察到的真实场景', self.text(prs))

    def test_signed_or_invalid_values_do_not_become_positive_bars(self):
        for i, value in enumerate((-5, float('nan'), float('inf'), True, '5')):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, '第 1 页'):
                    self.build({'layout': 'bars', 'title': '带符号比较',
                                'series': [{'label': '待比较值', 'value': value}]}, name=str(i))

    def test_explicit_scale_cannot_clip_or_invert_bars(self):
        for i, maximum in enumerate((0, -10, 4, float('inf'))):
            with self.subTest(maximum=maximum):
                with self.assertRaisesRegex(ValueError, 'max_value'):
                    self.build({'layout': 'bars', 'title': '共同尺度', 'max_value': maximum,
                                'series': [{'label': '项目', 'value': 5}]}, name=str(i))

    def test_four_short_evidence_items_remain_visible_inside_content_area(self):
        prs, _, _ = self.build({'layout': 'evidence', 'title': '观察证据',
                                'items': [{'title': f'观察{i}', 'body': f'证据{i}'} for i in range(4)]})
        for i in range(4):
            self.assertIn(f'观察{i}', self.text(prs))
            self.assertIn(f'证据{i}', self.text(prs))
        observations = [s for s in prs.slides[0].shapes if s.has_text_frame
                        and s.text.startswith(('观察', '证据')) and s.name != 'title']
        self.assertTrue(observations)
        self.assertTrue(all(s.top + s.height <= 620 * 9525 for s in observations))

    def test_long_evidence_is_rejected_instead_of_covering_action_or_footer(self):
        with self.assertRaisesRegex(ValueError, '观察证据.*拆分'):
            self.build({'layout': 'evidence', 'title': '观察证据', 'action': '换文复核',
                        'items': [{'title': '观察', 'body': '需要保留的完整证据' * 80}]})

    def test_four_short_prompts_and_independent_task_do_not_overlap(self):
        prs, _, _ = self.build({'layout': 'lesson', 'title': '课堂观察', 'task': '完成任务',
                                'work': '完整材料', 'prompts': [f'提示{i}' for i in range(4)],
                                'independent_task': '独立写理由', 'answer': '反馈内容'},
                               scenario='classroom')
        self.assertEqual(len(prs.slides), 2)
        first = '\n'.join(s.text for s in prs.slides[0].shapes if s.has_text_frame)
        second = '\n'.join(s.text for s in prs.slides[1].shapes if s.has_text_frame)
        self.assertIn('独立写理由', first)
        self.assertNotIn('反馈内容', first)
        self.assertIn('反馈内容', second)
        for s in prs.slides[0].shapes:
            if s.has_text_frame and s.text.startswith('提示'):
                self.assertLessEqual(s.top + s.height, 582 * 9525)

    def test_parent_feedback_continues_without_hiding_observations_under_action(self):
        spec = json.loads((SKILL / 'assets/examples/parent-growth.json').read_text())
        path = self.directory / 'parent.pptx'
        report = build_deck(spec, path)
        prs = Presentation(path)
        self.assertGreater(report['page_plan'][0]['generated_pages'], 1)
        exported = self.text(prs)
        for item in spec['slides'][0]['items']:
            self.assertIn(item['title'], exported)
            self.assertIn(item['body'], exported)
        self.assertEqual(exported.count(spec['slides'][0]['action']), 1)

    def test_multiline_stage_claim_keeps_body_and_context_below_complete_lead(self):
        spec = json.loads((SKILL / 'assets/examples/public-address.json').read_text())
        path = self.directory / 'public.pptx'
        build_deck(spec, path)
        prs = Presentation(path)
        for slide in (prs.slides[1], prs.slides[3]):
            named = {shape.name: shape for shape in slide.shapes}
            lead, body, context = [named['statement-' + part] for part in ('lead', 'body', 'context')]
            self.assertLess(lead.top + lead.height, body.top)
            self.assertLess(body.top + body.height, context.top)
            self.assertLessEqual(context.top + context.height, 650 * 9525)
            for box in (lead, body, context):
                for paragraph in box.text_frame.paragraphs:
                    self.assertNotIsInstance(paragraph.line_spacing, float)
        with self.assertRaisesRegex(ValueError, '主视觉页.*续页'):
            self.build({'layout': 'statement', 'title': '完整主张', 'lead': '完整主张' * 80,
                        'body': '说明', 'context': '资料范围'}, scenario='public_address')

    def test_complete_classroom_text_ends_above_independent_task_band(self):
        spec = json.loads((SKILL / 'assets/examples/classroom.json').read_text())
        path = self.directory / 'classroom.pptx'
        build_deck(spec, path)
        prs = Presentation(path)
        work = next(shape for shape in prs.slides[1].shapes if shape.name == 'lesson-work')
        self.assertEqual(work.text, spec['slides'][0]['work'])
        self.assertIn('任务：林远给你留下了怎样的印象？', work.text)
        self.assertLessEqual(work.top + work.height, 582 * 9525)
        for paragraph in work.text_frame.paragraphs:
            self.assertNotIsInstance(paragraph.line_spacing, float)
        with self.assertRaisesRegex(ValueError, '完整学习对象.*续页'):
            self.build({'layout': 'lesson', 'title': '学习对象', 'task': '阅读并作答',
                        'work': '必须保留的原文' * 200, 'independent_task': '独立说明'},
                       scenario='classroom')

    def test_read_process_reveal_is_written_to_final_pptx(self):
        _, report, path = self.build({'layout': 'process', 'title': '协作步骤', 'reveal': True,
                                     'steps': [{'title': '准备', 'body': '查清材料'},
                                               {'title': '复核', 'body': '核对结果'}]})
        self.assertEqual(report['animated_slides'], 1)
        manifest = json.loads(Path(report['reveal_manifest']).read_text())
        self.assertEqual(len(manifest['slides'][0]['steps']), 2)
        with zipfile.ZipFile(path) as archive:
            xml = archive.read('ppt/slides/slide1.xml').decode()
        self.assertIn('<p:timing', xml)

    def test_long_table_preserves_all_rows_in_editable_continuations(self):
        rows = [[f'项目{i:02d}', f'结果{i:02d}'] for i in range(25)]
        prs, _, _ = self.build({'layout': 'table', 'title': '持续记录',
                                'table': {'columns': ['项目', '结果'], 'rows': rows}})
        self.assertGreater(len(prs.slides), 1)
        actual = []
        for slide in prs.slides:
            tables = [shape.table for shape in slide.shapes if shape.has_table]
            self.assertEqual(len(tables), 1)
            self.assertEqual([cell.text for cell in tables[0].rows[0].cells], ['项目', '结果'])
            actual.extend([[cell.text for cell in row.cells] for row in list(tables[0].rows)[1:]])
        self.assertEqual(actual, rows)


if __name__ == '__main__':
    unittest.main()
