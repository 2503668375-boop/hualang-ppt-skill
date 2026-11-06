#!/usr/bin/env python3
"""Measure a few text-boundary issues in an existing exported PDF.

This is an aid to visual review, not a layout/aesthetic pass. It uses PDF glyph
boxes and filled rectangles; it does not render, OCR, create or edit slides.
pdfplumber is optional and is never installed by this script.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import statistics
import sys

try:
    import pdfplumber
except ImportError:
    pdfplumber = None


@dataclass(frozen=True)
class Tolerances:
    """Detection tolerances in PDF points/fractions, not design standards."""

    boundary_pt: float = 1.0
    line_alignment_pt: float = 2.0
    separate_line_gap_em: float = 2.0
    minimum_panel_width_pt: float = 36.0
    minimum_panel_height_pt: float = 18.0
    background_area_fraction: float = 0.80
    background_width_fraction: float = 0.90
    background_height_fraction: float = 0.75
    near_edge_fraction: float = 0.04
    white_color_tolerance: float = 0.025


LIMITATIONS = [
    '只报告PDF字形包围框与可识别填色矩形的几何关系，不判断审美、主次、内容含义或场景是否适合。',
    'no_measured_issue仅表示本工具未测得指定问题，不能称为排版通过；仍须查看最终实际页面。',
    'PDF字形包围框受字体度量影响，不等同于每个可见墨迹的精确轮廓；裁切、遮挡及隐藏文字的可见性不在判断范围内。',
    '不做OCR；扫描页、文字转曲、图片内文字、无法提取的字形以及非横向文字不能可靠检查。无可测字形页列入unmeasured_pages，需人工查看，不计作几何缺陷。',
    '面板仅取有色填充矩形；曲线、图片、未识别的颜色模式，以及被规则排除的大背景和窄色条不作为内容面板。',
    '仅在一行实际字形从面板内部开始、横向位于该面板内且下沿越过其底边时提示；整行已落在面板外、跨列或复杂嵌套可能漏检。',
    '不推断文本属于哪个对象，不把一般对象重叠判为硬错；发现项均需结合实际页面人工复核。',
]


def _number(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


def _box(obj):
    values = [obj.get(k) for k in ('x0', 'top', 'x1', 'bottom')]
    if not all(_number(v) for v in values):
        return None
    x0, top, x1, bottom = map(float, values)
    return (x0, top, x1, bottom) if x1 > x0 and bottom > top else None


def _rounded(box):
    return [round(v, 3) for v in box] if box is not None else None


def _rgb(color):
    if _number(color):
        return (float(color),) * 3
    if not isinstance(color, (tuple, list)) or not all(_number(v) for v in color):
        return None
    if len(color) == 1:
        return (float(color[0]),) * 3
    if len(color) == 3:
        return tuple(map(float, color))
    if len(color) == 4:
        c, m, y, k = map(float, color)
        return tuple(1 - min(1.0, v + k) for v in (c, m, y))
    return None


def _content_panels(page, bounds, tolerance):
    """Exclude page backgrounds and thin decorations before measuring text."""
    px0, ptop, px1, pbottom = bounds
    pw, ph = px1-px0, pbottom-ptop
    near = max(tolerance.boundary_pt, min(pw, ph)*tolerance.near_edge_fraction)
    result = []
    seen = set()
    for rect in page.rects:
        box = _box(rect)
        rgb = _rgb(rect.get('non_stroking_color'))
        if not rect.get('fill') or box is None or rgb is None:
            continue
        if max(abs(1-channel) for channel in rgb) <= tolerance.white_color_tolerance:
            continue
        x0, top, x1, bottom = box
        width, height = x1-x0, bottom-top
        if width < tolerance.minimum_panel_width_pt or height < tolerance.minimum_panel_height_pt:
            continue
        if width*height >= pw*ph*tolerance.background_area_fraction:
            continue
        edge_count = sum((abs(x0-px0) <= near, abs(top-ptop) <= near,
                          abs(x1-px1) <= near, abs(bottom-pbottom) <= near))
        if (width >= pw*tolerance.background_width_fraction
                and height >= ph*tolerance.background_height_fraction
                and edge_count >= 3):
            continue
        key = tuple(round(v, 3) for v in box)
        if key not in seen:
            result.append(box)
            seen.add(key)
    return sorted(result, key=lambda b: (b[2]-b[0])*(b[3]-b[1]))


def _text_lines(page, tolerance):
    """Group ordinary horizontal glyphs, splitting widely separated columns."""
    chars = []
    ignored = 0
    for char in page.chars:
        box = _box(char)
        if not str(char.get('text', '')).strip():
            continue
        if box is None or char.get('upright') is False:
            ignored += 1
            continue
        chars.append((char, box))
    rows = []
    for char, box in sorted(chars, key=lambda item: (item[1][3], item[1][0])):
        # Bottom-edge alignment is deliberately conservative for mixed-size
        # equations/superscripts; those may form several measured fragments.
        candidates = [row for row in rows
                      if abs(statistics.median(b[3] for _, b in row)-box[3])
                      <= tolerance.line_alignment_pt]
        if candidates:
            min(candidates, key=lambda row: abs(statistics.median(b[3] for _, b in row)-box[3])).append((char, box))
        else:
            rows.append([(char, box)])
    lines = []
    for row in rows:
        row.sort(key=lambda item: item[1][0])
        sizes = [float(c.get('size', b[3]-b[1])) for c, b in row
                 if _number(c.get('size', b[3]-b[1]))]
        em = statistics.median(sizes) if sizes else 12.0
        gap_limit = max(12.0, em*tolerance.separate_line_gap_em)
        fragments = [[]]
        previous_right = None
        for item in row:
            if previous_right is not None and item[1][0]-previous_right > gap_limit:
                fragments.append([])
            fragments[-1].append(item)
            previous_right = max(previous_right or item[1][2], item[1][2])
        for fragment in fragments:
            boxes = [b for _, b in fragment]
            bbox = (min(b[0] for b in boxes), min(b[1] for b in boxes),
                    max(b[2] for b in boxes), max(b[3] for b in boxes))
            # Preserve readable word gaps in Latin text without estimating text
            # extent from character counts.
            text = ''
            previous = None
            for char, box in fragment:
                if previous is not None and box[0]-previous > max(1.0, em*.15):
                    text += ' '
                text += str(char.get('text', ''))
                previous = box[2]
            lines.append({'text': text, 'bbox': bbox})
    return sorted(lines, key=lambda line: (line['bbox'][1], line['bbox'][0])), ignored


def audit(pdf_path, tolerance_pt=1.0, line_tolerance_pt=2.0):
    tolerance = Tolerances(boundary_pt=tolerance_pt, line_alignment_pt=line_tolerance_pt)
    result = {'parsed': False, 'status': 'review_required', 'findings': [],
              'unmeasured_pages': [],
              'limitations': list(LIMITATIONS), 'tolerances': asdict(tolerance),
              'coordinate_system': 'PDF points: [left, top, right, bottom], origin at page top-left',
              'page_summaries': [], 'errors': []}
    if not all(_number(v) and v >= 0 for v in (tolerance_pt, line_tolerance_pt)):
        result['errors'].append({'code': 'invalid_tolerance', 'message': '容差须为非负有限数，单位为PDF点。'})
        return result
    if pdfplumber is None:
        result['errors'].append({'code': 'dependency_missing', 'message': '缺少可选依赖pdfplumber，未读取PDF；本脚本不会自动安装，请使用已有该依赖的运行环境。'})
        return result
    try:
        with pdfplumber.open(Path(pdf_path)) as pdf:
            for page_number, page in enumerate(pdf.pages, 1):
                bounds = tuple(map(float, page.bbox))
                panels = _content_panels(page, bounds, tolerance)
                lines, ignored = _text_lines(page, tolerance)
                result['page_summaries'].append({'page': page_number, 'page_bbox': _rounded(bounds),
                                                'measured_lines': len(lines), 'content_panels': len(panels),
                                                'ignored_glyphs': ignored})
                if not lines:
                    result['unmeasured_pages'].append(page_number)
                for line in lines:
                    box = line['bbox']
                    x0, top, x1, bottom = box
                    if (x0 < bounds[0]-tolerance.boundary_pt
                            or top < bounds[1]-tolerance.boundary_pt
                            or x1 > bounds[2]+tolerance.boundary_pt
                            or bottom > bounds[3]+tolerance.boundary_pt):
                        result['findings'].append({'page': page_number, 'code': 'text_outside_page',
                                                   'text': line['text'], 'line_bbox': _rounded(box),
                                                   'panel_bbox': None})
                    for panel in panels:
                        left, panel_top, right, panel_bottom = panel
                        if (x0 >= left-tolerance.boundary_pt and x1 <= right+tolerance.boundary_pt
                                and top >= panel_top-tolerance.boundary_pt
                                and top < panel_bottom-tolerance.boundary_pt
                                and bottom > panel_bottom+tolerance.boundary_pt):
                            result['findings'].append({'page': page_number, 'code': 'text_crosses_panel',
                                                       'text': line['text'], 'line_bbox': _rounded(box),
                                                       'panel_bbox': _rounded(panel)})
                            break  # The smallest matching panel is enough to review this line.
            result['parsed'] = True
    except Exception as exc:
        result['errors'].append({'code': 'pdf_read_error', 'message': f'未能完整读取PDF：{type(exc).__name__}: {exc}'})
        return result
    result['status'] = ('review_required' if result['findings'] or result['unmeasured_pages']
                        else 'no_measured_issue')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf', type=Path, help='已经导出的PDF；不生成或修改PPT')
    parser.add_argument('--output', type=Path, help='另存JSON结果')
    parser.add_argument('--tolerance', type=float, default=1.0, help='边界测量容差，PDF点；默认1，并非审美标准')
    parser.add_argument('--line-tolerance', type=float, default=2.0, help='字形行对齐容差，PDF点；默认2')
    args = parser.parse_args(argv)
    if args.output:
        same_path = args.output.resolve() == args.pdf.resolve()
        same_file = (args.output.exists() and args.pdf.exists()
                     and args.output.samefile(args.pdf))
        if same_path or same_file:
            parser.error('--output不能与输入PDF相同；拒绝覆盖原文件。')
    result = audit(args.pdf, args.tolerance, args.line_tolerance)
    encoded = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded+'\n', encoding='utf-8')
    print(encoded)
    # 0 is only "no measured issue" for this limited probe, never a layout pass.
    return 2 if not result['parsed'] else 1 if result['status'] == 'review_required' else 0


if __name__ == '__main__':
    sys.exit(main())
