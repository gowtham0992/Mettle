from io import BytesIO

import pytest
from PIL import Image

from mettle.photo_upload import MAX_UPLOAD_BYTES, PhotoUploadError, normalize_photo


def _png(*, size: tuple[int, int] = (40, 30)) -> bytes:
    output = BytesIO()
    Image.new("RGBA", size, (242, 103, 47, 128)).save(output, format="PNG")
    return output.getvalue()


def test_normalize_photo_strips_input_format_and_returns_safe_jpeg() -> None:
    normalized = normalize_photo(_png())

    assert normalized.startswith(b"\xff\xd8\xff")
    with Image.open(BytesIO(normalized)) as image:
        assert image.format == "JPEG"
        assert image.mode == "RGB"
        assert image.size == (40, 30)


@pytest.mark.parametrize("raw", [b"", b"not an image", b"<svg></svg>"])
def test_normalize_photo_rejects_invalid_content(raw: bytes) -> None:
    with pytest.raises(PhotoUploadError):
        normalize_photo(raw)


def test_normalize_photo_rejects_oversized_body_before_decoding() -> None:
    with pytest.raises(PhotoUploadError, match="5 MB"):
        normalize_photo(b"x" * (MAX_UPLOAD_BYTES + 1))
