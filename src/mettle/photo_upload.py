from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError


MAX_UPLOAD_BYTES = 5_000_000
MAX_IMAGE_PIXELS = 20_000_000
MAX_IMAGE_EDGE = 4096


class PhotoUploadError(ValueError):
    """Raised when an uploaded photo cannot cross Mettle's trust boundary."""


def normalize_photo(raw: bytes) -> bytes:
    """Validate and re-encode a JPEG/PNG upload as metadata-free JPEG bytes."""
    if not raw:
        raise PhotoUploadError("photo is empty")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise PhotoUploadError("photo exceeds the 5 MB upload limit")

    Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
    try:
        with Image.open(BytesIO(raw)) as opened:
            if opened.format not in {"JPEG", "PNG"}:
                raise PhotoUploadError("photo must be a JPEG or PNG image")
            if getattr(opened, "n_frames", 1) != 1:
                raise PhotoUploadError("animated images are not supported")
            opened.verify()
        with Image.open(BytesIO(raw)) as opened:
            photo = ImageOps.exif_transpose(opened)
            photo.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE))
            if photo.mode not in {"RGB", "L"}:
                background = Image.new("RGB", photo.size, "white")
                if "A" in photo.getbands():
                    background.paste(photo, mask=photo.getchannel("A"))
                else:
                    background.paste(photo)
                photo = background
            elif photo.mode == "L":
                photo = photo.convert("RGB")
            output = BytesIO()
            photo.save(output, format="JPEG", quality=88, optimize=True)
    except PhotoUploadError:
        raise
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError) as exc:
        raise PhotoUploadError("photo is not a valid, safe JPEG or PNG image") from exc

    normalized = output.getvalue()
    if not normalized or len(normalized) > MAX_UPLOAD_BYTES:
        raise PhotoUploadError("normalized photo exceeds the 5 MB upload limit")
    return normalized
