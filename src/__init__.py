"""Day 8 — RAG Pipeline: VietGo, trợ lý du lịch Việt Nam."""

import sys

# Console Windows mặc định cp1252 -> print tiếng Việt bị UnicodeEncodeError.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
