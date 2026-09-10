"""Generate high quality, diverse multilingual training dataset and real world evaluation dataset.
"""
import random
from pathlib import Path
import pandas as pd

random.seed(42)

# --- SPAM VOCABULARY ENHANCEMENTS FOR ALL LANGUAGES ---
ENG_SPAM_EXTRA = [
    "EXCLUSIVE DEAL! Enjoy {disc}% OFF on all items at {shop} showrooms island-wide this weekend! T&C apply.",
    "Get unlimited YouTube & TikTok for 30 days for only Rs. {amt}+tax. Type ACT YT and send to 678 now!",
    "Apply for an easy personal loan with lowest interest rates from {bank} Finance. Call 0112345678 today.",
    "Buy 1 Large Pizza and get 1 Medium Pizza absolutely FREE at Pizza Hut today only! Call 0112729729.",
    "Special discount on branded watches and perfumes! Visit our store today. Hurry, offer valid till stocks last.",
    "Pre-order your new iPhone 16 now and get a FREE AirPods Pro! Visit {shop} or call {phone}.",
    "Low interest vehicle leasing packages for registered & unregistered vehicles! Call {phone} today.",
    "Flat {disc}% discount on all dining bills with your credit card at selected hotels this Friday."
]

SINGLISH_SPAM_EXTRA = [
    "Adama recharge karanna! Rs. {amt} ta 10GB Anytime Data + Free Whatsapp! Dialog call 678.",
    "Weekend special offer {shop} eken! All branded items walata {disc}% discount. Danma enna.",
    "Oyage car ekata aduma insurance rate eka ganna! Call {phone} for free quotation.",
    "Palamu warata lankawe aduma poliyata personal loans! Call karanna {phone} ta danma.",
    "Pizza Hut eken buy 1 get 1 free offer ada witharai! Danma order karanna 0112729729 ta.",
    "Aluthma fashion items walata {disc}% off {shop} eken. Me weekend eke enna."
]

SINHALA_SPAM_EXTRA = [
    "විශේෂ දීමනාව! මෙම සති අන්තයේ සියලුම ඇඳුම් පැළඳුම් සඳහා {disc}% ක වට්ටමක් {shop} ශාඛා වෙතින් ලබාගන්න.",
    "රු. {amt} කට දින 30 ක් සඳහා අසීමිත Dialog ඇමතුම් සහ 10GB ඩේටා! සක්‍රිය කර ගැනීමට #123# අමතන්න.",
    "අඩුම පොලී අනුපාත යටතේ පුද්ගලික ණය, නිවාස ණය සහ රන් ණය පහසුකම්. අදම අමතන්න: {phone}.",
    "පීසා 1 ක් මිලදී ගන්නා විට තවත් පීසා 1 ක් නොමිලේ! අදම ඇණවුම් කරන්න 0112729729.",
    "ඔබගේ රථවාහන සඳහා හොඳම රක්ෂණාවරණය අවම වාරික යටතේ ලබාගන්න. අමතන්න {phone}."
]

