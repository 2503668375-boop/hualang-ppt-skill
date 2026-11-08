"""V12 audit regressions: audience data, numeric meaning and real saved output."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'artifact-template-hualang-school'
sys.path.insert(0, str(SKILL / 'scripts'))
from hualang_build import build_deck
from pptx import Presentation
from test_v12_calculations import valid_calculation


class AuditRegressions(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hualang-v12-audit-')
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def build(self, slides, scenario='internal_report', **extra):
        spec = dict(title='审查模拟', scenario=scenario, content_only=True, slides=slides)
        spec.update(extra)
        path = self.directory / 'output.pptx'
        report = build_deck(spec, path)
        return Presentation(path), report, path

    def text(self, prs):
        return '\n'.join(shape.text for slide in prs.slides for shape in slide.shapes
                         if shape.has_text_frame)

    def test_calculation_error_cannot_be_bypassed(self):
        calculation = valid_calculation()
        calculation['expected'] = 99
        with self.assertRaisesRegex(ValueError, '复算不一致'):
            self.build([dict(layout='statement', title='模拟', lead='模拟')],
                       strict_quality=False, calculations=[calculation])
        self.assertFalse((self.directory / 'output.pptx').exists())

    def test_internal_source_is_only_in_review_report(self):
        source = '内部台账文件原始来源秘密标记'
        table_source = '内部工作簿页签秘密标记'
        slide = dict(layout='table', title='模拟人数', context='模拟；11月；单位人',
                     source=source, table=dict(columns=['项目', '人数'], rows=[['甲', 30]], source=table_source))
        prs, report, path = self.build([slide])
        self.assertIn(slide['context'], self.text(prs))
        with zipfile.ZipFile(path) as z:
            all_xml = '\n'.join(z.read(n).decode('utf-8') for n in z.namelist() if n.endswith('.xml'))
        self.assertNotIn(source, all_xml)
        self.assertNotIn(table_source, all_xml)
        self.assertEqual(report['source_records'][0]['source'], source)
        self.assertEqual(report['source_records'][0]['table_source'], table_source)
        self.assertEqual(slide['table']['source'], table_source)

    def test_classroom_context_and_legitimate_term_survive(self):
        slide = dict(layout='lesson', title='电路观察', context='模拟教学；非真实实验结果',
                     task='观察闭环电路', work='本例仅作版式验证', independent_task='写出观察记录')
        prs, report, _ = self.build([slide], 'classroom')
        self.assertIn(slide['context'], self.text(prs))
        self.assertIn(slide['task'], self.text(prs))
        self.assertIsNone(report['quality']['passed'])
        self.assertTrue(report['quality']['needs_review'])

    def test_teacher_task_label_matches_use(self):
        slide = dict(layout='lesson', title='教师安排', context='模拟说课',
                     task='说明课堂步骤', work='观察学生的两种回应', independent_task='按回应调整追问')
        prs, _, _ = self.build([slide], 'lesson_plan')
        self.assertIn('实施提示', self.text(prs))
        self.assertNotIn('独立作答', self.text(prs))

    def test_parent_process_action_is_visible(self):
        action = '教师周五反馈，家长周末复核。'
        slide = dict(layout='process', title='家校分工', context='模拟安排', action=action,
                     steps=[dict(title='教师', body='提供观察记录'), dict(title='家庭', body='陪伴阅读')])
        prs, _, _ = self.build([slide], 'parent_meeting')
        self.assertIn(action, self.text(prs))

    def test_unsupported_supplied_text_fails_instead_of_disappearing(self):
        slide = dict(layout='lesson', title='学习任务', task='完成观察', work='观察对象',
                     basis='必须交付的完整论证')
        with self.assertRaisesRegex(ValueError, 'basis 字段未'):
            self.build([slide], 'classroom')

    def test_metrics_preserve_body_and_basis_together(self):
        slide = dict(layout='metrics', title='人数变化', body='本期仅统计到校学生。',
                     basis='与上期采用相同统计范围。', metrics=[dict(label='人数', value=30)])
        prs, _, _ = self.build([slide])
        self.assertIn(slide['body'], self.text(prs))
        self.assertIn(slide['basis'], self.text(prs))

    def test_waterfall_and_numeric_target_relationships_are_checked(self):
        waterfall = dict(layout='waterfall', title='变化分解', steps=[
            dict(label='期初', kind='start', value=100), dict(label='增量', kind='delta', value=10),
            dict(label='期末', kind='total', value=111)])
        with self.assertRaisesRegex(ValueError, '合计.*不一致'):
            self.build([waterfall])
        target = dict(layout='targets', title='目标差额', items=[dict(label='人数', current=20, target=30, delta=15)])
        with self.assertRaisesRegex(ValueError, 'delta.*不一致'):
            self.build([target])

    def test_single_real_target_does_not_require_filler(self):
        slide = dict(layout='targets', title='一个目标', items=[dict(label='模拟人数', current=0, target=20, delta=20)])
        prs, _, _ = self.build([slide])
        marker = next(s for s in prs.slides[0].shapes if s.name == 'target-mark-1')
        self.assertAlmostEqual(marker.width / 9525, 6)
        self.assertGreater(marker.top / 9525, 112)
        self.assertLess((marker.top + marker.height) / 9525, 650)

    def test_activity_four_short_rows_share_page_and_long_rows_continue(self):
        steps = [dict(time=f'{i + 1}分钟', task=f'活动{i + 1}观察并记录',
                      expected='说明观察结果', feedback='依据回应调整追问') for i in range(4)]
        slide = dict(layout='activity', title='课堂活动', steps=steps, context='模拟教学')
        prs, _, _ = self.build([slide], 'lesson_plan')
        self.assertEqual(len(prs.slides), 1)
        for item in steps:
            self.assertIn(item['task'], self.text(prs))
        expanded = copy.deepcopy(slide)
        for item in expanded['steps']:
            item['task'] += '保留材料的条件并向小组解释观察结果。' * 6
            item['feedback'] += '针对遗漏条件重新观察与复核。' * 6
        prs, _, _ = self.build([expanded], 'lesson_plan')
        self.assertGreater(len(prs.slides), 1)
        for item in expanded['steps']:
            self.assertIn(item['task'], self.text(prs))
            self.assertIn(item['feedback'], self.text(prs))

    def test_short_three_decisions_stay_together_and_long_items_continue(self):
        slide = json.loads((SKILL / 'assets/examples/internal-report-v12.json').read_text())['slides'][-1]
        prs, _, _ = self.build([slide])
        self.assertEqual(len(prs.slides), 1)
        self.assertIn('模拟财务｜12月', self.text(prs))
        expanded = copy.deepcopy(slide)
        expanded['items'] = copy.deepcopy(slide['items'][:2])
        for item in expanded['items']:
            item['decision'] = '需要共同审议的模拟事项。' * 8
            item['recommendation'] = '需补充比较条件后形成明确意见。' * 8
        prs, report, _ = self.build([expanded])
        self.assertEqual(len(prs.slides), 2)
        self.assertEqual(report['page_plan'][0]['generated_pages'], 2)
        for item in expanded['items']:
            self.assertIn(item['decision'], self.text(prs))


if __name__ == '__main__':
    unittest.main()
