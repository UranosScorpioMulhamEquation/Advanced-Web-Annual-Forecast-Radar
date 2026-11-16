from __future__ import annotations
import base64
from dataclasses import dataclass
import datetime
from datetime import date, time, timezone
import html
import math
import os
import traceback
from typing import Any, Dict, List, Optional, Tuple

import geonamescache
import pandas as pd
import pytz
import streamlit as st
from timezonefinder import TimezoneFinder
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# استيراد مكتبة Swiss Ephemeris بطريقة آمنة ومرنة لدعم كافة البيئات البرمجية
try:
    import swisseph as swe
except ImportError:
    try:
        import libephemeris as swe
    except ImportError:
        import swisseph as swe

# =============================================================================
# 1. إعدادات المحرك الفلكي والواجهة التفاعلية (Streamlit RTL)
# =============================================================================
EPHE_PATH = "./ephe"
if not os.path.exists(EPHE_PATH):
    os.makedirs(EPHE_PATH)

swe.set_ephe_path(EPHE_PATH)

st.set_page_config(
    page_title="المحرك الفلكي المتقدم للتوافقية والقطبية الطاقية وصلاحية الزواج",
    page_icon="🔭",
    layout="wide"
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
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
        color: #ffffff;
        font-weight: 800;
        font-size: 17px;
        padding: 14px;
        border-radius: 10px;
        border: 1px solid #d4af37;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #d4af37 0%, #b48a1e 100%);
        color: #0f172a;
        border-color: #fde047;
        box-shadow: 0 4px 18px rgba(212, 175, 55, 0.45);
    }
    .main-header {
        text-align: center;
        background: linear-gradient(135deg, #090d16 0%, #172554 100%);
        color: #f8fafc;
        padding: 26px;
        border-radius: 14px;
        border: 2px solid #d4af37;
        margin-bottom: 25px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.12);
    }
    .main-header h1 {
        font-family: 'Amiri', serif;
        color: #facc15;
        font-size: 30px;
        margin-bottom: 8px;
        font-weight: 700;
    }
    .result-card {
        background: #ffffff;
        border-right: 6px solid #d4af37;
        border-radius: 10px;
        padding: 22px;
        margin-bottom: 20px;
        box-shadow: 0 3px 12px rgba(0,0,0,0.06);
        border: 1px solid #e2e8f0;
    }
    .polarity-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 18px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border: 1px solid #e2e8f0;
        margin-bottom: 15px;
    }
    .rec-box {
        background: #f8fafc;
        border-right: 5px solid #2563eb;
        padding: 18px;
        border-radius: 10px;
        margin-top: 15px;
        border: 1px solid #cbd5e1;
    }
    .planet-detail-box {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 2. وحدة البيانات الجغرافية وإدارة المناطق الزمنية
# =============================================================================
@dataclass
class City:
    geonameid: str
    name: str
    country_code: str
    latitude: float
    longitude: float
    admin1: str
    population: int

    def __getitem__(self, key):
        return getattr(self, key)
    
    def get(self, key, default=None):
        return getattr(self, key, default)

@st.cache_data
def load_cities():
    gc = geonamescache.GeonamesCache()
    cities_list = []
    for city_id, city_data in gc.get_cities().items():
        if city_data.get("population", 0) >= 15000:
            cities_list.append(
                City(
                    geonameid=city_id,
                    name=city_data.get("name", ""),
                    country_code=city_data.get("countrycode", ""),
                    latitude=float(city_data.get("latitude", 0.0)),
                    longitude=float(city_data.get("longitude", 0.0)),
                    admin1=city_data.get("admin1code", ""),
                    population=int(city_data.get("population", 0)),
                )
            )
    return cities_list

@st.cache_data
def load_countries():
    gc = geonamescache.GeonamesCache()
    return gc.get_countries()

def get_cities_by_country(country_code: str) -> list[City]:
    cities = load_cities()
    return sorted(
        [c for c in cities if c.country_code == country_code],
        key=lambda c: c.population,
        reverse=True,
    )

def get_timezone_for_city(city: City | None) -> str:
    if not city:
        return "UTC"
    try:
        tf = TimezoneFinder()
        tz = tf.timezone_at(lat=city.latitude, lng=city.longitude)
        return tz if tz else "UTC"
    except Exception:
        return "UTC"

# =============================================================================
# 3. المعاجم الفلكية الشاملة (الكواكب العشرة، الكرامات، الحدود، الكويكبات، النجوم)
# =============================================================================
ZODIAC_NAMES_AR = [
    "الحمل", "الثور", "الجوزاء", "السرطان",
    "الأسد", "العذراء", "الميزان", "العقرب",
    "القوس", "الجدي", "الدلو", "الحوت"
]
ZODIAC_NAMES = ZODIAC_NAMES_AR

PERSONAL_PLANETS = ["Sun", "Moon", "Mercury", "Venus", "Mars"]

ALL_PLANETS_IDS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO
}

ALL_PLANETS_AR = {
    "Sun": "الشمس",
    "Moon": "القمر",
    "Mercury": "عطارد",
    "Venus": "الزهرة",
    "Mars": "المريخ",
    "Jupiter": "المشتري",
    "Saturn": "زحل",
    "Uranus": "أورانوس",
    "Neptune": "نبتون",
    "Pluto": "بلوتو"
}

# متوسط السرعة اليومية للكواكب الشخصية (درجة/يوم) لتقييم السرعة والبطء
AVERAGE_DAILY_SPEEDS = {
    "Sun": 0.9856,
    "Moon": 13.1764,
    "Mercury": 1.383,
    "Venus": 1.200,
    "Mars": 0.524
}

# أرباب البيوت (Domicile Rulers)
SIGN_RULERS = {
    0: "Mars", 1: "Venus", 2: "Mercury", 3: "Moon",
    4: "Sun", 5: "Mercury", 6: "Venus", 7: "Mars",
    8: "Jupiter", 9: "Saturn", 10: "Saturn", 11: "Jupiter"
}

# الشرف (Exaltations) مع درجة الشرف الدقيقة
EXALTATIONS = {
    "Sun": (0, 19.0),     # الحمل 19
    "Moon": (1, 3.0),     # الثور 3
    "Mercury": (5, 15.0), # العذراء 15
    "Venus": (11, 27.0),  # الحوت 27
    "Mars": (9, 28.0)     # الجدي 28
}

# الوبال (Detriments)
DETRIMENTS = {
    "Sun": [10],
    "Moon": [9],
    "Mercury": [8, 11],
    "Venus": [0, 7],
    "Mars": [1, 6]
}

# الهبوط (Falls)
FALLS = {
    "Sun": 6,      # الميزان
    "Moon": 7,     # العقرب
    "Mercury": 11, # الحوت
    "Venus": 5,    # العذراء
    "Mars": 3      # السرطان
}

# المثلثات الفلكية (Triplicity Rulers: النهاري، الليلي، الشريك)
TRIPLICITY_RULERS = {
    0: ("Sun", "Jupiter", "Saturn"),     # ناري
    1: ("Venus", "Moon", "Mars"),        # ترابي
    2: ("Saturn", "Mercury", "Jupiter"), # هوائي
    3: ("Venus", "Mars", "Moon")         # مائي
}

# الحدود المصرية (Egyptian Terms / Bounds)
EGYPTIAN_TERMS = {
    0: [(6, "Jupiter"), (12, "Venus"), (20, "Mercury"), (25, "Mars"), (30, "Saturn")],   # الحمل
    1: [(8, "Venus"), (14, "Mercury"), (22, "Jupiter"), (27, "Saturn"), (30, "Mars")],   # الثور
    2: [(6, "Mercury"), (12, "Jupiter"), (17, "Venus"), (24, "Mars"), (30, "Saturn")],   # الجوزاء
    3: [(7, "Mars"), (13, "Venus"), (19, "Mercury"), (26, "Jupiter"), (30, "Saturn")],   # السرطان
    4: [(6, "Jupiter"), (11, "Venus"), (18, "Saturn"), (24, "Mercury"), (30, "Mars")],   # الأسد
    5: [(7, "Mercury"), (17, "Venus"), (21, "Jupiter"), (28, "Mars"), (30, "Saturn")],   # العذراء
    6: [(6, "Saturn"), (14, "Mercury"), (21, "Jupiter"), (28, "Venus"), (30, "Mars")],   # الميزان
    7: [(7, "Mars"), (11, "Venus"), (19, "Mercury"), (24, "Jupiter"), (30, "Saturn")],   # العقرب
    8: [(12, "Jupiter"), (17, "Venus"), (21, "Mercury"), (26, "Saturn"), (30, "Mars")],  # القوس
    9: [(7, "Mercury"), (14, "Jupiter"), (22, "Venus"), (26, "Saturn"), (30, "Mars")],   # الجدي
    10: [(7, "Mercury"), (13, "Venus"), (20, "Jupiter"), (25, "Mars"), (30, "Saturn")],  # الدلو
    11: [(12, "Venus"), (16, "Jupiter"), (19, "Mercury"), (28, "Mars"), (30, "Saturn")]  # الحوت
}

# الوجوه / العشريات الكلدانية (Chaldean Decans)
CHALDEAN_ORDER = ["Mars", "Sun", "Venus", "Mercury", "Moon", "Saturn", "Jupiter"]

# الكويكبات والنقاط الفلكية الشاملة للخرائط المقارنة والتوافقية
ASTEROIDS_IDS = {
    "Chiron": swe.CHIRON,
    "Ceres": swe.CERES,
    "Pallas": swe.PALLAS,
    "Juno": swe.JUNO,
    "Vesta": swe.VESTA
}

ASTEROIDS_AR = {
    "Chiron": "كيرون (المعالج)",
    "Ceres": "سيريس (الأمومة والرعاية)",
    "Pallas": "بالاس (الحكمة والاستراتيجية)",
    "Juno": "جونو (عقد الزواج والوفاء)",
    "Vesta": "فيستا (الالتزام والبيت)"
}

# المعجم الكامل لـ 17 جرماً ونقطة فلكية في التوافقية
PLANETS = {
    swe.SUN: {"name": "الشمس", "type": "شخصي", "desc": "الهوية والجوهر والوعي الأساسي"},
    swe.MOON: {"name": "القمر", "type": "شخصي", "desc": "العاطفة، المزاج، والاحتياجات النفسية"},
    swe.MERCURY: {"name": "عطارد", "type": "شخصي", "desc": "طريقة التفكير وأسلوب التبادل والاتصال"},
    swe.VENUS: {"name": "الزهرة", "type": "شخصي", "desc": "الحب، الانسجام، العواطف، والقيم المالية"},
    swe.MARS: {"name": "المريخ", "type": "شخصي", "desc": "الطاقة الجسدية، الحماسة، والدافع والغيرة"},
    swe.JUPITER: {"name": "المشتري", "type": "اجتماعي", "desc": "الحظ، التوسع، التفاهم، والفرص المشتركة"},
    swe.SATURN: {"name": "زحل", "type": "اجتماعي", "desc": "المسؤولية، الالتزام، القيود، ومصادر الضغط"},
    swe.URANUS: {"name": "أورانوس", "type": "خارجي", "desc": "المفاجآت، التمرد، والحاجة للحرية"},
    swe.NEPTUNE: {"name": "نبتون", "type": "خارجي", "desc": "الخيال، الرومانسية العليا، الوهم، أو الروحانية"},
    swe.PLUTO: {"name": "بلوتو", "type": "خارجي", "desc": "التحول الجذري، السيطرة، والعمق العاطفي"},
    swe.TRUE_NODE: {"name": "العقدة الشمالية (راهو)", "type": "روحي", "desc": "المسار القدري وقدر الارتباط المشترك"},
    swe.CHIRON: {"name": "كيرون", "type": "كويكب", "desc": "الجروح العميقة، الشفاء، والتعاطف التوافقي"},
    swe.JUNO: {"name": "جونو", "type": "كويكب", "desc": "ارتباط الزواج، الوفاء، والشراكة الرسمية"},
    swe.MEAN_APOG: {"name": "ليليث السوداء", "type": "نقطة فلكية", "desc": "الجانب المظلم، الرغبات الدفينة، والجاذبية المغناطيسية"},
    swe.CERES: {"name": "سيريس", "type": "كويكب", "desc": "الرعاية، الحنان، والدعم الأسري والعاطفي"},
    swe.PALLAS: {"name": "بالاس", "type": "كويكب", "desc": "الحكمة، الفكر الاستراتيجي، وحل النزاعات"},
    swe.VESTA: {"name": "فيستا", "type": "كويكب", "desc": "الإخلاص المطلق، التكريس، والتركيز العاطفي"}
}