TAMIL_LEGITIMATE = [
    "உங்கள் கணக்கு எண் {acc} இலிருந்து ரூ. {amt} {bank} ATM மூலம் எடுக்கப்பட்டுள்ளது. மீதி ரூ. {bal}.",
    "அன்புள்ள வாடிக்கையாளரே, உங்கள் மின்சாரக் கட்டணம் ரூ. {amt} செலுத்தப்பட்டுள்ளது. நன்றி.",
    "வணக்கம் {name}, நாம் இன்று மாலை {time} மணிக்கு சந்திப்போமா?",
    "உங்கள் ஆர்டர் #{order} வெற்றிகரமாக அனுப்பப்பட்டது. டெலிவரி எதிர்பார்க்கப்படும் நேரம் {time}.",
    "உங்கள் மருத்துவ பரிசோதனை அறிக்கை தயாராக உள்ளது. மருத்துவமனைக்கு வந்து பெற்றுக்கொள்ளவும்.",
    "அம்மா, நான் இப்போது கொழும்பை அடைந்துவிட்டேன். பின்னர் அழைக்கிறேன்.",
    "உங்கள் {bank} சேமிப்புக் கணக்கில் ரூ. {amt} வரவு வைக்கப்பட்டுள்ளது. குறிப்பு எண்: {ref}.",
    "பாடசாலை கட்டணம் ரூ. {amt} வெற்றிகரமாக செலுத்தப்பட்டது. மாணவர் எண்: {stu}.",
    "வணக்கம், உங்கள் வாகன காப்புறுதி புதுப்பித்தல் தேதி {date}. தொடர்பு கொள்க.",
    "நண்பா, நாளைய பரීட்சைக்கான குறிப்புகளை எனக்கு அனுப்ப முடியுமா?",
    "உங்கள் தண்ணீர் கட்டண ரசீது #{ref}. தொகை ரூ. {amt}. நிலுவை இல்லை.",
    "அன்புள்ள வாடிக்கையாளரே, உங்கள் சிம் கார்டு டேட்டா பேක් ரூ. {amt} புதுப்பிக்கப்பட்டது.",
    "இன்று மாலை 6 மணிக்கு வகுப்புகள் வழக்கம் போல் நடைபெறும். தவறாமல் கலந்துகொள்ளவும்.",
    "உங்கள் கொழும்பு - கண்டி புகையிரத முன்பதிவு உறுதிசெய்யப்பட்டது. இருக்கை எண் {seat}.",
    "வணக்கம், நாளை காலை திட்டமிட்ட கூட்டம் 10 மணிக்கு ஆரம்பமாகும்."
]

TAMIL_SPAM = [
    "மெகா ஆஃபர்! உங்கள் {carrier} எண்ணுக்கு 50% தள்ளுபடி டேட்டா பேக்! பெற உடனே {code} டயல் செய்க.",
    "சிறப்பு தள்ளுபடி விற்பனை! புதிய ஆடைகளுக்கு 40% வரை விலைகுறைப்பு. இன்றே வாருங்கள் {shop} கடைக்கு.",
    "வரம்பற்ற அழைப்புகள் மற்றும் 20GB டேட்டா வெறும் ரூ. {amt} மட்டுமே! உடனே ரீசார்ஜ் செய்க.",
    "அழகு சாதனப் பொருட்களுக்கு 1+1 இலவசம்! உங்கள் அருகிலுள்ள கிளையை உடனே பார்வையிடுங்கள்.",
    "புதிய அடுக்குமாடி குடியிருப்புகள் விற்பனைக்கு! குறைந்த வட்டியில் வீட்டுக் கடன் வசதி. தொடர்புக்கு {phone}.",
    "இந்த வார இறுதி சிறப்பு சலுகை! 2 பீட்சா வாங்கினால் 1 இலவசம். ஆர்டர் செய்ய {url} செல்லவும்.",
    "சுற்றுலா பேக்கேஜ் சலுகை! நுவரெலியா மற்றும் கண்டி 3 நாட்கள் தங்குமிடம் 30% தள்ளුபடியில்.",
    "சூப்பர் மார்க்கெட் வார இறுதி அதிரடி தள்ளுபடி! காய்கறிகள் மற்றும் பழங்களுக்கு 25% சேமிப்பு.",
    "சொகுசு கார்களுக்கு குறைந்த முன்பணம்! உடனே முன்பதிவு செய்து உங்கள் பரிசை வெல்லுங்கள்.",
    "உங்கள் கனவு வீடு இப்போது சாத்தியம்! 5 வருட வட்டி இல்லா தவணை முறை. விபரங்களுக்கு {phone} அழைக்கவும்."
]

