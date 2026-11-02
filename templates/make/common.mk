# ============================================================
# drafter - common.mk
# 各 papers/*/Makefile から include して使用する共通ルール
# ============================================================

# --- デフォルト値（各paperのMakefileで上書き可能） ---
MAIN_TEX     ?= main.tex
BIB_DIR      ?= ../bib
FIGURES_DIR  ?= ../../figures
WORD_TEMPLATE ?= template-article.docx
REVIEW_WORD_TEMPLATE ?= template-review.docx
RULES_DIR    ?= ../../templates/rules
PANDOC_DEFAULTS ?= ../../templates/pandoc/defaults.yaml
TEMPLATES_WORD_DIR ?= ../../templates/msword

# --- 導出変数 ---
# latexmkのaux_dirはdist/の外（既定では/tmp配下）にあるためcleanで消え残る。
# 定義の単一の情報源は.latexmkrcなので、そこから読み取る。
LATEXMKRC    ?= .latexmkrc
AUX_DIR_RE   := s/^\$$aux_dir[[:space:]]*=[[:space:]]*'\([^']*\)'.*/\1/p
AUX_DIR      := $(shell sed -n "$(AUX_DIR_RE)" $(LATEXMKRC) 2>/dev/null)
MAIN_BASE    := $(basename $(MAIN_TEX))
DIST_DIR     := dist
DIST_PDF     := $(DIST_DIR)/$(MAIN_BASE).pdf
DIST_DOCX    := $(DIST_DIR)/$(MAIN_BASE).docx
DIST_REVIEW_DOCX := $(DIST_DIR)/$(MAIN_BASE)-review.docx
REVIEW_REPORT := $(DIST_DIR)/review-report.md

# --- bib自動検出 ---
BIB_SOURCES  := $(wildcard $(BIB_DIR)/*.bib)
PANDOC_BIB_FLAGS := $(foreach bib,$(BIB_SOURCES),--bibliography=$(bib))

# --- LaTeX関連 ---
TEX_SOURCES  := $(wildcard *.tex) $(wildcard sections/*.tex)
FIG_SOURCES  := $(wildcard figures/*)

# --- Pandocの画像探索先 ---
# 中間ファイルがdist/にあるため、Pandocの既定探索先もdist/になる。
# \graphicspath は Pandoc に効かないので明示する。
PANDOC_RESOURCE_FLAGS := --resource-path . --resource-path $(FIGURES_DIR)

# --- latexmkにbibパスを通す ---
export BIBINPUTS := $(BIB_DIR):

# --- phony ---
.PHONY: all review lint pdf docx docx-review clean

# --- デフォルトターゲット ---
all: pdf docx

# ============================================================
# review: LLM校閲（人間の介入を前提、ビルドチェーンには含めない）
# ============================================================
review: $(REVIEW_REPORT)

$(REVIEW_REPORT): $(TEX_SOURCES) | $(DIST_DIR)
	uv run python -m drafter.reviewer.pipeline \
		--input $(MAIN_TEX) \
		--rules-dir $(RULES_DIR) \
		--output $@

# ============================================================
# lint: 構文チェック・Pandoc互換化（失敗時ビルドをブロック）
# ============================================================
lint:
	uv run python -m drafter.linter.pipeline \
		--input $(MAIN_TEX)

# ============================================================
# pdf: LaTeXコンパイル（lint通過が前提）
# ============================================================
pdf: lint | $(DIST_DIR)
	latexmk -lualatex -output-directory=$(DIST_DIR) $(MAIN_TEX)

# ============================================================
# docx: Pandoc変換（lint通過が前提）
# WORD_TEMPLATE を各paperのMakefileで切り替える
#   template-article.docx … 長文（章節項の4階層・章ごとに改ページ）
#   template-short.docx   … ショートペーパー（2段組・章節の2階層）
# ============================================================
docx: lint $(DIST_DOCX)

$(DIST_DOCX): $(TEX_SOURCES) $(BIB_SOURCES) | $(DIST_DIR)
	uv run python -m drafter.converter.pipeline \
		--input $(MAIN_TEX) \
		$(PANDOC_BIB_FLAGS) \
		--template $(TEMPLATES_WORD_DIR)/$(WORD_TEMPLATE) \
		--defaults $(PANDOC_DEFAULTS) \
		$(PANDOC_RESOURCE_FLAGS) \
		--output $@

# ============================================================
# docx-review: 1段組・行間2行・行番号つき。書き込みながらの校閲用
# 節以下は採番しないので、章単位で通して読むのに向く
# ============================================================
docx-review: lint $(DIST_REVIEW_DOCX)

$(DIST_REVIEW_DOCX): $(TEX_SOURCES) $(BIB_SOURCES) | $(DIST_DIR)
	uv run python -m drafter.converter.pipeline \
		--input $(MAIN_TEX) \
		$(PANDOC_BIB_FLAGS) \
		--template $(TEMPLATES_WORD_DIR)/$(REVIEW_WORD_TEMPLATE) \
		--defaults $(PANDOC_DEFAULTS) \
		$(PANDOC_RESOURCE_FLAGS) \
		--output $@

# ============================================================
# ディレクトリ作成
# ============================================================
$(DIST_DIR):
	mkdir -p $(DIST_DIR)

# ============================================================
# clean
# ============================================================
# latexmk -C は出力先ディレクトリを作り直すので、先に走らせてから削除する。
clean:
	latexmk -C -output-directory=$(DIST_DIR) $(MAIN_TEX) 2>/dev/null || true
	rm -rf $(DIST_DIR)
	@if [ -n "$(AUX_DIR)" ] && [ "$(AUX_DIR)" != "/" ]; then \
		echo "rm -rf $(AUX_DIR)"; rm -rf -- "$(AUX_DIR)"; \
	fi
