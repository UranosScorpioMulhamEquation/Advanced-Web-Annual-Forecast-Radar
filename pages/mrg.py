# marriage_astrology_pro_single.py
"""
حاسبة احتمالات سنوات الزواج والارتباط العاطفي الفلكية الشاملة (الـ 50 دلالة) - الإصدار الموحد المتكامل
وفقاً للتنجيم الغربي، عودة الشمس (Solar Return)، ونقاط المنتصف والمحاور (Midpoints Axis) واشتقاق البيوت (Derived Houses).
إعداد وتطوير: الفلكي الدكتور استرو رادار.
"""

import streamlit as st
import swisseph as swe
import datetime
import pytz
from timezonefinder import TimezoneFinder
import geonamescache
import os
# ==========================================
# ==================== إعدادات Swiss Ephemeris ====================
swe.set_ephe_path('')  # استخدام وضع Moshier الافتراضي للتقويم الفلكي الدقيق

# =============================================================================
# 1. إعدادات الصفحة والتنسيق البصري العربي الاحترافي (RTL)
# =============================================================================
st.set_page_config(
    page_title="حاسبة سنوات الزواج",
    layout="wide",
    page_icon="💍"
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
        background: linear-gradient(135deg, #1e3a8a 0%, #0f172a 100%);
        color: #ffffff;
        font-weight: 800;
        font-size: 17px;
        padding: 12px;
        border-radius: 10px;
        border: 1px solid #3b82f6;
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

TWELVE_POINTS = [
    "Sun", "Moon", "Mercury", "Venus", "Mars",
    "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto",
    "Rahu", "Ketu"
]

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

def check_midpoint_axis_activation(p_lon, midpoint_lon, orb=2.0):
    """
    فحص تفعيل محور الميد بوينت (Hard Aspects / Axis: 0, 90, 180, 270 degrees)
    نفس البرج (اقتران)، البرج المقابل (مقابلة)، أو البرج التربيعي (تربيع 90 درجة يميناً أو يساراً).
    """
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

# =============================================================================
# 4. محرك اشتقاق البيوت وتفسيرات مواصفات الشريك
# =============================================================================
def get_sign_idx(lon):
    return int(lon / 30) % 12

def get_physical_appearance(activating_planet_name, p_lon, partner_title="العريس", partner_type="groom"):
    sign_idx = get_sign_idx(p_lon)
    sign_name = ZODIAC_NAMES_AR[sign_idx]
    deg_in_sign = p_lon % 30

    descriptions = {
        "Venus": {
            "title": f"تأثير كوكب الزهرة (سيدة الجمال والجاذبية)",
            "face": "وجه مشرق آسر شديد الجاذبية، ملامح ناعمة ومتناسقة بشكل ملفت. عينان ناعستان ساحرتان تشعان دفئاً ورقة، حواجب مرسومة بجمال، بشرة نقية نضرة، وابتسامة بديعة قد تظهر معها غمازات واضحة أو شفتان ممتلئتان متناسقتان. الملامح تبعث على الراحة والألفة الفورية وتلفت الأنظار بأناقة طبيعية.",
            "height_build": "قامة معتدلة تميل للطول المتناسق، قوام رشيق ومتناسق جداً، حركات رشيقة وأسلوب ملبس رفيع وذوق راقٍ في اختيار الألوان والعطور والمظهر العام.",
            "age_bracket": "تحت 30 سنة (أو يتمتع بمظهر شبابي نضر ودائم الحيوية يوحي بأنه أصغر من عمره الزمني بكثير)",
            "age_code": "<30"
        },
        "Mercury": {
            "title": f"تأثير كوكب عطارد (رسول الذكاء والحيوية والشباب الدائم)",
            "face": "وجه بيضاوي أو دقيق ذكي الملامح، عينان براقتان سريعتان الحركة تعكسان يقظة ذهنية وسرعة بديهة. أنف دقيق ومستقيم، ملامح معبرة متغيرة بابتسامة خفيفة وحركات وجه حيوية تنم عن روح مرحة ومحبوبة.",
            "height_build": "قامة متوسطة إلى ممشوقة القوام، جسد نحيف أو رشيق خفيف الحركة، سريع الخطوات، نشيط ومرن في حركته.",
            "age_bracket": "تحت 30 سنة (صغير السن أو يبدو أصغر من سنه الحقيقي بكثير بفضل خفة ظله وروحه الحيوية)",
            "age_code": "<30"
        },
        "Moon": {
            "title": f"تأثير كوكب القمر (الأمومة، العاطفة، والملامح الملائكية)",
            "face": "وجه دائري ممتلئ كالبدر المضيء، ملامح ملائكية حنونة وعاطفية جداً. عينان واسعتان لامعتان كأنهما مغلفتان بطبقة مائية حالمة، بشرة فاتحة أو نقية وناعمة، تعبير الوجه دافئ يفيض بالسكينة والأمان كأنه مألوف لديك منذ الأزل.",
            "height_build": "قامة متوسطة، جسد ذو انحناءات ممتلئة بلطافة ودفء، حضور هادئ مريح، يميل للبساطة المريحة في المظهر.",
            "age_bracket": "تحت 30 إلى 35 سنة (بين فتوة الشباب ونضج العاطفة الأسرية)",
            "age_code": "30-35"
        },
        "Sun": {
            "title": f"تأثير كوكب الشمس (الهيبة والملوكية والحضور القيادي)",
            "face": "وجه مهيب مشرق كالضياء، جبهة عريضة واضحة، ملامح بارزة وقوية تعكس فخراً وثقة عالية بالنفس. عينان ذهبيتان أو حادتان تنظران بثبات، شعر كثيف أو تسريحة لافتة تشبه لبدة الأسد، نظرات قيادية واثقة.",
            "height_build": "قامة متوسطة إلى طويلة مع استقامة تامة في الظهر والصدر، عريض المنكبين، بنية قوية ذات حضور كاريزمي طاغٍ يفرض احترامه.",
            "age_bracket": "30 - 35 سنة (مرحلة النضج القيادي وتحقيق المكانة الاجتماعية الراسخة)",
            "age_code": "30-35"
        },
        "Mars": {
            "title": f"تأثير كوكب المريخ (الطاقة الرياضية، الحزم، والجاذبية الجريئة)",
            "face": "ملامح حادة ومنحوتة، عظام وجنتين بارزة، فك قوي وحاسم. عينان ثاقبتان مليئتان بالحماس والتحدي، نظرة مباشرة غير مترددة، بشرة قد تميل للتورد أو بها أثر/شامة مميزة.",
            "height_build": "قامة ممشوقة وقوية، بنية رياضية عضلية مشدودة، كتفان عريضان، حركة سريعة وحاسمة تعكس شجاعة وجرأة بدنية.",
            "age_bracket": "تحت 30 سنة إلى 35 سنة (في ذروة القوة البدنية والحيوية والنشاط)",
            "age_code": "30-35"
        },
        "Jupiter": {
            "title": f"تأثير كوكب المشتري (السعد الأكبر، الوجاهة، والسعة)",
            "face": "وجه بشوش وضيء، ابتسامة عريضة كريمة تشع تفاؤلاً وسروراً. جبين مرتفع، عينان واسعتان صافيتان ممتلئتان بالأمل والحكمة، ملامح وجيهة توحي بالشهامة والكرم والشرف.",
            "height_build": "قامة طويلة أو بنية جسدية ضخمة/ممتلئة بمهابة ووجاهة، هيبة اجتماعية ملحوظة، مشية واثقة معتدة بالذات.",
            "age_bracket": "30 - 35 سنة (أو ناضج في أوائل الأربعينات يتمتع بالحكمة والمكانة المادية المريحة)",
            "age_code": "30-35"
        },
        "Saturn": {
            "title": f"تأثير كوكب زحل (الوقار، الرصانة، والاستقرار الكلاسيكي)",
            "face": "وجه رصين منحوت بدقة، عظام بارزة، ملامح عميقة وجادة توحي بالحكمة والتحمل. عينان غائرتان مركزتان تتأملان بعمق ومسؤولية، بشرة كلاسيكية هادئة، هيبة وقورة تلزم من يراها بالاحترام.",
            "height_build": "قامة طويلة ونحيفة أو متوسطة باستقامة صارمة، جسد صلب ومقتصد الحركة، مظهر كلاسيكي رسمي أنيق ومتحفظ.",
            "age_bracket": "فوق 40 سنة (أو شخص ناضج ومسؤول يفوق عمره الزمني وعياً وخبرة، وغالباً أكبر من صاحب الخريطة)",
            "age_code": ">40"
        },
        "Uranus": {
            "title": f"تأثير كوكب أورانوس (التميز الفريد، العصرية، والجاذبية الاستثنائية)",
            "face": "ملامح غير مألوفة جذابة بطريقة عصرية وفريدة، نظرات غير تقليدية ومتحررة. عينان سريعتان تلمعان بالعبقرية والتمرد على المألوف، ملامح مبتكرة تترك انطباعاً لا ينسى.",
            "height_build": "قامة تميل للطول والنحافة، حركة ديناميكية مفاجئة، مظهر عصري جريء وغير تقليدي في الملابس والتسريحة.",
            "age_bracket": "متنوع (غالباً تحت 35 سنة يحمل فكراً مستقبلياً متجدداً)",
            "age_code": "30-35"
        },
        "Neptune": {
            "title": f"تأثير كوكب نبتون (السحر الروحي، الخيال، والملامح الأثيرية الحالمة)",
            "face": "ملامح حالمة كأنها لوحة فنية ساحرة، عينان واسعتان غامضتان كزرقة المحيط تأسران القلب برومانسيتهما. بشرة ناعمة ورقيقة، نظرة تائهة في عالم من المشاعر، ابتسامة رقيقة غامضة تنضح بالدفء الروحي.",
            "height_build": "قامة انسيابية رشيقة وناعمة، حركة هادئة وشاعرية توحي بالرقة وخفة الحضور.",
            "age_bracket": "تحت 30 أو 30-35 سنة (ملامح خالية من علامات التقدم بالسن)",
            "age_code": "<30"
        },
        "Pluto": {
            "title": f"تأثير كوكب بلوتو (الجاذبية المغناطيسية الخارقة والعمق السري)",
            "face": "وجه غامض ذو حضور مغناطيسي لا يقاوم، عينان ثاقبتان كأنهما تقرآن أعمق أسرارك بنظرة واحدة. ملامح حادة ومكثفة، ابتسامة نادرة لكنها تزلزل الكيان، هيبة غامضة تجمع بين السحر والرهبة.",
            "height_build": "بنية جسدية صلبة مكثفة، قامة متوسطة توحي بالقوة الداخلية الهائلة والسيطرة التامة على الذات.",
            "age_bracket": "30 - 35 سنة إلى فوق 40 سنة (نضج عميق وخبرات حياتية محورية)",
            "age_code": "30-35"
        },
        "Rahu": {
            "title": f"تأثير راهو - العقدة الشمالية (الكاريزما الاستثنائية والجاذبية القدرية الصاعقة)",
            "face": "ملامح ملفتة للانتباه وغير مألوفة، وجه يحمل سحراً غريباً يجذبك بقوة دون قدرة على التفسير. نظرات حارقة وطموحة جداً، مظهر ينتمي لبيئة أو ثقافة أو أسلوب مختلف يثير الفضول والانجذاب القهري.",
            "height_build": "قامة لافتة ذات حضور بصري قوي، جسد مميز وطاقة حضور تجعل الجميع يلتفت نحوه في أي مكان يتواجد فيه.",
            "age_bracket": "تحت 30 أو 30-35 سنة (طموح جارف وتطلع نحو مستقبل واعد)",
            "age_code": "<30"
        },
        "Ketu": {
            "title": f"تأثير كيتو - العقدة الجنوبية (العمق الكارمي، الروحانية، والسكينة العتيقة)",
            "face": "ملامح روحانية هادئة تشعرك بأنك تعرف هذا الشخص منذ حيوات سابقة. عينان عميقتان ممتلئتان بالحكمة والزهد، ملامح غير متكلفة بسيطة ومريحة جداً تمنح النفس طمأنينة فورية.",
            "height_build": "قامة معتدلة إلى نحيفة، جسد خفيف ومظهر متواضع وأنيق بأسلوب فطري وطبيعي بعيد عن التكلف.",
            "age_bracket": "يحمل روحاً ناضجة وحكيمة (قد يكون فوق 35 سنة أو شاباً بوقار الشيوخ وحكمتهم)",
            "age_code": ">40"
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
        "age_bracket": p_info["age_bracket"],
        "age_code": p_info["age_code"]
    }

def derive_partner_career(natal_cusps, natal_planets, partner_title="العريس"):
    c4 = natal_cusps[3]
    sign_idx = get_sign_idx(c4)
    sign_name = ZODIAC_NAMES_AR[sign_idx]
    ruler = SIGN_RULERS[sign_idx]
    modern_ruler = MODERN_SIGN_RULERS[sign_idx]
    planets_in_4th = [p_name for p_name, p_data in natal_planets.items() if p_data.get('house') == 4]

    career_profiles = {
        "Mercury": "قطاع التكنولوجيا، تكنولوجيا المعلومات والبرمجة، التجارة وسلاسل الإمداد، المحاسبة والتدقيق المالي، الإعلام والصحافة، أو التعليم والاستشارات والتحليل الاستراتيجي.",
        "Venus": "المجالات الإبداعية والفنون، التصميم المعماري والديكور، قطاع الأزياء والموضة والجمال، التجارة الفاخرة، الضيافة الراقية، أو الشؤون القانونية والدبلوماسية والعلاقات العامة.",
        "Mars": "الهندسة بمختلف فروعها (المدنية، الميكانيكية، الصناعية)، المقاولات والتطوير العقاري، الجراحة والمجال الطبي الطارئ، القوات المسلحة والأمن، أو ريادة الأعمال والمشاريع الحرة المستقلة.",
        "Jupiter": "القانون والقضاء، السلك الدبلوماسي، الأكاديميا والتعليم العالي، الاستشارات الإدارية والدولية، المصارف والاستثمار البنكي، أو التجارة الدولية والسياحة العالمية.",
        "Saturn": "الإدارة التنفيذية العليا، إدارة وتملك العقارات والأراضي، الهياكل الحكومية والمؤسسات الكبرى، الهندسة الإنشائية، الإشراف المالي والرقابي، أو قطاع التعدين والصناعات الثقيلة.",
        "Sun": "مناصب قيادية ورئاسية، إدارة عامة، مدراء تنفيذيون وأصحاب شركات خاصة، مناصب حكومية رفيعة، أو قطاع الإنتاج الإبداعي والريادة ذات التأثير المجتمعي البارز.",
        "Moon": "القطاع الطبي والرعاية الصحية والصيدلانية، إدارة المنشآت الفندقية والمطاعم، التجارة في المواد الاستهلاكية والغذائية، قطاع العقارات السكنية، أو شؤون الموارد البشرية والخدمة المجتمعية.",
        "Uranus": "هندسة البرمجيات والذكاء الاصطناعي، علوم الفضاء والطيران، الطاقة المتجددة، الابتكار التقني، أو العمل الحر الرقمي والمشاريع الاستشرافية الرائدة.",
        "Neptune": "الطب النفسي والعلاجي، صناعة الأدوية والكيمياء الحيوية، الفنون البصرية والسينما والموسيقى، الملاحة البحرية، أو المنظمات الإنسانية والإغاثية الدولية.",
        "Pluto": "الاستثمارات وصناديق التحوط، إدارة الأزمات والشركات الاستراتيجية، التحقيقات والبحث الجنائي، قطاع الطاقة والنفط، أو الجراحة الدقيقة وعلم المناعة."
    }

    ruler_ar = PLANET_NAMES_AR.get(ruler, ruler)
    prof_text = career_profiles.get(ruler, career_profiles["Jupiter"])
    if modern_ruler != ruler:
        prof_text += f" كما يدعمه تأثير {PLANET_NAMES_AR.get(modern_ruler, modern_ruler)}: {career_profiles.get(modern_ruler, '')}"

    planets_text = f"بتأثير الكواكب المتواجدة فيه: ({', '.join([PLANET_NAMES_AR.get(p, p) for p in planets_in_4th])})" if planets_in_4th else "لا توجد كواكب معرقلة داخل وتد البيت."

    return {
        "derived_house": "البيت العاشر من السابع = البيت الرابع الميلادي",
        "sign": sign_name,
        "ruler": ruler_ar,
        "planets_in_house": planets_text,
        "career_description": prof_text
    }

def derive_partner_intimacy(natal_cusps, natal_planets, partner_title="العريس"):
    c2 = natal_cusps[1]
    sign_idx = get_sign_idx(c2)
    sign_name = ZODIAC_NAMES_AR[sign_idx]
    element = ZODIAC_SIGNS[sign_idx]["element"]
    ruler = SIGN_RULERS[sign_idx]

    intimacy_styles = {
        "مائي": "علاقة حميمية شديدة العمق والشغف، اندماج روحي وعاطفي كامل يجمع بين الحنان الفياض والجاذبية المغناطيسية القوية. الشريك يبحث عن التلاحم الوجداني والاحتواء التام، وتكون العلاقة مصدر شفاء وتجدد دائم للطرفين.",
        "ناري": "علاقة نارية ملتهبة بالحماس والإثارة، تجدد دائم ومبادرة عفوية وجرأة عاطفية. تسودها مشاعر الشغف القوي والتعبير الجسدي الصريح والحيوي الممتلئ بالطاقة والمرح وتجنب الروتين.",
        "ترابي": "علاقة حسية راقية وراسخة، مفعمة بالثبات والوفاء والأمان الجسدي العميق. الشريك يتسم بالصبر، الدفء اللمسي، والاهتمام البالغ بإسعاد الطرف الآخر برعاية وتفانٍ طويل الأمد.",
        "هوائي": "علاقة قائمة على الانسجام الذهني والتواصل اللفظي الرقيق والتجديد الفكري. حميمية مفعمة بالمرح، الأحاديث العميقة قبل وبعد اللقاء، كسر التكلف، واستكشاف أبعاد فكرية وعاطفية مشتركة."
    }

    return {
        "derived_house": "البيت الثامن من السابع = البيت الثاني الميلادي",
        "sign": sign_name,
        "element": element,
        "ruler": PLANET_NAMES_AR.get(ruler, ruler),
        "intimacy_description": intimacy_styles.get(element, intimacy_styles["ترابي"])
    }

def derive_partner_wealth(natal_cusps, natal_planets, partner_title="العريس"):
    c8 = natal_cusps[7]
    sign_idx = get_sign_idx(c8)
    sign_name = ZODIAC_NAMES_AR[sign_idx]
    ruler = SIGN_RULERS[sign_idx]
    planets_in_8th = [p_name for p_name, p_data in natal_planets.items() if p_data.get('house') == 8]

    if "Jupiter" in planets_in_8th or "Venus" in planets_in_8th or ruler in ["Jupiter", "Venus"]:
        wealth_text = "ملاءة مالية ممتازة وثراء لافت؛ الشريك يتمتع بوضع مالي متين، تدفقات نقدية متعددة، استثمارات رابحة، وأصول عقارية أو تجارية ذات قيمة متنامية، مع حظوظ عالية في الميراث والشراكات المالية الناجحة."
    elif "Saturn" in planets_in_8th or ruler == "Saturn":
        wealth_text = "ثروة متينة مبنية على أسس راسخة ومجهود تراكمي منظم؛ يمتلك ممتلكات عقارية ثابتة وأصولاً مؤمنة بعناية، حكيم جداً في إدارة مصاريفه، ويحرص على تأمين مستقبل الأسرة المالي بأمان مطلق."
    elif "Mars" in planets_in_8th or ruler == "Mars" or ruler == "Sun":
        wealth_text = "شخصية عصامية تبني ثروتها باستقلالية تامة وقوة عمل شخصية؛ يمتلك مشاريع خاصة ومصادر دخل حيوية، سريع المبادرة الاستثمارية، ووضعه المادي يشهد قفزات صعود ممتازة بعد الارتباط."
    else:
        wealth_text = "وضع مالي مستقر وجيد جداً مع تنوع في الأصول؛ قدرة ذكية على التجارة وإدارة الأموال، ممتلكات مادية مريحة تضمن حياة كريمة ومترفة للأسرة."

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
    has_saturn_prominent = sr_planets['Saturn']['house'] in [1, 4, 7]

    if has_jupiter_prominent or has_sun_prominent or sign11_idx in [4, 8]:
        style = "حفل زفاف فخم وملكي (Grand Luxury Wedding)"
        desc = "حفل كبير وأسطوري في قاعة فاخرة أو فندق راقٍ، حضور واسع ومبهج يضم نخبة اجتماعية ووجهاء، تنظيم استثنائي، تفاصيل باذخة، وأجواء احتفالية ملكية تحظى بإعجاب وحديث الجميع."
    elif sr_planets['Venus']['house'] in [1, 5, 7, 10] or sign11_idx in [1, 6]:
        style = "حفل زفاف أنيق وكلاسيكي (Elegant & Aesthetic Wedding)"
        desc = "حفل يتميز بأعلى درجات الذوق والرقي الكلاسيكي، ديكورات زهرية ساحرة وإضاءة رومانسية هادئة، موسيقى راقية مختارة بعناية، وأجواء تمزج بين الفخامة والنعومة الأنيقة."
    elif has_saturn_prominent or sign11_idx in [5, 9]:
        style = "حفل زفاف رصين ومتواضع (Classy, Elegant & Intimate)"
        desc = "حفل يتسم بالوقار والجدية وحسن التنظيم، مقتصد ومدروس التكاليف بعيداً عن البذخ المبالغ فيه، يركز على قدسية عقد القران وجوهر الارتباط الدائم بحضور دائرة منتقاة بعناية."
    elif sr_planets['Moon']['house'] in [4, 7] or sign11_idx in [3, 11]:
        style = "حفل زفاف عائلي دافئ ومبهج (Warm Family Gathering)"
        desc = "حفل عائلي دافئ مفعم بالحب والألفة، يجمع الأهل والأقربين في أجواء ملؤها السعادة والتآلف، مع احترام العادات والتقاليد الأصيلة التي تبارك بدء الحياة الزوجية."
    else:
        style = "حفل زفاف عصري ومميز (Modern & Unique Celebration)"
        desc = "حفل يتسم بلمسات غير تقليدية وأفكار مبتكرة، يكسر القوالب المعتادة بأجواء مرحة وحيوية تناسب تطلعات العصر وروح الشريكين المنطلقة."

    return {"style": style, "description": desc}

def derive_partner_social_details(natal_cusps, natal_planets, partner_title="العريس"):
    c7 = natal_cusps[6]
    ruler7 = SIGN_RULERS[get_sign_idx(c7)]
    ruler7_house = natal_planets.get(ruler7, {}).get('house', 7)
    is_ruler7_retrograde = natal_planets.get(ruler7, {}).get('is_retrograde', False)

    # 1. أقارب أم غريب
    if ruler7_house in [3, 4] or ruler7 in ["Mercury", "Moon"]:
        relative_status = "من طرف الأقارب أو محيط العائلة الموسعة"
        relative_desc = "الشريك له صلة قرابة ممتدة أو ينحدر من نفس الشبكة العائلية والاجتماعية المقربة، أو معارف الطفولة وحي النشأة المشترك."
    else:
        relative_status = "شخص غريب تماماً (لا توجد صلة قرابة دموية)"
        relative_desc = "الشريك غريب عن العائلة تماماً، يلتقي بك عبر مسارات الحياة العامة، سواء في مجالات العمل، التعليم العالي، الأنشطة الاجتماعية، أو اللقاءات القدرية السعيدة."

    # 2. الإقامة في نفس الدولة
    if ruler7_house in [9, 12] or get_sign_idx(c7) in [8, 10]:
        residence_status = "مقيم في بلد/مدينة أخرى أو كثير التنقل"
        residence_desc = "الشريك يقيم حالياً في مدينة أخرى أو في دولة خارجية بداعي العمل أو الدراسة أو الإقامة الدائمة، ويتطلب الارتباط ترتيبات تتعلق بالتنقل أو السفر المشترك."
    else:
        residence_status = "مقيم في نفس الدولة والبيئة المحلية"
        residence_desc = "الشريك يقيم في نفس البلد وربما في نفس المدينة التي يتواجد بها صاحب الخريطة، مما يسهل اللقاء المباشر وترتيبات الخطوبة والزواج بسلاسة."

    # 3. مغترب / جنسية أخرى / ديانة أو ثقافة مغايرة
    has_rahu_7_or_9 = natal_planets.get('Rahu', {}).get('house') in [7, 9]
    has_jupiter_9 = natal_planets.get('Jupiter', {}).get('house') in [7, 9]
    if ruler7_house == 9 or has_rahu_7_or_9 or has_jupiter_9 or get_sign_idx(c7) == 8:
        expatriate_status = "مغترب / يحمل جنسية أخرى أو ينحدر من ثقافة/لهجة أو بيئة فكرية مغايرة"
        expatriate_desc = "توجد دلالات فلكية قوية تشير إلى أن الشريك قد يكون حاملاً لجنسية أجنبية أو مزدوجة، أو مغترباً يعيش خارج وطنه الأم، أو ينتمي إلى خلفية ثقافية/دينية أو فلسفية مختلفة تتسم بالانفتاح والتعددية."
    else:
        expatriate_status = "ينتمي لنفس الوطن والثقافة والديانة الأصلية"
        expatriate_desc = "الشريك من نفس النسيج الوطني، يحمل نفس الجنسية ويتشارك معك نفس الجذور الثقافية والقيم الدينية والاجتماعية المتوارثة."

    # 4. حبيب سابق / صديق سابق أم شخص جديد
    has_ketu_7_5 = natal_planets.get('Ketu', {}).get('house') in [7, 5]
    if is_ruler7_retrograde or has_ketu_7_5 or ruler7_house == 11:
        history_status = "حبيب سابق أو صديق قديم تعود قصته للاكتمال"
        history_desc = "العلاقة تحمل طابعاً كارمياً مميزاً؛ قد تكون عودة لشخص من الماضي كنت ترتبط به عاطفياً، أو صديقاً مقرّباً تتحول علاقتك معه فجأة إلى حب رسمي معلن وزواج بعد نضج الظروف."
    else:
        history_status = "شخص جديد تماماً لم يسبق لك معرفته"
        history_desc = "شخص يدخل حياتك كصفحة جديدة نقية لم تلتقِ به من قبل، يظهر فجأة في توقيت كوني مقدّر ليبدأ معك مرحلة التعارف الجدي المباشر نحو الزواج."

    # 5. قصة حب أم زواج تقليدي
    if ruler7_house in [5, 11] or get_sign_idx(c7) in [4, 6]:
        marriage_type = "زواج ناتج عن قصة حب جارفة وتوافق عاطفي صريح"
        marriage_desc = "الارتباط يتوج قصة حب حقيقية، تعارف شخصي متبادل، واختيار حر نابع من القلب، حيث يلعب التجاذب العاطفي والشغف الدور الأول في اتخاذ قرار الزواج."
    else:
        marriage_type = "زواج تقليدي عائلي راقٍ ومدروس"
        marriage_desc = "الزواج يتم عبر الأطر التقليدية الرفيعة، بوساطة عائلية كريمة أو تقديم رسمي من قبل الأهل والمعارف، يتلوه تآلف قلبي عميق وقبول متبادل مبني على التكافؤ والاحترام."

    return {
        "relative": {"status": relative_status, "desc": relative_desc},
        "residence": {"status": residence_status, "desc": residence_desc},
        "expatriate": {"status": expatriate_status, "desc": expatriate_desc},
        "history": {"status": history_status, "desc": history_desc},
        "marriage_type": {"status": marriage_type, "desc": marriage_desc}
    }

# =============================================================================
# 5. محرك الـ 50 دلالة فلكية الشاملة مع تحديث محور الميد بوينت وتثبيت المعايير
# =============================================================================
def evaluate_all_50_indicators(natal_data, sr_data, general_orb=1.0, midpoint_orb=2.0):
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

    # 1 - 10: تراكب الأوتاد والمنازل الميلادية
    sr_asc_in_n = get_house_of_point(sr_asc, n_cusps)
    sr_desc_in_n = get_house_of_point(sr_desc, n_cusps)
    sr_mc_in_n = get_house_of_point(sr_mc, n_cusps)

    indicators.append({"id": 1, "code": "D01", "category": "تراكب الأوتاد والمنازل الميلادية", "name_ar": "طالع السنوية يقع في البيت السابع الميلادي", "description": "من أقوى أدلة الزواج الكلاسيكية؛ حلول طالع العام في بيت الشراكة والزواج الميلادي يعلن عام الشريك بامتياز.", "is_active": sr_asc_in_n == 7, "detail": f"طالع السنوية ({sr_asc%30:.2f}° {ZODIAC_NAMES_AR[int(sr_asc/30)%12]}) يقع في البيت {sr_asc_in_n} الميلادي"})
    indicators.append({"id": 2, "code": "D02", "category": "تراكب الأوتاد والمنازل الميلادية", "name_ar": "سابع السنوية (بيت الشريك) يقع في البيت الأول الميلادي", "description": "انعكاس وتدي استثنائي، الشريك يدخل مجال الذات ويبادر بالاقتراب المباشر للارتباط بصاحب الخريطة.", "is_active": sr_desc_in_n == 1, "detail": f"سابع السنوية ({sr_desc%30:.2f}° {ZODIAC_NAMES_AR[int(sr_desc/30)%12]}) يقع في البيت {sr_desc_in_n} الميلادي"})
    indicators.append({"id": 3, "code": "D03", "category": "تراكب الأوتاد والمنازل الميلادية", "name_ar": "طالع السنوية يقع في البيت الخامس الميلادي", "description": "عام مكرس للمشاعر الرومانسية وبداية العلاقات الغرامية الجادة والتعبير عن الرغبة في الشراكة.", "is_active": sr_asc_in_n == 5, "detail": f"طالع السنوية في البيت {sr_asc_in_n} الميلادي"})
    indicators.append({"id": 4, "code": "D04", "category": "تراكب الأوتاد والمنازل الميلادية", "name_ar": "سابع السنوية يقع في البيت الخامس الميلادي", "description": "تحول علاقة حب وغرام قائمة إلى التزام رسمي وشراكة زواج معلنة.", "is_active": sr_desc_in_n == 5, "detail": f"سابع السنوية في البيت {sr_desc_in_n} الميلادي"})
    indicators.append({"id": 5, "code": "D05", "category": "تراكب الأوتاد والمنازل الميلادية", "name_ar": "طالع السنوية يقع في البيت العاشر الميلادي", "description": "تغير جذري ورسمي في الحالة الاجتماعية والمكانة العامة أمام المجتمع بالزواج وعقد القران.", "is_active": sr_asc_in_n == 10, "detail": f"طالع السنوية في البيت {sr_asc_in_n} الميلادي"})
    indicators.append({"id": 6, "code": "D06", "category": "تراكب الأوتاد والمنازل الميلادية", "name_ar": "عاشر السنوية (وتد وسط السماء) يقع في سابع الأصل", "description": "إشهار الزواج وجعله الحدث الأبرز في السمعة الاجتماعية لصاحب الخريطة خلال العام.", "is_active": sr_mc_in_n == 7, "detail": f"عاشر السنوية يقع في البيت {sr_mc_in_n} الميلادي"})
    indicators.append({"id": 7, "code": "D07", "category": "تراكب الأوتاد والمنازل الميلادية", "name_ar": "طالع السنوية يقع في البيت الرابع الميلادي", "description": "التركيز على تأسيس وتد الأسرة وعش الزوجية والانتقال إلى سكن جديد مع الشريك.", "is_active": sr_asc_in_n == 4, "detail": f"طالع السنوية في البيت {sr_asc_in_n} الميلادي"})

    m8, d8_diff = is_aspect(sr_asc, n_planets['Venus']['lon'], 0, orb=general_orb)
    indicators.append({"id": 8, "code": "D08", "category": "تراكب الأوتاد والمنازل الميلادية", "name_ar": "اقتران طالع السنوية بالزهرة الميلادية", "description": "توهج الجاذبية الشخصية والاستعداد القلبي الكامل لاستقبال شريك الحياة بأورب 3 درجات.", "is_active": m8, "detail": f"الفرق بين طالع السنوية والزهرة الميلادية: {d8_diff:.2f}°" if m8 else "غير مقترن"})

    m9, d9_diff = is_aspect(sr_desc, n_planets['Venus']['lon'], 0, orb=general_orb)
    indicators.append({"id": 9, "code": "D09", "category": "تراكب الأوتاد والمنازل الميلادية", "name_ar": "اقتران سابع السنوية بالزهرة الميلادية", "description": "حلول كوكب الحب والزواج على خط بداية بيت الزواج السنوي مباشرة.", "is_active": m9, "detail": f"الفرق بين سابع السنوية والزهرة الميلادية: {d9_diff:.2f}°" if m9 else "غير مقترن"})

    m10, d10_diff = is_aspect(sr_desc, n_planets['Jupiter']['lon'], 0, orb=general_orb)
    indicators.append({"id": 10, "code": "D10", "category": "تراكب الأوتاد والمنازل الميلادية", "name_ar": "اقتران سابع السنوية بالمشتري الميلادي", "description": "السعد الأكبر يبارك بيت الشراكة السنوي بالارتباط السعيد وتسهيل مراسم الزواج.", "is_active": m10, "detail": f"الفرق بين سابع السنوية والمشتري الميلادي: {d10_diff:.2f}°" if m10 else "غير مقترن"})

    # 11 - 20: تموضع الكواكب في بيوت السنوية
    indicators.append({"id": 11, "code": "D11", "category": "تموضع الكواكب في بيوت السنوية", "name_ar": "الشمس السنوية تقع في البيت السابع السنوي", "description": "تسليط نور الوعي والاهتمام الكامل طوال العام على الشريك وشؤون الزواج.", "is_active": sr_planets['Sun']['house'] == 7, "detail": f"الشمس في البيت {sr_planets['Sun']['house']} السنوي"})
    indicators.append({"id": 12, "code": "D12", "category": "تموضع الكواكب في بيوت السنوية", "name_ar": "القمر السنوي يقع في البيت السابع السنوي", "description": "رغبة نفسية وعاطفية ملحة في التشارك والأمان العاطفي مع شخص مميز.", "is_active": sr_planets['Moon']['house'] == 7, "detail": f"القمر في البيت {sr_planets['Moon']['house']} السنوي"})
    indicators.append({"id": 13, "code": "D13", "category": "تموضع الكواكب في بيوت السنوية", "name_ar": "الزهرة السنوية تقع في البيت السابع السنوي", "description": "الزهرة في بيتها الطبيعي بالسنوية؛ دلالة قاطعة على الانسجام والخطوبة وعقد القران.", "is_active": sr_planets['Venus']['house'] == 7, "detail": f"الزهرة في البيت {sr_planets['Venus']['house']} السنوي"})
    indicators.append({"id": 14, "code": "D14", "category": "تموضع الكواكب في بيوت السنوية", "name_ar": "المشتري السنوي يقع في البيت السابع السنوي", "description": "كوكب السعادة والبركة في بيت الزواج؛ زواج محظوظ من شخص ذي وجاهة وسعة.", "is_active": sr_planets['Jupiter']['house'] == 7, "detail": f"المشتري في البيت {sr_planets['Jupiter']['house']} السنوي"})
    indicators.append({"id": 15, "code": "D15", "category": "تموضع الكواكب في بيوت السنوية", "name_ar": "الزهرة السنوية تقع في البيت الخامس السنوي", "description": "نشوة الحب والرومانسية ودخول علاقة عاطفية تسعد القلب وتؤسس للارتباط.", "is_active": sr_planets['Venus']['house'] == 5, "detail": f"الزهرة في البيت {sr_planets['Venus']['house']} السنوي"})
    indicators.append({"id": 16, "code": "D16", "category": "تموضع الكواكب في بيوت السنوية", "name_ar": "الشمس السنوية تقع في البيت الخامس السنوي", "description": "حيوية المشاعر العاطفية وإشراق الحب الجاد المعلن خلال السنة.", "is_active": sr_planets['Sun']['house'] == 5, "detail": f"الشمس في البيت {sr_planets['Sun']['house']} السنوي"})
    indicators.append({"id": 17, "code": "D17", "category": "تموضع الكواكب في بيوت السنوية", "name_ar": "القمر السنوي يقع في البيت الخامس السنوي", "description": "تعلق عاطفي وغرامي عميق وتطلع لتكوين رابطة قلبية دائمة.", "is_active": sr_planets['Moon']['house'] == 5, "detail": f"القمر في البيت {sr_planets['Moon']['house']} السنوي"})
    indicators.append({"id": 18, "code": "D18", "category": "تموضع الكواكب في بيوت السنوية", "name_ar": "الزهرة السنوية تقع في البيت الأول السنوي", "description": "إشراقة الشخصية وجاذبيتها الفائقة للخطاب وإعلان الرغبة في التآلف والزواج.", "is_active": sr_planets['Venus']['house'] == 1, "detail": f"الزهرة في البيت {sr_planets['Venus']['house']} السنوي"})
    indicators.append({"id": 19, "code": "D19", "category": "تموضع الكواكب في بيوت السنوية", "name_ar": "الشمس السنوية تقع في البيت الأول السنوي", "description": "سنة بداية دورة حياة جديدة، ثقة عالية ومبادرة شخصية لحسم مصير الارتباط.", "is_active": sr_planets['Sun']['house'] == 1, "detail": f"الشمس في البيت {sr_planets['Sun']['house']} السنوي"})
    indicators.append({"id": 20, "code": "D20", "category": "تموضع الكواكب في بيوت السنوية", "name_ar": "القمر السنوي يقع في البيت الأول أو الرابع السنوي", "description": "التركيز على بناء السكن الأسري، الاستقرار العاطفي، والارتباط الشرعي.", "is_active": sr_planets['Moon']['house'] in [1, 4], "detail": f"القمر في البيت {sr_planets['Moon']['house']} السنوي"})

    # 21 - 30: اتصالات كواكب السنوية فيما بينها
    m21, asp21, diff21 = is_soft_or_conjunction(sr_planets['Venus']['lon'], sr_planets['Mars']['lon'], orb=general_orb)
    indicators.append({"id": 21, "code": "D21", "category": "اتصالات كواكب السنوية الفعالة", "name_ar": "اتصال سعيد أو اقتران بين الزهرة والمريخ في السنوية", "description": "التوازن التام والجاذبية الكبرى بين طاقة الأنوثة والذكورة وتتويجها بالاقتران.", "is_active": m21, "detail": f"{asp21} بفارق {diff21:.2f}°" if m21 else "لا يوجد اتصال متناغم بأورب 3°"})

    m22, asp22, diff22 = is_soft_or_conjunction(sr_planets['Venus']['lon'], sr_planets['Jupiter']['lon'], orb=general_orb)
    indicators.append({"id": 22, "code": "D22", "category": "اتصالات كواكب السنوية الفعالة", "name_ar": "اتصال سعيد أو اقتران بين الزهرة والمشتري (سعد السعدين)", "description": "أعظم اتصال للسعادة العاطفية وتيسير الزواج والاحتفالات المبهجة.", "is_active": m22, "detail": f"{asp22} بفارق {diff22:.2f}°" if m22 else "لا يوجد اتصال متناغم بأورب 3°"})

    m23, asp23, diff23 = is_soft_or_conjunction(sr_planets['Sun']['lon'], sr_planets['Moon']['lon'], orb=general_orb)
    indicators.append({"id": 23, "code": "D23", "category": "اتصالات كواكب السنوية الفعالة", "name_ar": "اتصال سعيد أو اقتران بين الشمس والقمر السنويين", "description": "توافق الإرادة والوجدان وتناغم الشريكين على أهداف الزواج المشترك.", "is_active": m23, "detail": f"{asp23} بفارق {diff23:.2f}°" if m23 else "لا يوجد اتصال بأورب 3°"})

    m24, asp24, diff24 = is_soft_or_conjunction(sr_planets['Venus']['lon'], sr_planets['Saturn']['lon'], orb=general_orb)
    indicators.append({"id": 24, "code": "D24", "category": "اتصالات كواكب السنوية الفعالة", "name_ar": "اتصال تثبيت رسمي ودائم بين الزهرة وزحل في السنوية", "description": "زحل يمنح العلاقة العاطفية الثبات والجدية والعقد القانوني المكتوب غير القابل للنقض.", "is_active": m24, "detail": f"{asp24} بفارق {diff24:.2f}°" if m24 else "لا يوجد اتصال بأورب 3°"})

    m25, asp25, diff25 = is_soft_or_conjunction(sr_planets['Venus']['lon'], sr_planets['Uranus']['lon'], orb=general_orb)
    indicators.append({"id": 25, "code": "D25", "category": "اتصالات كواكب السنوية الفعالة", "name_ar": "اتصال سعيد أو اقتران بين الزهرة وأورانوس في السنوية", "description": "حب سريع ومفاجئ، كسر العزوبية بشكل غير متوقع وقرار زواج سريع وجريء.", "is_active": m25, "detail": f"{asp25} بفارق {diff25:.2f}°" if m25 else "لا يوجد اتصال بأورب 3°"})

    m26, diff26 = is_aspect(sr_planets['Sun']['lon'], sr_planets['Venus']['lon'], 0, orb=general_orb)
    indicators.append({"id": 26, "code": "D26", "category": "اتصالات كواكب السنوية الفعالة", "name_ar": "اقتران الشمس والزهرة في السنوية", "description": "إشراق الحب ونيل المنى العاطفي والارتباط عن اقتناع وحب عميق.", "is_active": m26, "detail": f"اقتران بفارق {diff26:.2f}°" if m26 else "غير مقترن بأورب 3°"})

    m27, diff27 = is_aspect(sr_planets['Moon']['lon'], sr_planets['Venus']['lon'], 0, orb=general_orb)
    indicators.append({"id": 27, "code": "D27", "category": "اتصالات كواكب السنوية الفعالة", "name_ar": "اقتران القمر والزهرة في السنوية", "description": "فيض من الرقة والبهجة والاستعداد التام لإنشاء عش الزوجية والمودة.", "is_active": m27, "detail": f"اقتران بفارق {diff27:.2f}°" if m27 else "غير مقترن بأورب 3°"})

    m28, asp28, diff28 = is_soft_or_conjunction(sr_planets['Mars']['lon'], sr_planets['Jupiter']['lon'], orb=general_orb)
    indicators.append({"id": 28, "code": "D28", "category": "اتصالات كواكب السنوية الفعالة", "name_ar": "اتصال سعيد بين المريخ والمشتري في السنوية", "description": "شجاعة الحسم والمبادرة الفعالة لإتمام مراسم الخطوبة وتخطي العقبات.", "is_active": m28, "detail": f"{asp28} بفارق {diff28:.2f}°" if m28 else "لا يوجد اتصال بأورب 3°"})

    m29, diff29 = is_aspect(sr_planets['Venus']['lon'], sr_planets['Rahu']['lon'], 0, orb=general_orb)
    indicators.append({"id": 29, "code": "D29", "category": "اتصالات كواكب السنوية الفعالة", "name_ar": "اقتران الزهرة مع راهو السنوي (العقدة الشمالية)", "description": "لقاء قدري مقدر لا مفر منه وانجذاب مغناطيسي صاعق يقود للزواج.", "is_active": m29, "detail": f"اقتران بفارق {diff29:.2f}°" if m29 else "غير مقترن بأورب 3°"})

    m30, diff30 = is_aspect(sr_planets['Jupiter']['lon'], sr_planets['Rahu']['lon'], 0, orb=general_orb)
    indicators.append({"id": 30, "code": "D30", "category": "اتصالات كواكب السنوية الفعالة", "name_ar": "اقتران المشتري مع راهو السنوي", "description": "فرصة كبرى قدرية لتوسيع الأفق العائلي وتحقيق زواج وافر الخير والبركة.", "is_active": m30, "detail": f"اقتران بفارق {diff30:.2f}°" if m30 else "غير مقترن بأورب 3°"})

    # 31 - 40: اتصالات السنوية مع حكام الأصل وكواكبها
    m31, asp31, diff31 = is_soft_or_conjunction(sr_planets['Venus']['lon'], n_7th_ruler_lon, orb=general_orb)
    indicators.append({"id": 31, "code": "D31", "category": "اتصالات السنوية مع حكام وكواكب الأصل", "name_ar": f"الزهرة السنوية تتصل بحاكم السابع الميلادي ({PLANET_NAMES_AR.get(n_7th_ruler, n_7th_ruler)})", "description": "تنشيط مباشر للشريك الأصلي بالحب والارتباط الفعلي خلال السنة.", "is_active": m31, "detail": f"{asp31} بفارق {diff31:.2f}°" if m31 else "لا يوجد اتصال بأورب 3°"})

    m32, asp32, diff32 = is_soft_or_conjunction(sr_planets['Jupiter']['lon'], n_7th_ruler_lon, orb=general_orb)
    indicators.append({"id": 32, "code": "D32", "category": "اتصالات السنوية مع حكام وكواكب الأصل", "name_ar": f"المشتري السنوي يتصل بحاكم السابع الميلادي ({PLANET_NAMES_AR.get(n_7th_ruler, n_7th_ruler)})", "description": "بركة وتوفيق كوني يطال شريك الحياة وتسهيل كافة الإجراءات.", "is_active": m32, "detail": f"{asp32} بفارق {diff32:.2f}°" if m32 else "لا يوجد اتصال بأورب 3°"})

    m33, asp33, diff33 = is_soft_or_conjunction(sr_planets['Sun']['lon'], n_7th_ruler_lon, orb=general_orb)
    indicators.append({"id": 33, "code": "D33", "category": "اتصالات السنوية مع حكام وكواكب الأصل", "name_ar": f"الشمس السنوية تتصل بحاكم السابع الميلادي ({PLANET_NAMES_AR.get(n_7th_ruler, n_7th_ruler)})", "description": "تسليط الضوء الحيوي والاعتراف الرسمي بالشريك.", "is_active": m33, "detail": f"{asp33} بفارق {diff33:.2f}°" if m33 else "لا يوجد اتصال بأورب 3°"})

    m34, asp34, diff34 = is_soft_or_conjunction(sr_planets['Moon']['lon'], n_7th_ruler_lon, orb=general_orb)
    indicators.append({"id": 34, "code": "D34", "category": "اتصالات السنوية مع حكام وكواكب الأصل", "name_ar": f"القمر السنوي يتصل بحاكم السابع الميلادي ({PLANET_NAMES_AR.get(n_7th_ruler, n_7th_ruler)})", "description": "رابطة وجدانية متينة واستجابة عاطفية متبادلة مع الشريك.", "is_active": m34, "detail": f"{asp34} بفارق {diff34:.2f}°" if m34 else "لا يوجد اتصال بأورب 3°"})

    m35, diff35 = is_aspect(sr_7th_ruler_lon, n_planets['Venus']['lon'], 0, orb=general_orb)
    indicators.append({"id": 35, "code": "D35", "category": "اتصالات السنوية مع حكام وكواكب الأصل", "name_ar": f"حاكم السابع السنوي ({PLANET_NAMES_AR.get(sr_7th_ruler, sr_7th_ruler)}) يقترن بالزهرة الميلادية", "description": "شريك هذا العام يلتقي مباشرة بكوكب الحب الأصلي لصاحب الخريطة.", "is_active": m35, "detail": f"اقتران بفارق {diff35:.2f}°" if m35 else "غير مقترن بأورب 3°"})

    indicators.append({"id": 36, "code": "D36", "category": "اتصالات السنوية مع حكام وكواكب الأصل", "name_ar": f"حاكم السابع السنوي ({PLANET_NAMES_AR.get(sr_7th_ruler, sr_7th_ruler)}) في البيت الأول السنوي", "description": "الشريك يسعى بنشاط نحو صاحب الخريطة ويطلب يده للزواج.", "is_active": sr_planets[sr_7th_ruler]['house'] == 1, "detail": f"حاكم السابع في البيت {sr_planets[sr_7th_ruler]['house']} السنوي"})
    indicators.append({"id": 37, "code": "D37", "category": "اتصالات السنوية مع حكام وكواكب الأصل", "name_ar": f"حاكم الأول السنوي ({PLANET_NAMES_AR.get(sr_1st_ruler, sr_1st_ruler)}) في البيت السابع السنوي", "description": "صاحب الخريطة يكرس كامل جهده واهتمامه لإتمام الشراكة والزواج.", "is_active": sr_planets[sr_1st_ruler]['house'] == 7, "detail": f"حاكم الأول في البيت {sr_planets[sr_1st_ruler]['house']} السنوي"})

    m38, asp38, diff38 = is_soft_or_conjunction(sr_1st_ruler_lon, sr_7th_ruler_lon, orb=general_orb)
    indicators.append({"id": 38, "code": "D38", "category": "اتصالات السنوية مع حكام وكواكب الأصل", "name_ar": "اتصال سعيد بين حاكم الطالع وحاكم السابع في السنوية", "description": "التوافق والتلاقي التام بين طرفي العلاقة لإتمام عقد القران بأورب 3 درجات.", "is_active": m38, "detail": f"{asp38} بفارق {diff38:.2f}°" if m38 else "لا يوجد اتصال بأورب 3°"})

    m39, asp39, diff39 = is_soft_or_conjunction(sr_planets['Venus']['lon'], n_planets['Sun']['lon'], orb=general_orb)
    indicators.append({"id": 39, "code": "D39", "category": "اتصالات السنوية مع حكام وكواكب الأصل", "name_ar": "الزهرة السنوية تتصل بالشمس الميلادية", "description": "تناغم عاطفي رفيع يعزز الثقة والقبول بالزواج والارتباط الجاد.", "is_active": m39, "detail": f"{asp39} بفارق {diff39:.2f}°" if m39 else "لا يوجد اتصال بأورب 3°"})

    m40, asp40, diff40 = is_soft_or_conjunction(sr_planets['Venus']['lon'], n_planets['Moon']['lon'], orb=general_orb)
    indicators.append({"id": 40, "code": "D40", "category": "اتصالات السنوية مع حكام وكواكب الأصل", "name_ar": "الزهرة السنوية تتصل بالقمر الميلادي", "description": "سكينة ودفء أسري عميق يمهد لتكوين عائلة سعيدة وناجحة.", "is_active": m40, "detail": f"{asp40} بفارق {diff40:.2f}°" if m40 else "لا يوجد اتصال بأورب 3°"})

    # 41 - 50: العقد القمرية، الأوتاد الحساسة، ونقاط المنتصف
    indicators.append({"id": 41, "code": "D41", "category": "العقد القمرية ونقاط الحسم", "name_ar": "راهو السنوي في البيت السابع السنوي", "description": "الشراكة والزواج هما الغاية التطورية والقدرية الكبرى خلال هذا العام.", "is_active": sr_planets['Rahu']['house'] == 7, "detail": f"راهو في البيت {sr_planets['Rahu']['house']} السنوي"})
    indicators.append({"id": 42, "code": "D42", "category": "العقد القمرية ونقاط الحسم", "name_ar": "راهو السنوي في البيت الخامس السنوي", "description": "تجربة عاطفية استثنائية مشحونة بالشغف والمصيرية تدفع نحو الالتزام.", "is_active": sr_planets['Rahu']['house'] == 5, "detail": f"راهو في البيت {sr_planets['Rahu']['house']} السنوي"})

    p_in_7 = [p for p, d in sr_planets.items() if d['house'] == 7]
    indicators.append({"id": 43, "code": "D43", "category": "العقد القمرية ونقاط الحسم", "name_ar": f"تجمع كواكب وهيمنة في البيت السابع السنوي ({len(p_in_7)} كواكب)", "description": "تركيز طاقي هائل في قطاع الزواج يؤكد حتمية الأحداث المرتبطة به.", "is_active": len(p_in_7) >= 2, "detail": f"الكواكب في البيت السابع: ({', '.join([PLANET_NAMES_AR.get(p, p) for p in p_in_7])})" if p_in_7 else "لا توجد كواكب"})

    p_in_5 = [p for p, d in sr_planets.items() if d['house'] == 5]
    indicators.append({"id": 44, "code": "D44", "category": "العقد القمرية ونقاط الحسم", "name_ar": f"تجمع كواكب في البيت الخامس السنوي ({len(p_in_5)} كواكب)", "description": "توهج المحور الرومانسي والأنشطة العاطفية المبهجة طوال السنة.", "is_active": len(p_in_5) >= 2, "detail": f"الكواكب في الخامس: ({', '.join([PLANET_NAMES_AR.get(p, p) for p in p_in_5])})" if p_in_5 else "لا توجد كواكب"})

    v_near_angle = False
    v_angle_txt = ""
    for a_idx, a_lon in enumerate([sr_asc, sr_ic, sr_desc, sr_mc]):
        a_diff = angular_diff(sr_planets['Venus']['lon'], a_lon)
        if a_diff <= 3.0:
            v_near_angle = True
            h_num = [1, 4, 7, 10][a_idx]
            v_angle_txt = f"الزهرة مقترنة بوتد البيت {h_num} بفارق {a_diff:.2f}°"
            break
    indicators.append({"id": 45, "code": "D45", "category": "العقد القمرية ونقاط الحسم", "name_ar": "الزهرة السنوية تقع على وتد من أوتاد السنوية (أورب 3 درجات)", "description": "بروز طاقة كوكب الزهرة بقوة وتأثير حاسم في مجريات العام.", "is_active": v_near_angle, "detail": v_angle_txt if v_near_angle else "الزهرة بعيدة عن الأوتاد بأكثر من 3°"})

    j_near_angle = False
    j_angle_txt = ""
    for a_idx, a_lon in enumerate([sr_asc, sr_ic, sr_desc, sr_mc]):
        a_diff = angular_diff(sr_planets['Jupiter']['lon'], a_lon)
        if a_diff <= 3.0:
            j_near_angle = True
            h_num = [1, 4, 7, 10][a_idx]
            j_angle_txt = f"المشتري مقترن بوتد البيت {h_num} بفارق {a_diff:.2f}°"
            break
    indicators.append({"id": 46, "code": "D46", "category": "العقد القمرية ونقاط الحسم", "name_ar": "المشتري السنوي يقع على وتد من أوتاد السنوية (أورب 3 درجات)", "description": "بروز الحظ السعيد والارتقاء الاجتماعي والزواج الوافر البركة.", "is_active": j_near_angle, "detail": j_angle_txt if j_near_angle else "المشتري بعيد عن الأوتاد بأكثر من 3°"})

    m47_rahu, diff47_r = is_aspect(sr_planets['Moon']['lon'], sr_planets['Rahu']['lon'], 0, orb=general_orb)
    m47_ketu, diff47_k = is_aspect(sr_planets['Moon']['lon'], sr_planets['Ketu']['lon'], 0, orb=general_orb)
    d47 = m47_rahu or m47_ketu
    indicators.append({"id": 47, "code": "D47", "category": "العقد القمرية ونقاط الحسم", "name_ar": "القمر السنوي يقترن بمحور العقدتين (راهو أو كيتو)", "description": "ارتباط عائلي وشراكة زوجية ذات بصمة كارمية مقدرة في مسار الروح.", "is_active": d47, "detail": f"القمر مع راهو (فرق: {diff47_r:.2f}°)" if m47_rahu else (f"القمر مع كيتو (فرق: {diff47_k:.2f}°)" if m47_ketu else "لا يوجد اقتران بالعقدتين")})

    m48, asp48, diff48 = is_soft_or_conjunction(sr_5th_ruler_lon, sr_7th_ruler_lon, orb=general_orb)
    d48 = m48 or (sr_planets[sr_5th_ruler]['house'] == 7) or (sr_planets[sr_7th_ruler]['house'] == 5)
    indicators.append({"id": 48, "code": "D48", "category": "العقد القمرية ونقاط الحسم", "name_ar": "اتصال أو تبادل بين حاكم البيت الخامس وحاكم البيت السابع في السنوية", "description": "العلامة الدقيقة على تتويج قصة الحب والانسجام العاطفي بالزواج الرسمي.", "is_active": d48, "detail": f"{asp48} بفارق {diff48:.2f}°" if m48 else ("تبادل منازل بين الحاكمين" if d48 else "لا يوجد اتصال بأورب 3°")})

    m49_v, _, diff49_v = is_soft_or_conjunction(sr_marriage_part, sr_planets['Venus']['lon'], orb=general_orb)
    m49_j, _, diff49_j = is_soft_or_conjunction(sr_marriage_part, sr_planets['Jupiter']['lon'], orb=general_orb)
    m49_a, _, diff49_a = is_soft_or_conjunction(sr_marriage_part, sr_asc, orb=general_orb)
    d49 = m49_v or m49_j or m49_a
    indicators.append({"id": 49, "code": "D49", "category": "العقد القمرية ونقاط الحسم", "name_ar": "تفعيل سهم الزواج (Part of Marriage) باتصال سعيد مع السعدين أو الطالع", "description": "سهم السعادة الزوجية يتلقى دعماً مباشراً من أدلة الخير والارتباط.", "is_active": d49, "detail": f"سهم الزواج عند {sr_marriage_part%30:.1f}° {ZODIAC_NAMES_AR[int(sr_marriage_part/30)%12]} متصل بنجاح" if d49 else "سهم الزواج غير مفعل بأورب 3°"})

    # دلالة 50: تفعيل محور نقطة منتصف الشمس/القمر (نفس البرج 0° أو المقابل 180° أو التربيع 90°) بفرق لا يتجاوز 2.0°
    activated_midpoint_list = []
    for p_name, p_data in sr_planets.items():
        p_lon = p_data['lon']
        is_active, aspect_type, dist = check_midpoint_axis_activation(p_lon, n_midpoint, orb=midpoint_orb)
        if is_active:
            deg_in_sign = p_lon % 30
            p_sign = int(p_lon / 30) % 12
            activated_midpoint_list.append({
                "planet": p_name,
                "planet_ar": PLANET_NAMES_AR.get(p_name, p_name),
                "lon": p_lon,
                "sign_name": ZODIAC_NAMES_AR[p_sign],
                "deg_in_sign": deg_in_sign,
                "diff": dist,
                "aspect_type": aspect_type
            })

    d50 = len(activated_midpoint_list) > 0
    mp_details_text = ", ".join([f"{act['planet_ar']} ({act['aspect_type']} - فرق: {act['diff']:.2f}°)" for act in activated_midpoint_list]) if d50 else "لا يوجد كوكب سنوي مفعل على محور الميد بوينت ضمن أورب 2.0°"

    indicators.append({"id": 50, "code": "D50", "category": "العقد القمرية ونقاط الحسم", "name_ar": "تفعيل محور نقطة منتصف الشمس/القمر الميلادية (Sun/Moon Midpoint Axis)", "description": "الشرط المحوري الصارم؛ وقوع كوكب سنوي في نفس برج الميد بوينت (0°) أو المقابل (180°) أو التربيع (90°) بفرق لا يتجاوز درجة  (2.0°).", "is_active": d50, "detail": f"الكواكب المفعلة على المحور: {mp_details_text}" if d50 else "لم يتم التفعيل ضمن أورب 2.0°"})

    total_active_count = sum(1 for ind in indicators if ind['is_active'])

    return {
        "total_count": len(indicators),
        "active_count": total_active_count,
        "indicators": indicators,
        "activated_midpoint_planets": activated_midpoint_list
    }

# =============================================================================
# 6. مولد التقرير الفلكي الشامل بصيغة HTML
# =============================================================================
def generate_printable_html_report(native_info, candidate_years, general_orb=1.0, midpoint_orb=2.0):
    report_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    gender_title = "العروس / الزوجة المستقبلية" if native_info['gender'] == "ذكر" else "العريس / الزوج المستقبلي"
    partner_noun = "العروس" if native_info['gender'] == "ذكر" else "العريس"

    html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تقرير كشف سنوات الزواج والارتباط الفلكي - {native_info['name']}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Amiri:ital,wght@0,400;0,700;1,400&family=Cairo:wght@400;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #1a2a44;
            --primary-light: #2c3e50;
            --gold: #c59b27;
            --gold-light: #e6ca65;
            --gold-soft: #fcf8e8;
            --text-dark: #222222;
            --text-muted: #555555;
            --bg-light: #f8fafc;
            --border-color: #e2e8f0;
            --success: #15803d;
            --danger: #b91c1c;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: 'Cairo', 'Segoe UI', Tahoma, sans-serif; background-color: var(--bg-light); color: var(--text-dark); line-height: 1.65; padding: 30px; font-size: 14px; }}
        .report-container {{ max-width: 1100px; margin: 0 auto; background: #ffffff; padding: 40px 50px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.06); border: 1px solid var(--border-color); }}
        .toolbar {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; padding-bottom: 20px; border-bottom: 2px dashed var(--border-color); }}
        .btn-print {{ background: linear-gradient(135deg, #1a2a44, #2c3e50); color: #ffffff; border: none; padding: 10px 24px; font-size: 15px; font-weight: 700; font-family: 'Cairo', sans-serif; border-radius: 8px; cursor: pointer; box-shadow: 0 4px 12px rgba(26,42,68,0.25); transition: all 0.3s ease; }}
        .btn-print:hover {{ background: #c59b27; color: #1a2a44; }}
        .header {{ text-align: center; padding: 25px 20px; background: linear-gradient(135deg, #0d1b2a 0%, #1b263b 100%); color: #ffffff; border-radius: 10px; margin-bottom: 35px; border: 2px solid var(--gold); position: relative; }}
        .header h1 {{ font-family: 'Amiri', serif; font-size: 30px; color: var(--gold-light); margin-bottom: 8px; font-weight: 700; }}
        .header p {{ font-size: 14px; color: #e0e1dd; }}
        .badge-consultant {{ display: inline-block; background: rgba(197, 155, 39, 0.2); color: var(--gold-light); border: 1px solid var(--gold); padding: 4px 14px; border-radius: 20px; font-size: 12px; font-weight: 600; margin-top: 10px; }}
        .card {{ background: #ffffff; border: 1px solid var(--border-color); border-radius: 10px; padding: 24px; margin-bottom: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.02); }}
        .card-header {{ font-size: 18px; font-weight: 800; color: var(--primary); border-bottom: 2px solid var(--gold); padding-bottom: 10px; margin-bottom: 20px; display: flex; align-items: center; justify-content: space-between; }}
        .grid-3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }}
        .data-item {{ background: var(--bg-light); padding: 12px 16px; border-radius: 8px; border-right: 4px solid var(--gold); }}
        .data-item label {{ display: block; font-size: 12px; color: var(--text-muted); font-weight: 600; margin-bottom: 3px; }}
        .data-item span {{ font-size: 15px; font-weight: 700; color: var(--primary); }}
        .year-section {{ background: #ffffff; border: 2px solid #cbd5e1; border-radius: 12px; padding: 28px; margin-bottom: 40px; page-break-inside: avoid; }}
        .year-section.verified {{ border-color: var(--gold); background: #fafbfc; }}
        .year-title-bar {{ display: flex; justify-content: space-between; align-items: center; background: var(--primary); color: #ffffff; padding: 14px 20px; border-radius: 8px; margin-bottom: 22px; }}
        .year-title-bar h2 {{ font-size: 20px; color: var(--gold-light); }}
        .score-pill {{ background: var(--gold); color: #1a2a44; font-weight: 800; padding: 6px 14px; border-radius: 20px; font-size: 13px; }}
        .traits-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-top: 20px; }}
        .trait-box {{ background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; box-shadow: 0 1px 4px rgba(0,0,0,0.03); border-top: 3px solid var(--primary); }}
        .trait-box.highlight {{ border-top-color: var(--gold); background: var(--gold-soft); }}
        .trait-box h3 {{ font-size: 15px; color: var(--primary); margin-bottom: 10px; display: flex; align-items: center; font-weight: 800; }}
        .trait-box p {{ font-size: 13.5px; color: #334155; line-height: 1.6; }}
        .trait-sub {{ margin-top: 8px; font-size: 12.5px; background: #ffffff; padding: 6px 10px; border-radius: 6px; border: 1px dashed #cbd5e1; font-weight: 600; }}
        .indicators-table {{ width: 100%; border-collapse: collapse; margin-top: 25px; font-size: 12.5px; }}
        .indicators-table th {{ background: #1e293b; color: #ffffff; text-align: right; padding: 10px 12px; font-weight: 700; }}
        .indicators-table td {{ padding: 9px 12px; border-bottom: 1px solid var(--border-color); }}
        .indicators-table tr:nth-child(even) {{ background-color: #f8fafc; }}
        .status-badge {{ display: inline-block; padding: 3px 8px; border-radius: 12px; font-weight: 700; font-size: 11px; text-align: center; }}
        .status-badge.active {{ background: #dcfce7; color: #15803d; border: 1px solid #86efac; }}
        .status-badge.inactive {{ background: #f1f5f9; color: #94a3b8; }}
        .footer {{ text-align: center; margin-top: 50px; padding-top: 25px; border-top: 2px solid var(--border-color); color: var(--text-muted); font-size: 12px; }}
        .signature-box {{ display: flex; justify-content: space-around; margin-top: 30px; padding: 20px; background: #fafbfc; border-radius: 8px; border: 1px dashed #cbd5e1; }}
        .sig-item {{ text-align: center; }}
        .sig-item strong {{ display: block; color: var(--primary); font-size: 14px; margin-bottom: 4px; }}
        @media print {{
            body {{ background: #ffffff; padding: 0; font-size: 12px; }}
            .report-container {{ box-shadow: none; border: none; padding: 0; max-width: 100%; }}
            .toolbar {{ display: none; }}
            .year-section {{ page-break-before: always; border: 1px solid #94a3b8; }}
            .header {{ background: #0d1b2a !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
            .year-title-bar {{ background: #1a2a44 !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
            .status-badge.active {{ background: #dcfce7 !important; color: #15803d !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
            .trait-box.highlight {{ background: #fcf8e8 !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
        }}
    </style>
</head>
<body>
<div class="report-container">
    <div class="toolbar">
        <div><strong>تاريخ صدور التقرير:</strong> {report_date}</div>
        <button class="btn-print" onclick="window.print()">🖨️ طباعة التقرير الفلكي (Print / PDF)</button>
    </div>
    <div class="header">
        <h1>كشف دراسة سنوات الزواج والارتباط العاطفي الدقيق</h1>
        <p>تحليل يعتمد على محور الميد بوينت الميلادي و السنوية حيث وقوع الكوكب السنوي في نفس برج الميد بوينت يشير لزواج و ليس علاقة عابرة</p>
        <span class="badge-consultant">إعداد: الفلكي الدكتور استرو رادار</span>
    </div>
    <div class="card">
        <div class="card-header">
            <span>البيانات الفلكية للمولود (صاحب الخريطة)</span>
            <span style="font-size: 13px; font-weight: normal; color: var(--text-muted);">نظام البيوت: ريجومونتانوس (Regiomontanus)</span>
        </div>
        <div class="grid-3">
            <div class="data-item"><label>الاسم الكامل</label><span>{native_info['name']}</span></div>
            <div class="data-item"><label>الجنس</label><span>{native_info['gender']} (المطلوب: مواصفات {partner_noun})</span></div>
            <div class="data-item"><label>تاريخ ووقت الميلاد</label><span>{native_info['birth_date']} | {native_info['birth_time']}</span></div>
            <div class="data-item"><label>مكان الميلاد</label><span>{native_info['birth_city']}, {native_info['birth_country']}</span></div>
            <div class="data-item"><label>مكان السنوية (الموقع الحالي)</label><span>{native_info['sr_city']}, {native_info['sr_country']}</span></div>
            <div class="data-item"><label>موقع الشمس الميلادية</label><span>{native_info['natal_sun_deg']:.2f}° {native_info['natal_sun_sign']}</span></div>
            <div class="data-item"><label>موقع القمر الميلادي</label><span>{native_info['natal_moon_deg']:.2f}° {native_info['natal_moon_sign']}</span></div>
            <div class="data-item" style="border-right-color: #b91c1c;"><label>نقطة منتصف (شمس - قمر) الميلادية</label><span style="color: #b91c1c;">{native_info['midpoint_deg']:.2f}° {native_info['midpoint_sign']}</span></div>
            <div class="data-item"><label>معايير الأورب الفلكي المثبتة</label><span>أورب الاتصالات: 1.0° | أورب محور الميد بوينت: 2.0° (أقل من 2.0°)</span></div>
        </div>
    </div>
"""

    if not candidate_years:
        html += """
    <div class="card" style="text-align: center; padding: 40px; background: #fff5f5; border-color: #fecaca;">
        <h3 style="color: #b91c1c; margin-bottom: 10px;">لم يتم رصد سنوات تطابق الشروط الفلكية الصارمة خلال النطاق المفحوص (العمر 16 - 56 سنة)</h3>
        <p style="color: #7f1d1d; font-size: 14px;">
            الشروط المثبتة تتطلب: تفعيل كوكب سنوي على محور نقطة منتصف الشمس/القمر الميلادية (نفس البرج، المقابل، أو التربيع) بفرق أقل من 1.0 درجة
            بالإضافة إلى تحقق 5 دلالات زواج فأكثر من أصل 50 دلالة سنوية معتمدة.
        </p>
    </div>
        """
    else:
        html += f"""
    <div class="card" style="background: var(--gold-soft); border-color: var(--gold);">
        <div class="card-header" style="border-bottom-color: var(--gold); color: #854d0e;">
            <span>ملخص السنوات المحققة لشروط الزواج والارتباط الجدي المؤكد فلكياً</span>
            <span>عدد السنوات المكتشفة: {len(candidate_years)} سنة</span>
        </div>
        <p style="margin-bottom: 15px; color: #713f12;">
            تم العثور على <strong>{len(candidate_years)}</strong> سنة يتحقق فيها شرط الاقتران أو التواجد على محور نقطة منتصف الشمس/القمر الميلادية (نفس البرج/مقابل/تربيع)
            مع توفر 5 دلالات زواج فأكثر من أصل 50 دلالة فلكية معتمدة:
        </p>
        <div style="display: flex; gap: 12px; flex-wrap: wrap;">
        """
        for y_data in candidate_years:
            html += f"""
            <div style="background: #ffffff; border: 1px solid var(--gold); border-radius: 8px; padding: 10px 18px; text-align: center;">
                <div style="font-size: 18px; font-weight: 800; color: var(--primary);">سنة {y_data['year']}</div>
                <div style="font-size: 12px; color: var(--text-muted); font-weight: 600;">العمر: {y_data['age']} سنة</div>
                <div style="font-size: 12px; color: var(--success); font-weight: 700; margin-top: 4px;">{y_data['active_count']} دلالة محققة</div>
            </div>
            """
        html += "</div></div>"

        for y_data in candidate_years:
            p_desc = y_data['partner_physical']
            p_career = y_data['partner_career']
            p_intimacy = y_data['partner_intimacy']
            p_wealth = y_data['partner_wealth']
            p_wedding = y_data['wedding_style']
            p_social = y_data['partner_social']
            prim = y_data['primary_activator']

            html += f"""
    <div class="year-section verified">
        <div class="year-title-bar">
            <div>
                <h2>سنة الزواج المتوقعة: {y_data['year']} ميلادي (العمر: {y_data['age']} سنة)</h2>
                <div style="font-size: 13px; color: #cbd5e1; margin-top: 3px;">
                    الكوكب المفعل للمحور: <strong>{p_desc['planet_ar']}</strong> — {prim['aspect_type']} (بفارق: {y_data['midpoint_diff_str']})
                </div>
            </div>
            <div class="score-pill">تحقق {y_data['active_count']} من أصل 50 دلالة زواج</div>
        </div>

        <div class="card-header" style="margin-top: 15px;">
            <span>الملف الفلكي لمواصفات {gender_title} (اشتقاق البيوت الفلكية)</span>
        </div>

        <div class="traits-grid">
            <div class="trait-box highlight">
                <h3>👑 الصفات الشكلية، ملامح الوجه، والعمر التقديري</h3>
                <p><strong>كوكب الهيئة المفعل:</strong> {p_desc['title']}</p>
                <p style="margin-top: 6px;"><strong>ملامح الوجه الدقيقة:</strong> {p_desc['face']}</p>
                <div class="trait-sub"><strong>الطول والبنية الجسدية:</strong> {p_desc['height_build']}</div>
                <div class="trait-sub" style="margin-top: 6px; color: #b45309; font-weight: 700;"><strong>العمر التقديري:</strong> {p_desc['age_bracket']}</div>
            </div>

            <div class="trait-box">
                <h3>💼 طبيعة عمل ومهنة {partner_noun}</h3>
                <p><strong>الاشتقاق الفلكي:</strong> {p_career['derived_house']}</p>
                <p><strong>البرج والحاكم الفلكي:</strong> برج {p_career['sign']} (الحاكم: {p_career['ruler']})</p>
                <p style="margin-top: 6px;"><strong>التوقع المهني التفصيلي:</strong> {p_career['career_description']}</p>
                <div class="trait-sub">{p_career['planets_in_house']}</div>
            </div>

            <div class="trait-box">
                <h3>❤️ العلاقة الحميمية والاندماج الوجداني بعد الزواج</h3>
                <p><strong>الاشتقاق الفلكي:</strong> {p_intimacy['derived_house']}</p>
                <p><strong>طبيعة الاتصال الحميمي:</strong> وتد {p_intimacy['sign']} (طاقة العنصر {p_intimacy['element']}) - بحكم {p_intimacy['ruler']}</p>
                <p style="margin-top: 6px;"><strong>التفاصيل:</strong> {p_intimacy['intimacy_description']}</p>
            </div>

            <div class="trait-box">
                <h3>💰 ممتلكات وثروة {partner_noun} ومصادر دخله</h3>
                <p><strong>الاشتقاق الفلكي:</strong> {p_wealth['derived_house']}</p>
                <p><strong>البرج الحاكم لمال الشريك:</strong> برج {p_wealth['sign']} (الحاكم: {p_wealth['ruler']})</p>
                <p style="margin-top: 6px;"><strong>التقييم المالي:</strong> {p_wealth['wealth_description']}</p>
            </div>

            <div class="trait-box">
                <h3>🎉 طابع وأجواء حفل الزفاف</h3>
                <p><strong style="color: var(--gold); font-size: 15px;">{p_wedding['style']}</strong></p>
                <p style="margin-top: 6px;">{p_wedding['description']}</p>
            </div>

            <div class="trait-box">
                <h3>🌍 الجذور، الإقامة، والظروف الاجتماعية</h3>
                <ul style="padding-right: 20px; font-size: 13px; line-height: 1.8;">
                    <li><strong>صلة القرابة:</strong> {p_social['relative']['status']} - <span style="color: var(--text-muted);">{p_social['relative']['desc']}</span></li>
                    <li><strong>محل الإقامة:</strong> {p_social['residence']['status']} - <span style="color: var(--text-muted);">{p_social['residence']['desc']}</span></li>
                    <li><strong>الجنسية والديانة:</strong> {p_social['expatriate']['status']} - <span style="color: var(--text-muted);">{p_social['expatriate']['desc']}</span></li>
                    <li><strong>طبيعة التعارف:</strong> {p_social['history']['status']} - <span style="color: var(--text-muted);">{p_social['history']['desc']}</span></li>
                    <li><strong>نوع الزواج:</strong> {p_social['marriage_type']['status']} - <span style="color: var(--text-muted);">{p_social['marriage_type']['desc']}</span></li>
                </ul>
            </div>
        </div>

        <div style="margin-top: 30px;">
            <div class="card-header" style="font-size: 16px;">
                <span>جدول فحص وتدقيق الـ 50 دلالة زواج فلكية لسنة {y_data['year']}</span>
                <span style="font-size: 12px; color: var(--success);">المتحقق: {y_data['active_count']} دلالة نشطة</span>
            </div>
            
            <table class="indicators-table">
                <thead>
                    <tr>
                        <th style="width: 50px; text-align: center;">الرقم</th>
                        <th style="width: 140px;">الفئة الفلكية</th>
                        <th>الدلالة الفلكية وقاعدتها</th>
                        <th style="width: 100px; text-align: center;">الحالة</th>
                        <th>القيمة الفلكية المسجلة وتفاصيل الأورب</th>
                    </tr>
                </thead>
                <tbody>
            """
            for ind in y_data['indicators']:
                status_class = "active" if ind['is_active'] else "inactive"
                status_text = "متحققة ✓" if ind['is_active'] else "غير متحققة"
                row_bg = "background-color: #f0fdf4;" if ind['is_active'] else ""
                html += f"""
                    <tr style="{row_bg}">
                        <td style="text-align: center; font-weight: 700;">{ind['code']}</td>
                        <td style="color: var(--text-muted);">{ind['category']}</td>
                        <td>
                            <strong>{ind['name_ar']}</strong>
                            <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px;">{ind['description']}</div>
                        </td>
                        <td style="text-align: center;"><span class="status-badge {status_class}">{status_text}</span></td>
                        <td style="font-size: 12px; font-weight: 600; color: #1e293b;">{ind['detail']}</td>
                    </tr>
                """
            html += """
                </tbody>
            </table>
        </div>
    </div>
            """

    html += f"""
    <div class="footer">
        <p>تم استخراج هذا التقرير الفلكي التخصصي بناءً على حسابات إفيميريدس السويسرية عالية الدقة (Swiss Ephemeris DE431).</p>
        <p>جميع الحسابات الفلكية واشتقاقات البيوت خاضعة لأصول التنجيم الغربي الرصين وقواعد نقاط المنتصف (Cosmobiology Midpoints Axis).</p>
        <div class="signature-box">
            <div class="sig-item"><strong>تخصص البرنامج</strong><span>أبحاث الزواج والسنوية والميد بوينت</span></div>
            <div class="sig-item"><strong>الخبير والمطور الفلكي</strong><span>الفلكي الدكتور استرو رادار</span></div>
            <div class="sig-item"><strong>نطاق العمل</strong><span>حاسبة لـ 50 دلالة ارتباط عاطفي لخريطة العودة الشمسية v2.0</span></div>
        </div>
    </div>
</div>
</body>
</html>
"""
    return html

# =============================================================================
# 7. واجهة المستخدم الرئيسية وتدفق التنفيذ
# =============================================================================
st.markdown("""
<div class="main-header">
    <h1>حاسبة احتمالات سنوات الزواج والارتباط العاطفي الفلكية</h1>
    <p>تحليل فلكي غربي متقدم يدمج محور نقطة منتصف الشمس/القمر الميلادية، العودة الشمسية، واشتقاق البيوت</p>
    <p>تطوير الفلكي استرو رادار</p>
</div>
""", unsafe_allow_html=True)

with st.container():
    col1, col2, col3, col4 = st.columns([1.2, 1, 1.2, 1.2])
    
    with col1:
        st.markdown("#### 👤 البيانات الشخصية")
        name = st.text_input("اسم صاحب/ة الخريطة", "سارة")
        gender = st.selectbox("الجنس", ["أنثى", "ذكر"], index=0, help="يحدد توقع مواصفات العريس (للأنثى) أو العروس (للذكر)")
        partner_title = "العريس" if gender == "أنثى" else "العروس"
        partner_type = "groom" if gender == "أنثى" else "bride"

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
FIXED_MIDPOINT_ORB = 2.0     # أورب الميد بوينت (اقتران بأقل من 2.0 درجة)
FIXED_MIN_INDICATORS = 5     # 5 دلالات فما فوق للزواج
SCAN_AGE_MIN = 16            # نطاق العمر من 16
SCAN_AGE_MAX = 56            # لغاية 56 سنة

st.info("📌 **القواعد الفلكية الصارمة المطبقة آلياً:** أورب الاتصالات الفلكية = 1.0° | أورب تفعيل محور الميد بوينت = 2.0° (نفس البرج، مقابل، أو تربيع 90°) | الحد الأدنى لدلالات الزواج = 5 دلالات | فحص العمر = من 16 إلى 56 سنة.")

submit = st.button("🔮 بدء التحليل الفلكي واستخراج سنوات الزواج ومواصفات الشريك", type="primary")

if submit:
    b_city_obj = next((c for c in b_city_objects if c['name'] == b_city_name), None)
    sr_city_obj = next((c for c in sr_city_objects if c['name'] == sr_city_name), None)
    
    b_lat, b_lon = (b_city_obj['latitude'], b_city_obj['longitude']) if b_city_obj else (33.5138, 36.2765)
    sr_lat, sr_lon = (sr_city_obj['latitude'], sr_city_obj['longitude']) if sr_city_obj else (25.2048, 55.2708)
        
    b_tz = tf.timezone_at(lng=b_lon, lat=b_lat) or "UTC"
    sr_tz = tf.timezone_at(lng=sr_lon, lat=sr_lat) or "UTC"
    
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
    
    midpoint_lon = (natal_sun + natal_moon) / 2.0
    if abs(natal_sun - natal_moon) > 180:
        midpoint_lon = (midpoint_lon + 180) % 360
        
    midpoint_sign_idx = int(midpoint_lon / 30) % 12
    midpoint_deg = midpoint_lon % 30

    natal_data = {
        'cusps': natal_cusps,
        'planets': natal_planets,
        'midpoint_lon': midpoint_lon
    }

    opp_sign_idx = (midpoint_sign_idx + 6) % 12
    sq1_sign_idx = (midpoint_sign_idx + 3) % 12
    sq2_sign_idx = (midpoint_sign_idx + 9) % 12

    st.markdown(f"""
    <div class="info-card">
        <h3 style="color: #1e3a8a; margin-bottom: 8px;">🌟 المعطيات الميلادية الثابتة ومحور الميد بوينت لـ ({name}):</h3>
        <p>• موقع الشمس الميلادية: <strong>{natal_sun%30:.2f}° {ZODIAC_NAMES_AR[int(natal_sun/30)%12]}</strong> (البيت {natal_planets['Sun']['house']})</p>
        <p>• موقع القمر الميلادي: <strong>{natal_moon%30:.2f}° {ZODIAC_NAMES_AR[int(natal_moon/30)%12]}</strong> (البيت {natal_planets['Moon']['house']})</p>
        <p style="color: #b91c1c; font-size: 16px;">• <strong>نقطة منتصف (شمس - قمر) الميلادية: {midpoint_deg:.2f}° {ZODIAC_NAMES_AR[midpoint_sign_idx]}</strong></p>
        <p style="color: #1e3a8a;">• <strong>أبراج محور التفعيل (Axis):</strong> نفس البرج ({ZODIAC_NAMES_AR[midpoint_sign_idx]}) + المقابل ({ZODIAC_NAMES_AR[opp_sign_idx]}) + التربيع ({ZODIAC_NAMES_AR[sq1_sign_idx]} / {ZODIAC_NAMES_AR[sq2_sign_idx]}) بدرجة {midpoint_deg:.2f}° (أورب أقل من 2.0°).</p>
    </div>
    """, unsafe_allow_html=True)

    start_year = birth_date.year + SCAN_AGE_MIN
    end_year = birth_date.year + SCAN_AGE_MAX
    years_list = list(range(start_year, end_year + 1))
    total_years = len(years_list)
    
    candidate_years = []
    progress_bar = st.progress(0.0)
    status_text = st.empty()

    for i, target_year in enumerate(years_list):
        progress_val = min(1.0, (i + 1) / total_years)
        status_text.text(f"جاري تدقيق وحساب سنوية عام {target_year} م...")
        
        jd_sr = find_exact_solar_return(target_year, natal_sun, birth_date.month, birth_date.day, birth_time, b_tz)
        sr_cusps, _ = swe.houses(jd_sr, sr_lat, sr_lon, b'R')
        
        sr_planets = {}
        for p_name, p_id in PLANET_IDS.items():
            res = swe.calc_ut(jd_sr, p_id)
            lon = res[0][0]
            sr_planets[p_name] = {
                'lon': lon,
                'sign': int(lon / 30) % 12,
                'deg_in_sign': lon % 30,
                'house': get_house_of_point(lon, sr_cusps)
            }
            
        sr_rahu_lon = sr_planets['Rahu']['lon']
        sr_ketu_lon = (sr_rahu_lon + 180) % 360
        sr_planets['Ketu'] = {
            'lon': sr_ketu_lon,
            'sign': int(sr_ketu_lon / 30) % 12,
            'deg_in_sign': sr_ketu_lon % 30,
            'house': get_house_of_point(sr_ketu_lon, sr_cusps)
        }

        sr_data = {
            'cusps': sr_cusps,
            'planets': sr_planets
        }

        eval_result = evaluate_all_50_indicators(natal_data, sr_data, general_orb=FIXED_ASPECT_ORB, midpoint_orb=FIXED_MIDPOINT_ORB)
        activated_midpoint_list = eval_result['activated_midpoint_planets']
        active_count = eval_result['active_count']

        if activated_midpoint_list and active_count >= FIXED_MIN_INDICATORS:
            primary_activator = activated_midpoint_list[0]
            
            partner_physical = get_physical_appearance(
                primary_activator['planet'],
                primary_activator['lon'],
                partner_title=partner_title,
                partner_type=partner_type
            )
            partner_career = derive_partner_career(natal_cusps, natal_planets, partner_title=partner_title)
            partner_intimacy = derive_partner_intimacy(natal_cusps, natal_planets, partner_title=partner_title)
            partner_wealth = derive_partner_wealth(natal_cusps, natal_planets, partner_title=partner_title)
            wedding_style = derive_wedding_party(natal_cusps, sr_cusps[0], sr_planets)
            partner_social = derive_partner_social_details(natal_cusps, natal_planets, partner_title=partner_title)

            diff_str = f"{primary_activator['diff']:.2f}° ({int(primary_activator['diff'])}° {int((primary_activator['diff']%1)*60)}')"

            candidate_years.append({
                "year": target_year,
                "age": target_year - birth_date.year,
                "active_count": active_count,
                "indicators": eval_result['indicators'],
                "activated_midpoint_planets": activated_midpoint_list,
                "primary_activator": primary_activator,
                "midpoint_diff_str": diff_str,
                "partner_physical": partner_physical,
                "partner_career": partner_career,
                "partner_intimacy": partner_intimacy,
                "partner_wealth": partner_wealth,
                "wedding_style": wedding_style,
                "partner_social": partner_social
            })

        progress_bar.progress(progress_val)

    status_text.empty()
    progress_bar.empty()

    native_info = {
        'name': name,
        'gender': gender,
        'birth_date': birth_date.strftime("%Y-%m-%d"),
        'birth_time': birth_time.strftime("%H:%M"),
        'birth_city': b_city_name,
        'birth_country': b_country_name,
        'sr_city': sr_city_name,
        'sr_country': sr_country_name,
        'natal_sun_deg': natal_sun % 30,
        'natal_sun_sign': ZODIAC_NAMES_AR[int(natal_sun/30)%12],
        'natal_moon_deg': natal_moon % 30,
        'natal_moon_sign': ZODIAC_NAMES_AR[int(natal_moon/30)%12],
        'midpoint_deg': midpoint_deg,
        'midpoint_sign': ZODIAC_NAMES_AR[midpoint_sign_idx]
    }

    html_report_content = generate_printable_html_report(
        native_info, candidate_years, general_orb=FIXED_ASPECT_ORB, midpoint_orb=FIXED_MIDPOINT_ORB
    )

    st.markdown("---")
    st.subheader("📑 التقرير الفلكي الشامل المطبوع")
    st.download_button(
        label=f"📥 تحميل التقرير الفلكي الكامل لـ ({name}) بصيغة HTML جاهز للطباعة الفورية (PDF)",
        data=html_report_content,
        file_name=f"تقرير_الزواج_والارتباط_الفلكي_{name}.html",
        mime="text/html",
        use_container_width=True
    )
    st.markdown("---")

    if candidate_years:
        st.success(f"تم رصد **{len(candidate_years)}** سنة زواج مؤكدة فلكياً استوفت شرط تفعيل محور الميد بوينت (فرق < 2.0°) وتجاوزت 5 دلالات من أصل 50!")
        
        for y_data in candidate_years:
            year_title = f"💍 سنة {y_data['year']} ميلادي (العمر: {y_data['age']} سنة) — تحقق {y_data['active_count']} دلالة من أصل 50"
            with st.expander(year_title, expanded=True):
                
                p_desc = y_data['partner_physical']
                prim = y_data['primary_activator']
                st.markdown(f"""
                <div style="background: #eff6ff; padding: 12px 16px; border-radius: 8px; border-right: 4px solid #3b82f6; margin-bottom: 15px;">
                    <strong>الكوكب السنوي المفعل لمحور الميد بوينت الميلادي (شمس/قمر):</strong>
                    <span style="color: #1d4ed8; font-weight: 800;">{p_desc['planet_ar']}</span> 
                    — <span style="color: #b91c1c; font-weight: 700;">{prim['aspect_type']}</span> 
                    (الموقع السنوي: {p_desc['deg_in_sign']:.2f}° {p_desc['sign_name']} | الفرق الزاوي عن المحور: {y_data['midpoint_diff_str']})
                </div>
                """, unsafe_allow_html=True)

                tab1, tab2 = st.tabs([f"📋 المواصفات الفلكية لـ {partner_title} (اشتقاق البيوت)", "🔍 تفاصيل الـ 50 دلالة زواج المفحوصة"])
                
                with tab1:
                    col_t1, col_t2 = st.columns(2)
                    
                    with col_t1:
                        st.markdown(f"#### 👑 1. المظهر الخارجي، الوجه، والعمر التقديري")
                        st.write(f"**تأثير الكوكب:** {p_desc['title']}")
                        st.write(f"**ملامح الوجه الدقيقة:** {p_desc['face']}")
                        st.write(f"**الطول والبنية الجسدية:** {p_desc['height_build']}")
                        st.info(f"**العمر التقديري لـ {partner_title}:** {p_desc['age_bracket']}")
                        
                        st.markdown("---")
                        st.markdown(f"#### 💼 2. طبيعة عمل ومهنة {partner_title} (العاشر من السابع = الرابع الميلادي)")
                        p_car = y_data['partner_career']
                        st.write(f"**برج البيت وحاكمه:** {p_car['sign']} (الحاكم: {p_car['ruler']})")
                        st.write(f"**التوقع المهني:** {p_car['career_description']}")
                        st.caption(f"{p_car['planets_in_house']}")

                        st.markdown("---")
                        st.markdown(f"#### ❤️ 3. العلاقة الحميمية بعد الزواج (الثامن من السابع = الثاني الميلادي)")
                        p_int = y_data['partner_intimacy']
                        st.write(f"**طبيعة الاتصال الحميمي:** برج {p_int['sign']} ({p_int['element']}) — الحاكم: {p_int['ruler']}")
                        st.write(f"**التفاصيل الوجدانية:** {p_int['intimacy_description']}")

                    with col_t2:
                        st.markdown(f"#### 💰 4. ممتلكات وثروة {partner_title} (الثاني من السابع = الثامن الميلادي)")
                        p_wlth = y_data['partner_wealth']
                        st.write(f"**البرج الحاكم للمال:** برج {p_wlth['sign']} — الحاكم: {p_wlth['ruler']}")
                        st.write(f"**التقييم المالي:** {p_wlth['wealth_description']}")

                        st.markdown("---")
                        st.markdown(f"#### 🎉 5. طابع وأجواء حفل الزفاف")
                        p_wed = y_data['wedding_style']
                        st.write(f"**النمط المتوقع:** **{p_wed['style']}**")
                        st.write(f"{p_wed['description']}")

                        st.markdown("---")
                        st.markdown(f"#### 🌍 6. الأسئلة الاجتماعية الدقيقة والنسب والإقامة")
                        p_soc = y_data['partner_social']
                        st.write(f"• **أقارب أم غريب:** {p_soc['relative']['status']} ({p_soc['relative']['desc']})")
                        st.write(f"• **محل الإقامة:** {p_soc['residence']['status']} ({p_soc['residence']['desc']})")
                        st.write(f"• **الجنسية والديانة:** {p_soc['expatriate']['status']} ({p_soc['expatriate']['desc']})")
                        st.write(f"• **طبيعة التعارف:** {p_soc['history']['status']} ({p_soc['history']['desc']})")
                        st.write(f"• **نوع الزواج:** {p_soc['marriage_type']['status']} ({p_soc['marriage_type']['desc']})")

                with tab2:
                    st.markdown(f"##### جدول الفحص الشامل لـ 50 دلالة فلكية (سنة {y_data['year']}):")
                    filter_active = st.checkbox(f"عرض الدلالات المتحققة فقط ({y_data['active_count']} دلالة)", value=False, key=f"filter_{y_data['year']}")
                    
                    for ind in y_data['indicators']:
                        if filter_active and not ind['is_active']:
                            continue
                        
                        icon = "✅" if ind['is_active'] else "⚪"
                        status_str = "**[متحققة]**" if ind['is_active'] else "[غير متحققة]"
                        color = "#15803d" if ind['is_active'] else "#64748b"
                        
                        st.markdown(f"""
                        <div style="padding: 8px 12px; margin-bottom: 6px; border-radius: 6px; background: {'#f0fdf4' if ind['is_active'] else '#f8fafc'}; border: 1px solid {'#bbf7d0' if ind['is_active'] else '#e2e8f0'};">
                            <span style="font-weight: 700; color: {color};">{icon} {ind['code']}: {ind['name_ar']} {status_str}</span>
                            <div style="font-size: 13px; color: #334155; margin-top: 2px;">{ind['detail']} — <span style="color: #64748b;">({ind['description']})</span></div>
                        </div>
                        """, unsafe_allow_html=True)
    else:
        st.warning("لم يتم العثور على سنوات تطابق جميع الشروط الفلكية المثبتة والصارمة (تفعيل كوكب سنوي لمحور الميد بوينت 0°/90°/180° بفرق أقل من 2.0° مع 5 دلالات فأكثر خلال الأعمار من 16 إلى 56 سنة).")
