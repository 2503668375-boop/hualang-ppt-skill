#!/usr/bin/env python3
"""Check distributable skill assets and links using Python's standard library."""

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit


NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
}
SKILL_NAME = "artifact-template-hualang-school"


def local_target(base, target, allowed_root):
    parsed = urlsplit(target.strip().strip("<>"))
    if parsed.scheme or parsed.netloc or not parsed.path:
        return None
    resolved = (base / unquote(parsed.path)).resolve()
    try:
        resolved.relative_to(allowed_root)
    except ValueError:
        raise ValueError("相对引用指向仓库之外：" + target)
    return resolved


def inspect_pptx(pptx_path):
    with zipfile.ZipFile(pptx_path) as archive:
        corrupt = archive.testzip()
        if corrupt:
            raise ValueError("压缩内容损坏：" + corrupt)
        names = set(archive.namelist())
        for name in names:
            part = PurePosixPath(name)
            if part.is_absolute() or ".." in part.parts or "\\" in name:
                raise ValueError("压缩包包含不安全路径：" + name)
        required = {"[Content_Types].xml", "ppt/presentation.xml"}
        missing = sorted(required - names)
        if missing:
            raise ValueError("缺少 PPTX 必需文件：" + ", ".join(missing))
        presentation = ET.fromstring(archive.read("ppt/presentation.xml"))
        slide_ids = presentation.findall("p:sldIdLst/p:sldId", NS)
        slide_parts = sorted(
            name for name in names
            if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
        )
        if len(slide_ids) != len(slide_parts):
            raise ValueError("幻灯片清单与幻灯片文件数量不一致")
        tables = charts = shapes = 0
        for name in slide_parts:
            slide = ET.fromstring(archive.read(name))
            tables += len(slide.findall(".//a:tbl", NS))
            charts += len(slide.findall(".//c:chart", NS))
            shapes += len(slide.findall(".//p:sp", NS))
        return {
            "slides": len(slide_ids),
            "native_tables": tables,
            "native_charts": charts,
            "slide_shapes": shapes,
        }


def validate(root, expected_slides=None):
    errors = []
    summary = {}
    package = root / SKILL_NAME
    required = [
        package / "SKILL.md",
        package / "artifact-template.json",
        package / "agents/openai.yaml",
        package / "assets/source-original.pptx",
        package / "assets/one-page-report.docx",
    ]
    for file in required:
        if not file.is_file() or file.stat().st_size == 0:
            errors.append("缺少或为空：" + str(file.relative_to(root)))

    manifest_path = package / "artifact-template.json"
    reference = None
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("kind") != "presentation":
                errors.append("manifest.kind 应为 presentation")
            for key in ("reference", "preview"):
                value = manifest.get(key)
                if not isinstance(value, str) or not value:
                    errors.append("manifest 缺少有效字段：" + key)
                    continue
                target = local_target(package, value, package.resolve())
                if target is None or not target.is_file() or target.stat().st_size == 0:
                    errors.append("manifest 资产不存在或为空：" + value)
                elif key == "reference":
                    reference = target
        except (ValueError, OSError) as exc:
            errors.append("manifest 无效：" + str(exc))

    skill_path = package / "SKILL.md"
    if skill_path.is_file():
        content = skill_path.read_text(encoding="utf-8")
        frontmatter = re.match(r"\A---\s*\n(.*?)\n---(?:\s*\n|$)", content, re.S)
        if not frontmatter:
            errors.append("SKILL.md 缺少 YAML frontmatter")
        else:
            header = frontmatter.group(1)
            if not re.search(r"^name:\s*[\"']?" + re.escape(SKILL_NAME) + r"[\"']?\s*$", header, re.M):
                errors.append("SKILL.md 的 name 与技能目录不一致")
            if not re.search(r"^description:\s*\S", header, re.M):
                errors.append("SKILL.md 缺少 description")

    # Scan only maintained Markdown, ignoring Git and local dependency folders.
    ignored = {".git", "node_modules", "build", "tmp", ".cache", "local", "backups"}
    for file in sorted(root.rglob("*.md")):
        if ignored.intersection(file.relative_to(root).parts):
            continue
        text = file.read_text(encoding="utf-8")
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text):
            try:
                path = local_target(file.parent, target, root)
                if path is not None and not path.exists():
                    errors.append(str(file.relative_to(root)) + "：链接不存在 " + target)
            except ValueError as exc:
                errors.append(str(file.relative_to(root)) + "：" + str(exc))
        for target in re.findall(r"(?:href|src)=[\"']([^\"']+)[\"']", text):
            try:
                path = local_target(file.parent, target, root)
                if path is not None and not path.exists():
                    errors.append(str(file.relative_to(root)) + "：素材不存在 " + target)
            except ValueError as exc:
                errors.append(str(file.relative_to(root)) + "：" + str(exc))

    if reference is not None:
        try:
            summary = inspect_pptx(reference)
            if expected_slides is not None and summary["slides"] != expected_slides:
                errors.append("模板页数为 {}，本次要求为 {}".format(summary["slides"], expected_slides))
        except (ValueError, OSError, zipfile.BadZipFile, ET.ParseError) as exc:
            errors.append("PPTX 无效：" + str(exc))

    return {"ok": not errors, "template": summary, "errors": errors}


def main():
    parser = argparse.ArgumentParser(description="核对华朗技能的文件、相对引用与 PPTX 原生对象结构")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help="仓库根目录")
    parser.add_argument("--expected-slides", type=int, help="本次发布预期页数；不设置时只报告实际页数")
    args = parser.parse_args()
    if args.expected_slides is not None and args.expected_slides < 1:
        parser.error("--expected-slides 必须大于 0")
    result = validate(args.root.resolve(), args.expected_slides)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
