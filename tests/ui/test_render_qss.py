from pathlib import Path

from lumi.ui.theme import spacing
from lumi.ui.theme.styles import render_qss


def test_render_qss_substitutes_at_tokens(tmp_path: Path) -> None:
    qss = tmp_path / "widget.qss"
    qss.write_text(
        "#Widget {\n    padding: @SPACE_SM@px;\n}\n",
        encoding="utf-8",
    )

    rendered = render_qss(qss)

    assert rendered == f"#Widget {{\n    padding: {spacing.SPACE_SM}px;\n}}\n"
