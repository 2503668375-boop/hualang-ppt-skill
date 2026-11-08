"""有具体材料的原生页面组合：批注、对应修订和有代价的方案比较。

局部 draw_* 接受 Page 和逻辑像素区域；返回实际占用高度。整页入口按完整
材料单元续页，不截取文字，不靠缩字消化超量内容。字号取 Page.t。
"""
from __future__ import annotations

import math

from pptx.util import Pt

from hualang_deck import TIERS, _textbox, _write, text_height

CONTENT_LAYOUTS = {'annotated', 'revision', 'tradeoff'}


def _text(value, path):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{path} 必须是非空文字。')
    return value


def _items(value, path):
    if not isinstance(value, list) or not value or any(not isinstance(v, dict) for v in value):
        raise ValueError(f'{path} 必须是非空对象列表。')
    return value


def choose_content_layout(slide):
    if slide.get('source_blocks'):
        return 'annotated'
    if slide.get('changes'):
        return 'revision'
    if slide.get('options') and slide.get('metric'):
        return 'tradeoff'
    return None


def validate_content_slide(slide, layout, index=''):
    prefix = f'第 {index} 页 ' if index else ''
    if layout == 'annotated':
        blocks = _items(slide.get('source_blocks'), prefix + 'source_blocks')
        ids = []
        for i, block in enumerate(blocks):
            ids.append(_text(block.get('id'), prefix + f'source_blocks[{i}].id'))
            _text(block.get('text'), prefix + f'source_blocks[{i}].text')
        if len(set(ids)) != len(ids):
            raise ValueError(prefix + 'source_blocks.id 不得重复；批注需要明确对应原文。')
        annotations = _items(slide.get('annotations'), prefix + 'annotations')
        targets = []
        for i, note in enumerate(annotations):
            target = _text(note.get('target'), prefix + f'annotations[{i}].target')
            if target not in ids:
                raise ValueError(prefix + f'annotations[{i}].target 找不到对应原文段落。')
            targets.append(target)
            for field in ('label', 'comment'):
                _text(note.get(field), prefix + f'annotations[{i}].{field}')
            if 'rewrite' in note:
                _text(note['rewrite'], prefix + f'annotations[{i}].rewrite')
        if len(set(targets)) != len(targets):
            raise ValueError(prefix + '同一段落的相关批注请并入一个完整单元，不能重叠放置。')
    elif layout == 'revision':
        changes = _items(slide.get('changes'), prefix + 'changes')
        for i, change in enumerate(changes):
            for field in ('label', 'before', 'after', 'reason'):
                _text(change.get(field), prefix + f'changes[{i}].{field}')
    elif layout == 'tradeoff':
        options = _items(slide.get('options'), prefix + 'options')
        if len(options) < 2:
            raise ValueError(prefix + 'tradeoff 至少需要两个真实备选项。')
        metric = slide.get('metric')
        if not isinstance(metric, dict):
            raise ValueError(prefix + 'metric 必须包含 label、unit 及可选 max。')
        _text(metric.get('label'), prefix + 'metric.label')
        _text(metric.get('unit'), prefix + 'metric.unit')
        values = []
        for i, option in enumerate(options):
            for field in ('name', 'fit', 'cost', 'condition'):
                _text(option.get(field), prefix + f'options[{i}].{field}')
            value = option.get('value')
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError(prefix + f'options[{i}].value 必须是非负有限数；负值比较使用带零基线的专用图。')
            values.append(value)
        maximum = metric.get('max', max(values) or 1)
        if (isinstance(maximum, bool) or not isinstance(maximum, (int, float))
                or not math.isfinite(maximum) or maximum <= 0 or maximum < max(values)):
            raise ValueError(prefix + 'metric.max 必须为正且覆盖全部数值。')
    for field in ('boundary', 'source_title', 'before_label', 'after_label'):
        if field in slide:
            _text(slide[field], prefix + field)
    if 'recommendation' in slide:
        value = slide['recommendation']
        if isinstance(value, dict):
            _text(value.get('option'), prefix + 'recommendation.option')
            _text(value.get('why'), prefix + 'recommendation.why')
        else:
            _text(value, prefix + 'recommendation')