# أهم النجوم الثابتة وتأثيرها التنجيمي المئوي
FIXED_STARS_CATALOG = [
    ("Regulus", "قلب الأسد (Regulus)", +5.0, "نجم ملكي: مجد وقيادة ورفعة"),
    ("Spica", "السماك الأعزل (Spica)", +5.5, "أعظم نجوم الحظ والمواهب والحماية"),
    ("Aldebaran", "الدبران (Aldebaran)", +3.5, "نجم ملكي: نجاح وشجاعة بشرط النزاهة"),
    ("Antares", "قلب العقرب (Antares)", +2.5, "نجم ملكي: قوة عاطفية وحسم"),
    ("Fomalhaut", "فم الحوت (Fomalhaut)", +3.5, "نجم ملكي: مثالية وتألق روحي"),
    ("Sirius", "الشعرى اليمانية (Sirius)", +4.5, "تألق وشهرة ونجاح استثنائي"),
    ("Vega", "النسر الواقع (Vega)", +3.0, "جاذبية فنية والكاريزما وسحر"),
    ("Arcturus", "السماك الرامح (Arcturus)", +3.5, "ريادة وعدالة وثروة"),
    ("Algol", "رأس الغول (Algol)", -5.5, "نجم عنيف: حدة وتوتر شديد"),
    ("Alcyone", "الثريا (Alcyone)", -2.5, "حساسية عاطفية وتقلبات")
]

# =============================================================================
# 4. دوال الحسابات الفلكية والهندسية الدقيقة
# =============================================================================
def angular_diff(lon1: float, lon2: float) -> float:
    """حساب أقصر مسافة زاوية على الدائرة البروجية (0 إلى 180 درجة)."""
    diff = abs(lon1 - lon2) % 360.0
    return min(diff, 360.0 - diff)

def get_aspect_details(lon1: float, lon2: float) -> Optional[Tuple[str, float, float]]:
    """تحديد نوع الاتصال الفلكي والاورب ومعامل الدقة (0.6 إلى 1.0) لتقييم الكوكب."""
    dist = angular_diff(lon1, lon2)
    aspects_rules = [
        ("اقتران (0°)", 0.0, 8.0),
        ("مقابلة (180°)", 180.0, 8.0),
        ("تثليث (120°)", 120.0, 7.0),
        ("تربيع (90°)", 90.0, 7.0),
        ("تسديس (60°)", 60.0, 5.0),
    ]
    for asp_name, target_angle, max_orb in aspects_rules:
        orb = abs(dist - target_angle)
        if orb <= max_orb:
            precision_factor = 1.0 - (orb / max_orb) * 0.4
            return asp_name, orb, precision_factor
    return None

def calculate_aspect(lon1: float, lon2: float) -> Tuple[Optional[str], int]:
    """حساب الاتصال الفلكي بين شريكين في الخريطة التوافقية (Synastry)."""
    diff = abs(lon1 - lon2)
    if diff > 180:
        diff = 360 - diff

    if diff <= 6:
        return "اقتران (0° - دمج طاقات وتأثير مباشر)", +3
    elif abs(diff - 60) <= 6:
        return "تسديس (60° - فرصة وتناغم سلس)", +2
    elif abs(diff - 90) <= 6:
        return "تربيع (90° - تحدي واحتكاك ضاغط)", -3
    elif abs(diff - 120) <= 6:
        return "تثليث (120° - تدفق وتوافق طبيعي عالٍ)", +4
    elif abs(diff - 180) <= 6:
        return "معارضة (180° - شد وجذب وتكامل أو صراع)", -2

    return None, 0

def get_term_ruler(sign_idx: int, deg_in_sign: float) -> str:
    """استخراج رب الحد المصري للدرجة داخل البرج."""
    for limit, ruler in EGYPTIAN_TERMS[sign_idx]:
        if deg_in_sign < limit:
            return ruler
    return EGYPTIAN_TERMS[sign_idx][-1][1]

