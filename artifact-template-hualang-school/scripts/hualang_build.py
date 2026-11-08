#!/usr/bin/env python3
"""华朗学校整稿构建器：deck-spec JSON -> 原生可编辑 PPTX。

内容策划由 WorkBuddy 完成；本脚本负责场景路由、分页、版式、表格、
首尾、页码和可选点击出现。不会替用户虚构学校事实或数据。
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from pptx.enum.text import MSO_ANCHOR
from pptx.util import Pt

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
sys.path.insert(0, str(HERE))

from hualang_deck import (  # noqa: E402
    COLORS, Deck, EMU, _rect, _textbox, _write, text_height,
)
from hualang_tables import draw_table, plan_table, table_report  # noqa: E402

SCENARIOS = {
    'internal_report': {
        'label': '校务决策与内部汇报', 'tier': 'read',
        'layouts': ['comparison', 'table', 'metrics', 'bars', 'timeline', 'process'],
        'closing': '汇报完毕，敬请指导',
    },
    'lesson_plan': {
        'label': '教师教案与说课', 'tier': 'read',
        'layouts': ['activity', 'lesson', 'table', 'process', 'evidence'],
        'closing': '以学定教，共同研磨',
    },
    'classroom': {
        'label': '学生课堂', 'tier': 'near',
        'layouts': ['lesson', 'evidence', 'comparison', 'process', 'table'],
        'closing': '华夏俊采，朗若星辰',
    },
    'practice': {
        'label': '练习复习与检测', 'tier': 'read',
        'layouts': ['practice', 'comparison', 'table', 'lesson'],
        'closing': '独立完成，及时订正',
    },
    'parent_growth': {
        'label': '个体家长成长反馈', 'tier': 'near',
        'layouts': ['evidence', 'comparison', 'process', 'table'],
        'closing': '看见成长，协同支持',
    },
    'parent_meeting': {
        'label': '班级家长会与家校协同', 'tier': 'near',
        'layouts': ['statement', 'metrics', 'timeline', 'process', 'table', 'evidence'],
        'closing': '家校同行，共育成长',
    },
    'admissions': {
        'label': '招生开放日与课程选择', 'tier': 'far',
        'layouts': ['statement', 'image', 'metrics', 'comparison', 'timeline', 'table'],
        'closing': '期待在华朗相见',
    },
    'public_address': {
        'label': '公众成果发布与主题演讲', 'tier': 'far',
        'layouts': ['statement', 'image', 'metrics', 'evidence', 'process'],
        'closing': '感谢聆听，期待同行',
    },
}

ALIASES = {
    'internal': 'internal_report', 'report': 'internal_report', '内部': 'internal_report',
    '内部汇报': 'internal_report', '校务': 'internal_report', '管理汇报': 'internal_report',
    'lessonplan': 'lesson_plan', 'teaching_plan': 'lesson_plan', '教案': 'lesson_plan',
    '说课': 'lesson_plan', '教师备课': 'lesson_plan',
    'lesson': 'classroom', '课堂': 'classroom', '学生课堂': 'classroom', '课件': 'classroom',
    'worksheet': 'practice', '练习': 'practice', '复习': 'practice', '检测': 'practice',
    'parent': 'parent_growth', '家长反馈': 'parent_growth', '成长反馈': 'parent_growth',
    '家长会': 'parent_meeting', '家校协同': 'parent_meeting', '班级家长': 'parent_meeting',
    '招生': 'admissions', '开放日': 'admissions', '招生宣讲': 'admissions',
    'public': 'public_address', '公众': 'public_address', '公众演讲': 'public_address',
    '成果发布': 'public_address', '品牌发布': 'public_address',
}

IMAGE_LAYOUTS = {'statement', 'image', 'evidence'}


def resolve_scenario(value):
    key = str(value or '').strip()
    key = ALIASES.get(key, key)
    if key not in SCENARIOS:
        raise ValueError('未知场景：%s。可选：%s' % (value, '、'.join(SCENARIOS)))
    return key


def resolve_tier(slide, scenario):
    explicit = slide.get('tier') or slide.get('usage')
    if explicit:
        if explicit not in ('read', 'near', 'far'):
            raise ValueError('页面 tier 仅支持 read / near / far。')
        return explicit
    layout = choose_layout(slide)
    if scenario == 'admissions' and layout in ('table', 'timeline', 'comparison'):
        return 'near'
    if scenario == 'parent_meeting' and layout == 'table':
        return 'near'
    return SCENARIOS[scenario]['tier']


def choose_layout(slide):
    layout = slide.get('layout', 'auto')
    if layout != 'auto':
        return layout
    if slide.get('table'):
        return 'table'
    if slide.get('questions'):
        return 'practice'
    if slide.get('task') or slide.get('prompts'):
        return 'lesson'
    if slide.get('metrics'):
        return 'metrics'
    if slide.get('series'):
        return 'bars'
    if slide.get('left') or slide.get('right'):
        return 'comparison'
    steps = slide.get('steps') or []
    if steps:
        if any(isinstance(s, dict) and (s.get('expected') or s.get('feedback')) for s in steps):
            return 'activity'
        if any(isinstance(s, dict) and s.get('date') for s in steps):
            return 'timeline'
        return 'process'
    if slide.get('image'):
        return 'evidence'
    return 'statement'


def validate_spec(spec):
    if not isinstance(spec, dict):
        raise ValueError('页面规格必须是 JSON 对象。')
    if not str(spec.get('title', '')).strip():
        raise ValueError('缺少正式题名 title。')
    scenario = resolve_scenario(spec.get('scenario'))
    content_only = bool(spec.get('content_only', False))
    if not content_only:
        if not str(spec.get('presenter', '')).strip() or not str(spec.get('date', '')).strip():
            raise ValueError('完整稿必须提供 presenter 和 date；不得虚构署名或日期。')
    slides = spec.get('slides')
    if not isinstance(slides, list) or not slides:
        raise ValueError('slides 至少需要一页正文。')
    for i, slide in enumerate(slides, 1):
        if not isinstance(slide, dict):
            raise ValueError(f'第 {i} 页规格必须是对象。')
        layout = choose_layout(slide)
        known = {'auto', 'statement', 'section', 'comparison', 'table', 'timeline', 'process',
                 'evidence', 'lesson', 'activity', 'practice', 'metrics', 'bars', 'image'}
        if layout not in known:
            raise ValueError(f'第 {i} 页使用未知版式：{layout}')
        if layout != 'image' and not str(slide.get('title', '')).strip():
            raise ValueError(f'第 {i} 页缺少具体题名 title。')
        resolve_tier(slide, scenario)
        limits = {
            'statement': {'items': 3}, 'section': {'items': 3},
            'image': {'items': 3}, 'metrics': {'metrics': 4},
            'bars': {'series': 7}, 'evidence': {'items': 4},
            'lesson': {'prompts': 4, 'feedback_items': 3},
        }
        for field, limit in limits.get(layout, {}).items():
            values = slide.get(field) or []
            if not isinstance(values, list):
                raise ValueError(f'第 {i} 页 {field} 必须是列表。')
            if len(values) > limit:
                raise ValueError(f'第 {i} 页 {field} 有 {len(values)} 项，当前版式最多 {limit} 项；'
                                 '请拆成续页，不会截断输入。')
        if layout in ('statement', 'section', 'image'):
            tier = resolve_tier(slide, scenario)
            if slide.get('bleed', tier == 'far') and slide.get('items'):
                raise ValueError(f'第 {i} 页出血主视觉版式不接收 items；'
                                 '请将观察要点拆成续页，不能省略。')
        if layout == 'comparison':
            for side in ('left', 'right'):
                values = (slide.get(side) or {}).get('items') or []
                if not isinstance(values, list) or len(values) > 3:
                    raise ValueError(f'第 {i} 页 {side}.items 最多 3 项；请拆成续页。')
        if layout == 'bars':
            values = []
            for index, item in enumerate(slide.get('series') or [], 1):
                value = item.get('value')
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise ValueError(f'第 {i} 页 series 第 {index} 项 value 必须是有限数值。')
                if value < 0:
                    raise ValueError(f'第 {i} 页包含负数，当前横条版式只支持非负数；'
                                     '请改用保留符号的表格或定制带零基线的图表。')
                values.append(value)
            if 'max_value' in slide:
                maximum = slide['max_value']
                if (isinstance(maximum, bool) or not isinstance(maximum, (int, float))
                        or not math.isfinite(maximum) or maximum <= 0
                        or maximum < max(values, default=0)):
                    raise ValueError(f'第 {i} 页 max_value 必须是正数且不小于所有数值；'
                                     '请调整共同尺度，不能让横条越界。')
    return scenario


def asset_path(value):
    if not value:
        return None
    p = Path(str(value)).expanduser()
    if not p.is_absolute():
        p = SKILL / p
    return p.resolve()


def text_box(page, text, x, y, w, h=None, size=None, color='ink', bold=False,
             align='l', spacing=1.35, name=None, anchor='top', fixed_spacing=False):
    size = size or page.t['body']
    h = h or text_height(text, w, size, spacing)
    box = _textbox(page.slide, x, y, w, h, name=name, anchor=anchor)
    _write(box.text_frame, text, size, color, bold=bold, line_spacing=spacing, align=align)
    if fixed_spacing:
        # Absolute line pitch avoids font-metric multipliers differing by renderer.
        for paragraph in box.text_frame.paragraphs:
            paragraph.line_spacing = Pt(size * spacing * 0.75)
    return box


def shape_name(shape, name):
    if shape is not None and name:
        shape.name = name
    return shape


def image_or_slot(page, spec, x, y, w, h, name='evidence-image'):
    value = spec.get('image')
    path = asset_path(value)
    if path:
        if not path.exists():
            raise FileNotFoundError(f'图片不存在：{path}')
        pic = page.image(path, x, y, w, h, cover=spec.get('fit', 'cover') != 'contain',
                         focus=tuple(spec.get('focus', [0.5, 0.5])))
        pic.name = name
        return pic
    frame = page.panel(x, y, w, h, fill='pale', name=name)
    title = spec.get('image_title') or '待补真实场景图片'
    brief = spec.get('image_brief') or '说明需要补入的人物、动作、作品或证据，以及图片用途。'
    text_box(page, title, x + 32, y + h / 2 - 52, w - 64, 36,
             size=page.t['subhead'], color='purple', bold=True, align='c')
    text_box(page, brief, x + 32, y + h / 2, w - 64, 72,
             size=page.t['note'], color='secondary', align='c')
    return frame


def base_page(deck, slide, scenario, title=None):
    tier = resolve_tier(slide, scenario)
    page = deck.page(title or slide.get('title') or slide.get('lead') or '主题页', tier=tier)
    return page


def add_lead_context(page, slide, start_y=112):
    y = start_y
    lead = str(slide.get('lead') or slide.get('summary') or '').strip()
    if lead:
        h = text_height(lead, 1184, page.t['lead'], 1.2)
        page.lead(lead, y=y)
        y += max(48, h + 16)
    context = str(slide.get('context') or slide.get('source') or '').strip()
    if context:
        page.context(context, y=y)
        y += max(32, text_height(context, 1184, page.t['note'], 1.4) + 8)
    return y


def final_slide_index(deck):
    return len(deck._pages) if deck.content_only else len(deck._pages) + 1


def add_reveal(manifest, deck, steps):
    if not steps:
        return
    manifest['slides'].append({'slide': final_slide_index(deck), 'steps': steps})


def render_statement(deck, slide, scenario, manifest):
    tier = resolve_tier(slide, scenario)
    image = asset_path(slide.get('image'))
    full_bleed = bool(slide.get('bleed', tier == 'far'))
    if full_bleed:
        if tier != 'far':
            raise ValueError('整页出血仅用于 far 档；请将本页改为 far 或取消 bleed。')
        page = deck.bleed_page(tier='far', fill='purple')
        right_side = slide.get('text_side', 'left') == 'right'
        tx = 532 if right_side else 148
        body_x = 572 if right_side else 148
        brand_x = 1000 if right_side else 148
        rule_x = 1068 if right_side else 148
        if image:
            if not image.exists():
                raise FileNotFoundError(f'图片不存在：{image}')
            page.image(image, 0, 0, 1280, 720, focus=tuple(slide.get('focus', [0.5, 0.5])))
            page.scrim(0, 0, 1280, 720,
                       [(0.0, 0.92), (0.30, 0.86), (0.50, 0.48), (0.72, 0.10)],
                       angle=180 if right_side else 0)
        page.brand_mark(brand_x, 44, 132)
        lead = slide.get('lead') or slide.get('title')
        lead_h = text_height(lead, 600, 64, 1.18)
        text_box(page, lead, tx, 176, 600, lead_h, size=64, color='white', bold=True,
                 spacing=1.18, name='statement-lead', fixed_spacing=True)
        body_y = max(392, 176 + lead_h + 24)
        body_h = text_height(slide['body'], 560, 34, 1.4) if slide.get('body') else 0
        if slide.get('body'):
            text_box(page, slide['body'], body_x, body_y, 560, body_h, size=34,
                     color='F0ECF5', spacing=1.4, name='statement-body', fixed_spacing=True)
        rule_y = max(526, body_y + body_h + 24)
        context = slide.get('context') or slide.get('source') or ''
        context_y = rule_y + 22
        context_h = text_height(context, 560, 20, 1.35) if context else 0
        if (context_y + context_h if context else rule_y) > 650:
            raise ValueError(f'主视觉页“{slide.get("title")}”完整主张与说明超出可用高度；'
                             '请拆成续页，不会删除文字或压住页码。')
        page.rule(rule_x, rule_y, 64, color='gold', width=2)
        if context:
            text_box(page, context, body_x, context_y, 560, context_h, size=20,
                     color='D9D1DE', spacing=1.35, name='statement-context', fixed_spacing=True)
        if right_side:
            text_box(page, f'{page.number:02d}', body_x, 677, 120, 24, size=14, color='white')
        else:
            page.page_number(light=True)
        return [page]

    if image or (slide.get('layout') == 'image'
                 and (slide.get('image_title') or slide.get('image_brief'))):
        return render_evidence(deck, slide, scenario, manifest)
    page = base_page(deck, slide, scenario)
    page.gold_rule(48, 128, 64)
    lead = slide.get('lead') or slide.get('body') or slide.get('title')
    size = page.t['lead'] if tier != 'far' else 58
    text_box(page, lead, 48, 168, 1080, 180, size=size, color='purple', bold=True, spacing=1.2)
    items = slide.get('items') or []
    if items:
        width = 1080 / min(3, len(items))
        for i, item in enumerate(items):
            x = 48 + i * width
            text_box(page, item.get('title', ''), x, 424, width - 32, 40,
                     size=page.t['subhead'], color='purple', bold=True)
            text_box(page, item.get('body', ''), x, 480, width - 32, 112,
                     size=page.t['body'], color='ink')
    elif slide.get('body') and slide.get('lead'):
        text_box(page, slide['body'], 48, 382, 980, 150, size=page.t['body'])
    if slide.get('context'):
        page.context(slide['context'], y=604)
    page.page_number()
    return [page]


def render_comparison(deck, slide, scenario, manifest):
    page = base_page(deck, slide, scenario)
    y = add_lead_context(page, slide)
    y = max(y, 196 if slide.get('lead') else 128)
    left = slide.get('left') or {'title': slide.get('left_title', '现状'), 'body': slide.get('left_body', '')}
    right = slide.get('right') or {'title': slide.get('right_title', '方案'), 'body': slide.get('right_body', '')}
    split = slide.get('split', 0.5)
    left_w = int(1184 * split) - 24
    right_x = 48 + left_w + 48
    right_w = 1232 - right_x
    for idx, (item, x, w) in enumerate(((left, 48, left_w), (right, right_x, right_w))):
        if item.get('fill', idx == 1):
            page.panel(x, y, w, 620 - y, fill=item.get('fill', 'pale'))
            ix = x + 24
            iw = w - 48
        else:
            ix, iw = x, w
        text_box(page, item.get('title', ''), ix, y + 24, iw, 42,
                 size=page.t['subhead'], color=item.get('color', 'purple'), bold=True)
        page.rule(ix, y + 82, min(64, iw), color='gold', width=2)
        body = item.get('body', '')
        body_h = text_height(body, iw, page.t['body'], 1.5)
        if y + 108 + body_h > 620:
            raise ValueError(f'比较页“{slide.get("title")}”主体文字超出可用高度；请拆成续页。')
        text_box(page, body, ix, y + 108, iw, body_h,
                 size=page.t['body'], color='ink', spacing=1.5)
        bullets = item.get('items') or []
        by = y + 108 + body_h + 24
        for bullet in bullets:
            text = '— ' + (bullet if isinstance(bullet, str) else bullet.get('body', ''))
            bullet_h = text_height(text, iw, page.t['label'], 1.35)
            if by + bullet_h > 620:
                raise ValueError(f'比较页“{slide.get("title")}”补充要点超出可用高度；请拆成续页。')
            text_box(page, text, ix, by, iw, bullet_h,
                     size=page.t['label'], color='secondary')
            by += bullet_h + 16
    page.page_number()
    return [page]


def table_measure(slide):
    """统一扣除概论、口径、表题和来源，防止页底重叠。"""
    spec = slide.get('table') or {}
    reserved = 188 if slide.get('lead') else 128
    if slide.get('context'):
        reserved += 32
    caption_space = 40 if spec.get('caption') else 0
    source_space = 40 if spec.get('source') or slide.get('source') else 0
    return reserved, 616 - reserved - caption_space - source_space


def render_table(deck, slide, scenario, manifest):
    spec = dict(slide.get('table') or {})
    tier = resolve_tier(slide, scenario)
    reserved, max_height = table_measure(slide)
    chunks = plan_table(spec, 1184, max_height, tier)
    pages = []
    for i, chunk in enumerate(chunks):
        current = dict(slide)
        if i:
            current['title'] = str(slide.get('title')) + '（续）'
            current['lead'] = ''
            current['context'] = '续表 · 字段、单位与统计口径保持不变'
        page = base_page(deck, current, scenario)
        y = add_lead_context(page, current)
        y = max(y, reserved)
        caption = spec.get('caption')
        if caption and i == 0:
            text_box(page, caption, 48, y, 1184, 32, size=page.t['label'],
                     color='purple', bold=True)
            y += 40
        shape = draw_table(page, chunk, 48, y, tier)
        shape.name = f'table-{final_slide_index(deck)}-{i + 1}'
        source = spec.get('source') or slide.get('source')
        if source:
            text_box(page, source, 48, y + chunk['height'] + 12, 1184, 28,
                     size=page.t['note'], color='secondary')
        page.page_number()
        pages.append(page)
    return pages


def render_metrics(deck, slide, scenario, manifest):
    page = base_page(deck, slide, scenario)
    y = add_lead_context(page, slide)
    metrics = slide.get('metrics') or []
    if not metrics:
        raise ValueError('metrics 版式至少需要一个指标。')
    count = len(metrics)
    gap = 32
    w = (1184 - gap * (count - 1)) / count
    y = max(y, 168)
    for i, metric in enumerate(metrics):
        x = 48 + i * (w + gap)
        page.rule(x, y, w, color='gold' if i == slide.get('focus', 0) else 'line', width=2)
        text_box(page, str(metric.get('value', '')), x, y + 32, w, 88,
                 size=64 if page.tier == 'far' else 54,
                 color='purple' if i != slide.get('focus', 0) else 'red', bold=True)
        text_box(page, metric.get('label', ''), x, y + 132, w, 48,
                 size=page.t['subhead'], color='ink', bold=True)
        if metric.get('note'):
            text_box(page, metric['note'], x, y + 196, w, 90,
                     size=page.t['note'], color='secondary')
    if slide.get('body'):
        text_box(page, slide['body'], 48, 494, 1184, 104, size=page.t['body'])
    if slide.get('context'):
        page.context(slide['context'], y=620)
    page.page_number()
    return [page]


def render_bars(deck, slide, scenario, manifest):
    page = base_page(deck, slide, scenario)
    y = add_lead_context(page, slide)
    series = slide.get('series') or []
    if not series:
        raise ValueError('bars 版式需要 series。')
    max_value = slide.get('max_value') or max(float(s['value']) for s in series) or 1
    y = max(y, 184)
    row_h = min(86, int(400 / max(1, len(series))))
    for i, item in enumerate(series):
        yy = y + i * row_h
        text_box(page, item.get('label', ''), 48, yy, 208, 38,
                 size=page.t['label'], color='ink', bold=True)
        page.rule(280, yy + 8, 700, color='EDEDED', width=24)
        value = float(item['value'])
        width = max(2, 700 * value / max_value)
        page.rule(280, yy + 8, width, color=item.get('color', 'purple'), width=24)
        text_box(page, item.get('display', str(item.get('value', ''))), 1004, yy, 228, 38,
                 size=page.t['label'], color=item.get('color', 'purple'), bold=True, align='r')
    if slide.get('body'):
        text_box(page, slide['body'], 48, min(596, y + len(series) * row_h + 24), 1184, 70,
                 size=page.t['body'])
    page.page_number()
    return [page]


def render_timeline(deck, slide, scenario, manifest):
    steps = slide.get('steps') or []
    if not steps:
        raise ValueError('timeline 版式需要 steps。')
    tier = resolve_tier(slide, scenario)
    per_page = 4 if tier != 'read' else 5
    groups = [steps[i:i + per_page] for i in range(0, len(steps), per_page)]
    pages = []
    for gi, group in enumerate(groups):
        current = dict(slide)
        if gi:
            current['title'] = str(slide.get('title')) + '（续）'
            current['lead'] = ''
        page = base_page(deck, current, scenario)
        y = add_lead_context(page, current)
        y = max(y, 240)
        page.rule(96, y + 100, 1088, color='gold', width=2)
        gap = 1088 / max(1, len(group) - 1) if len(group) > 1 else 0
        for i, item in enumerate(group):
            x = 96 + i * gap if len(group) > 1 else 640
            page.dot(x, y + 100, 8, 'purple')
            w = min(240, 1088 / len(group) - 16)
            tx = max(48, min(1232 - w, x - w / 2))
            text_box(page, item.get('date', ''), tx, y + 20, w, 36,
                     size=page.t['label'], color='purple', bold=True, align='c')
            text_box(page, item.get('title', item.get('label', '')), tx, y + 140, w, 48,
                     size=page.t['subhead'], color='ink', bold=True, align='c')
            text_box(page, item.get('body', item.get('detail', '')), tx, y + 204, w, 112,
                     size=page.t['note'], color='secondary', align='c')
        if slide.get('body') and gi == len(groups) - 1:
            text_box(page, slide['body'], 48, 590, 1184, 52, size=page.t['body'])
        page.page_number()
        pages.append(page)
    return pages


def render_process(deck, slide, scenario, manifest):
    steps = slide.get('steps') or []
    if not steps:
        raise ValueError('process 版式需要 steps。')
    tier = resolve_tier(slide, scenario)
    per_page = 4 if tier != 'read' else 5
    groups = [steps[i:i + per_page] for i in range(0, len(steps), per_page)]
    pages = []
    for gi, group in enumerate(groups):
        current = dict(slide)
        if gi:
            current['title'] = str(slide.get('title')) + '（续）'
            current['lead'] = ''
        page = base_page(deck, current, scenario)
        y = add_lead_context(page, current)
        y = max(y, 160)
        horizontal = tier != 'read' and len(group) <= 4
        reveal_steps = []
        if horizontal:
            gap = 24
            w = (1184 - gap * (len(group) - 1)) / len(group)
            for i, item in enumerate(group):
                x = 48 + i * (w + gap)
                objects = []
                marker = page.panel(x, y, 48, 48, fill='purple')
                objects.append(shape_name(marker, f'process-{gi}-{i}-marker'))
                number = text_box(page, str(gi * per_page + i + 1).zfill(2), x, y + 7, 48, 30,
                                  size=page.t['label'], color='white', bold=True, align='c',
                                  name=f'process-{gi}-{i}-number')
                objects.append(number)
                objects.append(text_box(page, item.get('title', ''), x, y + 72, w, 56,
                                        size=page.t['subhead'], color='purple', bold=True,
                                        name=f'process-{gi}-{i}-title'))
                objects.append(text_box(page, item.get('body', item.get('detail', '')), x, y + 148, w, 190,
                                        size=page.t['body'], spacing=1.45,
                                        name=f'process-{gi}-{i}-body'))
                if current.get('reveal'):
                    reveal_steps.append({'label': item.get('title', f'步骤{i + 1}'),
                                         'objects': [o.name for o in objects]})
        else:
            available = 610 - y
            row_h = min(104, available / len(group))
            for i, item in enumerate(group):
                yy = y + i * row_h
                marker = page.panel(48, yy, 56, 56, fill='purple',
                                    name=f'process-{gi}-{i}-marker')
                number = text_box(page, str(gi * per_page + i + 1).zfill(2), 48, yy + 10, 56, 30,
                                  size=page.t['label'], color='white', bold=True, align='c',
                                  name=f'process-{gi}-{i}-number')
                title = text_box(page, item.get('title', ''), 128, yy, 280, 44,
                                 size=page.t['subhead'], color='purple', bold=True,
                                 name=f'process-{gi}-{i}-title')
                body = text_box(page, item.get('body', item.get('detail', '')), 424, yy, 808, row_h - 8,
                                size=page.t['body'], spacing=1.35,
                                name=f'process-{gi}-{i}-body')
                if current.get('reveal'):
                    reveal_steps.append({'label': item.get('title', f'步骤{i + 1}'),
                                         'objects': [marker.name, number.name, title.name, body.name]})
                if i < len(group) - 1:
                    page.rule(128, yy + row_h - 12, 1104, color='line', width=1)
        if current.get('reveal'):
            add_reveal(manifest, deck, reveal_steps)
        page.page_number()
        pages.append(page)
    return pages


def render_evidence(deck, slide, scenario, manifest):
    tier = resolve_tier(slide, scenario)
    orientation = slide.get('orientation', 'left')
    image_w = 720 if tier == 'read' else 744
    image_x = 48 if orientation == 'left' else 1232 - image_w
    notes_x = 48 + image_w + 48 if orientation == 'left' else 48
    notes_w = 1232 - notes_x if orientation == 'left' else image_x - 96
    pages = []

    def new_page(continued=False):
        current = dict(slide)
        if continued:
            current['title'] = str(slide.get('title')) + '（续）'
            current['lead'] = current['summary'] = ''
            current['context'] = '续页 · 保持同一作品及观察口径'
        page = base_page(deck, current, scenario)
        y = max(add_lead_context(page, current), 144)
        if 560 - y < 160:
            raise ValueError(f'证据页“{slide.get("title")}”概论与口径占用过多；请拆成续页。')
        image_or_slot(page, slide, image_x, y, image_w, 560 - y)
        if slide.get('caption'):
            text_box(page, slide['caption'], image_x, 574, image_w, 42,
                     size=page.t['note'], color='secondary')
        pages.append(page)
        return page, y

    page, yy = new_page()
    items = slide.get('items') or []
    if not items and slide.get('body'):
        items = [{'title': slide.get('note_title', '观察重点'), 'body': slide['body']}]
    bottom = 506 if slide.get('action') else 620
    count_on_page = 0
    for i, item in enumerate(items):
        title_h = text_height(item.get('title', ''), notes_w, page.t['subhead'], 1.35)
        body_h = text_height(item.get('body', ''), notes_w, page.t['body'], 1.4)
        required = title_h + 12 + body_h
        if yy + required > bottom and count_on_page:
            page.page_number()
            page, yy = new_page(continued=True)
            count_on_page = 0
        if yy + required > bottom:
            raise ValueError(f'证据页“{slide.get("title")}”第 {i + 1} 个观察项超出可用高度；'
                             '请拆分该观察项，保留图像及完整观察内容。')
        text_box(page, item.get('title', ''), notes_x, yy, notes_w, title_h,
                 size=page.t['subhead'], color=item.get('color', 'purple'), bold=True)
        text_box(page, item.get('body', ''), notes_x, yy + title_h + 12, notes_w, body_h,
                 size=page.t['body'], spacing=1.4)
        yy += required + 24
        count_on_page += 1
    if slide.get('action'):
        page.panel(notes_x, 522, notes_w, 96, fill='pale')
        action_h = text_height(slide['action'], notes_w - 48, page.t['label'], 1.35)
        if action_h > 64:
            raise ValueError(f'证据页“{slide.get("title")}”行动内容过长；请拆成续页。')
        text_box(page, slide['action'], notes_x + 24, 540, notes_w - 48, 64,
                 size=page.t['label'], color='purple', bold=True)
    page.page_number()
    return pages


def render_activity(deck, slide, scenario, manifest):
    steps = slide.get('steps') or []
    if not steps:
        raise ValueError('activity 版式需要 steps，且应包含 task / expected / feedback。')
    groups = [steps[i:i + 3] for i in range(0, len(steps), 3)]
    pages = []
    for gi, group in enumerate(groups):
        current = dict(slide)
        if gi:
            current['title'] = str(slide.get('title')) + '（续）'
            current['lead'] = ''
        page = base_page(deck, current, scenario)
        y = add_lead_context(page, current)
        y = max(y, 144)
        headers = [('时间', 48, 88), ('学习任务', 144, 400), ('预期回应', 560, 320), ('评价与调整', 896, 336)]
        for label, x, w in headers:
            text_box(page, label, x, y, w, 32, size=page.t['label'], color='purple', bold=True)
        page.rule(48, y + 42, 1184, color='gold', width=2)
        row_h = min(150, (610 - y - 48) / len(group))
        for i, item in enumerate(group):
            yy = y + 58 + i * row_h
            if i % 2 == 0:
                page.panel(48, yy - 8, 1184, row_h - 4, fill='F7F5F9')
            text_box(page, item.get('time', '—'), 48, yy + 8, 88, 40,
                     size=page.t['label'], color='purple', bold=True)
            text_box(page, item.get('task', item.get('title', '')), 144, yy + 8, 400, row_h - 20,
                     size=page.t['body'], bold=True)
            text_box(page, item.get('expected', '待课堂观察'), 560, yy + 8, 320, row_h - 20,
                     size=page.t['label'], color='ink')
            text_box(page, item.get('feedback', item.get('body', '依据学生回应调整')), 896, yy + 8, 336, row_h - 20,
                     size=page.t['label'], color='ink')
        page.page_number()
        pages.append(page)
    return pages


def render_lesson(deck, slide, scenario, manifest):
    page = base_page(deck, slide, scenario)
    task = slide.get('task') or slide.get('lead')
    if not task:
        raise ValueError('课堂页需要完整学习任务 task。')
    task_h = max(86, text_height(task, 1080, page.t['body'], 1.3) + 30)
    page.band(48, 112, 1184, task_h, task, fill='purple', size=page.t['body'])
    y = 112 + task_h + 24
    prompts = slide.get('prompts') or []
    has_work = bool(slide.get('work') or slide.get('body') or slide.get('image'))
    work_w = 744 if prompts else 1184
    if slide.get('image') or not has_work:
        image_or_slot(page, slide, 48, y, work_w, 590 - y)
    else:
        work = slide.get('work') or slide.get('body')
        work_size = slide.get('work_size', page.t['subhead'])
        work_h = text_height(work, work_w, work_size, 1.45)
        work_bottom = 582 if slide.get('independent_task') else 620
        if y + work_h > work_bottom:
            raise ValueError(f'课堂页“{slide.get("title")}”完整学习对象超出可用高度；'
                             '请拆成续页或重新编排，不能遮盖任务或独立作答区。')
        text_box(page, work, 48, y, work_w, work_h,
                 size=work_size, color='ink',
                 bold=bool(slide.get('work_bold', False)), spacing=1.45,
                 name='lesson-work', fixed_spacing=True)
    reveal_steps = []
    if prompts:
        px = 840
        py = y
        for i, prompt in enumerate(prompts):
            if isinstance(prompt, str):
                prompt = {'body': prompt}
            body_h = max(40, text_height(prompt.get('body', ''), 336, page.t['body'], 1.35))
            bottom = 582 if slide.get('independent_task') else 620
            if py + body_h > bottom:
                raise ValueError(f'课堂页“{slide.get("title")}”第 {i + 1} 个提示超出可用高度；'
                                 '请拆成续页，保留独立作答区。')
            marker = page.panel(px, py, 40, 40, fill='pale')
            marker.name = f'lesson-{len(deck._pages)}-prompt-{i}-marker'
            num = text_box(page, str(i + 1), px, py + 5, 40, 28,
                           size=page.t['label'], color='purple', bold=True, align='c',
                           name=f'lesson-{len(deck._pages)}-prompt-{i}-number')
            body = text_box(page, prompt.get('body', ''), px + 56, py, 336, body_h,
                            size=page.t['body'], color=prompt.get('color', 'ink'),
                            bold=bool(prompt.get('bold', False)), spacing=1.35,
                            name=f'lesson-{len(deck._pages)}-prompt-{i}-body')
            if slide.get('reveal'):
                reveal_steps.append({'label': prompt.get('label', f'提示 {i + 1}'),
                                     'objects': [marker.name, num.name, body.name]})
            py += body_h + 24
    if slide.get('independent_task'):
        page.panel(48, 596, 1184, 54, fill='pale')
        text_box(page, '独立作答　' + slide['independent_task'], 72, 606, 1136, 36,
                 size=page.t['label'], color='purple', bold=True)
    if reveal_steps:
        add_reveal(manifest, deck, reveal_steps)
    page.page_number()
    pages = [page]
    answer = slide.get('answer')
    if answer:
        answer_slide = {
            'title': str(slide.get('title')) + '·反馈',
            'lead': slide.get('answer_lead', '依据关键条件核对作答，定位具体错误。'),
            'body': answer,
            'items': slide.get('feedback_items', []),
            'tier': page.tier,
            'layout': 'statement',
            'bleed': False,
        }
        pages.extend(render_statement(deck, answer_slide, scenario, manifest))
    return pages


def render_practice(deck, slide, scenario, manifest):
    questions = slide.get('questions') or []
    if not questions:
        raise ValueError('practice 版式需要 questions。')
    per_page = 2 if resolve_tier(slide, scenario) != 'read' else 3
    groups = [questions[i:i + per_page] for i in range(0, len(questions), per_page)]
    pages = []
    for gi, group in enumerate(groups):
        current = dict(slide)
        if gi:
            current['title'] = str(slide.get('title')) + '（续）'
        page = base_page(deck, current, scenario)
        y = add_lead_context(page, current)
        y = max(y, 128)
        row_h = (606 - y) / len(group)
        for i, question in enumerate(group):
            if isinstance(question, str):
                question = {'body': question}
            yy = y + i * row_h
            text_box(page, str(gi * per_page + i + 1).zfill(2), 48, yy, 64, 44,
                     size=page.t['subhead'], color='purple', bold=True)
            text_box(page, question.get('body', ''), 128, yy, 1104, row_h - 30,
                     size=page.t['body'], bold=bool(question.get('bold', False)), spacing=1.45)
            if question.get('hint'):
                text_box(page, '条件提示　' + question['hint'], 128, yy + row_h - 52, 1104, 34,
                         size=page.t['note'], color='secondary')
            if i < len(group) - 1:
                page.rule(128, yy + row_h - 12, 1104, color='line')
        page.page_number()
        pages.append(page)
    answers = slide.get('answers') or slide.get('answer')
    if answers:
        body = answers if isinstance(answers, str) else '\n'.join(
            f'{i + 1}. {a}' for i, a in enumerate(answers))
        feedback = {
            'title': str(slide.get('title')) + '·答案与判据',
            'lead': slide.get('answer_lead', '按作答证据核对，不只看最终答案。'),
            'body': body,
            'tier': resolve_tier(slide, scenario), 'layout': 'statement', 'bleed': False,
        }
        pages.extend(render_statement(deck, feedback, scenario, manifest))
    return pages


def build_deck(spec, out_path):
    scenario = validate_spec(spec)
    content_only = bool(spec.get('content_only', False))
    deck = Deck(SKILL / 'assets' / 'source-original.pptx',
                title=spec['title'], presenter=spec.get('presenter'), date=spec.get('date'),
                content_only=content_only)
    if not content_only:
        deck.set_closing_message(spec.get('closing_text') or SCENARIOS[scenario]['closing'])
    manifest = {'schemaVersion': 1, 'effect': 'appear', 'slides': []}
    all_tables = []
    page_log = []
    for source_index, slide in enumerate(spec['slides'], 1):
        layout = choose_layout(slide)
        if layout == 'table':
            table_spec = slide.get('table') or {}
            tier = resolve_tier(slide, scenario)
            _, max_height = table_measure(slide)
            all_tables.extend(plan_table(table_spec, 1184, max_height, tier))
        renderer = {
            'statement': render_statement, 'section': render_statement,
            'comparison': render_comparison, 'table': render_table,
            'metrics': render_metrics, 'bars': render_bars,
            'timeline': render_timeline, 'process': render_process,
            'evidence': render_evidence, 'image': render_statement,
            'activity': render_activity, 'lesson': render_lesson,
            'practice': render_practice,
        }.get(layout)
        if renderer is None:
            raise ValueError(f'暂不支持的版式：{layout}')
        before = len(deck._pages)
        pages = renderer(deck, slide, scenario, manifest)
        page_log.append({
            'source_slide': source_index, 'layout': layout,
            'generated_pages': len(deck._pages) - before,
            'tier': resolve_tier(slide, scenario),
        })
        if len(pages) != len(deck._pages) - before:
            raise RuntimeError('页数记录不一致，请检查构建器。')
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    warnings = []
    if scenario == 'internal_report' and not any(t['layout'] in ('table', 'metrics', 'bars', 'comparison') for t in page_log):
        warnings.append('内部汇报缺少比较、指标或表格页，请确认资料是否足以支持判断。')
    if scenario == 'lesson_plan' and not any(t['layout'] == 'activity' for t in page_log):
        warnings.append('教案缺少任务—预期回应—评价调整序列。')
    if scenario == 'parent_growth' and not any(t['layout'] == 'evidence' for t in page_log):
        warnings.append('个体家长反馈缺少作品或记录证据页。')
    if scenario in ('admissions', 'public_address') and not any(t['layout'] in ('statement', 'image', 'evidence') for t in page_log):
        warnings.append('对外稿缺少主视觉或证据页。')
    report = {
        'scenario': scenario, 'scenario_label': SCENARIOS[scenario]['label'],
        'body_pages': len(deck._pages), 'page_plan': page_log,
        'tables': table_report(all_tables), 'warnings': warnings,
        'animated_slides': len(manifest['slides']), 'output': str(out_path),
    }
    if manifest['slides']:
        base_path = out_path.with_name(out_path.stem + '.base.pptx')
        manifest_path = out_path.with_name(out_path.stem + '.reveals.json')
        deck.save(base_path)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        from apply_reveals import transform
        if out_path.exists():
            raise FileExistsError(f'带动画输出已存在，请换一个新文件名：{out_path}')
        transform(base_path, out_path, manifest)
        report['base_pptx'] = str(base_path)
        report['reveal_manifest'] = str(manifest_path)
    else:
        deck.save(out_path)
    report['size_bytes'] = out_path.stat().st_size
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', type=Path, required=True, help='deck-spec JSON 文件')
    parser.add_argument('--out', type=Path, required=True, help='输出 PPTX')
    parser.add_argument('--report', type=Path, help='可选构建报告 JSON')
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text(encoding='utf-8'))
    report = build_deck(spec, args.out)
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(payload, encoding='utf-8')
    print(payload)


if __name__ == '__main__':
    main()
