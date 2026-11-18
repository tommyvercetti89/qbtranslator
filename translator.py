"""
translator.py — Çeviri motorları.

Varsayılan: Google Translate (ücretsiz gtx uç noktası, API anahtarı gerekmez).
İsteğe bağlı: MyMemory, LibreTranslate, Lingva, LLM (OpenAI uyumlu).

Yalnızca standart kütüphane kullanır (urllib, json, re).
"""

from __future__ import annotations

import html
import http.client
import json
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock

from langs import lang_name

TIMEOUT = 10
LLM_TIMEOUT = 60
CACHE_LIMIT = 300

GOOGLE_ENDPOINTS = [
    "https://translate.googleapis.com/translate_a/single",
    "https://translate.google.com/translate_a/single",
]

BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "tr,en;q=0.8",
}

ENGINE_LABELS = {
    "google": "Google Translate",
    "mymemory": "MyMemory",
    "libretranslate": "LibreTranslate",
    "lingva": "Lingva",
    "llm": "LLM",
}

ENGINE_OPTIONS = [
    ("Google Translate (varsayılan)", "google"),
    ("MyMemory (ücretsiz yedek)", "mymemory"),
    ("LibreTranslate", "libretranslate"),
    ("Lingva", "lingva"),
    ("LLM — OpenAI uyumlu (Ollama / LM Studio / OpenAI)", "llm"),
]


class TranslationError(Exception):
    pass


@dataclass
class TranslationOutcome:
    text: str
    source_lang: str
    target_lang: str
    engine: str

    @property
    def engine_label(self) -> str:
        return ENGINE_LABELS.get(self.engine, self.engine)


# --------------------------------------------------------------------------
# Küçük HTTP yardımcıları
# --------------------------------------------------------------------------
def _http_get(url: str, timeout: int = TIMEOUT) -> str:
    request = urllib.request.Request(url, headers=BASE_HEADERS)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace")


def _http_post_json(url: str, payload: dict, headers: dict | None = None, timeout: int = TIMEOUT) -> str:
    body = json.dumps(payload).encode("utf-8")
    merged = dict(BASE_HEADERS)
    merged["Content-Type"] = "application/json"
    if headers:
        merged.update(headers)
    request = urllib.request.Request(url, data=body, headers=merged, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace")


# --------------------------------------------------------------------------
# Google için kalıcı HTTPS bağlantısı
# (her istekte TLS el sıkışmasını tekrarlamamak için)
# --------------------------------------------------------------------------
_keepalive_lock = Lock()
_keepalive_connections: dict[str, http.client.HTTPSConnection] = {}
_proxy_configured = bool(
    urllib.request.getproxies().get("https") or urllib.request.getproxies().get("http")
)


def _http_get_google(url: str, timeout: int = TIMEOUT) -> str:
    if _proxy_configured:
        return _http_get(url, timeout)

    parts = urllib.parse.urlsplit(url)
    host = parts.netloc
    path = parts.path + (("?" + parts.query) if parts.query else "")

    with _keepalive_lock:
        connection = _keepalive_connections.get(host)
        for attempt in (1, 2):
            try:
                if connection is None:
                    connection = http.client.HTTPSConnection(host, timeout=timeout)
                    _keepalive_connections[host] = connection
                connection.request("GET", path, headers=BASE_HEADERS)
                response = connection.getresponse()
                payload = response.read()
                if response.status != 200:
                    raise TranslationError(f"Google HTTP {response.status}")
                return payload.decode("utf-8", "replace")
            except TranslationError:
                raise
            except (http.client.HTTPException, OSError):
                try:
                    if connection is not None:
                        connection.close()
                except Exception:
                    pass
                _keepalive_connections.pop(host, None)
                connection = None
                if attempt == 2:
                    raise
        raise TranslationError("Google bağlantısı kurulamadı.")


def _friendly_error(exc: Exception) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code} ({exc.reason})"
    if isinstance(exc, urllib.error.URLError):
        return f"bağlantı hatası: {exc.reason}"
    if isinstance(exc, TimeoutError):
        return "zaman aşımı"
    if isinstance(exc, TranslationError):
        return str(exc)
    return str(exc) or exc.__class__.__name__


# --------------------------------------------------------------------------
# Önbellek (aynı metni tekrar tekrar göndermemek için)
# --------------------------------------------------------------------------
_cache: OrderedDict[tuple, TranslationOutcome] = OrderedDict()
_cache_lock = Lock()


def _cache_get(key: tuple) -> TranslationOutcome | None:
    with _cache_lock:
        outcome = _cache.get(key)
        if outcome is not None:
            _cache.move_to_end(key)
        return outcome


