# -*- coding: utf-8 -*-
"""
UTF-8 Encoding Utilities

This module provides utilities to ensure consistent UTF-8 encoding
across the entire application. All file I/O operations should use
the helpers in this module to prevent unicode corruption.

CRITICAL: Always use UTF-8 encoding when:
  - Reading/writing JSON files
  - Reading/writing Vue/JavaScript files
  - Reading/writing PGN files
  - Reading/writing text files
  - Database operations
"""

import io
from typing import Any, Dict, List, Optional
import json as stdlib_json


def ensure_utf8_json_dumps(obj: Any, **kwargs) -> str:
    """
    Safely dump an object to JSON with UTF-8 encoding.

    Args:
        obj: Object to serialize
        **kwargs: Additional arguments for json.dumps()

    Returns:
        UTF-8 encoded JSON string
    """
    kwargs.setdefault('ensure_ascii', False)
    return stdlib_json.dumps(obj, **kwargs)


def ensure_utf8_json_loads(text: str, **kwargs) -> Any:
    """
    Safely load JSON from UTF-8 encoded text.

    Args:
        text: JSON string
        **kwargs: Additional arguments for json.loads()

    Returns:
        Deserialized object
    """
    return stdlib_json.loads(text, **kwargs)


def read_text_utf8(file_path: str) -> str:
    """
    Read a text file with UTF-8 encoding.

    Args:
        file_path: Path to the file

    Returns:
        File contents as string

    Raises:
        UnicodeDecodeError: If file cannot be decoded as UTF-8
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def write_text_utf8(file_path: str, content: str) -> None:
    """
    Write text to a file with UTF-8 encoding.

    Args:
        file_path: Path to the file
        content: Content to write
    """
    with open(file_path, 'w', encoding='utf-8', newline='') as f:
        f.write(content)


def read_json_utf8(file_path: str) -> Any:
    """
    Read a JSON file with UTF-8 encoding.

    Args:
        file_path: Path to the JSON file

    Returns:
        Deserialized JSON object
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return stdlib_json.load(f)


def write_json_utf8(file_path: str, obj: Any, **kwargs) -> None:
    """
    Write an object to a JSON file with UTF-8 encoding.

    Args:
        file_path: Path to the JSON file
        obj: Object to serialize
        **kwargs: Additional arguments for json.dump()
    """
    kwargs.setdefault('ensure_ascii', False)
    kwargs.setdefault('indent', 2)
    with open(file_path, 'w', encoding='utf-8', newline='') as f:
        stdlib_json.dump(obj, f, **kwargs)


def read_pgn_utf8(file_path: str) -> str:
    """
    Read a PGN file with UTF-8 encoding.

    Args:
        file_path: Path to the PGN file

    Returns:
        File contents as string

    Raises:
        UnicodeDecodeError: If file cannot be decoded as UTF-8
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def write_pgn_utf8(file_path: str, content: str) -> None:
    """
    Write content to a PGN file with UTF-8 encoding.

    Args:
        file_path: Path to the PGN file
        content: Content to write
    """
    with open(file_path, 'w', encoding='utf-8', newline='') as f:
        f.write(content)


def decode_bytes_utf8(data: bytes, fallback_encoding: str = 'latin-1') -> str:
    """
    Decode bytes to UTF-8 string with fallback support.

    Tries UTF-8 first, falls back to specified encoding if needed.

    Args:
        data: Bytes to decode
        fallback_encoding: Encoding to use if UTF-8 fails (default: latin-1)

    Returns:
        Decoded string
    """
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        return data.decode(fallback_encoding)


def encode_str_utf8(text: str) -> bytes:
    """
    Encode string to UTF-8 bytes.

    Args:
        text: String to encode

    Returns:
        UTF-8 encoded bytes
    """
    return text.encode('utf-8')

