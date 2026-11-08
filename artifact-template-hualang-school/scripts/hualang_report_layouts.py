#!/usr/bin/env python3
"""V12 内部汇报原生版式。坐标为 1280×720 逻辑像素。"""
from __future__ import annotations

import math

from hualang_deck import _rect, _textbox, _write, est_lines, text_height

REPORT_LAYOUTS = {
    'positioning', 'waterfall', 'trend', 'diagnostic',
    'targets', 'conversion', 'swimlane', 'decision',
}


def _error(index, message):
    raise ValueError(f'第 {index} 页 {message}')


def _list(slide, field, index, minimum=1, maximum=None):
    value = slide.get(field)
    if not isinstance(value, list) or len(value) < minimum:
        _error(index, f'{field} 必须是至少 {minimum} 项的非空列表；请补全内容或更换版式。')
    if maximum is not None and len(value) > maximum:
        _error(index, f'{field} 有 {len(value)} 项，当前版式最多 {maximum} 项；请拆成续页。')
    if any(not isinstance(item, dict) for item in value):
        _error(index, f'{field} 的每一项都必须是对象。')
    return value


def _number(value, index, path):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        _error(index, f'{path} 必须是有限数值，不能为 NaN、无穷、布尔值或字符串。')
    return float(value)


def _axis(slide, field, index, required=True):
    value = slide.get(field)
    if value is None and not required:
        return None
    if not isinstance(value, dict):
        _error(index, f'{field} 必须是包含 label/min/max/unit 的对象。')
    minimum = _number(value.get('min'), index, f'{field}.min')
    maximum = _number(value.get('max'), index, f'{field}.max')
    if maximum <= minimum:
        _error(index, f'{field}.max 必须大于 min；请修正坐标范围。')
    if not str(value.get('label', '')).strip():
        _error(index, f'{field}.label 不能为空。')
    return value


def _required(item, fields, index, path):
    for field in fields:
        if field not in item or not str(item.get(field, '')).strip():
            _error(index, f'{path}.{field} 不能为空；请补齐后再生成。')


def _finite_text_number(value, index, path):
    if isinstance(value, (int, float)):
        _number(value, index, path)


