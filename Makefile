# See the README for more options.

.DEFAULT_GOAL := help

help: ## Show this help
	@echo "Usage: make <target>"
	@echo
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

serve: ## Serve the site locally
	bundle exec jekyll serve --livereload

serve-drafts: ## Serve the site locally, including posts in _drafts/
	bundle exec jekyll serve --livereload --drafts

code: ## Clone or update the code submodules under code/
	git submodule update --init --remote code

.PHONY: help serve serve-drafts code