def _height(text, width, size, spacing=1.35):
    return text_height(str(text), width, size, spacing) + 3


def _box(page, text, x, y, w, size, *, color='ink', bold=False, name=None, spacing=1.35, align='l'):
    h = _height(text, w, size, spacing)
    shape = _textbox(page.slide, x, y, w, h, name=name)
    _write(shape.text_frame, str(text), size, color, bold=bold, line_spacing=spacing, align=align)
    for paragraph in shape.text_frame.paragraphs:
        paragraph.line_spacing = Pt(size * spacing * .75)
    return h


def _region(x, y, w, h):
    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in (x, y, w, h)):
        raise ValueError('组件区域坐标必须是有限数值。')
    if w < 580 or h <= 0 or x < 0 or y < 0 or x + w > 1280 or y + h > 680:
        raise ValueError('组件区域须位于正文画布内且宽度不少于580px；请重排，不能缩成不可读微缩页。')


def _fit(required, h, layout):
    if required > h + .01:
        raise ValueError(f'{layout} 当前区域需 {required:.0f}px，只有 {h:.0f}px；请扩大区域或用整稿入口续页，不会裁字。')


def _annotated_geometry(t, blocks, notes, w):
    sw = w * .60
    nw = w - sw - 58
    size, note_size = t['body'], t['label']
    mapped = {n['target']: n for n in notes}
    rows = []
    for block in blocks:
        note = mapped.get(block['id'])
        source_h = _height(block['text'], sw - 64, size)
        note_h = 0
        if note:
            note_h = _height(note['label'], nw, note_size) + 7
            note_h += _height(note['comment'], nw, note_size)
            if note.get('rewrite'):
                note_h += 8 + _height(note['rewrite'], nw, note_size)
        rows.append(max(source_h, note_h) + 24)
    return sw, nw, rows


def draw_annotated(page, source_blocks, annotations, *, x=48, y=200, w=1184, h=430,
                   source_title='原始材料'):
    """宽幅原文＋近邻批注；每条批注用 target 对应实际原文段落。"""
    # A paginated excerpt can contain only unannotated source paragraphs.
    if annotations:
        validate_content_slide({'source_blocks': source_blocks, 'annotations': annotations}, 'annotated')
    else:
        _items(source_blocks, 'source_blocks')
        for block in source_blocks:
            _text(block.get('id'), 'source_blocks.id'); _text(block.get('text'), 'source_blocks.text')
    _region(x, y, w, h)
    sw, nw, rows = _annotated_geometry(page.t, source_blocks, annotations, w)
    header = _height(source_title, sw - 48, page.t['label']) + 27
    required = header + sum(rows) + 8
    _fit(required, h, 'annotated')
    page.panel(x, y, sw, required, fill='pale', name='annotated-source-field')
    _box(page, source_title, x + 26, y + 18, sw - 48, page.t['label'],
         color='purple', bold=True, name='annotated-source-title')
    page.rule(x + 26, y + header - 10, 46, color='gold', width=2)
    mapped = {note['target']: note for note in annotations}
    cy = y + header
    for block, row_h in zip(source_blocks, rows):
        note = mapped.get(block['id'])
        _box(page, block['text'], x + 30, cy, sw - 64, page.t['body'],
             name='source-' + block['id'])
        if note:
            nx = x + sw + 58
            page.dot(x + sw - 13, cy + 12, r=3, color='gold')
            line = page.freeform([(x + sw - 10, cy + 12), (nx - 24, cy + 12), (nx - 12, cy + 12)],
                                 color='gold', width=1.4)
            line.name = 'annotation-anchor-' + block['id']
            nh = _box(page, note['label'], nx, cy, nw, page.t['label'],
                      color='purple', bold=True, name='annotation-label-' + block['id'])
            ny = cy + nh + 7
            ny += _box(page, note['comment'], nx, ny, nw, page.t['label'],
                       name='annotation-comment-' + block['id'])
            if note.get('rewrite'):
                _box(page, note['rewrite'], nx, ny + 8, nw, page.t['label'],
                     color='blue', name='annotation-rewrite-' + block['id'])
        cy += row_h
    return required


