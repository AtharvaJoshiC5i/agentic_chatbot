"""HTML document render previews."""

from pathlib import Path

from app.services.document_render import render_email_html

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_render_email_html_includes_subject_and_body() -> None:
    sample = next(
        PROJECT_ROOT.glob("data/unstructured/communications/*.eml"),
        None,
    )
    if sample is None:
        return
    html_out = render_email_html(sample.read_bytes(), sample.name)
    assert "<html" in html_out.lower()
    assert "From" in html_out
