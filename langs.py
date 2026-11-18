"""
langs.py — Dil listesi ve dil kodu yardımcıları.
"""

from __future__ import annotations

import unicodedata

# (Türkçe ad, kod) — kodlar Google Translate ile uyumludur.
LANGUAGES: list[tuple[str, str]] = [
    ("Otomatik algıla", "auto"),
    ("Türkçe", "tr"),
    ("İngilizce", "en"),
    ("Almanca", "de"),
    ("Fransızca", "fr"),
    ("İspanyolca", "es"),
    ("İtalyanca", "it"),
    ("Rusça", "ru"),
    ("Arapça", "ar"),
    ("Farsça", "fa"),
    ("Urduca", "ur"),
    ("Yunanca", "el"),
    ("Bulgarca", "bg"),
    ("Romence", "ro"),
    ("Ukraynaca", "uk"),
    ("Azerice", "az"),
    ("Kazakça", "kk"),
    ("Özbekçe", "uz"),
    ("Hintçe", "hi"),
    ("Bengalce", "bn"),
    ("Çince (Basitleştirilmiş)", "zh-CN"),
    ("Çince (Geleneksel)", "zh-TW"),
    ("Japonca", "ja"),
    ("Korece", "ko"),
    ("Vietnamca", "vi"),
    ("Tayca", "th"),
    ("Endonezce", "id"),
    ("Malayca", "ms"),
    ("Hollandaca", "nl"),
    ("İsveççe", "sv"),
    ("Norveççe", "no"),
    ("Danca", "da"),
    ("Fince", "fi"),
    ("Lehçe", "pl"),
    ("Çekçe", "cs"),
    ("Slovakça", "sk"),
    ("Macarca", "hu"),
    ("Hırvatça", "hr"),
    ("Sırpça", "sr"),
    ("Slovence", "sl"),
    ("Litvanca", "lt"),
    ("Letonca", "lv"),
    ("Estonca", "et"),
    ("İbranice", "he"),
    ("Portekizce", "pt"),
    ("Portekizce (Brezilya)", "pt-BR"),
    ("Galiçyaca", "gl"),
    ("Katalanca", "ca"),
    ("Baskça", "eu"),
    ("İrlandaca", "ga"),
    ("İzlandaca", "is"),
    ("Arnavutça", "sq"),
    ("Makedonca", "mk"),
    ("Boşnakça", "bs"),
    ("Gürcüce", "ka"),
    ("Ermenice", "hy"),
    ("Svahili", "sw"),
    ("Afrikanca", "af"),
    ("Filipince", "tl"),
    ("Nepalce", "ne"),
    ("Sinhala", "si"),
    ("Khmer", "km"),
    ("Laoca", "lo"),
    ("Myanmar", "my"),
    ("Moğolca", "mn"),
    ("Tacikçe", "tg"),
    ("Kırgızca", "ky"),
    ("Belarusça", "be"),
    ("Maltaca", "mt"),
    ("Lüksemburgca", "lb"),
    ("Galce", "cy"),
    ("İskoç Galcesi", "gd"),
    ("Esperanto", "eo"),
    ("Latince", "la"),
    ("Hawaii dili", "haw"),
    ("Maori", "mi"),
    ("Samoaca", "sm"),
    ("Yidiş", "yi"),
]

_LANG_NAME = {code: name for name, code in LANGUAGES}
_RTL_LANGS = {"ar", "fa", "he", "ur", "yi", "ps", "sd", "ug", "ckb"}

