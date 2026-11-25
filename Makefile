# Host entry points. All paper tools run through uv inside Docker.
.DEFAULT_GOAL := help
DOCKER_COMPOSE ?= docker compose
export HOST_UID ?= $(shell id -u)
export HOST_GID ?= $(shell id -g)
PAPER ?=
MAIN_TEX ?= main.tex
WORD_TEMPLATE_DIR ?= /workspace/templates/msword
FORMAT ?= article
SKIP_LINT ?= 0
WORD_TEMPLATE ?= template-$(FORMAT).docx

.PHONY: help build up down bash build-pdf build-docx lint review \
        word-templates check-paper

help:
	@echo 'make build | up | down | bash'
	@echo 'make build-pdf | build-docx | lint | review PAPER=<name> [FORMAT=article|short|review]'
	@echo 'make word-templates'

build:
	$(DOCKER_COMPOSE) build

up:
	$(DOCKER_COMPOSE) up -d

down:
	$(DOCKER_COMPOSE) down

bash:
	$(DOCKER_COMPOSE) run --rm drafter bash

check-paper:
	@test -n "$(PAPER)" || { echo 'Specify PAPER=<directory name>' >&2; exit 1; }

build-pdf build-docx lint review: check-paper
	@case "$(FORMAT)" in article|short|review) ;; \
		*) echo 'FORMAT must be article, short or review' >&2; exit 1 ;; esac
	$(DOCKER_COMPOSE) run --rm \
		-e SKIP_LINT="$(SKIP_LINT)" \
		-e WORD_TEMPLATE_DIR="$(WORD_TEMPLATE_DIR)" \
		-e WORD_TEMPLATE="$(WORD_TEMPLATE)" \
		drafter bash /workspace/scripts/build-paper.sh \
		"$(patsubst build-%,%,$@)" "$(PAPER)" "$(MAIN_TEX)"

word-templates:
	$(DOCKER_COMPOSE) run --rm drafter uv run python \
		-m drafter.converter.word_template_pipeline --output-dir "$(WORD_TEMPLATE_DIR)"
