import json
from pathlib import Path

import pytest

from judgewatch.__main__ import main


def test_cli_report_then_site(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    main(["report"])
    payload = json.loads(Path("data/latest.json").read_text())
    assert payload["run"] is None

    main(["site"])
    assert Path("docs/index.html").exists()
    assert Path("docs/data.json").exists()


def test_cli_run_without_judges_exits(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("judges.yaml").write_text("judges: []\n")
    with pytest.raises(SystemExit):
        main(["run"])