def get_face_ruler(sign_idx: int, deg_in_sign: float) -> str:
    """استخراج رب الوجه (العشرية) وفق الترتيب الكلداني."""
    decan_idx = min(2, int(deg_in_sign // 10))
    total_decan = sign_idx * 3 + decan_idx
    return CHALDEAN_ORDER[total_decan % 7]

def compute_fixed_stars(jd: float) -> List[Dict[str, Any]]:
    """حساب المواقع الدقيقة للنجوم الثابتة في لحظة الميلاد مع تصحيح مبادرة الاعتدالين."""
    stars_positions = []
    for star_key, star_ar, weight, desc in FIXED_STARS_CATALOG:
        try:
            res, _ = swe.fixstar2_ut(star_key, jd)
            stars_positions.append({
                "key": star_key,
                "name_ar": star_ar,
                "lon": res[0],
                "weight": weight,
                "desc": desc
            })
        except Exception:
            continue
    return stars_positions

def analyze_house_overlay(planet_id: int, planet_name: str, house_num: int, target_name: str) -> Tuple[Optional[str], str]:
    """تحليل إسقاط الكواكب في بيوت الشريك (House Overlays)."""
    warning = None
    interpretations = {
        swe.SATURN: {
            8: f"⚠️ **تحذير خطير:** زحل لـ {planet_name} يقع في البيت الثامن لـ {target_name} (ضغط مالي، قيود على الموارد المشتركة، وثقل نفسي وعاطفي).",
            7: f"⚠️ **تنبيه:** زحل يقع في البيت السابع لـ {target_name} (يفرض التزامات رسمية قاسية ولكنه يسبب بروداً وجفاءً عاطفياً).",
            4: f"⚠️ **تنبيه:** زحل يقع في البيت الرابع لـ {target_name} (ضغط عائلي، جفاف معيشي، وصعوبة في الاستقرار المنزلي).",
            1: f"⚠️ **تنبيه:** زحل يقع في البيت الأول لـ {target_name} (فرض رقابة وسلطة وتقليل من عفوية وحيوية الطرف الآخر).",
        },
        swe.PLUTO: {
            8: f"🔥 **تنبيه شديد:** بلوتو يقع في البيت الثامن لـ {target_name} (طاقة سيطرة، غيرة جارفة، وصراعات على النفوذ وأزمات عميقة).",
            7: f"🔥 **تنبيه:** بلوتو يقع في البيت السابع لـ {target_name} (علاقة مكثفة للغاية تحمل طابع الهيمنة أو التحولات العنيفة).",
            1: f"🔥 **تنبيه:** بلوتو يقع في البيت الأول لـ {target_name} (تأثير مغناطيسي مهيمن قد يتحول لسيطرة خانقة إن لم يتم ضبطه).",
        },
        swe.MARS: {
            8: f"⚡ **تنبيه:** المريخ يقع في البيت الثامن لـ {target_name} (جذب جسدي وكيمياء عالية، يرافقها احتكاكات ونزاعات متكررة).",
            1: f"⚡ **تنبيه:** المريخ يقع في البيت الأول لـ {target_name} (طاقة عالية، اصطدام مباشر في المبادرات والآراء وتهور في الحوار).",
            7: f"⚡ **تنبيه:** المريخ يقع في البيت السابع لـ {target_name} (شعلة تنافس أو خلافات حادة ومباشرة تشتعل بسرعة).",
        },
        swe.JUNO: {
            1: f"💍 **إشارة إيجابية:** جونو في البيت الأول لـ {target_name} (شعور قوي بالانتماء والرغبة العالية في إضفاء الطابع الرسمي على العلاقة).",
            7: f"💍 **إشارة إيجابية:** جونو في البيت السابع لـ {target_name} (تطابق مثالي لطاقة الزواج والشراكة الملزمة والوفاء المتبادل).",
            4: f"🏠 **إشارة إيجابية:** جونو في البيت الرابع لـ {target_name} (استقرار منزلي ورغبة عميقة في تأسيس عائلة وبناء عش الزوجية).",
        },
        swe.CHIRON: {
            8: f"🩹 **تأثير علاجي:** كيرون في البيت الثامن لـ {target_name} (عمق عاطفي وقدرة على مداواة الجروح والآلام النفسية السابقة معاً).",
            7: f"🩹 **تأثير علاجي:** كيرون في البيت السابع لـ {target_name} (فهم متبادل للضعف الإنساني وتحقيق توازن وتصالح وجداني).",
        },
        swe.MEAN_APOG: {
            5: f"🔥 **جاذبية خاصة:** ليليث في البيت الخامس لـ {target_name} (كيمياء رومانسية وجاذبية مغناطيسية طاغية لا يمكن مقاومتها).",
            8: f"🔥 **كيمياء عميقة:** ليليث في البيت الثامن لـ {target_name} (انجذاب روحي وجسدي جارف يحمل طابعاً سرياً أو مكثفاً للغاية).",
        }
    }

    if planet_id in interpretations and house_num in interpretations[planet_id]:
        warning = interpretations[planet_id][house_num]

    general_notes = {
        swe.SUN: f"يسلط ضوء الوعي والهوية على شؤون البيت {house_num} لـ {target_name}.",
        swe.MOON: f"يثير عواطف عميقة وتجاوباً وجدانياً في شؤون البيت {house_num} لـ {target_name}.",
        swe.MERCURY: f"ينشط الحوار وتبادل الأفكار الفكرية والتجارية في البيت {house_num} لـ {target_name}.",
        swe.VENUS: f"يجلب الانسجام، المودة، الراحة، والبهجة لبيت {house_num} لـ {target_name}.",
        swe.MARS: f"يحفز طاقة وحماسة وفي بعض الأحيان حدة في البيت {house_num} لـ {target_name}.",
        swe.JUPITER: f"🌟 يجلب الحظ، التوسع، والدعم المادي والمعنوي في البيت {house_num} لـ {target_name}.",
        swe.SATURN: f"يفرض دروساً ومسؤوليات جادة وهيكلة واضحة في البيت {house_num} لـ {target_name}.",
        swe.URANUS: f"يجلب مفاجآت ورغبة في التجدد والكسر للروتين في البيت {house_num} لـ {target_name}.",
        swe.NEPTUNE: f"يضفي مسحة رومانسية خيالية أو غموضاً وشفافية في البيت {house_num} لـ {target_name}.",
        swe.PLUTO: f"يحدث تأثيراً تحولياً وعميقاً في شؤون البيت {house_num} لـ {target_name}.",
        swe.TRUE_NODE: f"يربط المسار القدري والروحي للشريك بشؤون البيت {house_num} لـ {target_name}.",
        swe.CHIRON: f"يلامس نقاط الضعف ويفتح باب الشفاء العاطفي في شؤون البيت {house_num} لـ {target_name}.",
        swe.JUNO: f"يعزز الالتزام، الوفاء، والروابط الرسمية في شؤون البيت {house_num} لـ {target_name}.",
        swe.MEAN_APOG: f"يخلق جاذبية مغناطيسية ورغبات غير تقليدية في شؤون البيت {house_num} لـ {target_name}.",
        swe.CERES: f"يوفر الرعاية والحنان والدعم الأسري في شؤون البيت {house_num} لـ {target_name}.",
        swe.PALLAS: f"يجلب الحلول الذكية والتفكير الاستراتيجي المشترك في شؤون البيت {house_num} لـ {target_name}.",
        swe.VESTA: f"يعزز الولاء والإخلاص المطلق والتركيز في شؤون البيت {house_num} لـ {target_name}."
    }

    note = warning if warning else general_notes.get(planet_id, f"تأثير في البيت {house_num} لـ {target_name}.")
    return warning, note

# =============================================================================
# 5. محرك تقييم قوى الكواكب الشخصية (مقياس 100 نقطة شامل الكرامات والاتصالات)
# =============================================================================
def evaluate_planet_100_scale(
    planet_name: str,
    all_planets: Dict[str, Dict[str, Any]],
    asteroids: Dict[str, Dict[str, Any]],
    fixed_stars: List[Dict[str, Any]],
    is_day_chart: bool,
    has_birth_time: bool
) -> Tuple[float, List[str], Dict[str, float], List[Dict[str, str]]]:
    """
    حساب قوة الكوكب الشخصي من أصل 100 نقطة بدمج:
    - الكرامات الذاتية الخمس (البيت، الشرف، المثلثة، الحد، الوجه) والانتكاسات (الوبال، الهبوط، الغربة)
    - التبادل بالربوبية (Mutual Reception)
    - الكرامات العرضية: البيوت، السرعة، التراجع، الموقف من الشمس (Cazimi / Combust / Under Beams)، الحيّز
    - اتصالات الكواكب العشرة، الكويكبات الخمسة، والنجوم الثابتة
    """
    p_data = all_planets[planet_name]
    p_lon = p_data["lon"]
    p_speed = p_data["speed"]
    sign_idx = p_data["sign_idx"]
    deg_in_sign = p_data["deg_in_sign"]
    house_num = p_data["whole_sign_house"]

    score = 40.0
    breakdown = {
        "essential": 0.0,
        "accidental": 0.0,
        "planets_aspects": 0.0,
        "asteroids_stars": 0.0
    }
    reasons: List[str] = ["نقطة الأساس: 40.0"]
    structured_aspects: List[Dict[str, str]] = []
    has_any_essential_dignity = False

    # أ) الكرامات الذاتية الخمس (Essential Dignities)
    # 1. البيت (Domicile)
    if SIGN_RULERS.get(sign_idx) == planet_name:
        score += 12.0
        breakdown["essential"] += 12.0
        has_any_essential_dignity = True
        reasons.append("في بيته (Domicile) [+12.0]")

    # 2. الشرف (Exaltation)
    exalt_info = EXALTATIONS.get(planet_name)
    if exalt_info and exalt_info[0] == sign_idx:
        score += 15.0
        breakdown["essential"] += 15.0
        has_any_essential_dignity = True
        reasons.append("في شرفه (Exaltation) [+15.0]")
        if abs(deg_in_sign - exalt_info[1]) <= 1.5:
            score += 3.0
            breakdown["essential"] += 3.0
            reasons.append("في درجة الشرف الدقيقة [+3.0]")

    # 3. المثلثة (Triplicity)
    element_idx = sign_idx % 4
    day_ruler, night_ruler, part_ruler = TRIPLICITY_RULERS[element_idx]
    primary_trip = day_ruler if is_day_chart else night_ruler
    if planet_name == primary_trip:
        score += 7.0
        breakdown["essential"] += 7.0
        has_any_essential_dignity = True
        reasons.append("رب المثلثة الأساسي [+7.0]")
    elif planet_name == part_ruler:
        score += 4.0
        breakdown["essential"] += 4.0
        has_any_essential_dignity = True
        reasons.append("شريك المثلثة [+4.0]")

    # 4. الحد المصري (Egyptian Term / Bound)
    if get_term_ruler(sign_idx, deg_in_sign) == planet_name:
        score += 5.0
        breakdown["essential"] += 5.0
        has_any_essential_dignity = True
        reasons.append("في حده المصري (Term) [+5.0]")

    # 5. الوجه / العشرية (Face / Decan)
    if get_face_ruler(sign_idx, deg_in_sign) == planet_name:
        score += 3.0
        breakdown["essential"] += 3.0
        has_any_essential_dignity = True
        reasons.append("في وجهه (Face/Decan) [+3.0]")

    # ب) الانتكاسات الذاتية (Debilities) والغربة (Peregrine)
    is_detriment = sign_idx in DETRIMENTS.get(planet_name, [])
    is_fall = (FALLS.get(planet_name) == sign_idx)

    if is_detriment and is_fall:
        score -= 18.0
        breakdown["essential"] -= 18.0
        reasons.append("في وباله وهبوطه معاً [-18.0]")
    else:
        if is_detriment:
            score -= 12.0
            breakdown["essential"] -= 12.0
            reasons.append("في وباله (Detriment) [-12.0]")
        if is_fall:
            score -= 15.0
            breakdown["essential"] -= 15.0
            reasons.append("في هبوطه (Fall) [-15.0]")

    if not has_any_essential_dignity and not is_detriment and not is_fall:
        score -= 5.0
        breakdown["essential"] -= 5.0
        reasons.append("غريب بلا حظ ذاتي (Peregrine) [-5.0]")

    # ج) التبادل بالربوبية (Mutual Reception) مع الكواكب الأخرى
    host_ruler = SIGN_RULERS.get(sign_idx)
    if host_ruler and host_ruler != planet_name and host_ruler in all_planets:
        host_sign = all_planets[host_ruler]["sign_idx"]
        if SIGN_RULERS.get(host_sign) == planet_name:
            score += 10.0
            breakdown["essential"] += 10.0
            reasons.append(f"تبادل كامل بالبيت مع {ALL_PLANETS_AR[host_ruler]} [+10.0]")
        elif EXALTATIONS.get(planet_name) and EXALTATIONS[planet_name][0] == host_sign:
            score += 7.0
            breakdown["essential"] += 7.0
            reasons.append(f"تبادل مختلط (بيت/شرف) مع {ALL_PLANETS_AR[host_ruler]} [+7.0]")

    # د) الكرامات العرضية: البيوت، السرعة، التراجع، الموقف من الشمس، الحيّز
    if has_birth_time:
        if house_num in [1, 10]:
            score += 10.0
            breakdown["accidental"] += 10.0
            reasons.append(f"في وتد رئيسي (البيت {house_num}) [+10.0]")
        elif house_num in [4, 7]:
            score += 8.0
            breakdown["accidental"] += 8.0
            reasons.append(f"في وتد (البيت {house_num}) [+8.0]")
        elif house_num in [5, 11]:
            score += 6.0
            breakdown["accidental"] += 6.0
            reasons.append(f"في بيت سعيد (البيت {house_num}) [+6.0]")
        elif house_num in [2, 9]:
            score += 4.0
            breakdown["accidental"] += 4.0
            reasons.append(f"في بيت داعم (البيت {house_num}) [+4.0]")
        elif house_num == 3:
            score += 1.0
            breakdown["accidental"] += 1.0
            reasons.append("في البيت 3 (فرح القمر) [+1.0]")
        elif house_num in [6, 8, 12]:
            score -= 7.0
            breakdown["accidental"] -= 7.0
            reasons.append(f"في بيت ساقط نحيس (البيت {house_num}) [-7.0]")

    avg_spd = AVERAGE_DAILY_SPEEDS[planet_name]
    if planet_name not in ["Sun", "Moon"]:
        if p_speed < 0:
            score -= 8.0
            breakdown["accidental"] -= 8.0
            reasons.append(f"متراجع (Retrograde: {p_speed:.2f}°/يوم) [-8.0]")
        elif abs(p_speed) < 0.08:
            score -= 4.0
            breakdown["accidental"] -= 4.0
            reasons.append("متوقف (Stationary) [-4.0]")
        else:
            if p_speed > avg_spd * 1.15:
                score += 4.0
                breakdown["accidental"] += 4.0
                reasons.append("سريع الحركة فوق المعدل [+4.0]")
            elif p_speed < avg_spd * 0.65:
                score -= 3.0
                breakdown["accidental"] -= 3.0
                reasons.append("بطيء الحركة [-3.0]")
            else:
                score += 2.0
                breakdown["accidental"] += 2.0
                reasons.append("مستقيم الحركة المعتدلة [+2.0]")
    else:
        if p_speed > avg_spd * 1.05:
            score += 3.0
            breakdown["accidental"] += 3.0
            reasons.append("سريع السير [+3.0]")
        elif p_speed < avg_spd * 0.92:
            score -= 2.0
            breakdown["accidental"] -= 2.0
            reasons.append("بطيء السير [-2.0]")

    if planet_name != "Sun":
        sun_dist = angular_diff(p_lon, all_planets["Sun"]["lon"])
        if sun_dist <= 0.2833:
            score += 12.0
            breakdown["accidental"] += 12.0
            reasons.append("في صميم الشمس (Cazimi) [+12.0]")
        elif sun_dist <= 8.5:
            combust_pen = -5.0 if (SIGN_RULERS.get(sign_idx) == planet_name or (exalt_info and exalt_info[0] == sign_idx)) else -10.0
            score += combust_pen
            breakdown["accidental"] += combust_pen
            reasons.append(f"محترق بالشمس ({sun_dist:.1f}°) [{combust_pen}]")
        elif sun_dist <= 17.0:
            score -= 5.0
            breakdown["accidental"] -= 5.0
            reasons.append(f"تحت شعاع الشمس ({sun_dist:.1f}°) [-5.0]")
        else:
            score += 2.0
            breakdown["accidental"] += 2.0
            reasons.append("بريء من الاحتراق (حُر من الشعاع) [+2.0]")

    diurnal_planets = ["Sun", "Jupiter", "Saturn"]
    nocturnal_planets = ["Moon", "Venus", "Mars"]
    if (is_day_chart and planet_name in diurnal_planets) or (not is_day_chart and planet_name in nocturnal_planets):
        score += 3.0
        breakdown["accidental"] += 3.0
        reasons.append("موافق للحيّز (نهاري/ليلي) [+3.0]")

    # هـ) اتصالات الكواكب العشرة (Planets Aspects)
    benefics = ["Jupiter", "Venus"]
    malefics = ["Saturn", "Mars"]
    outers_hard = ["Uranus", "Neptune", "Pluto"]

    for other_p, other_info in all_planets.items():
        if other_p == planet_name:
            continue
        asp_res = get_aspect_details(p_lon, other_info["lon"])
        if not asp_res:
            continue

        asp_name, orb, prec = asp_res
        other_ar = ALL_PLANETS_AR[other_p]
        delta = 0.0

        if asp_name in ["تثليث (120°)", "تسديس (60°)"]:
            base_w = 5.5 if other_p in benefics else (4.0 if other_p in ["Sun", "Moon", "Mercury"] else 3.0)
            delta = round(base_w * prec, 1)
        elif asp_name == "اقتران (0°)":
            if other_p in benefics:
                delta = round(6.5 * prec, 1)
            elif other_p in malefics:
                delta = round(-6.5 * prec, 1)
            elif other_p in outers_hard:
                delta = round(-4.5 * prec, 1)
            else:
                delta = round(4.0 * prec, 1)
        elif asp_name in ["تربيع (90°)", "مقابلة (180°)"]:
            if other_p in malefics:
                delta = round(-6.5 * prec, 1)
            elif other_p in outers_hard:
                delta = round(-5.0 * prec, 1)
            elif other_p in benefics:
                delta = round(-2.0 * prec, 1)
            else:
                delta = round(-3.5 * prec, 1)

        if delta != 0.0:
            score += delta
            breakdown["planets_aspects"] += delta
            sign_str = "+" if delta > 0 else ""
            reasons.append(f"{asp_name} مع {other_ar} (أورب {orb:.1f}°) [{sign_str}{delta}]")
            structured_aspects.append({
                "target": other_ar,
                "type": asp_name,
                "orb": f"{orb:.1f}°",
                "score": f"{sign_str}{delta}"
            })

    # و) اتصالات الكويكبات الخمسة (Asteroids & Chiron)
    for ast_name, ast_info in asteroids.items():
        dist = angular_diff(p_lon, ast_info["lon"])
        ast_ar = ASTEROIDS_AR[ast_name]
        delta = 0.0
        if dist <= 3.0:
            if ast_name in ["Juno", "Ceres", "Vesta", "Pallas"]:
                delta = 2.5
                reasons.append(f"اقتران مع كويكب {ast_ar} [+2.5]")
                structured_aspects.append({"target": f"كويكب {ast_ar}", "type": "اقتران (0°)", "orb": f"{dist:.1f}°", "score": "+2.5"})
            elif ast_name == "Chiron":
                delta = -2.5
                reasons.append(f"اقتران مع {ast_ar} [-2.5]")
                structured_aspects.append({"target": f"كويكب {ast_ar}", "type": "اقتران (0°)", "orb": f"{dist:.1f}°", "score": "-2.5"})
        elif abs(dist - 120.0) <= 2.5 or abs(dist - 60.0) <= 2.5:
            delta = 1.5
            reasons.append(f"اتصال سعيد مع {ast_ar} [+1.5]")
            structured_aspects.append({"target": f"كويكب {ast_ar}", "type": "اتصال متناغم", "orb": f"{abs(dist-120):.1f}°", "score": "+1.5"})
        elif abs(dist - 90.0) <= 2.5 or abs(dist - 180.0) <= 2.5:
            delta = -1.5
            reasons.append(f"اتصال ضاغط مع {ast_ar} [-1.5]")
            structured_aspects.append({"target": f"كويكب {ast_ar}", "type": "اتصال ضاغط", "orb": f"{abs(dist-90):.1f}°", "score": "-1.5"})

        if delta != 0.0:
            breakdown["asteroids_stars"] += delta

    # ز) اتصالات النجوم الثابتة الكبرى
    for star in fixed_stars:
        dist = angular_diff(p_lon, star["lon"])
        if dist <= 1.5:
            w = star["weight"]
            score += w
            breakdown["asteroids_stars"] += w
            sign_str = "+" if w > 0 else ""
            reasons.append(f"اقتران بالنجم الثابت {star['name_ar']} ({star['desc']}) [{sign_str}{w}]")
            structured_aspects.append({"target": f"النجم الثابت {star['name_ar']}", "type": "اقتران (0°)", "orb": f"{dist:.1f}°", "score": f"{sign_str}{w}"})
        elif abs(dist - 180.0) <= 1.2 and star["weight"] < 0:
            w = round(star["weight"] * 0.6, 1)
            score += w
            breakdown["asteroids_stars"] += w
            reasons.append(f"مقابلة النجم الثابت {star['name_ar']} [{w}]")
            structured_aspects.append({"target": f"النجم الثابت {star['name_ar']}", "type": "مقابلة (180°)", "orb": f"{abs(dist-180):.1f}°", "score": f"{w}"})

    final_score = round(min(100.0, score), 1)
    return final_score, reasons, breakdown, structured_aspects

def get_strength_classification(score: float) -> Tuple[str, str, str]:
    """تصنيف قوة الكوكب حسب المقياس المئوي المعتمد."""
    if score > 60.0:
        return "قوي", "🟢", "strong"
    elif 50.0 <= score <= 60.0:
        return "متوسط القوى", "🟡", "moderate"
    else:
        return "ضعيف", "🔴", "weak"

# =============================================================================
# 6. دالة العلاجات الفلكية المتقدمة وفق مراجع التنجيم الغربي
# =============================================================================
def get_advanced_recommendations(
    gender: str,
    venus_sc: float,
    moon_sc: float,
    sun_sc: float,
    mars_sc: float,
    fem_power: float,
    masc_power: float
) -> List[str]:
    recommendations = []
    
    is_venus_strong = venus_sc > 60.0
    is_moon_strong = moon_sc > 60.0
    is_sun_strong = sun_sc > 60.0
    is_mars_strong = mars_sc > 60.0
    
    if gender == "أنثى":
        if is_venus_strong and is_moon_strong and (fem_power > masc_power):
            recommendations.append("✨ **حالة متوازنة وممتازة:** لا تحتاجين إلى نصائح إضافية، فطاقة الأنوثة والقمر والزهرة تجاوزت 60 نقطة وهي في أعلى مستويات التناغم الداخلي والخارجي وفقاً لدلائل التنجيم الحديث.")
        else:
            if is_venus_strong and not is_moon_strong:
                recommendations.append("🏡 **دعم الجانب المنزلي والعاطفي (تقوية كوكب القمر فلكياً):**")
                recommendations.append("جلب مربية أو مساعدة كفوءة لتنظيم التدبير المنزلي ورعاية الشؤون اليومية.")
                recommendations.append("قراءة كتب تعليم الطبخ، فن التدبير المنزلي، وكيفية الاعتناء بالأطفال وتربيتهم التربية الواعية.")
                recommendations.append("🌙 **فلكياً - تقوية طاقة القمر (وفق مراجع التنجيم الغربي الحديث وعلم الأعشاب الطبية):**")
                recommendations.append("**دلائل القمر:** الارتباط بالطبيعة الدورية، الهدوء الداخلي، العناية بالبيئة المنزلية، والاتصال العاطفي العميق بالماء والحدائق.")
                recommendations.append("**الأعشاب:** البابونج الألماني، زهرة الآلام (Passionflower)، والمليسا (تُشرب على شكل منقوع فاتر مساءً للاسترخاء العاطفي).")
                recommendations.append("**الأطعمة:** الخضروات الورقية ذات الأوراق العريضة، الأغذية الغنية بالسوائل الطبيعية، منتجات الألبان الطازجة، والقرع.")
                recommendations.append("**المشروبات:** الماء النقي المفوّر، الحليب النباتي أو الحيواني الدافئ مع قليل من العسل الطبيعي.")
            
            if not is_venus_strong and is_moon_strong:
                recommendations.append("💖 **دعم جانب الثقافة الزوجية والعلاقة (تقوية كوكب الزهرة فلكياً):**")
                recommendations.append("زيادة قراءة كتب الثقافة الزوجية، فن الحوار مع الشريك، وأسس بناء العلاقات العاطفية الناجحة.")
                recommendations.append("🌹 **فلكياً - تقوية طاقة الزهرة (وفق مراجع التنجيم الغربي الحديث):**")
                recommendations.append("**دلائل الزهرة:** الجمال الحسي، الانسجام والتوافق، العناية بالمظهر الراقي، وتنسيق البيئة المحيطة بالألوان الهادئة والعطور الزكية.")
                recommendations.append("**الأعشاب:** بتلات الورد المحمدي، الفانيليا الطبيعية، واللافندر (تُستعمل كشراب لطيف أو عطور منزلية مهدئة).")
                recommendations.append("**الأطعمة:** الفواكه الطازجة ذات الطابع الحلو والمغذي (التوت البري، الفراولة، التين، والرمان)، الشوكولاتة الداكنة النقية.")
                recommendations.append("**المشروبات:** شاي بتلات الورد الفاتر، العصائر الطبيعية المنسقة بعناية.")
            
            if (not is_venus_strong and not is_moon_strong) or (fem_power <= masc_power):
                recommendations.append("🛠️ **برنامج متكامل لتعزيز مهارات الزواج والتدبير (تقوية الزهرة والقمر معاً):**")
                recommendations.append("قراءة كتب الثقافة الزوجية وبناء الألفة والتفاهم المستدام.")
                recommendations.append("جلب مربية أو مساعدة للتدبير المنزلي وتنظيم شؤون الأسرة.")
                recommendations.append("قراءة كتب تعليم الطبخ، التدبير المنزلي، وأصول تربية الأطفال الحديثة.")
                recommendations.append("🌸 **فلكياً - تقوية طاقة الزهرة والقمر:**")
                recommendations.append("**دلائل الزهرة:** الجمال الحسي، الانسجام والتوافق، العناية بالمظهر الراقي، وتنسيق البيئة المحيطة بالألوان الهادئة والعطور الزكية.")
                recommendations.append("**دلائل القمر:** الارتباط بالطبيعة الدورية، الهدوء الداخلي، العناية بالبيئة المنزلية، والاتصال العاطفي العميق بالماء والحدائق.")
                recommendations.append("**الأعشاب:** دمج البابونج (للقمر) مع بتلات الورد (للزهرة) في منقوع مسائي مهدئ.")
                recommendations.append("**الأطعمة والمشروبات:** التركيز على الأغذية الطازجة المتوازنة، شرب السوائل بانتظام، والاهتمام بالجانب الجمالي للوجبات الغذائية.")

    else:  # ذكر
        if (masc_power > fem_power) and is_sun_strong and is_mars_strong:
            recommendations.append("👑 **حالة ذكورية قيادية متوازنة:** لا تحتاج إلى نصائح إضافية، فطاقة الشمس والمريخ تتجاوز 60 نقطة وتدعمك بكفاءة عالية للقيادة وتحمل المسؤولية والإنجاب.")
        else:
            if is_sun_strong and not is_mars_strong:
                recommendations.append("🛠️ **دعم الجانب البدني والمهاري المنزلي (تقوية كوكب المريخ فلكياً):**")
                recommendations.append("التعاقد مع شركة صيانة منزلية دورية أو التسجيل في دورات متخصصة في أعمال الصيانة اليدوية والمنزلية.")
                recommendations.append("الاهتمام بالتمارين الرياضية المنتظمة، اللياقة البدنية، والصحة الإنجابية والجسدية.")
                recommendations.append("🔥 **فلكياً - تقوية طاقة المريخ (وفق مراجع التنجيم الغربي الحديث):**")
                recommendations.append("**دلائل المريخ:** الحركة الجسدية الواعية، النشاط الرياضي، الحيوية الحركية، والشجاعة في مواجهة التحديات العملية.")
                recommendations.append("**الأعشاب:** جذور الزنجبيل الطازج، القرفة، والزعتر البري (تُشرب كمغلي دافئ لتحفيز الدورة الدموية وطاقة الحركة).")
                recommendations.append("**الأطعمة:** اللحوم الحمراء الصحية، البروتينات عالية الجودة، التوابل الدافئة المعتدلة (الفلفل الأسود، الثوم)، والمكسرات الغنية بالطاقة.")
                recommendations.append("**المشروبات:** شاي الزنجبيل بالقرفة، المشروبات الدافئة المنشطة للطاقة الجسدية.")
            
            if not is_sun_strong and is_mars_strong:
                recommendations.append("👔 **دعم الجانب القيادي والإداري الأسري (تقوية كوكب الشمس فلكياً):**")
                recommendations.append("حضور دورات تدريبية متخصصة في تقوية الشخصية، الإدارة الاستراتيجية، والقيادة الأسرية الفعالة.")
                recommendations.append("☀️ **فلكياً - تقوية طاقة الشمس (وفق مراجع التنجيم الغربي الحديث):**")
                recommendations.append("**دلائل الشمس:** الحيوية المركزية، الوضوح الإداري، الثقة العالية بالنفس، والتعرض المعتدل لأشعة الشمس الصباحية لبناء الطاقة الحيوية.")
                recommendations.append("**الأعشاب:** إكليل الجبل (الروزماري)، عشبة الليمون (Lemongrass)، والبابونج الإيجابي.")
                recommendations.append("**الأطعمة:** الحمضيات الطازجة الغنية بفيتامين سي (البرتقال، الليمون، الجريب فروت)، الحبوب الكاملة، والعسل الطبيعي النقي.")
                recommendations.append("**المشروبات:** ماء دافئ مع قطرات الليمون الطازج صباحاً، شاي إكليل الجبل المنعش.")
            
            if (not is_sun_strong and not is_mars_strong) or (masc_power <= fem_power):
                recommendations.append("🚀 **برنامج مكثف لتطوير المهارات الشخصية والقيادية والمنزلية (تقوية الشمس والمريخ معاً):**")
                recommendations.append("الانتظام في التمارين الرياضية وبناء اللياقة البدنية بانتظام.")
                recommendations.append("حضور دورات متخصصة في تطوير الذات، تقوية الشخصية، والثقة بالنفس.")
                recommendations.append("حضور دورات تدريبية في الصيانة المنزلية وإدارة شؤون البيت الأساسية.")
                recommendations.append("⚡ **فلكياً - تقوية طاقة المريخ والشمس:**")
                recommendations.append("**دلائل المريخ:** الحركة الجسدية الواعية، النشاط الرياضي، الحيوية الحركية، والشجاعة في مواجهة التحديات العملية.")
                recommendations.append("**دلائل الشمس:** الحيوية المركزية، الوضوح الإداري، الثقة العالية بالنفس، والتعرض المعتدل لأشعة الشمس الصباحية لبناء الطاقة الحيوية.")
                recommendations.append("**الأعشاب والمشروبات:** شاي الزنجبيل والقرفة صباحاً (للمريخ) مع شاي إكليل الجبل والليمون عصراً (للشمس).")
                recommendations.append("**الأطعمة:** الأغذية الغنية بالبروتين، الخضروات الجذرية الطازجة، الحمضيات، والعسل الطبيعي.")

    return recommendations

# =============================================================================
# 7. دالة الحساب الفلكي الشاملة للشريك (خريطة الميلاد، القوى، والقطبية)
# =============================================================================
def calculate_partner_chart(birth_date: date, birth_time_input, city: City | None, gender: str = "ذكر"):
    """
    حساب الخريطة الفلكية للشريك مع تقييم القوى المئوية وتحديد طاقة الذكورة والأنوثة.
    """
    is_unknown_time = (birth_time_input == "الساعة غير معروفة")
    if is_unknown_time:
        actual_time = time(12, 0)
    elif isinstance(birth_time_input, str):
        h, m = map(int, birth_time_input.split(":"))
        actual_time = time(h, m)
    else:
        actual_time = birth_time_input

    tz_name = get_timezone_for_city(city) if city else "UTC"
    try:
        tz = ZoneInfo(tz_name)
        local_dt = datetime.datetime.combine(birth_date, actual_time, tzinfo=tz)
        utc_dt = local_dt.astimezone(timezone.utc)
    except Exception:
        local_tz = pytz.timezone(tz_name)
        naive_dt = datetime.datetime.combine(birth_date, actual_time)
        localized_dt = local_tz.localize(naive_dt)
        utc_dt = localized_dt.astimezone(pytz.utc)

    decimal_hour = utc_dt.hour + utc_dt.minute / 60.0 + utc_dt.second / 3600.0
    jd_utc = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, decimal_hour)

    lat = city.latitude if city else 33.5138
    lon = city.longitude if city else 36.2765

    # حساب الطالع والبيوت بنظام كل برج بيت (Whole Sign)
    if not is_unknown_time:
        _, ascmc = swe.houses_ex(jd_utc, lat, lon, b'W')
        asc_deg = ascmc[0]
        asc_sign_idx = int(asc_deg // 30) % 12
        house_system_name = "Whole Sign (كل برج بيت بناءً على الطالع الدقيق)"
        asc_label = f"الطالع: {ZODIAC_NAMES_AR[asc_sign_idx]} ({asc_deg % 30:.2f}°)"
    else:
        sun_res, _ = swe.calc_ut(jd_utc, swe.SUN)
        sun_lon = sun_res[0]
        asc_deg = sun_lon
        asc_sign_idx = int(sun_lon // 30) % 12
        house_system_name = "Solar Sign (البيوت الشمسية الافتراضية لعدم دقة الوقت)"
        asc_label = f"طالع شمسي تقديري: {ZODIAC_NAMES_AR[asc_sign_idx]}"

    # مواقع الـ 17 جرماً ونقطة فلكية للتوافقية
    positions = {}
    for p_id, info in PLANETS.items():
        try:
            res, _ = swe.calc_ut(jd_utc, p_id, swe.FLG_SWIEPH | swe.FLG_SPEED)
            p_lon = res[0]
            speed = res[3]
            sign_idx = int(p_lon // 30) % 12
            deg_rem = p_lon % 30
            house_num = ((sign_idx - asc_sign_idx) % 12) + 1

            positions[p_id] = {
                "lon": p_lon,
                "speed": speed,
                "sign_idx": sign_idx,
                "sign_name": ZODIAC_NAMES_AR[sign_idx],
                "deg_rem": deg_rem,
                "house": house_num,
                "is_retro": speed < 0
            }
        except Exception:
            pass

    # تجهيز بيانات الكواكب العشرة والكويكبات والنجوم لمحرك التقييم المئوي
    all_planets_data = {}
    for p_name, p_id in ALL_PLANETS_IDS.items():
        if p_id in positions:
            p_pos = positions[p_id]
            all_planets_data[p_name] = {
                "lon": p_pos["lon"],
                "speed": p_pos["speed"],
                "sign_idx": p_pos["sign_idx"],
                "sign_name": p_pos["sign_name"],
                "deg_in_sign": p_pos["deg_rem"],
                "whole_sign_house": p_pos["house"]
            }

    asteroids_data = {}
    for ast_name, ast_id in ASTEROIDS_IDS.items():
        if ast_id in positions:
            asteroids_data[ast_name] = {"lon": positions[ast_id]["lon"]}

    fixed_stars_data = compute_fixed_stars(jd_utc)

    # تحديد طبيعة الخريطة (نهارية إذا كانت الشمس فوق الأفق في البيوت 7 إلى 12)
    sun_house = all_planets_data["Sun"]["whole_sign_house"]
    is_day_chart = (sun_house in [7, 8, 9, 10, 11, 12]) if not is_unknown_time else True
    sect_label = "خريطة نهارية (Diurnal)" if is_day_chart else "خريطة ليلية (Nocturnal)"

    # حساب قوى الكواكب الشخصية الخمسة من 100 نقطة
    scores: Dict[str, float] = {}
    reasons: Dict[str, List[str]] = {}
    breakdowns: Dict[str, Dict[str, float]] = {}
    structured_aspects_all: Dict[str, List[Dict[str, str]]] = {}

    for p_name in PERSONAL_PLANETS:
        sc, r_list, b_dict, struct_asp = evaluate_planet_100_scale(
            planet_name=p_name,
            all_planets=all_planets_data,
            asteroids=asteroids_data,
            fixed_stars=fixed_stars_data,
            is_day_chart=is_day_chart,
            has_birth_time=not is_unknown_time
        )
        scores[p_name] = sc
        reasons[p_name] = r_list
        breakdowns[p_name] = b_dict
        structured_aspects_all[p_name] = struct_asp

    # ميزان القوى الطاقية: الأنوثة والذكورة
    fem_power = round(scores["Venus"] + scores["Moon"], 1)
    masc_power = round(scores["Sun"] + scores["Mars"], 1)

    # تحديد هوية الهالة الطاقية (Aura Energy) وفق قاعدة التنجيم الغربي الصارمة
    if masc_power > fem_power:
        energy_type = "طاقة ذكورة"
        energy_badge = "⚡ طاقة ذكورة غالبة"
        energy_desc = f"طاقة ذكورة غالبة (مجموع الشمس والمريخ {masc_power:.1f} > مجموع الزهرة والقمر {fem_power:.1f})"
    elif fem_power > masc_power:
        energy_type = "طاقة أنوثة"
        energy_badge = "🌸 طاقة أنوثة غالبة"
        energy_desc = f"طاقة أنوثة غالبة (مجموع الزهرة والقمر {fem_power:.1f} > مجموع الشمس والمريخ {masc_power:.1f})"
    else:
        energy_type = "طاقة متوازنة"
        energy_badge = "⚖️ طاقة متعادلة"
        energy_desc = f"طاقة متوازنة تماماً (الأنوثة {fem_power:.1f} = الذكورة {masc_power:.1f})"

    recommendations = get_advanced_recommendations(
        gender, scores["Venus"], scores["Moon"], scores["Sun"], scores["Mars"], fem_power, masc_power
    )

    return {
        "jd": jd_utc,
        "utc_dt": utc_dt,
        "asc_deg": asc_deg,
        "asc_sign_idx": asc_sign_idx,
        "asc_sign_name": ZODIAC_NAMES_AR[asc_sign_idx],
        "asc_label": asc_label,
        "house_system": house_system_name,
        "has_birth_time": not is_unknown_time,
        "is_day_chart": is_day_chart,
        "sect_label": sect_label,
        "positions": positions,
        "all_planets_data": all_planets_data,
        "asteroids_data": asteroids_data,
        "fixed_stars_data": fixed_stars_data,
        "scores": scores,
        "reasons": reasons,
        "breakdowns": breakdowns,
        "structured_aspects": structured_aspects_all,
        "fem_power": fem_power,
        "masc_power": masc_power,
        "energy_type": energy_type,
        "energy_badge": energy_badge,
        "energy_desc": energy_desc,
        "recommendations": recommendations,
        "tz_name": tz_name
    }

# =============================================================================
# 8. مولد التقرير التنفيذي للطباعة (HTML Print-Ready Report)
# =============================================================================
def generate_combined_html_report(
    name1: str, gender1: str, dob1: date, t1_select: str, city1_name: str, chart1: Dict[str, Any],
    name2: str, gender2: str, dob2: date, t2_select: str, city2_name: str, chart2: Dict[str, Any],
    synastry_res: Dict[str, Any]
) -> str:
    """توليد ملف HTML متكامل وجاهز للطباعة والـ PDF يحتوي التحليل التوافقي وميزان الطاقة والكرامات."""
    def build_planets_table(p_name_owner: str, chart_data: Dict[str, Any]) -> str:
        rows = ""
        for p_name in PERSONAL_PLANETS:
            p_info = chart_data["all_planets_data"][p_name]
            sc = chart_data["scores"][p_name]
            lbl, icon, status_cls = get_strength_classification(sc)
            reasons_html = "".join([f"<span class='tag'>{r}</span>" for r in chart_data["reasons"][p_name]])
            badge_style = (
                "background:#dcfce7; color:#166534; border:1px solid #86efac;" if status_cls == "strong"
                else ("background:#fef9c3; color:#854d0e; border:1px solid #fde047;" if status_cls == "moderate"
                      else "background:#fee2e2; color:#991b1b; border:1px solid #fca5a5;")
            )
            retro_badge = " <span style='color:#dc2626; font-weight:bold;'>(R متراجع)</span>" if p_info["speed"] < 0 else ""
            rows += f"""
            <tr>
                <td style="font-weight:800; font-size:14px;">{ALL_PLANETS_AR[p_name]}{retro_badge}</td>
                <td>{p_info['sign_name']} ({p_info['deg_in_sign']:.2f}°)</td>
                <td style="text-align:center;">البيت {p_info['whole_sign_house']}</td>
                <td style="text-align:center; font-weight:900; font-size:15px;">{sc:.1f} / 100</td>
                <td style="text-align:center;">
                    <span style="padding:4px 10px; border-radius:15px; font-weight:700; font-size:11.5px; display:inline-block; {badge_style}">
                        {icon} {lbl}
                    </span>
                </td>
                <td style="font-size:11px; color:#334155; line-height:1.6;">{reasons_html}</td>
            </tr>
            """
        return f"""
        <table style="width:100%; border-collapse:collapse; margin-bottom:15px;">
            <thead>
                <tr style="background:#0f172a; color:#ffffff;">
                    <th style="padding:8px 10px; text-align:right;">الكوكب ({p_name_owner})</th>
                    <th style="padding:8px 10px; text-align:right;">البرج والدرجة</th>
                    <th style="padding:8px 10px; text-align:center;">البيت</th>
                    <th style="padding:8px 10px; text-align:center;">النتيجة</th>
                    <th style="padding:8px 10px; text-align:center;">التصنيف</th>
                    <th style="padding:8px 10px; text-align:right;">أسباب التقييم المئوي</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        """

    p1_table_html = build_planets_table(name1, chart1)
    p2_table_html = build_planets_table(name2, chart2)

    aspects_rows_html = "".join([
        f"<tr><td>{row.get(f'كوكب {name1}', '-')}</td><td>{row.get('برج الطرف الأول', '-')}</td><td><b>{row.get('الاتصال الفلكي', '-')}</b></td><td>{row.get(f'كوكب {name2}', '-')}</td><td>{row.get('برج الطرف الثاني', '-')}</td><td>{row.get('نوع التأثير', '-')}</td></tr>"
        for _, row in synastry_res["df_aspects"].iterrows()
    ])

    overlays_rows_html = "".join([
        f"<tr><td>{row['صاحب الكوكب']}</td><td>{row['الكوكب']}</td><td>{row['يسقط في بيت الشريك']}</td><td>{row['التأثير الفلكي']}</td></tr>"
        for _, row in synastry_res["df_overlays"].iterrows()
    ])

    warnings_html = "".join([f"<li>{w}</li>" for w in synastry_res["warnings"]]) if synastry_res["warnings"] else "<li>لا توجد تحذيرات جوهرية مسجلة.</li>"

    html_content = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>التقرير الفلكي التوافقي المتقدم وميزان القطبية الطاقية - {name1} و {name2}</title>
    <link href="https://fonts.googleapis.com/css2?family=Amiri:wght@700&family=Cairo:wght@400;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        body {{
            font-family: 'Cairo', sans-serif;
            direction: rtl;
            text-align: right;
            background: #f1f5f9;
            color: #0f172a;
            padding: 25px;
            margin: 0;
            font-size: 13.5px;
            line-height: 1.7;
        }}
        .container {{
            max-width: 1150px;
            margin: 0 auto;
            background: #ffffff;
            padding: 35px;
            border-radius: 14px;
            border: 1px solid #cbd5e1;
            box-shadow: 0 6px 25px rgba(0,0,0,0.07);
        }}
        .header {{
            text-align: center;
            background: linear-gradient(135deg, #090d16 0%, #172554 100%);
            color: #f8fafc;
            padding: 25px;
            border-radius: 12px;
            border: 2px solid #d4af37;
            margin-bottom: 25px;
        }}
        .header h1 {{
            font-family: 'Amiri', serif;
            color: #facc15;
            font-size: 28px;
            margin: 0 0 6px 0;
        }}
        .section-title {{
            font-size: 17px;
            font-weight: 800;
            color: #0f172a;
            border-bottom: 2px solid #d4af37;
            padding-bottom: 6px;
            margin: 24px 0 14px 0;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }}
        .info-box {{
            background: #f8fafc;
            padding: 14px 18px;
            border-radius: 10px;
            border-right: 5px solid #2563eb;
            border: 1px solid #e2e8f0;
        }}
        .polarity-banner {{
            border-right: 6px solid {synastry_res['polarity_border_color']};
            background-color: {synastry_res['polarity_bg_color']};
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            border-top: 1px solid #e2e8f0;
            border-bottom: 1px solid #e2e8f0;
            border-left: 1px solid #e2e8f0;
        }}
        .polarity-banner h3 {{
            color: {synastry_res['polarity_title_color']};
            margin-top: 0;
            margin-bottom: 8px;
            font-size: 18px;
        }}
        .power-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 18px;
        }}
        .power-card {{
            background: #fefce8;
            border: 1px solid #fde047;
            border-radius: 10px;
            padding: 14px;
            text-align: center;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
            background: #f8fafc;
            padding: 15px;
            border-radius: 10px;
            border: 1px solid #e2e8f0;
            margin-bottom: 20px;
            text-align: center;
        }}
        .metric-cell {{
            padding: 10px;
            background: #ffffff;
            border-radius: 8px;
            border: 1px solid #cbd5e1;
        }}
        .metric-cell b {{
            display: block;
            font-size: 14px;
            color: #1e3a8a;
        }}
        .metric-cell span {{
            font-size: 20px;
            font-weight: 900;
            color: #0f172a;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }}
        th {{
            background: #0f172a;
            color: #ffffff;
            padding: 10px 12px;
            text-align: right;
            font-weight: 700;
            font-size: 13px;
        }}
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #e2e8f0;
            vertical-align: top;
        }}
        .tag {{
            display: inline-block;
            background: #f1f5f9;
            border: 1px solid #cbd5e1;
            border-radius: 5px;
            padding: 2px 6px;
            margin: 2px;
            font-size: 11px;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 15px;
            border-top: 1px solid #cbd5e1;
            color: #64748b;
            font-size: 12px;
        }}
        @media print {{
            body {{ background: #ffffff; padding: 0; }}
            .container {{ box-shadow: none; border: none; padding: 10px; max-width: 100%; }}
            .no-print {{ display: none; }}
        }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>التقرير الفلكي التوافقي المتقدم وميزان القطبية الطاقية (Aura & Synastry)</h1>
        <p>تحليل تكامل طاقات الذكورة والأنوثة — قوى الكواكب المئوية (100 نقطة) — الكويكبات والمسؤوليات</p>
    </div>

    <div class="section-title">بيانات الشريكين الفلكية</div>
    <div class="info-grid">
        <div class="info-box">
            <h4 style="margin:0 0 6px 0; color:#1e3a8a;">👤 الطرف الأول: {name1} ({gender1})</h4>
            <div>تاريخ الميلاد: <b>{dob1} ({t1_select})</b> | المدينة: <b>{city1_name}</b></div>
            <div>الطالع: <b>{chart1['asc_label']}</b> | الحيّز: <b>{chart1['sect_label']}</b></div>
            <div>ميزان الطاقة: <b>{chart1['energy_badge']}</b> (شمس+مريخ: {chart1['masc_power']:.1f} | زهرة+قمر: {chart1['fem_power']:.1f})</div>
        </div>
        <div class="info-box">
            <h4 style="margin:0 0 6px 0; color:#1e3a8a;">❤️ الطرف الثاني: {name2} ({gender2})</h4>
            <div>تاريخ الميلاد: <b>{dob2} ({t2_select})</b> | المدينة: <b>{city2_name}</b></div>
            <div>الطالع: <b>{chart2['asc_label']}</b> | الحيّز: <b>{chart2['sect_label']}</b></div>
            <div>ميزان الطاقة: <b>{chart2['energy_badge']}</b> (شمس+مريخ: {chart2['masc_power']:.1f} | زهرة+قمر: {chart2['fem_power']:.1f})</div>
        </div>
    </div>

    <div class="section-title">ميزان القطبية الطاقية وقانون التوافق الصارم</div>
    <div class="polarity-banner">
        <h3>{synastry_res['polarity_title']}</h3>
        <p style="font-size:14px; margin:0 0 8px 0; font-weight:700;">{synastry_res['polarity_desc']}</p>
        <p style="margin:0;"><b>القرار التوافقي النهائي:</b> {synastry_res['verdict_text']}</p>
    </div>

    <div class="section-title">تحديد المسؤوليات والأدوار الفلكية</div>
    <div class="info-grid">
        <div class="info-box" style="border-right-color:#16a34a;">
            <div>💰 <b>الشريك الداعم مادياً واقتصادياً:</b> {synastry_res['material_supporter']}</div>
            <div>🏆 <b>المستفيد الأساسي من العلاقة:</b> {synastry_res['beneficiary']}</div>
        </div>
        <div class="info-box" style="border-right-color:#dc2626;">
            <div>⚖️ <b>مصدر الضغط الهيكلي والزحلي:</b> {synastry_res['pressure_source']}</div>
            <div>💔 <b>الطرف الأكثر تضرراً نفسياً:</b> {synastry_res['psych_sufferer']}</div>
            <div>👶 <b>المسؤول عن تعطيل الاستقرار/الأطفال:</b> {synastry_res['children_blocker']}</div>
        </div>
    </div>

    <div class="section-title">المؤشرات التوافقية والنسب المئوية</div>
    <div class="metrics-grid">
        <div class="metric-cell"><b>الراحة النفسية</b><span>{synastry_res['comfort_pct']}%</span></div>
        <div class="metric-cell"><b>الحميمية العاطفية</b><span>{synastry_res['emotional_pct']}%</span></div>
        <div class="metric-cell"><b>نسبة السعادة</b><span>{synastry_res['happiness_pct']}%</span></div>
        <div class="metric-cell"><b>التفاهم العقلي</b><span>{synastry_res['mental_pct']}%</span></div>
        <div class="metric-cell"><b>نسبة الصراعات</b><span>{synastry_res['conflict_pct']}%</span></div>
        <div class="metric-cell"><b>مؤشر الجروح والقيود</b><span>{synastry_res['hurt_pct']}%</span></div>
        <div class="metric-cell" style="grid-column: span 2;"><b>نسبة الاستمرار والدوام</b><span>{synastry_res['continuity_pct']}%</span></div>
    </div>

    <div class="section-title">تقييم الكواكب الشخصية لـ {name1} (مقياس 100 نقطة والكرامات الخمس)</div>
    {p1_table_html}

    <div class="section-title">تقييم الكواكب الشخصية لـ {name2} (مقياس 100 نقطة والكرامات الخمس)</div>
    {p2_table_html}

    <div class="section-title">التنبيهات والتحذيرات الفلكية المشتركة</div>
    <ul style="background:#fffbeb; border:1px solid #fef3c7; border-radius:8px; padding:18px 30px; line-height:1.8;">
        {warnings_html}
    </ul>

    <div class="section-title">تحليل إسقاط البيوت التوافقية (House Overlays)</div>
    <table>
        <thead><tr><th>صاحب الكوكب</th><th>الكوكب/الكويكب</th><th>يسقط في بيت الشريك</th><th>الأثر الفلكي والتحذير</th></tr></thead>
        <tbody>{overlays_rows_html}</tbody>
    </table>

    <div class="section-title">الاتصالات الفلكية المباشرة بين الخريطتين (Synastry Aspects)</div>
    <table>
        <thead><tr><th>كوكب {name1}</th><th>البرج</th><th>الاتصال الفلكي</th><th>كوكب {name2}</th><th>البرج</th><th>نوع التأثير</th></tr></thead>
        <tbody>{aspects_rows_html}</tbody>
    </table>

    <div class="footer">
        <p>تم إعداد هذا التقرير الشامل باستخدام خوارزميات السويِس إيفيميريس (Swiss Ephemeris) الدقيقة وميزان الطاقة الفلكية الغربية.</p>
    </div>

    <div style="text-align: center; margin-top: 30px;" class="no-print">
        <button onclick="window.print()" style="padding: 12px 25px; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; font-weight: bold;">🖨️ طباعة التقرير أو حفظه بصيغة PDF</button>
    </div>
</div>
</body>
</html>
"""
    return html_content

# =============================================================================
# 9. محرك تقييم التوافقية والقطبية الطاقية (Synastry & Polarity Engine)
# =============================================================================
def evaluate_synastry_with_aura(
    name1: str, gender1: str, chart1: Dict[str, Any],
    name2: str, gender2: str, chart2: Dict[str, Any]
) -> Dict[str, Any]:
    """
    الدمج الفلكي الكامل بين تحليل التوافقية وميزان القطبية الطاقية (طاقة الذكورة والأنوثة).
    """
    total_score = 0
    aspect_records = []
    overlay_records = []
    warnings_list = []
    marriage_support_score = 0

    p1_financial_score = 0
    p2_financial_score = 0
    p1_pressure_score = 0
    p2_pressure_score = 0
    p1_positive_hits = 0
    p2_positive_hits = 0

    harmony_hits = 0
    conflict_hits = 0
    emotional_hits = 0
    mental_hits = 0
    hurt_hits = 0

    seen_aspect_pairs = set()

    # 1. حساب الاتصالات الفلكية بين كافة الأجرام الـ 17 في الخريطتين
    for p1_id, p1_info in PLANETS.items():
        if p1_id not in chart1["positions"]:
            continue
        for p2_id, p2_info in PLANETS.items():
            if p2_id not in chart2["positions"]:
                continue

            lon1 = chart1["positions"][p1_id]["lon"]
            lon2 = chart2["positions"][p2_id]["lon"]
            asp, sc = calculate_aspect(lon1, lon2)

            if asp:
                pair_key = tuple(sorted([f"{name1}_{p1_info['name']}", f"{name2}_{p2_info['name']}"]))
                if pair_key not in seen_aspect_pairs:
                    seen_aspect_pairs.add(pair_key)
                    total_score += sc

                    if sc > 0:
                        harmony_hits += 1
                        p1_positive_hits += 1
                        p2_positive_hits += 1
                    else:
                        conflict_hits += 1

                    if p1_id in [swe.SUN, swe.MARS, swe.VENUS, swe.JUNO] and sc > 0:
                        p1_financial_score += sc
                    if p2_id in [swe.SUN, swe.MARS, swe.VENUS, swe.JUNO] and sc > 0:
                        p2_financial_score += sc

                    if p1_id in [swe.SATURN, swe.PLUTO] and sc < 0:
                        p1_pressure_score += abs(sc)
                    if p2_id in [swe.SATURN, swe.PLUTO] and sc < 0:
                        p2_pressure_score += abs(sc)

                    if p1_id in [swe.VENUS, swe.MOON, swe.MARS, swe.CHIRON] or p2_id in [swe.VENUS, swe.MOON, swe.MARS, swe.CHIRON]:
                        if sc > 0:
                            emotional_hits += 1
                        else:
                            hurt_hits += 1

                    if p1_id in [swe.MERCURY, swe.JUPITER, swe.SUN, swe.PALLAS] or p2_id in [swe.MERCURY, swe.JUPITER, swe.SUN, swe.PALLAS]:
                        if sc > 0:
                            mental_hits += 1

                    if p1_id in [swe.SUN, swe.MOON, swe.VENUS, swe.JUNO] and p2_id in [swe.SUN, swe.MOON, swe.VENUS, swe.MARS, swe.JUNO] and sc > 0:
                        marriage_support_score += sc

                    if sc < 0:
                        if p1_id == swe.MARS or p2_id == swe.MARS:
                            warnings_list.append(f"⚠️ صراعات حادة أو طاقة تنافسية بين كوكب ({p1_info['name']} لـ {name1}) و({p2_info['name']} لـ {name2})")
                        elif p1_id == swe.VENUS or p2_id == swe.VENUS:
                            warnings_list.append(f"💔 جرح عاطفي أو إحباط وجداني بين ({p1_info['name']} و {p2_info['name']})")
                        elif p1_id == swe.SATURN or p2_id == swe.SATURN:
                            warnings_list.append(f"⚖️ ضغط زحلي يعيق المرونة بين ({p1_info['name']} و {p2_info['name']})")

                    aspect_records.append({
                        f"كوكب {name1}": p1_info["name"],
                        "برج الطرف الأول": chart1["positions"][p1_id]["sign_name"],
                        "الاتصال الفلكي": asp,
                        f"كوكب {name2}": p2_info["name"],
                        "برج الطرف الثاني": chart2["positions"][p2_id]["sign_name"],
                        "نوع التأثير": "إيجابي (توافق ودعم)" if sc > 0 else "سلبي (تحدي وضغط)",
                    })

    # 2. تحليل إسقاط البيوت التوافقية في كلا الاتجاهين
    for p1_id, p1_info in chart1["positions"].items():
        h_num = p1_info["house"]
        p_name = PLANETS[p1_id]["name"]
        warn, note = analyze_house_overlay(p1_id, p_name, h_num, name2)
        if warn:
            warnings_list.append(warn)
            if p1_id in [swe.SATURN, swe.PLUTO]:
                p1_pressure_score += 4
        overlay_records.append({
            "صاحب الكوكب": name1,
            "الكوكب": p_name,
            "يسقط في بيت الشريك": f"البيت {h_num}",
            "التأثير الفلكي": note
        })

    for p2_id, p2_info in chart2["positions"].items():
        h_num = p2_info["house"]
        p_name = PLANETS[p2_id]["name"]
        warn, note = analyze_house_overlay(p2_id, p_name, h_num, name1)
        if warn:
            warnings_list.append(warn)
            if p2_id in [swe.SATURN, swe.PLUTO]:
                p2_pressure_score += 4
        overlay_records.append({
            "صاحب الكوكب": name2,
            "الكوكب": p_name,
            "يسقط في بيت الشريك": f"البيت {h_num}",
            "التأثير الفلكي": note
        })

    # 3. تحديد المسؤوليات والآثار المالية والنفسية
    total_fin = p1_financial_score + p2_financial_score
    if total_fin > 0:
        p1_fin_pct = int((p1_financial_score / total_fin) * 100)
        p2_fin_pct = int((p2_financial_score / total_fin) * 100)
    else:
        p1_fin_pct, p2_fin_pct = 50, 50

    if p1_financial_score > p2_financial_score:
        material_supporter = f"{name1} (بنسبة مساهمة ودعم فلكي {p1_fin_pct}%)"
    elif p2_financial_score > p1_financial_score:
        material_supporter = f"{name2} (بنسبة مساهمة ودعم فلكي {p2_fin_pct}%)"
    else:
        material_supporter = f"مشترك بالتساوي بين {name1} و {name2} (50% لكل منهما)"

    if p1_pressure_score > p2_pressure_score:
        pressure_source = name1
        psych_sufferer = name2
    elif p2_pressure_score > p1_pressure_score:
        pressure_source = name2
        psych_sufferer = name1
    else:
        pressure_source = f"متبادل بين {name1} و {name2}"
        psych_sufferer = f"متوازن / كلاهما ({name1} و {name2})"

    if total_score >= 12:
        beneficiary = f"{name1} و {name2} (بشكل تبادلي ومتوازن)"
    elif total_score >= 0:
        beneficiary = name1 if p1_positive_hits >= p2_positive_hits else name2
    else:
        beneficiary = "لا يوجد مستفيد حقيقي (علاقة استنزافية متبادلة)"

    if p1_pressure_score > p2_pressure_score + 2:
        children_blocker = f"{name1} (بسبب هيمنة الثقل وزحل في بيوت الاستقرار)"
    elif p2_pressure_score > p1_pressure_score + 2:
        children_blocker = f"{name2} (بسبب هيمنة الثقل وزحل في بيوت الاستقرار)"
    else:
        children_blocker = "لا يوجد معيق فردي مباشر؛ المسؤولية مشتركة أو محايدة بين الطرفين"

    # 4. حساب المؤشرات والنسب المئوية التوافقية
    total_aspects = max(1, (harmony_hits + conflict_hits))
    comfort_pct = int(min(100, max(10, (harmony_hits / total_aspects) * 100 + (total_score * 1.5))))
    emotional_pct = int(min(100, max(10, 50 + (emotional_hits * 5) - (hurt_hits * 6))))
    happiness_pct = int(min(100, max(5, comfort_pct * 0.75 + (marriage_support_score * 1.8))))
    conflict_pct = int(min(100, max(5, (conflict_hits / total_aspects) * 100 + ((p1_pressure_score + p2_pressure_score) * 1.5))))
    hurt_pct = int(min(100, max(5, (hurt_hits / total_aspects) * 100 + ((p1_pressure_score + p2_pressure_score) * 1.2))))
    mental_pct = int(min(100, max(15, (mental_hits / max(1, total_aspects)) * 100 + 25)))
    continuity_pct = int(min(100, max(10, (comfort_pct + emotional_pct - conflict_pct) / 1.15)))

    driver_party = name1 if p1_positive_hits >= p2_positive_hits else name2

    # =========================================================================
    # 5. تطبيق قانون القطبية الطاقية الصارم (Aura Polarity Law)
    # =========================================================================
    # طاقة الذكورة: الشمس والمريخ > الزهرة والقمر
    # طاقة الأنوثة: الزهرة والقمر > الشمس والمريخ
    p1_energy = chart1["energy_type"]
    p2_energy = chart2["energy_type"]

    p1_masc = chart1["masc_power"]
    p1_fem = chart1["fem_power"]
    p2_masc = chart2["masc_power"]
    p2_fem = chart2["fem_power"]

    is_same_masculine = (p1_energy == "طاقة ذكورة" and p2_energy == "طاقة ذكورة")
    is_same_feminine = (p1_energy == "طاقة أنوثة" and p2_energy == "طاقة أنوثة")
    is_complementary = (
        (p1_energy == "طاقة ذكورة" and p2_energy == "طاقة أنوثة") or
        (p1_energy == "طاقة أنوثة" and p2_energy == "طاقة ذكورة")
    )

    verdict_text = ""
    v_color = "green"
    polarity_title = ""
    polarity_desc = ""
    polarity_border_color = "#16a34a"
    polarity_bg_color = "#f0fdf4"
    polarity_title_color = "#166534"
    same_energy_blocked = False

    if is_same_masculine:
        same_energy_blocked = True
        polarity_title = "⛔ عدم توافق قطعي — تصادم طاقة ذكورة مع طاقة ذكورة"
        polarity_desc = (
            f"وفقاً لقانون القطبية الفلكية الصارم في التنجيم الغربي، لا يمكن حدوث توافق أو زواج مستقر بين شخصين يحملان كلاهما طاقة ذكورة "
            f"({name1}: شمس ومريخ {p1_masc:.1f} > زهرة وقمر {p1_fem:.1f} | "
            f"{name2}: شمس ومريخ {p2_masc:.1f} > زهرة وقمر {p2_fem:.1f}). "
            f"هذا التطابق الطاقي يلغي الانجذاب القطبي الفطري ويخلق صراعاً دائماً على القيادة والسيطرة والندية والاستقلالية، "
            f"مما يولد نفوراً واصطداماً مدمراً للعلاقة بغض النظر عن أي اتصالات فلكية إيجابية أخرى."
        )
        verdict_text = f"❌ **عدم توافق قطعي (تنافر ذكوري):** العلاقة محكومة بالصدام والنزاع الدائم على القيادة والسيطرة؛ نظراً لأن الطرفين يحملان طاقة ذكورة غالبة."
        v_color = "red"
        polarity_border_color = "#ef4444"
        polarity_bg_color = "#fef2f2"
        polarity_title_color = "#991b1b"
        continuity_pct = min(continuity_pct, 12)
        conflict_pct = max(conflict_pct, 88)
        happiness_pct = min(happiness_pct, 15)
        warnings_list.insert(0, f"⛔ **تحذير طاقي مصيري:** {name1} و {name2} كلاهما يمتلكان طاقة ذكورة غالبة (الشمس والمريخ أعلى من الزهرة والقمر). قانون القطبية يمنع التوافق الزواجي بين قطبين موجبين.")

    elif is_same_feminine:
        same_energy_blocked = True
        polarity_title = "⛔ عدم توافق قطعي — تنافر طاقة أنوثة مع طاقة أنوثة"
        polarity_desc = (
            f"وفقاً لقانون القطبية الفلكية الصارم في التنجيم الغربي، لا يمكن حدوث توافق أو زواج مستقر بين شخصين يحملان كلاهما طاقة أنوثة "
            f"({name1}: زهرة وقمر {p1_fem:.1f} > شمس ومريخ {p1_masc:.1f} | "
            f"{name2}: زهرة وقمر {p2_fem:.1f} > شمس ومريخ {p2_masc:.1f}). "
            f"هذا التطابق الطاقي يجرد العلاقة من عمود الحسم والمبادرة الخارجية والقدرة على القيادة ومواجهة الأعباء الخشنة، "
            f"ويغرق الطرفين في الحساسية المفرطة والتردد والعاطفية الزائدة والاتكالية المتبادلة دون وجود قطب ذكوري موجه."
        )
        verdict_text = f"❌ **عدم توافق قطعي (تنافر أنثوي):** العلاقة تفتقر تماماً للمبادرة والقيادة والحسم، وتغرق في الحساسية والاتكالية؛ نظراً لأن كليكما يحمل طاقة أنوثة غالبة."
        v_color = "red"
        polarity_border_color = "#ef4444"
        polarity_bg_color = "#fef2f2"
        polarity_title_color = "#991b1b"
        continuity_pct = min(continuity_pct, 15)
        conflict_pct = max(conflict_pct, 70)
        happiness_pct = min(happiness_pct, 20)
        warnings_list.insert(0, f"⛔ **تحذير طاقي مصيري:** {name1} و {name2} كلاهما يمتلكان طاقة أنوثة غالبة (الزهرة والقمر أعلى من الشمس والمريخ). غياب القطبية الذكورية الفاعلة يعيق إقامة زواج متماسك.")

    elif is_complementary:
        masc_partner = name1 if p1_energy == "طاقة ذكورة" else name2
        fem_partner = name2 if p1_energy == "طاقة ذكورة" else name1
        masc_val = p1_masc if p1_energy == "طاقة ذكورة" else p2_masc
        fem_val = p2_fem if p1_energy == "طاقة ذكورة" else p1_fem

        polarity_title = "✨ تكامل قطبي ممتاز — طاقة ذكورة متناغمة مع طاقة أنوثة"
        polarity_desc = (
            f"يتحقق هنا شرط القطبية الفلكية الأساسي بنجاح: "
            f"({masc_partner}) يمثل القطب الذكوري الفاعل الموجه بقوة {masc_val:.1f} نقطة (الشمس والمريخ)، بينما "
            f"({fem_partner}) تمثل القطب الأنثوي المستجيب والمحتضن بقوة {fem_val:.1f} نقطة (الزهرة والقمر). "
            f"هذا التباين الطاقي يولد الانجذاب المغناطيسي الفطري الضروري لتوازن عش الزوجية."
        )
        polarity_border_color = "#16a34a"
        polarity_bg_color = "#f0fdf4"
        polarity_title_color = "#166534"

        # تقييم القرار التوافقي بناءً على الرصيد الفلكي للاتصالات
        if total_score >= 15 and marriage_support_score >= 8:
            verdict_text = f"💍 **علاقة ممتازة وتصلح بامتياز للزواج والاستقرار الدائم:** تكامل طاقي سليم مدعوم باتصالات فلكية متناغمة ورصيد إيجابي مرتفع ({total_score} نقطة)."
            v_color = "green"
        elif total_score >= 6:
            verdict_text = f"🤝 **علاقة جيدة وتصلح للارتباط مع وجود تفاهم وتنازلات واعية:** القطبية متحققة بنجاح مع اتصالات فلكية إيجابية تحتاج إلى التنسيق المستمر للمسؤوليات."
            v_color = "green"
        elif -2 <= total_score < 6:
            verdict_text = f"⚖️ **علاقة متوسطة تتطلب جهداً شاقاً وإدارة حكيمة للخلافات:** القطبية الطاقية موجودة، لكن الاتصالات تشهد بعض الضغوطات والامتحانات المشتركة."
            v_color = "orange"
        else:
            verdict_text = f"❌ **علاقة شديدة الصعوبة (تحذير من الارتباط):** رغم وجود التكامل القطبي الطاقي، إلا أن الاتصالات الفلكية المعاكسة والضغوط الزحلية والبلوتونية تستنزف العلاقة."
            v_color = "red"

    else:
        polarity_title = "⚖️ قطبية حيادية / تعادل طاقي"
        polarity_desc = "أحد الشريكين أو كلاهما يمتلك طاقة متوازنة تماماً بين الأنوثة والذكورة، مما يجعل استقرار العلاقة معتمداً كلياً على قوة الاتصالات الفلكية وتوزيع البيوت."
        polarity_border_color = "#2563eb"
        polarity_bg_color = "#eff6ff"
        polarity_title_color = "#1e40af"

        if total_score >= 12:
            verdict_text = f"💍 **علاقة صالحة للزواج مع تعادل طاقي مرن** مدعومة باتصالات فلكية طيبة ({total_score} نقطة)."
            v_color = "green"
        elif total_score >= 4:
            verdict_text = f"🤝 **علاقة مقبولة تتطلب وضوحاً في توزيع الأدوار الأسرية**."
            v_color = "orange"
        else:
            verdict_text = f"❌ **علاقة غير متوافقة نظراً لضعف الرصيد الفلكي العام**."
            v_color = "red"

    df_aspects = pd.DataFrame(aspect_records) if aspect_records else pd.DataFrame(columns=["ملاحظة"])
    df_overlays = pd.DataFrame(overlay_records) if overlay_records else pd.DataFrame(columns=["ملاحظة"])

    return {
        "total_score": total_score,
        "marriage_support_score": marriage_support_score,
        "comfort_pct": comfort_pct,
        "emotional_pct": emotional_pct,
        "happiness_pct": happiness_pct,
        "conflict_pct": conflict_pct,
        "hurt_pct": hurt_pct,
        "mental_pct": mental_pct,
        "continuity_pct": continuity_pct,
        "material_supporter": material_supporter,
        "pressure_source": pressure_source,
        "psych_sufferer": psych_sufferer,
        "beneficiary": beneficiary,
        "children_blocker": children_blocker,
        "driver_party": driver_party,
        "df_aspects": df_aspects,
        "df_overlays": df_overlays,
        "warnings": list(set(warnings_list)),
        "polarity_title": polarity_title,
        "polarity_desc": polarity_desc,
        "polarity_border_color": polarity_border_color,
        "polarity_bg_color": polarity_bg_color,
        "polarity_title_color": polarity_title_color,
        "verdict_text": verdict_text,
        "v_color": v_color,
        "same_energy_blocked": same_energy_blocked
    }

# =============================================================================
# 10. واجهة المستخدم التفاعلية في Streamlit
# =============================================================================
st.markdown("""
<div class="main-header">
    <h1>🔭 النظام الفلكي التوافقي المطور (شامل قوى الكواكب، الكويكبات، وميزان القطبية الطاقية)</h1>
    <p>تطوير: استرو رادار</p>
</div>
""", unsafe_allow_html=True)

countries = load_countries()
country_options = sorted([(f"{c['name']} ({c['iso']})", c['iso']) for c in countries.values()], key=lambda x: x[0])
country_display = [x[0] for x in country_options]
country_codes = [x[1] for x in country_options]

time_options = ["الساعة غير معروفة"] + [time(h, m).strftime('%H:%M') for h in range(24) for m in range(0, 60, 5)]

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 👤 بيانات الطرف الأول")
    name1 = st.text_input("الاسم أو الرمز:", "أحمد", key="name1")
    gender1 = st.selectbox("الجنس:", ["ذكر", "أنثى"], index=0, key="gen1")
    dob1 = st.date_input("تاريخ الميلاد:", min_value=date(1850, 1, 1), max_value=date(2100, 1, 1), value=date(1990, 1, 1), key="dob1")
    t1_select = st.selectbox("ساعة الميلاد المحلية:", time_options, index=time_options.index("12:00") if "12:00" in time_options else 0, key="t1")
    
    sy_idx = country_codes.index("SY") if "SY" in country_codes else 0
    c1_display = st.selectbox("الدولة:", country_display, index=sy_idx, key="c1_disp")
    c1_code = country_codes[country_display.index(c1_display)]
    c1_cities = get_cities_by_country(c1_code)
    c1_names = [c.name for c in c1_cities]
    c1_name = st.selectbox("المدينة:", c1_names if c1_names else ["غير متوفرة"], key="c1_name")
    city1 = next((c for c in c1_cities if c.name == c1_name), None)

with col2:
    st.markdown("### ❤️ بيانات الطرف الثاني")
    name2 = st.text_input("الاسم أو الرمز:", "سارة", key="name2")
    gender2 = st.selectbox("الجنس:", ["أنثى", "ذكر"], index=0, key="gen2")
    dob2 = st.date_input("تاريخ الميلاد:", min_value=date(1850, 1, 1), max_value=date(2100, 1, 1), value=date(1992, 5, 15), key="dob2")
    t2_select = st.selectbox("ساعة الميلاد المحلية:", time_options, index=time_options.index("12:00") if "12:00" in time_options else 0, key="t2")
    
    ae_idx = country_codes.index("AE") if "AE" in country_codes else 0
    c2_display = st.selectbox("الدولة:", country_display, index=ae_idx, key="c2_disp")
    c2_code = country_codes[country_display.index(c2_display)]
    c2_cities = get_cities_by_country(c2_code)
    c2_names = [c.name for c in c2_cities]
    c2_name = st.selectbox("المدينة:", c2_names if c2_names else ["غير متوفرة"], key="c2_name")
    city2 = next((c for c in c2_cities if c.name == c2_name), None)

st.markdown("---")

submit = st.button("🚀 تشغيل المحرك التوافقي الشامل وتحديد ميزان القوى والقطبية الطاقية", type="primary", use_container_width=True)

if submit:
    with st.spinner("جاري حساب الطوالع الدقيقة، تقييم قوى الكواكب المئوية، وميزان القطبية الطاقية والمسؤوليات..."):
        try:
            chart1 = calculate_partner_chart(dob1, t1_select, city1, gender1)
            chart2 = calculate_partner_chart(dob2, t2_select, city2, gender2)

            synastry_res = evaluate_synastry_with_aura(name1, gender1, chart1, name2, gender2, chart2)

            # =========================================================================
            # عرض النتائج في واجهة Streamlit
            # =========================================================================
            st.markdown("---")
            st.header("📊 التقرير التوافقي الشامل وميزان القطبية الطاقية")

            # 1. بطاقة ميزان القطبية الطاقية
            st.markdown(f"""
            <div class="result-card" style="border-right-color: {synastry_res['polarity_border_color']}; background-color: {synastry_res['polarity_bg_color']};">
                <h3 style="color: {synastry_res['polarity_title_color']}; margin-top: 0;">{synastry_res['polarity_title']}</h3>
                <p style="font-size: 15px; font-weight: 700; line-height: 1.8;">{synastry_res['polarity_desc']}</p>
                <hr style="border: 0; border-top: 1px solid #cbd5e1; margin: 12px 0;">
                <h4 style="margin: 0; color: #0f172a;">🎯 القرار الفلكي النهائي:</h4>
                <div style="font-size: 16px; font-weight: 800; margin-top: 5px;">{synastry_res['verdict_text']}</div>
            </div>
            """, unsafe_allow_html=True)

            # 2. تفصيل موازين الطاقة لكل من الطرفين
            st.subheader("⚖️ ميزان طاقة الذكورة والأنوثة (مجموع الشمس والمريخ مقابل الزهرة والقمر)")
            col_en1, col_en2 = st.columns(2)
            with col_en1:
                st.markdown(f"""
                <div class="polarity-card" style="border-right: 5px solid #2563eb;">
                    <h4>👤 {name1} ({gender1}) — {chart1['energy_badge']}</h4>
                    <p style="font-size:13px; color:#475569;">{chart1['energy_desc']}</p>
                    <div style="display:flex; justify-content:space-between; margin-top:10px;">
                        <div><b>طاقة الذكورة (الشمس + المريخ):</b> <code style="font-size:16px;">{chart1['masc_power']:.1f}</code></div>
                        <div><b>طاقة الأنوثة (الزهرة + القمر):</b> <code style="font-size:16px;">{chart1['fem_power']:.1f}</code></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col_en2:
                st.markdown(f"""
                <div class="polarity-card" style="border-right: 5px solid #db2777;">
                    <h4>❤️ {name2} ({gender2}) — {chart2['energy_badge']}</h4>
                    <p style="font-size:13px; color:#475569;">{chart2['energy_desc']}</p>
                    <div style="display:flex; justify-content:space-between; margin-top:10px;">
                        <div><b>طاقة الذكورة (الشمس + المريخ):</b> <code style="font-size:16px;">{chart2['masc_power']:.1f}</code></div>
                        <div><b>طاقة الأنوثة (الزهرة + القمر):</b> <code style="font-size:16px;">{chart2['fem_power']:.1f}</code></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # 3. الأدوار والمسؤوليات الفلكية
            st.markdown("---")
            st.subheader("👑 المسؤوليات والأدوار في العلاقة")
            c_r1, c_r2 = st.columns(2)
            with c_r1:
                st.markdown(f"- 💰 **الشريك الداعم ماديّاً واقتصادياً:** **{synastry_res['material_supporter']}**")
                st.markdown(f"- 🏆 **المستفيد الأساسي من العلاقة:** **{synastry_res['beneficiary']}**")
                st.markdown(f"- 📍 **طالع {name1}:** {chart1['asc_label']} | **طالع {name2}:** {chart2['asc_label']}")
            with c_r2:
                st.markdown(f"- ⚖️ **مصدر الضغط الهيكلي والزحلي:** **{synastry_res['pressure_source']}**")
                st.markdown(f"- 💔 **الطرف الأكثر تضرراً نفسياً:** **{synastry_res['psych_sufferer']}**")
                st.markdown(f"- 👶 **المسؤول عن تعطيل الاستقرار أو الأطفال:** **{synastry_res['children_blocker']}**")

            # 4. المؤشرات التوافقية والنسب المئوية
            st.markdown("---")
            st.subheader("📈 مؤشرات ونسب التوافق (مع تحديد المحرك والمصدر)")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("الراحة النفسية", f"{synastry_res['comfort_pct']}%", f"الداعم: {synastry_res['driver_party']}")
            m2.metric("الحميمية العاطفية", f"{synastry_res['emotional_pct']}%", "مشترك بين الطرفين")
            m3.metric("نسبة السعادة", f"{synastry_res['happiness_pct']}%", "مرتبطة بالقطبية والاتصالات")
            m4.metric("التفاهم العقلي", f"{synastry_res['mental_pct']}%", f"المحرك: {synastry_res['driver_party']}")

            m5, m6, m7 = st.columns(3)
            m5.metric("نسبة الصراعات", f"{synastry_res['conflict_pct']}%", f"المصدر: {synastry_res['pressure_source']}")
            m6.metric("مؤشر الجروح والقيود", f"{synastry_res['hurt_pct']}%", f"المتأثر: {synastry_res['psych_sufferer']}")
            m7.metric("نسبة الاستمرار والدوام", f"{synastry_res['continuity_pct']}%", "بناءً على ميزان القوى")

            # 5. التنبيهات والتحذيرات
            st.markdown("---")
            st.subheader("⚠️ التنبيهات والتحذيرات الفلكية الهامة")
            if synastry_res["warnings"]:
                for w in synastry_res["warnings"]:
                    st.warning(w)
            else:
                st.success("لم يتم رصد تحذيرات خطيرة أو اتصالات هدامة قوية بين الخريطتين.")

            # 6. تفصيل قوى الكواكب الشخصية (100 نقطة) لكلا الطرفين في Tabs
            st.markdown("---")
            st.subheader("⭐ تقييم الكواكب الشخصية بمقياس 100 نقطة والكرامات الخمس")
            tab_p1, tab_p2 = st.tabs([f"👤 كواكب {name1}", f"❤️ كواكب {name2}"])

            def render_planets_tab(chart_data: Dict[str, Any], owner_name: str):
                for p_name in PERSONAL_PLANETS:
                    sc = chart_data["scores"][p_name]
                    lbl, icon, _ = get_strength_classification(sc)
                    p_info = chart_data["all_planets_data"][p_name]
                    retro_tag = " [متراجع R]" if p_info["speed"] < 0 else ""
                    st.markdown(f"""
                    <div class="planet-detail-box">
                        <strong>{ALL_PLANETS_AR[p_name]}{retro_tag}</strong>: 
                        <code>{sc:.1f} / 100</code> — {icon} <strong>{lbl}</strong> | 
                        برج {p_info['sign_name']} ({p_info['deg_in_sign']:.2f}°) — البيت {p_info['whole_sign_house']}<br>
                        <span style="font-size:12px; color:#475569;">{' • '.join(chart_data['reasons'][p_name])}</span>
                    </div>
                    """, unsafe_allow_html=True)

            with tab_p1:
                render_planets_tab(chart1, name1)
            with tab_p2:
                render_planets_tab(chart2, name2)

            # 7. جداول إسقاط البيوت والاتصالات المباشرة
            st.markdown("---")
            st.subheader("🏠 تحليل البيوت التوافقية الشامل (House Overlays - Whole Sign)")
            st.dataframe(synastry_res["df_overlays"], use_container_width=True)

            st.subheader("🔗 تفاصيل الاتصالات الفلكية المباشرة بين الكواكب والكويكبات (بدون تكرار)")
            st.dataframe(synastry_res["df_aspects"], use_container_width=True)

            # 8. التوصيات الفلكية والعلاجات
            st.markdown("---")
            st.subheader("💡 التوصيات والإرشادات العملية وعلاجات تقوية الكواكب فلكياً")
            tab_rec1, tab_rec2 = st.tabs([f"توصيات {name1}", f"توصيات {name2}"])
            with tab_rec1:
                for r in chart1["recommendations"]:
                    if r.startswith(("✨", "🏡", "💖", "🛠️", "👑", "👔", "🔥", "☀️", "🚀", "🌙", "🌹", "🌸", "⚡")):
                        st.markdown(f"#### {r}")
                    else:
                        st.markdown(f"- {r}")
            with tab_rec2:
                for r in chart2["recommendations"]:
                    if r.startswith(("✨", "🏡", "💖", "🛠️", "👑", "👔", "🔥", "☀️", "🚀", "🌙", "🌹", "🌸", "⚡")):
                        st.markdown(f"#### {r}")
                    else:
                        st.markdown(f"- {r}")

            # 9. توليد وتنزيل تقرير HTML المتكامل
            html_report = generate_combined_html_report(
                name1, gender1, dob1, t1_select, c1_name, chart1,
                name2, gender2, dob2, t2_select, c2_name, chart2,
                synastry_res
            )

            st.markdown("---")
            st.subheader("🖨️ تصدير وتحميل التقرير النهائي الشامل")
            b64 = base64.b64encode(html_report.encode("utf-8")).decode("utf-8")
            href = f'<a href="data:text/html;base64,{b64}" download="Synastry_Aura_Report_{name1}_{name2}.html" style="text-decoration: none;"><button style="padding: 14px 28px; background: linear-gradient(135deg, #16a34a 0%, #15803d 100%); color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: bold; width: 100%; box-shadow: 0 4px 15px rgba(22, 163, 74, 0.4);">📥 تنزيل التقرير الفلكي الشامل والجاهز للطباعة والـ PDF (HTML)</button></a>'
            st.markdown(href, unsafe_allow_html=True)
            st.success("تم إتمام التحليل الفلكي وميزان القطبية الطاقية بنجاح تام وبدقة رياضية صارمة.")

        except Exception as ex:
            st.error(f"حدث خطأ أثناء تنفيذ الحسابات الفلكية: {ex}")
            st.code(traceback.format_exc())

if __name__ == "__main__":
    pass
