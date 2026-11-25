#!/usr/bin/env python3
"""ドキュメントの完了前チェック（write-docs skill §7）。

使い方: python3 check_docs.py [docs_dir ...] [--exclude PATH ...]
チェック内容:
  1. Markdownの相対リンク・画像リンクのリンク切れ
  2. Issue / PR番号（#12、issues/12）の混入
  3. 図の編集元（.drawio / .puml / .mmd）に対応する .svg の有無
  4. .md を含む各フォルダの README.md の有無
問題があれば一覧を表示して終了コード1で終わる。
"""

import argparse
import os
import re
import sys
from collections.abc import Iterator

LINK = re.compile(r"\]\(([^)\s]+)\)")
ISSUE = re.compile(r"(?<![\w&])#\d{1,4}\b|issues/\d+|pull/\d+")
FENCE = re.compile(r"```.*?```", re.S)
INLINE = re.compile(r"`[^`\n]*`")
SKIP_DIRS = {"node_modules", ".git", ".venv", ".next", "dist", "build"}


def md_files(roots: list[str], excludes: list[str]) -> Iterator[str]:
    for root in roots:
        for d, dirs, files in os.walk(root):
            dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
            if any(os.path.normpath(d).startswith(os.path.normpath(e)) for e in excludes):
                continue
            for f in files:
                yield os.path.join(d, f)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("roots", nargs="*", default=["docs"])
    ap.add_argument("--exclude", nargs="*", default=[], help="対象外のパス（例: docs/features）")
    a = ap.parse_args()

    problems = []
    all_files = list(md_files(a.roots, a.exclude))
    folders_with_md = set()

    for path in all_files:
        base, ext = os.path.splitext(path)
        d = os.path.dirname(path)
        if ext == ".md":
            folders_with_md.add(d)
            text = open(path, encoding="utf-8").read()
            body = INLINE.sub("", FENCE.sub("", text))
            for m in LINK.finditer(body):
                t = m.group(1).split("#")[0]
                if not t or t.startswith(("http://", "https://", "mailto:")):
                    continue
                if not os.path.exists(os.path.normpath(os.path.join(d, t))):
                    problems.append(f"リンク切れ: {path} -> {m.group(1)}")
            for i, line in enumerate(body.splitlines(), 1):
                if ISSUE.search(line):
                    problems.append(f"Issue/PR番号: {path}: {line.strip()[:60]}")
        elif ext in (".drawio", ".puml", ".mmd"):
            if not os.path.exists(base + ".svg"):
                problems.append(f"書き出し漏れ（.svgなし）: {path}")

    for d in sorted(folders_with_md):
        if not os.path.exists(os.path.join(d, "README.md")):
            problems.append(f"README.mdなし: {d}/")

    if problems:
        print("\n".join(problems))
        print(f"\n{len(problems)} 件の問題")
        sys.exit(1)
    print("問題なし（リンク切れ・Issue番号・書き出し漏れ・README）")


if __name__ == "__main__":
    main()