def validate_report_slide(slide, layout, index):
    """校验 V12 字段；任何缺失、空数组或非法数值都明确失败。"""
    if layout == 'positioning':
        x_axis = _axis(slide, 'x_axis', index)
        y_axis = _axis(slide, 'y_axis', index)
        points = _list(slide, 'points', index, 1, 8)
        for i, point in enumerate(points, 1):
            _required(point, ('label',), index, f'points[{i - 1}]')
            x = _number(point.get('x'), index, f'points[{i - 1}].x')
            y = _number(point.get('y'), index, f'points[{i - 1}].y')
            for field in ('display_x', 'display_y', 'label_dx', 'label_dy'):
                if field in point:
                    _finite_text_number(point[field], index, f'points[{i - 1}].{field}')
            if not x_axis['min'] <= x <= x_axis['max'] or not y_axis['min'] <= y <= y_axis['max']:
                _error(index, f'points[{i - 1}] 超出坐标轴范围；请调整数值或 min/max，不能裁切。')
        for field, axis in (('x_reference', x_axis), ('y_reference', y_axis)):
            if field in slide:
                reference = _number(slide[field], index, field)
                if not axis['min'] <= reference <= axis['max']:
                    _error(index, f'{field} 必须位于对应坐标轴范围内。')
    elif layout == 'waterfall':
        steps = _list(slide, 'steps', index, 2, 8)
        for i, step in enumerate(steps, 1):
            _required(step, ('label', 'kind'), index, f'steps[{i - 1}]')
            if step['kind'] not in ('start', 'delta', 'total'):
                _error(index, f'steps[{i - 1}].kind 仅支持 start / delta / total。')
            _number(step.get('value'), index, f'steps[{i - 1}].value')
            if 'display' in step:
                _finite_text_number(step['display'], index, f'steps[{i - 1}].display')
        if steps[0]['kind'] != 'start':
            _error(index, 'waterfall 首项必须为 start，以明确累计起点。')
        running = float(steps[0]['value'])
        for i, step in enumerate(steps[1:], 1):
            if step['kind'] == 'start':
                _error(index, f'steps[{i}] 不能再次使用 start；请拆成独立比较。')
            if step['kind'] == 'total':
                if not math.isclose(float(step['value']), running, rel_tol=1e-9, abs_tol=1e-9):
                    _error(index, f'steps[{i}] 合计 {step["value"]} 与累计值 {running:g} 不一致。')
            else:
                running += float(step['value'])
    elif layout == 'trend':
        categories = slide.get('categories')
        if not isinstance(categories, list) or not categories or len(categories) > 12:
            _error(index, 'categories 必须是 1–12 项的非空字符串列表。')
        if any(not isinstance(item, str) or not item.strip() for item in categories):
            _error(index, 'categories 的每一项都必须是非空字符串。')
        y_axis = _axis(slide, 'y_axis', index)
        series = _list(slide, 'series', index, 1, 4)
        for i, item in enumerate(series, 1):
            _required(item, ('label',), index, f'series[{i - 1}]')
            values = item.get('values')
            if not isinstance(values, list) or len(values) != len(categories):
                _error(index, f'series[{i - 1}].values 必须与 categories 等长且非空。')
            for j, value in enumerate(values):
                number = _number(value, index, f'series[{i - 1}].values[{j}]')
                if not y_axis['min'] <= number <= y_axis['max']:
                    _error(index, f'series[{i - 1}].values[{j}] 超出 y_axis 范围；请调整范围。')
            displays = item.get('displays')
            if displays is not None and (not isinstance(displays, list) or len(displays) != len(categories)):
                _error(index, f'series[{i - 1}].displays 必须与 categories 等长。')
            for j, display in enumerate(displays or []):
                _finite_text_number(display, index, f'series[{i - 1}].displays[{j}]')
    elif layout == 'diagnostic':
        items = _list(slide, 'items', index, 1, 5)
        for i, item in enumerate(items):
            _required(item, ('title', 'evidence', 'implication', 'action', 'status'), index, f'items[{i}]')
    elif layout == 'targets':
        items = _list(slide, 'items', index, 1, 5)
        for i, item in enumerate(items):
            _required(item, ('label', 'current', 'target', 'delta'), index, f'items[{i}]')
            for field in ('current', 'target', 'delta'):
                _finite_text_number(item[field], index, f'items[{i}].{field}')
            if all(isinstance(item[f], (int, float)) for f in ('current', 'target', 'delta')):
                if not math.isclose(item['target'] - item['current'], item['delta'],
                                    rel_tol=1e-9, abs_tol=1e-9):
                    _error(index, f'items[{i}].delta 与 target - current 不一致。')
    elif layout == 'conversion':
        stages = _list(slide, 'stages', index, 2, 6)
        for i, stage in enumerate(stages):
            _required(stage, ('label', 'definition', 'owner'), index, f'stages[{i}]')
            if 'target' in stage:
                _finite_text_number(stage['target'], index, f'stages[{i}].target')
    elif layout == 'swimlane':
        periods = slide.get('periods')
        if not isinstance(periods, list) or not periods or len(periods) > 12:
            _error(index, 'periods 必须是 1–12 项的非空字符串列表。')
        if any(not isinstance(item, str) or not item.strip() for item in periods):
            _error(index, 'periods 的每一项都必须是非空字符串。')
        lanes = _list(slide, 'lanes', index, 1, 6)
        for i, lane in enumerate(lanes):
            _required(lane, ('label', 'owner'), index, f'lanes[{i}]')
            tasks = _list(lane, 'tasks', index, 1, 6)
            for j, task in enumerate(tasks):
                _required(task, ('label', 'deliverable'), index, f'lanes[{i}].tasks[{j}]')
                for field in ('start', 'end'):
                    value = task.get(field)
                    if isinstance(value, bool) or not isinstance(value, int):
                        _error(index, f'lanes[{i}].tasks[{j}].{field} 必须是 periods 的 0 基整数索引。')
                if not 0 <= task['start'] <= task['end'] < len(periods):
                    _error(index, f'lanes[{i}].tasks[{j}] 的 start/end 越界或顺序错误。')
    elif layout == 'decision':
        items = _list(slide, 'items', index, 1, 4)
        for i, item in enumerate(items):
            _required(item, ('title', 'decision', 'recommendation', 'reason', 'owner', 'date'),
                      index, f'items[{i}]')


def choose_report_layout(slide):
    """只识别具有判别力的字段，返回 None 时交给旧版自动路由。"""
    if (slide.get('points') is not None or slide.get('x_axis') is not None
            or (slide.get('y_axis') is not None and slide.get('series') is None
                and slide.get('categories') is None)):
        return 'positioning'
    if slide.get('stages') is not None:
        return 'conversion'
    if slide.get('periods') is not None or slide.get('lanes') is not None:
        return 'swimlane'
    steps = slide.get('steps')
    if isinstance(steps, list) and any(isinstance(s, dict) and s.get('kind') in ('start', 'delta', 'total') for s in steps):
        return 'waterfall'
    series = slide.get('series')
    if slide.get('categories') is not None or (isinstance(series, list) and any(
            isinstance(s, dict) and 'values' in s for s in series)):
        return 'trend'
    items = slide.get('items')
    if isinstance(items, list) and items:
        first = items[0]
        if isinstance(first, dict):
            if 'evidence' in first or 'implication' in first:
                return 'diagnostic'
            if 'current' in first or 'target' in first or 'delta' in first:
                return 'targets'
            if 'decision' in first or 'recommendation' in first:
                return 'decision'
    return None


