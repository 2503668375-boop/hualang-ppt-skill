#!/usr/bin/env python3
"""hualang_tables 的离线单元测试；只依赖 python-pptx，不需要 LibreOffice。"""
import unittest
from io import BytesIO
from types import SimpleNamespace

from pptx import Presentation
from pptx.enum.text import PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu

from hualang_deck import EMU, validate_order
from hualang_tables import draw_table, plan_table, table_report


class TablePlanningTests(unittest.TestCase):
    def test_types_content_widths_and_width_sum(self):
        spec = {
            'columns': [
                {'label': '课程说明', 'type': 'longtext'},
                {'label': '得分', 'type': 'number'},
                {'label': '日期', 'type': 'date'},
                {'label': '状态', 'type': 'status'},
            ],
            'rows': [[
                '项目化学习成果与课堂观察记录的综合说明', '96.5', '2026-11-08', '已完成',
            ]],
        }
        chunks = plan_table(spec, width=900, max_height=300)
        self.assertEqual(len(chunks), 1)
        chunk = chunks[0]
        self.assertEqual(chunk['types'], ['longtext', 'number', 'date', 'status'])
        self.assertAlmostEqual(sum(chunk['widths']), 900, places=6)
        self.assertGreater(chunk['widths'][0], chunk['widths'][1])
        self.assertEqual(chunk['height'], sum(chunk['row_heights']))
        self.assertLessEqual(chunk['height'], 300)
        self.assertFalse(chunk['continued'])
        self.assertFalse(chunk['continuation'])

    def test_long_table_splits_on_whole_rows_and_repeats_headers(self):
        spec = {
            'columns': ['项目', {'label': '人数', 'type': 'number'}],
            'rows': [[f'第 {index + 1} 项课程内容', index * 3] for index in range(24)],
        }
        chunks = plan_table(spec, width=700, max_height=190)
        self.assertGreater(len(chunks), 1)
        flattened = []
        for index, chunk in enumerate(chunks):
            self.assertEqual(chunk['headers'], ['项目', '人数'])
            self.assertEqual(len(chunk['row_heights']), len(chunk['rows']) + 1)
            self.assertLessEqual(chunk['height'], 190 + 1e-6)
            self.assertEqual(chunk['end'] - chunk['start'], len(chunk['rows']))
            self.assertEqual(chunk['continued'], index > 0)
            self.assertEqual(chunk['continuation'], index < len(chunks) - 1)
            flattened.extend(chunk['rows'])
        self.assertEqual(flattened, [[f'第 {i + 1} 项课程内容', str(i * 3)]
                                     for i in range(24)])
        self.assertEqual([(c['start'], c['end']) for c in chunks],
                         [(0, 3), (3, 6), (6, 9), (9, 12), (12, 15),
                          (15, 18), (18, 21), (21, 24)])

    def test_focus_rows_are_mapped_to_each_chunk(self):
        spec = {
            'columns': ['项目', '结果'],
            'rows': [[f'项目{i}', f'结果{i}'] for i in range(12)],
            'focus_columns': [1],
            'focus_rows': [1, 4, 8, 11],
        }
        chunks = plan_table(spec, width=600, max_height=190)
        for chunk in chunks:
            expected = [index - chunk['start'] for index in (1, 4, 8, 11)
                        if chunk['start'] <= index < chunk['end']]
            self.assertEqual(chunk['focus_rows'], expected)
            self.assertTrue(all(0 <= index < len(chunk['rows'])
                                for index in chunk['focus_rows']))
            self.assertEqual(chunk['focus_columns'], [1])
        self.assertEqual([row for chunk in chunks for row in chunk['focus_rows']],
                         [1, 1, 2, 2])

    def test_dict_rows_follow_column_labels(self):
        spec = {
            'columns': [
                '课程',
                {'label': '课时', 'type': 'number'},
                {'label': '日期', 'type': 'date'},
            ],
            'rows': [
                {'课程': '科学探究', '课时': 4, '日期': '2026-11-08'},
                {'课程': '阅读表达', '课时': 2, '日期': '2026-11-09'},
            ],
        }
        chunk = plan_table(spec, width=720, max_height=240)[0]
        self.assertEqual(chunk['rows'], [
            ['科学探究', '4', '2026-11-08'],
            ['阅读表达', '2', '2026-11-09'],
        ])

    def test_dict_rows_prefer_explicit_column_keys(self):
        spec = {
            'columns': [
                {'key': 'course', 'label': '课程'},
                {'key': 'sessions', 'label': '课时', 'type': 'number'},
            ],
            'rows': [{'course': '阅读表达', 'sessions': 2, '课程': '错误回退值'}],
        }
        chunk = plan_table(spec, width=600, max_height=180)[0]
        self.assertEqual(chunk['rows'], [['阅读表达', '2']])

    def test_total_row_marker_is_only_on_last_page(self):
        spec = {
            'columns': ['项目', {'label': '数量', 'type': 'number'}],
            'rows': [[f'项目{i}', i] for i in range(1, 8)] + [['合计', 28]],
            'total_row': True,
        }
        chunks = plan_table(spec, width=600, max_height=180)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(not chunk['total_row'] for chunk in chunks[:-1]))
        self.assertTrue(chunks[-1]['total_row'])
        self.assertEqual(chunks[-1]['rows'][-1], ['合计', '28'])

    def test_header_height_includes_wrapping(self):
        spec = {
            'columns': ['非常非常长的课程与教学评价维度表头', '评价结果'],
            'rows': [['短内容', '完成']],
        }
        chunk = plan_table(spec, width=180, max_height=400)[0]
        self.assertGreater(chunk['row_heights'][0], 38)
        self.assertLessEqual(chunk['height'], 400)

    def test_too_many_columns_raise_chinese_error(self):
        spec = {'columns': [f'列{i}' for i in range(9)], 'rows': []}
        with self.assertRaisesRegex(ValueError, '最多支持 8 列'):
            plan_table(spec, width=900, max_height=300)

    def test_single_oversized_row_raises_instead_of_shrinking(self):
        spec = {
            'columns': [{'label': '说明', 'type': 'longtext'}],
            'rows': [['这是一段用于验证单行过高时明确报错的长文本。' * 12]],
        }
        with self.assertRaisesRegex(ValueError, '数据第 1 行'):
            plan_table(spec, width=180, max_height=120)

    def test_invalid_indices_and_row_shape_are_reported(self):
        with self.assertRaisesRegex(ValueError, 'focus_rows 索引 2 超出'):
            plan_table({'columns': ['项目'], 'rows': [['甲']], 'focus_rows': [2]}, 400, 200)
        with self.assertRaisesRegex(ValueError, '数据第 1 行有 2 个单元格'):
            plan_table({'columns': ['项目'], 'rows': [['甲', '乙']]}, 400, 200)

    def test_report_counts_rows_without_duplicated_headers(self):
        spec = {
            'columns': ['项目', '结果'],
            'rows': [[f'项目{i}', '完成'] for i in range(10)],
            'caption': '课堂观察',
            'source': '模拟资料',
        }
        chunks = plan_table(spec, width=600, max_height=180, tier='near')
        report = table_report(chunks)
        self.assertEqual(report['page_count'], len(chunks))
        self.assertEqual(report['row_count'], 10)
        self.assertEqual(report['column_count'], 2)
        self.assertEqual(report['min_font_px'], 21)
        self.assertIsInstance(report['warnings'], list)
        self.assertEqual(chunks[0]['caption'], '课堂观察')
        self.assertEqual(chunks[0]['source'], '模拟资料')