def _cache_put(key: tuple, outcome: TranslationOutcome) -> None:
    with _cache_lock:
        _cache[key] = outcome
        while len(_cache) > CACHE_LIMIT:
            _cache.popitem(last=False)


# --------------------------------------------------------------------------
# Google Translate (varsayılan)
# --------------------------------------------------------------------------
def _google_once(text: str, source: str, target: str) -> tuple[str, str]:
    params = urllib.parse.urlencode(
        {
            "client": "gtx",
            "sl": source or "auto",
            "tl": target,
            "dt": "t",
            "dj": "1",
            "q": text,
        }
    )
    last_error: Exception | None = None
    for endpoint in GOOGLE_ENDPOINTS:
        try:
            data = json.loads(_http_get_google(endpoint + "?" + params))
            sentences = data.get("sentences") or []
            translated = "".join(str(item.get("trans") or "") for item in sentences)
            detected = data.get("src") or ""
            return translated, detected
        except Exception as exc:
            last_error = exc
            continue
    if last_error is not None:
        raise TranslationError(f"Google: {_friendly_error(last_error)}")
    raise TranslationError("Google uç noktasına ulaşılamadı.")


def _split_chunks(text: str, limit: int = 4000) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    buffer = ""
    for part in re.split(r"(?<=[.!?。！？\n])", text):
        if buffer and len(buffer) + len(part) > limit:
            chunks.append(buffer)
            buffer = part
        else:
            buffer += part
    if buffer:
        chunks.append(buffer)
    return chunks


def google_translate(text: str, source: str, target: str) -> tuple[str, str]:
    translated_parts: list[str] = []
    detected = ""
    for index, chunk in enumerate(_split_chunks(text)):
        part, chunk_detected = _google_once(chunk, source, target)
        # Parçalar ayrı çevrildiğinde baştaki boşluk kaybolabilir; cümleler
        # birbirine yapışmasın diye özgün boşluğu koru.
        if (
            index > 0
            and chunk[:1].isspace()
            and translated_parts
            and not translated_parts[-1].endswith((" ", "\n"))
        ):
            translated_parts.append(" ")
        translated_parts.append(part)
        detected = detected or chunk_detected
    return "".join(translated_parts), detected


def detect_language(text: str) -> str:
    """Google'ın otomatik algılamasını kullanarak dil kodunu döndürür."""
    try:
        _, detected = _google_once(text[:400], "auto", "en")
        return detected or "en"
    except Exception:
        return "en"


# --------------------------------------------------------------------------
# MyMemory
# --------------------------------------------------------------------------
def mymemory_translate(text: str, source: str, target: str) -> tuple[str, str]:
    if len(text) > 480:
        raise TranslationError("MyMemory tek istekte yaklaşık 500 karakter destekler.")
    src = source if source and source != "auto" else detect_language(text)
    params = urllib.parse.urlencode({"q": text, "langpair": f"{src}|{target}"})
    data = json.loads(_http_get("https://api.mymemory.translated.net/get?" + params))
    translated = html.unescape(((data.get("responseData") or {}).get("translatedText") or "")).strip()
    if not translated:
        raise TranslationError(str(data.get("responseDetails") or "MyMemory boş yanıt döndürdü."))
    return translated, src


# --------------------------------------------------------------------------
# LibreTranslate
# --------------------------------------------------------------------------
def libretranslate_translate(
    text: str, source: str, target: str, endpoint: str, api_key: str = ""
) -> tuple[str, str]:
    endpoint = (endpoint or "").strip().rstrip("/")
    if not endpoint:
        raise TranslationError("LibreTranslate uç noktası ayarlanmamış.")
    payload = {
        "q": text,
        "source": source or "auto",
        "target": target,
        "format": "text",
    }
    if api_key:
        payload["api_key"] = api_key
    data = json.loads(_http_post_json(endpoint + "/translate", payload))
    translated = (data.get("translatedText") or "").strip()
    if not translated:
        raise TranslationError(str(data.get("error") or "LibreTranslate boş yanıt döndürdü."))
    detected = ((data.get("detectedLanguage") or {}).get("language")) or source or "auto"
    return translated, detected


# --------------------------------------------------------------------------
# Lingva
# --------------------------------------------------------------------------
def lingva_translate(text: str, source: str, target: str, endpoint: str) -> tuple[str, str]:
    endpoint = (endpoint or "").strip().rstrip("/")
    if not endpoint:
        raise TranslationError("Lingva uç noktası ayarlanmamış.")
    src = source or "auto"
    url = f"{endpoint}/api/v1/{src}/{target}/{urllib.parse.quote(text, safe='')}"
    data = json.loads(_http_get(url))
    translated = (data.get("translation") or "").strip()
    if not translated:
        raise TranslationError("Lingva boş yanıt döndürdü.")
    detected = ((data.get("info") or {}).get("detectedSource")) or src
    return translated, detected


