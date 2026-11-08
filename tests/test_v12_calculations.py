"""V12 derived-metric semantics and complete statement-content checks."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'artifact-template-hualang-school'
sys.path.insert(0, str(SKILL / 'scripts'))

from check_calculations import check_calculations
from hualang_build import build_deck
from pptx import Presentation


def valid_calculation():
    return {
        'comparison_id': 'price_cut_student_3yr',
        'subject': '华朗全面降至3.2万元的每生学费变化',
        'baseline': '6.8万元与3.2万元均为每学期',
        'perspective': '家庭三年学费减少；学校单生学费收入减少',
        'period': '高中三年6学期',
        'unit': '万元/生/三年',
        'formula': '(old_price - new_price) * semesters',
        'inputs': {'old_price': 6.8, 'new_price': 3.2, 'semesters': 6},
        'expected': 21.6,
        'tolerance': 0,
    }


class CalculationTests(unittest.TestCase):
    def test_safe_formula_and_float_noise_pass(self):
        report = check_calculations({'calculations': [valid_calculation()]})
        self.assertTrue(report['passed'])
        self.assertAlmostEqual(report['results'][0]['actual'], 21.6)

    def test_required_comparison_perspective_is_enforced(self):
        calculation = valid_calculation()
        del calculation['perspective']
        with self.assertRaisesRegex(ValueError, 'perspective'):
            check_calculations({'calculations': [calculation]})

    def test_same_id_cannot_change_subject_or_baseline(self):
        first, second = valid_calculation(), valid_calculation()
        second['baseline'] = '改为每学年口径'
        with self.assertRaisesRegex(ValueError, '跨页主体、基线、视角、期间或单位不一致'):
            check_calculations({'calculations': [first, second]})

    def test_wrong_expected_value_is_rejected(self):
        calculation = valid_calculation()
        calculation['expected'] = 21.78
        with self.assertRaisesRegex(ValueError, '复算不一致'):
            check_calculations({'calculations': [calculation]})

    def test_arbitrary_code_and_zero_division_are_rejected(self):
        for formula in ('__import__("os").system("true")', 'old_price / zero'):
            calculation = valid_calculation()
            calculation['formula'] = formula
            if 'zero' in formula:
                calculation['inputs']['zero'] = 0
            with self.subTest(formula=formula):
                with self.assertRaises(ValueError):
                    check_calculations({'calculations': [calculation]})

    def test_invalid_calculation_stops_before_pptx_output(self):
        calculation = valid_calculation()
        calculation['expected'] = 20
        spec = {'title': '拒绝错误指标', 'scenario': 'internal_report', 'content_only': True,
                'calculations': [calculation],
                'slides': [{'layout': 'statement', 'title': '模拟页', 'lead': '模拟判断',
                            'body': '模拟说明', 'basis': '模拟依据'}]}
        with tempfile.TemporaryDirectory(prefix='hualang-v12-calc-') as directory:
            output = Path(directory) / 'must-not-exist.pptx'
            with self.assertRaisesRegex(ValueError, '复算不一致'):
                build_deck(spec, output)
            self.assertFalse(output.exists())

    def test_v12_example_builds_and_reports_calculation(self):
        spec = json.loads((SKILL / 'assets/examples/internal-report-v12.json').read_text())
        with tempfile.TemporaryDirectory(prefix='hualang-v12-example-') as directory:
            output = Path(directory) / 'example.pptx'
            report = build_deck(spec, output)
            self.assertEqual(report['calculations']['count'], 1)
            self.assertTrue(report['calculations']['passed'])
            self.assertEqual(len(Presentation(output).slides), 8)

    def test_statement_body_and_items_are_both_preserved(self):
        spec = {'title': '完整开场', 'scenario': 'internal_report', 'content_only': True,
                'strict_quality': False,
                'slides': [{'layout': 'statement', 'title': '模拟开场', 'lead': '模拟核心判断',
                            'body': '必须保留的正文', 'basis': '模拟资料范围',
                            'items': [{'title': '第一项', 'body': '必须保留的条目'}]}]}
        with tempfile.TemporaryDirectory(prefix='hualang-v12-statement-') as directory:
            output = Path(directory) / 'statement.pptx'
            build_deck(spec, output)
            prs = Presentation(output)
            text = '\n'.join(shape.text for shape in prs.slides[0].shapes if shape.has_text_frame)
            self.assertIn('必须保留的正文', text)
            self.assertIn('必须保留的条目', text)


if __name__ == '__main__':
    unittest.main()
