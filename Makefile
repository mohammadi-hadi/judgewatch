.PHONY: install lint test audit report site serve build

install:
	python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"

lint:
	.venv/bin/ruff check .

test:
	.venv/bin/python -m pytest -q

# Usage: make audit JUDGES=anthropic:claude-haiku-4-5 [MONTH=2026-09]
audit:
	.venv/bin/python -m judgewatch run $(if $(JUDGES),--judges $(JUDGES)) $(if $(MONTH),--month $(MONTH))
	.venv/bin/python -m judgewatch report
	.venv/bin/python -m judgewatch site

report:
	.venv/bin/python -m judgewatch report
	.venv/bin/python -m judgewatch site

site:
	.venv/bin/python -m judgewatch site

serve:
	.venv/bin/python -m http.server 8765 -d docs

# Build sdist + wheel from a clean `git archive` export, so only committed
# files can reach a distribution, then audit the artifacts.
build:
	rm -rf dist .build-src
	mkdir .build-src
	git archive HEAD | tar -x -C .build-src
	cd .build-src && ../.venv/bin/python -m build --outdir ../dist
	rm -rf .build-src
	@if tar -tzf dist/*.tar.gz | grep -qiE 'claude|gitignore'; then \
		echo "TAINTED SDIST"; exit 1; fi
	@if unzip -l dist/*.whl | grep -qiE 'claude|gitignore'; then \
		echo "TAINTED WHEEL"; exit 1; fi
	@echo "artifacts clean:" && ls dist
