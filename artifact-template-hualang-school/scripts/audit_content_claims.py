#!/usr/bin/env python3
"""从最后保存的PPTX提取需人工复读的主张。提示不等于语义判决。"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path
from pptx import Presentation

NUMBER = r'(?:\d+(?:\.\d+)?|[一二三四五六七八九十百两]+)'
INVENTORY = re.compile(NUMBER + r'\s*(?:套|部|种|类|份|个|道|档)\s*(?:场景|版式|表格|体系|方法|框架|模型|脚本|资料|参考|门禁|字阶|能力|机制|流程)')
ABSOLUTE = re.compile(r'唯一解|不会跑版|自动(?:保证|确保)|保证(?:正确|无误|通过)|全部自动|无需(?:人工|复核|检查)|不用(?:人工|复核)|改一个(?:数字|数据).{0,16}(?:自动|跟着|重排)|没有一页.{0,10}手工|不靠人眼')
PROCESS = re.compile(r'deck-spec\.json|\b(?:references|scripts)/|hualang_\w+\.py|(?:版式|layout)\s*[:：]?\s*(?:statement|comparison|waterfall|positioning|swimlane)|\b\d+(?:\.\d+)?\s*px\b')


def _texts(shapes):
    for sh in shapes:
        if getattr(sh, 'has_text_frame', False) and sh.text.strip():
            yield sh.text.strip()
        if getattr(sh, 'has_table', False):
            for row in sh.table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        yield cell.text.strip()
        if getattr(sh, 'shape_type', None) == 6:
            yield from _texts(sh.shapes)


def audit_presentation(path):
    path = Path(path)
    prs = Presentation(str(path))
    slides, findings, seen = [], [], {}
    for index, slide in enumerate(prs.slides, 1):
        blocks = list(_texts(slide.shapes))
        slides.append({'page': index, 'text_blocks': blocks})
        joined = '\n'.join(blocks)
        for category, pattern, question in [
            ('inventory_rhetoric', INVENTORY, '数量是否帮助判断或办理？若只是组件库存，改为实际对象、处理与可见结果。'),
            ('absolute_claim', ABSOLUTE, '这项绝对承诺有无实际操作或材料支持？保留成立条件，不能用可编辑等同自动关联。'),
            ('production_language', PROCESS, '这些制作参数是否属于本次听众任务？普通业务页应移入独立底稿；维护培训可保留。'),
        ]:
            hits = list(dict.fromkeys(m.group(0) for m in pattern.finditer(joined)))
            if hits:
                findings.append({'page': index, 'category': category, 'excerpts': hits, 'review_question': question})
        for block in blocks:
            normalized = re.sub(r'\s+', '', block)
            if len(normalized) < 35:
                continue
            if normalized in seen:
                findings.append({'page': index, 'category': 'repeated_passage', 'also_on_page': seen[normalized],
                                 'excerpt': block, 'review_question': '是否必要题干、续表口径或前后比较？否则核对复制遗漏和跨页信息增量。'})
            else:
                seen[normalized] = index
    return {'schema_version': 1, 'file_name': path.name,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'page_count': len(slides), 'status': 'human_review_required',
            'limitations': '只定位候选文案和重复段落；未检出不代表内容正确、充分或视觉通过。标题、引文、教学辨错和维护培训均须结合上下文判断。',
            'findings': findings, 'slides': slides}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('pptx', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    result = audit_presentation(args.pptx)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'pages': result['page_count'], 'findings': len(result['findings']), 'status': result['status']}, ensure_ascii=False))

if __name__ == '__main__':
    main()
