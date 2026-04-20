"""
抽象解析器基类
"""
from abc import ABC, abstractmethod
from .models import ParsedBook


class BaseParser(ABC):
    @abstractmethod
    def can_handle(self, file_path: str) -> bool:
        """判断是否能处理该文件格式"""
        ...

    @abstractmethod
    def parse(self, file_path: str) -> ParsedBook:
        """解析文件，返回结构化书籍对象"""
        ...
