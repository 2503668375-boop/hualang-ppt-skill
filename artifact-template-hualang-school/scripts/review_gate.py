#!/usr/bin/env python3
"""Check review evidence consistency, never the aesthetic quality of a deck."""
import argparse
import hashlib
import json
import posixpath
import re
from pathlib import Path
import sys
import xml.etree.ElementTree as E
import zipfile

P = 'http://schemas.openxmlformats.org/presentationml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
AREAS = ('content', 'expression', 'visual', 'file')
NOTICE = '只核审查记录一致性与文件证据，不能代替内容、审美或场景的人工判断。'


def digest(path):
    with path.open('rb') as stream:
        value = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def valid_hash(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-fA-F]{64}', value) is not None


def resolve(base, value):
    if not nonempty(value):
        raise ValueError('文件路径为空')
    return (base / value).resolve()


def slide_count(path):
    """Read the actual presentation order and ensure every slide part exists."""
    with zipfile.ZipFile(path) as archive:
        root = E.fromstring(archive.read('ppt/presentation.xml'))
        if root.tag != '{'+P+'}presentation':
            raise ValueError('不是有效的演示文稿主部件')
        relationships = E.fromstring(archive.read('ppt/_rels/presentation.xml.rels'))
        rels = {r.get('Id'): r for r in relationships}
        listing = root.find('{'+P+'}sldIdLst')
        slides = list(listing) if listing is not None else []
        if not slides:
            raise ValueError('演示文稿没有页面')
        for slide in slides:
            rel = rels[slide.get('{'+R+'}id')]
            if rel.get('TargetMode') == 'External' or rel.get('Type') != R+'/slide':
                raise ValueError('页面关系不指向内部幻灯片')
            target = rel.get('Target', '')
            part = target.lstrip('/') if target.startswith('/') else posixpath.normpath('ppt/'+target)
            if E.fromstring(archive.read(part)).tag != '{'+P+'}sld':
                raise ValueError('幻灯片部件无效：'+part)
        return len(slides)


