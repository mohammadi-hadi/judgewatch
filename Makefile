.PHONY: install lint test audit report site serve

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
