from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError
from mettle.photo_upload import normalize_photo


MAX_NOTICE_BYTES = 5_000_000
MAX_NOTICE_PAGES = 25
MAX_NOTICE_TEXT = 100_000
MAX_OCR_BYTES = 3_500_000  # Fits the Lambda request limit after base64 encoding.


class NoticeUploadError(ValueError):
    """Raised when a notice cannot be safely converted to bounded text."""


def extract_notice_ocr(raw: bytes, *, filename: str, client) -> str:
    """One-page OCR; caller must enforce authentication and explicit enablement."""
    if not raw or len(raw) > MAX_OCR_BYTES:
        raise NoticeUploadError("Choose a non-empty photo or scan no larger than 3.5 MB.")
    if raw.startswith(b"%PDF-"):
        try:
            reader = PdfReader(BytesIO(raw), strict=True)
            if reader.is_encrypted or len(reader.pages) != 1:
                raise NoticeUploadError("For scanned PDFs, upload one unencrypted page at a time.")
        except (PdfReadError, ValueError, TypeError) as exc:
            raise NoticeUploadError("Choose a readable, single-page scanned PDF.") from exc
        document = raw
    else:
        document = normalize_photo(raw)
    result = client.detect_document_text(Document={"Bytes": document})
    lines = [block["Text"] for block in result.get("Blocks", [])
             if block.get("BlockType") == "LINE" and isinstance(block.get("Text"), str)]
    text = "\n".join(lines).strip()
    if len(text) < 20 or len(text) > MAX_NOTICE_TEXT:
        raise NoticeUploadError("The photo did not produce a usable report. Try a clearer image or paste the comments.")
    return text


def extract_notice_text(raw: bytes, *, filename: str) -> str:
    if not raw:
        raise NoticeUploadError("Choose a non-empty PDF or text file.")
    if len(raw) > MAX_NOTICE_BYTES:
        raise NoticeUploadError("The report must be 5 MB or smaller.")

    lowered = filename.lower()
    if raw.startswith(b"%PDF-"):
        if not lowered.endswith(".pdf"):
            raise NoticeUploadError("The file contents are PDF, but the filename is not .pdf.")
        try:
            reader = PdfReader(BytesIO(raw), strict=True)
            if reader.is_encrypted:
                raise NoticeUploadError("Password-protected PDF reports are not supported.")
            if len(reader.pages) > MAX_NOTICE_PAGES:
                raise NoticeUploadError("The report must contain 25 pages or fewer.")
            text = "\n\n".join((page.extract_text() or "").strip() for page in reader.pages)
        except NoticeUploadError:
            raise
        except (PdfReadError, ValueError, TypeError) as exc:
            raise NoticeUploadError("Mettle could not read this PDF. Try another copy or paste the inspection comments.") from exc
        if len(text.strip()) < 20:
            raise NoticeUploadError("This PDF appears to be a scan without selectable text. Paste the inspection comments instead.")
    elif lowered.endswith(".txt") and b"\x00" not in raw:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise NoticeUploadError("Text reports must use UTF-8 encoding.") from exc
    else:
        raise NoticeUploadError("Choose a PDF or .txt report.")

    normalized = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if len(normalized) > MAX_NOTICE_TEXT:
        raise NoticeUploadError("The extracted report text is too long. Keep only the inspection header and correction comments.")
    return normalized
