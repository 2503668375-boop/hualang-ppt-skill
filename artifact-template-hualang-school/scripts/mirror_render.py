#!/usr/bin/env python3
"""PPTX 结构镜像：按最终文件里的真实坐标、字号、颜色重绘一份 HTML，用于实页核对。

这是 structural_mirror，不是 PowerPoint 渲染。它能证明坐标、字号、层级、换行与
对象顺序，不能证明字体替换、母版继承或放映效果。正式交付前仍须在装有演示软件
的机器上打开最终文件。

用法::

    python3 mirror_render.py 成品.pptx --out 镜像.html [--slides 2,3,4]
"""
from __future__ import annotations

import argparse
import base64
import io
from pathlib import Path

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.oxml.ns import qn

EMU = 9525
PX = lambda v: 0 if v is None else v / EMU


def _solid_color(shape):
    try:
        f = shape.fill
        if f.type == 1:
            return '#' + str(f.fore_color.rgb)
    except Exception:
        pass
    return None


def _gradient_css(shape):
    el = shape.fill._xPr.find(qn('a:gradFill')) if hasattr(shape.fill, '_xPr') else None
    if el is None:
        return None
    stops = []
    for gs in el.iter(qn('a:gs')):
        pos = int(gs.get('pos')) / 100000
        clr = gs.find(qn('a:srgbClr'))
        if clr is None:
            continue
        rgb = clr.get('val')
        alpha = 1.0
        a = clr.find(qn('a:alpha'))
        if a is not None:
            alpha = int(a.get('val')) / 100000
        stops.append((pos, f'rgba({int(rgb[0:2],16)},{int(rgb[2:4],16)},{int(rgb[4:6],16)},{alpha:.3f})'))
    lin = el.find(qn('a:lin'))
    ang = int(lin.get('ang')) / 60000 if lin is not None else 0
    stops.sort()
    body = ','.join(f'{c} {int(p*100)}%' for p, c in stops)
    return f'linear-gradient({90+ang}deg,{body})'


def _line_css(shape):
    try:
        ln = shape.line
        c = ln.color.rgb
        w = ln.width.pt / 0.75 if ln.width else 1
        return f'1px solid #{c}', w
    except Exception:
        return None, 0


def _font(run):
    f = run.font
    size = f.size.pt / 0.75 if f.size else 18
    color = None
    try:
        color = '#' + str(f.color.rgb)
    except Exception:
        pass
    return size, color, bool(f.bold), bool(f.italic)


def _para_html(p):
    a = p.alignment
    name = getattr(a, 'name', None) or str(a).split(' ')[0].split('.')[-1]
    align = {'LEFT': 'left', 'RIGHT': 'right', 'CENTER': 'center',
             'JUSTIFY': 'justify'}.get(str(name).upper(), 'left')
    ls = p.line_spacing
    out = []
    for r in p.runs:
        size, color, bold, italic = _font(r)
        style = f'font-size:{size:.1f}px'
        if color:
            style += f';color:{color}'
        if bold:
            style += ';font-weight:700'
        if italic:
            style += ';font-style:italic'
        txt = (r.text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
               .replace('\n', '<br>'))
        out.append(f'<span style="{style}">{txt}</span>')
    lh = ''
    if isinstance(ls, float):
        lh = f'line-height:{ls}'
    elif ls is not None:
        lh = f'line-height:{ls.pt/0.75:.1f}px'
    return f'<div style="text-align:{align};{lh};white-space:pre-wrap;width:100%">{"" if out else "&nbsp;"}{"".join(out)}</div>'


def _anchor(shape):
    from pptx.enum.text import MSO_ANCHOR
    try:
        a = shape.text_frame.vertical_anchor
    except Exception:
        return 'flex-start'
    return {MSO_ANCHOR.MIDDLE: 'center', MSO_ANCHOR.BOTTOM: 'flex-end'}.get(a, 'flex-start')


