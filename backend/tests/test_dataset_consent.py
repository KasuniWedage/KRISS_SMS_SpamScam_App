"""Dataset Consent, Privacy Anonymization, and Authorization Test Suite.

Validates that submitted SMS samples respect privacy masking, consent flags,
and authorization controls when stored in the research and training tables.
"""
import pytest
from app.text_utils import mask_pii
from app.database import Base, engine, SessionLocal
from app.models import User, SMSMessage, Feedback
from app.auth import create_session_token, hash_password
from app.services import classify_and_store


def test_pii_masking_of_sensitive_entities():
    # Mask phone numbers
    raw_1 = "Contact support on 0771234567 or +94719876543 immediately."
    masked_1 = mask_pii(raw_1)
    assert "0771234567" not in masked_1
    assert "[PHONE]" in masked_1

    # Mask URLs
    raw_2 = "Verify account at http://secure-bank-login.com/auth now."
    masked_2 = mask_pii(raw_2)
    assert "http://secure-bank-login.com/auth" not in masked_2
    assert "[URL]" in masked_2

    # Mask NIC / Long numbers
    raw_3 = "My reference number is 199512345678."
    masked_3 = mask_pii(raw_3)
    assert "199512345678" not in masked_3
    assert "[NUMBER]" in masked_3 or "[PHONE]" in masked_3


def test_database_storage_masks_pii():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    user = db.query(User).filter(User.username == "test_consent_user").first()
    if not user:
        user = User(
            name="Consent Tester",
            username="test_consent_user",
            email="consent@kriss.lk",
            password_hash=hash_password("Pass1234!"),
            role="user"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    result = classify_and_store(
        db=db,
        user_id=user.id,
        message="Call 0771234567 to claim lottery prize at http://fake-win.com",
        sender_no="0779999999"
    )

    sms_record = db.query(SMSMessage).filter(SMSMessage.id == result["sms_id"]).first()
    assert sms_record is not None
    # Verify stored masked_text does not contain raw phone / URL
    assert "0771234567" not in sms_record.masked_text
    assert "[PHONE]" in sms_record.masked_text
    assert "[URL]" in sms_record.masked_text
    db.close()
