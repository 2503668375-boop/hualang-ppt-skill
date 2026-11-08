#!/usr/bin/env python3
"""从最终文件整理完整复读材料与有限候选线索；不判文风、不自动改写。"""
from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib
import json
import re
from pathlib import Path
from pptx import Presentation

NUMBER = r'(?:\d+(?:\.\d+)?|[一二三四五六七八九十百两]+)'
INVENTORY = re.compile(NUMBER + r'\s*(?:套|部|种|类|份|个|项|道|档|重|步|层)\s*(?:场景|版式|表格|体系|方法|框架|模型|脚本|资料|参考|门禁|字阶|能力|机制|流程|目的|目标|重点|保障|步骤)')
ABSOLUTE = re.compile(r'唯一解|不会跑版|自动(?:保证|确保)|保证(?:正确|无误|通过)|全部自动|无需(?:人工|复核|检查)|不用(?:人工|复核)|改一个(?:数字|数据).{0,16}(?:自动|跟着|重排)|没有一页.{0,10}手工|不靠人眼|(?:所有|任何|全部).{0,12}(?:一键|自动).{0,8}(?:完成|生成)|(?:不会|永不).{0,8}(?:出错|错误)')
PROCESS = re.compile(r'deck-spec\.json|\b(?:references|scripts)/|hualang_\w+\.py|(?:版式|layout)\s*[:：]?\s*(?:statement|comparison|waterfall|positioning|swimlane)|\b\d+(?:\.\d+)?\s*px\b')
ISOLATED_COUNT = re.compile(r'^\s*' + NUMBER + r'\s*(?:套|部|类|档|种|份)\s*$')
SEQUENCE = re.compile(r'先([^，,；;。\n]{1,16})[，,]\s*再([^；;。\n]{1,20})')
EMU_PER_PX = 9525


def _bbox(shape):
    return {key: round(float(getattr(shape, attr)) / EMU_PER_PX, 2)
            for key, attr in [('x', 'left'), ('y', 'top'), ('w', 'width'), ('h', 'height')]}


def _role(name):
    lowered = name.lower()
    if lowered == 'title' or lowered.endswith('-title'):
        return 'title'
    if 'lead' in lowered or 'summary' in lowered:
        return 'lead'
    if any(token in lowered for token in ('context', 'source', 'page-number', 'footer')):
        return 'context'
    return 'content'


def extract_objects(shapes, parent='', group_coordinates=False):
    """Return text and incomplete objects; group-local positions stay identified."""
    objects, incomplete = [], []
    for index, shape in enumerate(shapes, 1):
        name = str(getattr(shape, 'name', '') or f'object-{index}')
        path = f'{parent}/{name}' if parent else name
        position = _bbox(shape)
        common = {'name': path, 'bbox': position,
                  'coordinate_space': 'group_local' if group_coordinates else 'slide',
                  'role': _role(name)}
        if getattr(shape, 'has_text_frame', False) and shape.text.strip():
            objects.append({**common, 'kind': 'text', 'text': shape.text.strip()})
        if getattr(shape, 'has_table', False):
            table = shape.table
            y = position['y']
            for ri, row in enumerate(table.rows):
                x = position['x']
                for ci, cell in enumerate(row.cells):
                    cw = float(table.columns[ci].width) / EMU_PER_PX
                    rh = float(row.height) / EMU_PER_PX
                    if cell.text.strip():
                        objects.append({**common, 'name': f'{path}/cell-{ri + 1}-{ci + 1}',
                                        'kind': 'table_cell', 'role': 'content', 'text': cell.text.strip(),
                                        'bbox': {'x': round(x, 2), 'y': round(y, 2),
                                                 'w': round(cw, 2), 'h': round(rh, 2)},
                                        'position_note': '合并单元格位置按原表网格记录'})
                    x += cw
                y += float(row.height) / EMU_PER_PX
        if getattr(shape, 'shape_type', None) == 6:
            nested, gaps = extract_objects(shape.shapes, path, True)
            objects.extend(nested); incomplete.extend(gaps)
        elif getattr(shape, 'has_chart', False):
            incomplete.append({**common, 'kind': 'chart',
                               'reason': '原生图表标题、轴与标签未完整提取，须对照实页和数据核对。'})
        elif getattr(shape, 'shape_type', None) in (11, 13):
            incomplete.append({**common, 'kind': 'image',
                               'reason': '图片内文字未识别，须对照实页；包含校徽等品牌图片。'})
    return objects, incomplete


