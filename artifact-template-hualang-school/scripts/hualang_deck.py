#!/usr/bin/env python3
"""华朗 PPTX 生产库（python-pptx 通道）。

设计依据：assets/style-contract.json 与 references/scene-visual-grammar.md。
坐标单位一律为逻辑像素（1280×720 画布，1px = 9525EMU = 0.75pt）。
字号入参为逻辑像素，内部换算为 pt：size_pt = px * 0.75。

用法::

    from hualang_deck import Deck, TIERS

    deck = Deck(template='assets/source-original.pptx',
                title='开放日费用与到场', presenter='市场部', date='2026年11月8日')
    p = deck.page('开放日费用与到场', tier='read')
    p.lead('费用增25%、实到增31.3%，B场每位实到费用低4.8%')
    p.context('模拟资料 · 非学校实绩')
    p.table(48, 200, [680, 484], rows, right_cols=[1])
    deck.save('成品.pptx')
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Pt

EMU = 9525
CANVAS = (1280, 720)
CONTENT = (48, 112, 1184, 538)

COLORS = {
    'purple': '403653',
    'ink': '222222',
    'secondary': '666666',
    'gold': 'BCA36D',
    'red': 'B4232C',
    'blue': '1B385B',
    'paper': 'FDFDFE',
    'pale': 'F0ECF5',
    'line': 'D8D8D8',
    'white': 'FFFFFF',
}

# 三档视觉密度：字号为逻辑像素
TIERS = {
    'read': {'title': 28, 'lead': 33, 'subhead': 26, 'body': 21,
             'label': 17, 'note': 14, 'table': 19, 'row': 46, 'head_row': 38},
    'near': {'title': 30, 'lead': 42, 'subhead': 32, 'body': 26,
             'label': 21, 'note': 17, 'table': 23, 'row': 46, 'head_row': 38},
    'far':  {'title': 30, 'lead': 64, 'subhead': 44, 'body': 34,
             'label': 26, 'note': 20, 'table': 26, 'row': 54, 'head_row': 44},
}

# 12 栏网格：步进 100（栏宽 84 + 间距 16），左边界 x = 48 + 100n
GRID_STEP = 100
GRID_ORIGIN = 48
GUTTER = 16
COL_WIDTH = 84


def col(n: int) -> int:
    """第 n 栏（0 基）的左边界。col(0)=48, col(7)=748。"""
    return GRID_ORIGIN + n * GRID_STEP


def span(start: int, end: int) -> tuple[int, int]:
    """从第 start 栏到第 end 栏（含）的 (x, w)。span(0, 5) -> (48, 584)。"""
    x = col(start)
    w = col(end) + COL_WIDTH - x
    return x, w


def fmt(color: str) -> RGBColor:
    """接受 COLORS 的名字（'purple'）或 6 位十六进制（'403653'）。"""
    key = COLORS.get(color, color)
    return RGBColor.from_string(key)


def _rpr_typeface(run, zh: str, latin: str):
    """同时写入 latin / ea / cs 字体，避免中文回落到主题字体。"""
    rpr = run._r.get_or_add_rPr()
    for tag, face in (('a:latin', latin), ('a:ea', zh), ('a:cs', latin)):
        el = rpr.find(qn(tag))
        if el is None:
            el = rpr.makeelement(qn(tag), {})
            rpr.append(el)
        el.set('typeface', face)


def _style_run(run, size_px: float, color: str = 'ink', bold: bool = False,
               zh: str = 'PingFang SC', latin: str = 'Arial', italic: bool = False):
    run.font.size = Pt(size_px * 0.75)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = fmt(color)
    _rpr_typeface(run, zh, latin)


def _textbox(slide, x, y, w, h, name=None, anchor='top', wrap=True):
    box = slide.shapes.add_textbox(Emu(int(x * EMU)), Emu(int(y * EMU)),
                                   Emu(int(w * EMU)), Emu(int(h * EMU)))
    tf = box.text_frame
    tf.word_wrap = wrap
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    tf.vertical_anchor = {'top': MSO_ANCHOR.TOP, 'middle': MSO_ANCHOR.MIDDLE,
                          'bottom': MSO_ANCHOR.BOTTOM}[anchor]
    if name:
        box.name = name
    return box


def _write(tf, lines, size_px, color='ink', bold=False, line_spacing=1.4,
           align='l', first=True, space_before=0):
    """lines: str 或 [(text, {size,color,bold,italic}) ...] 列表；支持 \\n 分段。"""
    align_map = {'l': PP_ALIGN.LEFT, 'r': PP_ALIGN.RIGHT, 'c': PP_ALIGN.CENTER}
    if isinstance(lines, str):
        lines = lines.split('\n')
    if lines and isinstance(lines[0], tuple):
        runs_spec = [lines]
    else:
        runs_spec = [[(ln, {})] for ln in lines]
    for i, runs in enumerate(runs_spec):
        p = tf.paragraphs[0] if (first and i == 0) else tf.add_paragraph()
        p.alignment = align_map[align]
        p.line_spacing = line_spacing
        p.space_before = Pt(space_before * 0.75)
        p.space_after = Pt(0)
        for text, opt in runs:
            r = p.add_run()
            r.text = text
            _style_run(r, opt.get('size', size_px), opt.get('color', color),
                       opt.get('bold', bold), italic=opt.get('italic', False))


def est_lines(text, width_px, size_px):
    """估算文本在给定宽度下的行数。中文按 1 字宽 = 字号，英文按 0.55。"""
    if isinstance(text, list):
        chunks = [''.join(r[0] for r in text)]
    else:
        chunks = str(text).split('\n')
    total = 0
    for c in chunks:
        if not c:
            total += 1
            continue
        w = 0.0
        for ch in c:
            w += 1.0 if ord(ch) > 0x2E80 else 0.55
        cap = max(1.0, width_px / size_px)
        total += max(1, int(w / cap) + (1 if w % cap else 0))
    return total


def text_height(text, width_px, size_px, spacing):
    return est_lines(text, width_px, size_px) * size_px * spacing + 6


def _rect(slide, x, y, w, h, color, name=None, line=None, line_w=1.0):
    shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Emu(int(x * EMU)), Emu(int(y * EMU)),
                                 Emu(int(w * EMU)), Emu(int(h * EMU)))
    shp.shadow.inherit = False
    if color:
        shp.fill.solid()
        shp.fill.fore_color.rgb = fmt(color)
    else:
        shp.fill.background()
    if line:
        shp.line.color.rgb = fmt(line)
        shp.line.width = Pt(line_w * 0.75)
    else:
        shp.line.fill.background()
    if name:
        shp.name = name
    shp.text_frame.word_wrap = True
    for m in ('margin_left', 'margin_right', 'margin_top', 'margin_bottom'):
        setattr(shp.text_frame, m, 0)
    return shp


def _cell_border(cell, color='D8D8D8', width_px=1.0, sides=('B',)):
    tcPr = cell._tc.get_or_add_tcPr()
    order = {qn(tag): index for index, tag in enumerate(_TCPR_ORDER)}
    for side in sides:
        tag = f'a:ln{side}'
        for el in list(tcPr.findall(qn(tag))):
            tcPr.remove(el)
        ln = tcPr.makeelement(qn(tag), {'w': str(int(width_px * EMU)), 'cap': 'flat',
                                        'cmpd': 'sng', 'algn': 'ctr'})
        fill = ln.makeelement(qn('a:solidFill' if color else 'a:noFill'), {})
        if color:
            clr = fill.makeelement(qn('a:srgbClr'), {'val': color})
            fill.append(clr)
        ln.append(fill)
        # 替换任意一侧后仍保持 L/R/T/B 与填充的 OOXML 顺序，调用者无需倒序。
        rank = order[ln.tag]
        for index, child in enumerate(tcPr):
            if order.get(child.tag, len(order)) > rank:
                tcPr.insert(index, ln)
                break
        else:
            tcPr.append(ln)


def _no_style(tbl):
    """清除默认样式，并显式关闭各边线，避免兼容渲染器补出黑色框线。"""
    tblPr = tbl._tbl.tblPr
    for attr in ('firstRow', 'bandRow', 'firstCol', 'lastRow', 'lastCol'):
        tblPr.set(attr, '0')
    style = tblPr.find(qn('a:tableStyleId'))
    if style is not None:
        tblPr.remove(style)
    for row in tbl.rows:
        for cell in row.cells:
            _cell_border(cell, color=None, sides=('L', 'R', 'T', 'B'))


def _set_cell(cell, text, size_px, color='ink', bold=False, align='l',
              fill=None, anchor='middle', inset=14, line_spacing=1.3):
    cell.fill.solid() if fill else cell.fill.background()
    if fill:
        cell.fill.fore_color.rgb = fmt(fill)
    cell.vertical_anchor = {'top': MSO_ANCHOR.TOP, 'middle': MSO_ANCHOR.MIDDLE}[anchor]
    cell.margin_left = Emu(int(inset * EMU))
    cell.margin_right = Emu(int(inset * EMU))
    cell.margin_top = 0
    cell.margin_bottom = 0
    tf = cell.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = {'l': PP_ALIGN.LEFT, 'r': PP_ALIGN.RIGHT, 'c': PP_ALIGN.CENTER}[align]
    p.line_spacing = line_spacing
    r = p.add_run()
    r.text = text
    _style_run(r, size_px, color, bold)



_SPPR_ORDER = ['a:xfrm', 'a:custGeom', 'a:prstGeom', 'a:noFill', 'a:solidFill', 'a:gradFill',
               'a:blipFill', 'a:pattFill', 'a:grpFill', 'a:ln', 'a:effectLst', 'a:effectDag',
               'a:scene3d', 'a:sp3d', 'a:extLst']
_TCPR_ORDER = ['a:lnL', 'a:lnR', 'a:lnT', 'a:lnB', 'a:lnTlToBr', 'a:lnBlToTr', 'a:cell3D',
               'a:noFill', 'a:solidFill', 'a:gradFill', 'a:blipFill', 'a:pattFill', 'a:grpFill',
               'a:headers', 'a:extLst']


def _check_order(el, order, label, errors):
    idx = []
    for child in el:
        tag = child.tag.split('}')[-1]
        full = 'a:' + tag
        if full in order:
            idx.append((order.index(full), full))
    for (i1, t1), (i2, t2) in zip(idx, idx[1:]):
        if i2 < i1:
            errors.append(f'{label}: {t2} 排在 {t1} 之后，违反 schema 顺序')


def validate_order(prs):
    """检查 spPr / tcPr 子元素顺序。PowerPoint 对顺序敏感，错了会触发修复。"""
    from lxml import etree
    errors = []
    for si, slide in enumerate(prs.slides, 1):
        for sp in slide._element.iter(qn('p:sp')):
            sppr = sp.find(qn('p:spPr'))
            if sppr is not None:
                nv = sp.find(qn('p:nvSpPr'))
                cnv = nv.find(qn('p:cNvPr')) if nv is not None else None
                nm = cnv.get('name') if cnv is not None else '?'
                _check_order(sppr, _SPPR_ORDER, f'第{si}页 {nm}', errors)
        for tc in slide._element.iter(qn('a:tc')):
            tcpr = tc.find(qn('a:tcPr'))
            if tcpr is not None:
                _check_order(tcpr, _TCPR_ORDER, f'第{si}页 表格单元格', errors)
    return errors


class Page:
    """一页正文。所有方法坐标为逻辑像素。"""

    def __init__(self, deck: 'Deck', slide, tier: str, number: int):
        self.deck = deck
        self.slide = slide
        self.tier = tier
        self.t = TIERS[tier]
        self.number = number
        self.bleed = False

    # ---- 文字 ----
    def title(self, text):
        box = _textbox(self.slide, 48, 30, 1010, 43, name='title', anchor='middle')
        _write(box.text_frame, text, self.t['title'], 'purple', bold=True, line_spacing=1.0)
        return self

    def lead(self, text, x=48, y=110, w=1184, runs=None, color='ink'):
        box = _textbox(self.slide, x, y, w,
                       text_height(runs or text, w, self.t['lead'], 1.2), name='lead')
        spec = runs if runs else text
        _write(box.text_frame, spec, self.t['lead'], color, bold=True, line_spacing=1.2)
        return self

    def subhead(self, text, x, y, w, color='purple'):
        box = _textbox(self.slide, x, y, w, text_height(text, w, self.t['subhead'], 1.25))
        _write(box.text_frame, text, self.t['subhead'], color, bold=True, line_spacing=1.25)
        return self

    def body(self, text, x, y, w, h=None, runs=None, color='ink', spacing=1.5, bold=False):
        box = _textbox(self.slide, x, y, w,
                       h or text_height(runs or text, w, self.t['body'], spacing))
        _write(box.text_frame, runs if runs else text, self.t['body'], color,
               bold=bold, line_spacing=spacing)
        return self

    def label(self, text, x, y, w, color='ink', bold=False):
        box = _textbox(self.slide, x, y, w, text_height(text, w, self.t['label'], 1.5))
        _write(box.text_frame, text, self.t['label'], color, bold=bold, line_spacing=1.5)
        return self

    def context(self, text, x=48, y=166, w=1184, runs=None):
        box = _textbox(self.slide, x, y, w, text_height(runs or text, w, self.t['note'], 1.5),
                       name='context')
        _write(box.text_frame, runs if runs else text, self.t['note'], 'secondary',
               line_spacing=1.5)
        return self

    def note(self, text, x, y, w, runs=None, color='secondary'):
        box = _textbox(self.slide, x, y, w, text_height(runs or text, w, self.t['note'], 1.55))
        _write(box.text_frame, runs if runs else text, self.t['note'], color, line_spacing=1.55)
        return self

    # ---- 面与线 ----
    def panel(self, x, y, w, h, fill='pale', color=None, name=None, anchor=None):
        """色面。默认浅紫分组底。"""
        shp = _rect(self.slide, x, y, w, h, fill, name=name)
        return shp

    def band(self, x, y, w, h, text, fill='purple', color='white', inset=26,
             size=None, anchor='middle', runs=None, spacing=1.3):
        """色面带，文字居中，内距 24（inset 可调，默认 26 与 24 同族）。"""
        shp = _rect(self.slide, x, y, w, h, fill)
        tf = shp.text_frame
        tf.vertical_anchor = {'top': MSO_ANCHOR.TOP, 'middle': MSO_ANCHOR.MIDDLE}[anchor]
        tf.margin_left = Emu(int(inset * EMU))
        tf.margin_right = Emu(int(inset * EMU))
        tf.margin_top = 0
        tf.margin_bottom = 0
        _write(tf, runs if runs else text, size or self.t['body'], color,
               line_spacing=spacing)
        return shp

    def rule(self, x, y, w, color='line', width=1.0):
        shp = _rect(self.slide, x, y, w, width, color)
        return shp

    def gold_rule(self, x, y, w):
        return self.rule(x, y, w, 'gold', 1.4)

    # ---- 结构化 ----
    def table(self, x, y, widths, rows, head=True, align=None, head_fill='purple',
              row_h=None, head_h=None, bold_last=False, right_cols=None):
        """rows: 第一行若 head=True 作为表头；单元格可为 str 或 (text, {color,bold})。"""
        row_h = row_h or self.t['row']
        head_h = head_h or self.t['head_row']
        n_rows = len(rows)
        n_cols = len(widths)
        total_w = sum(widths)
        total_h = (head_h if head else 0) + row_h * (n_rows - (1 if head else 0))
        gshape = self.slide.shapes.add_table(n_rows, n_cols, Emu(int(x * EMU)),
                                             Emu(int(y * EMU)),
                                             Emu(int(total_w * EMU)), Emu(int(total_h * EMU)))
        tbl = gshape.table
        _no_style(tbl)
        for i, wd in enumerate(widths):
            tbl.columns[i].width = Emu(int(wd * EMU))
        for i in range(n_rows):
            tbl.rows[i].height = Emu(int((head_h if (head and i == 0) else row_h) * EMU))
        right_cols = set(right_cols if right_cols is not None else range(1, n_cols))
        for ri, row in enumerate(rows):
            is_head = head and ri == 0
            for ci, val in enumerate(row):
                text, opt = (val if isinstance(val, tuple) else (val, {}))
                if align:
                    al = align[ci] if isinstance(align, (list, tuple)) else align
                else:
                    al = 'l' if ci == 0 else ('r' if ci in right_cols else 'c')
                if is_head:
                    _set_cell(tbl.cell(ri, ci), text, self.t['label'], 'white',
                              bold=True, align=al, fill=head_fill)
                else:
                    bold = opt.get('bold', bold_last and ri == n_rows - 1)
                    _set_cell(tbl.cell(ri, ci), text, self.t['table'],
                              opt.get('color', 'ink'), bold=bold, align=al)
                    _cell_border(tbl.cell(ri, ci), COLORS['line'], 1.0)
        return gshape

    def bars(self, x, y, w, items, max_value=None, gap=12, unit=''):
        """同尺度横向条。items: [(标签, 数值, 显示文本)]。"""
        max_value = max_value or max(abs(v) for _, v, _ in items)
        usable = w - 96
        for i, (_, val, text) in enumerate(items):
            width = max(48, int(abs(val) / max_value * usable))
            shp = _rect(self.slide, x, y + i * (36 + gap), width, 36, 'gold')
            tf = shp.text_frame
            tf.vertical_anchor = MSO_ANCHOR.MIDDLE
            _write(tf, text, self.t['label'], 'purple', bold=True, line_spacing=1.0,
                   align='c')
        return self

    def scrim(self, x, y, w, h, stops, angle=0):
        """图片上的深色遮罩。stops: [(位置0-1, alpha0-1)]，颜色固定为 20182A。

        用于全幅图压字，替代硬边色块。
        """
        shp = _rect(self.slide, x, y, w, h, '20182A')
        sppr = shp.fill._xPr
        for tag in ('a:solidFill', 'a:noFill', 'a:gradFill', 'a:pattFill', 'a:blipFill', 'a:grpFill'):
            el = sppr.find(qn(tag))
            if el is not None:
                sppr.remove(el)
        grad = sppr.makeelement(qn('a:gradFill'), {'rotWithShape': '1'})
        gs_lst = grad.makeelement(qn('a:gsLst'), {})
        for pos, alpha in stops:
            gs = grad.makeelement(qn('a:gs'), {'pos': str(int(pos * 100000))})
            clr = grad.makeelement(qn('a:srgbClr'), {'val': '20182A'})
            a = grad.makeelement(qn('a:alpha'), {'val': str(int(alpha * 100000))})
            clr.append(a)
            gs.append(clr)
            gs_lst.append(gs)
        grad.append(gs_lst)
        lin = grad.makeelement(qn('a:lin'), {'ang': str(int(angle * 60000)), 'scaled': '0'})
        grad.append(lin)
        # schema：填充必须排在 a:ln / a:effectLst 之前
        anchor = None
        for tag in ('a:ln', 'a:effectLst', 'a:effectDag', 'a:scene3d', 'a:sp3d', 'a:extLst'):
            el = sppr.find(qn(tag))
            if el is not None:
                anchor = el
                break
        if anchor is not None:
            anchor.addprevious(grad)
        else:
            sppr.append(grad)
        return shp

    def freeform(self, points, color='blue', width=2.8, closed=False, fill=None):
        """按 (x,y) 像素点序列画可编辑折线，用于函数图像与关系线。"""
        pts = [(Emu(int(px * EMU)), Emu(int(py * EMU))) for px, py in points]
        builder = self.slide.shapes.build_freeform(pts[0][0], pts[0][1], scale=1.0)
        builder.add_line_segments(pts[1:], close=closed)
        shp = builder.convert_to_shape()
        shp.shadow.inherit = False
        if fill:
            shp.fill.solid()
            shp.fill.fore_color.rgb = fmt(fill)
        else:
            shp.fill.background()
        shp.line.color.rgb = fmt(color)
        shp.line.width = Pt(width * 0.75)
        return shp

    def dot(self, x, y, r=5, color='blue'):
        shp = self.slide.shapes.add_shape(MSO_SHAPE.OVAL, Emu(int((x - r) * EMU)),
                                          Emu(int((y - r) * EMU)), Emu(int(2 * r * EMU)),
                                          Emu(int(2 * r * EMU)))
        shp.shadow.inherit = False
        shp.fill.solid()
        shp.fill.fore_color.rgb = fmt(color)
        shp.line.fill.background()
        return shp

    def image(self, path, x, y, w, h, cover=True, focus=(0.5, 0.5)):
        """放图。cover=True 时按目标比例裁切，focus=(fx,fy) 决定保留画面的哪个位置。

        focus=(0.5,0.5) 居中（默认）；fy=1 贴底裁（去掉底部水印）；fx=0 贴左。
        """
        pic = self.slide.shapes.add_picture(str(path), Emu(int(x * EMU)), Emu(int(y * EMU)),
                                            Emu(int(w * EMU)), Emu(int(h * EMU)))
        if cover:
            self._crop_to_fill(pic, path, w, h, focus)
        return pic

    @staticmethod
    def _crop_to_fill(pic, path, w, h, focus=(0.5, 0.5)):
        from PIL import Image
        with Image.open(path) as source_image:
            iw, ih = source_image.size
        target = w / h
        src = iw / ih
        fx, fy = focus
        if src > target:            # 图更宽，裁左右
            cut = (1 - target / src) / 2
            pic.crop_left = cut * 2 * fx
            pic.crop_right = cut * 2 * (1 - fx)
        elif src < target:          # 图更高，裁上下
            cut = (1 - src / target) / 2
            pic.crop_top = cut * 2 * fy
            pic.crop_bottom = cut * 2 * (1 - fy)

    def brand_mark(self, x=96, y=44, w=116, light=True):
        """出血页上的校徽。light=True 用金色版，压在深色图上。"""
        name = 'logo-gold.png' if light else 'logo-horizontal.png'
        h = w / (440 / 261 if light else 385 / 134)
        pic = self.slide.shapes.add_picture(str(self.deck.template_dir / name),
                                            Emu(int(x * EMU)), Emu(int(y * EMU)),
                                            Emu(int(w * EMU)), Emu(int(h * EMU)))
        pic.name = 'brand-mark'
        return pic

    def page_number(self, total=None, light=False):
        """页码。出血页用左上文字列的左边界、左对齐浅色，避免压在亮画面上看不清。"""
        txt = f'{self.number:02d}' if total is None else f'{self.number:02d}/{total:02d}'
        if light:
            box = _textbox(self.slide, 148, 677, 120, 24, anchor='middle')
            _write(box.text_frame, txt, 14, 'FFFFFF', line_spacing=1.0, align='l')
        else:
            box = _textbox(self.slide, 1190, 677, 42, 24, anchor='middle')
            _write(box.text_frame, txt, 14, 'secondary', line_spacing=1.0, align='r')
        return self


class Deck:
    def __init__(self, template, title=None, presenter=None, date=None,
                 content_only=False):
        self.prs = Presentation(str(template))
        self.template_dir = Path(template).parent
        self.content_only = content_only
        self._pages = []
        self._closing = None
        self._prepare(title, presenter, date)

    # ---- 骨架 ----
    def _prepare(self, title, presenter, date):
        sldIdLst = self.prs.slides._sldIdLst
        ids = list(sldIdLst)
        if self.content_only:
            for el in ids:
                self.prs.part.drop_rel(el.get(qn('r:id')))
                sldIdLst.remove(el)
            self._blank_layout = self._pick_blank()
            return
        # 保留封面与封尾，删除中间正文页
        keep = {ids[0], ids[-1]}
        for el in ids[1:-1]:
            self.prs.part.drop_rel(el.get(qn('r:id')))
            sldIdLst.remove(el)
        self._closing_el = ids[-1]
        self._blank_layout = self._pick_blank()
        self._fill_cover(title, presenter, date)
        self._fill_closing()

    def _pick_blank(self):
        for lay in self.prs.slide_layouts:
            if lay.name in ('空白', 'Blank'):
                return lay
        return self.prs.slide_layouts[-1]

    def _add_slide(self):
        s = self.prs.slides.add_slide(self._blank_layout)
        for ph in list(s.placeholders):
            ph._element.getparent().remove(ph._element)
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = fmt(COLORS['paper'])
        return s

    # ---- 封面 / 封尾 ----
    def _fill_cover(self, title, presenter, date):
        cover = self.prs.slides[0]
        if title is None:
            return
        box = None
        for sh in cover.shapes:
            if sh.has_text_frame and sh.text_frame.text.strip():
                box = sh
                break
        if box is None:
            box = _textbox(cover, 64, 488, 1050, 74.4)
        else:
            box.left, box.top = Emu(64 * EMU), Emu(int(488 * EMU))
            box.width, box.height = Emu(1050 * EMU), Emu(int(74.4 * EMU))
        box.name = 'cover-title'
        tf = box.text_frame
        tf.clear() if hasattr(tf, 'clear') else None
        for p in list(tf.paragraphs)[1:]:
            p._p.getparent().remove(p._p)
        p0 = tf.paragraphs[0]
        for r in list(p0.runs):
            r._r.getparent().remove(r._r)
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        r = p0.add_run()
        r.text = title
        _style_run(r, 45, 'white', bold=True)
        p0.line_spacing = 1.1

        import re as _re
        for name, text, y, size, prefix in (
                ('cover-presenter', presenter, 610, 20, '汇报人：'),
                ('cover-date', date, 650, 20, '汇报时间：')):
            if text is None:
                continue
            clean = _re.sub(r'^(汇报人|汇报时间)[：:]\s*', '', str(text).strip())
            b = _textbox(cover, 64, y, 680, 30, name=name, anchor='middle')
            _write(b.text_frame, prefix + clean, size, 'white', line_spacing=1.0)

    def _fill_closing(self):
        """封尾固定版式：培养目标与结束语在设计区域内居中，不用左上坐标。

        底图的弧线与金线集中在画面下半部，文字落在视觉中心偏上，
        因此以 1280 画布中心 640 对齐，标题块 262–334，金线 346，结束语 372–420。
        """
        closing = self.prs.slides[-1]
        m = _textbox(closing, 140, 262, 1000, 72, name='closing-motto', anchor='middle')
        _write(m.text_frame, '华夏俊采，朗若星辰', 46, 'white', bold=True,
               line_spacing=1.1, align='c')
        _rect(closing, 604, 346, 72, 2, 'gold', name='closing-rule')
        msg = _textbox(closing, 140, 368, 1000, 52, name='closing-message', anchor='middle')
        _write(msg.text_frame, self.closing_message or '感谢聆听　欢迎讨论', 21, 'white',
               line_spacing=1.3, align='c')

    closing_message = '感谢聆听　欢迎讨论'

    def set_closing_message(self, text):
        self.closing_message = text
        for sh in self.prs.slides[-1].shapes:
            if sh.name == 'closing-message':
                tf = sh.text_frame
                for p in list(tf.paragraphs)[1:]:
                    p._p.getparent().remove(p._p)
                for r in list(tf.paragraphs[0].runs):
                    r._r.getparent().remove(r._r)
                _write(tf, text, 21, 'white', line_spacing=1.3, align='c')
        return self

    # ---- 页面 ----
    def page(self, title, tier='read'):
        s = self._add_slide()
        pm = s.shapes.add_picture(str(self.template_dir / 'logo-horizontal.png'),
                                  Emu(1093 * EMU), Emu(int(25 * EMU)),
                                  Emu(139 * EMU), Emu(int(49 * EMU)))
        pm.name = 'logo'
        line = _rect(s, 48, 86, 1184, 1.4, 'gold', name='divider')
        pg = Page(self, s, tier, len(self._pages) + 1)
        pg.title(title)
        self._pages.append(pg)
        return pg

    def _renumber_slides(self):
        """把幻灯片部件按当前顺序重命名为 slide1..slideN。

        python-pptx 的 next_partname 只扫描可达部件，删页后会与残留编号相撞，
        出现同名 slide5.xml 覆盖封尾。两趟重命名保证唯一。
        """
        from pptx.opc.packuri import PackURI
        slides = list(self.prs.slides)
        for i, s in enumerate(slides):
            s.part.partname = PackURI(f'/ppt/slides/_tmp{i}.xml')
        for i, s in enumerate(slides):
            s.part.partname = PackURI(f'/ppt/slides/slide{i + 1}.xml')

    def bleed_page(self, tier='far', fill='paper'):
        """整页出血页：无页眉题名、无金线、无近白边，图或色面铺满 1280×720。

        用于对外演讲、开放日、招生宣讲。题名由主张承担；校徽用 brand_mark() 压在
        文字侧上方。数量与相邻规则见场景视觉语法。
        """
        if tier != 'far':
            raise ValueError('整页出血只用于 far 档；留阅与近距页须保留页眉框架。')
        s = self._add_slide()
        if fill != 'paper':
            s.background.fill.solid()
            s.background.fill.fore_color.rgb = fmt(fill)
        pg = Page(self, s, tier, len(self._pages) + 1)
        pg.bleed = True
        self._pages.append(pg)
        return pg

    def save(self, path):
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        if not self.content_only and getattr(self, '_closing_el', None) is not None:
            # 把封尾元素移到末尾（新增页总是追加在它后面）
            sldIdLst = self.prs.slides._sldIdLst
            if self._closing_el in list(sldIdLst):
                sldIdLst.remove(self._closing_el)
            sldIdLst.append(self._closing_el)
        self._renumber_slides()
        errs = validate_order(self.prs)
        if errs:
            raise ValueError('元素顺序不合 schema，PowerPoint 可能报修复：\n' + '\n'.join(errs[:10]))
        self.prs.save(str(out))
        return out


def load_contract(skill_dir):
    p = Path(skill_dir) / 'assets' / 'style-contract.json'
    return json.loads(p.read_text(encoding='utf8'))
