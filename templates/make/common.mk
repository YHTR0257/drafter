# ============================================================
# drafter - common.mk
# 各 papers/*/Makefile から include して使用する共通ルール
# ============================================================

# --- デフォルト値（各paperのMakefileで上書き可能） ---
MAIN_TEX     ?= main.tex
BIB_DIR      ?= ../bib
WORD_TEMPLATE ?= template-a.docx
RULES_DIR    ?= ../../templates/rules
PANDOC_DEFAULTS ?= ../../templates/pandoc/defaults.yaml
TEMPLATES_WORD_DIR ?= ../../templates/word

# --- 導出変数 ---
MAIN_BASE    := $(basename $(MAIN_TEX))
DIST_DIR     := dist
DIST_PDF     := $(DIST_DIR)/$(MAIN_BASE).pdf
DIST_DOCX    := $(DIST_DIR)/$(MAIN_BASE).docx
REVIEW_REPORT := $(DIST_DIR)/review-report.md

# --- bib自動検出 ---
BIB_SOURCES  := $(wildcard $(BIB_DIR)/*.bib)
PANDOC_BIB_FLAGS := $(foreach bib,$(BIB_SOURCES),--bibliography=$(bib))

# --- LaTeX関連 ---
TEX_SOURCES  := $(wildcard *.tex)
FIG_SOURCES  := $(wildcard figures/*)

# --- latexmkにbibパスを通す ---
export BIBINPUTS := $(BIB_DIR):

# --- phony ---
.PHONY: all review lint pdf docx clean

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
# ============================================================
docx: lint $(DIST_DOCX)

$(DIST_DOCX): $(TEX_SOURCES) $(BIB_SOURCES) | $(DIST_DIR)
	uv run python -m drafter.converter.pipeline \
		--input $(MAIN_TEX) \
		$(PANDOC_BIB_FLAGS) \
		--template $(TEMPLATES_WORD_DIR)/$(WORD_TEMPLATE) \
		--defaults $(PANDOC_DEFAULTS) \
		--output $@

# ============================================================
# ディレクトリ作成
# ============================================================
$(DIST_DIR):
	mkdir -p $(DIST_DIR)

# ============================================================
# clean
# ============================================================
clean:
	rm -rf $(DIST_DIR)
	latexmk -C -output-directory=$(DIST_DIR) $(MAIN_TEX) 2>/dev/null || true
