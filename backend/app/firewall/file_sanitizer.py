"""
Layer 1: Deterministic File Sanitisation
Validates uploads by magic bytes (not extension), strips EXIF metadata.
"""

import io
import logging
from typing import Optional, Tuple

logger = logging.getLogger("jerry.firewall.file_sanitizer")

ALLOWED_MIMES = {"image/jpeg", "image/png"}

try:
    import filetype
    FILETYPE_AVAILABLE = True
except ImportError:
    FILETYPE_AVAILABLE = False
    logger.warning("filetype package not installed — file validation disabled")

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    logger.warning("Pillow package not installed — EXIF stripping disabled")


class FileSanitizer:
    """Validates uploaded files by magic bytes and strips EXIF metadata."""

    def validate_mime(self, data: bytes) -> Tuple[bool, str]:
        """Check magic bytes. Returns (is_valid, detected_mime_or_error)."""
        if not FILETYPE_AVAILABLE:
            return (True, "filetype_unavailable")

        kind = filetype.guess(data)
        if kind is None:
            return (False, "unknown_file_type")

        if kind.mime not in ALLOWED_MIMES:
            logger.warning(f"Blocked file type: {kind.mime}")
            return (False, f"blocked_mime:{kind.mime}")

        return (True, kind.mime)

    def strip_exif(self, image_data: bytes) -> bytes:
        """Strip all EXIF/metadata from image by re-creating pixel data."""
        if not PILLOW_AVAILABLE:
            return image_data

        try:
            image_stream = io.BytesIO(image_data)
            original = Image.open(image_stream)

            # Create new image with only pixel data (strips EXIF, comments, etc.)
            clean = Image.new(original.mode, original.size)
            clean.putdata(list(original.getdata()))

            # Save back to bytes
            clean_stream = io.BytesIO()
            fmt = original.format or "PNG"
            clean.save(clean_stream, format=fmt)
            return clean_stream.getvalue()

        except Exception as e:
            logger.error(f"EXIF stripping failed: {e}")
            return image_data  # Return original if stripping fails

    def sanitize(self, data: bytes, claimed_mime: str = "") -> Tuple[bool, bytes, str]:
        """
        Full pipeline: validate magic bytes + strip metadata.
        Returns (ok, cleaned_data, message).
        """
        # Step 1: Validate magic bytes
        is_valid, detected = self.validate_mime(data)
        if not is_valid:
            return (False, b"", f"File rejected: {detected}")

        # Step 2: Strip EXIF metadata
        if detected in ("image/jpeg", "image/png"):
            cleaned = self.strip_exif(data)
            return (True, cleaned, f"Sanitized {detected}")

        return (True, data, f"Passed: {detected}")
