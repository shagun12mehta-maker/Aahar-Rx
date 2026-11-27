"""Elderly-friendly trilingual (EN / HI / MR) voice script builder and TTS synthesizer."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

VOICE_PROFILES: dict[str, dict[str, str]] = {
    "en": {"voice": "en-IN-NeerjaNeural", "locale": "en-IN", "rate": "-12%", "pitch": "+0Hz"},
    "hi": {"voice": "hi-IN-SwaraNeural", "locale": "hi-IN", "rate": "-12%", "pitch": "+0Hz"},
    "mr": {"voice": "mr-IN-AarohiNeural", "locale": "mr-IN", "rate": "-12%", "pitch": "+0Hz"},
}

# Respectful, unhurried, clear phrasing designed specifically for elderly Indian listeners.
_RULE_VOICE_SCRIPTS: dict[str, dict[str, str]] = {
    "RULE-THY-001": {
        "en": (
            "Namaste. You are taking Levothyroxine for thyroid care. "
            "Please take your tablet with plain lukewarm water on an empty stomach, and wait 1 hour before having masala chai with milk or curd. "
            "You can enjoy black lemon water right after the waiting window. Do not stop or change your tablet dose without asking your doctor."
        ),
        "hi": (
            "नमस्ते। आप थायरॉइड के लिए लेवोथायरोक्सिन की गोली ले रहे हैं। "
            "कृपया यह गोली सुबह खाली पेट सादे गुनगुने पानी से लें और दूध वाली चाय या दही लेने से पहले कम से कम 1 घंटे का अंतर रखें। "
            "आप हल्का नींबू पानी सुरक्षित विकल्प के रूप में ले सकते हैं। डॉक्टर की सलाह के बिना अपनी दवा बंद न करें।"
        ),
        "mr": (
            "नमस्कार. आपण थायरॉइडसाठी लेव्होथायरॉक्सिन गोळी घेत आहात. "
            "कृपया ही गोळी सकाळी उपाशी पोटी कोमट पाण्यासोबत घ्या आणि दुधाचा चहा किंवा दही घेण्यापूर्वी किमान 1 तास थांबा. "
            "त्याऐवजी कोमट लिंबू पाणी हा सुरक्षित पर्याय आहे. डॉक्टरांच्या सल्ल्याशिवाय गोळी बंद करू नका."
        ),
    },
    "RULE-IRO-002": {
        "en": (
            "Namaste. To help your body absorb your iron supplement properly, avoid masala chai, filter coffee, or palak paneer for 1 hour before and 2 hours after your tablet. "
            "Taking freshly squeezed nimbu pani or amla juice helps iron absorb well. Never alter your prescribed dose without medical advice."
        ),
        "hi": (
            "नमस्ते। आयरन की गोली का पूरा असर मिलने के लिए गोली लेने से 1 घंटे पहले और 2 घंटे बाद तक चाय, कॉफ़ी या पालक पनीर न लें। "
            "इसके बदले ताज़ा नींबू पानी या आंवला रस लेना शरीर में आयरन बढ़ाने में मदद करता है। अपनी दवा की मात्रा बिना सलाह न बदलें।"
        ),
        "mr": (
            "नमस्कार. आयर्नच्या गोळीचा पूर्ण फायदा मिळण्यासाठी गोळीपूर्वी 1 तास आणि नंतर 2 तास चहा, कॉफी किंवा पालक पनीर टाळा. "
            "ताजे लिंबू पाणी किंवा आवळा रस घेतल्यास शरीरात लोह चांगले शोषले जाते. डॉक्टरांच्या सल्ल्याशिवाय औषध बदलू नका."
        ),
    },
    "RULE-ANT-003": {
        "en": (
            "Namaste. Milk, chaas, curd, and paneer can block Ciprofloxacin antibiotic absorption by nearly half. "
            "Keep a 2-hour gap before dairy foods and 4 hours after dairy foods when taking this tablet. Fresh jaljeera or clear soup is a safe meal drink. Consult your doctor before any dose change."
        ),
        "hi": (
            "नमस्ते। दूध, छाछ, दही और पनीर जैसी चीज़ें सिप्रोफ़्लॉक्सासिन एंटीबायोटिक के असर को आधा कर सकती हैं। "
            "कृपया डेयरी आहार से 2 घंटे पहले या 4 घंटे बाद यह दवा लें। भोजन के साथ जीरा पानी या सादा सूप सुरक्षित विकल्प है।"
        ),
        "mr": (
            "नमस्कार. दूध, ताक, दही आणि पनीर यामुळे सिप्रोफ्लॉक्सासिन अँटीबायोटिकचा परिणाम निम्मा होऊ शकतो. "
            "कृपया दुग्धजन्य पदार्थांपासून 2 तास आधी किंवा 4 तासांनंतर ही गोळी घ्या. त्याऐवजी जिरे पाणी किंवा सूप सुरक्षित आहे."
        ),
    },
    "RULE-BLD-004": {
        "en": (
            "Namaste. Warfarin requires steady daily Vitamin K levels. Sudden heavy portions of sarson ka saag, palak, methi, or thick coriander chutney can lower medicine protection. "
            "Bottle gourd or lauki, ridge gourd, and bhindi are safer steady vegetables. Never skip your prescribed tablet."
        ),
        "hi": (
            "नमस्ते। वारफ़रिन दवा के साथ विटामिन के की मात्रा संतुलित रखना ज़रूरी है। अचानक अधिक सरसों का साग, पालक, मेथी या हरी चटनी खाने से दवा का असर कम हो सकता है। "
            "लौकी, तोरी या भिंडी की सब्ज़ी सुरक्षित विकल्प हैं। कृपया अपनी नियमित दवा समय पर जारी रखें।"
        ),
        "mr": (
            "नमस्कार. वारफरीन औषध सुरू असताना आहारातील व्हिटॅमिन के स्थिर ठेवणे गरजेचे असते. अचानक भरपूर मोहरीचे साग, पालक, मेथी किंवा कोथिंबीर चटणी खाल्ल्यास औषधाचा परिणाम कमी होऊ शकतो. "
            "दुधी भोपळा, दोडका किंवा भेंडी ही सुरक्षित भाज्या आहेत. डॉक्टरांशिवाय गोळी बंद करू नका."
        ),
    },
    "RULE-HTN-005": {
        "en": (
            "Namaste. For Amlodipine blood pressure care, please avoid concentrated mosambi sweet lime juice or pomelo close to your dose, as they can raise blood pressure medicine levels sharply. "
            "Fresh coconut water or apple slices are gentle, safe choices. Always follow your physician's dose instructions."
        ),
        "hi": (
            "नमस्ते। ब्लड प्रेशर की दवा एमलोडिपिन के साथ बड़ा गिलास मौसंबी जूस या चकोतरा लेने से बचें, क्योंकि इससे शरीर में दवा की मात्रा अचानक बढ़ सकती है। "
            "ताज़ा नारियल पानी या सेब के टुकड़े सुरक्षित विकल्प हैं। अपने डॉक्टर के निर्देशानुसार ही दवा लेते रहें।"
        ),
        "mr": (
            "नमस्कार. रक्तदाबाच्या अ‍ॅम्लोडिपिन गोळीसोबत मोसंबीचा जास्त रस किंवा पपई-सदृश चकोतरा घेणे टाळा, कारण त्यामुळे शरीरात औषधाचे प्रमाण अचानक वाढू शकते. "
            "ताजे नारळ पाणी किंवा सफरचंदाचे काप सुरक्षित पर्याय आहेत. डॉक्टरांच्या सल्ल्यानेच औषध घ्या."
        ),
    },
    "RULE-DIA-006": {
        "en": (
            "Namaste. Take your Metformin tablet during or immediately after a balanced high-fiber meal such as dal, sabzi, and roti to protect your stomach from discomfort. "
            "Avoid sweet syrup desserts like gulab jamun and sugary tea around dose time. Never skip prescribed diabetes medication without checking with your doctor."
        ),
        "hi": (
            "नमस्ते। पेट में जलन या मरोड़ से बचने के लिए मेटफ़ॉर्मिन की गोली खाली पेट न लेकर दाल, सब्ज़ी और रोटी के भोजन के बीच या तुरंत बाद लें। "
            "गुलाब जामुन, जलेबी या मीठी चाय से बचें। डॉक्टर से पूछे बिना अपनी दवा बंद न करें।"
        ),
        "mr": (
            "नमस्कार. पोटाचा त्रास टाळण्यासाठी मेटफॉर्मिन गोळी उपाशी पोटी न घेता डाळ, भाजी आणि पोळीच्या जेवणादरम्यान किंवा लगेच नंतर घ्या. "
            "गुलाबजाम किंवा अतिगोड चहा टाळा. डॉक्टरांच्या सल्ल्याशिवाय गोळी बंद करू नका."
        ),
    },
    "RULE-HYP-007": {
        "en": (
            "Namaste. Telmisartan protects blood pressure by conserving potassium, so avoid potassium-based low-sodium salt substitutes like sendha namak blends and do not drink multiple tender coconuts daily. "
            "Standard iodized salt in small moderation and plain spiced chaas without extra salt are safer choices."
        ),
        "hi": (
            "नमस्ते। टेल्मिसार्टन दवा लेते समय अधिक पोटैशियम वाले लो-सोडियम नमक या दिन में कई नारियल पानी पीने से सावधान रहें। "
            "सीमित मात्रा में सामान्य आयोडीन नमक और बिना अतिरिक्त नमक वाला सादा छाछ बेहतर विकल्प हैं। अपनी दवा बिना डॉक्टर की सलाह न बदलें।"
        ),
        "mr": (
            "नमस्कार. टेल्मिसार्टन औषध सुरू असताना पोटॅशियम असलेले लो-सोडियम मीठ किंवा दिवसातून अनेक वेळा नारळ पाणी पिणे टाळावे. "
            "मर्यादित प्रमाणात साधे आयोडीनयुक्त मीठ आणि मीठ न घातलेले ताक हा सुरक्षित पर्याय आहे. डॉक्टरांशिवाय औषध बदलू नका."
        ),
    },
    "RULE-LIP-008": {
        "en": (
            "Namaste. For Atorvastatin cholesterol care, avoid concentrated citrus juice and repeatedly heated deep-fried snacks like market samosas or pakoras near bedtime or dose time. "
            "Roasted makhana or boiled chana chaat keeps your lipid plan safe. Continue your prescribed dose unless advised otherwise by your doctor."
        ),
        "hi": (
            "नमस्ते। कोलेस्ट्रॉल की दवा एटोरवास्टेटिन के साथ गाढ़े खट्टे जूस और बार-बार तले हुए समोसे या पकौड़े खाने से बचें। "
            "भुना मखाना या उबले चने की चाट एक सुरक्षित और स्वास्थ्यवर्धक विकल्प है। डॉक्टर की सलाह के बिना दवा न रोकें।"
        ),
        "mr": (
            "नमस्कार. कोलेस्ट्रॉलच्या अ‍ॅटोर्वास्टॅटिन गोळीसोबत कडवट लिंबूवर्गीय रस आणि बाहेरचे तळलेले समोसे किंवा भजी खाणे टाळा. "
            "भाजलेले मखाने किंवा उकडलेल्या चण्याची चाट हा सुरक्षित पर्याय आहे. डॉक्टरांच्या सल्ल्याशिवाय गोळी बंद करू नका."
        ),
    },
}

_UX_ALERT_SCRIPTS: dict[str, dict[str, str]] = {
    "ALERT-HIGH-RISK": {
        "en": (
            "Attention. A high priority food-drug interaction clash has been detected. "
            "Please tap Consult Doctor Now to share your report with explicit consent. "
            "Only your doctor can adjust a prescribed medicine dose."
        ),
        "hi": (
            "कृपया ध्यान दें। दवा और भोजन के बीच उच्च सावधानी वाला टकराव मिला है। "
            "सुरक्षित सलाह के लिए डॉक्टर से अभी बात करें बटन चुनें। दवा की मात्रा केवल डॉक्टर ही बदल सकते हैं।"
        ),
        "mr": (
            "कृपया लक्ष द्या. औषध आणि अन्न यामध्ये उच्च दक्षतेचा अडथळा आढळला आहे. "
            "योग्य सल्ल्यासाठी डॉक्टरांशी आत्ताच बोला हा पर्याय निवडा. औषधाची मात्रा फक्त डॉक्टरच बदलू शकतात."
        ),
    },
    "ALERT-REFILL": {
        "en": (
            "Medicine refill reminder. One of your daily medicines in the Medicine Box has 3 days or fewer remaining. "
            "Please reorder a fresh strip on time via 1mg or PharmEasy so your treatment continues smoothly."
        ),
        "hi": (
            "दवा रिफ़िल सूचना। आपके दवा बॉक्स की एक नियमित दवा केवल 3 दिन या उससे कम बची है। "
            "समय पर नई पट्टी मंगवाने के लिए 1mg या PharmEasy का विकल्प उपयोग करें।"
        ),
        "mr": (
            "औषध साठा सूचना. तुमच्या औषध बॉक्समधील एक नियमित औषध 3 दिवस किंवा त्यापेक्षा कमी शिल्लक आहे. "
            "वेळेवर नवीन पाकीट मागवण्यासाठी 1mg किंवा PharmEasy पर्याय वापरा."
        ),
    },
}


def build_ux_alert_voice_scripts() -> dict[str, dict[str, Any]]:
    """Build EN/HI/MR elderly audio script metadata for Consult Doctor Now & Refill alerts."""
    alerts: dict[str, dict[str, Any]] = {}
    for aid, lang_texts in _UX_ALERT_SCRIPTS.items():
        row: dict[str, Any] = {"rule_id": aid, "languages": {}}
        for lang, profile in VOICE_PROFILES.items():
            text = lang_texts[lang]
            row["languages"][lang] = {
                "text": text,
                "voice_name": profile["voice"],
                "locale": profile["locale"],
                "rate": profile["rate"],
                "audio_rel_path": f"audio/{lang}/{aid}.mp3",
                "estimated_seconds": round(max(6.0, len(text.split()) / 2.1), 1),
            }
        alerts[aid] = row
    return alerts


def build_voice_scripts_for_rules(rules: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Build deterministic EN/HI/MR elderly voice script metadata keyed by rule_id."""
    scripts: dict[str, dict[str, Any]] = {}
    for rule in rules:
        rid = rule["rule_id"]
        if rid not in _RULE_VOICE_SCRIPTS:
            raise KeyError(f"Missing trilingual voice script for rule {rid}")
        row: dict[str, Any] = {
            "rule_id": rid,
            "drug_class": rule["drug_class"],
            "active_salts": list(rule["active_salts"]),
            "languages": {},
        }
        for lang, profile in VOICE_PROFILES.items():
            text = _RULE_VOICE_SCRIPTS[rid][lang]
            row["languages"][lang] = {
                "text": text,
                "voice_name": profile["voice"],
                "locale": profile["locale"],
                "rate": profile["rate"],
                "audio_rel_path": f"audio/{lang}/{rid}.mp3",
                "estimated_seconds": round(max(6.0, len(text.split()) / 2.1), 1),
            }
        scripts[rid] = row
    return scripts


