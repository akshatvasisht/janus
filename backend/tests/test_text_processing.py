"""
Tests for SentenceBuffer and text tokenization utilities.
"""

import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from backend.services.text_processing import SentenceBuffer, iter_text_tokens


def test_sentence_buffer_emits_on_punctuation_and_flush() -> None:
    buf = SentenceBuffer()

    # Feed a sentence with explicit punctuation
    tokens = list("Hello world!")
    sentences = []
    for tok in tokens:
        s = buf.add_token(tok)
        if s:
            sentences.append(s)

    # After '!' we should have received one sentence and buffer should be empty.
    assert sentences == ["Hello world!"]
    assert buf.flush() is None  # nothing left


def test_sentence_buffer_flushes_without_punctuation() -> None:
    buf = SentenceBuffer()

    for tok in "Hello world":
        s = buf.add_token(tok)
        assert s is None

    # End-of-packet flush should emit the buffered text even without punctuation.
    flushed = buf.flush()
    assert flushed == "Hello world"
    # Second flush should be empty
    assert buf.flush() is None


def test_iter_text_tokens_char_level() -> None:
    text = "Hi."
    tokens = iter_text_tokens(text)
    assert tokens == ["H", "i", "."]

