#!/usr/bin/env bash
# Isolated build smoke test. Leaves fixtures and outputs for inspection.
set -euo pipefail
cd "$(dirname "$0")/.."
repo_root="$PWD"
fixture_dir="$(mktemp -d /tmp/drafter-compose.XXXXXX)"
export HOST_UID="$(id -u)"
export HOST_GID="$(id -g)"
export PAPERS_DIR="$fixture_dir/papers"
export BIB_DIR="$fixture_dir/bib"
export FONTS_DIR="${FONTS_DIR:-$repo_root/.devcontainer/fonts}"
mkdir -p "$PAPERS_DIR/sample/sections" "$PAPERS_DIR/bib" "$BIB_DIR"
cat > "$PAPERS_DIR/sample/.latexmkrc" <<'LATEXMK'
$pdf_mode = 4;
$aux_dir = '/tmp/latex-build/sample';
$lualatex = 'lualatex -synctex=1 -interaction=nonstopmode -halt-on-error %O %S';
LATEXMK
cat > "$PAPERS_DIR/sample/main.tex" <<'TEX'
\documentclass{jlreq}
\usepackage{luatexja-fontspec}
\setmainfont[Path=/usr/share/fonts/ms-fonts/]{times.ttf}
\setmainjfont[Path=/usr/share/fonts/ms-fonts/,FontIndex=0]{msmincho.ttc}
\title{Compose build verification}
\author{Drafter}
\begin{document}
\maketitle
\input{sections/introduction}
\end{document}
TEX
cat > "$PAPERS_DIR/sample/sections/introduction.tex" <<'TEX'
\section{Introduction}
日本語と English のビルド検証。共有文献を参照する~\cite{sample2026}。
\bibliographystyle{plain}
\bibliography{sample}
TEX
cat > "$BIB_DIR/sample.bib" <<'BIB'
@article{sample2026,
  author = {Example, Author},
  title = {Compose verification reference},
  journal = {Example Journal},
  year = {2026}
}
BIB
printf 'Fixtures and outputs: %s\n' "$fixture_dir"
docker compose --env-file .env.example config --quiet
make DOCKER_COMPOSE="docker compose --env-file .env.example" PAPER=sample build-pdf
for layout in article short review; do
    make DOCKER_COMPOSE="docker compose --env-file .env.example" \
        PAPER=sample FORMAT="$layout" WORD_TEMPLATE_DIR=/workspace/papers/word-templates build-docx
    cp "$PAPERS_DIR/sample/dist/main.docx" "$fixture_dir/$layout.docx"
done
# Exercise an arbitrary Linux UID even on macOS. This is not a WSL host test.
docker compose --env-file .env.example run --rm --user 12345:12345 drafter \
    sh -ec 'test "$(id -u)" = 12345; test ! -w /usr/share/fonts/ms-fonts/times.ttf;
    test ! -w /workspace/papers/bib/sample.bib;
    uv run python -c "import drafter, click"; mkdir -p /tmp/latex-build/uid-test'
python3 - "$fixture_dir" "$HOST_UID" "$HOST_GID" <<'PY'
import os
import sys
import zipfile
from pathlib import Path

fixture_dir = Path(sys.argv[1])
for path in (fixture_dir / "papers/sample/dist/main.pdf", *fixture_dir.glob("*.docx")):
    assert path.stat().st_size > 0, path
    assert path.stat().st_uid == int(sys.argv[2]), path
    # Docker Desktop can translate bind-mount groups on macOS.
    if sys.platform != "darwin":
        assert path.stat().st_gid == int(sys.argv[3]), path
    assert os.access(path, os.W_OK), path
    if path.suffix == ".pdf":
        assert path.read_bytes().startswith(b"%PDF-"), path
    else:
        with zipfile.ZipFile(path) as docx:
            assert docx.testzip() is None, path
            text = docx.read("word/document.xml").decode()
            assert "日本語" in text and "compose verification reference" in text.lower(), path
    print(f"PASS {path} ({path.stat().st_size} bytes, {os.stat(path).st_uid})")
PY
