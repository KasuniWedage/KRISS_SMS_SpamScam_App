from app.hybrid_rules import evaluate_rules
from app.text_utils import anonymize_text, detect_language, preprocess_text


def test_anonymizes_email_and_sri_lankan_mobile_number():
    result = anonymize_text("Call 0771234567, OTP 123456, or mail person@example.com")
    assert "0771234567" not in result
    assert "person@example.com" not in result
    assert "123456" not in result
    assert "[PHONE]" in result
    assert "[EMAIL]" in result
    assert "[NUMBER]" in result


def test_detects_supported_scripts_and_singlish():
    assert detect_language("ඔබට කොහොමද") == "Sinhala"
    assert detect_language("உங்களுக்கு எப்படி") == "Tamil"
    assert detect_language("oya danma enna") == "Singlish"
    assert detect_language("Meeting tomorrow") == "English"


def test_preprocessing_replaces_sensitive_tokens():
    result = preprocess_text("Pay 123456 to 0771234567 at https://example.com")
    assert "numbertoken" in result
    assert "phonetoken" in result
    assert "urltoken" in result


def test_high_risk_rule_overrides_to_scam_category():
    result = evaluate_rules("Urgent: your bank account is suspended. Verify at https://bad.example")
    assert result.override is True
    assert result.scam_type == "Fake Bank / Phishing"
    assert result.confidence >= 0.88


def test_normal_message_does_not_trigger_override():
    result = evaluate_rules("The meeting starts at three tomorrow afternoon")
    assert result.override is False
    assert result.scam_type is None
