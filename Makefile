# ============================================================
# drafter - Root Makefile
# 全文書の一括操作
# ============================================================

PAPERS_DIR := papers
PAPERS     := $(wildcard $(PAPERS_DIR)/*)

.PHONY: all review-all lint-all pdf-all docx-all clean-all

# --- デフォルト: 全文書のpdf+docx ---
all: pdf-all docx-all

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

clean-all:
	@for paper in $(PAPERS); do \
		echo "==== clean: $$paper ===="; \
		$(MAKE) -C $$paper clean; \
	done