def _text_box_html(shape, x, y, w, h):
    tf = shape.text_frame
    ml, mr, mt, mb = (PX(tf.margin_left), PX(tf.margin_right),
                      PX(tf.margin_top), PX(tf.margin_bottom))
    body = ''.join(_para_html(p) for p in tf.paragraphs)
    return (f'<div style="position:absolute;left:{x:.1f}px;top:{y:.1f}px;'
            f'width:{w:.1f}px;height:{h:.1f}px;display:flex;flex-direction:column;align-items:{_anchor(shape)};'
            f'box-sizing:border-box;padding:{mt:.1f}px {mr:.1f}px {mb:.1f}px {ml:.1f}px;'
            f'font-family:\'PingFang SC\',Arial;color:#222">{body}</div>')


def _text_in_shape(shape, x, y, w, h, extra=''):
    tf = shape.text_frame
    if not tf.text.strip():
        return extra
    ml, mr = PX(tf.margin_left), PX(tf.margin_right)
    body = ''.join(_para_html(p) for p in tf.paragraphs)
    return (f'<div style="position:absolute;left:{x:.1f}px;top:{y:.1f}px;'
            f'width:{w:.1f}px;height:{h:.1f}px;display:flex;flex-direction:column;align-items:{_anchor(shape)};'
            f'box-sizing:border-box;padding:0 {mr:.1f}px 0 {ml:.1f}px;'
            f'font-family:\'PingFang SC\',Arial">{body}</div>')


def _picture_html(shape, x, y, w, h, asset_dir: Path, n):
    img = shape.image
    ext = img.ext
    path = asset_dir / f'img{n}.{ext}'
    path.write_bytes(img.blob)
    cl, cr = shape.crop_left or 0, shape.crop_right or 0
    ct, cb = shape.crop_top or 0, shape.crop_bottom or 0
    iw = w / max(1e-6, (1 - cl - cr))
    ih = h / max(1e-6, (1 - ct - cb))
    left = -cl * iw
    top = -ct * ih
    return (f'<div style="position:absolute;left:{x:.1f}px;top:{y:.1f}px;'
            f'width:{w:.1f}px;height:{h:.1f}px;overflow:hidden">'
            f'<img src="{asset_dir.name}/img{n}.{ext}" style="position:absolute;left:{left:.1f}px;'
            f'top:{top:.1f}px;width:{iw:.1f}px;height:{ih:.1f}px"></div>')


def _freeform_svg(shape, x, y, w, h):
    spPr = shape._element.spPr
    cust = spPr.find(qn('a:custGeom'))
    if cust is None:
        return ''
    path = cust.find(qn('a:pathLst')).find(qn('a:path'))
    pw, ph = float(path.get('w') or w), float(path.get('h') or h)
    sx, sy = (w / pw if pw else 1), (h / ph if ph else 1)
    d = []
    for cmd in path:
        tag = cmd.tag.split('}')[-1]
        pts = cmd.findall(qn('a:pt'))
        if tag == 'moveTo' and pts:
            d.append(f'M{float(pts[0].get("x"))*sx:.1f},{float(pts[0].get("y"))*sy:.1f}')
        elif tag == 'lnTo' and pts:
            d.append(f'L{float(pts[0].get("x"))*sx:.1f},{float(pts[0].get("y"))*sy:.1f}')
    stroke, sw = _line_css(shape)
    if stroke is None:
        stroke, sw = 'none', 0
    fill_c = _solid_color(shape) or _gradient_css(shape) or 'none'
    color = 'none'
    ln = spPr.find(qn('a:ln'))
    if ln is not None:
        clr = ln.find(qn('a:solidFill'))
        if clr is not None:
            rgb = clr.find(qn('a:srgbClr'))
            if rgb is not None:
                color = '#' + rgb.get('val')
    return (f'<svg style="position:absolute;left:{x:.1f}px;top:{y:.1f}px" '
            f'width="{w:.1f}" height="{h:.1f}" viewBox="0 0 {w:.1f} {h:.1f}">'
            f'<path d="{"".join(d)}" fill="{fill_c}" stroke="{color}" stroke-width="{sw:.1f}" '
            f'stroke-linejoin="round"/></svg>')


