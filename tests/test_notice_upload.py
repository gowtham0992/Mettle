from io import BytesIO

import pytest
from pypdf import PdfWriter

from mettle.notice_upload import NoticeUploadError, extract_notice_text


def test_accepts_utf8_text_report() -> None:
    assert extract_notice_text(b"Permit: TEST-1\n1. Repair panel clearance", filename="notice.txt") == (
        "Permit: TEST-1\n1. Repair panel clearance"
    )


def test_rejects_disguised_and_binary_files() -> None:
    with pytest.raises(NoticeUploadError, match="PDF or .txt"):
        extract_notice_text(b"not an image", filename="notice.jpg")
    with pytest.raises(NoticeUploadError, match="PDF or .txt"):
        extract_notice_text(b"hello\x00world", filename="notice.txt")


def test_rejects_pdf_without_selectable_text() -> None:
    stream = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.write(stream)
    with pytest.raises(NoticeUploadError, match="scan without selectable text"):
        extract_notice_text(stream.getvalue(), filename="notice.pdf")