# İngilizce adlar: arayüz dili İngilizce olduğunda ve aramada alias olarak kullanılır.
ENGLISH_NAMES = {
    "auto": "Auto-detect",
    "tr": "Turkish",
    "en": "English",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "it": "Italian",
    "ru": "Russian",
    "ar": "Arabic",
    "fa": "Persian",
    "ur": "Urdu",
    "el": "Greek",
    "bg": "Bulgarian",
    "ro": "Romanian",
    "uk": "Ukrainian",
    "az": "Azerbaijani",
    "kk": "Kazakh",
    "uz": "Uzbek",
    "hi": "Hindi",
    "bn": "Bengali",
    "zh-CN": "Chinese (Simplified)",
    "zh-TW": "Chinese (Traditional)",
    "ja": "Japanese",
    "ko": "Korean",
    "vi": "Vietnamese",
    "th": "Thai",
    "id": "Indonesian",
    "ms": "Malay",
    "nl": "Dutch",
    "sv": "Swedish",
    "no": "Norwegian",
    "da": "Danish",
    "fi": "Finnish",
    "pl": "Polish",
    "cs": "Czech",
    "sk": "Slovak",
    "hu": "Hungarian",
    "hr": "Croatian",
    "sr": "Serbian",
    "sl": "Slovenian",
    "lt": "Lithuanian",
    "lv": "Latvian",
    "et": "Estonian",
    "he": "Hebrew",
    "pt": "Portuguese",
    "pt-BR": "Portuguese (Brazil)",
    "gl": "Galician",
    "ca": "Catalan",
    "eu": "Basque",
    "ga": "Irish",
    "is": "Icelandic",
    "sq": "Albanian",
    "mk": "Macedonian",
    "bs": "Bosnian",
    "ka": "Georgian",
    "hy": "Armenian",
    "sw": "Swahili",
    "af": "Afrikaans",
    "tl": "Filipino",
    "ne": "Nepali",
    "si": "Sinhala",
    "km": "Khmer",
    "lo": "Lao",
    "my": "Burmese",
    "mn": "Mongolian",
    "tg": "Tajik",
    "ky": "Kyrgyz",
    "be": "Belarusian",
    "mt": "Maltese",
    "lb": "Luxembourgish",
    "cy": "Welsh",
    "gd": "Scottish Gaelic",
    "eo": "Esperanto",
    "la": "Latin",
    "haw": "Hawaiian",
    "mi": "Maori",
    "sm": "Samoan",
    "yi": "Yiddish",
}

# Türkçe karakterleri arama için ASCII karşılıklarına indirger.
_TR_FOLD = str.maketrans(
    {
        "ç": "c",
        "Ç": "C",
        "ğ": "g",
        "Ğ": "G",
        "ı": "i",
        "İ": "I",
        "ö": "o",
        "Ö": "O",
        "ş": "s",
        "Ş": "S",
        "ü": "u",
        "Ü": "U",
    }
)


def _fold(text: str) -> str:
    """Arama anahtarı: küçük harf, Türkçe/aksan farklarını normalize eder."""
    text = (text or "").translate(_TR_FOLD)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.casefold()


def language_search_key(name: str, code: str) -> str:
    english = ENGLISH_NAMES.get(code, "")
    return _fold(f"{name} {english} {name.replace(' ', '')} {code}")


def filter_target_languages(query: str = "") -> list[tuple[str, str]]:
    """
    Hedef dilleri arama sorgusuna göre filtreler.
    Hem Türkçe hem İngilizce adlarla, Türkçe karakterler yazılmadan da eşleşir.
    Dönüş: [(görünen etiket, kod), ...] — ortak diller önce gelecek şekilde.
    """
    tokens = _fold(query).split()
    results: list[tuple[str, str]] = []
    for name, code in LANGUAGES:
        if code == "auto":
            continue
        haystack = language_search_key(name, code)
        if all(token in haystack for token in tokens):
            results.append((f"{name} ({code})", code))
    return results

SOURCE_LABELS = [name if code == "auto" else f"{name} ({code})" for name, code in LANGUAGES]
TARGET_LABELS = [f"{name} ({code})" for name, code in LANGUAGES if code != "auto"]


def lang_name(code: str) -> str:
    """Koddan Türkçe dil adı döndürür; bilinmiyorsa kodu döndürür."""
    if not code:
        return ""
    return _LANG_NAME.get(code, _LANG_NAME.get(code.split("-")[0], code))


def code_to_label(code: str, include_auto: bool = True) -> str:
    if code == "auto":
        return "Otomatik algıla" if include_auto else "Türkçe (tr)"
    name = _LANG_NAME.get(code, code)
    return f"{name} ({code})"


def label_to_code(label: str, default: str = "auto") -> str:
    """'Türkçe (tr)' veya 'Türkçe' biçimindeki etiketten kodu çıkarır."""
    label = (label or "").strip()
    if not label:
        return default
    for name, code in LANGUAGES:
        if label == name or label == f"{name} ({code})":
            return code
    # "(xx)" kalıbını dene
    if label.endswith(")") and "(" in label:
        code = label[label.rfind("(") + 1 : -1].strip()
        if code:
            return code
    return default


def is_rtl(code: str) -> bool:
    code = (code or "").lower()
    return code in _RTL_LANGS or code.split("-")[0] in _RTL_LANGS
