#!/usr/bin/env python3
"""Review saved PPTX composition, with an optional semantic manifest.

Geometry findings ignore layout names, text, colours and continuation reasons.
They identify pages to inspect, not aesthetic failures. Standard library only.
"""
import argparse
import collections
import hashlib
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as E
import zipfile
from check_style_contract import NS, slide_parts

CHART_NS = 'http://schemas.openxmlformats.org/drawingml/2006/chart'
IDENTITY = (1, 0, 0, 1, 0, 0)


def multiply(a, b):
    """Compose affine transforms: a(b(point))."""
    aa, ab, ac, ad, ae, af = a
    ba, bb, bc, bd, be, bf = b
    return (aa*ba+ac*bb, ab*ba+ad*bb, aa*bc+ac*bd, ab*bc+ad*bd,
            aa*be+ac*bf+ae, ab*be+ad*bf+af)


def point(matrix, x, y):
    a, b, c, d, e, f = matrix
    return a*x+c*y+e, b*x+d*y+f


def values(transform, name, fields, default):
    node = transform.find('a:'+name, NS) if transform is not None else None
    return tuple(float(node.get(k, v)) for k, v in zip(fields, default)) if node is not None else default


def rotation(transform, x, y, w, h):
    angle = math.radians(float(transform.get('rot', 0))/60000)
    fx = -1 if transform.get('flipH') in ('1', 'true') else 1
    fy = -1 if transform.get('flipV') in ('1', 'true') else 1
    c, s = math.cos(angle), math.sin(angle)
    cx, cy = x+w/2, y+h/2
    linear = (c*fx, s*fx, -s*fy, c*fy, 0, 0)
    return multiply((1, 0, 0, 1, cx, cy), multiply(linear, (1, 0, 0, 1, -cx, -cy)))


def group_transform(transform):
    if transform is None:
        return IDENTITY
    x, y = values(transform, 'off', ('x', 'y'), (0, 0))
    w, h = values(transform, 'ext', ('cx', 'cy'), (1, 1))
    ox, oy = values(transform, 'chOff', ('x', 'y'), (0, 0))
    ow, oh = values(transform, 'chExt', ('cx', 'cy'), (w, h))
    sx, sy = w/(ow or 1), h/(oh or 1)
    return multiply(rotation(transform, x, y, w, h), (sx, 0, 0, sy, x-ox*sx, y-oy*sy))


def object_box(transform, parent, slide_size):
    if transform is None:
        return None
    x, y = values(transform, 'off', ('x', 'y'), (0, 0))
    w, h = values(transform, 'ext', ('cx', 'cy'), (0, 0))
    matrix = multiply(parent, rotation(transform, x, y, w, h))
    corners = [point(matrix, xx, yy) for xx in (x, x+w) for yy in (y, y+h)]
    xs, ys = zip(*corners)
    sw, sh = slide_size
    return [min(xs)/sw, min(ys)/sh, (max(xs)-min(xs))/sw, (max(ys)-min(ys))/sh]


