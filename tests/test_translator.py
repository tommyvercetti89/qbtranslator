"""qbtranslator.core.translator.py için ağa çıkmayan birim testleri."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from qbtranslator import i18n
from qbtranslator.core import translator

i18n.set_language("tr")


class MyMemoryTests(unittest.TestCase):
    def test_autodetect_uses_mymemory_and_reads_detected_language(self) -> None:
        payload = {
            "responseData": {
                "translatedText": "Hello world",
                "detectedLanguage": "tr",
            },
            "responseStatus": 200,
            "responseDetails": "",
        }
        with patch("qbtranslator.core.translator._http_get", return_value=json.dumps(payload)) as get:
            text, detected = translator.mymemory_translate("Merhaba dünya", "auto", "en")

        self.assertEqual(text, "Hello world")
        self.assertEqual(detected, "tr")
        query = parse_qs(urlsplit(get.call_args.args[0]).query)
        self.assertEqual(query["langpair"], ["Autodetect|en"])

    def test_same_language_is_not_sent_to_api(self) -> None:
        with patch("qbtranslator.core.translator._http_get") as get:
            text, detected = translator.mymemory_translate("Merhaba", "tr", "tr")
        self.assertEqual(text, "Merhaba")
        self.assertEqual(detected, "tr")
        get.assert_not_called()

    def test_same_language_error_from_auto_detect_is_friendly(self) -> None:
        payload = {
            "responseData": {"translatedText": "PLEASE SELECT TWO DISTINCT LANGUAGES"},
            "responseStatus": "403",
            "responseDetails": "PLEASE SELECT TWO DISTINCT LANGUAGES",
        }
        with patch("qbtranslator.core.translator._http_get", return_value=json.dumps(payload)):
            with self.assertRaises(translator.TranslationError) as caught:
                translator.mymemory_translate("Merhaba", "auto", "tr")
        self.assertIn("zaten hedef dilde", str(caught.exception))
        self.assertNotIn("PLEASE SELECT", str(caught.exception))

    def test_error_text_with_http_200_is_rejected(self) -> None:
        payload = {
            "responseData": {
                "translatedText": "MYMEMORY WARNING: YOU USED ALL AVAILABLE FREE TRANSLATIONS"
            },
            "responseStatus": 200,
            "responseDetails": "",
        }
        with patch("qbtranslator.core.translator._http_get", return_value=json.dumps(payload)):
            with self.assertRaises(translator.TranslationError):
                translator.mymemory_translate("Merhaba", "tr", "en")

    def test_non_200_status_is_rejected(self) -> None:
        payload = {
            "responseData": {"translatedText": "server error"},
            "responseStatus": "500",
            "responseDetails": "temporary failure",
        }
        with patch("qbtranslator.core.translator._http_get", return_value=json.dumps(payload)):
            with self.assertRaises(translator.TranslationError) as caught:
                translator.mymemory_translate("Merhaba", "tr", "en")
        self.assertIn("temporary failure", str(caught.exception))


class TranslateTests(unittest.TestCase):
    def test_explicit_same_language_short_circuits(self) -> None:
        with patch("qbtranslator.core.translator._run_engine") as run_engine:
            outcome = translator.translate(
                "Merhaba", "tr", "tr", {"engine": "mymemory", "backup_engines": False}
            )
        self.assertEqual(outcome.text, "Merhaba")
        self.assertEqual(outcome.source_lang, "tr")
        self.assertEqual(outcome.target_lang, "tr")
        run_engine.assert_not_called()

    def test_auto_target_is_rejected(self) -> None:
        with self.assertRaises(translator.TranslationError):
            translator.translate("Merhaba", "tr", "auto", {"engine": "google"})

    def test_fallback_chain_uses_next_engine_after_error(self) -> None:
        def failing(*_args, **_kwargs):
            raise translator.TranslationError("primary failed")

        def working(*_args, **_kwargs):
            return "Hello", "tr"

        config = {"engine": "mymemory", "backup_engines": True}
        with patch("qbtranslator.core.translator.mymemory_translate", side_effect=failing), patch(
            "qbtranslator.core.translator.lingva_translate", side_effect=working
        ):
            outcome = translator.translate("Merhaba fallback testi", "auto", "en", config)

        self.assertEqual(outcome.text, "Hello")
        self.assertEqual(outcome.engine, "lingva")

    def test_backup_setting_is_part_of_cache_key(self) -> None:
        calls = []

        def fake_run(engine, text, source, target, config):
            calls.append((engine, text, config.get("backup_engines")))
            return translator.TranslationOutcome(
                text=f"{text}-{engine}", source_lang="tr", target_lang="en", engine=engine
            )

        text = "önbellek anahtarı testi"
        with patch("qbtranslator.core.translator._run_engine", side_effect=fake_run):
            first = translator.translate(
                text, "tr", "en", {"engine": "google", "backup_engines": False}
            )
            second = translator.translate(
                text, "tr", "en", {"engine": "google", "backup_engines": True}
            )

        self.assertEqual(first.text, f"{text}-google")
        self.assertEqual(second.text, f"{text}-google")
        self.assertEqual(len(calls), 2)

    def test_long_unpunctuated_text_is_chunked_safely(self) -> None:
        text = ("kelime " * 2000).strip()
        chunks = translator._split_chunks(text, limit=1500)
        self.assertTrue(chunks)
        self.assertTrue(all(len(chunk) <= 1500 for chunk in chunks))
        self.assertEqual("".join(chunks), text)

    def test_errors_are_localized(self) -> None:
        i18n.set_language("en")
        try:
            with self.assertRaises(translator.TranslationError) as caught:
                translator.translate("", "tr", "en", {"engine": "google"})
            self.assertIn("empty", str(caught.exception).lower())
        finally:
            i18n.set_language("tr")


class ConfigurableEngineTests(unittest.TestCase):
    def test_libretranslate_uses_endpoint_and_key_from_config(self) -> None:
        response = json.dumps(
            {"translatedText": "Hello", "detectedLanguage": {"language": "tr"}}
        )
        text = "LibreTranslate ayar testi"
        with patch(
            "qbtranslator.core.translator._http_post_json", return_value=response
        ) as post:
            outcome = translator.translate(
                text,
                "tr",
                "en",
                {
                    "engine": "libretranslate",
                    "backup_engines": False,
                    "libretranslate_endpoint": "http://127.0.0.1:5000",
                    "libretranslate_api_key": "test-key",
                },
            )

        self.assertEqual(outcome.text, "Hello")
        self.assertEqual(outcome.engine, "libretranslate")
        self.assertEqual(post.call_args.args[0], "http://127.0.0.1:5000/translate")
        payload = post.call_args.args[1]
        self.assertEqual(payload["q"], text)
        self.assertEqual(payload["source"], "tr")
        self.assertEqual(payload["target"], "en")
        self.assertEqual(payload["api_key"], "test-key")

    def test_lingva_uses_endpoint_from_config(self) -> None:
        response = json.dumps(
            {"translation": "Hello", "info": {"detectedSource": "tr"}}
        )
        text = "Lingva ayar testi"
        with patch(
            "qbtranslator.core.translator._http_get", return_value=response
        ) as get:
            outcome = translator.translate(
                text,
                "tr",
                "en",
                {
                    "engine": "lingva",
                    "backup_engines": False,
                    "lingva_endpoint": "https://lingva.example",
                },
            )

        self.assertEqual(outcome.text, "Hello")
        self.assertEqual(outcome.engine, "lingva")
        self.assertTrue(
            get.call_args.args[0].startswith("https://lingva.example/api/v1/tr/en/")
        )

    def test_llm_uses_endpoint_model_and_key_from_config(self) -> None:
        response = json.dumps({"choices": [{"message": {"content": "Hello"}}]})
        text = "LLM ayar testi"
        with patch(
            "qbtranslator.core.translator._http_post_json", return_value=response
        ) as post:
            outcome = translator.translate(
                text,
                "tr",
                "en",
                {
                    "engine": "llm",
                    "backup_engines": False,
                    "llm_endpoint": "http://127.0.0.1:11434/v1",
                    "llm_model": "qwen3",
                    "llm_api_key": "llm-key",
                },
            )

        self.assertEqual(outcome.text, "Hello")
        self.assertEqual(outcome.engine, "llm")
        self.assertEqual(
            post.call_args.args[0], "http://127.0.0.1:11434/v1/chat/completions"
        )
        self.assertEqual(post.call_args.args[1]["model"], "qwen3")
        self.assertEqual(
            post.call_args.args[2]["Authorization"], "Bearer llm-key"
        )


if __name__ == "__main__":
    unittest.main()