def text_box(page, text, x, y, w, h=None, size=None, color='ink', bold=False,
             align='l', spacing=1.3, name=None, anchor='top'):
    size = size or page.t['body']
    required = text_height(str(text), w, size, spacing)
    tolerance = 6.0 if est_lines(str(text), w, size) == 1 else 0.6
    if h is not None and str(text).strip() and required > h + tolerance:
        excerpt = str(text).replace('\n', ' ')[:24]
        raise ValueError(f'文字“{excerpt}”需要 {required:.1f}px 高度，当前仅 {h:.1f}px；'
                         '请精简或拆页，不能缩字、截断或越界。')
    h = h or required
    box = _textbox(page.slide, x, y, w, h, name=name, anchor=anchor)
    _write(box.text_frame, str(text), size, color, bold=bold, line_spacing=spacing, align=align)
    return box


def _basis_text(basis):
    if isinstance(basis, dict):
        return str(basis.get('title') or '依据'), str(basis.get('body') or '').strip()
    return '依据', str(basis or '').strip()


def plan_supporting(slide, page, include_body=True):
    """为正文预留 body/basis/action/source，返回主体底边与绘制函数。"""
    blocks = []
    cursor = 620.0
    if slide.get('source'):
        text = str(slide['source']).strip()
        h = text_height(text, 1184, 14, 1.25)
        if h > 42:
            raise ValueError(f'页面“{slide.get("title")}”来源过长；请精简口径或拆成续页。')
        cursor -= h
        blocks.append(('source', text, cursor, h))
    if slide.get('action'):
        text = str(slide['action']).strip()
        h = text_height(text, 1184, 19, 1.25)
        if h > 54:
            raise ValueError(f'页面“{slide.get("title")}”行动内容过长；请拆成续页，不能缩字硬塞。')
        cursor -= h + 12
        blocks.append(('action', text, cursor + 8, h))
    if slide.get('basis'):
        label, text = _basis_text(slide['basis'])
        if text:
            text_h = text_height(text, 1058, 16, 1.3)
            h = text_h + 22
            if h > 112:
                raise ValueError(f'页面“{slide.get("title")}”依据内容过长；请拆成续页。')
            cursor -= h + 12
            blocks.append(('basis', (label, text), cursor + 6, h))
    if include_body and slide.get('body'):
        text = str(slide['body']).strip()
        h = text_height(text, 1184, 19, 1.35)
        if h > 96:
            raise ValueError(f'页面“{slide.get("title")}”补充正文过长；请拆成续页。')
        cursor -= h + 14
        blocks.append(('body', text, cursor + 8, h))

    def draw():
        for kind, value, y, h in blocks:
            if kind == 'source':
                text_box(page, value, 48, y, 1184, h, size=14, color='secondary',
                         spacing=1.25, name='report-source')
            elif kind == 'action':
                page.rule(48, y - 8, 1184, color='gold', width=1.6)
                text_box(page, value, 48, y, 1184, h, size=19, color='purple', bold=True,
                         spacing=1.25, name='report-action')
            elif kind == 'basis':
                label, text = value
                page.panel(48, y - 6, 1184, h, fill='pale', name='report-basis')
                text_box(page, label, 68, y + 5, 74, 24, size=15, color='purple', bold=True)
                text_box(page, text, 158, y + 5, 1054, h - 12, size=16, spacing=1.3)
            elif kind == 'body':
                text_box(page, value, 48, y, 1184, h, size=19, spacing=1.35,
                         name='report-body')
    return cursor - 10, draw


def _start(page, slide):
    y = 112.0
    lead = str(slide.get('lead') or slide.get('summary') or '').strip()
    if lead:
        h = text_height(lead, 1184, page.t['lead'], 1.2)
        if h > 100:
            raise ValueError(f'页面“{slide.get("title")}”概论过长；请拆成续页。')
        page.lead(lead, y=y)
        y += h + 12
    context = str(slide.get('context') or '').strip()
    if context:
        h = text_height(context, 1184, page.t['note'], 1.35)
        if h > 48:
            raise ValueError(f'页面“{slide.get("title")}”口径说明过长；请精简。')
        page.context(context, y=y)
        y += h + 8
    return max(128.0, y)


def _region(slide, page, minimum=150, include_body=True):
    y = _start(page, slide)
    bottom, draw_support = plan_supporting(slide, page, include_body=include_body)
    if bottom - y < minimum:
        raise ValueError(f'页面“{slide.get("title")}”主体空间不足；请拆分概论、正文、依据与行动。')
    return y, bottom, draw_support