def check(review_path):
    review_path = Path(review_path).resolve()
    base = review_path.parent
    errors = []
    count = 0
    scope = []
    full = False

    def fail(message):
        errors.append(message)

    def result():
        notice = NOTICE
        if count and scope and not full:
            notice += ' 本记录仅覆盖第'+ '、'.join(map(str, scope))+'页，不能声明全稿通过。'
        return {'schemaVersion': 1,
                'decision': 'return_for_revision' if errors else 'ready_for_human_signoff',
                'coversWholeDeck': full, 'slideCount': count, 'scope': scope,
                'errors': errors, 'notice': notice}

    try:
        record = json.loads(review_path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        fail('无法读取审查记录：'+str(exc))
        return result()
    if not isinstance(record, dict):
        fail('审查记录必须为JSON对象')
        return result()
    if type(record.get('schemaVersion')) is not int or record['schemaVersion'] != 1:
        fail('schemaVersion须为1')
    artifact = record.get('artifact')
    if not isinstance(artifact, dict):
        fail('缺少artifact文件信息')
        return result()
    try:
        deck = resolve(base, artifact.get('path'))
        actual_hash = digest(deck)
        count = slide_count(deck)
    except (OSError, ValueError, KeyError, E.ParseError, zipfile.BadZipFile) as exc:
        fail('无法回读PPTX：'+str(exc))
        return result()
    if not valid_hash(artifact.get('sha256')) or artifact['sha256'].lower() != actual_hash:
        fail('artifact.sha256与当前PPTX不一致')
    if not valid_hash(record.get('renderSourceSha256')) or record['renderSourceSha256'].lower() != actual_hash:
        fail('渲染来源不是当前PPTX版本')

    def page_number(value):
        return type(value) is int and 1 <= value <= count

    wanted = record.get('scope', list(range(1, count+1)))
    if not isinstance(wanted, list) or not wanted or any(not page_number(n) for n in wanted):
        fail('scope须为实际存在的非空页码列表')
        return result()
    if len(set(wanted)) != len(wanted):
        fail('scope页码重复')
    scope = sorted(set(wanted))
    scope_set = set(scope)
    full = scope_set == set(range(1, count+1))
    pages = record.get('pages')
    if not isinstance(pages, list):
        fail('缺少pages逐页记录')
        pages = []
    observed = set()
    image_hashes = {}
    for index, page in enumerate(pages, 1):
        if not isinstance(page, dict):
            fail(f'pages第{index}项不是对象')
            continue
        number = page.get('slide')
        if not page_number(number) or number not in scope_set:
            fail(f'pages第{index}项页码不在审查范围内')
            continue
        if number in observed:
            fail(f'第{number}页审查记录重复')
        observed.add(number)
        if not nonempty(page.get('scene')) or not nonempty(page.get('subject')):
            fail(f'第{number}页缺少场景或主体对象')
        if page.get('verdict') != 'pass':
            fail(f'第{number}页尚未完成通过判断')
        try:
            render = resolve(base, page.get('render'))
            with render.open('rb') as stream:
                signature = stream.read(8)
            if signature != b'\x89PNG\r\n\x1a\n' and not signature.startswith(b'\xff\xd8\xff'):
                raise ValueError('渲染文件不是PNG或JPEG')
            actual = digest(render)
            image_hashes[number] = actual
            if not valid_hash(page.get('renderSha256')) or page['renderSha256'].lower() != actual:
                fail(f'第{number}页渲染摘要不一致')
        except (OSError, ValueError) as exc:
            fail(f'第{number}页渲染无法回读：{exc}')
    missing = sorted(scope_set-observed)
    if missing:
        fail('缺少逐页审查：'+ '、'.join(map(str, missing)))

    gates = record.get('gates')
    if not isinstance(gates, dict):
        fail('缺少gates四项审查')
        gates = {}
    for area in AREAS:
        gate = gates.get(area)
        if not isinstance(gate, dict):
            fail('缺少审查项：'+area)
            continue
        allowed = ('pass',) if full else ('pass', 'not_applicable')
        if gate.get('verdict') not in allowed:
            fail('审查项尚未通过：'+area)
        evidence = gate.get('evidence')
        if not isinstance(evidence, list) or not evidence:
            fail('审查项缺少具体观察：'+area)
            continue
        for item in evidence:
            if not isinstance(item, dict):
                fail('审查观察格式错误：'+area)
                continue
            numbers = item.get('slides')
            if (not isinstance(numbers, list) or not numbers or
                    any(not page_number(n) or n not in scope_set for n in numbers)):
                fail('审查观察未指向范围内页面：'+area)
            if not nonempty(item.get('observation')):
                fail('审查项缺少实际观察文字：'+area)

    issues = record.get('issues')
    if not isinstance(issues, list):
        fail('issues须列明发现的问题；未发现时用空列表')
        issues = []
    issue_ids = set()
    for index, issue in enumerate(issues, 1):
        if not isinstance(issue, dict):
            fail(f'issues第{index}项不是对象')
            continue
        name = issue.get('id')
        if not nonempty(name):
            fail(f'issues第{index}项缺少id')
            name = str(index)
        elif name in issue_ids:
            fail('问题id重复：'+name)
        issue_ids.add(name)
        number = issue.get('slide')
        if not page_number(number) or number not in scope_set:
            fail('问题页不在本次审查范围内：'+name)
        if issue.get('area') not in AREAS or not nonempty(issue.get('problem')):
            fail('问题缺少类别或描述：'+name)
        if issue.get('status') != 'fixed':
            fail('仍有未修复问题：'+name)
            continue
        if not nonempty(issue.get('resolution')):
            fail('问题标为fixed但未说明修复：'+name)
        checked = issue.get('checkedRenderSha256')
        if (not valid_hash(checked) or not page_number(number) or
                checked.lower() != image_hashes.get(number)):
            fail('问题修复未以当前页面渲染复查：'+name)
    return result()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('review', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    outcome = check(args.review)
    encoded = json.dumps(outcome, ensure_ascii=False, indent=2)+'\n'
    if args.output:
        # A mistaken output argument must not replace a deck or a review input.
        protected = {args.review.resolve()}
        try:
            record = json.loads(args.review.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            record = {}
        if isinstance(record, dict):
            inputs = []
            artifact = record.get('artifact')
            if isinstance(artifact, dict):
                inputs.append(artifact.get('path'))
            pages = record.get('pages')
            if isinstance(pages, list):
                inputs.extend(p.get('render') for p in pages if isinstance(p, dict))
            for value in inputs:
                try:
                    protected.add(resolve(args.review.resolve().parent, value))
                except (OSError, ValueError):
                    pass
        if args.output.resolve() in protected:
            parser.error('--output不能覆盖PPTX、审查记录或渲染输入')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding='utf-8')
    sys.stdout.write(encoded)
    return int(outcome['decision'] != 'ready_for_human_signoff')


if __name__ == '__main__':
    sys.exit(main())
