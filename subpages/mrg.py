# unified_astrology_pro_app.py
"""
حاسبة التنجيم الفلكي الشاملة والمتكاملة للزواج والحمل والإنجاب (100 دلالة فلكية تخصصية)
وفقاً للتنجيم الغربي، عودة الشمس (Solar Return)، ونقاط المنتصف والمحاور (Midpoints Axis) واشتقاق البيوت.
إعداد وتطوير: الفلكي الدكتور استرو رادار.
"""

import streamlit as st
import swisseph as swe
import datetime
import pytz
from timezonefinder import TimezoneFinder
import geonamescache
import os

# =============================================================================
# إعدادات Swiss Ephemeris
# =============================================================================
swe.set_ephe_path('')  # استخدام وضع Moshier الافتراضي للتقويم الفلكي الدقيق

# =============================================================================
# 1. إعدادات الصفحة والتنسيق البصري العربي الاحترافي (RTL)
# =============================================================================
st.set_page_config(
    page_title="حاسبة سنوات الزواج والحمل والإنجاب الفلكية",
    layout="wide",
    page_icon="🔮"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&family=Amiri:wght@700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif;
        direction: rtl;
        text-align: right;
    }
    
    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #1a2a44 0%, #0d1b2a 100%);
        color: #ffffff;
        font-weight: 800;
        font-size: 17px;
        padding: 12px;
        border-radius: 10px;
        border: 1px solid #c59b27;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #c59b27 0%, #a17c18 100%);
        color: #0f172a;
        border-color: #ffd700;
        box-shadow: 0 4px 15px rgba(197, 155, 39, 0.4);
    }
    .main-header {
        text-align: center;
        background: linear-gradient(135deg, #0d1b2a 0%, #1b263b 100%);
        color: #f1f5f9;
        padding: 24px;
        border-radius: 12px;
        border: 2px solid #c59b27;
        margin-bottom: 25px;
    }
    .main-header h1 {
        font-family: 'Amiri', serif;
        color: #e6ca65;
        font-size: 28px;
        margin-bottom: 6px;
        font-weight: 700;
    }
    .info-card {
        background: #ffffff;
        border-right: 5px solid #c59b27;
        border-radius: 8px;
        padding: 18px 22px;
        margin-bottom: 20px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        border: 1px solid #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 2. الثوابت والمعاجم الفلكية
# =============================================================================
ZODIAC_SIGNS = [
    {"id": 0, "name_ar": "الحمل", "name_en": "Aries", "element": "ناري", "modality": "منقلب", "ruler": "Mars", "exaltation": "Sun"},
    {"id": 1, "name_ar": "الثور", "name_en": "Taurus", "element": "ترابي", "modality": "ثابت", "ruler": "Venus", "exaltation": "Moon"},
    {"id": 2, "name_ar": "الجوزاء", "name_en": "Gemini", "element": "هوائي", "modality": "متبدل", "ruler": "Mercury", "exaltation": "Rahu"},
    {"id": 3, "name_ar": "السرطان", "name_en": "Cancer", "element": "مائي", "modality": "منقلب", "ruler": "Moon", "exaltation": "Jupiter"},
    {"id": 4, "name_ar": "الأسد", "name_en": "Leo", "element": "ناري", "modality": "ثابت", "ruler": "Sun", "exaltation": "None"},
    {"id": 5, "name_ar": "العذراء", "name_en": "Virgo", "element": "ترابي", "modality": "متبدل", "ruler": "Mercury", "exaltation": "Mercury"},
    {"id": 6, "name_ar": "الميزان", "name_en": "Libra", "element": "هوائي", "modality": "منقلب", "ruler": "Venus", "exaltation": "Saturn"},
    {"id": 7, "name_ar": "العقرب", "name_en": "Scorpio", "element": "مائي", "modality": "ثابت", "ruler": "Mars", "modern_ruler": "Pluto", "exaltation": "Uranus"},
    {"id": 8, "name_ar": "القوس", "name_en": "Sagittarius", "element": "ناري", "modality": "متبدل", "ruler": "Jupiter", "exaltation": "Ketu"},
    {"id": 9, "name_ar": "الجدي", "name_en": "Capricorn", "element": "ترابي", "modality": "منقلب", "ruler": "Saturn", "exaltation": "Mars"},
    {"id": 10, "name_ar": "الدلو", "name_en": "Aquarius", "element": "هوائي", "modality": "ثابت", "ruler": "Saturn", "modern_ruler": "Uranus", "exaltation": "None"},
    {"id": 11, "name_ar": "الحوت", "name_en": "Pisces", "element": "مائي", "modality": "متبدل", "ruler": "Jupiter", "modern_ruler": "Neptune", "exaltation": "Venus"}
]

ZODIAC_NAMES_AR = [z["name_ar"] for z in ZODIAC_SIGNS]

SIGN_RULERS = {
    0: "Mars", 1: "Venus", 2: "Mercury", 3: "Moon",
    4: "Sun", 5: "Mercury", 6: "Venus", 7: "Mars",
    8: "Jupiter", 9: "Saturn", 10: "Saturn", 11: "Jupiter"
}

MODERN_SIGN_RULERS = {
    0: "Mars", 1: "Venus", 2: "Mercury", 3: "Moon",
    4: "Sun", 5: "Mercury", 6: "Venus", 7: "Pluto",
    8: "Jupiter", 9: "Saturn", 10: "Uranus", 11: "Neptune"
}

PLANET_NAMES_AR = {
    "Sun": "الشمس",
    "Moon": "القمر",
    "Mercury": "عطارد",
    "Venus": "الزهرة",
    "Mars": "المريخ",
    "Jupiter": "المشتري",
    "Saturn": "زحل",
    "Uranus": "أورانوس",
    "Neptune": "نبتون",
    "Pluto": "بلوتو",
    "Rahu": "راهو (العقدة الشمالية)",
    "Ketu": "كيتو (العقدة الجنوبية)"
}

PLANET_IDS = {
    'Sun': swe.SUN, 'Moon': swe.MOON, 'Mercury': swe.MERCURY, 
    'Venus': swe.VENUS, 'Mars': swe.MARS, 'Jupiter': swe.JUPITER, 
    'Saturn': swe.SATURN, 'Uranus': swe.URANUS, 'Neptune': swe.NEPTUNE, 
    'Pluto': swe.PLUTO, 'Rahu': swe.TRUE_NODE
}

# =============================================================================
# 3. محرك البيانات الجغرافية والحسابات الفلكية الأساسية
# =============================================================================
@st.cache_data
def load_geo_data():
    gc = geonamescache.GeonamesCache()
    countries = gc.get_countries()
    cities = gc.get_cities()
    country_map = {c['name']: code for code, c in countries.items()}
    sorted_countries = sorted(list(country_map.keys()))
    cities_by_country = {}
    for c_code in country_map.values():
        c_cities = [city for city in cities.values() if city['countrycode'] == c_code]
        c_cities_sorted = sorted(c_cities, key=lambda x: x['population'], reverse=True)
        cities_by_country[c_code] = c_cities_sorted
    return gc, country_map, sorted_countries, cities_by_country

gc, country_map, country_list, cities_by_country = load_geo_data()
tf = TimezoneFinder()

def get_utc_julian_day(date_obj, time_obj, tz_str):
    local_tz = pytz.timezone(tz_str)
    dt = datetime.datetime.combine(date_obj, time_obj)
    local_dt = local_tz.localize(dt)
    utc_dt = local_dt.astimezone(pytz.utc)
    return swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour + utc_dt.minute/60.0 + utc_dt.second/3600.0)

def find_exact_solar_return(target_year, natal_sun_lon, birth_month, birth_day, birth_time, b_tz):
    guess_dt = datetime.datetime(target_year, birth_month, birth_day, birth_time.hour, birth_time.minute)
    local_tz = pytz.timezone(b_tz)
    utc_dt = local_tz.localize(guess_dt).astimezone(pytz.utc)
    jd_guess = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour + utc_dt.minute/60.0)
    
    for _ in range(20):
        sun_lon = swe.calc_ut(jd_guess, swe.SUN)[0][0]
        diff = (natal_sun_lon - sun_lon)
        if diff > 180: diff -= 360
        if diff < -180: diff += 360
        jd_guess += diff / 0.985647
        if abs(diff) < 0.000001:
            break
    return jd_guess

def angular_diff(lon1, lon2):
    diff = abs(lon1 - lon2) % 360
    return min(diff, 360 - diff)

def is_aspect(lon1, lon2, target_angle, orb=1.0):
    dist = angular_diff(lon1, lon2)
    diff_from_target = abs(dist - target_angle)
    return diff_from_target <= orb, diff_from_target

def is_soft_or_conjunction(lon1, lon2, orb=1.0):
    for angle in [0, 60, 120]:
        matched, diff = is_aspect(lon1, lon2, angle, orb)
        if matched:
            name = "اقتران" if angle == 0 else ("تسديس" if angle == 60 else "تثليث")
            return True, name, diff
    return False, None, 0.0

def get_house_of_point(p_lon, cusps):
    for i in range(12):
        c1 = cusps[i]
        c2 = cusps[(i + 1) % 12]
        if c1 < c2:
            if c1 <= p_lon < c2: return i + 1
        else:
            if p_lon >= c1 or p_lon < c2: return i + 1
    return 1

def calculate_midpoint(lon1, lon2):
    diff = abs(lon1 - lon2)
    if diff <= 180:
        mp = (lon1 + lon2) / 2.0
    else:
        mp = (lon1 + lon2 + 360) / 2.0
        if mp >= 360:
            mp -= 360
    return mp

def check_conjunction_or_opposition(p_lon, midpoint_lon, orb=2.0):
    dist = angular_diff(p_lon, midpoint_lon)
    for target_angle in [0.0, 180.0]:
        diff_from_target = abs(dist - target_angle)
        if diff_from_target < orb:
            aspect_label = "اقتران مباشر (0°)" if target_angle == 0.0 else "مقابلة تامة (180°)"
            return True, aspect_label, diff_from_target
    return False, None, 0.0

def check_midpoint_axis_activation(p_lon, midpoint_lon, orb=2.0):
    dist = angular_diff(p_lon, midpoint_lon)
    for axis_angle in [0.0, 90.0, 180.0]:
        diff_from_axis = abs(dist - axis_angle)
        if diff_from_axis <= orb:
            if axis_angle == 0.0:
                aspect_name = "اقتران في نفس البرج (0°)"
            elif axis_angle == 90.0:
                aspect_name = "تربيع على المحور (90°)"
            else:
                aspect_name = "مقابلة على المحور (180°)"
            return True, aspect_name, diff_from_axis
    return False, None, 0.0

def get_sign_idx(lon):
    return int(lon / 30) % 12