def _fmt(value):
    return f'{value:g}' if isinstance(value, (int, float)) else str(value)


def _line(page, x1, y1, x2, y2, color='line', width=1.2):
    if abs(y2 - y1) < 0.01:
        return page.rule(min(x1, x2), y1, abs(x2 - x1), color=color, width=width)
    if abs(x2 - x1) < 0.01:
        return _rect(page.slide, x1, min(y1, y2), width, abs(y2 - y1), color)
    return page.freeform([(x1, y1), (x2, y2)], color=color, width=width)


def _positioning(page, slide, y, bottom):
    xa, ya = slide['x_axis'], slide['y_axis']
    x0, x1, y0, y1 = 174.0, 1150.0, y + 28, bottom - 64
    if y1 - y0 < 100:
        raise ValueError('positioning 绘图区高度不足；请减少辅助文字。')
    xr = slide.get('x_reference', (xa['min'] + xa['max']) / 2)
    yr = slide.get('y_reference', (ya['min'] + ya['max']) / 2)
    px = lambda v: x0 + (v - xa['min']) / (xa['max'] - xa['min']) * (x1 - x0)
    py = lambda v: y1 - (v - ya['min']) / (ya['max'] - ya['min']) * (y1 - y0)
    _line(page, x0, y0, x0, y1, 'ink', 1.4)
    _line(page, x0, y1, x1, y1, 'ink', 1.4)
    _line(page, px(xr), y0, px(xr), y1, 'line', 1.0)
    _line(page, x0, py(yr), x1, py(yr), 'line', 1.0)
    xu = f'（{xa.get("unit", "")}）' if xa.get('unit') else ''
    yu = f'（{ya.get("unit", "")}）' if ya.get('unit') else ''
    text_box(page, f'{xa["label"]}{xu}', x0, y1 + 30, x1 - x0, 24, size=16,
             color='purple', bold=True, align='c')
    text_box(page, f'{_fmt(xa["min"])}', x0 - 36, y1 + 6, 72, 20, size=13, color='secondary', align='c')
    text_box(page, f'{_fmt(xa["max"])}', x1 - 36, y1 + 6, 72, 20, size=13, color='secondary', align='c')
    text_box(page, f'{ya["label"]}{yu}  {_fmt(ya["max"])}', 48, y0 - 24, 220, 22,
             size=14, color='purple', bold=True)
    text_box(page, _fmt(ya['min']), 116, y1 - 10, 48, 20, size=13, color='secondary', align='r')
    occupied = []
    point_boxes = [(px(p['x']) - 10, py(p['y']) - 10, px(p['x']) + 10, py(p['y']) + 10)
                   for p in slide['points']]
    for i, point in enumerate(slide['points']):
        cx, cy = px(point['x']), py(point['y'])
        page.dot(cx, cy, 7, point.get('color', 'purple'))
        dx = point.get('display_x', _fmt(point['x']))
        dy = point.get('display_y', _fmt(point['y']))
        label = f'{point["label"]}\n{dx} / {dy}'
        note = str(point.get('note') or '')
        w = 224
        h = text_height(label, w, 16, 1.2) + (text_height(note, w, 13, 1.2) if note else 0)
        candidates = [(cx + 14, cy - h - 12), (cx + 14, cy + 12),
                      (cx - w - 14, cy - h - 12), (cx - w - 14, cy + 12),
                      (cx + 14, cy - h / 2), (cx - w - 14, cy - h / 2)]
        placed = None
        for tx, ty in candidates:
            tx = max(x0 + 4, min(x1 - w, tx))
            ty = max(y0, min(y1 - h, ty))
            rect = (tx, ty, tx + w, ty + h)
            if all(rect[2] < r[0] or rect[0] > r[2] or rect[3] < r[1] or rect[1] > r[3]
                   for r in occupied + point_boxes):
                placed = (tx, ty, rect)
                break
        if placed is None:
            raise ValueError(f'positioning 第 {i + 1} 个学校标签无法避让；请减少点或拆页。')
        tx, ty, rect = placed
        occupied.append(rect)
        # 当标签被避让到远处，以引线保持点与名称的对应。
        edge_x = max(tx, min(tx + w, cx))
        edge_y = max(ty, min(ty + h, cy))
        _line(page, cx, cy, edge_x, edge_y, point.get('color', 'purple'), 0.8)
        text_box(page, label, tx, ty, w, text_height(label, w, 16, 1.2), size=16,
                 color=point.get('color', 'ink'), bold=True, spacing=1.2,
                 align='r' if tx + w / 2 < cx else 'l')
        if note:
            text_box(page, note, tx, ty + text_height(label, w, 16, 1.2), w,
                     text_height(note, w, 13, 1.2), size=13, color='secondary', spacing=1.2,
                     align='r' if tx + w / 2 < cx else 'l')