def read_objects(root, slide_size):
    objects = []

    def walk(tree, parent=IDENTITY):
        for node in tree:
            tag = node.tag.rsplit('}', 1)[-1]
            if tag == 'grpSp':
                transform = node.find('p:grpSpPr/a:xfrm', NS)
                walk(node, multiply(parent, group_transform(transform)))
                continue
            if tag not in ('sp', 'pic', 'graphicFrame', 'cxnSp'):
                continue
            transform = node.find('p:xfrm', NS) if tag == 'graphicFrame' else node.find('p:spPr/a:xfrm', NS)
            box = object_box(transform, parent, slide_size)
            if box is None:
                continue
            text = ''.join(n.text or '' for n in node.findall('.//a:t', NS))
            preset = node.find('p:spPr/a:prstGeom', NS)
            geometry = preset.get('prst', '') if preset is not None else ''
            if tag == 'pic':
                kind = 'picture'
            elif tag == 'graphicFrame':
                kind = 'table' if node.find('.//a:tbl', NS) is not None else (
                    'chart' if node.find('.//{'+CHART_NS+'}chart') is not None else 'frame')
            elif tag == 'cxnSp' or geometry in ('line', 'straightConnector1'):
                kind = 'line'
            else:
                kind = 'text' if text and geometry in ('', 'rect') and node.find('p:spPr/a:solidFill', NS) is None else 'shape'
            filled = node.find('p:spPr/a:solidFill', NS) is not None or node.find('p:style/a:fillRef', NS) is not None
            outline = node.find('p:spPr/a:ln/a:solidFill', NS) is not None
            panel = tag == 'sp' and geometry in ('rect', 'roundRect', 'round1Rect', 'round2SameRect') and (filled or outline)
            x, y, w, h = box
            # Ignore fixed header/footer, full-slide backgrounds and tiny marks.
            if y+h <= .14 or y >= .94 or w*h > .85:
                continue
            if max(w, h) < .025 or (min(w, h) < .002 and kind != 'line'):
                continue
            objects.append({'kind': kind, 'box': box, 'characters': len(text),
                            'geometry': geometry, 'panel': panel})

    tree = root.find('p:cSld/p:spTree', NS)
    if tree is not None:
        walk(tree)
    return objects


def panel_groups(objects):
    """Find equally sized independent rectangular containers, not bar marks."""
    panels = [o for o in objects if o['panel'] and .02 <= o['box'][2]*o['box'][3] <= .42
              and o['box'][2] >= .12 and o['box'][3] >= .10]
    # A nested coloured heading is part of its containing card, not another card.
    panels = [o for o in panels if not any(
        other is not o and other['box'][2]*other['box'][3] > o['box'][2]*o['box'][3]*1.15
        and other['box'][0] <= o['box'][0]+.003 and other['box'][1] <= o['box'][1]+.003
        and other['box'][0]+other['box'][2] >= o['box'][0]+o['box'][2]-.003
        and other['box'][1]+other['box'][3] >= o['box'][1]+o['box'][3]-.003
        for other in panels)]
    groups, used = [], set()
    for index, first in enumerate(panels):
        if index in used:
            continue
        w, h = first['box'][2:]
        peers = [(i, o) for i, o in enumerate(panels) if i not in used
                 and abs(o['box'][2]-w) <= w*.12 and abs(o['box'][3]-h) <= h*.12]
        rows = []
        for i, ob in sorted(peers, key=lambda item: (item[1]['box'][1], item[1]['box'][0])):
            row = next((r for r in rows if abs(r[0][1]['box'][1]-ob['box'][1]) <= .025), None)
            if row is None:
                rows.append([(i, ob)])
            else:
                row.append((i, ob))
        rows = [r for r in rows if len(r) >= 2]
        if not rows:
            continue
        ids = [i for row in rows for i, _ in row]
        used.update(ids)
        groups.append({'rows': len(rows), 'columns_by_row': [len(r) for r in rows],
                       'panels': len(ids), 'boxes': [[round(v, 4) for v in o['box']] for r in rows for _, o in r]})
    return groups


def signature(objects):
    geometry = [[o['kind'], o['geometry'] if o['kind'] == 'shape' else '',
                 *[round(v, 3) for v in o['box']]] for o in objects]
    return hashlib.sha256(json.dumps(sorted(geometry, key=str)).encode()).hexdigest()


def weight(obj):
    if obj['kind'] in ('chart', 'table', 'picture', 'frame'):
        return 5
    if obj['panel']:
        return 3
    return .35 if obj['kind'] == 'line' else 1


def similarity(left, right, mirror=False):
    """Weighted geometric matching; text/colour/labels cannot raise the score."""
    if not left or not right:
        return 0
    possible = []
    for i, a in enumerate(left):
        ax, ay, aw, ah = a['box']
        if mirror:
            ax = 1-ax-aw
        for j, b in enumerate(right):
            if a['kind'] != b['kind'] or (a['kind'] == 'shape' and a['geometry'] != b['geometry']):
                continue
            bx, by, bw, bh = b['box']
            distance = max(abs(ax-bx), abs(ay-by), abs(aw-bw), abs(ah-bh))
            if distance > .04:
                continue
            scale = max(min(aw, bw), min(ah, bh), .02)
            if distance > max(.012, scale*.16):
                continue
            quality = 1-min(distance/.08, .35)
            possible.append((quality*min(weight(a), weight(b)), i, j))
    matched_left, matched_right, matched = set(), set(), 0
    for score, i, j in sorted(possible, reverse=True):
        if i not in matched_left and j not in matched_right:
            matched_left.add(i)
            matched_right.add(j)
            matched += score
    return 2*matched/(sum(map(weight, left))+sum(map(weight, right)))