async def _synthesize_all_async(
    scripts: dict[str, dict[str, Any]],
    output_root: Path,
    overwrite: bool = False,
) -> list[dict[str, Any]]:
    import edge_tts

    generated: list[dict[str, Any]] = []
    for rid, item in scripts.items():
        for lang, meta in item["languages"].items():
            target = output_root / meta["audio_rel_path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            if overwrite or not target.exists() or target.stat().st_size < 1024:
                communicator = edge_tts.Communicate(
                    text=meta["text"],
                    voice=meta["voice_name"],
                    rate=meta["rate"],
                    pitch=VOICE_PROFILES[lang]["pitch"],
                )
                await communicator.save(str(target))
            generated.append(
                {
                    "rule_id": rid,
                    "lang": lang,
                    "voice": meta["voice_name"],
                    "file": str(target),
                    "bytes": target.stat().st_size,
                }
            )
    return generated


def synthesize_voice_assets(
    rules: list[dict[str, Any]],
    output_root: Path,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Synthesize elderly-friendly EN/HI/MR MP3 clips via edge-tts neural voices."""
    scripts = build_voice_scripts_for_rules(rules)
    ux_alerts = build_ux_alert_voice_scripts()
    combined = {**scripts, **ux_alerts}
    records = asyncio.run(_synthesize_all_async(combined, output_root=output_root, overwrite=overwrite))
    return {"scripts": scripts, "ux_alerts": ux_alerts, "audio_files": records}