def _waterfall(page, slide, y, bottom):
    steps = slide['steps']
    cumulative = 0.0
    levels = []
    running = []
    for step in steps:
        previous = cumulative
        if step['kind'] in ('start', 'total'):
            cumulative = float(step['value'])
        else:
            cumulative += float(step['value'])
        levels.append((previous, cumulative))
        running.extend((previous, cumulative, 0.0))
    low, high = min(running), max(running)
    if low == high:
        low, high = low - 1, high + 1
    padding = (high - low) * 0.12
    low, high = low - padding, high + padding
    x0, x1, y0, y1 = 96.0, 1200.0, y + 38, bottom - 76
    py = lambda v: y1 - (v - low) / (high - low) * (y1 - y0)
    _line(page, x0, py(0), x1, py(0), 'secondary', 1.2)
    slot = (x1 - x0) / len(steps)
    width = min(112, slot * 0.58)
    for i, (step, (previous, current)) in enumerate(zip(steps, levels)):
        cx = x0 + slot * (i + 0.5)
        if step['kind'] == 'delta':
            top, base = py(max(previous, current)), py(min(previous, current))
        else:
            top, base = py(max(0, current)), py(min(0, current))
        color = step.get('color') or ('red' if step['kind'] == 'delta' and step['value'] < 0
                                     else 'blue' if step['kind'] == 'delta'
                                     else 'gold' if step['kind'] == 'total' else 'purple')
        _rect(page.slide, cx - width / 2, top, width, max(2, base - top), color,
              name=f'waterfall-{i + 1}')
        if i:
            _line(page, cx - slot + width / 2, py(previous), cx - width / 2, py(previous), 'secondary', 1.1)
        display = step.get('display')
        if display is None:
            display = f'{step["value"]:+g}' if step['kind'] == 'delta' else _fmt(step['value'])
        label_y = top - 36
        text_box(page, display, cx - slot / 2 + 4, label_y, slot - 8, 26, size=17,
                 color=color, bold=True, align='c')
        text_box(page, step['label'], cx - slot / 2 + 4, y1 + 14, slot - 8, 44,
                 size=16, bold=True, align='c')
        if step.get('note'):
            note_h = text_height(step['note'], slot - 8, 13, 1.2)
            if y1 + 58 + note_h > bottom:
                raise ValueError(f'waterfall 第 {i + 1} 项注释超出绘图区；请精简或拆页。')
            text_box(page, step['note'], cx - slot / 2 + 4, y1 + 56, slot - 8, note_h,
                     size=13, color='secondary', align='c', spacing=1.2)


def _trend(page, slide, y, bottom):
    categories, series, axis = slide['categories'], slide['series'], slide['y_axis']
    x0, x1, y0, y1 = 154.0, 1180.0, y + 64, bottom - 62
    if y1 - y0 < 100:
        raise ValueError('trend 绘图区高度不足；请减少辅助文字或拆页。')
    py = lambda v: y1 - (v - axis['min']) / (axis['max'] - axis['min']) * (y1 - y0)
    _line(page, x0, y0, x0, y1, 'ink', 1.3)
    _line(page, x0, y1, x1, y1, 'ink', 1.3)
    unit = f'（{axis.get("unit", "")}）' if axis.get('unit') else ''
    text_box(page, f'{axis["label"]}{unit}', 48, y + 2, 100, 50,
             size=14, color='purple', bold=True)
    text_box(page, _fmt(axis['max']), 96, y0 - 10, 48, 20,
             size=13, color='secondary', align='r')
    text_box(page, _fmt(axis['min']), 96, y1 - 10, 48, 20, size=13, color='secondary', align='r')
    for i, category in enumerate(categories):
        cx = x0 + (x1 - x0) * i / max(1, len(categories) - 1)
        text_box(page, category, cx - 64, y1 + 14, 128, 38, size=15, align='c')
    legend_x = 200.0
    for si, item in enumerate(series):
        color = item.get('color') or ('purple', 'blue', 'gold', 'red')[si]
        legend_w = max(130, len(item['label']) * 17 + 50)
        _line(page, legend_x, y + 16, legend_x + 28, y + 16, color, 3)
        text_box(page, item['label'], legend_x + 36, y + 4, legend_w - 36, 26,
                 size=15, color=color, bold=True)
        legend_x += legend_w + 20
    if legend_x > 1232:
        raise ValueError('trend 图例过长；请缩短系列名称或拆页。')
    for si, item in enumerate(series):
        color = item.get('color') or ('purple', 'blue', 'gold', 'red')[si]
        points = []
        for i, value in enumerate(item['values']):
            cx = x0 + (x1 - x0) * i / max(1, len(categories) - 1)
            points.append((cx, py(value)))
        if len(points) > 1:
            page.freeform(points, color=color, width=2.6)
        for i, ((cx, cy), value) in enumerate(zip(points, item['values'])):
            page.dot(cx, cy, 5, color)
            display = item.get('displays', [None] * len(categories))[i]
            display = _fmt(value) if display is None else str(display)
            dy = -30 - si * 3 if si % 2 == 0 else 10 + si * 3
            if cy + dy + 22 > y1 - 4:
                dy = -30
            ty = max(y0 - 32, cy + dy)
            tx = max(x0 + 8, min(x1 - 108, cx - 54))
            _rect(page.slide, tx, ty, 108, 22, 'paper', name='trend-label-backdrop')
            text_box(page, display, tx, ty, 108, 22, size=14, color=color,
                     bold=True, align='c')