def _revision_geometry(t, changes, w):
    gap = 28
    widths = ((w - 2 * gap) * .29, (w - 2 * gap) * .43, (w - 2 * gap) * .28)
    rows = []
    for change in changes:
        label_h = _height(change['label'], w, t['label'])
        content_h = max(_height(change['before'], widths[0], t['body']),
                        _height(change['after'], widths[1], t['body']),
                        _height(change['reason'], widths[2], t['label']))
        rows.append(label_h + 12 + content_h + 22)
    return widths, gap, rows


def draw_revision(page, changes, *, x=48, y=200, w=1184, h=430,
                  before_label='原稿', after_label='修订稿'):
    """以同一修改单元对照原稿、修订稿和具体依据，完整保留前后文字。"""
    validate_content_slide({'changes': changes}, 'revision')
    _region(x, y, w, h)
    widths, gap, rows = _revision_geometry(page.t, changes, w)
    header = max(_height(v, cw, page.t['label']) for v, cw in zip(
        (before_label, after_label, '修改依据'), widths)) + 16
    required = header + sum(rows)
    _fit(required, h, 'revision')
    xs = [x, x + widths[0] + gap, x + widths[0] + widths[1] + 2 * gap]
    for i, (label, cw) in enumerate(zip((before_label, after_label, '修改依据'), widths)):
        _box(page, label, xs[i], y, cw, page.t['label'], color='purple', bold=True,
             name=f'revision-column-{i}')
    page.rule(xs[1], y + header - 8, widths[1], color='gold', width=2)
    cy = y + header
    for i, (change, row_h) in enumerate(zip(changes, rows)):
        lh = _box(page, change['label'], x, cy, w, page.t['label'], color='purple', bold=True,
                  name=f'revision-label-{i}')
        ty = cy + lh + 12
        _box(page, change['before'], xs[0], ty, widths[0], page.t['body'],
             name=f'revision-before-{i}')
        _box(page, change['after'], xs[1], ty, widths[1], page.t['body'], bold=True,
             name=f'revision-after-{i}')
        _box(page, change['reason'], xs[2], ty, widths[2], page.t['label'], color='blue',
             name=f'revision-reason-{i}')
        if i < len(changes) - 1:
            page.rule(x, cy + row_h - 10, w, color='line')
        cy += row_h
    return required


def _tradeoff_metric_lane(t, option, width, metric):
    """Keep name and value beside each other; wrap either at its own measured width."""
    display = str(option.get('display') or f'{option["value"]:g}{metric.get("unit", "")}')
    natural_width = max(sum(1.0 if ord(ch) > 0x2E80 else .55 for ch in line)
                        for line in display.split('\n')) * t['label'] + 8
    value_w = min(max(72, natural_width), width * .40)
    name_w = width - 16 - value_w
    heading_h = max(_height(option['name'], name_w, t['body']),
                    _height(display, value_w, t['label']))
    return name_w, value_w, display, heading_h


def _tradeoff_geometry(t, options, w, metric=None):
    # Metric lane is dominant; prose lanes share comparisons, not equal cards.
    gap = 26
    widths = ((w - gap * 3) * .36, (w - gap * 3) * .21,
              (w - gap * 3) * .22, (w - gap * 3) * .21)
    rows = []
    for option in options:
        _, _, _, heading_h = _tradeoff_metric_lane(t, option, widths[0], metric or {})
        metric_h = heading_h + 8 + 22
        prose_h = max(_height(option[field], widths[i], t['label'])
                      for i, field in enumerate(('fit', 'cost', 'condition'), 1))
        rows.append(max(metric_h, prose_h) + 24)
    return widths, gap, rows


