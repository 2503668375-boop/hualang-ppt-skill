#!/usr/bin/env python3
"""可组合的原生教学图形：分数条、范围标记、锚定批注。单位为1280×720逻辑像素。"""
from __future__ import annotations
import math
from hualang_deck import _rect, _textbox, _write, text_height


def _positive(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f'{name} 必须为有限正数')


def _int(value, name, minimum=0):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f'{name} 必须为不小于{minimum}的整数')


def fraction_strip(page, x, y, w, h, numerator, denominator, *, split=1,
                   highlight=(), fill='pale', accent='purple', name='fraction-strip'):
    """一个完整单位等分为denominator格，每格再split等分；highlight为细格下标。

    numerator限定0..denominator。多个完整单位应画相同宽度的多个条，不能伸长一条
    同时沿用“一米”的标识。返回对象、细格中心和单元宽，供批注/揭示使用。
    """
    _int(numerator, 'numerator'); _int(denominator, 'denominator', 1); _int(split, 'split', 1)
    _positive(w, 'w'); _positive(h, 'h')
    if numerator > denominator:
        raise ValueError('一条表示一个完整单位；假分数请按同尺度画多个完整单位')
    count = denominator * split
    if count > 72 or w / count < 10:
        raise ValueError('细格过密，需扩大图形或按单位分行，不能画成不可读细线')
    highlight = list(highlight)
    if any(isinstance(i, bool) or not isinstance(i, int) or i < 0 or i >= numerator*split for i in highlight):
        raise ValueError('highlight 必须落在已着色分数内的细格上')
    cell_w = w / count; shapes = []
    for i in range(count):
        color = accent if i in highlight else fill if i < numerator * split else 'white'
        shapes.append(_rect(page.slide, x+i*cell_w, y, cell_w, h, color,
                            name=f'{name}-cell-{i}', line='line', line_w=.75))
    # 原单位分界保留较强线，细分后能追踪分数单位变化。
    for i in range(denominator+1):
        line = page.freeform([(x+i*w/denominator,y),(x+i*w/denominator,y+h)], color='ink', width=1.3)
        line.name = f'{name}-unit-boundary-{i}'; shapes.append(line)
    return {'shapes':shapes, 'cell_width':cell_w,
            'centers':[(x+(i+.5)*cell_w,y+h/2) for i in range(count)],
            'shaded_end':x+w*numerator/denominator, 'denominator':count}


def brace_label(page, x1, x2, y, text, *, size=19, color='purple', depth=10, label_width=None):
    """实际范围下方的括线；不从无证据的文字虚构关系。"""
    if x2 <= x1:
        raise ValueError('括线终点必须在起点右侧')
    line=page.freeform([(x1,y),(x1,y+depth),(x2,y+depth),(x2,y)],color=color,width=1.5)
    width=label_width or max(x2-x1,160)
    box=_textbox(page.slide,(x1+x2-width)/2,y+depth+7,width,text_height(text,width,size,1.2))
    _write(box.text_frame,text,size,color,line_spacing=1.2,align='c')
    return [line,box]


def anchored_note(page, text, anchor, x, y, w, *, label='', size=21, side='left', max_height=None):
    """批注指向真实材料位置；窄引线与说明独立，不给每项包卡。"""
    if side not in ('left','right'):
        raise ValueError('side 仅为 left 或 right')
    height=text_height(text,w,size,1.4)+(32 if label else 0)
    if max_height is not None and height > max_height:
        raise ValueError('批注超出可用高度，请缩短复述、加宽或续页；不裁掉内容')
    edge=x if side=='left' else x+w
    elbow=edge-18 if side=='left' else edge+18
    line=page.freeform([anchor,(elbow,anchor[1]),(elbow,y+12),(edge,y+12)],color='gold',width=1.3)
    shapes=[line,page.dot(*anchor,r=3,color='gold')]
    if label:
        b=_textbox(page.slide,x,y,w,30);_write(b.text_frame,label,size,'purple',bold=True,line_spacing=1.1);shapes.append(b)
    b=_textbox(page.slide,x,y+(32 if label else 0),w,height-(32 if label else 0))
    _write(b.text_frame,text,size,'ink',line_spacing=1.4);shapes.append(b)
    return shapes