def _diagnostic(page, slide, y, bottom):
    items = slide['items']
    headers = [('编号 / 状态', 48, 210), ('诊断事项', 144, 232), ('证据', 396, 254),
               ('含义', 682, 238), ('动作', 952, 280)]
    for label, x, w in headers[1:]:
        text_box(page, label, x, y, w, 26, size=15, color='purple', bold=True)
    page.rule(48, y + 34, 1184, color='gold', width=1.5)
    row_h = (bottom - y - 44) / len(items)
    if row_h < 86:
        raise ValueError('diagnostic 每行不足以容纳编号与状态；请减少辅助文字或拆页。')
    for i, item in enumerate(items):
        yy = y + 44 + i * row_h
        text_box(page, f'{i + 1:02d}', 48, yy + 8, 72, 38, size=26, color='purple', bold=True)
        text_box(page, item['status'], 48, yy + 52, 84, 28, size=14, color='secondary')
        columns = [('title', 144, 232, 20, 'ink', True),
                   ('evidence', 396, 254, 17, 'ink', False),
                   ('implication', 682, 238, 17, 'ink', False),
                   ('action', 952, 280, 17, 'purple', True)]
        for field, x, w, size, color, bold in columns:
            h = text_height(item[field], w, size, 1.3)
            if h > row_h - 14:
                raise ValueError(f'diagnostic 第 {i + 1} 项 {field} 超出开放行；请拆页，不能缩字。')
            text_box(page, item[field], x, yy + 6, w, h, size=size, color=color,
                     bold=bold, spacing=1.3)
        if i < len(items) - 1:
            page.rule(144, yy + row_h - 4, 1088, color='line')


def _targets(page, slide, y, bottom):
    items = slide['items']
    row_h = (bottom - y) / len(items)
    if row_h < 86:
        raise ValueError('targets 目标行高度不足；请减少辅助文字或拆页，不能叠行。')
    for i, item in enumerate(items):
        yy = y + i * row_h
        color = item.get('color', 'purple')
        _rect(page.slide, 48, yy + 10, 6, row_h - 20, color, name=f'target-mark-{i + 1}')
        text_box(page, item['label'], 76, yy + 12, 276, 36, size=22, bold=True)
        if item.get('note'):
            h = text_height(item['note'], 276, 15, 1.25)
            if yy + 58 + h > yy + row_h - 6:
                raise ValueError(f'targets 第 {i + 1} 项注释过长；请精简或拆页。')
            text_box(page, item['note'], 76, yy + 56, 276, h, size=15, color='secondary', spacing=1.25)
        text_box(page, '当前', 396, yy + 12, 130, 24, size=14, color='secondary')
        current_h = text_height(str(item['current']), 180, 26, 1.15)
        text_box(page, str(item['current']), 396, yy + 40, 180, current_h,
                 size=26, color='ink', bold=True, spacing=1.15)
        text_box(page, '差额', 614, yy + 12, 130, 24, size=14, color='secondary')
        delta_h = text_height(str(item['delta']), 200, 26, 1.15)
        text_box(page, str(item['delta']), 614, yy + 40, 200, delta_h,
                 size=26, color=color, bold=True, spacing=1.15)
        text_box(page, '目标', 916, yy + 12, 130, 24, size=14, color='secondary')
        target_h = text_height(str(item['target']), 316, 38, 1.1)
        if max(current_h, delta_h, target_h) > row_h - 40:
            raise ValueError(f'targets 第 {i + 1} 项当前值、差额或目标值过长；请缩短显示文本。')
        text_box(page, str(item['target']), 916, yy + 34, 316, target_h, size=38,
                 color=color, bold=True, align='r', spacing=1.1)
        if i < len(items) - 1:
            page.rule(76, yy + row_h - 4, 1156, color='line')