def _table_html(shape, x, y, w, h):
    tbl = shape.table
    cols = ''.join(f'<col style="width:{PX(c.width):.1f}px">' for c in tbl.columns)
    rows = []
    for r in tbl.rows:
        cells = []
        for c in r.cells:
            fill = '#FFFFFF'
            try:
                if c.fill.type == 1:
                    fill = '#' + str(c.fill.fore_color.rgb)
            except Exception:
                pass
            body = ''.join(_para_html(p) for p in c.text_frame.paragraphs)
            mt = PX(c.margin_left)
            cells.append(f'<td style="background:{fill};border-bottom:1px solid #D8D8D8;'
                         f'padding:0 {mt:.1f}px;vertical-align:{_anchor(c)};'
                         f'font-family:\'PingFang SC\',Arial">{body}</td>')
        rows.append(f'<tr style="height:{PX(r.height):.1f}px">' + ''.join(cells) + '</tr>')
    return (f'<table style="position:absolute;left:{x:.1f}px;top:{y:.1f}px;'
            f'width:{w:.1f}px;border-collapse:collapse;table-layout:fixed">'
            f'<colgroup>{cols}</colgroup>{"".join(rows)}</table>')


def render(pptx_path, out_html, slides=None, scale_note=True):
    prs = Presentation(str(pptx_path))
    W, H = PX(prs.slide_width), PX(prs.slide_height)
    out_dir = Path(out_html).parent
    asset_dir = out_dir / (Path(out_html).stem + '_assets')
    asset_dir.mkdir(parents=True, exist_ok=True)
    pages = []
    n = 0
    for idx, slide in enumerate(prs.slides, 1):
        if slides and idx not in slides:
            continue
        bg = '#FDFDFE'
        try:
            if slide.background.fill.type == 1:
                bg = '#' + str(slide.background.fill.fore_color.rgb)
        except Exception:
            pass
        parts = []
        # 母版与版式层的图片/图形先画（正文品牌框架多来自版式），跳过空占位符
        layers = []
        try:
            master = slide.slide_layout.slide_master
            layers.append(master.shapes)
        except Exception:
            pass
        try:
            layers.append(slide.slide_layout.shapes)
        except Exception:
            pass
        inherited = [sh for group in layers for sh in group
                     if not getattr(sh, 'is_placeholder', False)]
        for shape in inherited + list(slide.shapes):
            x, y = PX(shape.left), PX(shape.top)
            w, h = PX(shape.width), PX(shape.height)
            n += 1
            st = shape.shape_type
            if st == MSO_SHAPE_TYPE.PICTURE:
                parts.append(_picture_html(shape, x, y, w, h, asset_dir, n))
                continue
            if getattr(shape, 'has_table', False) and shape.has_table:
                parts.append(_table_html(shape, x, y, w, h))
                continue
            if st == MSO_SHAPE_TYPE.FREEFORM or shape._element.spPr.find(qn('a:custGeom')) is not None:
                svg = _freeform_svg(shape, x, y, w, h)
                if svg:
                    parts.append(svg)
                    continue
            fill = _solid_color(shape)
            grad = _gradient_css(shape)
            stroke, _ = _line_css(shape)
            box = 'position:absolute;'
            if grad:
                box += f'background:{grad};'
            elif fill:
                box += f'background:{fill};'
            if stroke:
                box += f'border:{stroke};box-sizing:border-box;'
            base = (f'<div style="{box}left:{x:.1f}px;top:{y:.1f}px;'
                    f'width:{w:.1f}px;height:{h:.1f}px"></div>')
            parts.append(base)
            if shape.has_text_frame and shape.text_frame.text.strip():
                parts.append(_text_in_shape(shape, x, y, w, h))
        pages.append(f'<div class="slide" style="background:{bg}">{"".join(parts)}'
                     f'<div class="pno">P{idx}</div></div>')
    html = f'''<!DOCTYPE html><html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#9a9a9e;font-family:"PingFang SC",Arial;-webkit-font-smoothing:antialiased}}
.slide{{width:{W:.0f}px;height:{H:.0f}px;position:relative;overflow:hidden;margin:0 auto 20px}}
.pno{{position:absolute;right:6px;bottom:4px;font-size:11px;color:#bbb}}
</style></head><body>{''.join(pages)}</body></html>'''
    Path(out_html).write_text(html, encoding='utf8')
    return len(pages)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('pptx', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--slides', default='')
    a = ap.parse_args()
    sel = {int(x) for x in a.slides.split(',') if x.strip()} or None
    n = render(a.pptx, a.out, sel)
    print(f'mirror: {n} 页 -> {a.out}')