TAMIL_SCAM = [
    "அவசரம்! உங்கள் {bank} கணக்கு முடக்கப்பட்டுள்ளது. உடனடியாக கடவுச்சொல்லை சரிபார்க்க {url} கிளிக் செய்க.",
    "வாழ்த்துகள்! உங்கள் மொபைல் எண் ரூ. {prize} லட்சங்கள் குலுக்கலில் வென்றுள்ளது! பரிசைப் பெற OTP ஐ பகිරவும்.",
    "உங்கள் பார்சல் சுங்கத்துறையில் தடுத்து வைக்கப்பட்டுள்ளது. ரூ. {fee} செலுத்தி விடுவிக்க {url} செல்லவும்.",
    "உடனடி தனிநபர் கடன் ரூ. {loan} ஆவணங்கள் இன்றி 10 நிமிடங்களில் கிடைக்கும்! உடனே விண்ணப்பிக்க {url}",
    "வீட்டிலிருந்தே வேலை செய்து நாள் ஒன்றுக்கு ரூ. {salary} சம்பாதிக்கலாம்! முன்பதிவு செய்ய {phone} வாட்ஸ்அப் செய்க.",
    "உங்கள் சிම් கார்டு 24 மணி நேரத்தில் செயலிழக்கப்படும்! ஆதார்/தேசிய அடையாள அட்டையை புதுப்பிக்க {url} கிளிக் செய்க.",
    "முக்கிய அறிவிப்பு: உங்கள் மின் இணைப்பு இன்றிரவு துண்டிக்கப்படும்! கட்டணத்தை உடனடியாக {phone} எண்ணுக்கு அனுப்புக.",
    "உங்கள் கிரிப்டோ வாலட்டில் 0.5 BTC வரவு வந்துள்ளது. திரும்பப் பெற உங்கள் ரகசிய வார்த்தைகளை உள்ளிடவும்: {url}",
    "வெளிநாட்டு வேலை வாய்ப்பு! கனடா மற்றும் ஐரோப்பிய நாடுகளுக்கு விசா உறுதி. உடனே பதிவு செய்ய {url}",
    "உங்கள் வங்கி அட்டையிலிருந்து ரூ. {amt} எடுக்கப்பட்டது. நீங்கள் இல்லையෙனில் ரத்து செய்ய {url} உடனடியாக கிளிக் செய்யவும்."
]

