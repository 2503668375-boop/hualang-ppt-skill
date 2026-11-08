#!/usr/bin/env python3
"""华朗智能表格：内容测量、整行续页与 python-pptx 原生绘制。

坐标、列宽和行高均使用华朗逻辑像素（1px = 9525EMU）。典型用法::

    chunks = plan_table(spec, width=1184, max_height=438, tier='read')
    for chunk in chunks:
        draw_table(page, chunk, x=48, y=200, tier='read')
    report = table_report(chunks)

规划阶段固定字号并按列宽估算换行；无法放入当前页时只按完整数据行
拆分，绝不通过自动缩字或拆分单元格来挤压内容。
"""
from __future__ import annotations

import math

from pptx.enum.text import MSO_AUTO_SIZE
from pptx.oxml.ns import qn
from pptx.util import Emu

from hualang_deck import (
    COLORS,
    TIERS,
    _cell_border,
    _no_style,
    _set_cell,
    est_lines,
)


EMU = 9525
CELL_INSET = 10
LINE_SPACING = 1.25
VERTICAL_PADDING = 12

VALID_TYPES = ('text', 'longtext', 'number', 'date', 'status')
VALID_STYLES = ('editorial', 'comparison', 'matrix', 'schedule', 'rubric', 'checklist')

_DEFAULT_WEIGHT = {
    'text': 1.25,
    'longtext': 2.10,
    'number': 0.75,
    'date': 0.90,
    'status': 1.00,
}
_DEFAULT_MIN_WIDTH = {
    'text': 64.0,
    'longtext': 88.0,
    'number': 56.0,
    'date': 76.0,
    'status': 68.0,
}
_ALIGNMENT = {
    'text': 'l',
    'longtext': 'l',
    'number': 'r',
    'date': 'c',
    'status': 'c',
}


def _text(value):
    """把单元格值稳定转换为文本；空值不显示为 ``None``。"""
    return '' if value is None else str(value)


def _validate_tier(tier):
    if tier not in TIERS:
        raise ValueError(f"未知排版档位“{tier}”，可选值为 read、near、far。")


def _normalise_columns(raw_columns):
    if isinstance(raw_columns, (str, bytes)) or raw_columns is None:
        raise ValueError('表格 columns 必须是列名或列定义组成的列表。')
    try:
        raw_columns = list(raw_columns)
    except TypeError as exc:
        raise ValueError('表格 columns 必须是可遍历的列定义。') from exc
    if not raw_columns:
        raise ValueError('表格至少需要一列。')
    if len(raw_columns) > 8:
        raise ValueError(f'表格最多支持 8 列，当前为 {len(raw_columns)} 列；请拆表或减少列数。')

    columns = []
    for index, raw in enumerate(raw_columns, 1):
        if isinstance(raw, str):
            raw = {'label': raw}
        if not isinstance(raw, dict):
            raise ValueError(f'第 {index} 列定义无效，请使用字符串或包含 label 的字典。')
        if 'label' not in raw:
            raise ValueError(f'第 {index} 列缺少 label。')
        kind = str(raw.get('type', 'text')).lower()
        if kind not in VALID_TYPES:
            raise ValueError(
                f"第 {index} 列类型“{kind}”无效，可选值为 text、longtext、number、date、status。"
            )
        try:
            weight = float(raw.get('weight', _DEFAULT_WEIGHT[kind]))
        except (TypeError, ValueError) as exc:
            raise ValueError(f'第 {index} 列 weight 必须是正数。') from exc
        if not math.isfinite(weight) or weight <= 0:
            raise ValueError(f'第 {index} 列 weight 必须是正数。')

        explicit_min = raw.get('min_width') is not None
        try:
            min_width = float(raw.get('min_width', _DEFAULT_MIN_WIDTH[kind]))
        except (TypeError, ValueError) as exc:
            raise ValueError(f'第 {index} 列 min_width 必须是正数。') from exc
        if not math.isfinite(min_width) or min_width <= 0:
            raise ValueError(f'第 {index} 列 min_width 必须是正数。')
        columns.append({
            'label': _text(raw['label']),
            'key': raw.get('key'),
            'type': kind,
            'weight': weight,
            'min_width': min_width,
            'explicit_min': explicit_min,
        })
    return columns


