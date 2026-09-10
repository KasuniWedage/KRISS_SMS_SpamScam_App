"""Multilingual Classification & Rendering Tests for Sinhala, Tamil, English, and Singlish.

Validates that Sinhala (Unicode), Tamil (Unicode), English (Latin), and
Singlish (Latin transliteration) texts are correctly detected and classified.
"""
import pytest
from app.text_utils import detect_language, clean_text
from app.ml_service import ml_service


def test_trilingual_script_detection():
    # Sinhala Unicode
    assert detect_language("ඔබගේ බැංකු ගිණුම අත්හිටුවා ඇත") == "Sinhala"
    assert detect_language("සුබ උදෑසනක් වේවා") == "Sinhala"

    # Tamil Unicode
    assert detect_language("உங்கள் வங்கி கணக்கு முடக்கப்பட்டுள்ளது") == "Tamil"
    assert detect_language("காலை வணக்கம்") == "Tamil"

    # English
    assert detect_language("Dear customer, your OTP is 123456.") == "English"
    assert detect_language("Your package delivery is pending.") == "English"

    # Singlish
    assert detect_language("Oyata puluwanda mata eka ewanna?") == "Singlish"
    assert detect_language("Meka adha ude labuna ekak.") == "Singlish"


def test_multilingual_inference_stability():
    if not ml_service.ready:
        pytest.skip("ML service model not ready")

    samples = [
        ("ඔබට රුපියල් ලක්ෂ 10ක ත්‍යාගයක් හිමිව ඇත. ලබාගැනීමට අමතන්න.", "Sinhala"),
        ("நீங்கள் 10 லட்சம் பரிசு வென்றுள்ளீர்கள். அழைக்கவும்.", "Tamil"),
        ("URGENT: Your account 4829 has suspicious activity. Click http://bank-sec.xyz", "English"),
        ("Obata laksha 5k lottery dinumak labila thiyenawa. Call karanna 0771234567", "Singlish"),
        ("Ada reeta dinner ekata apith ekka enna puluwanda?", "Singlish")
    ]

    for text, expected_lang in samples:
        label, confidence, probs = ml_service.predict(text)
        assert detect_language(text) == expected_lang
        assert label in ["Legitimate", "Spam", "Scam"]
        assert 0.0 <= confidence <= 1.0
        assert isinstance(probs, dict)