# --------------------------------------------------------------------------
# LLM (OpenAI uyumlu: Ollama, LM Studio, OpenAI, OpenRouter, Groq...)
# --------------------------------------------------------------------------
def llm_translate(
    text: str,
    source: str,
    target: str,
    endpoint: str,
    model: str,
    api_key: str = "",
) -> tuple[str, str]:
    endpoint = (endpoint or "").strip().rstrip("/")
    model = (model or "").strip()
    if not endpoint:
        raise TranslationError("LLM uç noktası ayarlanmamış (örn. http://localhost:11434/v1).")
    if not model:
        raise TranslationError("LLM modeli ayarlanmamış (örn. llama3.2).")

    target_name = lang_name(target)
    if source and source != "auto":
        instruction = f"Translate the text from {lang_name(source)} to {target_name}."
    else:
        instruction = f"Translate the text to {target_name}."

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a translation engine. Return only the translated text. "
                    "Never add explanations, notes, quotes or extra markup."
                ),
            },
            {"role": "user", "content": f"{instruction}\n<text>\n{text}\n</text>"},
        ],
        "temperature": 0.1,
    }
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else None
    data = json.loads(_http_post_json(endpoint + "/chat/completions", payload, headers, LLM_TIMEOUT))
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise TranslationError("LLM yanıtı beklenen biçimde değil.")
    translated = (content or "").strip()
    if not translated:
        raise TranslationError("LLM boş yanıt döndürdü.")
    return translated, source or "auto"


# --------------------------------------------------------------------------
# Motor çalıştırma + yedek zinciri
# --------------------------------------------------------------------------
def _run_engine(engine: str, text: str, source: str, target: str, config: dict) -> TranslationOutcome:
    if engine == "google":
        translated, detected = google_translate(text, source, target)
    elif engine == "mymemory":
        translated, detected = mymemory_translate(text, source, target)
    elif engine == "libretranslate":
        translated, detected = libretranslate_translate(
            text,
            source,
            target,
            config.get("libretranslate_endpoint", ""),
            config.get("libretranslate_api_key", ""),
        )
    elif engine == "lingva":
        translated, detected = lingva_translate(
            text, source, target, config.get("lingva_endpoint", "")
        )
    elif engine == "llm":
        translated, detected = llm_translate(
            text,
            source,
            target,
            config.get("llm_endpoint", ""),
            config.get("llm_model", ""),
            config.get("llm_api_key", ""),
        )
    else:
        raise TranslationError(f"Bilinmeyen motor: {engine}")

    translated = (translated or "").strip()
    if not translated:
        raise TranslationError("Motor boş yanıt döndürdü.")

    detected = detected or (source if source and source != "auto" else "")
    return TranslationOutcome(
        text=translated,
        source_lang=detected,
        target_lang=target,
        engine=engine,
    )


def translate(text: str, source: str, target: str, config: dict) -> TranslationOutcome:
    """
    Metni çevirir. cfg:
      engine            — birincil motor ("google" vb.)
      backup_engines    — True ise hata durumunda MyMemory/Lingva/LibreTranslate denenir
    """
    text = (text or "").strip()
    if not text:
        raise TranslationError("Çevrilecek metin boş.")
    if not target:
        raise TranslationError("Hedef dil seçilmemiş.")

    engine = config.get("engine", "google")
    order = [engine]
    if config.get("backup_engines"):
        for candidate in ("mymemory", "lingva", "libretranslate", "google"):
            if candidate != engine and candidate not in order:
                order.append(candidate)

    # Motor ayarları değişince eski önbellek sonucu kullanılmasın.
    fingerprint = (
        config.get("llm_endpoint", ""),
        config.get("llm_model", ""),
        config.get("llm_api_key", ""),
        config.get("libretranslate_endpoint", ""),
        config.get("libretranslate_api_key", ""),
        config.get("lingva_endpoint", ""),
    )
    cache_key = (engine, source, target, text, fingerprint)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    errors: list[str] = []
    for candidate in order:
        try:
            outcome = _run_engine(candidate, text, source, target, config)
            _cache_put(cache_key, outcome)
            return outcome
        except Exception as exc:
            errors.append(f"{ENGINE_LABELS.get(candidate, candidate)}: {_friendly_error(exc)}")

    raise TranslationError("Çeviri başarısız oldu.\n" + "\n".join(errors))