def _normalise_rows(raw_rows, columns):
    headers = [column['label'] for column in columns]
    keys = [column.get('key') or column['label'] for column in columns]
    if raw_rows is None:
        return []
    if isinstance(raw_rows, (str, bytes, dict)):
        raise ValueError('表格 rows 必须是由列表或字典数据行组成的列表。')
    try:
        raw_rows = list(raw_rows)
    except TypeError as exc:
        raise ValueError('表格 rows 必须是可遍历的数据行集合。') from exc

    rows = []
    for row_index, raw in enumerate(raw_rows):
        if isinstance(raw, dict):
            rows.append([_text(raw.get(key, raw.get(header, ''))) for key, header in zip(keys, headers)])
        elif isinstance(raw, (list, tuple)):
            if len(raw) != len(headers):
                raise ValueError(
                    f'数据第 {row_index + 1} 行有 {len(raw)} 个单元格，'
                    f'但表格定义为 {len(headers)} 列。'
                )
            rows.append([_text(value) for value in raw])
        else:
            raise ValueError(f'数据第 {row_index + 1} 行必须是列表或字典。')
    return rows


def _normalise_indices(raw, limit, label):
    if raw is None:
        return []
    if isinstance(raw, (str, bytes)):
        raise ValueError(f'{label} 必须是整数索引列表。')
    try:
        values = list(raw)
    except TypeError as exc:
        raise ValueError(f'{label} 必须是整数索引列表。') from exc
    result = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f'{label} 只能包含从 0 开始的整数索引。')
        if value < 0 or value >= limit:
            raise ValueError(f'{label} 索引 {value} 超出有效范围 0 至 {limit - 1}。')
        if value not in result:
            result.append(value)
    return result


def _line_units(value):
    """返回最长显式行的估算字宽单位，与 hualang_deck.est_lines 一致。"""
    longest = 0.0
    for line in _text(value).split('\n'):
        units = sum(1.0 if ord(char) > 0x2E80 else 0.55 for char in line)
        longest = max(longest, units)
    return longest


def _allocate_widths(columns, rows, width, body_size):
    """按类型、权重和实际内容分配宽度，同时遵守显式最小列宽。"""
    minima = [column['min_width'] for column in columns]
    minimum_total = sum(minima)
    if minimum_total > width + 1e-6:
        if any(column['explicit_min'] for column in columns):
            raise ValueError(
                f'列最小宽度合计为 {minimum_total:.1f}px，超过表格宽度 {width:.1f}px。'
            )
        # 默认最小值只是排版偏好；极窄表格中同比收缩，并在行高中真实反映换行。
        scale = width / minimum_total
        widths = [value * scale for value in minima]
        return widths

    scores = []
    for column_index, column in enumerate(columns):
        content = [column['label']] + [row[column_index] for row in rows]
        units = max((_line_units(value) for value in content), default=0.0)
        # 平方根避免个别长文垄断整表；字号参与计算，保证远距档不会维持拥挤短列。
        content_factor = math.sqrt(max(4.0, min(units, 64.0)))
        scores.append(column['weight'] * content_factor * math.sqrt(body_size / 19.0))

    widths = list(minima)
    remaining = width - minimum_total
    score_total = sum(scores)
    for index, score in enumerate(scores):
        widths[index] += remaining * score / score_total
    # 消除浮点求和误差，确保调用方可直接把 widths 写入表格列宽。
    widths[-1] += width - sum(widths)
    return widths


def _measure_row(values, widths, font_size, minimum_height):
    lines = 1
    for value, column_width in zip(values, widths):
        usable_width = max(1.0, column_width - 2 * CELL_INSET)
        lines = max(lines, est_lines(value, usable_width, font_size))
    measured = math.ceil(lines * font_size * LINE_SPACING + VERTICAL_PADDING)
    return float(max(minimum_height, measured))


