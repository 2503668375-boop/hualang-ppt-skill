"""V12 报告版式、字段保留与整稿质量门禁的离线回归。"""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'artifact-template-hualang-school'
sys.path.insert(0, str(SKILL / 'scripts'))
try:
    from pptx import Presentation
    from hualang_build import assess_quality, build_deck, choose_layout
    from hualang_deck import validate_order
except ImportError as exc:
    raise unittest.SkipTest('python-pptx and Pillow are required for V12 builder checks') from exc


class ReportLayoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hualang-v12-layouts-')
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def slides(self):
        return [
            {
                'layout': 'positioning', 'title': '学校定位与数值',
                'x_axis': {'label': '课程选择丰富度', 'min': 0, 'max': 100, 'unit': '分'},
                'y_axis': {'label': '培养成果', 'min': 0, 'max': 100, 'unit': '分'},
                'x_reference': 50, 'y_reference': 50,
                'points': [
                    {'label': '华朗学校', 'x': 72, 'y': 82, 'display_x': '72分', 'display_y': '82分',
                     'note': '本校模拟定位', 'color': 'purple'},
                    {'label': '对照校A', 'x': 48, 'y': 62, 'note': '同口径模拟值', 'color': 'blue'},
                ],
                'body': '两个坐标均为演示评分，只用于展示定位关系。',
                'basis': '演示评分表；非学校实绩。', 'action': '按同一口径复核后，再决定课程资源投入。',
                'source': '来源：V12 原生散点回归数据',
            },
            {
                'layout': 'waterfall', 'title': '报名变化拆解',
                'steps': [
                    {'label': '上期报名', 'value': 120, 'kind': 'start', 'display': '120人'},
                    {'label': '开放日新增', 'value': 36, 'kind': 'delta', 'display': '+36人'},
                    {'label': '延期流失', 'value': -14, 'kind': 'delta', 'display': '-14人', 'color': 'red'},
                    {'label': '本期报名', 'value': 142, 'kind': 'total', 'display': '142人'},
                ],
                'basis': '起点 120，增加 36，减少 14，终点 142。',
                'action': '优先复核延期原因，不把净增长掩盖的流失忽略。',
                'source': '来源：模拟报名台账',
            },
            {
                'layout': 'trend', 'title': '到校与报名趋势',
                'categories': ['3月', '4月', '5月', '6月'],
                'y_axis': {'label': '人数', 'min': 0, 'max': 160, 'unit': '人'},
                'series': [
                    {'label': '到校', 'color': 'blue', 'values': [60, 82, 104, 126]},
                    {'label': '报名', 'color': 'purple', 'values': [30, 48, 68, 92],
                     'displays': ['30人', '48人', '68人', '92人']},
                ],
                'basis': '模拟月度汇总，人数口径保持一致。',
                'action': '后续按到校与报名差额检查跟进，不伪造转化率。',
                'source': '来源：模拟月度汇总',
            },
            {
                'layout': 'diagnostic', 'title': '招生问题诊断',
                'items': [
                    {'title': '首轮响应慢', 'evidence': '模拟记录中有两条咨询次日回复',
                     'implication': '家庭可能转向响应更及时的学校', 'action': '招生办当日分派并复核', 'status': '待改进'},
                    {'title': '课程解释散', 'evidence': '三场开放日使用三套不同口径',
                     'implication': '家长难以比较课程路径', 'action': '课程中心统一一页说明', 'status': '核对中'},
                    {'title': '到访衔接弱', 'evidence': '模拟回访显示到访后缺少明确下一步',
                     'implication': '意向难以进入正式申请', 'action': '离场前确认责任人与日期', 'status': '待改进'},
                ],
                'action': '校务会按三项问题分别检查责任落实。', 'source': '来源：模拟咨询与回访记录',
            },
            {
                'layout': 'targets', 'title': '下一阶段目标差额',
                'items': [
                    {'label': '重点课程咨询', 'current': '80人', 'target': '110人', 'delta': '+30人',
                     'note': '模拟目标，需校务会审议', 'color': 'purple'},
                    {'label': '校园开放日到校', 'current': '96人', 'target': '128人', 'delta': '+32人',
                     'note': '不得解释为既有实绩', 'color': 'blue'},
                ],
                'basis': '当前值与目标值均为演示输入。', 'action': '按差额安排咨询与活动资源。',
                'source': '来源：模拟目标卡',
            },
            {
                'layout': 'conversion', 'title': '招生阶段与接口',
                'stages': [
                    {'label': '咨询', 'definition': '确认家庭需求与基本资格', 'target': '待补', 'owner': '招生办'},
                    {'label': '到访', 'definition': '完成课程说明与校园参访', 'target': '待补', 'owner': '课程中心'},
                    {'label': '申请', 'definition': '提交材料并确认评估节点', 'target': '待补', 'owner': '招生办'},
                    {'label': '录取', 'definition': '完成评估、审议与通知', 'target': '待补', 'owner': '校务会'},
                ],
                'basis': '基线未知，全部标为待补；本页不计算转化率。',
                'action': '补齐同口径阶段人数后再讨论转化。',
                'source': '来源：模拟流程定义',
            },
            {
                'layout': 'swimlane', 'title': '招生推进泳道',
                'periods': ['6月', '7月', '8月', '9月'],
                'lanes': [
                    {'label': '招生办', 'owner': '招生负责人', 'tasks': [
                        {'start': 0, 'end': 1, 'label': '回访', 'deliverable': '咨询清单', 'status': '进行中'},
                        {'start': 2, 'end': 3, 'label': '申请', 'deliverable': '材料台账', 'status': '未开始'},
                    ]},
                    {'label': '课程中心', 'owner': '课程负责人', 'tasks': [
                        {'start': 0, 'end': 2, 'label': '课程说明', 'deliverable': '统一讲义', 'status': '进行中'},
                    ]},
                ],
                'body': '任务条按 periods 的 0 基索引跨列，交付物随任务展示。',
                'basis': '模拟工作安排，月份与责任均为演示。',
                'action': '每月按交付物复核，而不是只报活动次数。',
                'source': '来源：模拟推进计划',
            },
            {
                'layout': 'decision', 'title': '校董会拟审议事项',
                'items': [
                    {'title': '开放日频次', 'decision': '是否由每月一场调整为两场',
                     'recommendation': '先试办两场并按到校质量复核', 'reason': '模拟回访显示时间冲突',
                     'owner': '招生办', 'date': '2026年11月'},
                    {'title': '课程说明统一', 'decision': '是否采用统一课程路径说明',
                     'recommendation': '同意统一口径并保留学段差异', 'reason': '现有说明不利于家庭比较',
                     'owner': '课程中心', 'date': '2026年11月'},
                ],
                'action': '请按两项分别形成审议结论。', 'source': '来源：模拟审议材料',
            },
        ]

    def build(self, slides, name='v12', strict=False):
        if isinstance(slides, dict):
            slides = [slides]
        path = self.directory / f'{name}.pptx'
        spec = {'title': 'V12 回归', 'scenario': 'internal_report', 'content_only': True,
                'strict_quality': strict, 'slides': slides}
        report = build_deck(spec, path)
        return Presentation(path), report, path

    @staticmethod
    def text(prs):
        return '\n'.join(shape.text for slide in prs.slides for shape in slide.shapes
                         if shape.has_text_frame)

    def test_every_new_layout_generates_native_editable_content(self):
        for index, slide in enumerate(self.slides()):
            with self.subTest(layout=slide['layout']):
                auto = dict(slide)
                auto['layout'] = 'auto'
                self.assertEqual(choose_layout(auto), slide['layout'])
                prs, report, _ = self.build(slide, name=f'layout-{index}')
                self.assertEqual(len(prs.slides), 1)
                self.assertEqual(report['page_plan'][0]['layout'], slide['layout'])
                self.assertFalse(validate_order(prs))
                self.assertGreater(len(prs.slides[0].shapes), 12)
                self.assertFalse(any(shape.has_table for shape in prs.slides[0].shapes))
                for field in ('basis', 'action'):
                    if field in slide:
                        self.assertIn(str(slide[field]), self.text(prs))
                self.assertNotIn(slide['source'], self.text(prs))
                self.assertEqual(report['source_records'][0]['source'], slide['source'])

    def test_signed_waterfall_and_trend_values_are_preserved(self):
        prs, _, _ = self.build(self.slides()[1], name='signed-waterfall')
        exported = self.text(prs)
        self.assertIn('+36人', exported)
        self.assertIn('-14人', exported)
        self.assertIn('142人', exported)
        prs, _, _ = self.build(self.slides()[2], name='trend-values')
        self.assertIn('92人', self.text(prs))

    def test_eight_layout_regression_has_expected_pages_objects_and_valid_xml(self):
        prs, report, path = self.build(self.slides(), name='eight-layouts', strict=True)
        self.assertEqual(len(prs.slides), 8)
        self.assertEqual(report['body_pages'], 8)
        self.assertEqual(len(report['quality']['layout_families']), 8)
        self.assertIsNone(report['quality']['passed'])
        self.assertTrue(report['quality']['needs_review'])
        self.assertFalse(validate_order(prs))
        self.assertGreater(path.stat().st_size, 20000)
        for slide in prs.slides:
            self.assertTrue(any(shape.has_text_frame and shape.text.strip() for shape in slide.shapes))

    def test_empty_targets_and_other_primary_arrays_are_rejected(self):
        empty_cases = []
        for slide in self.slides():
            item = copy.deepcopy(slide)
            field = {'positioning': 'points', 'waterfall': 'steps', 'trend': 'series',
                     'diagnostic': 'items', 'targets': 'items', 'conversion': 'stages',
                     'swimlane': 'lanes', 'decision': 'items'}[item['layout']]
            item[field] = []
            empty_cases.append(item)
        for index, slide in enumerate(empty_cases):
            with self.subTest(layout=slide['layout']):
                with self.assertRaisesRegex(ValueError, '第 1 页.*非空'):
                    self.build(slide, name=f'empty-{index}')

    def test_invalid_positioning_values_and_ranges_are_rejected(self):
        for index, value in enumerate((float('nan'), float('inf'), True, '72')):
            slide = copy.deepcopy(self.slides()[0])
            slide['points'][0]['x'] = value
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, '有限数值'):
                    self.build(slide, name=f'bad-position-{index}')
        slide = copy.deepcopy(self.slides()[0])
        slide['points'][0]['x'] = 120
        with self.assertRaisesRegex(ValueError, '超出坐标轴范围'):
            self.build(slide, name='out-of-range')

    def test_empty_and_invalid_trend_values_are_rejected(self):
        slide = copy.deepcopy(self.slides()[2])
        slide['series'][0]['values'][0] = float('nan')
        with self.assertRaisesRegex(ValueError, '有限数值'):
            self.build(slide, name='nan-trend')
        slide = copy.deepcopy(self.slides()[2])
        slide['series'][0]['values'] = []
        with self.assertRaisesRegex(ValueError, '等长且非空'):
            self.build(slide, name='empty-trend-values')

    def test_short_report_with_necessary_table_is_not_blocked(self):
        slides = [copy.deepcopy(self.slides()[0]),
                  {'layout': 'table', 'title': '必要查数表', 'basis': '模拟依据',
                   'table': {'columns': ['项目', '数值'], 'rows': [['咨询', '80'], ['到访', '60']]}}]
        _, report, _ = self.build(slides, name='necessary-table', strict=True)
        self.assertEqual(report['quality']['table_ratio'], 0.5)
        self.assertIsNone(report['quality']['passed'])
        self.assertTrue(report['quality']['needs_review'])
        self.assertFalse(report['quality']['sequence_findings'])

    def test_repeated_long_report_prompts_review_without_layout_quota(self):
        slides = []
        for i in range(8):
            slide = copy.deepcopy(self.slides()[4])
            slide['title'] = f'目标差额 {i + 1}'
            slides.append(slide)
        _, report, _ = self.build(slides, name='sequence-review', strict=True)
        self.assertTrue(report['quality']['needs_review'])
        self.assertTrue(report['quality']['sequence_findings'])
        self.assertIsNone(report['quality']['passed'])
        self.assertTrue(report['quality']['needs_review'])

    def test_appendix_is_reported_separately(self):
        appendix = copy.deepcopy(self.slides()[0])
        appendix['appendix'] = True
        appendix['basis'] = appendix['action'] = appendix['source'] = ''
        prs, report, _ = self.build([appendix], name='appendix-only', strict=True)
        self.assertEqual(report['body_pages'], 1)
        self.assertEqual(report['quality']['checked_body_pages'], 0)
        self.assertEqual(report['quality']['appendix_pages'], 1)
        self.assertIsNone(report['quality']['passed'])
        self.assertTrue(report['quality']['needs_review'])

    def test_existing_statement_comparison_bars_timeline_keep_supporting_fields(self):
        cases = [
            {'layout': 'statement', 'title': '开场与收束不同', 'lead': '先说明核心判断',
             'items': [{'title': '事实', 'body': '具体事实与案例'}, {'title': '取舍', 'body': '方案选择依据'}],
             'bleed': False},
            {'layout': 'comparison', 'title': '比较保留依据', 'left': {'title': '现状', 'body': '当前安排'},
             'right': {'title': '建议', 'body': '调整安排'}},
            {'layout': 'bars', 'title': '横条保留依据', 'series': [{'label': '咨询', 'value': 80}]},
            {'layout': 'timeline', 'title': '节点保留依据',
             'steps': [{'date': '11月', 'title': '复核', 'body': '核对阶段材料'}]},
        ]
        for index, slide in enumerate(cases):
            slide.update({'basis': f'依据内容{index}', 'action': f'收束行动{index}', 'source': f'来源内容{index}'})
            with self.subTest(layout=slide['layout']):
                prs, _, _ = self.build(slide, name=f'legacy-support-{index}')
                exported = self.text(prs)
                for value in (f'依据内容{index}', f'收束行动{index}'):
                    self.assertIn(value, exported)
                self.assertNotIn(f'来源内容{index}', exported)

    def test_quality_result_can_be_assessed_without_export(self):
        slides = self.slides()
        logs = [{'source_slide': i + 1, 'layout': slide['layout'], 'generated_pages': 1}
                for i, slide in enumerate(slides)]
        quality = assess_quality({'slides': slides}, 'internal_report', logs)
        self.assertIsNone(quality['passed'])
        self.assertTrue(quality['needs_review'])
        self.assertEqual(quality['table_ratio'], 0)


if __name__ == '__main__':
    unittest.main()
