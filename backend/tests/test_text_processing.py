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


def test_sentence_buffer_weak_punctuation_ignores_short_length() -> None:
    buf = SentenceBuffer()
    sentences = []
    
    # "Hi, how are you?" -> The comma shouldn't split it because len("Hi,") < 30.
    for tok in list("Hi, how are you?"):
        s = buf.add_token(tok)
        if s:
            sentences.append(s)
            
    # The whole sentence is buffered, then flushed at the '?', so one item.
    assert len(sentences) == 1
    assert sentences[0] == "Hi, how are you?"


def test_sentence_buffer_weak_punctuation_splits_long_length() -> None:
    buf = SentenceBuffer()
    sentences = []
    
    # 36 characters before the comma: "This is a very long text before the,"
    text = "This is a very long text before the, and then more."
    for tok in list(text):
        s = buf.add_token(tok)
        if s:
            sentences.append(s)
            
    # And then we flush the rest
    flushed = buf.flush()
    if flushed:
        sentences.append(flushed)
        
    assert len(sentences) == 2
    assert sentences[0] == "This is a very long text before the,"
    assert sentences[1] == "and then more."