def _texts(shapes):
    """Compatibility helper for callers that only need extracted text."""
    objects, _ = extract_objects(shapes)
    yield from (item['text'] for item in objects)


def _normalize(text):
    return re.sub(r'\s+', '', str(text))


def audit_text_pages(pages):
    """Pure text/object review. Every page remains reviewable even with no finding.

    Input pages may contain ``objects`` (name/text/bbox/role) or ``text_blocks``.
    Positions and exact text are evidence for an editor, not a semantic score.
    """
    prepared, findings = [], []
    repeated = defaultdict(list)
    sequence_pages = []
    for index, original in enumerate(pages, 1):
        page = int(original.get('page', index))
        objects = [dict(item) for item in original.get('objects', [])]
        if not objects:
            objects = [{'name': f'text-{i + 1}', 'kind': 'text', 'role': 'content',
                        'text': str(text), 'bbox': None, 'coordinate_space': 'unknown'}
                       for i, text in enumerate(original.get('text_blocks', []))]
        for item in objects:
            item.setdefault('name', 'unnamed'); item.setdefault('role', 'content')
            item.setdefault('bbox', None); item.setdefault('coordinate_space', 'unknown')
            item['text'] = str(item.get('text', ''))
        texts = [item['text'] for item in objects if item['text'].strip()]
        prepared.append({'page': page, 'text_blocks': texts, 'objects': objects,
                         'incomplete_objects': list(original.get('incomplete_objects', [])),
                         'review_required': True,
                         'review_focus': ['重要判断是否由本页或相邻材料支持，事实状态和条件是否完整？',
                                          '逐句连读是否新增具体信息，重复是否用于必要题干、比较或操作？']})
        joined = '\n'.join(texts)
        for category, pattern, question in [
            ('inventory_rhetoric', INVENTORY, '数量是否帮助判断或办理？正常业务数量保留；若只是库存包装，核对具体对象与结果。'),
            ('absolute_claim', ABSOLUTE, '承诺适用哪些材料与条件？引文、辨错任务与否定语境须按完整原句判断。'),
            ('production_language', PROCESS, '制作参数是否属于本次听众任务？普通业务页移入底稿，维护培训可按需保留。'),
        ]:
            matches = list(dict.fromkeys(match.group(0) for match in pattern.finditer(joined)))
            if matches:
                findings.append({'page': page, 'category': category, 'excerpts': matches,
                                 'context': texts, 'review_question': question})
        counts = []
        sequence_objects = []
        local_fragments = defaultdict(list)
        for item in objects:
            text = item['text']
            normalized = _normalize(text)
            if len(normalized) >= 8 and item['role'] != 'context':
                repeated[normalized].append({'page': page, 'name': item['name'], 'text': text,
                                             'bbox': item['bbox'], 'role': item['role']})
            for fragment in re.split(r'[·|｜；;\n]', text):
                if ISOLATED_COUNT.fullmatch(fragment):
                    counts.append({'name': item['name'], 'text': fragment.strip(), 'bbox': item['bbox']})
            sequences = list(SEQUENCE.finditer(text))
            if sequences:
                sequence_objects.append({'name': item['name'], 'text': text,
                                         'matches': [match.group(0) for match in sequences]})
            for fragment in re.split(r'[，,；;。.!?！？\n]', text):
                key = _normalize(fragment)
                if 6 <= len(key) <= 34 and re.search(r'[\u3400-\u9fffA-Za-z]', key):
                    local_fragments[key].append(item['name'])
        for first, second in zip(objects, objects[1:]):
            if not re.fullmatch(NUMBER, first['text'].strip()) or not re.fullmatch(r'[套部类档种份]', second['text'].strip()):
                continue
            a, b = first.get('bbox'), second.get('bbox')
            if a and b and (abs(a['x'] - b['x']) > 180 or abs(a['y'] - b['y']) > 120):
                continue
            counts.append({'name': [first['name'], second['name']],
                           'text': first['text'].strip() + second['text'].strip(),
                           'bbox': [a, b]})
        # Two or more isolated quantities are a group to review, never wrong by definition.
        if len(counts) >= 2:
            findings.append({'page': page, 'category': 'detached_quantity_group', 'objects': counts,
                             'context': texts, 'review_question': '这些数量各指什么、是否可核对？业务清单与数量关系可保留，不为文风删除数字。'})
        if sum(len(item['matches']) for item in sequence_objects) >= 2:
            findings.append({'page': page, 'category': 'parallel_sequence_candidate',
                             'objects': sequence_objects, 'context': texts,
                             'review_question': '连读这些顺序句：是否各有实际对象、因果或操作依赖？真实实验步骤、办理时序和教学顺序保留。'})
        if sequence_objects:
            sequence_pages.append({'page': page, 'objects': sequence_objects})
        repeats = [{'text': key, 'objects': names} for key, names in local_fragments.items() if len(names) >= 2]
        if repeats:
            findings.append({'page': page, 'category': 'repeated_short_phrase', 'phrases': repeats,
                             'context': texts, 'review_question': '重复短句是否承担必要对照或作答提示？若只复述同一主张，合并并补具体信息。'})
    for normalized, occurrences in repeated.items():
        unique_pages = sorted({item['page'] for item in occurrences})
        if len(unique_pages) < 2:
            continue
        findings.append({'page': unique_pages[-1], 'pages': unique_pages,
                         'category': 'repeated_passage' if len(normalized) >= 35 else 'repeated_short_passage',
                         'also_on_page': unique_pages[0], 'excerpt': occurrences[0]['text'],
                         'occurrences': occurrences,
                         'review_question': '是否必要题干、同一材料比较、续表口径或稳定术语？保留理由须结合上下文，不按重复长度自动删改。'})
    if len(sequence_pages) >= 3:
        findings.append({'page': sequence_pages[-1]['page'], 'pages': [item['page'] for item in sequence_pages],
                         'category': 'recurring_sequence_candidate', 'occurrences': sequence_pages,
                         'review_question': '连续材料是否反复用同一顺序句包装不同主题？逐页核对实际依赖与新增内容，正常操作流程保留。'})
    for index, page in enumerate(prepared):
        page['adjacent_context'] = {
            'previous': {'page': prepared[index - 1]['page'], 'text_blocks': prepared[index - 1]['text_blocks']} if index else None,
            'next': {'page': prepared[index + 1]['page'], 'text_blocks': prepared[index + 1]['text_blocks']} if index + 1 < len(prepared) else None,
        }
    return {'schema_version': 2, 'page_count': len(prepared), 'status': 'human_review_required',
            'has_automated_findings': bool(findings),
            'limitations': '仅整理实际提取的文字与有限候选线索，不自动删改、判错或评分。未命中不代表正确、充分或自然；图片、图表及组合坐标限制见逐页记录，须对照最终实页。',
            'findings': findings, 'slides': prepared,
            'incomplete_object_count': sum(len(page['incomplete_objects']) for page in prepared)}


def audit_presentation(path):
    path = Path(path)
    prs = Presentation(str(path))
    pages = []
    for index, slide in enumerate(prs.slides, 1):
        objects, incomplete = extract_objects(slide.shapes)
        pages.append({'page': index, 'objects': objects, 'incomplete_objects': incomplete})
    result = audit_text_pages(pages)
    result.update({'file_name': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    return result


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
