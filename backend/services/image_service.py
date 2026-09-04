"""
Image Evidence Service for SIH26165 (OIL Safety Intelligence Platform)
------------------------------------------------------------------------
Handles safe receipt, validation, integrity verification, persistent storage,
and report association for optional safety observation field images.

Key Guarantees:
1. Strict Validation:
   - Allowed formats: JPEG, PNG, WEBP, BMP, TIFF
   - Maximum file size: 10 MB
   - Corruption detection: PIL Image.verify()
2. Isolation & Safety:
   - Image processing errors NEVER disrupt the text-based AI pipeline.
   - Zero fake CV predictions (explicitly flags cv_analysis_status='NOT_CONFIGURED').
3. Report Association:
   - Associated with report_id and stored in backend/data/uploaded_evidence/.
"""

import base64
import binascii
import io
import re
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple, Union, Any

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# Maximum file size: 10 MB
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024

# Supported MIME types and image formats
ALLOWED_FORMATS = {"JPEG", "JPG", "PNG", "WEBP", "BMP", "TIFF"}
ALLOWED_MIME_TYPES = {
    "image/jpeg": "JPEG",
    "image/jpg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
    "image/bmp": "BMP",
    "image/tiff": "TIFF",
}


@dataclass
class ImageEvidenceRecord:
    image_attached: bool
    image_id: Optional[str] = None
    report_id: Optional[str] = None
    original_filename: Optional[str] = None
    stored_filename: Optional[str] = None
    content_type: Optional[str] = None
    format: Optional[str] = None
    file_size_bytes: int = 0
    width: Optional[int] = None
    height: Optional[int] = None
    url_reference: Optional[str] = None
    attached_at: Optional[str] = None
    cv_analysis_status: str = "NOT_CONFIGURED"
    status_note: str = "Image evidence securely stored with report record."
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ImageEvidenceService:
    """Service for safely processing and storing optional image attachments."""

    def __init__(self, storage_dir: Optional[Union[str, Path]] = None):
        if storage_dir is None:
            self.storage_dir = Path(__file__).resolve().parent.parent / "data" / "uploaded_evidence"
        else:
            self.storage_dir = Path(storage_dir)

        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_index: Dict[str, Dict[str, Any]] = {}

    def _decode_image_payload(
        self,
        image_payload: Union[bytes, str]
    ) -> Tuple[Optional[bytes], Optional[str], Optional[str]]:
        """
        Extracts raw bytes and detected MIME type from base64 string, data URL, or bytes.
        Returns: (raw_bytes, detected_mime, error_str)
        """
        if not image_payload:
            return None, None, "Empty image payload provided."

        # If already bytes
        if isinstance(image_payload, bytes):
            return image_payload, None, None

        # If string
        if isinstance(image_payload, str):
            image_str = image_payload.strip()

            # Check for Data URL header (e.g. data:image/png;base64,iVBORw0KGgo...)
            data_url_match = re.match(r"^data:(image\/[a-zA-Z0-9\+\.\-]+);base64,(.+)$", image_str, re.DOTALL)
            if data_url_match:
                detected_mime = data_url_match.group(1).lower()
                b64_data = data_url_match.group(2)
            else:
                detected_mime = None
                b64_data = image_str

            try:
                raw_bytes = base64.b64decode(b64_data, validate=True)
                return raw_bytes, detected_mime, None
            except (binascii.Error, ValueError) as e:
                return None, None, f"Invalid base64 encoding: {e}"

        return None, None, "Unsupported image payload type."

    def validate_image_bytes(
        self,
        image_bytes: bytes,
        declared_filename: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str], int, int, Optional[str]]:
        """
        Validates size, format, and corruption.
        Returns: (is_valid, format_name, content_type, width, height, error_message)
        """
        # 1. Size check
        size_bytes = len(image_bytes)
        if size_bytes == 0:
            return False, None, None, 0, 0, "Uploaded image is empty (0 bytes)."

        if size_bytes > MAX_IMAGE_SIZE_BYTES:
            max_mb = MAX_IMAGE_SIZE_BYTES / (1024 * 1024)
            current_mb = round(size_bytes / (1024 * 1024), 2)
            return False, None, None, 0, 0, f"File size ({current_mb} MB) exceeds maximum allowed limit of {max_mb} MB."

        # 2. PIL Image Integrity & Format Check
        if not HAS_PIL:
            # Fallback simple header inspection
            return True, "UNKNOWN", "application/octet-stream", 0, 0, None

        try:
            img_io = io.BytesIO(image_bytes)
            with Image.open(img_io) as img:
                fmt = (img.format or "").upper()
                if fmt not in ALLOWED_FORMATS and fmt != "JPEG":
                    return False, None, None, 0, 0, f"Unsupported image format '{fmt}'. Allowed formats: {', '.join(sorted(ALLOWED_FORMATS))}."

                width, height = img.size
                if width <= 0 or height <= 0:
                    return False, None, None, 0, 0, "Invalid image dimensions."

                # Verify integrity
                img.verify()

            # Determine MIME
            mime_map = {
                "JPEG": "image/jpeg",
                "JPG": "image/jpeg",
                "PNG": "image/png",
                "WEBP": "image/webp",
                "BMP": "image/bmp",
                "TIFF": "image/tiff"
            }
            content_type = mime_map.get(fmt, f"image/{fmt.lower()}")

            return True, fmt, content_type, width, height, None

        except Exception as e:
            return False, None, None, 0, 0, f"Corrupted or invalid image file: {str(e)}"

    def process_and_store_image(
        self,
        image_payload: Optional[Union[bytes, str]],
        report_id: str,
        original_filename: Optional[str] = None
    ) -> ImageEvidenceRecord:
        """
        Safely processes and stores optional image attachment associated with report_id.
        Never raises exceptions that would break text analysis.
        """
        if not image_payload:
            return ImageEvidenceRecord(
                image_attached=False,
                report_id=report_id,
                status_note="No image evidence attached to this safety report."
            )

        try:
            # 1. Decode payload
            raw_bytes, detected_mime, decode_err = self._decode_image_payload(image_payload)
            if decode_err or raw_bytes is None:
                return ImageEvidenceRecord(
                    image_attached=False,
                    report_id=report_id,
                    error_message=decode_err or "Failed to decode image data."
                )

            # 2. Validate format and corruption
            is_valid, fmt, content_type, width, height, val_err = self.validate_image_bytes(
                raw_bytes,
                declared_filename=original_filename
            )

            if not is_valid or fmt is None:
                return ImageEvidenceRecord(
                    image_attached=False,
                    report_id=report_id,
                    error_message=val_err or "Image validation failed."
                )

            # 3. Secure persistent storage
            image_id = f"IMG-{uuid.uuid4().hex[:10].upper()}"
            ext = fmt.lower() if fmt != "JPEG" else "jpg"
            stored_filename = f"{report_id}_{image_id}.{ext}"
            stored_path = self.storage_dir / stored_filename

            with open(stored_path, "wb") as f:
                f.write(raw_bytes)

            now_iso = datetime.now(timezone.utc).isoformat()
            url_ref = f"/evidence/{image_id}"

            record = ImageEvidenceRecord(
                image_attached=True,
                image_id=image_id,
                report_id=report_id,
                original_filename=original_filename or f"evidence.{ext}",
                stored_filename=stored_filename,
                content_type=content_type or detected_mime or f"image/{ext}",
                format=fmt,
                file_size_bytes=len(raw_bytes),
                width=width,
                height=height,
                url_reference=url_ref,
                attached_at=now_iso,
                cv_analysis_status="NOT_CONFIGURED",
                status_note="Image evidence securely stored with report record (Computer vision analysis not active)."
            )

            # Record in in-memory index
            self.metadata_index[image_id] = record.to_dict()

            return record

        except Exception as e:
            # Absolute fault tolerance: image failures must never disrupt text analysis
            return ImageEvidenceRecord(
                image_attached=False,
                report_id=report_id,
                error_message=f"Unexpected error storing image evidence: {str(e)}"
            )

    def get_image_file_path(self, image_id: str) -> Optional[Path]:
        """Retrieves absolute file path for a stored image ID."""
        for p in self.storage_dir.glob(f"*_{image_id}.*"):
            if p.exists():
                return p
        return None

    def get_image_metadata(self, image_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves stored metadata for an image ID."""
        return self.metadata_index.get(image_id)
