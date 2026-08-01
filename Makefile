# ============================================================
# drafter - Root Makefile
# 全文書の一括操作
# ============================================================

PAPERS_DIR := papers
# Makefileを持つディレクトリのみ対象（papers/bib, papers/dist などを除外）
PAPERS     := $(patsubst %/Makefile,%,$(wildcard $(PAPERS_DIR)/*/Makefile))
WORD_TEMPLATE_DIR := templates/msword

.PHONY: all review-all lint-all pdf-all docx-all docx-review-all word-templates clean-all

# --- デフォルト: 全文書のpdf+docx ---
all: pdf-all docx-all

# --- Wordテンプレート生成 ---
# templates/msword/ はgitignore対象のため、クローン直後はこれで生成する
word-templates:
	uv run python -m drafter.converter.word_template_pipeline \
		--output-dir $(WORD_TEMPLATE_DIR)

# --- 一括ターゲット ---
review-all:
	@for paper in $(PAPERS); do \
		echo "==== review: $$paper ===="; \
		$(MAKE) -C $$paper review || exit 1; \
	done

lint-all:
	@for paper in $(PAPERS); do \
		echo "==== lint: $$paper ===="; \
		$(MAKE) -C $$paper lint || exit 1; \
	done

pdf-all:
	@for paper in $(PAPERS); do \
		echo "==== pdf: $$paper ===="; \
		$(MAKE) -C $$paper pdf || exit 1; \
	done

docx-all:
	@for paper in $(PAPERS); do \
		echo "==== docx: $$paper ===="; \
		$(MAKE) -C $$paper docx || exit 1; \
	done

docx-review-all:
	@for paper in $(PAPERS); do \
		echo "==== docx-review: $$paper ===="; \
		$(MAKE) -C $$paper docx-review || exit 1; \
	done

clean-all:
	@for paper in $(PAPERS); do \
		echo "==== clean: $$paper ===="; \
		$(MAKE) -C $$paper clean; \
	done
