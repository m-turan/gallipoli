#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Yerel dosyayı FTP sunucusuna yükler."""

from __future__ import annotations

import ftplib
import os
import sys
from pathlib import Path


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"Hata: {name} ortam değişkeni tanımlı değil.", file=sys.stderr)
        sys.exit(1)
    return value


def ensure_remote_dir(ftp: ftplib.FTP, remote_dir: str) -> None:
    parts = [p for p in remote_dir.split("/") if p]
    for part in parts:
        try:
            ftp.cwd(part)
        except ftplib.error_perm:
            ftp.mkd(part)
            ftp.cwd(part)


def upload_file(local_path: Path, remote_filename: str) -> None:
    host = require_env("FTP_HOST")
    user = require_env("FTP_USER")
    password = require_env("FTP_PASSWORD")
    remote_dir = require_env("FTP_REMOTE_DIR")

    if not local_path.is_file():
        print(f"Hata: Dosya bulunamadı: {local_path}", file=sys.stderr)
        sys.exit(1)

    with ftplib.FTP(host, timeout=120) as ftp:
        ftp.login(user, password)
        ftp.set_pasv(True)
        ensure_remote_dir(ftp, remote_dir)

        with local_path.open("rb") as file_handle:
            ftp.storbinary(f"STOR {remote_filename}", file_handle)

    print(f"Yüklendi: {remote_filename} -> {host}{remote_dir}/{remote_filename}")


def main() -> int:
    if len(sys.argv) != 2:
        print("Kullanım: python upload_ftp.py <dosya>", file=sys.stderr)
        return 1

    local_path = Path(sys.argv[1])
    upload_file(local_path, local_path.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