# =============================================================================
# 4. وظائف اشتقاق مواصفات الشريك (للإرتباط والزواج)
# =============================================================================
def get_physical_appearance(activating_planet_name, p_lon, partner_title="العريس"):
    sign_idx = get_sign_idx(p_lon)
    sign_name = ZODIAC_NAMES_AR[sign_idx]
    deg_in_sign = p_lon % 30

    descriptions = {
        "Venus": {
            "title": "تأثير كوكب الزهرة (سيدة الجمال والجاذبية)",
            "face": "وجه مشرق آسر شديد الجاذبية، ملامح ناعمة ومتناسقة بشكل ملفت. عينان ناعستان ساحرتان تشعان دفئاً ورقة، حواجب مرسومة بجمال، بشرة نقية نضرة، وابتسامة بديعة.",
            "height_build": "قامة معتدلة تميل للطول المتناسق، قوام رشيق ومتناسق جداً، حركات رشيقة وأسلوب ملبس رفيع وذوق راقٍ.",
            "age_bracket": "تحت 30 سنة (مظهر شبابي نضر ودائم الحيوية)"
        },
        "Mercury": {
            "title": "تأثير كوكب عطارد (رسول الذكاء والحيوية)",
            "face": "وجه بيضاوي أو دقيق ذكي الملامح، عينان براقتان سريعتان الحركة تعكسان يقظة ذهنية وسرعة بديهة. أنف دقيق ومستقيم، وابتسامة خفيفة.",
            "height_build": "قامة متوسطة إلى ممشوقة القوام، جسد نحيف أو رشيق خفيف الحركة، سريع الخطوات ونشيط.",
            "age_bracket": "تحت 30 سنة (يبدو أصغر من سنه الحقيقي بفضل خفة ظله)"
        },
        "Moon": {
            "title": "تأثير كوكب القمر (الأمومة، العاطفة، والملامح الملائكية)",
            "face": "وجه دائري ممتلئ كالبدر المضيء، ملامح ملائكية حنونة وعاطفية جداً. عينان واسعتان لامعتان، بشرة ناعمة، وتبرير دافئ يفيض بالسكينة والأمان.",
            "height_build": "قامة متوسطة، جسد ذو انحناءات ممتلئة بلطافة ودفء، حضور هادئ مريح.",
            "age_bracket": "بين 30 إلى 35 سنة (بين فتوة الشباب ونضج العاطفة الأسرية)"
        },
        "Sun": {
            "title": "تأثير كوكب الشمس (الهيبة والملوكية والحضور القيادي)",
            "face": "وجه مهيب مشرق كالضياء، جبهة عريضة واضحة، ملامح بارزة وقوية تعكس فخراً وثقة عالية بالنفس. عينان حادتان ونظرات قيادية واثقة.",
            "height_build": "قامة متوسطة إلى طويلة مع استقامة تامة في الظهر، عريض المنكبين، بنية قوية ذات حضور كاريزمي.",
            "age_bracket": "30 - 35 سنة (مرحلة النضج القيادي والمكانة الاجتماعية الراسخة)"
        },
        "Mars": {
            "title": "تأثير كوكب المريخ (الطاقة الرياضية، الحزم، والجرأة)",
            "face": "ملامح حادة ومنحوتة، عظام وجنتين بارزة، فك قوي وحاسم. عينان ثاقبتان مليئتان بالحماس والتحدي ونظرة مباشرة غير مترددة.",
            "height_build": "قامة ممشوقة وقوية، بنية رياضية عضلية مشدودة، كتفان عريضان وحركة سريعة.",
            "age_bracket": "تحت 30 سنة إلى 35 سنة (في ذروة القوة البدنية والحيوية)"
        },
        "Jupiter": {
            "title": "تأثير كوكب المشتري (السعد الأكبر، الوجاهة، والسعة)",
            "face": "وجه بشوش وضيء، ابتسامة عريضة كريمة تشع تفاؤلاً وسروراً. جبين مرتفع، وعينان واسعتان صافيتان ممتلئتان بالأمل والحكمة.",
            "height_build": "قامة طويلة أو بنية جسدية ضخمة/ممتلئة بمهابة ووجاهة، هيبة اجتماعية ملحوظة.",
            "age_bracket": "30 - 35 سنة أو ناضج في أوائل الأربعينات"
        },
        "Saturn": {
            "title": "تأثير كوكب زحل (الوقار، الرصانة، والاستقرار الكلاسيكي)",
            "face": "وجه رصين منحوت بدقة، ملامح عميقة وجادة توحي بالحكمة والتحمل. عينان غائرتان مركزتان تتأملان بعمق ومسؤولية.",
            "height_build": "قامة طويلة ونحيفة أو متوسطة باستقامة صارمة، جسد صلب ومظهر كلاسيكي رسمي أنيق.",
            "age_bracket": "فوق 40 سنة (شخص ناضج ومسؤول يفوق عمره الزمني وعياً)"
        },
        "Uranus": {
            "title": "تأثير كوكب أورانوس (التميز الفريد، العصرية، والجاذبية)",
            "face": "ملامح غير مألوفة جذابة بطريقة عصرية وفريدة، نظرات غير تقليدية ومتحررة تلمعان بالعبقرية والتمرد.",
            "height_build": "قامة تميل للطول والنحافة، حركة ديناميكية ومظهر عصري جريء غير تقليدي.",
            "age_bracket": "تحت 35 سنة (فكراً مستقبلياً متجدداً)"
        },
        "Neptune": {
            "title": "تأثير كوكب نبتون (السحر الروحي، الخيال، والملامح الحالمة)",
            "face": "ملامح حالمة كأنها لوحة فنية ساحرة، عينان واسعتان غامضتان تأسران القلب برومانسيتهما وبشرة ناعمة ورقيقة.",
            "height_build": "قامة انسيابية رشيقة وناعمة، حركة هادئة وشاعرية توحي بالرقة.",
            "age_bracket": "تحت 30 أو 30-35 سنة"
        },
        "Pluto": {
            "title": "تأثير كوكب بلوتو (الجاذبية المغناطيسية الخارقة والعمق السري)",
            "face": "وجه غامض ذو حضور مغناطيسي لا يقاوم، عينان ثاقبتان كأنهما تقرآن الأسرار، ملامح حادة ومكثفة.",
            "height_build": "بنية جسدية صلبة مكثفة، قامة متوسطة توحي بالقوة الداخلية الهائلة والسيطرة.",
            "age_bracket": "30 - 35 سنة إلى فوق 40 سنة"
        },
        "Rahu": {
            "title": "تأثير راهو - العقدة الشمالية (الكاريزما الاستثنائية القدرية)",
            "face": "ملامح ملفتة للانتباه وغير مألوفة، وجه يحمل سحراً غريباً يجذبك بقوة ونظرات حارقة وطموحة.",
            "height_build": "قامة لافتة ذات حضور بصري قوي وجسد مميز يفرض طاقة حضور في أي مكان.",
            "age_bracket": "تحت 30 أو 30-35 سنة"
        },
        "Ketu": {
            "title": "تأثير كيتو - العقدة الجنوبية (العمق الكارمي والروحانية)",
            "face": "ملامح روحانية هادئة تشع بالسكينة، عينان عميقتان ممتلئتان بالحكمة والزهد وبساطة مريحة تمنح الطمأنينة.",
            "height_build": "قامة معتدلة إلى نحيفة، جسد خفيف ومظهر متواضع وأنيق بأسلوب طبيعي.",
            "age_bracket": "شخص بوقار الشيوخ وحكمتهم (غالباً فوق 35 سنة)"
        }
    }

    p_info = descriptions.get(activating_planet_name, descriptions["Venus"])
    return {
        "planet": activating_planet_name,
        "planet_ar": PLANET_NAMES_AR.get(activating_planet_name, activating_planet_name),
        "sign_name": sign_name,
        "deg_in_sign": deg_in_sign,
        "title": p_info["title"],
        "face": p_info["face"],
        "height_build": p_info["height_build"],
        "age_bracket": p_info["age_bracket"]
    }

def derive_partner_career(natal_cusps, natal_planets):
    c4 = natal_cusps[3]
    sign_idx = get_sign_idx(c4)
    sign_name = ZODIAC_NAMES_AR[sign_idx]
    ruler = SIGN_RULERS[sign_idx]
    modern_ruler = MODERN_SIGN_RULERS[sign_idx]
    planets_in_4th = [p_name for p_name, p_data in natal_planets.items() if p_data.get('house') == 4]

    career_profiles = {
        "Mercury": "قطاع التكنولوجيا، تكنولوجيا المعلومات والبرمجة، التجارة، المحاسبة والتدقيق المالي، الإعلام، أو الاستشارات والتحليل.",
        "Venus": "المجالات الإبداعية والفنون، التصميم المعماري والديكور، الأزياء والموضة والجمال، التجارة الفاخرة، أو العلاقات العامة.",
        "Mars": "الهندسة بمختلف فرعيها، المقاولات والتطوير العقاري، الجراحة والمجال الطبي الطارئ، الأمن، أو ريادة الأعمال والمشاريع الحرة.",
        "Jupiter": "القانون والقضاء، السلك الدبلوماسي، الأكاديميا والتعليم العالي، الاستشارات، المصارف والاستثمار، أو التجارة الدولية.",
        "Saturn": "الإدارة التنفيذية العليا، إدارة وتملك العقارات، الهياكل المؤسسية الكبرى، الإشراف المالي والرقابي، أو الصناعات الثقيلة.",
        "Sun": "مناصب قيادية ورئاسية، إدارة عامة، أصحاب شركات خاصة، مناصب حكومية رفيعة، أو الإنتاج الإبداعي والريادة.",
        "Moon": "القطاع الطبي والرعاية الصحية، إدارة المنشآت الفندقية، التجارة الاستهلاكية والغذائية، العقارات السكنية، أو الموارد البشرية.",
        "Uranus": "هندسة البرمجيات والذكاء الاصطناعي، الفضاء والطيران، الطاقة المتجددة، الابتكار التقني، أو العمل الحر الرقمي.",
        "Neptune": "الطب النفسي والعلاجي، صناعة الأدوية والكيمياء، الفنون البصرية والسينما والموسيقى، الملاحة، أو المنظمات الإنسانية.",
        "Pluto": "الاستثمارات وصناديق التحوط، إدارة الأزمات والشركات الاستراتيجية، التحقيقات والبحث الجنائي، أو قطاع الطاقة."
    }

    ruler_ar = PLANET_NAMES_AR.get(ruler, ruler)
    prof_text = career_profiles.get(ruler, career_profiles["Jupiter"])
    if modern_ruler != ruler:
        prof_text += f" كما يدعمه تأثير {PLANET_NAMES_AR.get(modern_ruler, modern_ruler)}: {career_profiles.get(modern_ruler, '')}"
    planets_text = f"بتأثير الكواكب المتواجدة فيه: ({', '.join([PLANET_NAMES_AR.get(p, p) for p in planets_in_4th])})" if planets_in_4th else ""

    return {
        "derived_house": "البيت العاشر من السابع = البيت الرابع الميلادي",
        "sign": sign_name,
        "ruler": ruler_ar,
        "planets_in_house": planets_text,
        "career_description": prof_text
    }

def derive_partner_intimacy(natal_cusps, natal_planets):
    c2 = natal_cusps[1]
    sign_idx = get_sign_idx(c2)
    sign_name = ZODIAC_NAMES_AR[sign_idx]
    element = ZODIAC_SIGNS[sign_idx]["element"]
    ruler = SIGN_RULERS[sign_idx]

    intimacy_styles = {
        "مائي": "علاقة حميمية شديدة العمق والشغف، اندماج روحي وعاطفي كامل يجمع بين الحنان الفياض والجاذبية المغناطيسية القوية.",
        "ناري": "علاقة نارية ملتهبة بالحماس والإثارة، تجدد دائم ومبادرة عفوية وجرأة عاطفية ممتلئة بالطاقة والمرح.",
        "ترابي": "علاقة حسية راقية وراسخة، مفعمة بالثبات والوفاء والأمان الجسدي العميق والعناية الطويلة.",
        "هوائي": "علاقة قائمة على الانسجام الذهني والتواصل اللفظي الرقيق والتجديد الفكري والمرح."
    }

    return {
        "derived_house": "البيت الثامن من السابع = البيت الثاني الميلادي",
        "sign": sign_name,
        "element": element,
        "ruler": PLANET_NAMES_AR.get(ruler, ruler),
        "intimacy_description": intimacy_styles.get(element, intimacy_styles["ترابي"])
    }

def derive_partner_wealth(natal_cusps, natal_planets):
    c8 = natal_cusps[7]
    sign_idx = get_sign_idx(c8)
    sign_name = ZODIAC_NAMES_AR[sign_idx]
    ruler = SIGN_RULERS[sign_idx]
    planets_in_8th = [p_name for p_name, p_data in natal_planets.items() if p_data.get('house') == 8]

    if "Jupiter" in planets_in_8th or "Venus" in planets_in_8th or ruler in ["Jupiter", "Venus"]:
        wealth_text = "ملاءة مالية ممتازة وثراء لافت؛ الشريك يتمتع بوضع مالي متين، تدفقات نقدية متعددة، استثمارات رابحة، وأصول عقارية أو تجارية."
    elif "Saturn" in planets_in_8th or ruler == "Saturn":
        wealth_text = "ثروة متينة مبنية على أسس راسخة ومجهود تراكمي منظم؛ يمتلك ممتلكات عقارية ثابتة وأصولاً مؤمنة وحكيم جداً في إدارة أمواله."
    elif "Mars" in planets_in_8th or ruler == "Mars" or ruler == "Sun":
        wealth_text = "شخصية عصامية تبني ثروتها باستقلالية تامة وقوة عمل شخصية؛ يمتلك مشاريع خاصة ومصادر دخل حيوية."
    else:
        wealth_text = "وضع مالي مستقر وجيد جداً مع تنوع في الأصول وقدرة ذكية على إدارة الأموال."

    return {
        "derived_house": "البيت الثاني من السابع = البيت الثامن الميلادي",
        "sign": sign_name,
        "ruler": PLANET_NAMES_AR.get(ruler, ruler),
        "wealth_description": wealth_text
    }

def derive_wedding_party(natal_cusps, sr_asc, sr_planets):
    c11 = natal_cusps[10]
    sign11_idx = get_sign_idx(c11)
    has_jupiter_prominent = sr_planets['Jupiter']['house'] in [1, 5, 7, 10, 11]
    has_sun_prominent = sr_planets['Sun']['house'] in [1, 10, 11]

    if has_jupiter_prominent or has_sun_prominent or sign11_idx in [4, 8]:
        style = "حفل زفاف فخم وملكي (Grand Luxury Wedding)"
        desc = "حفل كبير وأسطوري في قاعة فاخرة أو فندق راقٍ، حضور واسع ومبهج يضم نخبة اجتماعية ووجهاء وتنظيم استثنائي."
    elif sr_planets['Venus']['house'] in [1, 5, 7, 10] or sign11_idx in [1, 6]:
        style = "حفل زفاف أنيق وكلاسيكي (Elegant & Aesthetic Wedding)"
        desc = "حفل يتميز بأعلى درجات الذوق والرقي الكلاسيكي، ديكورات زهرية ساحرة وإضاءة رومانسية هادئة."
    else:
        style = "حفل زفاف عائلي دافئ ومبهج (Warm Family Gathering)"
        desc = "حفل عائلي دافئ مفعم بالحب والألفة، يجمع الأهل والأقربين في أجواء ملؤها السعادة والتآلف."

    return {"style": style, "description": desc}

def derive_partner_social_details(natal_cusps, natal_planets):
    c7 = natal_cusps[6]
    ruler7 = SIGN_RULERS[get_sign_idx(c7)]
    ruler7_house = natal_planets.get(ruler7, {}).get('house', 7)
    is_ruler7_retrograde = natal_planets.get(ruler7, {}).get('is_retrograde', False)

    if ruler7_house in [3, 4] or ruler7 in ["Mercury", "Moon"]:
        relative_status = "من طرف الأقارب أو محيط العائلة الموسعة"
        relative_desc = "الشريك له صلة قرابة ممتدة أو ينحدر من نفس الشبكة الاجتماعية المقربة."
    else:
        relative_status = "شخص غريب تماماً (لا توجد صلة قرابة دموية)"
        relative_desc = "الشريك غريب عن العائلة، يلتقي بك عبر مسارات الحياة العامة كالعمل أو الدراسة."

    if ruler7_house in [9, 12] or get_sign_idx(c7) in [8, 10]:
        residence_status = "مقيم في بلد/مدينة أخرى أو كثير التنقل"
        residence_desc = "الشريك يقيم حالياً في مدينة أخرى أو دولة خارجية."
    else:
        residence_status = "مقيم في نفس الدولة والبيئة المحلية"
        residence_desc = "الشريك يقيم في نفس البلد وربما نفس المدينة التي يتواجد بها صاحب الخريطة."

    has_rahu_7_9 = natal_planets.get('Rahu', {}).get('house') in [7, 9]
    if ruler7_house == 9 or has_rahu_7_9 or get_sign_idx(c7) == 8:
        expatriate_status = "مغترب / يحمل جنسية أخرى أو ثقافة مغايرة"
        expatriate_desc = "الشريك يحمل جنسية أجنبية أو مغترب أو ينتمي لخلفية ثقافية مختلفة."
    else:
        expatriate_status = "ينتمي لنفس الوطن والثقافة والديانة الأصلية"
        expatriate_desc = "الشريك من نفس النسيج الوطني والبيئة الثقافية."

    if is_ruler7_retrograde or ruler7_house == 11:
        history_status = "حبيب سابق أو صديق قديم تعود قصته للاكتمال"
        history_desc = "عودة لشخص من الماضي أو صديق مقرّب تحولت العلاقة معه لزواج."
    else:
        history_status = "شخص جديد تماماً لم يسبق لك معرفته"
        history_desc = "شخص يدخل حياتك كصفحة جديدة نقية في توقيت مقدّر."

    if ruler7_house in [5, 11] or get_sign_idx(c7) in [4, 6]:
        marriage_type = "زواج ناتج عن قصة حب جارفة وتوافق عاطفي"
        marriage_desc = "الارتباط يتوج قصة حب حقيقية واختيار حر نابع من القلب."
    else:
        marriage_type = "زواج تقليدي عائلي راقٍ ومدروس"
        marriage_desc = "الزواج يتم عبر الأطر التقليدية الرفيعة بوساطة عائلية كريمة."

    return {
        "relative": {"status": relative_status, "desc": relative_desc},
        "residence": {"status": residence_status, "desc": residence_desc},
        "expatriate": {"status": expatriate_status, "desc": expatriate_desc},
        "history": {"status": history_status, "desc": history_desc},
        "marriage_type": {"status": marriage_type, "desc": marriage_desc}
    }