class NativeTableDrawingTests(unittest.TestCase):
    def setUp(self):
        self.prs = Presentation()
        self.slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self.page = SimpleNamespace(slide=self.slide)

    def test_native_table_alignment_dimensions_and_header_semantics(self):
        spec = {
            'columns': [
                '课程',
                {'label': '得分', 'type': 'number'},
                {'label': '日期', 'type': 'date'},
                {'label': '状态', 'type': 'status'},
            ],
            'rows': [
                ['科学探究', 96, '2026-11-08', '已完成'],
                ['阅读表达', 88, '2026-11-09', '需关注'],
                ['艺术实践', 91, '2026-11-10', '延期'],
                ['合计', 275, '', ''],
            ],
            'style': 'matrix',
            'focus_columns': [1],
            'focus_rows': [1],
            'total_row': True,
        }
        chunk = plan_table(spec, width=900, max_height=350)[0]
        shape = draw_table(self.page, chunk, x=48, y=200)
        self.assertTrue(shape.has_table)
        table = shape.table
        self.assertEqual(len(table.rows), 5)
        self.assertEqual(len(table.columns), 4)
        self.assertEqual(table._tbl.tblPr.get('firstRow'), '1')
        self.assertEqual(table._tbl.tblPr.get('bandRow'), '0')
        self.assertIsNone(table._tbl.tblPr.find(qn('a:tableStyleId')))

        self.assertEqual(table.cell(0, 1).text_frame.paragraphs[0].alignment, PP_ALIGN.RIGHT)
        self.assertEqual(table.cell(1, 0).text_frame.paragraphs[0].alignment, PP_ALIGN.LEFT)
        self.assertEqual(table.cell(1, 1).text_frame.paragraphs[0].alignment, PP_ALIGN.RIGHT)
        self.assertEqual(table.cell(1, 2).text_frame.paragraphs[0].alignment, PP_ALIGN.CENTER)
        self.assertEqual(table.cell(1, 3).text_frame.paragraphs[0].alignment, PP_ALIGN.CENTER)
        self.assertEqual(table.cell(1, 3).text, '已完成')
        self.assertEqual(table.cell(3, 3).text, '延期')
        self.assertTrue(table.cell(4, 0).text_frame.paragraphs[0].runs[0].font.bold)
        self.assertTrue(table.cell(2, 0).text_frame.paragraphs[0].runs[0].font.bold)

        for index, width in enumerate(chunk['widths']):
            self.assertEqual(table.columns[index].width, Emu(int(width * EMU)))
        for index, height in enumerate(chunk['row_heights']):
            self.assertEqual(table.rows[index].height, Emu(int(height * EMU)))
        for row in table.rows:
            for cell in row.cells:
                self.assertFalse(cell.is_merge_origin)
                self.assertFalse(cell.is_spanned)
        self.assertEqual(validate_order(self.prs), [])

    def test_continuation_shape_remains_editable(self):
        spec = {
            'columns': ['项目', '结果'],
            'rows': [[f'项目{i}', '进行中'] for i in range(8)],
        }
        chunks = plan_table(spec, width=600, max_height=180)
        shape = draw_table(self.page, chunks[1])
        self.assertEqual(shape.name, 'table-continued')
        self.assertTrue(shape.has_table)
        self.assertEqual(shape.table.cell(0, 0).text, '项目')
        self.assertEqual(validate_order(self.prs), [])

    def test_saved_table_has_explicit_unused_edges_and_preserves_semantic_borders(self):
        for style in ('editorial', 'comparison', 'matrix'):
            with self.subTest(style=style):
                chunk = plan_table({
                    'columns': ['项目', '数量'],
                    'rows': [['阅读', 3], ['合计', 3]],
                    'style': style,
                    'focus_columns': [1],
                    'total_row': True,
                }, width=600, max_height=250)[0]
                shape = draw_table(self.page, chunk)
                stream = BytesIO()
                self.prs.save(stream)
                saved = Presentation(BytesIO(stream.getvalue()))
                table = saved.slides[0].shapes[len(self.slide.shapes) - 1].table
                for ri, row in enumerate(table.rows):
                    for ci, cell in enumerate(row.cells):
                        visible = {'B'}
                        if ci == 1:
                            visible.update(('L', 'R'))
                        if ri > 0 and style == 'matrix' and ci == 0:
                            visible.add('R')
                        if ri == 2:
                            visible.add('T')
                        tcpr = cell._tc.get_or_add_tcPr()
                        edges = [node.tag for node in tcpr
                                 if node.tag in {qn('a:ln' + s) for s in 'LRTB'}]
                        self.assertEqual(edges, [qn('a:ln' + s) for s in 'LRTB'])
                        for side in 'LRTB':
                            line = tcpr.find(qn('a:ln' + side))
                            if side in visible:
                                self.assertIsNotNone(line.find(qn('a:solidFill')))
                                self.assertIsNone(line.find(qn('a:noFill')))
                            else:
                                self.assertIsNotNone(line.find(qn('a:noFill')))
                                self.assertIsNone(line.find(qn('a:solidFill')))
                self.assertEqual(validate_order(saved), [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
