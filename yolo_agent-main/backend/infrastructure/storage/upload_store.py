from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

from fastapi import UploadFile


class UploadStore:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir

    def save(self, upload_file: UploadFile, request_id: str) -> Path:
        date_segment = datetime.now(UTC).strftime("%Y-%m-%d")
        target_dir = self.base_dir / date_segment / request_id
        target_dir.mkdir(parents=True, exist_ok=True)

        raw_name = Path(upload_file.filename or "upload.bin").name
        safe_name = raw_name.strip() or "upload.bin"
        target = target_dir / safe_name

        if target.exists():
            parsed = Path(safe_name)
            stem = parsed.stem or "upload"
            suffix = parsed.suffix
            index = 1
            while True:
                candidate = target_dir / f"{stem}-{index}{suffix}"
                if not candidate.exists():
                    target = candidate
                    break
                index += 1

        with target.open("wb") as handle:
            shutil.copyfileobj(upload_file.file, handle)
        upload_file.file.seek(0)
        return target

    def cleanup(self, file_path: Path) -> None:
        if file_path.exists():
            file_path.unlink()
        current = file_path.parent
        while current != self.base_dir and current.exists():
            if any(current.iterdir()):
                break
            current.rmdir()
            current = current.parent