# =============================================================================
# 5. محرك الـ 50 دلالة فلكية للزواج والارتباط
# =============================================================================
def evaluate_marriage_50_indicators(natal_data, sr_data, general_orb=1.0, midpoint_orb=2.0):
    n_cusps = natal_data['cusps']
    n_planets = natal_data['planets']
    n_midpoint = natal_data['midpoint_lon']
    
    sr_cusps = sr_data['cusps']
    sr_planets = sr_data['planets']
    sr_asc = sr_cusps[0]
    sr_desc = sr_cusps[6]
    sr_mc = sr_cusps[9]
    sr_ic = sr_cusps[3]

    n_7th_sign = int(n_cusps[6] / 30) % 12
    n_7th_ruler = SIGN_RULERS[n_7th_sign]
    n_7th_ruler_lon = n_planets.get(n_7th_ruler, {}).get('lon', 0.0)

    sr_1st_sign = int(sr_cusps[0] / 30) % 12
    sr_1st_ruler = SIGN_RULERS[sr_1st_sign]
    sr_1st_ruler_lon = sr_planets.get(sr_1st_ruler, {}).get('lon', 0.0)

    sr_7th_sign = int(sr_cusps[6] / 30) % 12
    sr_7th_ruler = SIGN_RULERS[sr_7th_sign]
    sr_7th_ruler_lon = sr_planets.get(sr_7th_ruler, {}).get('lon', 0.0)

    sr_5th_sign = int(sr_cusps[4] / 30) % 12
    sr_5th_ruler = SIGN_RULERS[sr_5th_sign]
    sr_5th_ruler_lon = sr_planets.get(sr_5th_ruler, {}).get('lon', 0.0)

    sr_marriage_part = (sr_asc + sr_desc - sr_planets['Venus']['lon']) % 360
    indicators = []

    sr_asc_in_n = get_house_of_point(sr_asc, n_cusps)
    sr_desc_in_n = get_house_of_point(sr_desc, n_cusps)
    sr_mc_in_n = get_house_of_point(sr_mc, n_cusps)

    indicators.append({"id": 1, "code": "M01", "category": "تراكب الأوتاد والمنازل", "name_ar": "طالع السنوية يقع في البيت السابع الميلادي", "description": "حلول طالع العام في بيت الشراكة والزواج الميلادي يعلن عام الشريك بامتياز.", "is_active": sr_asc_in_n == 7, "detail": f"طالع السنوية في البيت {sr_asc_in_n} الميلادي"})
    indicators.append({"id": 2, "code": "M02", "category": "تراكب الأوتاد والمنازل", "name_ar": "سابع السنوية يقع في البيت الأول الميلادي", "description": "الشريك يدخل مجال الذات ويبادر بالاقتراب المباشر للارتباط.", "is_active": sr_desc_in_n == 1, "detail": f"سابع السنوية في البيت {sr_desc_in_n} الميلادي"})
    indicators.append({"id": 3, "code": "M03", "category": "تراكب الأوتاد والمنازل", "name_ar": "طالع السنوية يقع في البيت الخامس الميلادي", "description": "عام مكرس للمشاعر الرومانسية وبداية العلاقات الغرامية الجادة.", "is_active": sr_asc_in_n == 5, "detail": f"طالع السنوية في البيت {sr_asc_in_n} الميلادي"})
    indicators.append({"id": 4, "code": "M04", "category": "تراكب الأوتاد والمنازل", "name_ar": "سابع السنوية يقع في البيت الخامس الميلادي", "description": "تحول علاقة حب وغرام قائمة إلى التزام رسمي وزواج معلن.", "is_active": sr_desc_in_n == 5, "detail": f"سابع السنوية في البيت {sr_desc_in_n} الميلادي"})
    indicators.append({"id": 5, "code": "M05", "category": "تراكب الأوتاد والمنازل", "name_ar": "طالع السنوية يقع في البيت العاشر الميلادي", "description": "تغير جذري ورسمي في الحالة الاجتماعية بالزواج وعقد القران.", "is_active": sr_asc_in_n == 10, "detail": f"طالع السنوية في البيت {sr_asc_in_n} الميلادي"})
    indicators.append({"id": 6, "code": "M06", "category": "تراكب الأوتاد والمنازل", "name_ar": "عاشر السنوية يقع في سابع الأصل", "description": "إشهار الزواج وجعله الحدث الأبرز في السمعة الاجتماعية خلال العام.", "is_active": sr_mc_in_n == 7, "detail": f"عاشر السنوية في البيت {sr_mc_in_n} الميلادي"})
    indicators.append({"id": 7, "code": "M07", "category": "تراكب الأوتاد والمنازل", "name_ar": "طالع السنوية يقع في البيت الرابع الميلادي", "description": "التركيز على تأسيس وتد الأسرة وعش الزوجية والانتقال لسكن جديد.", "is_active": sr_asc_in_n == 4, "detail": f"طالع السنوية في البيت {sr_asc_in_n} الميلادي"})

    m8, d8_diff = is_aspect(sr_asc, n_planets['Venus']['lon'], 0, orb=general_orb)
    indicators.append({"id": 8, "code": "M08", "category": "تراكب الأوتاد والمنازل", "name_ar": "اقتران طالع السنوية بالزهرة الميلادية", "description": "توهج الجاذبية الشخصية والاستعداد القلبي لاستقبال شريك الحياة.", "is_active": m8, "detail": f"اقتران بفارق {d8_diff:.2f}°" if m8 else "غير مقترن"})

    m9, d9_diff = is_aspect(sr_desc, n_planets['Venus']['lon'], 0, orb=general_orb)
    indicators.append({"id": 9, "code": "M09", "category": "تراكب الأوتاد والمنازل", "name_ar": "اقتران سابع السنوية بالزهرة الميلادية", "description": "حلول كوكب الحب والزواج على خط بداية بيت الزواج السنوي.", "is_active": m9, "detail": f"اقتران بفارق {d9_diff:.2f}°" if m9 else "غير مقترن"})

    m10, d10_diff = is_aspect(sr_desc, n_planets['Jupiter']['lon'], 0, orb=general_orb)
    indicators.append({"id": 10, "code": "M10", "category": "تراكب الأوتاد والمنازل", "name_ar": "اقتران سابع السنوية بالمشتري الميلادي", "description": "السعد الأكبر يبارك بيت الشراكة السنوي بالارتباط السعيد وتسهيل الزواج.", "is_active": m10, "detail": f"اقتران بفارق {d10_diff:.2f}°" if m10 else "غير مقترن"})

    indicators.append({"id": 11, "code": "M11", "category": "تموضع الكواكب", "name_ar": "الشمس السنوية تقع في البيت السابع السنوي", "description": "تسليط نور الوعي والاهتمام الكامل على الشريك وشؤون الزواج.", "is_active": sr_planets['Sun']['house'] == 7, "detail": f"الشمس في البيت {sr_planets['Sun']['house']} السنوي"})
    indicators.append({"id": 12, "code": "M12", "category": "تموضع الكواكب", "name_ar": "القمر السنوي يقع في البيت السابع السنوي", "description": "رغبة نفسية وعاطفية ملحة في التشارك والأمان العاطفي.", "is_active": sr_planets['Moon']['house'] == 7, "detail": f"القمر في البيت {sr_planets['Moon']['house']} السنوي"})
    indicators.append({"id": 13, "code": "M13", "category": "تموضع الكواكب", "name_ar": "الزهرة السنوية تقع في البيت السابع السنوي", "description": "الزهرة في بيتها الطبيعي بالسنوية؛ دلالة قاطعة على الخطوبة وعقد القران.", "is_active": sr_planets['Venus']['house'] == 7, "detail": f"الزهرة في البيت {sr_planets['Venus']['house']} السنوي"})
    indicators.append({"id": 14, "code": "M14", "category": "تموضع الكواكب", "name_ar": "المشتري السنوي يقع في البيت السابع السنوي", "description": "زواج محظوظ من شخص ذي وجاهة وسعة.", "is_active": sr_planets['Jupiter']['house'] == 7, "detail": f"المشتري في البيت {sr_planets['Jupiter']['house']} السنوي"})
    indicators.append({"id": 15, "code": "M15", "category": "تموضع الكواكب", "name_ar": "الزهرة السنوية تقع في البيت الخامس السنوي", "description": "نشوة الحب والرومانسية ودخول علاقة عاطفية تسعد القلب.", "is_active": sr_planets['Venus']['house'] == 5, "detail": f"الزهرة في البيت {sr_planets['Venus']['house']} السنوي"})
    indicators.append({"id": 16, "code": "M16", "category": "تموضع الكواكب", "name_ar": "الشمس السنوية تقع في البيت الخامس السنوي", "description": "حيوية المشاعر العاطفية وإشراق الحب الجاد المعلن خلال السنة.", "is_active": sr_planets['Sun']['house'] == 5, "detail": f"الشمس في البيت {sr_planets['Sun']['house']} السنوي"})
    indicators.append({"id": 17, "code": "M17", "category": "تموضع الكواكب", "name_ar": "القمر السنوي يقع في البيت الخامس السنوي", "description": "تعلق عاطفي وغرامي عميق وتطلع لتكوين رابطة دائمة.", "is_active": sr_planets['Moon']['house'] == 5, "detail": f"القمر في البيت {sr_planets['Moon']['house']} السنوي"})
    indicators.append({"id": 18, "code": "M18", "category": "تموضع الكواكب", "name_ar": "الزهرة السنوية تقع في البيت الأول السنوي", "description": "إشراقة الشخصية وجاذبيتها للخطاب وإعلان الرغبة في الارتباط.", "is_active": sr_planets['Venus']['house'] == 1, "detail": f"الزهرة في البيت {sr_planets['Venus']['house']} السنوي"})
    indicators.append({"id": 19, "code": "M19", "category": "تموضع الكواكب", "name_ar": "الشمس السنوية تقع في البيت الأول السنوي", "description": "بداية دورة حياة جديدة ومبادرة شخصية لحسم مصير الارتباط.", "is_active": sr_planets['Sun']['house'] == 1, "detail": f"الشمس في البيت {sr_planets['Sun']['house']} السنوي"})
    indicators.append({"id": 20, "code": "M20", "category": "تموضع الكواكب", "name_ar": "القمر السنوي يقع في البيت الأول أو الرابع السنوي", "description": "التركيز على بناء السكن الأسري والاستقرار الشرعي.", "is_active": sr_planets['Moon']['house'] in [1, 4], "detail": f"القمر في البيت {sr_planets['Moon']['house']} السنوي"})

    m21, asp21, diff21 = is_soft_or_conjunction(sr_planets['Venus']['lon'], sr_planets['Mars']['lon'], orb=general_orb)
    indicators.append({"id": 21, "code": "M21", "category": "اتصالات الكواكب", "name_ar": "اتصال سعيد أو اقتران بين الزهرة والمريخ في السنوية", "description": "التوازن التام والجاذبية بين طاقة الأنوثة والذكورة وتتويجها.", "is_active": m21, "detail": f"{asp21} بفارق {diff21:.2f}°" if m21 else "غير متصل"})

    m22, asp22, diff22 = is_soft_or_conjunction(sr_planets['Venus']['lon'], sr_planets['Jupiter']['lon'], orb=general_orb)
    indicators.append({"id": 22, "code": "M22", "category": "اتصالات الكواكب", "name_ar": "اتصال سعيد بين الزهرة والمشتري (سعد السعدين)", "description": "أعظم اتصال للسعادة العاطفية وتيسير الزواج.", "is_active": m22, "detail": f"{asp22} بفارق {diff22:.2f}°" if m22 else "غير متصل"})

    m23, asp23, diff23 = is_soft_or_conjunction(sr_planets['Sun']['lon'], sr_planets['Moon']['lon'], orb=general_orb)
    indicators.append({"id": 23, "code": "M23", "category": "اتصالات الكواكب", "name_ar": "اتصال سعيد بين الشمس والقمر السنويين", "description": "توافق الإرادة والوجدان وتناغم الشريكين على أهداف الزواج.", "is_active": m23, "detail": f"{asp23} بفارق {diff23:.2f}°" if m23 else "غير متصل"})

    m24, asp24, diff24 = is_soft_or_conjunction(sr_planets['Venus']['lon'], sr_planets['Saturn']['lon'], orb=general_orb)
    indicators.append({"id": 24, "code": "M24", "category": "اتصالات الكواكب", "name_ar": "اتصال تثبيت رسمي بين الزهرة وزحل في السنوية", "description": "زحل يمنح العلاقة الثبات والجدية والعقد القانوني المكتوب.", "is_active": m24, "detail": f"{asp24} بفارق {diff24:.2f}°" if m24 else "غير متصل"})

    m25, asp25, diff25 = is_soft_or_conjunction(sr_planets['Venus']['lon'], sr_planets['Uranus']['lon'], orb=general_orb)
    indicators.append({"id": 25, "code": "M25", "category": "اتصالات الكواكب", "name_ar": "اتصال سعيد بين الزهرة وأورانوس في السنوية", "description": "حب سريع ومفاجئ، كسر العزوبية وقرار زواج سريع.", "is_active": m25, "detail": f"{asp25} بفارق {diff25:.2f}°" if m25 else "غير متصل"})

    m26, diff26 = is_aspect(sr_planets['Sun']['lon'], sr_planets['Venus']['lon'], 0, orb=general_orb)
    indicators.append({"id": 26, "code": "M26", "category": "اتصالات الكواكب", "name_ar": "اقتران الشمس والزهرة في السنوية", "description": "إشراق الحب ونيل المنى العاطفي والارتباط عن اقتناع.", "is_active": m26, "detail": f"اقتران بفارق {diff26:.2f}°" if m26 else "غير مقترن"})

    m27, diff27 = is_aspect(sr_planets['Moon']['lon'], sr_planets['Venus']['lon'], 0, orb=general_orb)
    indicators.append({"id": 27, "code": "M27", "category": "اتصالات الكواكب", "name_ar": "اقتران القمر والزهرة في السنوية", "description": "فيض من الرقة والبهجة والاستعداد لإنشاء عش الزوجية.", "is_active": m27, "detail": f"اقتران بفارق {diff27:.2f}°" if m27 else "غير مقترن"})

    m28, asp28, diff28 = is_soft_or_conjunction(sr_planets['Mars']['lon'], sr_planets['Jupiter']['lon'], orb=general_orb)
    indicators.append({"id": 28, "code": "M28", "category": "اتصالات الكواكب", "name_ar": "اتصال سعيد بين المريخ والمشتري في السنوية", "description": "شجاعة الحسم والمبادرة الفعالة لإتمام مراسم الخطوبة.", "is_active": m28, "detail": f"{asp28} بفارق {diff28:.2f}°" if m28 else "غير متصل"})

    m29, diff29 = is_aspect(sr_planets['Venus']['lon'], sr_planets['Rahu']['lon'], 0, orb=general_orb)
    indicators.append({"id": 29, "code": "M29", "category": "اتصالات الكواكب", "name_ar": "اقتران الزهرة مع راهو السنوي (العقدة الشمالية)", "description": "لقاء قدري مقدر وانجذاب مغناطيسي يقود للزواج.", "is_active": m29, "detail": f"اقتران بفارق {diff29:.2f}°" if m29 else "غير مقترن"})

    m30, diff30 = is_aspect(sr_planets['Jupiter']['lon'], sr_planets['Rahu']['lon'], 0, orb=general_orb)
    indicators.append({"id": 30, "code": "M30", "category": "اتصالات الكواكب", "name_ar": "اقتران المشتري مع راهو السنوي", "description": "فرصة كبرى قدرية لتوسيع الأفق العائلي وزواج وافر الخير.", "is_active": m30, "detail": f"اقتران بفارق {diff30:.2f}°" if m30 else "غير مقترن"})

    m31, asp31, diff31 = is_soft_or_conjunction(sr_planets['Venus']['lon'], n_7th_ruler_lon, orb=general_orb)
    indicators.append({"id": 31, "code": "M31", "category": "اتصالات حكام الأصل", "name_ar": f"الزهرة السنوية تتصل بحاكم السابع الميلادي ({PLANET_NAMES_AR.get(n_7th_ruler, n_7th_ruler)})", "description": "تنشيط مباشر للشريك الأصلي بالحب والارتباط الفعلي.", "is_active": m31, "detail": f"{asp31} بفارق {diff31:.2f}°" if m31 else "غير متصل"})

    m32, asp32, diff32 = is_soft_or_conjunction(sr_planets['Jupiter']['lon'], n_7th_ruler_lon, orb=general_orb)
    indicators.append({"id": 32, "code": "M32", "category": "اتصالات حكام الأصل", "name_ar": f"المشتري السنوي يتصل بحاكم السابع الميلادي ({PLANET_NAMES_AR.get(n_7th_ruler, n_7th_ruler)})", "description": "بركة وتوفيق يطال شريك الحياة وتسهيل الإجراءات.", "is_active": m32, "detail": f"{asp32} بفارق {diff32:.2f}°" if m32 else "غير متصل"})

    m33, asp33, diff33 = is_soft_or_conjunction(sr_planets['Sun']['lon'], n_7th_ruler_lon, orb=general_orb)
    indicators.append({"id": 33, "code": "M33", "category": "اتصالات حكام الأصل", "name_ar": f"الشمس السنوية تتصل بحاكم السابع الميلادي ({PLANET_NAMES_AR.get(n_7th_ruler, n_7th_ruler)})", "description": "تسليط الضوء والاعتراف الرسمي بالشريك.", "is_active": m33, "detail": f"{asp33} بفارق {diff33:.2f}°" if m33 else "غير متصل"})

    m34, asp34, diff34 = is_soft_or_conjunction(sr_planets['Moon']['lon'], n_7th_ruler_lon, orb=general_orb)
    indicators.append({"id": 34, "code": "M34", "category": "اتصالات حكام الأصل", "name_ar": f"القمر السنوي يتصل بحاكم السابع الميلادي ({PLANET_NAMES_AR.get(n_7th_ruler, n_7th_ruler)})", "description": "رابطة وجدانية متينة واستجابة متبادلة مع الشريك.", "is_active": m34, "detail": f"{asp34} بفارق {diff34:.2f}°" if m34 else "غير متصل"})

    m35, diff35 = is_aspect(sr_7th_ruler_lon, n_planets['Venus']['lon'], 0, orb=general_orb)
    indicators.append({"id": 35, "code": "M35", "category": "اتصالات حكام الأصل", "name_ar": f"حاكم السابع السنوي يقترن بالزهرة الميلادية", "description": "شريك هذا العام يلتقي مباشرة بكوكب الحب الأصلي.", "is_active": m35, "detail": f"اقتران بفارق {diff35:.2f}°" if m35 else "غير مقترن"})

    indicators.append({"id": 36, "code": "M36", "category": "اتصالات حكام الأصل", "name_ar": f"حاكم السابع السنوي في البيت الأول السنوي", "description": "الشريك يسعى بنشاط نحو صاحب الخريطة لطلب الزواج.", "is_active": sr_planets[sr_7th_ruler]['house'] == 1, "detail": f"حاكم السابع في البيت {sr_planets[sr_7th_ruler]['house']}"})
    indicators.append({"id": 37, "code": "M37", "category": "اتصالات حكام الأصل", "name_ar": f"حاكم الأول السنوي في البيت السابع السنوي", "description": "صاحب الخريطة يكرس جهده لإتمام الشراكة والزواج.", "is_active": sr_planets[sr_1st_ruler]['house'] == 7, "detail": f"حاكم الأول في البيت {sr_planets[sr_1st_ruler]['house']}"})

    m38, asp38, diff38 = is_soft_or_conjunction(sr_1st_ruler_lon, sr_7th_ruler_lon, orb=general_orb)
    indicators.append({"id": 38, "code": "M38", "category": "اتصالات حكام الأصل", "name_ar": "اتصال سعيد بين حاكم الطالع وحاكم السابع في السنوية", "description": "التلاقي التام بين طرفي العلاقة لإتمام عقد القران.", "is_active": m38, "detail": f"{asp38} بفارق {diff38:.2f}°" if m38 else "غير متصل"})

    m39, asp39, diff39 = is_soft_or_conjunction(sr_planets['Venus']['lon'], n_planets['Sun']['lon'], orb=general_orb)
    indicators.append({"id": 39, "code": "M39", "category": "اتصالات حكام الأصل", "name_ar": "الزهرة السنوية تتصل بالشمس الميلادية", "description": "تناغم عاطفي يعزز القبول بالزواج والارتباط.", "is_active": m39, "detail": f"{asp39} بفارق {diff39:.2f}°" if m39 else "غير متصل"})

    m40, asp40, diff40 = is_soft_or_conjunction(sr_planets['Venus']['lon'], n_planets['Moon']['lon'], orb=general_orb)
    indicators.append({"id": 40, "code": "M40", "category": "اتصالات حكام الأصل", "name_ar": "الزهرة السنوية تتصل بالقمر الميلادي", "description": "سكينة ودفء أسري يمهد لتكوين عائلة سعيدة.", "is_active": m40, "detail": f"{asp40} بفارق {diff40:.2f}°" if m40 else "غير متصل"})

    indicators.append({"id": 41, "code": "M41", "category": "العقد والسهام", "name_ar": "راهو السنوي في البيت السابع السنوي", "description": "الشراكة والزواج هما الغاية القدرية الكبرى خلال العام.", "is_active": sr_planets['Rahu']['house'] == 7, "detail": f"راهو في البيت {sr_planets['Rahu']['house']}"})
    indicators.append({"id": 42, "code": "M42", "category": "العقد والسهام", "name_ar": "راهو السنوي في البيت الخامس السنوي", "description": "تجربة عاطفية استثنائية مشحونة بالشغف تدفع نحو الالتزام.", "is_active": sr_planets['Rahu']['house'] == 5, "detail": f"راهو في البيت {sr_planets['Rahu']['house']}"})

    p_in_7 = [p for p, d in sr_planets.items() if d['house'] == 7]
    indicators.append({"id": 43, "code": "M43", "category": "العقد والسهام", "name_ar": f"تجمع كواكب في البيت السابع السنوي ({len(p_in_7)} كواكب)", "description": "تركيز طاقي هائل في قطاع الزواج يؤكد حتمية الأحداث.", "is_active": len(p_in_7) >= 2, "detail": f"الكواكب: {', '.join(p_in_7)}" if p_in_7 else "أقل من كوكبين"})

    p_in_5 = [p for p, d in sr_planets.items() if d['house'] == 5]
    indicators.append({"id": 44, "code": "M44", "category": "العقد والسهام", "name_ar": f"تجمع كواكب في البيت الخامس السنوي ({len(p_in_5)} كواكب)", "description": "توهج المحور الرومانسي والأنشطة العاطفية طوال السنة.", "is_active": len(p_in_5) >= 2, "detail": f"الكواكب: {', '.join(p_in_5)}" if p_in_5 else "أقل من كوكبين"})

    v_near_angle = any(angular_diff(sr_planets['Venus']['lon'], a) <= 3.0 for a in [sr_asc, sr_ic, sr_desc, sr_mc])
    indicators.append({"id": 45, "code": "M45", "category": "العقد والسهام", "name_ar": "الزهرة السنوية تقع على وتد من أوتاد السنوية (أورب 3°)", "description": "بروز طاقة كوكب الزهرة بقوة وتأثير حاسم في مجريات العام.", "is_active": v_near_angle, "detail": "الزهرة مقترنة بوتد" if v_near_angle else "غير مقترنة بوتد"})

    j_near_angle = any(angular_diff(sr_planets['Jupiter']['lon'], a) <= 3.0 for a in [sr_asc, sr_ic, sr_desc, sr_mc])
    indicators.append({"id": 46, "code": "M46", "category": "العقد والسهام", "name_ar": "المشتري السنوي يقع على وتد من أوتاد السنوية (أورب 3°)", "description": "بروز الحظ السعيد والارتقاء الاجتماعي والزواج الوافر البركة.", "is_active": j_near_angle, "detail": "المشتري مقترن بوتد" if j_near_angle else "غير مقترن بوتد"})

    m47_rahu, _ = is_aspect(sr_planets['Moon']['lon'], sr_planets['Rahu']['lon'], 0, orb=general_orb)
    m47_ketu, _ = is_aspect(sr_planets['Moon']['lon'], sr_planets['Ketu']['lon'], 0, orb=general_orb)
    d47 = m47_rahu or m47_ketu
    indicators.append({"id": 47, "code": "M47", "category": "العقد والسهام", "name_ar": "القمر السنوي يقترن بمحور العقدتين (راهو أو كيتو)", "description": "ارتباط وشراكة زوجية ذات بصمة كارمية مقدرة.", "is_active": d47, "detail": "مقترن بمحور العقد" if d47 else "غير مقترن"})

    m48, _, _ = is_soft_or_conjunction(sr_5th_ruler_lon, sr_7th_ruler_lon, orb=general_orb)
    d48 = m48 or (sr_planets[sr_5th_ruler]['house'] == 7) or (sr_planets[sr_7th_ruler]['house'] == 5)
    indicators.append({"id": 48, "code": "M48", "category": "العقد والسهام", "name_ar": "اتصال أو تبادل بين حاكم الخامس وحاكم السابع في السنوية", "description": "العلامة الدقيقة على تتويج قصة الحب بالزواج الرسمي.", "is_active": d48, "detail": "متحقق" if d48 else "غير متحقق"})

    m49_v, _, _ = is_soft_or_conjunction(sr_marriage_part, sr_planets['Venus']['lon'], orb=general_orb)
    m49_j, _, _ = is_soft_or_conjunction(sr_marriage_part, sr_planets['Jupiter']['lon'], orb=general_orb)
    d49 = m49_v or m49_j
    indicators.append({"id": 49, "code": "M49", "category": "العقد والسهام", "name_ar": "تفعيل سهم الزواج (Part of Marriage) مع السعدين", "description": "سهم السعادة الزوجية يتلقى دعماً من أدلة الخير.", "is_active": d49, "detail": "سهم الزواج مفعل" if d49 else "غير مفعل"})

    activated_midpoint_list = []
    for p_name, p_data in sr_planets.items():
        p_lon = p_data['lon']
        is_active, aspect_type, dist = check_midpoint_axis_activation(p_lon, n_midpoint, orb=midpoint_orb)
        if is_active:
            activated_midpoint_list.append({
                "planet": p_name,
                "planet_ar": PLANET_NAMES_AR.get(p_name, p_name),
                "lon": p_lon,
                "sign_name": ZODIAC_NAMES_AR[int(p_lon/30)%12],
                "deg_in_sign": p_lon % 30,
                "diff": dist,
                "aspect_type": aspect_type
            })

    d50 = len(activated_midpoint_list) > 0
    indicators.append({"id": 50, "code": "M50", "category": "العقد والسهام", "name_ar": "تفعيل محور نقطة منتصف الشمس/القمر الميلادية (Sun/Moon Midpoint Axis)", "description": "الشرط المحوري؛ وقوع كوكب سنوي في نفس برج الميد بوينت أو المقابل أو التربيع (أورب < 2.0°).", "is_active": d50, "detail": f"الكواكب المفعلة: {len(activated_midpoint_list)}" if d50 else "لم يتم التفعيل"})

    active_count = sum(1 for ind in indicators if ind['is_active'])
    return {
        "active_count": active_count,
        "indicators": indicators,
        "activated_midpoints": activated_midpoint_list
    }