def _conversion(page, slide, y, bottom):
    stages = slide['stages']
    gap = 28
    w = (1184 - gap * (len(stages) - 1)) / len(stages)
    h = bottom - y
    for i, stage in enumerate(stages):
        x = 48 + i * (w + gap)
        page.panel(x, y, w, h, fill='pale' if i % 2 == 0 else 'F7F5F9', name=f'conversion-{i + 1}')
        text_box(page, f'{i + 1:02d}', x + 16, y + 16, w - 32, 34, size=24, color='gold', bold=True)
        cursor = y + 62
        for field, size, color, bold in (('label', 21, 'purple', True),
                                         ('definition', 16, 'ink', False)):
            value = stage[field]
            th = text_height(value, w - 32, size, 1.3)
            if cursor + th > bottom - 112:
                raise ValueError(f'conversion 第 {i + 1} 阶段 {field} 过长；请拆页。')
            text_box(page, value, x + 16, cursor, w - 32, th, size=size, color=color,
                     bold=bold, spacing=1.3)
            cursor += th + 14
        target = stage.get('target') if str(stage.get('target', '')).strip() else '待补'
        owner = stage['owner']
        text_box(page, '目标 / 基线', x + 16, bottom - 104, w - 32, 22, size=13, color='secondary')
        target_h = text_height(str(target), w - 32, 18, 1.2)
        if target_h > 44:
            raise ValueError(f'conversion 第 {i + 1} 阶段目标文本过长；请精简。')
        text_box(page, str(target), x + 16, bottom - 78, w - 32, target_h, size=18,
                 color='purple', bold=True, spacing=1.2)
        text_box(page, '责任：' + owner, x + 16, bottom - 30, w - 32, 24, size=14, color='secondary')
        if i < len(stages) - 1:
            _line(page, x + w + 5, y + h / 2, x + w + gap - 5, y + h / 2, 'gold', 2.4)
            page.freeform([(x + w + gap - 12, y + h / 2 - 6),
                           (x + w + gap - 5, y + h / 2),
                           (x + w + gap - 12, y + h / 2 + 6)], color='gold', width=2.0)


def _swimlane(page, slide, y, bottom):
    periods, lanes = slide['periods'], slide['lanes']
    label_w = 184
    grid_x, grid_w = 48 + label_w, 1184 - label_w
    col_w = grid_w / len(periods)
    header_h = 42
    for i, period in enumerate(periods):
        text_box(page, period, grid_x + i * col_w + 4, y + 6, col_w - 8, 32,
                 size=17, color='purple', bold=True, align='c')
    lane_h = (bottom - y - header_h) / len(lanes)
    if lane_h < 64:
        raise ValueError('swimlane 泳道高度不足；请减少泳道、辅助文字或拆页。')
    for i in range(len(periods) + 1):
        _line(page, grid_x + i * col_w, y, grid_x + i * col_w, bottom, 'line', 1.0)
    for li, lane in enumerate(lanes):
        yy = y + header_h + li * lane_h
        if li % 2 == 0:
            page.panel(48, yy, 1184, lane_h, fill='F7F5F9')
        label_h = text_height(lane['label'], label_w - 12, 21, 1.2)
        owner = '责任：' + lane['owner']
        owner_h = text_height(owner, label_w - 12, 17, 1.2)
        if label_h + owner_h + 16 > lane_h:
            raise ValueError('swimlane 责任说明超出泳道高度；请重排或拆页，不能缩字。')
        text_box(page, lane['label'], 48, yy + 7, label_w - 12, label_h,
                 size=21, bold=True, spacing=1.2)
        text_box(page, owner, 48, yy + 9 + label_h, label_w - 12, owner_h,
                 size=17, color='secondary', spacing=1.2)
        # 同一责任方不重叠的时期共享基线；只有时间重叠才增加纵向任务轨。
        track_ends, assigned = [], {}
        for ti in sorted(range(len(lane['tasks'])), key=lambda i: lane['tasks'][i]['start']):
            task = lane['tasks'][ti]
            track = next((i for i, end in enumerate(track_ends) if task['start'] > end), len(track_ends))
            if track == len(track_ends): track_ends.append(task['end'])
            else: track_ends[track] = task['end']
            assigned[ti] = track
        task_h = (lane_h - 12) / len(track_ends)
        for ti, task in enumerate(lane['tasks']):
            tx = grid_x + task['start'] * col_w + 5
            tw = (task['end'] - task['start'] + 1) * col_w - 10
            ty = yy + 6 + assigned[ti] * task_h
            th = task_h - 4
            status = str(task.get('status') or '未标注')
            content = f'{task["label"]}｜{task["deliverable"]}｜{status}'
            size = 19
            needed = text_height(content, tw - 20, size, 1.2)
            if needed > th:
                raise ValueError(f'swimlane 任务“{task["label"]}”文字或交付物超出任务条；请拆页。')
            color = {'已完成': 'blue', '完成': 'blue', '进行中': 'purple',
                     '延期': 'red', '滞后': 'red'}.get(status, 'gold')
            band = page.band(tx, ty, tw, th, content, fill=color,
                             color='ink' if color == 'gold' else 'white', inset=10,
                             size=size, spacing=1.2)
            band.name = f'swimlane-{li + 1}-{ti + 1}'
        page.rule(48, yy + lane_h - 1, 1184, color='line')


