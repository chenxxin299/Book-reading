"""
解析器工厂 - 自动选择合适的解析器
"""
from pathlib import Path
from .pdf_parser import PDFParser
from .epub_parser import EPUBParser
from .models import ParsedBook

_PARSERS = [PDFParser(), EPUBParser()]


def parse_book(file_path: str) -> ParsedBook:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    for parser in _PARSERS:
        if parser.can_handle(file_path):
            return parser.parse(file_path)

    raise ValueError(f"不支持的文件格式: {path.suffix}（目前支持 PDF / EPUB）")