# =============================================================================
# 6. محرك الـ 50 دلالة فلكية للحمل والإنجاب (مع 7 ميد بوينت)
# =============================================================================
def evaluate_childbirth_50_indicators(natal_data, sr_data, general_orb=1.5, midpoint_orb=2.0):
    n_cusps = natal_data['cusps']
    n_planets = natal_data['planets']
    n_midpoints = natal_data['childbirth_midpoints']
    
    sr_cusps = sr_data['cusps']
    sr_planets = sr_data['planets']
    sr_asc = sr_cusps[0]
    sr_ic = sr_cusps[3]
    sr_5th = sr_cusps[4]
    sr_mc = sr_cusps[9]

    n_5th_sign = int(n_cusps[4] / 30) % 12
    n_5th_ruler = SIGN_RULERS[n_5th_sign]
    n_5th_ruler_lon = n_planets[n_5th_ruler]['lon']

    sr_1st_sign = int(sr_cusps[0] / 30) % 12
    sr_1st_ruler = SIGN_RULERS[sr_1st_sign]
    sr_1st_ruler_lon = sr_planets[sr_1st_ruler]['lon']

    sr_5th_sign = int(sr_cusps[4] / 30) % 12
    sr_5th_ruler = SIGN_RULERS[sr_5th_sign]
    sr_5th_ruler_lon = sr_planets[sr_5th_ruler]['lon']

    sr_4th_sign = int(sr_cusps[3] / 30) % 12
    sr_4th_ruler = SIGN_RULERS[sr_4th_sign]
    sr_4th_ruler_lon = sr_planets[sr_4th_ruler]['lon']

    sr_children_part = (sr_asc + sr_planets['Jupiter']['lon'] - sr_planets['Saturn']['lon']) % 360

    activated_midpoints_list = []
    for mp_item in n_midpoints:
        mp_name = mp_item['name']
        mp_lon = mp_item['lon']
        mp_sign_idx = int(mp_lon / 30) % 12
        
        activators_for_this_mp = []
        for p_name, p_data in sr_planets.items():
            p_lon = p_data['lon']
            is_act, aspect_label, diff_val = check_conjunction_or_opposition(p_lon, mp_lon, orb=midpoint_orb)
            if is_act:
                p_sign_idx = int(p_lon / 30) % 12
                activators_for_this_mp.append({
                    "planet": p_name,
                    "planet_ar": PLANET_NAMES_AR.get(p_name, p_name),
                    "sign_name": ZODIAC_NAMES_AR[p_sign_idx],
                    "deg_in_sign": p_lon % 30,
                    "aspect_type": aspect_label,
                    "diff": diff_val
                })
        
        if activators_for_this_mp:
            activators_for_this_mp.sort(key=lambda x: x['diff'])
            activated_midpoints_list.append({
                "midpoint_name": mp_name,
                "midpoint_lon": mp_lon,
                "midpoint_sign": ZODIAC_NAMES_AR[mp_sign_idx],
                "midpoint_deg": mp_lon % 30,
                "activators": activators_for_this_mp,
                "primary_activator": activators_for_this_mp[0]
            })

    indicators = []
    sr_asc_in_n = get_house_of_point(sr_asc, n_cusps)
    sr_5th_in_n = get_house_of_point(sr_5th, n_cusps)
    sr_mc_in_n = get_house_of_point(sr_mc, n_cusps)
    sr_ic_in_n = get_house_of_point(sr_ic, n_cusps)

    indicators.append({"id": 1, "code": "P01", "category": "تراكب الأوتاد والمنازل", "name_ar": "طالع السنوية يقع في البيت الخامس الميلادي", "description": "حلول طالع العام في بيت الأطفال والذرية يضع الإنجاب في صدارة الأحداث.", "is_active": sr_asc_in_n == 5, "detail": f"طالع السنوية في البيت {sr_asc_in_n}"})
    indicators.append({"id": 2, "code": "P02", "category": "تراكب الأوتاد والمنازل", "name_ar": "خامس السنوية يقع في البيت الأول الميلادي", "description": "دخول طاقة المولود مباشرة إلى مجال الذات والهوية.", "is_active": sr_5th_in_n == 1, "detail": f"خامس السنوية في البيت {sr_5th_in_n}"})
    indicators.append({"id": 3, "code": "P03", "category": "تراكب الأوتاد والمنازل", "name_ar": "طالع السنوية يقع في البيت الرابع الميلادي", "description": "توسع العائلة وتأسيس حاضنة الأمومة والبيت.", "is_active": sr_asc_in_n == 4, "detail": f"طالع السنوية في البيت {sr_asc_in_n}"})
    indicators.append({"id": 4, "code": "P04", "category": "تراكب الأوتاد والمنازل", "name_ar": "طالع السنوية يقع في البيت الحادي عشر الميلادي", "description": "البيت الحادي عشر بيت تحقق الأمنيات الكبرى كالإنجاب.", "is_active": sr_asc_in_n == 11, "detail": f"طالع السنوية في البيت {sr_asc_in_n}"})
    indicators.append({"id": 5, "code": "P05", "category": "تراكب الأوتاد والمنازل", "name_ar": "عاشر السنوية يقع في خامس الأصل", "description": "التحول إلى لقب 'أم' كحدث بارز يغير المكانة الاجتماعية.", "is_active": sr_mc_in_n == 5, "detail": f"عاشر السنوية في البيت {sr_mc_in_n}"})
    indicators.append({"id": 6, "code": "P06", "category": "تراكب الأوتاد والمنازل", "name_ar": "رابع السنوية يقع في خامس الأصل", "description": "ارتباط مباشر بين جذور العائلة وبيت الإنجاب والخصوبة.", "is_active": sr_ic_in_n == 5, "detail": f"رابع السنوية في البيت {sr_ic_in_n}"})
    indicators.append({"id": 7, "code": "P07", "category": "تراكب الأوتاد والمنازل", "name_ar": "خامس السنوية يقع في البيت الخامس الميلادي", "description": "تأكيد مضاعف لتفعيل بيت الأطفال الأصلي في الخريطة.", "is_active": sr_5th_in_n == 5, "detail": f"خامس السنوية في البيت {sr_5th_in_n}"})

    m8, d8 = is_aspect(sr_asc, n_planets['Moon']['lon'], 0, orb=general_orb)
    indicators.append({"id": 8, "code": "P08", "category": "تراكب الأوتاد والمنازل", "name_ar": "اقتران طالع السنوية بالقمر الميلادي", "description": "تفعيل غريزة الأمومة والخصوبة الفسيولوجية.", "is_active": m8, "detail": f"اقتران بفارق {d8:.2f}°" if m8 else "غير مقترن"})

    m9, d9 = is_aspect(sr_asc, n_planets['Jupiter']['lon'], 0, orb=general_orb)
    indicators.append({"id": 9, "code": "P09", "category": "تراكب الأوتاد والمنازل", "name_ar": "اقتران طالع السنوية بالمشتري الميلادي", "description": "السعد الأكبر ودليل الأبناء يمنح بركة التوسع العائلي.", "is_active": m9, "detail": f"اقتران بفارق {d9:.2f}°" if m9 else "غير مقترن"})

    m10, d10 = is_aspect(sr_5th, n_planets['Jupiter']['lon'], 0, orb=general_orb)
    indicators.append({"id": 10, "code": "P10", "category": "تراكب الأوتاد والمنازل", "name_ar": "اقتران وتد الخامس السنوي بالمشتري الميلادي", "description": "حلول كوكب الذرية والوفرة على رأس بيت الأطفال.", "is_active": m10, "detail": f"اقتران بفارق {d10:.2f}°" if m10 else "غير مقترن"})

    indicators.append({"id": 11, "code": "P11", "category": "تموضع الكواكب", "name_ar": "المشتري السنوي في البيت الخامس السنوي", "description": "أقوى دلالة كلاسيكية على الحمل السعيد والولادة الميسرة.", "is_active": sr_planets['Jupiter']['house'] == 5, "detail": f"المشتري في البيت {sr_planets['Jupiter']['house']}"})
    indicators.append({"id": 12, "code": "P12", "category": "تموضع الكواكب", "name_ar": "القمر السنوي في البيت الخامس السنوي", "description": "ارتفاع معدلات الخصوبة والحمل وتعلق النفس بالأمومة.", "is_active": sr_planets['Moon']['house'] == 5, "detail": f"القمر في البيت {sr_planets['Moon']['house']}"})
    indicators.append({"id": 13, "code": "P13", "category": "تموضع الكواكب", "name_ar": "الزهرة السنوية في البيت الخامس السنوي", "description": "فرحة استقبال مولود جميل وبهجة غامرة في محيط الأسرة.", "is_active": sr_planets['Venus']['house'] == 5, "detail": f"الزهرة في البيت {sr_planets['Venus']['house']}"})
    indicators.append({"id": 14, "code": "P14", "category": "تموضع الكواكب", "name_ar": "الشمس السنوية في البيت الخامس السنوي", "description": "ولادة طفل يجلب النور والفخر والبهجة للحياة.", "is_active": sr_planets['Sun']['house'] == 5, "detail": f"الشمس في البيت {sr_planets['Sun']['house']}"})
    indicators.append({"id": 15, "code": "P15", "category": "تموضع الكواكب", "name_ar": "القمر السنوي في البيت الأول السنوي", "description": "تغيرات جسدية مرتبطة بالحمل وتصدر دور الأمومة.", "is_active": sr_planets['Moon']['house'] == 1, "detail": f"القمر في البيت {sr_planets['Moon']['house']}"})
    indicators.append({"id": 16, "code": "P16", "category": "تموضع الكواكب", "name_ar": "المشتري السنوي في البيت الأول السنوي", "description": "توسع جسدي وبركة وسعادة عائلية كبرى.", "is_active": sr_planets['Jupiter']['house'] == 1, "detail": f"المشتري في البيت {sr_planets['Jupiter']['house']}"})
    indicators.append({"id": 17, "code": "P17", "category": "تموضع الكواكب", "name_ar": "المشتري السنوي في البيت الرابع السنوي", "description": "زيادة عدد أفراد الأسرة داخل المنزل وامتلاء البيت بالبهجة.", "is_active": sr_planets['Jupiter']['house'] == 4, "detail": f"المشتري في البيت {sr_planets['Jupiter']['house']}"})
    indicators.append({"id": 18, "code": "P18", "category": "تموضع الكواكب", "name_ar": "القمر السنوي في البيت الرابع السنوي", "description": "القمر في بيته الطبيعي؛ ذروة طاقة الأمومة والاحتواء.", "is_active": sr_planets['Moon']['house'] == 4, "detail": f"القمر في البيت {sr_planets['Moon']['house']}"})
    indicators.append({"id": 19, "code": "P19", "category": "تموضع الكواكب", "name_ar": "المشتري السنوي في البيت الحادي عشر السنوي", "description": "تحقق أمنية الإنجاب وتفعيل محور (5 - 11).", "is_active": sr_planets['Jupiter']['house'] == 11, "detail": f"المشتري في البيت {sr_planets['Jupiter']['house']}"})
    indicators.append({"id": 20, "code": "P20", "category": "تموضع الكواكب", "name_ar": "القمر السنوي في البيت الحادي عشر السنوي", "description": "استجابة عاطفية لتحقيق حلم الأمومة وتوسع العائلة.", "is_active": sr_planets['Moon']['house'] == 11, "detail": f"القمر في البيت {sr_planets['Moon']['house']}"})
    indicators.append({"id": 21, "code": "P21", "category": "تموضع الكواكب", "name_ar": "الزهرة السنوية في البيت الرابع السنوي", "description": "تزيين المنزل وتجهيز غرفة ومستلزمات المولود الجديد.", "is_active": sr_planets['Venus']['house'] == 4, "detail": f"الزهرة في البيت {sr_planets['Venus']['house']}"})
    indicators.append({"id": 22, "code": "P22", "category": "تموضع الكواكب", "name_ar": "أورانوس السنوي في البيت الخامس السنوي", "description": "حمل مفاجئ وغير متوقع أو تغير جذري سريع.", "is_active": sr_planets['Uranus']['house'] == 5, "detail": f"أورانوس في البيت {sr_planets['Uranus']['house']}"})

    m23, asp23, diff23 = is_soft_or_conjunction(sr_planets['Moon']['lon'], sr_planets['Jupiter']['lon'], orb=general_orb)
    indicators.append({"id": 23, "code": "P23", "category": "اتصالات كواكب", "name_ar": "اتصال سعيد بين القمر والمشتري السنويين", "description": "أعظم اتصال للحمل والخصوبة وسلامة الأم والجنين.", "is_active": m23, "detail": f"{asp23} بفارق {diff23:.2f}°" if m23 else "غير متصل"})

    m24, asp24, diff24 = is_soft_or_conjunction(sr_planets['Moon']['lon'], sr_planets['Venus']['lon'], orb=general_orb)
    indicators.append({"id": 24, "code": "P24", "category": "اتصالات كواكب", "name_ar": "اتصال سعيد بين القمر والزهرة السنويين", "description": "تناغم الأنوثة والخصوبة والفرحة بقدوم مولود.", "is_active": m24, "detail": f"{asp24} بفارق {diff24:.2f}°" if m24 else "غير متصل"})

    m25, asp25, diff25 = is_soft_or_conjunction(sr_planets['Jupiter']['lon'], sr_planets['Venus']['lon'], orb=general_orb)
    indicators.append({"id": 25, "code": "P25", "category": "اتصالات كواكب", "name_ar": "اتصال سعيد بين المشتري والزهرة السنويين", "description": "سعد السعدين؛ تيسير الحمل والولادة.", "is_active": m25, "detail": f"{asp25} بفارق {diff25:.2f}°" if m25 else "غير متصل"})

    m26, asp26, diff26 = is_soft_or_conjunction(sr_planets['Sun']['lon'], sr_planets['Jupiter']['lon'], orb=general_orb)
    indicators.append({"id": 26, "code": "P26", "category": "اتصالات كواكب", "name_ar": "اتصال سعيد بين الشمس والمشتري السنويين", "description": "نمو الحياة وازدهار الذرية وتيسير الإنجاب.", "is_active": m26, "detail": f"{asp26} بفارق {diff26:.2f}°" if m26 else "غير متصل"})

    m27, asp27, diff27 = is_soft_or_conjunction(sr_planets['Sun']['lon'], sr_planets['Moon']['lon'], orb=general_orb)
    indicators.append({"id": 27, "code": "P27", "category": "اتصالات كواكب", "name_ar": "اتصال سعيد بين الشمس والقمر السنويين", "description": "اكتمال دورة التخصيب والتكامل لإنجاب طفل.", "is_active": m27, "detail": f"{asp27} بفارق {diff27:.2f}°" if m27 else "غير متصل"})

    m28, asp28, diff28 = is_soft_or_conjunction(sr_planets['Moon']['lon'], sr_planets['Mars']['lon'], orb=general_orb)
    indicators.append({"id": 28, "code": "P28", "category": "اتصالات كواكب", "name_ar": "اتصال متناغم بين القمر والمريخ السنويين", "description": "حيوية جسدية وطاقة نشطة تدعم التخصيب والولادة.", "is_active": m28, "detail": f"{asp28} بفارق {diff28:.2f}°" if m28 else "غير متصل"})

    m29, asp29, diff29 = is_soft_or_conjunction(sr_planets['Jupiter']['lon'], sr_planets['Mars']['lon'], orb=general_orb)
    indicators.append({"id": 29, "code": "P29", "category": "اتصالات كواكب", "name_ar": "اتصال متناغم بين المشتري والمريخ السنويين", "description": "طاقة التوسع والحسم والإنجاب الفعلي.", "is_active": m29, "detail": f"{asp29} بفارق {diff29:.2f}°" if m29 else "غير متصل"})

    m30, asp30, diff30 = is_soft_or_conjunction(sr_planets['Moon']['lon'], sr_planets['Uranus']['lon'], orb=general_orb)
    indicators.append({"id": 30, "code": "P30", "category": "اتصالات كواكب", "name_ar": "اتصال متناغم بين القمر وأورانوس السنويين", "description": "بشرى حمل مفاجئة وسريعة وتغير جذري للأمومة.", "is_active": m30, "detail": f"{asp30} بفارق {diff30:.2f}°" if m30 else "غير متصل"})

    m31, diff31 = is_aspect(sr_planets['Moon']['lon'], sr_planets['Rahu']['lon'], 0, orb=general_orb)
    indicators.append({"id": 31, "code": "P31", "category": "اتصالات كواكب", "name_ar": "اقتران القمر السنوي مع راهو (العقدة الشمالية)", "description": "تطور قدري في شؤون الأمومة والنسل.", "is_active": m31, "detail": f"اقتران بفارق {diff31:.2f}°" if m31 else "غير مقترن"})

    m32, diff32 = is_aspect(sr_planets['Jupiter']['lon'], sr_planets['Rahu']['lon'], 0, orb=general_orb)
    indicators.append({"id": 32, "code": "P32", "category": "اتصالات كواكب", "name_ar": "اقتران المشتري السنوي مع راهو (العقدة الشمالية)", "description": "توسع كبير ومقدر في الذرية والأبناء.", "is_active": m32, "detail": f"اقتران بفارق {diff32:.2f}°" if m32 else "غير مقترن"})

    m33, asp33, diff33 = is_soft_or_conjunction(sr_planets['Moon']['lon'], sr_planets['Pluto']['lon'], orb=general_orb)
    indicators.append({"id": 33, "code": "P33", "category": "اتصالات كواكب", "name_ar": "اتصال متناغم بين القمر وبلوتو السنويين", "description": "تجدد بيولوجي عميق وتحول جذري بالحياة.", "is_active": m33, "detail": f"{asp33} بفارق {diff33:.2f}°" if m33 else "غير متصل"})

    indicators.append({"id": 34, "code": "P34", "category": "حكام بيوت الإنجاب", "name_ar": f"حاكم الخامس السنوي في البيت الأول السنوي", "description": "الطفل يقبل مباشرة نحو الأم.", "is_active": sr_planets[sr_5th_ruler]['house'] == 1, "detail": f"حاكم الخامس في البيت {sr_planets[sr_5th_ruler]['house']}"})
    indicators.append({"id": 35, "code": "P35", "category": "حكام بيوت الإنجاب", "name_ar": f"حاكم الأول السنوي في البيت الخامس السنوي", "description": "تركيز طاقة الأم وحياتها بالكامل على الحمل.", "is_active": sr_planets[sr_1st_ruler]['house'] == 5, "detail": f"حاكم الأول في البيت {sr_planets[sr_1st_ruler]['house']}"})
    indicators.append({"id": 36, "code": "P36", "category": "حكام بيوت الإنجاب", "name_ar": f"حاكم الخامس السنوي في البيت الخامس السنوي", "description": "قوة واستقلالية بيت الأطفال وتيسير شؤون الحمل.", "is_active": sr_planets[sr_5th_ruler]['house'] == 5, "detail": f"حاكم الخامس في البيت {sr_planets[sr_5th_ruler]['house']}"})
    indicators.append({"id": 37, "code": "P37", "category": "حكام بيوت الإنجاب", "name_ar": f"حاكم الخامس السنوي في البيت الرابع السنوي", "description": "قدوم الطفل إلى داخل بيت الأسرة.", "is_active": sr_planets[sr_5th_ruler]['house'] == 4, "detail": f"حاكم الخامس في البيت {sr_planets[sr_5th_ruler]['house']}"})

    m38, asp38, diff38 = is_soft_or_conjunction(sr_1st_ruler_lon, sr_5th_ruler_lon, orb=general_orb)
    indicators.append({"id": 38, "code": "P38", "category": "حكام بيوت الإنجاب", "name_ar": "اتصال سعيد بين حاكم الطالع وحاكم الخامس", "description": "الالتقاء المباشر بين الأم ومولودها.", "is_active": m38, "detail": f"{asp38} بفارق {diff38:.2f}°" if m38 else "غير متصل"})

    m39, asp39, diff39 = is_soft_or_conjunction(sr_5th_ruler_lon, sr_planets['Jupiter']['lon'], orb=general_orb)
    indicators.append({"id": 39, "code": "P39", "category": "حكام بيوت الإنجاب", "name_ar": "اتصال سعيد بين حاكم الخامس والمشتري", "description": "مباركة المشتري لدليل الأطفال.", "is_active": m39, "detail": f"{asp39} بفارق {diff39:.2f}°" if m39 else "غير متصل"})

    m40, asp40, diff40 = is_soft_or_conjunction(sr_5th_ruler_lon, sr_planets['Moon']['lon'], orb=general_orb)
    indicators.append({"id": 40, "code": "P40", "category": "حكام بيوت الإنجاب", "name_ar": "اتصال سعيد بين حاكم الخامس والقمر", "description": "تفعيل الخصوبة وحصول الحمل الفعلي.", "is_active": m40, "detail": f"{asp40} بفارق {diff40:.2f}°" if m40 else "غير متصل"})

    m41, asp41, diff41 = is_soft_or_conjunction(sr_planets['Jupiter']['lon'], n_5th_ruler_lon, orb=general_orb)
    indicators.append({"id": 41, "code": "P41", "category": "حكام بيوت الإنجاب", "name_ar": "المشتري السنوي يتصل بحاكم الخامس الميلادي", "description": "تنشيط دليل الإنجاب الأصلي بسعد المشتري.", "is_active": m41, "detail": f"{asp41} بفارق {diff41:.2f}°" if m41 else "غير متصل"})

    m42, asp42, diff42 = is_soft_or_conjunction(sr_planets['Moon']['lon'], n_5th_ruler_lon, orb=general_orb)
    indicators.append({"id": 42, "code": "P42", "category": "حكام بيوت الإنجاب", "name_ar": "القمر السنوي يتصل بحاكم الخامس الميلادي", "description": "تحريك طاقة الحمل والولادة في الخريطة الأصلية.", "is_active": m42, "detail": f"{asp42} بفارق {diff42:.2f}°" if m42 else "غير متصل"})

    m43, asp43, diff43 = is_soft_or_conjunction(sr_4th_ruler_lon, sr_5th_ruler_lon, orb=general_orb)
    indicators.append({"id": 43, "code": "P43", "category": "حكام بيوت الإنجاب", "name_ar": "اتصال سعيد بين حاكم الرابع وحاكم الخامس", "description": "تآلف بين بيت الأسرة وبيت الأطفال لاستقبال مولود.", "is_active": m43, "detail": f"{asp43} بفارق {diff43:.2f}°" if m43 else "غير متصل"})

    indicators.append({"id": 44, "code": "P44", "category": "العقد والسهام", "name_ar": "راهو السنوي في البيت الخامس السنوي", "description": "دخول عقدة القدر في بيت الأطفال.", "is_active": sr_planets['Rahu']['house'] == 5, "detail": f"راهو في البيت {sr_planets['Rahu']['house']}"})
    indicators.append({"id": 45, "code": "P45", "category": "العقد والسهام", "name_ar": "راهو السنوي في البيت الحادي عشر السنوي", "description": "تفعيل محور الإنجاب (5 - 11) وتحقيق أمنية الذرية.", "is_active": sr_planets['Rahu']['house'] == 11, "detail": f"راهو في البيت {sr_planets['Rahu']['house']}"})

    p_in_5_child = [p for p, d in sr_planets.items() if d['house'] == 5]
    indicators.append({"id": 46, "code": "P46", "category": "العقد والسهام", "name_ar": f"تجمع كوكبي في البيت الخامس ({len(p_in_5_child)} كواكب)", "description": "تركيز طاقي مكثف في بيت الأطفال.", "is_active": len(p_in_5_child) >= 2, "detail": f"الكواكب: {', '.join(p_in_5_child)}" if p_in_5_child else "أقل من كوكبين"})

    water_signs = [3, 7, 11]
    moon_fertile = sr_planets['Moon']['sign'] in water_signs and sr_planets['Moon']['house'] in [1, 4, 5, 7, 10, 11]
    indicators.append({"id": 47, "code": "P47", "category": "العقد والسهام", "name_ar": "القمر السنوي في برج مائي خصب وبيت فاعل", "description": "ذروة الخصوبة البيولوجية والاستعداد الجسدي.", "is_active": moon_fertile, "detail": f"القمر في البيت {sr_planets['Moon']['house']}" if moon_fertile else "غير متحقق"})

    jup_fertile = sr_planets['Jupiter']['sign'] in water_signs and sr_planets['Jupiter']['house'] in [1, 4, 5, 7, 10, 11]
    indicators.append({"id": 48, "code": "P48", "category": "العقد والسهام", "name_ar": "المشتري السنوي في برج مائي خصب وبيت فاعل", "description": "وفرة في النسل والبركة في الإنجاب.", "is_active": jup_fertile, "detail": f"المشتري في البيت {sr_planets['Jupiter']['house']}" if jup_fertile else "غير متحقق"})

    m49_j, _, _ = is_soft_or_conjunction(sr_children_part, sr_planets['Jupiter']['lon'], orb=general_orb)
    m49_m, _, _ = is_soft_or_conjunction(sr_children_part, sr_planets['Moon']['lon'], orb=general_orb)
    d49 = m49_j or m49_m
    indicators.append({"id": 49, "code": "P49", "category": "العقد والسهام", "name_ar": "تفعيل سهم الأولاد مع المشتري أو القمر", "description": "سهم الذرية يتلقى اتصالاً مباشراً من أدلة الإنجاب.", "is_active": d49, "detail": "سهم الأولاد مفعل" if d49 else "غير مفعل"})

    d50 = len(activated_midpoints_list) >= 2
    indicators.append({"id": 50, "code": "P50", "category": "العقد والسهام", "name_ar": "تفعيل 2 ميد بوينت على الأقل من نقاط الإنجاب الـ 7 (أورب < 2.0°)", "description": "تفعيل نقطتي منتصف على الأقل من نقاط الإنجاب بالاقتران أو المقابلة.", "is_active": d50, "detail": f"نقاط المنتصف المفعلة: {len(activated_midpoints_list)}" if d50 else "أقل من نقطتين"})

    active_count = sum(1 for ind in indicators if ind['is_active'])
    return {
        "active_count": active_count,
        "indicators": indicators,
        "activated_midpoints": activated_midpoints_list
    }