def _decision_height(item):
    heading = max(text_height(item['title'], 580, 22, 1.2),
                  text_height(f'{item["owner"]}｜{item["date"]}', 412, 15, 1.2))
    columns = max(text_height(f'拟审议｜{item["decision"]}', 500, 19, 1.3),
                  text_height(f'建议｜{item["recommendation"]}', 556, 19, 1.3))
    reason = text_height(f'依据｜{item["reason"]}', 1104, 17, 1.3)
    return heading + columns + reason + 20


def _decision(page, slide, y, bottom):
    items = slide['items']
    heights = [_decision_height(item) for item in items]
    if sum(heights) > bottom - y + 0.5:
        raise ValueError('decision 事项无法完整容纳；请拆成续页。')
    extra = (bottom - y - sum(heights)) / len(items)
    yy = y
    for i, (item, required) in enumerate(zip(items, heights)):
        row_h = required + extra
        text_box(page, f'{i + 1 + slide.get("_item_offset", 0):02d}', 48, yy + 4, 64, 40,
                 size=28, color='gold', bold=True)
        title_h = text_height(item['title'], 580, 22, 1.2)
        owner_text = f'{item["owner"]}｜{item["date"]}'
        owner_h = text_height(owner_text, 412, 15, 1.2)
        text_box(page, item['title'], 128, yy + 4, 580, title_h,
                 size=22, color='purple', bold=True, spacing=1.2)
        text_box(page, owner_text, 820, yy + 6, 412, owner_h,
                 size=15, color='secondary', align='r', spacing=1.2)
        cursor = yy + max(title_h, owner_h) + 10
        col_h = 0
        for field, label, x, w, color in (
                ('decision', '拟审议', 128, 500, 'ink'),
                ('recommendation', '建议', 676, 556, 'purple')):
            value = f'{label}｜{item[field]}'
            h = text_height(value, w, 19, 1.3)
            text_box(page, value, x, cursor, w, h, size=19, color=color, bold=True, spacing=1.3)
            col_h = max(col_h, h)
        value = f'依据｜{item["reason"]}'
        h = text_height(value, 1104, 17, 1.3)
        text_box(page, value, 128, cursor + col_h + 4, 1104, h,
                 size=17, color='ink', spacing=1.3)
        if i < len(items) - 1:
            page.rule(128, yy + row_h - 4, 1104, color='line')
        yy += row_h


def render_report_layout(deck, slide, tier, layout=None):
    layout = layout or (slide['layout'] if slide.get('layout') in REPORT_LAYOUTS else slide['_resolved_layout'])
    if layout == 'decision':
        if slide.get('body'):
            raise ValueError('decision 的 items 已承担正文；请将 body 并入对应字段，避免静默丢失。')
        remaining, pages, offset = list(slide['items']), [], 0
        while remaining:
            title = slide['title'] + ('（续）' if pages else '')
            page = deck.page(title, tier=tier)
            current = dict(slide, title=title, _item_offset=offset)
            y, bottom, draw_support = _region(current, page, minimum=100, include_body=False)
            group, used = [], 0
            for item in remaining:
                needed = _decision_height(item)
                if used + needed > bottom - y + 0.5:
                    break
                group.append(item)
                used += needed
            if not group:
                raise ValueError('decision 单项文字超过一页容量；请精简辅助文字或展开单项论证。')
            current['items'] = group
            _decision(page, current, y, bottom)
            draw_support()
            page.page_number()
            pages.append(page)
            offset += len(group)
            remaining = remaining[len(group):]
        return pages
    page = deck.page(slide['title'], tier=tier)
    include_body = layout not in ('diagnostic', 'decision')
    minimum = 190 if layout in ('positioning', 'waterfall', 'trend', 'conversion') else 140
    y, bottom, draw_support = _region(slide, page, minimum=minimum, include_body=include_body)
    renderer = {
        'positioning': _positioning, 'waterfall': _waterfall, 'trend': _trend,
        'diagnostic': _diagnostic, 'targets': _targets, 'conversion': _conversion,
        'swimlane': _swimlane, 'decision': _decision,
    }[layout]
    renderer(page, slide, y, bottom)
    if not include_body and slide.get('body'):
        raise ValueError(f'{layout} 的 items 已承担正文；请将 body 内容并入对应字段，避免静默丢失。')
    draw_support()
    page.page_number()
    return [page]
