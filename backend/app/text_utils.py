import re
import unicodedata

URL_RE = re.compile(r"https?://\S+|www\.\S+", re.I)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?94|0)?7\d{8}(?!\d)")
LONG_NUMBER_RE = re.compile(r"\b\d{4,}\b")

EN_STOP = {"the","a","an","is","are","was","were","to","of","for","and","or","in","on","at","this","that","your","you","we","our","be","with"}
SI_STOP = {"සහ","හා","මෙම","මේ","එක","වෙත","ඔබ","ඔබගේ","අපේ","අද","දින"}
TA_STOP = {"மற்றும்","இந்த","அது","ஒரு","உங்கள்","நீங்கள்","இன்று","க்கு","என்று"}
SINGLISH_HINTS = {"oya","oyage","mama","eka","karanna","ganna","enna","yanna","wage","nam","puluwanda","danma","gewanna","ewannam","adha","labuna","meka","ude","mata","ow","ne","machan","wela","thiyenawa","dinumak","laba","reeta"}

def anonymize_text(text: str) -> str:
    text = URL_RE.sub("[URL]", text)
    text = EMAIL_RE.sub("[EMAIL]", text)
    text = PHONE_RE.sub("[PHONE]", text)
    text = LONG_NUMBER_RE.sub("[NUMBER]", text)
    return text

def detect_language(text: str) -> str:
    if any('\u0d80' <= ch <= '\u0dff' for ch in text):
        return "Sinhala"
    if any('\u0b80' <= ch <= '\u0bff' for ch in text):
        return "Tamil"
    tokens = set(re.findall(r"[a-zA-Z]+", text.lower()))
    if len(tokens & SINGLISH_HINTS) >= 1:
        return "Singlish"
    return "English"

def preprocess_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower().strip()
    text = URL_RE.sub(" urltoken ", text)
    text = EMAIL_RE.sub(" emailtoken ", text)
    text = PHONE_RE.sub(" phonetoken ", text)
    text = LONG_NUMBER_RE.sub(" numbertoken ", text)
    text = re.sub(r"[^\w\u0D80-\u0DFF\u0B80-\u0BFF]+", " ", text, flags=re.UNICODE)
    tokens = [t for t in text.split() if t not in EN_STOP and t not in SI_STOP and t not in TA_STOP and len(t) > 1]
    return " ".join(tokens)

# Backward-compatible convenience aliases
mask_pii = anonymize_text
clean_text = preprocess_text