def plan_table(spec, width, max_height, tier='read'):
    """把表格规格规划为一页或多页原生表格 chunk。

    ``spec`` 支持 columns、rows、style、focus_columns、focus_rows、total_row、
    caption 和 source。数据行索引均为 0 基；``total_row=True`` 表示最后一行
    是合计行。返回 chunk 的 ``start``/``end`` 是原数据中的左闭右开索引，
    ``focus_rows`` 则转换为当前 chunk 内的数据行索引。

    每页重复表头，列宽合计等于 ``width``，``row_heights`` 包含表头且高度合计
    不超过 ``max_height``。单行连同表头仍无法容纳时抛出中文 ``ValueError``。
    """
    _validate_tier(tier)
    if not isinstance(spec, dict):
        raise ValueError('表格 spec 必须是字典。')
    try:
        width = float(width)
        max_height = float(max_height)
    except (TypeError, ValueError) as exc:
        raise ValueError('表格 width 和 max_height 必须是正数。') from exc
    if not math.isfinite(width) or width <= 0:
        raise ValueError('表格 width 必须是正数。')
    if not math.isfinite(max_height) or max_height <= 0:
        raise ValueError('表格 max_height 必须是正数。')

    columns = _normalise_columns(spec.get('columns'))
    headers = [column['label'] for column in columns]
    types = [column['type'] for column in columns]
    rows = _normalise_rows(spec.get('rows', []), columns)

    style = spec.get('style', 'editorial')
    if style not in VALID_STYLES:
        raise ValueError(f"未知表格样式“{style}”，可选值为 {', '.join(VALID_STYLES)}。")
    focus_columns = _normalise_indices(spec.get('focus_columns', []), len(columns), 'focus_columns')
    global_focus_rows = _normalise_indices(spec.get('focus_rows', []), len(rows), 'focus_rows')
    total_requested = bool(spec.get('total_row', False))
    if total_requested and not rows:
        raise ValueError('total_row=True 时，rows 的最后一行必须是合计行，不能为空表。')

    body_size = TIERS[tier]['table']
    header_size = max(TIERS[tier]['label'], {'read': 17, 'near': 21, 'far': 26}[tier])
    widths = _allocate_widths(columns, rows, width, body_size)
    header_height = _measure_row(headers, widths, header_size, TIERS[tier]['head_row'])
    if header_height > max_height + 1e-6:
        raise ValueError(
            f'表头按内容换行后需要 {header_height:.1f}px，超过可用高度 {max_height:.1f}px。'
        )
    row_heights = [
        _measure_row(row, widths, body_size, TIERS[tier]['row']) for row in rows
    ]

    # 先验证每一行，再贪心组页；每页至少保留一个完整数据行（空表除外）。
    for row_index, row_height in enumerate(row_heights):
        required = header_height + row_height
        if required > max_height + 1e-6:
            raise ValueError(
                f'数据第 {row_index + 1} 行换行后过高：连同表头需要 {required:.1f}px，'
                f'超过单页可用高度 {max_height:.1f}px；请精简内容或增大表格高度。'
            )

    groups = []
    if not rows:
        groups.append((0, 0, [], []))
    else:
        start = 0
        current_rows = []
        current_heights = []
        used = header_height
        for row_index, (row, row_height) in enumerate(zip(rows, row_heights)):
            if current_rows and used + row_height > max_height + 1e-6:
                groups.append((start, row_index, current_rows, current_heights))
                start = row_index
                current_rows = []
                current_heights = []
                used = header_height
            current_rows.append(row)
            current_heights.append(row_height)
            used += row_height
        groups.append((start, len(rows), current_rows, current_heights))

    chunks = []
    last_page = len(groups) - 1
    for page_index, (start, end, page_rows, body_heights) in enumerate(groups):
        heights = [header_height] + list(body_heights)
        chunk = {
            'headers': list(headers),
            'rows': [list(row) for row in page_rows],
            'types': list(types),
            'widths': list(widths),
            'row_heights': heights,
            'height': float(sum(heights)),
            'start': start,
            'end': end,
            'style': style,
            'focus_columns': list(focus_columns),
            'focus_rows': sorted(
                index - start for index in global_focus_rows if start <= index < end
            ),
            'total_row': total_requested and page_index == last_page,
            'continued': page_index > 0,
            'continuation': page_index < last_page,
            # 供绘制与构建报告使用，不改变上层 spec。
            'tier': tier,
            'min_font_px': min(body_size, header_size),
            'caption': spec.get('caption'),
            'source': spec.get('source'),
        }
        chunks.append(chunk)
    return chunks


