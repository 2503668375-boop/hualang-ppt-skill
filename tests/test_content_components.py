"""Check actual material preservation, references, capacity and common scales."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

from pptx import Presentation

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'artifact-template-hualang-school'
sys.path.insert(0, str(SKILL / 'scripts'))
from hualang_build import build_deck, choose_layout
from hualang_content_components import draw_revision
from hualang_deck import Deck


class ContentComponentsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.example = json.loads((SKILL / 'assets/examples/content-components.json').read_text())

    def build(self, slides):
        spec = {'title': '内容组件验证', 'scenario': 'internal_report', 'content_only': True,
                'slides': slides}
        path = self.folder / 'result.pptx'
        report = build_deck(spec, path)
        prs = Presentation(path)
        text = '\n'.join(s.text for p in prs.slides for s in p.shapes if s.has_text_frame)
        return prs, report, text

    def test_complete_source_annotations_and_rewrites_remain_editable(self):
        slide = self.example['slides'][0]
        prs, report, text = self.build([slide])
        for block in slide['source_blocks']:
            self.assertIn(block['text'], text)
        for note in slide['annotations']:
            for key in ('label', 'comment', 'rewrite'):
                if key in note:
                    self.assertIn(note[key], text)
        names = {s.name for p in prs.slides for s in p.shapes}
        self.assertIn('annotation-anchor-reason', names)
        self.assertIn('source-reason', names)
        self.assertEqual(report['content_review']['status'], 'human_review_required')

    def test_auto_routing_uses_material_fields(self):
        for slide in self.example['slides']:
            auto = copy.deepcopy(slide)
            auto['layout'] = 'auto'
            self.assertEqual(choose_layout(auto), slide['layout'])
            self.build([auto])

    def test_reference_to_absent_source_and_duplicate_source_fail(self):
        slide = copy.deepcopy(self.example['slides'][0])
        slide['annotations'][0]['target'] = 'absent'
        with self.assertRaisesRegex(ValueError, '找不到对应原文'):
            self.build([slide])
        slide = copy.deepcopy(self.example['slides'][0])
        slide['source_blocks'][1]['id'] = 'claim'
        with self.assertRaisesRegex(ValueError, '不得重复'):
            self.build([slide])

    def test_revision_paginates_complete_units_without_dropping_boundary(self):
        slide = copy.deepcopy(self.example['slides'][1])
        slide['changes'] *= 4
        prs, _, text = self.build([slide])
        self.assertGreater(len(prs.slides), 1)
        for page in prs.slides:
            page_text = '\n'.join(s.text for s in page.shapes if s.has_text_frame)
            self.assertIn(slide['boundary'], page_text)
            self.assertIn(slide['action'], page_text)
            # Every displayed before has its after and reason on the same page.
            for change in slide['changes']:
                if change['before'] in page_text:
                    self.assertIn(change['after'], page_text)
                    self.assertIn(change['reason'], page_text)
        for change in self.example['slides'][1]['changes']:
            self.assertEqual(text.count(change['before']), 4)

    def test_extreme_single_unit_and_small_local_region_fail_before_crop(self):
        slide = copy.deepcopy(self.example['slides'][1])
        slide['changes'][0]['after'] = '完整但超出页面的材料。' * 150
        with self.assertRaisesRegex(ValueError, '完整材料单元过长'):
            self.build([slide])
        deck = Deck(SKILL / 'assets/source-original.pptx', content_only=True)
        page = deck.page('局部容量')
        with self.assertRaisesRegex(ValueError, '不会裁字'):
            draw_revision(page, self.example['slides'][1]['changes'], h=60)
        self.assertFalse(any(s.name.startswith('revision-before') for s in page.slide.shapes))

    def test_tradeoff_shared_scale_survives_continuation(self):
        slide = copy.deepcopy(self.example['slides'][2])
        first = copy.deepcopy(slide['options'][0])
        second = copy.deepcopy(slide['options'][1])
        second['value'] = 6
        second['display'] = '6 万元'
        slide['options'] = [first, second, first, second]
        prs, _, text = self.build([slide])
        bars = [(float(s.width), s.name) for p in prs.slides for s in p.shapes if s.name.startswith('tradeoff-bar')]
        self.assertEqual(len(bars), 4)
        widths = sorted(set(v for v, _ in bars))
        self.assertAlmostEqual(widths[-1] / widths[0], 2, places=5)
        self.assertIn(slide['recommendation']['why'], text)
        self.assertIn(slide['boundary'], text)

    def test_three_short_options_stay_together_without_losing_conditions(self):
        slide = {
            'layout': 'tradeoff', 'title': '费用与取舍',
            'context': '原创模拟方案 · 下一个四周，17:00–19:00；预算为估算上限，三项均未批准',
            'metric': {'label': '四周预算上限', 'unit': '元', 'max': 4800},
            'options': [
                {'name': '每周四晚', 'value': 4800, 'display': '4800元',
                 'fit': '周一至周四。\n保留全部原晚间时段。', 'cost': '继续承担四晚值班与安保支出。',
                 'condition': '须核定人员、安保排班及预算。'},
                {'name': '每周两晚（建议）', 'value': 3000, 'display': '3000元',
                 'fit': '周一、周二。\n保留现有高到访时段。', 'cost': '周三、周四不再延时，相应使用机会收缩。',
                 'condition': '须批准方案及预算，并核定排班。'},
                {'name': '每周四晚预约制', 'value': 4200, 'display': '4200元',
                 'fit': '周一至周四。\n预约满10人开馆。', 'cost': '取消开馆仍有值班成本，节省受执行影响。',
                 'condition': '需明确预约与取消安排，并核定排班。'},
            ],
            'body': '本轮新增支出4800元：值班3200元、安保1200元、电费400元。',
            'recommendation': {'option': '每周两晚',
                               'why': '较四晚预算少1800元（37.5%）；保留历史高到访时段，未来参与人数仍需观察。'},
        }
        prs, report, text = self.build([slide])
        self.assertEqual(len(prs.slides), 1)
        self.assertEqual(report['page_plan'][0]['generated_pages'], 1)
        for option in slide['options']:
            for field in ('name', 'display', 'fit', 'cost', 'condition'):
                self.assertIn(option[field], text)
        self.assertIn(slide['body'], text)
        self.assertIn(slide['recommendation']['why'], text)
        shapes = {s.name: s for s in prs.slides[0].shapes}
        for i in range(3):
            name, value, bar = (shapes[f'tradeoff-{kind}-{i}'] for kind in ('name', 'value', 'bar'))
            self.assertEqual(name.top, value.top)
            self.assertGreater(value.left, name.left + name.width)
            self.assertGreater(bar.top, max(name.top + name.height, value.top + value.height))
            self.assertEqual(name.text_frame.paragraphs[0].runs[0].font.size.pt, 15.75)

    def test_long_tradeoff_name_and_value_wrap_above_their_bar(self):
        slide = copy.deepcopy(self.example['slides'][2])
        slide.pop('lead'); slide.pop('recommendation'); slide.pop('boundary')
        slide['options'][0]['name'] = '集中培训与共同备课结合的分层支持安排'
        slide['options'][0]['display'] = '预算上限为12万元，按学期分阶段投入'
        prs, _, text = self.build([slide])
        shapes = {s.name: s for s in prs.slides[0].shapes}
        name, value, bar = (shapes[f'tradeoff-{kind}-0'] for kind in ('name', 'value', 'bar'))
        self.assertIn(slide['options'][0]['name'], text)
        self.assertIn(slide['options'][0]['display'], text)
        self.assertGreater(name.height, 40 * 9525)
        self.assertGreater(value.height, 40 * 9525)
        self.assertGreater(bar.top, max(name.top + name.height, value.top + value.height))

    def test_invalid_metric_and_missing_cost_fail(self):
        for invalid in (-1, float('nan'), True):
            slide = copy.deepcopy(self.example['slides'][2])
            slide['options'][0]['value'] = invalid
            with self.assertRaisesRegex(ValueError, '非负有限数'):
                self.build([slide])
        slide = copy.deepcopy(self.example['slides'][2])
        slide['metric']['max'] = 1
        with self.assertRaisesRegex(ValueError, '覆盖全部数值'):
            self.build([slide])
        slide = copy.deepcopy(self.example['slides'][2])
        del slide['options'][0]['cost']
        with self.assertRaisesRegex(ValueError, 'cost'):
            self.build([slide])


if __name__ == '__main__':
    unittest.main()