# =============================================================================
# 7. مولدات التقارير HTML (تقارير منفصلة للزواج وللحمل/الإنجاب)
# =============================================================================
def generate_marriage_html_report(native_info, candidate_years):
    report_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    gender_title = "العروس / الزوجة المستقبلية" if native_info['gender'] == "ذكر" else "العريس / الزوج المستقبلي"
    partner_noun = "العروس" if native_info['gender'] == "ذكر" else "العريس"

    html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>تقرير سنوات الزواج والارتباط الفلكي - {native_info['name']}</title>
    <link href="https://fonts.googleapis.com/css2?family=Amiri:wght@700&family=Cairo:wght@400;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Cairo', sans-serif; direction: rtl; background: #f8fafc; color: #1e293b; padding: 30px; font-size: 14px; }}
        .container {{ max-width: 1100px; margin: 0 auto; background: #fff; padding: 40px; border-radius: 12px; border: 1px solid #cbd5e1; }}
        .header {{ text-align: center; background: linear-gradient(135deg, #0d1b2a, #1b263b); color: #fff; padding: 25px; border-radius: 10px; border: 2px solid #c59b27; margin-bottom: 30px; }}
        .header h1 {{ font-family: 'Amiri', serif; font-size: 28px; color: #e6ca65; margin-bottom: 6px; }}
        .card {{ background: #fff; border: 1px solid #cbd5e1; border-radius: 10px; padding: 20px; margin-bottom: 25px; }}
        .card-header {{ font-size: 18px; font-weight: 800; color: #1a2a44; border-bottom: 2px solid #c59b27; padding-bottom: 10px; margin-bottom: 15px; }}
        .grid-3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; }}
        .data-item {{ background: #f8fafc; padding: 12px; border-radius: 8px; border-right: 4px solid #c59b27; }}
        .data-item label {{ display: block; font-size: 12px; color: #64748b; font-weight: 600; }}
        .data-item span {{ font-size: 14px; font-weight: 700; color: #1a2a44; }}
        .year-section {{ background: #fff; border: 2px solid #c59b27; border-radius: 10px; padding: 25px; margin-bottom: 30px; }}
        .year-bar {{ background: #1a2a44; color: #fff; padding: 12px 20px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }}
        .traits-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }}
        .trait-box {{ background: #fcf8e8; border: 1px solid #e2e8f0; border-top: 3px solid #c59b27; border-radius: 8px; padding: 15px; }}
        .indicators-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 12px; }}
        .indicators-table th {{ background: #1e293b; color: #fff; text-align: right; padding: 8px; }}
        .indicators-table td {{ padding: 8px; border-bottom: 1px solid #e2e8f0; }}
        .status-badge {{ padding: 3px 8px; border-radius: 12px; font-weight: 700; font-size: 11px; }}
        .status-badge.active {{ background: #dcfce7; color: #15803d; }}
        .status-badge.inactive {{ background: #f1f5f9; color: #94a3b8; }}
        .footer {{ text-align: center; margin-top: 40px; color: #64748b; font-size: 12px; border-top: 1px solid #cbd5e1; pt: 20px; }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>تقرير دراسة سنوات الزواج والارتباط الفلكي</h1>
        <p>تحليل دقيق يعتمد على محور نقطة منتصف الشمس/القمر والـ 50 دلالة زواج</p>
    </div>
    <div class="card">
        <div class="card-header">البيانات الأساسية لصاحب/ة الخريطة</div>
        <div class="grid-3">
            <div class="data-item"><label>الاسم</label><span>{native_info['name']}</span></div>
            <div class="data-item"><label>الجنس</label><span>{native_info['gender']}</span></div>
            <div class="data-item"><label>تاريخ الميلاد</label><span>{native_info['birth_date']} | {native_info['birth_time']}</span></div>
            <div class="data-item"><label>مكان الميلاد</label><span>{native_info['birth_city']}</span></div>
            <div class="data-item"><label>مكان السنوية</label><span>{native_info['sr_city']}</span></div>
            <div class="data-item"><label>ميد بوينت (شمس/قمر)</label><span>{native_info['midpoint_deg']:.2f}° {native_info['midpoint_sign']}</span></div>
        </div>
    </div>
"""

    if not candidate_years:
        html += "<div class='card' style='text-align: center; color: #b91c1c;'><h3>لم يتم رصد سنوات مطابقة للشروط الصارمة للزواج.</h3></div>"
    else:
        for y in candidate_years:
            p_desc = y['partner_physical']
            p_car = y['partner_career']
            p_int = y['partner_intimacy']
            p_wlth = y['partner_wealth']
            p_wed = y['wedding_style']
            p_soc = y['partner_social']
            prim = y['primary_activator']

            html += f"""
    <div class="year-section">
        <div class="year-bar">
            <h2>سنة الزواج: {y['year']} ميلادي (العمر: {y['age']} سنة)</h2>
            <div style="background: #c59b27; color: #0d1b2a; padding: 4px 12px; border-radius: 15px; font-weight: 800;">تحقق {y['active_count']} من 50 دلالة</div>
        </div>
        <p style="margin-bottom: 15px; color: #334155;"><strong>الكوكب المفعل للمحور:</strong> {p_desc['planet_ar']} — {prim['aspect_type']} (بفارق: {y['midpoint_diff_str']})</p>
        
        <div class="traits-grid">
            <div class="trait-box">
                <h3 style="color: #1a2a44; margin-bottom: 8px;">👑 الصفات الشكلية والعمر</h3>
                <p><strong>{p_desc['title']}</strong></p>
                <p style="margin-top: 5px;"><strong>الملامح:</strong> {p_desc['face']}</p>
                <p style="margin-top: 5px;"><strong>البنية:</strong> {p_desc['height_build']}</p>
                <p style="margin-top: 5px; color: #b45309;"><strong>العمر التقديري:</strong> {p_desc['age_bracket']}</p>
            </div>
            <div class="trait-box">
                <h3 style="color: #1a2a44; margin-bottom: 8px;">💼 مهنة العمل</h3>
                <p><strong>البرج الحاكم:</strong> {p_car['sign']} ({p_car['ruler']})</p>
                <p style="margin-top: 5px;">{p_car['career_description']}</p>
            </div>
            <div class="trait-box">
                <h3 style="color: #1a2a44; margin-bottom: 8px;">❤️ العلاقة الحميمية</h3>
                <p><strong>العنصر:</strong> {p_int['element']} ({p_int['sign']})</p>
                <p style="margin-top: 5px;">{p_int['intimacy_description']}</p>
            </div>
            <div class="trait-box">
                <h3 style="color: #1a2a44; margin-bottom: 8px;">💰 الثروة والوضع المالي</h3>
                <p><strong>البرج:</strong> {p_wlth['sign']}</p>
                <p style="margin-top: 5px;">{p_wlth['wealth_description']}</p>
            </div>
            <div class="trait-box">
                <h3 style="color: #1a2a44; margin-bottom: 8px;">🎉 حفل الزفاف</h3>
                <p><strong>{p_wed['style']}</strong></p>
                <p style="margin-top: 5px;">{p_wed['description']}</p>
            </div>
            <div class="trait-box">
                <h3 style="color: #1a2a44; margin-bottom: 8px;">🌍 الظروف والنسب</h3>
                <p>• <strong>صلة القرابة:</strong> {p_soc['relative']['status']}</p>
                <p>• <strong>الإقامة:</strong> {p_soc['residence']['status']}</p>
                <p>• <strong>الجنسية:</strong> {p_soc['expatriate']['status']}</p>
                <p>• <strong>التعارف:</strong> {p_soc['history']['status']}</p>
            </div>
        </div>

        <div style="margin-top: 20px;">
            <h4 style="color: #1a2a44; margin-bottom: 10px;">جدول فحص وتدقيق الـ 50 دلالة زواج لسنة {y['year']} — المتحقق: {y['active_count']} دلالة إيجابية</h4>
            <table class="indicators-table">
                <thead>
                    <tr>
                        <th style="width: 50px;">الرمز</th>
                        <th>الفئة والفعل</th>
                        <th style="width: 90px; text-align: center;">الحالة</th>
                        <th>التفاصيل</th>
                    </tr>
                </thead>
                <tbody>
            """
            for ind in y['indicators']:
                st_cls = "active" if ind['is_active'] else "inactive"
                st_txt = "متحققة ✓" if ind['is_active'] else "غير متحققة"
                bg_col = "background: #f0fdf4;" if ind['is_active'] else ""
                html += f"""
                    <tr style="{bg_col}">
                        <td style="font-weight: 700;">{ind['code']}</td>
                        <td><strong>{ind['name_ar']}</strong><br><span style="color:#64748b; font-size:11px;">{ind['description']}</span></td>
                        <td style="text-align: center;"><span class="status-badge {st_cls}">{st_txt}</span></td>
                        <td style="font-size: 11.5px;">{ind['detail']}</td>
                    </tr>
                """
            html += """
                </tbody>
            </table>
        </div>
    </div>
            """

    html += """
    <div class="footer">
        <p>تقرير صادر عن حاسبة الأبحاث الفلكية التخصصية — الفلكي الدكتور استرو رادار</p>
    </div>
</div>
</body>
</html>
"""
    return html

def generate_childbirth_html_report(native_info, candidate_years):
    report_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>تقرير سنوات الحمل والإنجاب الفلكي - {native_info['name']}</title>
    <link href="https://fonts.googleapis.com/css2?family=Amiri:wght@700&family=Cairo:wght@400;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Cairo', sans-serif; direction: rtl; background: #f8fafc; color: #1e293b; padding: 30px; font-size: 14px; }}
        .container {{ max-width: 1100px; margin: 0 auto; background: #fff; padding: 40px; border-radius: 12px; border: 1px solid #cbd5e1; }}
        .header {{ text-align: center; background: linear-gradient(135deg, #022c22, #064e3b); color: #fff; padding: 25px; border-radius: 10px; border: 2px solid #10b981; margin-bottom: 30px; }}
        .header h1 {{ font-family: 'Amiri', serif; font-size: 28px; color: #6ee7b7; margin-bottom: 6px; }}
        .card {{ background: #fff; border: 1px solid #cbd5e1; border-radius: 10px; padding: 20px; margin-bottom: 25px; }}
        .card-header {{ font-size: 18px; font-weight: 800; color: #064e3b; border-bottom: 2px solid #10b981; padding-bottom: 10px; margin-bottom: 15px; }}
        .grid-3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; }}
        .data-item {{ background: #f8fafc; padding: 12px; border-radius: 8px; border-right: 4px solid #059669; }}
        .data-item label {{ display: block; font-size: 12px; color: #64748b; font-weight: 600; }}
        .data-item span {{ font-size: 14px; font-weight: 700; color: #064e3b; }}
        .year-section {{ background: #fff; border: 2px solid #10b981; border-radius: 10px; padding: 25px; margin-bottom: 30px; }}
        .year-bar {{ background: #064e3b; color: #fff; padding: 12px 20px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }}
        .indicators-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 12px; }}
        .indicators-table th {{ background: #065f46; color: #fff; text-align: right; padding: 8px; }}
        .indicators-table td {{ padding: 8px; border-bottom: 1px solid #e2e8f0; }}
        .status-badge {{ padding: 3px 8px; border-radius: 12px; font-weight: 700; font-size: 11px; }}
        .status-badge.active {{ background: #dcfce7; color: #15803d; }}
        .status-badge.inactive {{ background: #f1f5f9; color: #94a3b8; }}
        .footer {{ text-align: center; margin-top: 40px; color: #64748b; font-size: 12px; border-top: 1px solid #cbd5e1; pt: 20px; }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>تقرير دراسة سنوات الحمل والإنجاب الفلكي</h1>
        <p>تحليل يعتمد على اقتران أو مقابلة الكوكب السنوي بنقاط المنتصف الـ 7 للإنجاب (أورب < 2.0°)</p>
    </div>
    <div class="card">
        <div class="card-header">البيانات الأساسية للمولودة</div>
        <div class="grid-3">
            <div class="data-item"><label>الاسم</label><span>{native_info['name']}</span></div>
            <div class="data-item"><label>تاريخ الميلاد</label><span>{native_info['birth_date']} | {native_info['birth_time']}</span></div>
            <div class="data-item"><label>مكان الميلاد / السنوية</label><span>{native_info['birth_city']} / {native_info['sr_city']}</span></div>
        </div>
    </div>
"""

    if not candidate_years:
        html += "<div class='card' style='text-align: center; color: #b91c1c;'><h3>لم يتم رصد سنوات مطابقة للشروط الصارمة للحمل والإنجاب.</h3></div>"
    else:
        for y in candidate_years:
            html += f"""
    <div class="year-section">
        <div class="year-bar">
            <h2>سنة الحمل والإنجاب: {y['year']} ميلادي (العمر: {y['age']} سنة)</h2>
            <div style="background: #10b981; color: #fff; padding: 4px 12px; border-radius: 15px; font-weight: 800;">تفعيل {y['midpoints_count']} ميد بوينت | {y['active_count']} دلالة</div>
        </div>
        <div style="background: #fef3c7; padding: 12px; border-radius: 8px; border-right: 4px solid #d97706; margin-bottom: 15px;">
            <h4 style="color: #92400e; margin-bottom: 5px;">🎯 نقاط المنتصف المفعلة بالاقتران أو المقابلة (أورب < 2.0°):</h4>
            <ul style="padding-right: 20px;">
            """
            for mp in y['activated_midpoints']:
                acts_str = " ، ".join([f"كوكب <strong>{a['planet_ar']}</strong> ({a['aspect_type']} في برج {a['sign_name']} بفارق {a['diff']:.2f}°)" for a in mp['activators']])
                html += f"<li>ميد بوينت [{mp['midpoint_name']}]: تم تفعيله بواسطة {acts_str}.</li>"
            html += f"""
            </ul>
        </div>

        <div style="margin-top: 20px;">
            <h4 style="color: #064e3b; margin-bottom: 10px;">جدول فحص وتدقيق الـ 50 دلالة فلكية للحمل والإنجاب لسنة {y['year']} — المتحقق: {y['active_count']} دلالة إيجابية</h4>
            <table class="indicators-table">
                <thead>
                    <tr>
                        <th style="width: 50px;">الرمز</th>
                        <th>الفئة والفعل</th>
                        <th style="width: 90px; text-align: center;">الحالة</th>
                        <th>التفاصيل</th>
                    </tr>
                </thead>
                <tbody>
            """
            for ind in y['indicators']:
                st_cls = "active" if ind['is_active'] else "inactive"
                st_txt = "متحققة ✓" if ind['is_active'] else "غير متحققة"
                bg_col = "background: #f0fdf4;" if ind['is_active'] else ""
                html += f"""
                    <tr style="{bg_col}">
                        <td style="font-weight: 700;">{ind['code']}</td>
                        <td><strong>{ind['name_ar']}</strong><br><span style="color:#64748b; font-size:11px;">{ind['description']}</span></td>
                        <td style="text-align: center;"><span class="status-badge {st_cls}">{st_txt}</span></td>
                        <td style="font-size: 11.5px;">{ind['detail']}</td>
                    </tr>
                """
            html += """
                </tbody>
            </table>
        </div>
    </div>
            """

    html += """
    <div class="footer">
        <p>تقرير صادر عن حاسبة الأبحاث الفلكية التخصصية — الفلكي الدكتور استرو رادار</p>
    </div>
</div>
</body>
</html>
"""
    return html

# =============================================================================
# 8. واجهة المستخدم الرئيسية وتدفق التنفيذ الموحد
# =============================================================================
st.markdown("""
<div class="main-header">
    <h1>حاسبة احتمالات سنوات الزواج والحمل والإنجاب الفلكية الشاملة</h1>
    <p>تحليل فلكي غربي متقدم يدمج محور نقطة المنتصف، العودة الشمسية، والـ 100 دلالة تخصصية</p>
    <p>تطوير الفلكي استرو رادار</p>
</div>
""", unsafe_allow_html=True)

with st.container():
    col1, col2, col3, col4 = st.columns([1.2, 1, 1.2, 1.2])
    
    with col1:
        st.markdown("#### 👤 البيانات الشخصية")
        name = st.text_input("اسم صاحب/ة الخريطة", "سارة")
        gender = st.selectbox("الجنس", ["أنثى", "ذكر"], index=0, help="يحدد توقع مواصفات الشريك")
        partner_title = "العريس" if gender == "أنثى" else "العروس"

    with col2:
        st.markdown("#### 📅 تاريخ ووقت الميلاد")
        birth_date = st.date_input("تاريخ الميلاد", value=datetime.date(2000, 1, 1), min_value=datetime.date(1950, 1, 1))
        birth_time = st.time_input("ساعة الميلاد بدقة", value=datetime.time(14, 30), step=datetime.timedelta(minutes=1))

    with col3:
        st.markdown("#### 🌍 مكان الميلاد")
        default_b_country_idx = country_list.index("Syria") if "Syria" in country_list else 0
        b_country_name = st.selectbox("دولة الميلاد", country_list, index=default_b_country_idx, key="b_country_select")
        b_c_code = country_map[b_country_name]
        b_city_objects = cities_by_country.get(b_c_code, [])
        b_city_names = [c['name'] for c in b_city_objects] if b_city_objects else [b_country_name]
        b_city_name = st.selectbox("مدينة الميلاد", b_city_names, index=0, key="b_city_select")

    with col4:
        st.markdown("#### 📍 مكان السنوية (الإقامة الحالية)")
        default_sr_country_idx = country_list.index("United Arab Emirates") if "United Arab Emirates" in country_list else 0
        sr_country_name = st.selectbox("دولة السنوية", country_list, index=default_sr_country_idx, key="sr_country_select")
        sr_c_code = country_map[sr_country_name]
        sr_city_objects = cities_by_country.get(sr_c_code, [])
        sr_city_names = [c['name'] for c in sr_city_objects] if sr_city_objects else [sr_country_name]
        sr_city_name = st.selectbox("مدينة السنوية", sr_city_names, index=0, key="sr_city_select")

# الثوابت الفلكية الصارمة المعتمدة
FIXED_ASPECT_ORB = 1.0       # أورب الاتصالات العامة
FIXED_MIDPOINT_ORB = 2.0     # أورب الميد بوينت
FIXED_MIN_MARRIAGE_IND = 5   # 5 دلالات للزواج
FIXED_MIN_CHILD_IND = 3      # 3 دلالات للحمل
SCAN_AGE_MIN = 16            # العمر من 16 سنة
SCAN_AGE_MAX_MARRIAGE = 56   # لغاية 56 سنة للزواج
SCAN_AGE_MAX_CHILDBIRTH = 42 # لغاية 42 سنة للإنجاب

st.info("📌 **القواعد الفلكية الصارمة المطبقة آلياً:** تحليل مزدوج (الزواج والحمل والإنجاب) بمعايير دقيقة لنقاط المنتصف والاتصالات السنوية.")

submit = st.button("🔮 بدء التحليل الفلكي الشامل (الزواج + الحمل والإنجاب)", type="primary")

if submit:
    b_city_obj = next((c for c in b_city_objects if c['name'] == b_city_name), None)
    sr_city_obj = next((c for c in sr_city_objects if c['name'] == sr_city_name), None)
    
    b_lat, b_lon = (b_city_obj['latitude'], b_city_obj['longitude']) if b_city_obj else (33.5138, 36.2765)
    sr_lat, sr_lon = (sr_city_obj['latitude'], sr_city_obj['longitude']) if sr_city_obj else (25.2048, 55.2708)
        
    b_tz = tf.timezone_at(lng=b_lon, lat=b_lat) or "UTC"
    
    jd_birth = get_utc_julian_day(birth_date, birth_time, b_tz)
    natal_cusps, _ = swe.houses(jd_birth, b_lat, b_lon, b'R')
    
    natal_planets = {}
    for p_name, p_id in PLANET_IDS.items():
        res = swe.calc_ut(jd_birth, p_id)
        lon = res[0][0]
        speed = res[0][3]
        natal_planets[p_name] = {
            'lon': lon,
            'sign': int(lon / 30) % 12,
            'deg_in_sign': lon % 30,
            'house': get_house_of_point(lon, natal_cusps),
            'is_retrograde': speed < 0
        }
        
    natal_rahu_lon = natal_planets['Rahu']['lon']
    natal_ketu_lon = (natal_rahu_lon + 180) % 360
    natal_planets['Ketu'] = {
        'lon': natal_ketu_lon,
        'sign': int(natal_ketu_lon / 30) % 12,
        'deg_in_sign': natal_ketu_lon % 30,
        'house': get_house_of_point(natal_ketu_lon, natal_cusps),
        'is_retrograde': False
    }

    natal_sun = natal_planets['Sun']['lon']
    natal_moon = natal_planets['Moon']['lon']
    
    marriage_midpoint_lon = (natal_sun + natal_moon) / 2.0
    if abs(natal_sun - natal_moon) > 180:
        marriage_midpoint_lon = (marriage_midpoint_lon + 180) % 360

    # نقاط المنتصف الـ 7 للإنجاب
    childbirth_midpoints = [
        {"name": "القمر / يورانوس", "lon": calculate_midpoint(natal_planets['Moon']['lon'], natal_planets['Uranus']['lon'])},
        {"name": "القمر / الزهرة", "lon": calculate_midpoint(natal_planets['Moon']['lon'], natal_planets['Venus']['lon'])},
        {"name": "المشتري / الزهرة", "lon": calculate_midpoint(natal_planets['Jupiter']['lon'], natal_planets['Venus']['lon'])},
        {"name": "المشتري / المريخ", "lon": calculate_midpoint(natal_planets['Jupiter']['lon'], natal_planets['Mars']['lon'])},
        {"name": "المشتري / الشمس", "lon": calculate_midpoint(natal_planets['Jupiter']['lon'], natal_planets['Sun']['lon'])},
        {"name": "القمر / المشتري", "lon": calculate_midpoint(natal_planets['Moon']['lon'], natal_planets['Jupiter']['lon'])},
        {"name": "الشمس / القمر", "lon": calculate_midpoint(natal_planets['Sun']['lon'], natal_planets['Moon']['lon'])},
    ]

    natal_data = {
        'cusps': natal_cusps,
        'planets': natal_planets,
        'midpoint_lon': marriage_midpoint_lon,
        'childbirth_midpoints': childbirth_midpoints
    }

    # =========================================================================
    # مسح سنوات الزواج (من 16 إلى 56 سنة)
    # =========================================================================
    marriage_years = []
    start_y_m = birth_date.year + SCAN_AGE_MIN
    end_y_m = birth_date.year + SCAN_AGE_MAX_MARRIAGE
    years_m = list(range(start_y_m, end_y_m + 1))
    
    progress_bar = st.progress(0.0)
    status_text = st.empty()

    for i, target_year in enumerate(years_m):
        progress_bar.progress(min(1.0, (i + 1) / len(years_m)))
        status_text.text(f"جاري حساب دلالات الزواج لعام {target_year} م...")
        
        jd_sr = find_exact_solar_return(target_year, natal_sun, birth_date.month, birth_date.day, birth_time, b_tz)
        sr_cusps, _ = swe.houses(jd_sr, sr_lat, sr_lon, b'R')
        
        sr_planets = {}
        for p_name, p_id in PLANET_IDS.items():
            res = swe.calc_ut(jd_sr, p_id)
            lon = res[0][0]
            sr_planets[p_name] = {'lon': lon, 'sign': int(lon / 30) % 12, 'deg_in_sign': lon % 30, 'house': get_house_of_point(lon, sr_cusps)}
            
        sr_rahu_lon = sr_planets['Rahu']['lon']
        sr_ketu_lon = (sr_rahu_lon + 180) % 360
        sr_planets['Ketu'] = {'lon': sr_ketu_lon, 'sign': int(sr_ketu_lon / 30) % 12, 'deg_in_sign': sr_ketu_lon % 30, 'house': get_house_of_point(sr_ketu_lon, sr_cusps)}

        sr_data = {'cusps': sr_cusps, 'planets': sr_planets}
        eval_m = evaluate_marriage_50_indicators(natal_data, sr_data, general_orb=FIXED_ASPECT_ORB, midpoint_orb=FIXED_MIDPOINT_ORB)

        if eval_m['activated_midpoints'] and eval_m['active_count'] >= FIXED_MIN_MARRIAGE_IND:
            prim = eval_m['activated_midpoints'][0]
            p_phys = get_physical_appearance(prim['planet'], prim['lon'], partner_title=partner_title)
            p_car = derive_partner_career(natal_cusps, natal_planets)
            p_int = derive_partner_intimacy(natal_cusps, natal_planets)
            p_wlth = derive_partner_wealth(natal_cusps, natal_planets)
            p_wed = derive_wedding_party(natal_cusps, sr_cusps[0], sr_planets)
            p_soc = derive_partner_social_details(natal_cusps, natal_planets)

            diff_str = f"{prim['diff']:.2f}°"
            marriage_years.append({
                "year": target_year,
                "age": target_year - birth_date.year,
                "active_count": eval_m['active_count'],
                "indicators": eval_m['indicators'],
                "primary_activator": prim,
                "midpoint_diff_str": diff_str,
                "partner_physical": p_phys,
                "partner_career": p_car,
                "partner_intimacy": p_int,
                "partner_wealth": p_wlth,
                "wedding_style": p_wed,
                "partner_social": p_soc
            })

    # =========================================================================
    # مسح سنوات الحمل والإنجاب (من 16 إلى 42 سنة)
    # =========================================================================
    childbirth_years = []
    start_y_c = birth_date.year + SCAN_AGE_MIN
    end_y_c = birth_date.year + SCAN_AGE_MAX_CHILDBIRTH
    years_c = list(range(start_y_c, end_y_c + 1))

    for i, target_year in enumerate(years_c):
        status_text.text(f"جاري حساب دلالات الحمل والإنجاب لعام {target_year} م...")
        
        jd_sr = find_exact_solar_return(target_year, natal_sun, birth_date.month, birth_date.day, birth_time, b_tz)
        sr_cusps, _ = swe.houses(jd_sr, sr_lat, sr_lon, b'R')
        
        sr_planets = {}
        for p_name, p_id in PLANET_IDS.items():
            res = swe.calc_ut(jd_sr, p_id)
            lon = res[0][0]
            sr_planets[p_name] = {'lon': lon, 'sign': int(lon / 30) % 12, 'deg_in_sign': lon % 30, 'house': get_house_of_point(lon, sr_cusps)}
            
        sr_rahu_lon = sr_planets['Rahu']['lon']
        sr_ketu_lon = (sr_rahu_lon + 180) % 360
        sr_planets['Ketu'] = {'lon': sr_ketu_lon, 'sign': int(sr_ketu_lon / 30) % 12, 'deg_in_sign': sr_ketu_lon % 30, 'house': get_house_of_point(sr_ketu_lon, sr_cusps)}

        sr_data = {'cusps': sr_cusps, 'planets': sr_planets}
        eval_c = evaluate_childbirth_50_indicators(natal_data, sr_data, general_orb=1.5, midpoint_orb=FIXED_MIDPOINT_ORB)

        if len(eval_c['activated_midpoints']) >= 2 and eval_c['active_count'] >= FIXED_MIN_CHILD_IND:
            childbirth_years.append({
                "year": target_year,
                "age": target_year - birth_date.year,
                "active_count": eval_c['active_count'],
                "indicators": eval_c['indicators'],
                "activated_midpoints": eval_c['activated_midpoints'],
                "midpoints_count": len(eval_c['activated_midpoints'])
            })

    status_text.empty()
    progress_bar.empty()

    native_info = {
        'name': name,
        'gender': gender,
        'birth_date': birth_date.strftime("%Y-%m-%d"),
        'birth_time': birth_time.strftime("%H:%M"),
        'birth_city': b_city_name,
        'sr_city': sr_city_name,
        'midpoint_deg': marriage_midpoint_lon % 30,
        'midpoint_sign': ZODIAC_NAMES_AR[int(marriage_midpoint_lon/30)%12]
    }

    # توليد ملفات HTML للتقارير
    marriage_html = generate_marriage_html_report(native_info, marriage_years)
    childbirth_html = generate_childbirth_html_report(native_info, childbirth_years)

    st.markdown("---")
    st.subheader("📑 التقارير الفلكية الشاملة الجاهزة للتحميل والطباعة")
    
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        st.download_button(
            label=f"📥 تقرير سنوات الزواج والارتباط لـ ({name}) [HTML/PDF]",
            data=marriage_html,
            file_name=f"تقرير_الزواج_{name}.html",
            mime="text/html",
            use_container_width=True
        )
        st.success(f"تم رصد **{len(marriage_years)}** سنة مرشحة للزواج.")

    with col_btn2:
        st.download_button(
            label=f"📥 تقرير سنوات الحمل والإنجاب لـ ({name}) [HTML/PDF]",
            data=childbirth_html,
            file_name=f"تقرير_الحمل_والإنجاب_{name}.html",
            mime="text/html",
            use_container_width=True
        )
        st.success(f"تم رصد **{len(childbirth_years)}** سنة مرشحة للحمل والإنجاب.")

    st.markdown("---")