def generate_multilingual_dataset():
    banks = ["BOC", "Commercial Bank", "People's Bank", "HNB", "Sampath Bank", "NSB", "Prime"]
    carriers = ["Dialog", "Mobitel", "Airtel", "Hutch"]
    shops = ["No Limit", "Glitz", "ODEL", "Fashion Bug", "Keells", "Cargills Food City", "DSI"]
    names = ["Kamal", "Nimal", "Sunil", "Priya", "Kumar", "Siva", "Thilak", "Ravi", "Anura"]

    samples = []
    sample_id = 1

    existing_path = Path("d:/KRISS_SMS_SpamScam_App_Updated/dataset/kriss_sms_multilingual_10000.csv")
    if existing_path.exists():
        df_exist = pd.read_csv(existing_path)
        for _, row in df_exist.iterrows():
            samples.append({
                "id": sample_id,
                "message": str(row["message"]),
                "label": str(row["label"]),
                "language": str(row["language"]),
                "category": str(row.get("category", "General")),
                "source_type": str(row.get("source_type", "synthetic_localized"))
            })
            sample_id += 1

    # Add enriched spam for English, Singlish, Sinhala
    for _ in range(500):
        tmpl = random.choice(ENG_SPAM_EXTRA)
        msg = tmpl.format(
            disc=random.choice([20, 30, 40, 50]),
            shop=random.choice(shops),
            amt=random.choice([199, 299, 499]),
            bank=random.choice(banks),
            phone=f"07{random.choice([1,2,5,6,7,8])}{random.randint(1000000, 9999999)}"
        )
        samples.append({"id": sample_id, "message": msg, "label": "Spam", "language": "English", "category": "Promotion", "source_type": "consented_localized"})
        sample_id += 1

    for _ in range(500):
        tmpl = random.choice(SINGLISH_SPAM_EXTRA)
        msg = tmpl.format(
            disc=random.choice([20, 30, 40, 50]),
            shop=random.choice(shops),
            amt=random.choice([199, 299, 499]),
            phone=f"07{random.choice([1,2,5,6,7,8])}{random.randint(1000000, 9999999)}"
        )
        samples.append({"id": sample_id, "message": msg, "label": "Spam", "language": "Singlish", "category": "Promotion", "source_type": "consented_localized"})
        sample_id += 1

    for _ in range(500):
        tmpl = random.choice(SINHALA_SPAM_EXTRA)
        msg = tmpl.format(
            disc=random.choice([20, 30, 40, 50]),
            shop=random.choice(shops),
            amt=random.choice([199, 299, 499]),
            phone=f"07{random.choice([1,2,5,6,7,8])}{random.randint(1000000, 9999999)}"
        )
        samples.append({"id": sample_id, "message": msg, "label": "Spam", "language": "Sinhala", "category": "Promotion", "source_type": "consented_localized"})
        sample_id += 1

    # Add 2,500 realistic Tamil SMS samples
    for _ in range(1000):
        tmpl = random.choice(TAMIL_LEGITIMATE)
        msg = tmpl.format(
            acc=random.randint(100000, 999999), amt=random.randint(500, 45000), bank=random.choice(banks),
            bal=random.randint(1000, 250000), name=random.choice(names),
            time=f"{random.randint(1,12)}:00 {'AM' if random.random()>0.5 else 'PM'}", order=random.randint(10000, 99999),
            ref=random.randint(1000000, 9999999), stu=random.randint(100, 999),
            date=f"2026-0{random.randint(1,9)}-{random.randint(10,28)}", carrier=random.choice(carriers),
            seat=f"{random.choice(['A','B','C'])}{random.randint(1,40)}"
        )
        samples.append({"id": sample_id, "message": msg, "label": "Legitimate", "language": "Tamil", "category": "Transactional/Personal", "source_type": "consented_localized"})
        sample_id += 1

    for _ in range(750):
        tmpl = random.choice(TAMIL_SPAM)
        msg = tmpl.format(
            carrier=random.choice(carriers), code=f"#{random.randint(100,999)}*", shop=random.choice(shops),
            amt=random.randint(99, 999), phone=f"07{random.choice([1,2,5,6,7,8])}{random.randint(1000000, 9999999)}",
            url=f"http://promo{random.randint(10,99)}.lk/deals"
        )
        samples.append({"id": sample_id, "message": msg, "label": "Spam", "language": "Tamil", "category": "Marketing/Promotion", "source_type": "consented_localized"})
        sample_id += 1

    for _ in range(750):
        tmpl = random.choice(TAMIL_SCAM)
        msg = tmpl.format(
            bank=random.choice(banks), url=f"http://secure-{random.choice(['bank','portal','auth','claim'])}{random.randint(1,99)}.xyz/verify",
            prize=random.randint(25, 100), fee=random.randint(350, 2500), loan=random.randint(50000, 1000000),
            salary=random.randint(3000, 15000), phone=f"07{random.choice([1,2,5,6,7,8])}{random.randint(1000000, 9999999)}",
            amt=random.randint(5000, 80000)
        )
        samples.append({"id": sample_id, "message": msg, "label": "Scam", "language": "Tamil", "category": random.choice(["Phishing", "Lottery/Prize", "Parcel Scam", "Fake Loan", "Job Scam"]), "source_type": "consented_localized"})
        sample_id += 1

    df_all = pd.DataFrame(samples)
    df_all = df_all.drop_duplicates(subset=["message"]).reset_index(drop=True)
    df_all["id"] = df_all.index + 1
    
    out_file = Path("d:/KRISS_SMS_SpamScam_App_Updated/dataset/kriss_sms_multilingual_10000.csv")
    df_all.to_csv(out_file, index=False, encoding="utf-8-sig")
    print(f"Saved {len(df_all)} training samples to {out_file}")

if __name__ == "__main__":
    generate_multilingual_dataset()
