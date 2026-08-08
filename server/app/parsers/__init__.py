"""Package init."""
from app.parsers.excel import parse_excel
from app.parsers.markdown import parse_markdown
from app.parsers.pdf import parse_pdf
from app.parsers.word import parse_word

__all__ = ["parse_excel", "parse_word", "parse_pdf", "parse_markdown"]