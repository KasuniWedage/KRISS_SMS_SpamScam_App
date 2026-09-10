from dataclasses import dataclass
import re
from .text_utils import URL_RE

@dataclass
class RuleResult:
    override: bool
    confidence: float
    scam_type: str | None
    reasons: list[str]

RULE_GROUPS = [
    ("OTP / Credential Theft", [r"share\s+(?:your\s+)?otp", r"reply.*otp", r"password.*verify", r"otp.*yawanna", r"otp.*යවන්න"]),
    ("Fake Bank / Phishing", [r"account.*suspend", r"bank.*verify", r"unusual activity", r"ගිණුම.*අත්හිට", r"account.*block", r"ගිණුම්.*තහවුරු"]),
    ("Prize / Lottery Scam", [r"won.*(?:prize|cash|rs\.)", r"winner alert", r"prize.*claim", r"ත්‍යාග.*ජය", r"win wela", r"lucky draw"]),
    ("Parcel / Delivery Scam", [r"parcel.*(?:fee|pay|hold)", r"delivery.*(?:fee|pay|failed)", r"පාර්සල.*ගාස්තු", r"parcel.*gewanna"]),
    ("Loan Scam", [r"pre.?approved.*loan", r"loan approved.*fee", r"instant loan.*no documents", r"ණය.*අනුමත", r"loan.*gewanna"]),
    ("Fake Job Scam", [r"job.*(?:registration|activation).*fee", r"earn.*week.*pay.*registration", r"රැකියාව.*ගාස්තු", r"job.*fee.*gewanna"]),
]
MONEY_URGENCY = [r"urgent", r"immediately", r"danma", r"වහාම", r"expire", r"කල් ඉකුත්"]

def evaluate_rules(text: str) -> RuleResult:
    lower = text.lower()
    reasons=[]; scam_type=None; matches=0
    for name, patterns in RULE_GROUPS:
        local = [p for p in patterns if re.search(p, lower, re.I)]
        if local:
            scam_type=name; matches += len(local); reasons.append(f"Matched high-risk pattern: {name}")
            break
    has_url = bool(URL_RE.search(text))
    if has_url and scam_type:
        reasons.append("Contains a link combined with a high-risk request")
        matches += 1
    if any(re.search(p, lower, re.I) for p in MONEY_URGENCY) and scam_type:
        reasons.append("Uses urgency/pressure language")
        matches += 1
    if scam_type:
        confidence=min(0.99, 0.88 + 0.03 * matches)
        return RuleResult(True, confidence, scam_type, reasons)
    return RuleResult(False, 0.0, None, [])
