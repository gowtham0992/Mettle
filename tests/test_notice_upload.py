from io import BytesIO

import pytest
from pypdf import PdfWriter

from mettle.notice_upload import NoticeUploadError, extract_notice_text
from mettle.notice_upload import extract_notice_ocr
from mettle.photo_upload import PhotoUploadError
from PIL import Image
from unittest.mock import Mock


def test_ocr_normalizes_photo_and_returns_only_detected_lines():
    stream = BytesIO()
    Image.new("RGB", (100, 100), "white").save(stream, format="PNG")
    client = Mock()
    client.detect_document_text.return_value = {"Blocks": [
        {"BlockType": "LINE", "Text": "Permit TEST-1: repair panel clearance"},
        {"BlockType": "WORD", "Text": "duplicate"},
    ]}
    assert extract_notice_ocr(stream.getvalue(), filename="notice.png", client=client) == "Permit TEST-1: repair panel clearance"
    assert client.detect_document_text.call_args.kwargs["Document"]["Bytes"].startswith(b"\xff\xd8")


def test_ocr_rejects_invalid_images_before_aws():
    client = Mock()
    with pytest.raises(PhotoUploadError):
        extract_notice_ocr(b"not a photo", filename="notice.png", client=client)
    client.detect_document_text.assert_not_called()


def test_ocr_rejects_multiple_pages_before_aws():
    stream = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.add_blank_page(width=200, height=200)
    writer.write(stream)
    client = Mock()
    with pytest.raises(NoticeUploadError):
        extract_notice_ocr(stream.getvalue(), filename="notice.pdf", client=client)
    client.detect_document_text.assert_not_called()


def test_accepts_utf8_text_report() -> None:
    assert extract_notice_text(b"Permit: TEST-1\n1. Repair panel clearance", filename="notice.txt") == (
        "Permit: TEST-1\n1. Repair panel clearance"
    )


def test_report_limit_fits_encoded_lambda_request():
    with pytest.raises(NoticeUploadError, match="3.5 MB"):
        extract_notice_text(b"Report: repair framing.\n" + b" " * 3_500_000, filename="report.txt")


def test_report_at_limit_is_accepted():
    content = b"Report: repair framing.\n"
    raw = content + b" " * (3_500_000 - len(content))
    assert extract_notice_text(raw, filename="report.txt") == content.decode().strip()


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