def _status_color(value):
    """状态文本可着色，但原文始终保留，颜色不是唯一的信息载体。"""
    text = _text(value).strip().lower()
    negative = ('未通过', '未达成', '不合格', '延期', '逾期', '风险', '失败', '落后',
                'blocked', 'failed', 'late', 'overdue', 'risk')
    warning = ('待改进', '需关注', '进行中', '待完成', '部分', '预警', 'pending',
               'warning', 'progress', 'partial')
    positive = ('完成', '达成', '通过', '合格', '优秀', '良好', '正常', '就绪',
                'done', 'complete', 'passed', 'ready', 'on track')
    if any(token in text for token in negative):
        return COLORS['red']
    if any(token in text for token in warning):
        return '8A641C'
    if any(token in text for token in positive):
        return '2E6B57'
    return COLORS['purple']


def _cell_fill(style, row_index, column_index, is_focus_row, is_focus_column, is_total):
    if is_total:
        return 'E9E1F1'
    if is_focus_row:
        return 'F3EDF7'
    if is_focus_column:
        return 'EEE7F4'
    if column_index == 0:
        return 'F4F1F7'
    if style in ('comparison', 'matrix', 'rubric') and row_index % 2:
        return 'F7F5FA'
    return COLORS['paper'] if row_index % 2 == 0 else 'FAF9FC'


