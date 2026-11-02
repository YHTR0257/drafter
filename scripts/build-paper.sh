#!/usr/bin/env bash
# Container-side adapter for the existing Python CLIs. No make required.
set -euo pipefail
format="${1:?Specify pdf, docx, lint or review}"
paper="${2:?Specify a paper directory name}"
main_tex="${3:-main.tex}"
case "$format" in
    pdf|docx|lint|review) ;;
    *) echo "Unknown build format: $format" >&2; exit 2 ;;
esac
cd "/workspace/papers/$paper"
if [ "$format" = review ]; then
    uv run python -m drafter.reviewer.pipeline --input "$main_tex" \
        --rules-dir /workspace/templates/rules --output dist/review-report.md
    exit
fi
if [ "${SKIP_LINT:-0}" = 1 ] && [ "$format" != lint ]; then
    echo 'lint: skipped explicitly (SKIP_LINT=1)' >&2
else
    uv run python -m drafter.linter.pipeline --input "$main_tex"
fi
if [ "$format" = lint ]; then
    exit
fi
mkdir -p dist
if [ "$format" = pdf ]; then
    export BIBINPUTS="/workspace/papers/bib:"
    uv run latexmk -lualatex -output-directory=dist "$main_tex"
    exit
fi
word_template_dir="${WORD_TEMPLATE_DIR:-/workspace/templates/msword}"
template="${WORD_TEMPLATE:-template-article.docx}"
output="dist/${main_tex%.tex}.docx"
if [ ! -f "$word_template_dir/$template" ]; then
    uv run python -m drafter.converter.word_template_pipeline --output-dir "$word_template_dir"
fi
set --
for bibliography in /workspace/papers/bib/*.bib; do
    if [ -f "$bibliography" ]; then
        set -- "$@" --bibliography "$bibliography"
    fi
done
uv run python -m drafter.converter.pipeline --input "$main_tex" "$@" \
    --template "$word_template_dir/$template" \
    --defaults /workspace/templates/pandoc/defaults.yaml \
    --resource-path . --resource-path /workspace/figures --output "$output"