def audit(pptx, manifest=None):
    errors, warnings, rows, findings = [], [], [], []
    manifest = manifest or {}
    entries = manifest.get('slides')
    with zipfile.ZipFile(pptx) as archive:
        parts = slide_parts(archive)
        if entries is None:
            entries = [{'slide': i} for i in (range(2, len(parts)) if len(parts) >= 3 else range(1, len(parts)+1))]
        by = {r['slide']: r for r in entries}
        expected = list(range(2, len(parts))) if len(parts) >= 3 else list(range(1, len(parts)+1))
        if len(by) != len(entries) or sorted(by) != expected:
            errors.append('构图清单必须覆盖全部正文页，页码不能重复或缺失')
        presentation = E.fromstring(archive.read('ppt/presentation.xml'))
        size = presentation.find('p:sldSz', NS)
        slide_size = (float(size.get('cx')), float(size.get('cy'))) if size is not None else (12192000, 6858000)
        object_sets = {}
        for number, part in enumerate(parts, 1):
            root = E.fromstring(archive.read(part))
            objects = read_objects(root, slide_size)
            object_sets[number] = objects
            kinds = collections.Counter(o['kind'] for o in objects)
            row = {'slide': number, 'family': by.get(number, {}).get('family'),
                   'continuationReason': by.get(number, {}).get('continuationReason'),
                   'body_characters': sum(o['characters'] for o in objects),
                   'text_boxes': sum(bool(o['characters']) for o in objects),
                   'tables': kinds['table'], 'charts': kinds['chart'], 'pictures': kinds['picture'],
                   'native_shapes': len(objects), 'geometry_signature': signature(objects),
                   'panel_groups': panel_groups(objects)}
            rows.append(row)

    def add(code, pages, detail, **extra):
        reasons = {str(p): by[p]['continuationReason'] for p in pages
                   if p in by and by[p].get('continuationReason')}
        findings.append({'code': code, 'slides': pages, 'detail': detail,
                         'continuation_reasons': reasons, **extra})
        suffix = '；已登记连续理由，仍需联排确认：'+ '；'.join(reasons.values()) if reasons else ''
        warnings.append(detail+suffix)

    ordered = sorted(n for n in by if 1 <= n <= len(parts))
    similar_pairs, neighbors = [], collections.defaultdict(set)
    for index, left in enumerate(ordered):
        for right in ordered[index+1:]:
            a, b = object_sets[left], object_sets[right]
            direct, mirrored = similarity(a, b), similarity(a, b, mirror=True)
            score = max(direct, mirrored)
            if score < .84:
                continue
            pair = {'slides': [left, right], 'similarity': round(score, 3),
                    'mirrored': mirrored > direct+.015,
                    'exact': rows[left-1]['geometry_signature'] == rows[right-1]['geometry_signature']}
            similar_pairs.append(pair)
            neighbors[left].add(right)
            neighbors[right].add(left)
            if right == left+1:
                label = '完全重复' if pair['exact'] else ('镜像近似' if pair['mirrored'] else '近似重复')
                add('adjacent-geometry', [left, right],
                    f'第{left}、{right}页正文几何{label}（相似度{score:.0%}），核对是否服务同题推理或必要比较', similarity=pair['similarity'])
    # Avoid transitive A~B~C clusters when A and C are actually different.
    covered = set()
    for anchor in sorted(neighbors, key=lambda n: (-len(neighbors[n]), n)):
        cluster = sorted({anchor} | neighbors[anchor])
        if len(cluster) >= 3 and not set(cluster).issubset(covered):
            add('recurring-geometry', cluster,
                '第'+ '、'.join(map(str, cluster))+'页反复使用近似主体骨架，需查看全稿的观看任务与信息推进')
            covered.update(cluster)
    for pair in similar_pairs:
        left, right = pair['slides']
        if right > left+1 and not {left, right}.issubset(covered):
            add('revisited-geometry', [left, right], f'第{left}、{right}页再次使用近似主体骨架，结合章节与观看任务复核', similarity=pair['similarity'])
    pair_set = {tuple(pair['slides']) for pair in similar_pairs}
    for index in range(len(ordered)-3):
        a, b, c, d = ordered[index:index+4]
        if (a, c) in pair_set and (b, d) in pair_set and (a, b) not in pair_set:
            add('abab-geometry', [a, b, c, d], f'第{a}—{d}页实际正文几何存在ABAB重复，检查是否仅交替套用两种骨架')
    panel_pages = [n for n in ordered if rows[n-1]['panel_groups']]
    for left, right in zip(panel_pages, panel_pages[1:]):
        if right == left+1:
            add('adjacent-panel-grid', [left, right], f'第{left}、{right}页连续使用等宽矩形面板组，检查是否将不同关系都装入卡片')
    if len(panel_pages) >= 3:
        add('recurring-panel-grid', panel_pages,
            f'{len(panel_pages)}/{len(ordered)}页正文使用等宽矩形面板组（第'+ '、'.join(map(str, panel_pages))+'页），此计数仅提示复核，不是配额或失败判定')
    families = [by[n].get('family') for n in ordered]
    for a, b in zip(ordered, ordered[1:]):
        if by[a].get('family') and by[a].get('family') == by[b].get('family'):
            add('adjacent-family', [a, b], f'第{a}、{b}页清单标注同构，结合实际材料复核')
    for i in range(len(ordered)-3):
        f = families[i:i+4]
        if all(f) and f[0] == f[2] and f[1] == f[3]:
            pages = ordered[i:i+4]
            add('abab-family', pages, f'第{pages[0]}—{pages[-1]}页清单存在ABAB重复，结合实际观看任务复核')
    for i in range(len(ordered)-7):
        count = collections.Counter(f for f in families[i:i+8] if f)
        if count:
            family, number = count.most_common(1)[0]
            if number > 4:
                pages = ordered[i:i+8]
                add('dominant-family', pages, f'第{pages[0]}—{pages[-1]}页中，{family}标注{number}次，须实看复核')
    times = {}
    for entry in entries:
        if entry.get('lesson'):
            times[entry['lesson']] = times.get(entry['lesson'], 0)+entry.get('minutes', 0)
    return {'ok': not errors, 'structure_valid': not errors,
            'quality_verdict': 'not_assessed', 'human_visual_review_required': True,
            'findings_to_review': len(findings),
            'slide_count': len(rows), 'content_pages': len(ordered),
            'layout_families': len({f for f in families if f}),
            'planned_minutes_by_lesson': times, 'errors': errors, 'warnings': warnings,
            'findings': findings, 'similar_pairs': similar_pairs, 'panel_grid_pages': panel_pages,
            'slide_size_emu': list(slide_size), 'pages': rows,
            'scope': '最终文件的正文原生几何及可选清单检查；排除页眉页脚与继承母版。近似与面板提示不证明审美、教学质量或必须换版，仍需逐页和联排实看；不检测整页图片内部或SmartArt内部构图。'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pptx', type=Path)
    parser.add_argument('manifest', nargs='?', type=Path, help='可选逐页JSON清单，兼容原接口')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        result = audit(args.pptx, json.loads(args.manifest.read_text()) if args.manifest else None)
    except (OSError, ValueError, KeyError, TypeError, E.ParseError, zipfile.BadZipFile) as error:
        print(json.dumps({'ok': False, 'errors': [str(error)]}, ensure_ascii=False, indent=2))
        return 1
    if args.output:
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'pages'}, ensure_ascii=False, indent=2))
    return int(not result['ok'])


if __name__ == '__main__':
    sys.exit(main())