def draw_table(page, chunk, x=48, y=200, tier='read'):
    """把 ``plan_table`` 的 chunk 绘制为原生、可编辑的 PowerPoint 表格。

    文本/长文左对齐，数字右对齐，日期和状态居中，表头跟随列类型。正文以
    横线为主，matrix 增加轻竖线；焦点列使用浅紫底与金边，焦点行和合计行
    另有浅色强调。函数不合并/拆分单元格，也不启用自动缩字。
    """
    _validate_tier(tier)
    headers = list(chunk['headers'])
    rows = list(chunk['rows'])
    types = list(chunk['types'])
    widths = list(chunk['widths'])
    heights = list(chunk['row_heights'])
    if not headers or len(headers) != len(types) or len(headers) != len(widths):
        raise ValueError('表格 chunk 的 headers、types、widths 数量必须一致且不能为空。')
    if len(heights) != len(rows) + 1:
        raise ValueError('表格 chunk 的 row_heights 必须包含表头及每个数据行。')
    if any(len(row) != len(headers) for row in rows):
        raise ValueError('表格 chunk 中存在列数不一致的数据行。')

    slide = getattr(page, 'slide', page)
    shape = slide.shapes.add_table(
        len(rows) + 1,
        len(headers),
        Emu(int(float(x) * EMU)),
        Emu(int(float(y) * EMU)),
        Emu(int(sum(widths) * EMU)),
        Emu(int(sum(heights) * EMU)),
    )
    shape.name = 'table-continued' if chunk.get('continued') else 'table'
    table = shape.table
    _no_style(table)
    # 保留表头语义，但明确关闭默认条纹、首末列和合计行样式。
    table._tbl.tblPr.set('firstRow', '1')
    for attr in ('bandRow', 'firstCol', 'lastRow', 'lastCol'):
        table._tbl.tblPr.set(attr, '0')
    if table._tbl.tblPr.find(qn('a:tableStyleId')) is not None:
        raise ValueError('表格默认样式未清除，无法保证自定义配色。')

    for column_index, column_width in enumerate(widths):
        table.columns[column_index].width = Emu(int(float(column_width) * EMU))
    for row_index, row_height in enumerate(heights):
        table.rows[row_index].height = Emu(int(float(row_height) * EMU))

    body_size = TIERS[tier]['table']
    header_size = max(TIERS[tier]['label'], {'read': 17, 'near': 21, 'far': 26}[tier])
    style = chunk.get('style', 'editorial')
    focus_columns = set(chunk.get('focus_columns', []))
    focus_rows = set(chunk.get('focus_rows', []))
    header_fill = COLORS['pale'] if style == 'matrix' else COLORS['purple']
    header_color = COLORS['purple'] if style == 'matrix' else COLORS['white']

    for column_index, (header, kind) in enumerate(zip(headers, types)):
        cell = table.cell(0, column_index)
        _set_cell(
            cell, _text(header), header_size, header_color, bold=True,
            align=_ALIGNMENT[kind], fill=header_fill, inset=CELL_INSET,
            line_spacing=LINE_SPACING,
        )
        cell.text_frame.auto_size = MSO_AUTO_SIZE.NONE
        if column_index in focus_columns:
            sides = ('B', 'R', 'L')  # _cell_border 逐个前插，倒序传入以符合 OOXML 顺序
            _cell_border(cell, COLORS['gold'], 1.1, sides=sides)
        else:
            _cell_border(cell, COLORS['gold'], 1.2, sides=('B',))

    for row_index, row in enumerate(rows):
        is_focus_row = row_index in focus_rows
        is_total = bool(chunk.get('total_row')) and row_index == len(rows) - 1
        # 跨页交替底纹跟随原数据行，而不是每页重新从白色开始。
        source_row_index = int(chunk.get('start', 0)) + row_index
        for column_index, (value, kind) in enumerate(zip(row, types)):
            is_focus_column = column_index in focus_columns
            color = _status_color(value) if kind == 'status' else COLORS['ink']
            cell = table.cell(row_index + 1, column_index)
            _set_cell(
                cell, _text(value), body_size, color,
                bold=is_total or is_focus_row or kind == 'status',
                align=_ALIGNMENT[kind],
                fill=_cell_fill(
                    style, source_row_index, column_index,
                    is_focus_row, is_focus_column, is_total,
                ),
                inset=CELL_INSET,
                line_spacing=LINE_SPACING,
            )
            cell.text_frame.auto_size = MSO_AUTO_SIZE.NONE

            desired_sides = ['B']
            border_color = COLORS['line']
            border_width = 0.9
            if style == 'matrix' and column_index < len(headers) - 1:
                desired_sides.append('R')
            if is_focus_column:
                desired_sides.extend(['L', 'R'])
                border_color = COLORS['gold']
                border_width = 1.0
            if is_total:
                desired_sides.append('T')
                border_color = COLORS['gold']
                border_width = 1.1
            # 去重并倒序前插，最终 XML 顺序为 L、R、T、B。
            side_order = {'L': 0, 'R': 1, 'T': 2, 'B': 3}
            desired_sides = sorted(set(desired_sides), key=side_order.__getitem__)
            _cell_border(
                cell, border_color, border_width,
                sides=tuple(reversed(desired_sides)),
            )
    return shape


def table_report(chunks):
    """汇总规划结果，供构建器写入页数、行数、列数、最小字号和提醒。"""
    chunks = list(chunks)
    if not chunks:
        return {
            'page_count': 0,
            'row_count': 0,
            'column_count': 0,
            'min_font_px': 0,
            'warnings': [],
        }

    font_sizes = []
    for chunk in chunks:
        if 'min_font_px' in chunk:
            font_sizes.append(chunk['min_font_px'])
        else:
            tier = chunk.get('tier', 'read')
            _validate_tier(tier)
            font_sizes.append(min(TIERS[tier]['table'], TIERS[tier]['label']))

    warnings = []
    if len(chunks) > 1:
        warnings.append(f'表格已续排为 {len(chunks)} 页，每页均重复表头；请保持各页位置一致。')
    narrow = [
        width for chunk in chunks for width in chunk.get('widths', [])
        if width < 40
    ]
    if narrow:
        warnings.append('存在窄于 40px 的列；建议减少列数或加宽表格，避免过度换行。')
    return {
        'page_count': len(chunks),
        'row_count': sum(len(chunk.get('rows', [])) for chunk in chunks),
        'column_count': max((len(chunk.get('headers', [])) for chunk in chunks), default=0),
        'min_font_px': min(font_sizes),
        'warnings': warnings,
    }


__all__ = ['plan_table', 'draw_table', 'table_report']