def draw_tradeoff(page, options, metric, *, x=48, y=200, w=1184, h=430):
    """同一零基线的指标横条与适用问题、其他代价、成立条件同行比较。"""
    # Continuation page may have one remaining option; global validation occurs first.
    if len(options) >= 2:
        validate_content_slide({'options': options, 'metric': metric}, 'tradeoff')
    else:
        validate_content_slide({'options': options * 2, 'metric': metric}, 'tradeoff')
    _region(x, y, w, h)
    widths, gap, rows = _tradeoff_geometry(page.t, options, w, metric)
    labels = (f'{metric["label"]}（{metric["unit"]}）', '适用问题', '其他代价', '成立条件')
    header = max(_height(label, width, page.t['label']) for label, width in zip(labels, widths)) + 18
    required = header + sum(rows)
    _fit(required, h, 'tradeoff')
    xs = [x]
    for width in widths[:-1]:
        xs.append(xs[-1] + width + gap)
    for i, (label, width) in enumerate(zip(labels, widths)):
        _box(page, label, xs[i], y, width, page.t['label'], bold=True, color='purple',
             name=f'tradeoff-column-{i}')
    page.rule(x, y + header - 9, w, color='gold', width=1.4)
    maximum = metric.get('max', max(option['value'] for option in options) or 1)
    bar_w = widths[0] - 18
    cy = y + header
    for i, (option, row_h) in enumerate(zip(options, rows)):
        name_w, value_w, display, heading_h = _tradeoff_metric_lane(page.t, option, widths[0], metric)
        _box(page, option['name'], x, cy, name_w, page.t['body'], bold=True,
             name=f'tradeoff-name-{i}')
        _box(page, display, x + widths[0] - value_w, cy, value_w, page.t['label'],
             color='ink', bold=True, name=f'tradeoff-value-{i}', align='r')
        by = cy + heading_h + 8
        page.rule(x, by + 15, bar_w, color='line')
        page.rule(x, by, 1.4, color='gold', width=22)
        if option['value']:
            page.panel(x + 2, by + 2, (bar_w - 2) * option['value'] / maximum, 14,
                       fill=option.get('color', 'blue'), name=f'tradeoff-bar-{i}')
        for ci, field in enumerate(('fit', 'cost', 'condition'), 1):
            _box(page, option[field], xs[ci], cy, widths[ci], page.t['label'],
                 name=f'tradeoff-{field}-{i}')
        if i < len(options) - 1:
            page.rule(x, cy + row_h - 10, w, color='line')
        cy += row_h
    return required


def _support(slide):
    rows = []
    for field in ('body', 'basis', 'action', 'recommendation', 'boundary'):
        value = slide.get(field)
        if not value:
            continue
        if field == 'recommendation' and isinstance(value, dict):
            rows.append(('建议选择：' + value['option'], value['why']))
        elif isinstance(value, dict):
            rows.append((str(value.get('title') or ''), str(value.get('body') or '')))
        else:
            rows.append(('适用边界' if field == 'boundary' else '', str(value)))
    return rows


def _support_height(slide, t):
    return sum(_height((label + '　' if label else '') + text, 1184, t['label']) + 8
               for label, text in _support(slide))


def _header_height(slide, t):
    result = 0
    lead = slide.get('lead') or slide.get('summary')
    if lead:
        result += _height(lead, 1184, t['lead'], 1.2) + 10
    context = '\n'.join(str(slide[k]) for k in ('context', 'source') if slide.get(k))
    if context:
        result += _height(context, 1184, t['note']) + 10
    return result


