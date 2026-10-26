"""Full-document HTML rendering for in-app preview (email + Word fallback)."""

from __future__ import annotations

import base64
import email
import html
import re
from email import policy as email_policy
from pathlib import Path

import mammoth
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.services.document_preview import get_document_metadata, resolve_document_path

_PREVIEW_SHELL = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
      font-size: 15px;
      line-height: 1.55;
      color: #18181b;
      background: #f4f4f5;
    }}
    .preview-page {{
      max-width: 920px;
      margin: 0 auto;
      padding: 24px 20px 48px;
    }}
    .preview-card {{
      background: #fff;
      border: 1px solid #e4e4e7;
      border-radius: 8px;
      box-shadow: 0 1px 3px rgb(0 0 0 / 0.06);
      overflow: hidden;
    }}
    .email-headers {{
      padding: 20px 24px;
      border-bottom: 1px solid #e4e4e7;
      background: #fafafa;
    }}
    .email-headers h1 {{
      margin: 0 0 12px;
      font-size: 1.125rem;
      font-weight: 600;
      line-height: 1.35;
    }}
    .email-headers dl {{
      margin: 0;
      font-size: 13px;
      color: #52525b;
    }}
    .email-headers dt {{
      display: inline;
      font-weight: 600;
      color: #71717a;
    }}
    .email-headers dd {{
      display: inline;
      margin: 0 16px 0 4px;
    }}
    .email-body, .docx-body {{
      padding: 28px 32px 36px;
    }}
    .email-body pre {{
      white-space: pre-wrap;
      font-family: inherit;
      margin: 0;
    }}
    .docx-body img {{ max-width: 100%; height: auto; }}
    .docx-body table {{ border-collapse: collapse; max-width: 100%; }}
    .docx-body td, .docx-body th {{
      border: 1px solid #d4d4d8;
      padding: 6px 10px;
      vertical-align: top;
    }}
  </style>
</head>
<body>
  <div class="preview-page">
    <div class="preview-card">
      {inner}
    </div>
  </div>
</body>
</html>
"""


def _strip_scripts(html_fragment: str) -> str:
    return re.sub(r"<script\b[^>]*>[\s\S]*?</script>", "", html_fragment, flags=re.IGNORECASE)


def _collect_cid_map(message: email.message.Message) -> dict[str, str]:
    cid_map: dict[str, str] = {}
    for part in message.walk():
        if part.get_content_maintype() != "image":
            continue
        cid = part.get("Content-ID")
        if not cid:
            continue
        cid_key = cid.strip().strip("<>")
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        mime = part.get_content_type() or "image/png"
        b64 = base64.b64encode(payload).decode("ascii")
        cid_map[cid_key] = f"data:{mime};base64,{b64}"
    return cid_map


def _replace_cid_urls(body_html: str, cid_map: dict[str, str]) -> str:
    if not cid_map:
        return body_html
    for cid, data_url in cid_map.items():
        body_html = body_html.replace(f"cid:{cid}", data_url)
        body_html = body_html.replace(f"CID:{cid}", data_url)
    return body_html


def _extract_email_bodies(message: email.message.Message) -> tuple[str | None, str | None]:
    html_body: str | None = None
    text_body: str | None = None
    for part in message.walk():
        if part.get_content_disposition() == "attachment":
            continue
        ctype = part.get_content_type()
        if ctype == "text/html" and html_body is None:
            try:
                html_body = part.get_content()
            except Exception:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    html_body = payload.decode(charset, errors="replace")
        elif ctype == "text/plain" and text_body is None:
            try:
                text_body = part.get_content()
            except Exception:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    text_body = payload.decode(charset, errors="replace")
    if html_body is None and not message.is_multipart():
        if message.get_content_type() == "text/html":
            html_body = message.get_content()
        elif message.get_content_type() == "text/plain":
            text_body = message.get_content()
    return html_body, text_body


def render_email_html(raw: bytes, title: str) -> str:
    message = email.message_from_bytes(raw, policy=email_policy.default)
    subject = message.get("Subject", "") or "(No subject)"
    from_hdr = message.get("From", "")
    to_hdr = message.get("To", "")
    date_hdr = message.get("Date", "")
    cid_map = _collect_cid_map(message)
    html_body, text_body = _extract_email_bodies(message)

    header_block = f"""
    <div class="email-headers">
      <h1>{html.escape(str(subject))}</h1>
      <dl>
        <dt>From</dt><dd>{html.escape(str(from_hdr))}</dd>
        <dt>To</dt><dd>{html.escape(str(to_hdr))}</dd>
        <dt>Date</dt><dd>{html.escape(str(date_hdr))}</dd>
      </dl>
    </div>
    """

    if html_body and html_body.strip():
        body = _strip_scripts(_replace_cid_urls(html_body.strip(), cid_map))
        if body.lstrip().lower().startswith("<!doctype") or body.lstrip().lower().startswith("<html"):
            return body
        inner = header_block + f'<div class="email-body">{body}</div>'
    elif text_body and text_body.strip():
        inner = header_block + (
            f'<div class="email-body"><pre>{html.escape(text_body.strip())}</pre></div>'
        )
    else:
        inner = header_block + '<div class="email-body"><p><em>No message body.</em></p></div>'

    return _PREVIEW_SHELL.format(title=html.escape(title), inner=inner)


def render_docx_html(path: Path, title: str) -> str:
    with path.open("rb") as docx_file:
        result = mammoth.convert_to_html(docx_file)
    body_html = _strip_scripts(result.value)
    inner = f'<div class="docx-body">{body_html}</div>'
    return _PREVIEW_SHELL.format(title=html.escape(title), inner=inner)


def build_rendered_html_preview(session: Session, document_id: int) -> str:
    row = get_document_metadata(session, document_id)
    path = resolve_document_path(row)
    suffix = path.suffix.lower()
    title = row.filename

    if suffix == ".eml":
        return render_email_html(path.read_bytes(), title)
    if suffix == ".docx":
        return render_docx_html(path, title)
    if suffix == ".txt":
        text = html.escape(path.read_text(encoding="utf-8"))
        inner = f'<div class="docx-body"><pre>{text}</pre></div>'
        return _PREVIEW_SHELL.format(title=html.escape(title), inner=inner)

    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail=f"HTML render not available for {suffix}; use file download or PDF preview.",
    )
