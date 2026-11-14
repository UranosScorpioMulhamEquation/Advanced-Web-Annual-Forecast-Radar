from __future__ import annotations
import html
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import List, Tuple, Dict, Any
import base64
import traceback

import geonamescache
import libephemeris as swe
from timezonefinder import TimezoneFinder
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import os
import streamlit as st

# ==================== إعدادات الصفحة ودعم العربية (Streamlit) ====================
st.set_page_config(
    page_title="نظام التوافقية الفلكية المتقدم (شامل الكويكبات والمسؤوليات)",
    page_icon="✨",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');
html, body, [class*="css"] {
    direction: rtl;
    text-align: right;
    font-family: 'Cairo', sans-serif;
}
.stDownloadButton button {
    background-color: #27ae60 !important;
    color: white !important;
    font-weight: bold;
}
.stButton button {
    background-color: #6D28D9;
    color: white;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# ==================== إعدادات Swiss Ephemeris والكويكبات ====================
EPHE_PATH = "./ephe"
if not os.path.exists(EPHE_PATH):
    os.makedirs(EPHE_PATH)

swe.set_ephe_path(EPHE_PATH)

# ==================== الهياكل والبيانات الجغرافية ====================
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
                    latitude=city_data.get("latitude", 0.0),
                    longitude=city_data.get("longitude", 0.0),
                    admin1=city_data.get("admin1code", ""),
                    population=city_data.get("population", 0),
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

def get_timezone_for_city(city: City) -> str | None:
    try:
        tf = TimezoneFinder()
        return tf.timezone_at(lat=city.latitude, lng=city.longitude)
    except Exception:
        return None

# ==================== الأجرام والكواكب والكويكبات التوافقية الشاملة ====================
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

ZODIAC_NAMES = [
    "الحمل", "الثور", "الجوزاء", "السرطان",
    "الأسد", "العذراء", "الميزان", "العقرب",
    "القوس", "الجدي", "الدلو", "الحوت"
]

# ==================== الدوال الفلكية المتقدمة ====================
def calculate_partner_chart(birth_date: date, birth_time_input, city: City | None):
    is_unknown_time = (birth_time_input == "الساعة غير معروفة")
    if is_unknown_time:
        actual_time = time(12, 0)
    elif isinstance(birth_time_input, str):
        h, m = map(int, birth_time_input.split(":"))
        actual_time = time(h, m)
    else:
        actual_time = birth_time_input

    tz_name = get_timezone_for_city(city) if city else None
    tz = ZoneInfo(tz_name) if tz_name else timezone.utc

    local_dt = datetime.combine(birth_date, actual_time, tzinfo=tz)
    utc_dt = local_dt.astimezone(timezone.utc)
    jd_utc = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour + utc_dt.minute/60.0 + utc_dt.second/3600.0)

    lat = city.latitude if city else 33.5138
    lon = city.longitude if city else 36.2765

    cusps, ascmc = swe.houses_ex(jd_utc, lat, lon, b'W')
    asc_deg = ascmc[0]
    asc_sign_idx = int(asc_deg // 30) % 12

    house_system_name = "Whole Sign (كل برج بيت بناءً على الطالع الدقيق)"

    if is_unknown_time:
        sun_res, _ = swe.calc_ut(jd_utc, swe.SUN)
        sun_lon = sun_res[0]
        asc_deg = sun_lon
        asc_sign_idx = int(sun_lon // 30) % 12
        house_system_name = "Solar Sign (البيوت الشمسية الافتراضية لعدم دقة الوقت)"

    positions = {}
    for p_id, info in PLANETS.items():
        try:
            res, _ = swe.calc_ut(jd_utc, p_id)
            p_lon = res[0]
            speed = res[3]
            sign_idx = int(p_lon // 30) % 12
            deg_rem = p_lon % 30
            house_num = ((sign_idx - asc_sign_idx) % 12) + 1

            positions[p_id] = {
                "lon": p_lon,
                "sign_idx": sign_idx,
                "sign_name": ZODIAC_NAMES[sign_idx],
                "deg_rem": deg_rem,
                "house": house_num,
                "is_retro": speed < 0
            }
        except Exception:
            pass

    return {
        "jd": jd_utc,
        "asc_deg": asc_deg,
        "asc_sign_idx": asc_sign_idx,
        "asc_sign_name": ZODIAC_NAMES[asc_sign_idx],
        "positions": positions,
        "house_system": house_system_name
    }

def analyze_house_overlay(planet_id, planet_name, house_num, target_name):
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

def calculate_aspect(lon1, lon2):
    diff = abs(lon1 - lon2)
    if diff > 180:
        diff = 360 - diff

    aspect_name = None
    score = 0

    if diff <= 6:
        aspect_name = "اقتران (0° - دمج طاقات وتأثير مباشر)"
        score = +3
    elif abs(diff - 60) <= 6:
        aspect_name = "تسديس (60° - فرصة وتناغم سلس)"
        score = +2
    elif abs(diff - 90) <= 6:
        aspect_name = "تربيع (90° - تحدي واحتكاك ضاغط)"
        score = -3
    elif abs(diff - 120) <= 6:
        aspect_name = "تثليث (120° - تدفق وتوافق طبيعي عالٍ)"
        score = +4
    elif abs(diff - 180) <= 6:
        aspect_name = "معارضة (180° - شد وجذب وتكامل أو صراع)"
        score = -2

    return aspect_name, score

# ==================== واجهة المستخدم (Streamlit UI) ====================
st.title("✨ النظام المطور للخرائط الفلكية التوافقية (شامل الكويكبات والمسؤوليات)")
st.markdown("تطوير الخبير الفلكي: استرو رادار | تحليل دقيق للبيوت، الاتصالات، وكويكبات الزواج والشفاء (جونو، كيرون، ليليث)")
st.markdown("---")

countries = load_countries()
country_options = sorted([(f"{c['name']} ({c['iso']})", c['iso']) for c in countries.values()], key=lambda x: x[0])
country_display = [x[0] for x in country_options]
country_codes = [x[1] for x in country_options]

time_options = ["الساعة غير معروفة"] + [time(h, m).strftime('%H:%M') for h in range(24) for m in range(0, 60, 5)]

col1, col2 = st.columns(2)

with col1:
    st.subheader("👤 بيانات الشريك الأول")
    name1 = st.text_input("اسم الشريك الأول", "أحمد", key="n1")
    gender1 = st.selectbox("جنس الشريك الأول", ["ذكر", "أنثى"], index=0, key="g1")
    dob1 = st.date_input("تاريخ ميلاد الشريك الأول", min_value=date(1900, 1, 1), max_value=date(2100, 1, 1), value=date(1990, 1, 1), key="d1")
    t1_select = st.selectbox("ساعة ميلاد الشريك الأول", time_options, index=time_options.index("12:00") if "12:00" in time_options else 0, key="t1")
    
    sy_idx = country_codes.index("SY") if "SY" in country_codes else 0
    c1_display = st.selectbox("دولة ميلاد الشريك الأول", country_display, index=sy_idx, key="c1_disp")
    c1_code = country_codes[country_display.index(c1_display)]
    c1_cities = get_cities_by_country(c1_code)
    c1_names = [c.name for c in c1_cities]
    c1_name = st.selectbox("مدينة ميلاد الشريك الأول", c1_names if c1_names else ["غير متوفرة"], key="c1_name")
    city1 = next((c for c in c1_cities if c.name == c1_name), None)

with col2:
    st.subheader("❤️ بيانات الشريك الثاني")
    name2 = st.text_input("اسم الشريك الثاني", "سارة", key="n2")
    gender2 = st.selectbox("جنس الشريك الثاني", ["أنثى", "ذكر"], index=0, key="g2")
    dob2 = st.date_input("تاريخ ميلاد الشريك الثاني", min_value=date(1900, 1, 1), max_value=date(2100, 1, 1), value=date(1992, 5, 15), key="d2")
    t2_select = st.selectbox("ساعة ميلاد الشريك الثاني", time_options, index=time_options.index("12:00") if "12:00" in time_options else 0, key="t2")
    
    ae_idx = country_codes.index("AE") if "AE" in country_codes else 0
    c2_display = st.selectbox("دولة ميلاد الشريك الثاني", country_display, index=ae_idx, key="c2_disp")
    c2_code = country_codes[country_display.index(c2_display)]
    c2_cities = get_cities_by_country(c2_code)
    c2_names = [c.name for c in c2_cities]
    c2_name = st.selectbox("مدينة ميلاد الشريك الثاني", c2_names if c2_names else ["غير متوفرة"], key="c2_name")
    city2 = next((c for c in c2_cities if c.name == c2_name), None)

st.markdown("---")

if st.button("🚀 تشغيل التحليل التوافقي الشامل وتحديد المسؤوليات بدقة صارمة", type="primary", use_container_width=True):
    with st.spinner("جاري حساب الطوالع الدقيقة، مواقع الأجرام والكويكبات (جونو، كيرون، ليليث)، وتحديد المسؤوليات..."):
        try:
            chart1 = calculate_partner_chart(dob1, t1_select, city1)
            chart2 = calculate_partner_chart(dob2, t2_select, city2)

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

            # 1. حساب الاتصالات الفلكية بين الخريطتين
            for p1_id, p1_info in PLANETS.items():
                if p1_id not in chart1["positions"]: continue
                for p2_id, p2_info in PLANETS.items():
                    if p2_id not in chart2["positions"]: continue

                    lon1 = chart1["positions"][p1_id]["lon"]
                    lon2 = chart2["positions"][p2_id]["lon"]
                    asp, sc = calculate_aspect(lon1, lon2)

                    if asp:
                        pair_key = tuple(sorted([p1_info["name"], p2_info["name"]]))
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
                                if sc > 0: emotional_hits += 1
                                else: hurt_hits += 1

                            if p1_id in [swe.MERCURY, swe.JUPITER, swe.SUN, swe.PALLAS] or p2_id in [swe.MERCURY, swe.JUPITER, swe.SUN, swe.PALLAS]:
                                if sc > 0: mental_hits += 1

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

            # 2. تحليل البيوت التوافقية (House Overlays)
            for p1_id, p1_info in chart1["positions"].items():
                h_num = p1_info["house"]
                p_name = PLANETS[p1_id]["name"]
                warn, note = analyze_house_overlay(p1_id, p_name, h_num, name2)
                if warn:
                    warnings_list.append(warn)
                    if p1_id in [swe.SATURN, swe.PLUTO]: p1_pressure_score += 4
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
                    if p2_id in [swe.SATURN, swe.PLUTO]: p2_pressure_score += 4
                overlay_records.append({
                    "صاحب الكوكب": name2,
                    "الكوكب": p_name,
                    "يسقط في بيت الشريك": f"البيت {h_num}",
                    "التأثير الفلكي": note
                })

            # 3. تحديد المسؤوليات والأطراف بوضوح
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
                children_blocker = f"لا يوجد معيق فردي مباشر؛ المسؤولية مشتركة أو محايدة بين الطرفين"

            # 4. حساب المؤشرات والنسب المئوية
            total_aspects = max(1, (harmony_hits + conflict_hits))
            comfort_pct = int(min(100, max(10, (harmony_hits / total_aspects) * 100 + (total_score * 1.5))))
            emotional_pct = int(min(100, max(10, 50 + (emotional_hits * 5) - (hurt_hits * 6))))
            happiness_pct = int(min(100, max(5, comfort_pct * 0.75 + (marriage_support_score * 1.8))))
            conflict_pct = int(min(100, max(5, (conflict_hits / total_aspects) * 100 + ((p1_pressure_score + p2_pressure_score) * 1.5))))
            hurt_pct = int(min(100, max(5, (hurt_hits / total_aspects) * 100 + ((p1_pressure_score + p2_pressure_score) * 1.2))))
            mental_pct = int(min(100, max(15, (mental_hits / max(1, total_aspects)) * 100 + 25)))
            continuity_pct = int(min(100, max(10, (comfort_pct + emotional_pct - conflict_pct) / 1.15)))

            driver_party = name1 if p1_positive_hits >= p2_positive_hits else name2

            relationship_verdict = ""
            v_color = "green"
            if total_score >= 15 and marriage_support_score >= 8:
                relationship_verdict = f"💍 **علاقة ممتازة وتصلح بامتياز للزواج والاستقرار الدائم** بين {name1} و {name2}."
            elif total_score >= 6:
                relationship_verdict = f"🤝 **علاقة جيدة وتصلح للارتباط مع وجود تفاهم وتنازلات واعية**."
            elif -2 <= total_score < 6:
                relationship_verdict = f"⚖️ **علاقة متوسطة تتطلب جهداً شاقاً وإدارة حكيمة للخلافات**."
            else:
                relationship_verdict = f"❌ **علاقة شديدة الصعوبة (تحذير صارم من الارتباط)** نظراً لكثرة الضغوط والاستنزاف."
                v_color = "red"

            # ==================== عرض النتائج في واجهة الـ Streamlit ====================
            st.markdown("---")
            st.header("📊 التقرير التوافقي الشامل وتحديد المسؤوليات بدقة صارمة")

            col_res1, col_res2 = st.columns(2)
            with col_res1:
                st.markdown(f"### خلاصة العلاقة والقرار الفلكي:")
                st.markdown(f":{v_color}[{relationship_verdict}]")
                st.markdown(f"**المجموع الحسابي للنقاط:** {total_score}")
                st.markdown(f"**الشريك الداعم ماديّاً واقتصادياً:** **{material_supporter}**")
                st.markdown(f"**المستفيد الأساسي من العلاقة:** **{beneficiary}**")
                st.markdown(f"**طالع الشريك الأول ({name1}):** {chart1['asc_sign_name']} | **طالع الشريك الثاني ({name2}):** {chart2['asc_sign_name']}")

            with col_res2:
                st.markdown(f"**مصدر الضغط الهيكلي/الزحلي:** **{pressure_source}**")
                st.markdown(f"**الطرف الأكثر تضرراً نفسياً:** **{psych_sufferer}**")
                st.markdown(f"**المسؤول عن تعطيل الاستقرار أو دعم الأطفال:** **{children_blocker}**")
                st.markdown(f"**نظام البيوت المعمد:** {chart1['house_system']}")

            st.markdown("---")
            st.subheader("📈 مؤشرات ونسب التوافق مع تسمية المسؤول عنها صراحةً")

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("الراحة النفسية", f"{comfort_pct}%", f"الداعم: {driver_party}")
            m2.metric("الحميمية العاطفية", f"{emotional_pct}%", f"مشترك بين الطرفين")
            m3.metric("نسبة السعادة", f"{happiness_pct}%", f"مرتبطة بتناغم الطرفين")
            m4.metric("التفاهم العقلي", f"{mental_pct}%", f"المحرك: {driver_party}")

            m5, m6, m7 = st.columns(3)
            m5.metric("نسبة الصراعات", f"{conflict_pct}%", f"المسؤول: {pressure_source}")
            m6.metric("مؤشر الجروح والقيود", f"{hurt_pct}%", f"المتأثر: {psych_sufferer}")
            m7.metric("نسبة الاستمرار", f"{continuity_pct}%", f"بناءً على ميزان القوى")

            st.markdown("---")
            st.subheader("⚠️ التنبيهات والتحذيرات الفلكية الهامة")
            if warnings_list:
                for w in set(warnings_list):
                    st.warning(w)
            else:
                st.success("لم يتم رصد تحذيرات خطيرة أو اتصالات هدامة قوية بين الخريطتين.")

            import pandas as pd
            st.subheader("🏠 تحليل البيوت التوافقية الشامل (House Overlays - Whole Sign)")
            st.dataframe(pd.DataFrame(overlay_records), use_container_width=True)

            st.subheader("🔗 تفاصيل الاتصالات الفلكية بين الكواكب والكويكبات (بدون تكرار)")
            df_aspects = pd.DataFrame(aspect_records) if aspect_records else pd.DataFrame(columns=["ملاحظة"])
            st.dataframe(df_aspects, use_container_width=True)

            # ==================== بناء تقرير HTML المتكامل للطباعة والتحميل ====================
            aspects_html_rows = "".join([
                f"<tr><td>{row.get(f'كوكب {name1}', '-')}</td><td>{row.get('برج الطرف الأول', '-')}</td><td><b>{row.get('الاتصال الفلكي', '-')}</b></td><td>{row.get(f'كوكب {name2}', '-')}</td><td>{row.get('برج الطرف الثاني', '-')}</td><td>{row.get('نوع التأثير', '-')}</td></tr>"
                for _, row in df_aspects.iterrows()
            ])

            overlays_html_rows = "".join([
                f"<tr><td>{row['صاحب الكوكب']}</td><td>{row['الكوكب']}</td><td>{row['يسقط في بيت الشريك']}</td><td>{row['التأثير الفلكي']}</td></tr>"
                for _, row in pd.DataFrame(overlay_records).iterrows()
            ])

            warnings_html = "".join([f"<li>{w}</li>" for w in set(warnings_list)]) if warnings_list else "<li>لا توجد تحذيرات جوهرية مسجلة.</li>"

            html_report = f"""
            <!DOCTYPE html>
            <html lang="ar" dir="rtl">
            <head>
                <meta charset="UTF-8">
                <title>التقرير الفلكي التوافقي الشامل (بالكويكبات) - {name1} & {name2}</title>
                <style>
                    body {{ font-family: 'Cairo', Tahoma, Arial, sans-serif; margin: 40px; color: #2c3e50; background: #fdfdfd; line-height: 1.8; }}
                    h1, h2, h3 {{ color: #1a252f; text-align: center; }}
                    .header-box {{ background: #f8f9fa; padding: 25px; border-radius: 10px; border: 2px solid #cbd5e1; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
                    .metrics-box {{ display: flex; justify-content: space-around; background: #f1f5f9; padding: 20px; border-radius: 10px; margin-bottom: 25px; text-align: center; flex-wrap: wrap; border: 1px solid #e2e8f0; }}
                    .metric-item {{ margin: 10px; font-size: 15px; min-width: 120px; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; margin-bottom: 30px; font-size: 14px; background: white; }}
                    th, td {{ border: 1px solid #cbd5e1; padding: 12px; text-align: center; }}
                    th {{ background: #1e293b; color: white; }}
                    tr:nth-child(even) {{ background: #f8fafc; }}
                    .footer {{ text-align: center; margin-top: 50px; font-size: 13px; color: #64748b; border-top: 1px solid #e2e8f0; padding-top: 15px; }}
                    @media print {{ body {{ margin: 10px; background: white; }} .no-print {{ display: none; }} }}
                </style>
            </head>
            <body>
                <h1>✨ التقرير الفلكي التوافقي الشامل وتحديد المسؤوليات (بالكويكبات)</h1>
                
                <div class="header-box">
                    <p><b>الشريك الأول:</b> {name1} ({gender1}) | <b>تاريخ الميلاد:</b> {dob1} | <b>الطالع:</b> {chart1['asc_sign_name']}</p>
                    <p><b>الشريك الثاني:</b> {name2} ({gender2}) | <b>تاريخ الميلاد:</b> {dob2} | <b>الطالع:</b> {chart2['asc_sign_name']}</p>
                    <hr style="border: 0; border-top: 1px solid #cbd5e1; margin: 15px 0;">
                    <p><b>خلاصة العلاقة والقرار:</b> {relationship_verdict}</p>
                    <p><b>الشريك الداعم ماديّاً واقتصادياً:</b> <b>{material_supporter}</b></p>
                    <p><b>مصدر الضغط الهيكلي والزحلي:</b> <b>{pressure_source}</b> | <b>الطرف المتضرر نفسياً:</b> <b>{psych_sufferer}</b></p>
                    <p><b>المستفيد من العلاقة:</b> {beneficiary} | <b>المسؤول عن تعطيل الاستقرار:</b> {children_blocker}</p>
                </div>

                <div class="metrics-box">
                    <div class="metric-item"><b>الراحة النفسية:</b> {comfort_pct}% <br><small>الداعم: {driver_party}</small></div>
                    <div class="metric-item"><b>الحميمية:</b> {emotional_pct}% <br><small>مشترك</small></div>
                    <div class="metric-item"><b>السعادة:</b> {happiness_pct}% <br><small>مرتبط بالتناغم</small></div>
                    <div class="metric-item"><b>التفاهم العقلي:</b> {mental_pct}% <br><small>المحرك: {driver_party}</small></div>
                    <div class="metric-item"><b>الصراعات:</b> {conflict_pct}% <br><small>المسؤول: {pressure_source}</small></div>
                    <div class="metric-item"><b>الجروح والقيود:</b> {hurt_pct}% <br><small>المتأثر: {psych_sufferer}</small></div>
                    <div class="metric-item"><b>الاستمرار:</b> {continuity_pct}% <br><small>حسب الميزان</small></div>
                </div>

                <h2>⚠️ التنبيهات والتحذيرات الفلكية</h2>
                <ul style="line-height: 1.8; background: #fffbeb; padding: 20px 40px; border-radius: 8px; border: 1px solid #fef3c7;">{warnings_html}</ul>

                <h2>🏠 جدول تحليلات البيوت التوافقية الشامل (House Overlays)</h2>
                <table>
                    <thead><tr><th>صاحب الكوكب</th><th>الكوكب/الكويكب</th><th>يسقط في بيت الشريك</th><th>طبيعة التأثير والتحذير الفلكي</th></tr></thead>
                    <tbody>{overlays_html_rows}</tbody>
                </table>

                <h2>🔗 تفاصيل الاتصالات الفلكية المباشرة (بدون تكرار)</h2>
                <table>
                    <thead><tr><th>كوكب {name1}</th><th>البرج</th><th>الاتصال الفلكي</th><th>كوكب {name2}</th><th>برج الطرف الثاني</th><th>نوع التأثير</th></tr></thead>
                    <tbody>{aspects_html_rows}</tbody>
                </table>

                <div class="footer">
                    <p>تم إعداد هذا التقرير الاحترافي بالاعتماد على خوارزميات السويِس إيفيميريس (Swiss Ephemeris) ومسار ملفات الكويكبات الشامل.</p>
                </div>

                <div style="text-align: center; margin-top: 30px;" class="no-print">
                    <button onclick="window.print()" style="padding: 12px 25px; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; font-weight: bold;">🖨️ طباعة أو حفظ التقرير PDF</button>
                </div>
            </body>
            </html>
            """

            st.markdown("---")
            st.subheader("🖨️ تصدير وتحميل التقرير النهائي")
            b64 = base64.b64encode(html_report.encode("utf-8")).decode("utf-8")
            href = f'<a href="data:text/html;base64,{b64}" download="Synastry_Asteroids_Report_{name1}_{name2}.html" style="text-decoration: none;"><button style="padding: 12px 25px; background-color: #16a34a; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; font-weight: bold;">📥 تنزيل التقرير الشامل بالكويكبات (HTML جاهز للطباعة والـ PDF)</button></a>'
            st.markdown(href, unsafe_allow_html=True)
            st.success("تم إتمام الحسابات الفلكية الشاملة لكافة الكواكب والكويكبات الأساسية بنجاح.")

        except Exception as ex:
            st.error(f"حدث خطأ أثناء الحسابات الفلكية: {ex}")
            st.code(traceback.format_exc())

if __name__ == "__main__":
    pass
