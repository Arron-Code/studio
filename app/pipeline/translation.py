"""Lokale Übersetzung mit NLLB-200 (unterstützt Deutsch, Englisch und Tigrinya)."""
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

from app.config import DEVICE, NLLB_LANG_CODES, TRANSLATION_MODEL_NAME

_model = None
_tokenizer = None


def _load_model():
    global _model, _tokenizer
    if _model is None:
        _tokenizer = AutoTokenizer.from_pretrained(TRANSLATION_MODEL_NAME)
        _model = AutoModelForSeq2SeqLM.from_pretrained(TRANSLATION_MODEL_NAME).to(DEVICE)
    return _model, _tokenizer


def translate(text: str, source_lang: str, target_lang: str) -> str:
    """Übersetzt Text zwischen 'de', 'en', 'ti' (Tigrinya) mittels NLLB-200."""
    if source_lang == target_lang:
        return text
    if source_lang not in NLLB_LANG_CODES or target_lang not in NLLB_LANG_CODES:
        raise ValueError(
            f"Nicht unterstützte Sprache. Verfügbar: {list(NLLB_LANG_CODES.keys())}"
        )

    model, tokenizer = _load_model()
    tokenizer.src_lang = NLLB_LANG_CODES[source_lang]

    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512).to(DEVICE)
    target_token_id = tokenizer.convert_tokens_to_ids(NLLB_LANG_CODES[target_lang])

    generated = model.generate(
        **inputs,
        forced_bos_token_id=target_token_id,
        max_length=512,
    )
    return tokenizer.batch_decode(generated, skip_special_tokens=True)[0]


def translate_segments(
    segments: list[dict], source_lang: str, target_lang: str
) -> list[dict]:
    """Übersetzt eine Liste von Transkript-Segmenten und behält Zeitstempel bei."""
    translated = []
    for seg in segments:
        translated.append(
            {
                "start": seg["start"],
                "end": seg["end"],
                "text": translate(seg["text"], source_lang, target_lang),
            }
        )
    return translated
