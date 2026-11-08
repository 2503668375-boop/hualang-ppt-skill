"""Editorial behavior checks: no generic filling, no automatic style verdict."""
import copy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE
from pptx.util import Inches

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'artifact-template-hualang-school'
sys.path.insert(0, str(SKILL / 'scripts'))
from hualang_build import build_deck, validate_spec, assess_quality
from audit_content_claims import audit_text_pages, audit_presentation


class ExpressionTools(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='hualang-expression-')
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def build(self, slide, scenario='classroom'):
        path = self.folder / 'minimum.pptx'
        report = build_deck({'title': '验证', 'scenario': scenario,
                             'content_only': True, 'slides': [slide]}, path)
        return Presentation(path), report

    def test_missing_activity_details_are_not_filled_by_body_or_stock_phrase(self):
        slide = {'layout': 'activity', 'title': '任务反馈', 'steps': [
            {'task': '解释人物选择', 'body': '原有正文不能冒充反馈'}]}
        for fields in ({}, {'expected': '待课堂观察', 'feedback': '依据学生回应调整'},
                       {'expected': '指出具体动作', 'body': '补充说明'}):
            candidate = copy.deepcopy(slide)
            candidate['steps'][0].update(fields)
            with self.assertRaisesRegex(ValueError, r'第 1 页 活动 1.*expected|第 1 页 活动 1.*feedback'):
                validate_spec({'title': '验证', 'scenario': 'lesson_plan', 'content_only': True,
                               'slides': [candidate]})
        slide['steps'][0].update(expected='指出人物将仅有的伞给同桌。',
                                 feedback='若只说他很好，追问他自己承担了什么不便。')
        self.assertEqual(validate_spec({'title': '验证', 'scenario': 'lesson_plan',
                                        'content_only': True, 'slides': [slide]}), 'lesson_plan')

    def test_activity_needs_a_real_task_as_well_as_feedback(self):
        slide = {'layout': 'activity', 'title': '课堂安排', 'steps': [
            {'expected': '指出人物选择。', 'feedback': '要求指出相关动作。'}]}
        with self.assertRaisesRegex(ValueError, 'task'):
            validate_spec({'title': '课堂安排', 'scenario': 'lesson_plan',
                           'content_only': True, 'slides': [slide]})
        slide['steps'][0]['title'] = '阅读人物片段并说明选择'
        self.assertEqual(validate_spec({'title': '课堂安排', 'scenario': 'lesson_plan',
                                        'content_only': True, 'slides': [slide]}), 'lesson_plan')

    def test_answers_use_body_type_without_invented_lead(self):
        for slide in [
            {'layout': 'lesson', 'title': '作答反馈', 'task': '判断人物特点。',
             'work': '人物把仅有的伞交给同桌。', 'answer': '参考作答：他愿意承担不便。'},
            {'layout': 'practice', 'title': '练习反馈', 'questions': ['解释人物选择。'],
             'answer': '参考作答：他愿意承担不便。'},
        ]:
            prs, report = self.build(slide)
            feedback = prs.slides[-1]
            answers = [s for s in feedback.shapes if s.name == 'feedback-answer']
            self.assertEqual(len(answers), 1)
            self.assertIn(slide['answer'], answers[0].text)
            self.assertEqual(answers[0].text_frame.paragraphs[0].runs[0].font.size.pt, 19.5)
            self.assertFalse(any(s.name == 'lead' for s in feedback.shapes))
            text = '\n'.join(s.text for s in feedback.shapes if s.has_text_frame)
            self.assertNotIn('依据关键条件核对', text)
            self.assertNotIn('按作答证据核对', text)
            self.assertIsNone(report['quality']['passed'])
            self.assertTrue(report['quality']['needs_review'])
            slide['answer_lead'] = '让伞的动作说明他愿意承担不便。'
            prs, _ = self.build(slide)
            self.assertTrue(any(s.has_text_frame and s.text == slide['answer_lead'] for s in prs.slides[-1].shapes))

    def test_basis_has_no_generated_caption_but_preserves_explicit_caption(self):
        slides = [
            {'layout': 'bars', 'title': '费用比较', 'series': [{'label': '甲', 'value': 10}],
             'basis': '同一期间的已核费用。'},
            {'layout': 'targets', 'title': '目标差额',
             'items': [{'label': '人数', 'current': 10, 'target': 12, 'delta': 2}],
             'basis': '同一期间的已核费用。'},
        ]
        for slide in slides:
            prs, _ = self.build(slide, 'internal_report')
            text = [s.text for s in prs.slides[0].shapes if s.has_text_frame]
            self.assertIn(slide['basis'], text)
            self.assertNotIn('依据', text)
            slide['basis'] = {'title': '费用范围', 'body': '同一期间的已核费用。'}
            prs, _ = self.build(slide, 'internal_report')
            self.assertIn('费用范围', [s.text for s in prs.slides[0].shapes if s.has_text_frame])

    def test_clean_automatic_checks_do_not_mean_editorial_pass(self):
        spec = {'slides': [{'layout': 'table', 'title': '费用', 'role': 'evidence',
                            'reader_question': '费用多少', 'new_information': '实际费用'}]}
        result = assess_quality(spec, 'internal_report', [
            {'source_slide': 1, 'layout': 'table', 'generated_pages': 1}])
        self.assertIsNone(result['passed'])
        self.assertTrue(result['needs_review'])
        self.assertFalse(result['has_automated_findings'])

    def test_plain_text_candidates_keep_context_and_never_rewrite(self):
        pages = [
            {'page': 1, 'text_blocks': ['8套', '4套', '4部', '先判断，再定位；先比较，再取舍。',
                                      '判断、证据、行动。判断、证据、行动。', '依据关键条件核对作答，定位具体错误。']},
            {'page': 2, 'text_blocks': ['依据关键条件核对作答，定位具体错误。',
                                      '所有材料一键完成，生成的课件不会出错。']},
        ]
        result = audit_text_pages(pages)
        categories = {f['category'] for f in result['findings']}
        self.assertTrue({'detached_quantity_group', 'parallel_sequence_candidate',
                         'repeated_short_phrase', 'repeated_short_passage', 'absolute_claim'} <= categories)
        self.assertEqual(result['slides'][0]['text_blocks'], pages[0]['text_blocks'])
        self.assertEqual(result['slides'][0]['adjacent_context']['next']['text_blocks'], pages[1]['text_blocks'])
        self.assertEqual(result['status'], 'human_review_required')
        self.assertNotIn('score', result)
        self.assertNotIn('passed', result)

    def test_purpose_inventory_is_a_review_candidate_not_a_rewrite(self):
        vague = '本次汇报有三个目的：摸清现状、找准问题、明确方向。'
        actual = '年度计划有三项目标：招生、课室使用和预算执行，具体口径另列。'
        result = audit_text_pages([{'text_blocks': [vague, actual]}])
        self.assertTrue(any(f['category'] == 'inventory_rhetoric' for f in result['findings']))
        self.assertEqual(result['slides'][0]['text_blocks'], [vague, actual])
        self.assertEqual(result['status'], 'human_review_required')

    def test_normal_counts_order_quotes_and_steps_are_preserved(self):
        text = ['3套教材已送达七年级。', '4部教学纪录片，每部30分钟。',
                '第2题：先称取2.5 g食盐，再加入47.5 g水，搅拌至溶解。',
                '1. 阅读原文；2. 找出动作；3. 解释原因。']
        result = audit_text_pages([{'text_blocks': text}])
        self.assertFalse(result['findings'])
        self.assertEqual(result['slides'][0]['text_blocks'], text)
        self.assertTrue(result['slides'][0]['review_required'])
        quote = '辨错原句：“所有材料一键完成，课件不会出错。”请说明哪里缺少条件。'
        result = audit_text_pages([{'text_blocks': [quote]}])
        self.assertEqual(result['slides'][0]['text_blocks'], [quote])
        self.assertEqual(result['status'], 'human_review_required')

    def test_separate_numbers_units_and_source_coordinates_are_kept(self):
        objects = [{'name': f'n{i}', 'text': value, 'bbox': {'x': i * 20, 'y': 100, 'w': 30, 'h': 20}}
                   for i, value in enumerate(['8', '套', '4', '部'])]
        result = audit_text_pages([{'page': 7, 'objects': objects}])
        self.assertTrue(any(f['category'] == 'detached_quantity_group' for f in result['findings']))
        self.assertEqual(result['slides'][0]['objects'][0]['name'], 'n0')
        self.assertEqual(result['slides'][0]['objects'][0]['bbox']['x'], 0)
        self.assertEqual(result['slides'][0]['page'], 7)

    def test_actual_minimal_file_lists_text_position_and_unread_chart_image(self):
        prs = Presentation(); slide = prs.slides.add_slide(prs.slide_layouts[6])
        box = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1))
        box.name = 'actual-claim'; box.text = '正常费用说明，仍需对照材料。'
        data = CategoryChartData(); data.categories = ['甲']; data.add_series('费用', [10])
        slide.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(1), Inches(2), Inches(3), Inches(2), data)
        slide.shapes.add_picture(str(SKILL / 'assets/campus.jpg'), Inches(5), Inches(1), Inches(1), Inches(1))
        path = self.folder / 'objects.pptx'; prs.save(path)
        result = audit_presentation(path)
        claim = next(o for o in result['slides'][0]['objects'] if o['name'] == 'actual-claim')
        self.assertEqual(claim['bbox']['x'], 96)
        self.assertEqual(claim['text'], box.text)
        self.assertEqual({o['kind'] for o in result['slides'][0]['incomplete_objects']}, {'chart', 'image'})

    def test_js_title_review_warns_without_rejecting_valid_sequence(self):
        source = (SKILL / 'scripts/hualang-kit.mjs').read_text()
        start = source.index('export function assertTopicTitle(')
        end = source.index('\n\n\n', start)
        function = source[start:end].replace('export function', 'function', 1)
        script = function + '''\nconst messages=[]; console.warn=(x)=>messages.push(x);
for(const t of ['先称取再溶解','如何解释人物选择','先秦文化']) {
 if(assertTopicTitle(t)!==t) throw Error('title changed');
}
if(messages.length!==2) throw Error('review hints missing');
let rejected=false;try{assertTopicTitle('  ')}catch(e){rejected=true}
if(!rejected)throw Error('empty title accepted');
'''
        result = subprocess.run(['node', '--input-type=module', '-e', script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
