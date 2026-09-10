from datetime import datetime, timedelta, timezone
from typing import cast
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..auth import get_auth_context, get_current_user, hash_password, revoke_user_sessions, verify_password
from ..firebase_auth import delete_firebase_user
from ..database import get_db
from ..models import AuditLog, ClassificationResult, Feedback, PublishedSpam, Report, SMSMessage, User
from ..schemas import ActivityLogOut, DeleteAccountRequest, FeedbackRequest, PasswordChange, ProfileUpdate, PublishSpamRequest, PublishedSpamOut, ReportRequest, SettingsUpdate, UserFeedbackOut, UserOut, UserReportOut

router = APIRouter(prefix="/api", tags=["User Actions"])

@router.post("/reports", status_code=201)
def report(body: ReportRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sms = db.query(SMSMessage).filter(SMSMessage.id == body.sms_id, SMSMessage.user_id == user.id).first()
    if not sms: raise HTTPException(404, detail="SMS record not found")
    db.add(Report(sms_id=sms.id, user_id=user.id, reason=body.reason.strip()))
    db.add(AuditLog(user_id=user.id, action="SMS_REPORTED", detail=f"sms_id={sms.id}")); db.commit()
    return {"message":"Suspicious message reported successfully"}

@router.post("/feedback", status_code=201)
def feedback(body: FeedbackRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.expected_label and body.expected_label not in {"Legitimate","Spam","Scam"}:
        raise HTTPException(400, detail="expected_label must be Legitimate, Spam, or Scam")
    if body.sms_id:
        exists=db.query(SMSMessage).filter(SMSMessage.id==body.sms_id, SMSMessage.user_id==user.id).first()
        if not exists: raise HTTPException(404, detail="SMS record not found")
    db.add(Feedback(sms_id=body.sms_id,user_id=user.id,feedback_text=body.feedback_text,expected_label=body.expected_label)); db.commit()
    return {"message":"Thank you for your feedback"}

@router.post("/community-spam", status_code=201)
def publish_spam(body: PublishSpamRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row=db.query(SMSMessage,ClassificationResult).join(ClassificationResult).filter(SMSMessage.id==body.sms_id,SMSMessage.user_id==user.id).first()
    if not row: raise HTTPException(404,detail="SMS record not found")
    sms,result=row
    if result.predicted_class not in {"Spam","Scam"}: raise HTTPException(400,detail="Only Spam or Scam results can be published")
    if db.query(PublishedSpam).filter(PublishedSpam.sms_id==body.sms_id).first(): raise HTTPException(409,detail="This record is already published")
    item=PublishedSpam(
        sms_id=body.sms_id,
        user_id=user.id,
        sender_no=(sms.sender_no or "Unknown")[:50],
        message_text=sms.masked_text,
        label=result.predicted_class,
    )
    db.add(item);db.add(AuditLog(user_id=user.id,action="SPAM_PUBLISHED",detail=f"sms_id={body.sms_id}"));db.commit();db.refresh(item)
    return {"message":"Published to the community feed","id":item.id}

@router.get("/community-spam",response_model=list[PublishedSpamOut])
def community_spam(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows=db.query(PublishedSpam).order_by(PublishedSpam.published_at.desc()).limit(200).all()
    return [PublishedSpamOut(id=cast(int, x.id),sender_no=cast(str, x.sender_no),message=cast(str, x.message_text),label=cast(str, x.label),published_at=cast(datetime, x.published_at)) for x in rows]

@router.get("/my-reports",response_model=list[UserReportOut])
def my_reports(user: User = Depends(get_current_user),db: Session = Depends(get_db)):
    rows=db.query(Report,SMSMessage).join(SMSMessage,Report.sms_id==SMSMessage.id).filter(Report.user_id==user.id).order_by(Report.report_date.desc()).all()
    return [UserReportOut(id=cast(int, r.id),sms_id=cast(int, r.sms_id),message=cast(str, s.masked_text),reason=cast(str, r.reason),report_date=cast(datetime, r.report_date)) for r,s in rows]

@router.get("/my-feedback",response_model=list[UserFeedbackOut])
def my_feedback(user: User = Depends(get_current_user),db: Session = Depends(get_db)):
    rows=db.query(Feedback).filter(Feedback.user_id==user.id).order_by(Feedback.created_at.desc()).all();out=[]
    for x in rows:
        sms=db.query(SMSMessage).filter(SMSMessage.id==x.sms_id).first() if x.sms_id else None
        out.append(UserFeedbackOut(
            id=cast(int, x.id),
            sms_id=cast(int, x.sms_id) if x.sms_id is not None else None,
            message=cast(str, sms.masked_text) if sms is not None else None,
            feedback_text=cast(str, x.feedback_text) if x.feedback_text is not None else None,
            expected_label=cast(str, x.expected_label) if x.expected_label is not None else None,
            created_at=cast(datetime, x.created_at)
        ))
    return out

@router.get("/settings", response_model=UserOut)
def settings(user: User = Depends(get_current_user)):
    return user

@router.patch("/settings", response_model=UserOut)
def update_settings(body: SettingsUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.language_preference is not None:
        lang_raw = body.language_preference.strip().lower()
        norm_map = {
            "english": "English", "en": "English",
            "sinhala": "Sinhala", "si": "Sinhala",
            "tamil": "Tamil", "ta": "Tamil",
            "singlish": "Singlish"
        }
        if lang_raw not in norm_map:
            raise HTTPException(400, detail="Unsupported UI language. Supported: English, Sinhala, Tamil, Singlish")
        setattr(user, "language_preference", norm_map[lang_raw])
    if body.notifications_enabled is not None:
        setattr(user, "notifications_enabled", body.notifications_enabled)
    if body.auto_delete_history is not None:
        setattr(user, "auto_delete_history", body.auto_delete_history)
    db.add(AuditLog(user_id=user.id,action="SETTINGS_UPDATED")); db.commit(); db.refresh(user); return user

@router.patch("/profile",response_model=UserOut)
def update_profile(body:ProfileUpdate,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    if body.email.lower() != str(user.email).lower():
        raise HTTPException(400, detail="Email changes require a separate verified-email flow")
    duplicate=db.query(User).filter(User.id!=user.id,User.username==body.username).first()
    if duplicate: raise HTTPException(409,detail="Username or email already exists")
    setattr(user, "name", body.name.strip())
    setattr(user, "username", body.username.strip())
    setattr(user, "email", body.email.lower())
    db.add(AuditLog(user_id=user.id,action="PROFILE_UPDATED"));db.commit();db.refresh(user);return user

@router.post("/change-password")
def change_password(body:PasswordChange,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    if user.auth_provider != "email":
        raise HTTPException(400, detail="Password changes are managed by your identity provider")
    if not verify_password(body.current_password, str(user.password_hash)): raise HTTPException(400,detail="Current password is incorrect")
    if not any(c.isalpha() for c in body.new_password) or not any(c.isdigit() for c in body.new_password): raise HTTPException(400,detail="New password must contain letters and numbers")
    setattr(user, "password_hash", hash_password(body.new_password))
    revoke_user_sessions(db, cast(int, user.id))
    db.add(AuditLog(user_id=user.id,action="PASSWORD_CHANGED"));db.commit();return {"message":"Password changed. Please sign in again."}

@router.delete("/account")
def delete_account(body:DeleteAccountRequest,ctx=Depends(get_auth_context),db:Session=Depends(get_db)):
    user, session = ctx
    if body.confirmation != "DELETE ACCOUNT":
        raise HTTPException(400, detail="Type DELETE ACCOUNT exactly to confirm deletion.")
    session_created = cast(datetime, session.created_at)
    if session_created.tzinfo is None:
        session_created = session_created.replace(tzinfo=timezone.utc)
    if session_created < datetime.now(timezone.utc) - timedelta(minutes=10):
        raise HTTPException(401, detail="For security, sign in again before deleting your account.")
    if user.firebase_uid:
        delete_firebase_user(str(user.firebase_uid))
    db.delete(user);db.commit();return {"message":"Account permanently deleted"}

@router.get("/activity-log",response_model=list[ActivityLogOut])
def activity_log(user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    rows=db.query(AuditLog).filter(AuditLog.user_id==user.id).order_by(AuditLog.created_at.desc()).limit(200).all()
    return [ActivityLogOut(id=cast(int, x.id),action=cast(str, x.action),detail=cast(str, x.detail) if x.detail is not None else None,created_at=cast(datetime, x.created_at)) for x in rows]