def _draw_header(page, slide):
    y = 112
    lead = slide.get('lead') or slide.get('summary')
    if lead:
        y += _box(page, lead, 48, y, 1184, page.t['lead'], bold=True, name='lead', spacing=1.2) + 10
    context = '\n'.join(str(slide[k]) for k in ('context', 'source') if slide.get(k))
    if context:
        y += _box(page, context, 48, y, 1184, page.t['note'], color='secondary', name='context') + 10
    return y


def _draw_support(page, slide, y):
    if not _support(slide):
        return
    page.rule(48, y - 9, 1184, color='gold', width=1.4)
    for i, (label, text) in enumerate(_support(slide)):
        value = (label + '　' if label else '') + text
        y += _box(page, value, 48, y, 1184, page.t['label'], color='ink',
                  name=f'content-support-{i}') + 8


def render_content_layout(deck, slide, tier, layout=None):
    """完整材料单元自动续页；共同尺度跨续页保持一致。"""
    layout = layout or choose_content_layout(slide)
    validate_content_slide(slide, layout)
    t = TIERS[tier]
    source_title = slide.get('source_title', '原始材料')
    if layout == 'annotated':
        units = slide['source_blocks']
        _, _, heights = _annotated_geometry(t, units, slide['annotations'], 1184)
        heading = _height(source_title, 1184 * .60 - 48, t['label']) + 35
    elif layout == 'revision':
        units = slide['changes']
        widths, _, heights = _revision_geometry(t, units, 1184)
        heading = max(_height(v, w, t['label']) for v, w in zip(
            (slide.get('before_label', '原稿'), slide.get('after_label', '修订稿'), '修改依据'), widths)) + 16
    else:
        units = slide['options']
        metric = dict(slide['metric'])
        metric['max'] = metric.get('max', max(option['value'] for option in units) or 1)
        widths, _, heights = _tradeoff_geometry(t, units, 1184, metric)
        heading = max(_height(v, w, t['label']) for v, w in zip(
            (f'{metric["label"]}（{metric["unit"]}）', '适用问题', '其他代价', '成立条件'), widths)) + 18
    start_y = 112 + _header_height(slide, t)
    support_h = _support_height(slide, t)
    # Reserve the complete support statement on every continuation, making the
    # condition travel with excerpts instead of orphaning it on a final slide.
    available = 650 - start_y - support_h - (22 if support_h else 0)
    content_capacity = available - heading
    if content_capacity <= 0:
        raise ValueError(f'页面“{slide.get("title")}”概论与补充说明占满正文；请重组或拆成独立页面。')
    chunks, current, used = [], [], 0
    for index, (unit, required) in enumerate(zip(units, heights)):
        if required > content_capacity:
            raise ValueError(f'页面“{slide.get("title")}”第{index + 1}个完整材料单元过长；请扩展为相邻页，不会裁字或缩字。')
        if current and used + required > content_capacity:
            chunks.append(current); current, used = [], 0
        current.append(unit); used += required
    if current:
        chunks.append(current)
    pages = []
    for page_index, chunk in enumerate(chunks):
        title = slide['title'] + (f'（续{page_index}）' if page_index else '')
        page = deck.page(title, tier=tier)
        actual_y = _draw_header(page, slide)
        if layout == 'annotated':
            ids = {block['id'] for block in chunk}
            notes = [note for note in slide['annotations'] if note['target'] in ids]
            draw_annotated(page, chunk, notes, y=actual_y, h=available, source_title=source_title)
        elif layout == 'revision':
            draw_revision(page, chunk, y=actual_y, h=available,
                          before_label=slide.get('before_label', '原稿'),
                          after_label=slide.get('after_label', '修订稿'))
        else:
            draw_tradeoff(page, chunk, metric, y=actual_y, h=available)
        if support_h:
            _draw_support(page, slide, 650 - support_h)
        page.page_number()
        pages.append(page)
    return pages
