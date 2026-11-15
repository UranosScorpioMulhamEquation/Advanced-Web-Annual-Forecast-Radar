"""
حاسبة الأزمات الزوجية، الطلاق، الانفصال والشراكات المتقدمة (50 دلالة فلكية + جميع ميد بوينت الطلاق)
إعداد وتطوير: الفلكي الدكتور استرو رادار.
"""

import datetime
import os
import geonamescache
import pytz
import streamlit as st
import swisseph as swe
from timezonefinder import TimezoneFinder
from dataclasses import dataclass

# =============================================================================
# إعدادات Swiss Ephemeris
# =============================================================================
swe.set_ephe_path('')  # استخدام وضع Moshier الافتراضي للتقويم الفلكي الدقيق

# =============================================================================
# 1. إعدادات واجهة المستخدم وتكوين التطبيق (RTL)
# =============================================================================
st.set_page_config(
    page_title="حاسبة الأزمات الزوجية والطلاق المتقدمة (50 دلالة وميد بوينت شامل)",
    layout="wide",
    page_icon="💔",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&family=Amiri:wght@700&display=swap');
    
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stSidebar"] {
        font-family: 'Cairo', sans-serif;
        direction: rtl;
        text-align: right;
    }
    .stSelectbox, .stTextInput, .stDateInput, .stTimeInput, .stButton, div[data-baseweb="select"], .stMarkdown, p, span, label, div {
        direction: rtl;
        text-align: right;
    }
    div[data-baseweb="base-input"] {
        direction: rtl;
    }
    .main-header {
        text-align: center;
        background: linear-gradient(135deg, #1a0000 0%, #3d0000 100%);
        color: #f1f5f9;
        padding: 24px;
        border-radius: 12px;
        border: 2px solid #ef4444;
        margin-bottom: 25px;
    }
    .main-header h1 {
        font-family: 'Amiri', serif;
        color: #fca5a5;
        font-size: 26px;
        margin-bottom: 6px;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================================================================
# 2. تهيئة قواعد البيانات الجغرافية ودوال التحميل
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

def get_timezone_for_city(city: dict) -> str | None:
    try:
        tf = TimezoneFinder()
        return tf.timezone_at(lat=city["latitude"], lng=city["longitude"])
    except Exception:
        return None

@st.cache_data
def load_geo_data():
    countries = load_countries()
    cities = load_cities()

    country_map = {c["name"]: code for code, c in countries.items()}
    sorted_countries = sorted(list(country_map.keys()))

    cities_by_country = {}
    for c_code in country_map.values():
        c_cities = [
            city for city in cities if city.country_code == c_code
        ]
        c_cities_sorted = sorted(
            c_cities, key=lambda x: x.population, reverse=True
        )
        cities_by_country[c_code] = c_cities_sorted

    return country_map, sorted_countries, cities_by_country

country_map, country_list, cities_by_country = load_geo_data()
tf = TimezoneFinder()

# =============================================================================
# 3. الثوابت الفلكية وحكام البروج والنقاط المحورية
# =============================================================================
PLANETS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
    "Rahu": swe.TRUE_NODE
}

ZODIAC_NAMES = [
    "الحمل", "الثور", "الجوزاء", "السرطان",
    "الأسد", "العذراء", "الميزان", "العقرب",
    "القوس", "الجدي", "الدلو", "الحوت",
]

SIGN_RULERS = {
    0: "Mars",    
    1: "Venus",   
    2: "Mercury", 
    3: "Moon",    
    4: "Sun",     
    5: "Mercury", 
    6: "Venus",   
    7: "Pluto",   
    8: "Jupiter", 
    9: "Saturn",  
    10: "Uranus", 
    11: "Neptune" 
}

# =============================================================================
# 4. الدوال الفلكية والرياضية الأساسية
# =============================================================================
def get_utc_julian_day(date_obj, time_obj, tz_str):
    local_tz = pytz.timezone(tz_str)
    dt = datetime.datetime.combine(date_obj, time_obj)
    local_dt = local_tz.localize(dt)
    utc_dt = local_dt.astimezone(pytz.utc)
    return swe.julday(
        utc_dt.year,
        utc_dt.month,
        utc_dt.day,
        utc_dt.hour + utc_dt.minute / 60.0 + utc_dt.second / 3600.0,
    )

def find_exact_solar_return(target_year, natal_sun_lon, birth_month, birth_day, birth_time, b_tz):
    guess_dt = datetime.datetime(target_year, birth_month, birth_day, birth_time.hour, birth_time.minute)
    local_tz = pytz.timezone(b_tz)
    utc_dt = local_tz.localize(guess_dt).astimezone(pytz.utc)
    jd_guess = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour + utc_dt.minute / 60.0)

    for _ in range(20):
        sun_lon = swe.calc_ut(jd_guess, swe.SUN)[0][0]
        diff = natal_sun_lon - sun_lon
        if diff > 180: diff -= 360
        if diff < -180: diff += 360
        jd_guess += diff / 0.985647
        if abs(diff) < 0.000001:
            break
    return jd_guess

def get_house_of_planet(p_lon, cusps):
    for i in range(12):
        c1 = cusps[i]
        c2 = cusps[(i + 1) % 12]
        if c1 < c2:
            if c1 <= p_lon < c2: return i + 1
        else:
            if p_lon >= c1 or p_lon < c2: return i + 1
    return 1

def calc_midpoint(p1_lon, p2_lon):
    diff = abs(p1_lon - p2_lon)
    if diff <= 180:
        mp = (p1_lon + p2_lon) / 2.0
    else:
        mp = (p1_lon + p2_lon + 360) / 2.0
        if mp >= 360: mp -= 360
    return mp

def is_conjunct_cusp(p_lon, cusp_lon, orb=6):
    diff = abs((cusp_lon - p_lon + 180) % 360 - 180)
    return diff <= orb

def get_aspect(lon1, lon2, orb=6):
    diff = abs((lon1 - lon2 + 180) % 360 - 180)
    if diff <= orb: return "Conjunction"
    if abs(diff - 90) <= orb: return "Square"
    if abs(diff - 180) <= orb: return "Opposition"
    if abs(diff - 120) <= orb: return "Trine"
    if abs(diff - 60) <= orb: return "Sextile"
    return None

def check_conjunction_or_opposition(p_lon, midpoint_lon, orb=2.0):
    """
    التحقق من اتصال كوكب السنوية بميد بوينت الميلادي:
    - اقتراب في نفس البرج (0 درجة / نفس الموقع) أو مقابلة تامة (180 درجة) فقط[cite: 7].
    - الأورب أقل من درجتين (< 2.0°)[cite: 7].
    """
    dist = abs((p_lon - midpoint_lon + 180) % 360 - 180)
    for target_angle in [0.0, 180.0]:
        diff_from_target = abs(dist - target_angle)
        if diff_from_target < orb:
            aspect_label = "اقتران في نفس البرج (0°)" if target_angle == 0.0 else "مقابلة تامة (180°)"
            return True, aspect_label, diff_from_target
    return False, None, 0.0

def calculate_expected_months(target_year, birth_date, active_houses):
    """
    حساب وتحديد الأشهر المتوقعة للحدث خلال سنة العودة الشمسية بناءً على البيوت الفعالة[cite: 7].
    """
    birth_month = birth_date.month
    months_ar = [
        "يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
        "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"
    ]
    derived_months = []
    base_month = birth_month
    
    for h in active_houses:
        target_m = ((base_month + h - 2) % 12) + 1
        derived_months.append(target_m)
    
    if not derived_months:
        derived_months = [base_month, (base_month % 12) + 1]
        
    derived_months = sorted(list(set(derived_months)))
    month_names = [months_ar[m - 1] for m in derived_months]
    return " و ".join(month_names), derived_months

def check_midpoints_activation(sr_planets, midpoints_dict):
    """
    فحص تفعيل جميع نقاط المنتصف (Midpoints) الشاملة للطلاق والانفصال[cite: 7].
    الشروط: الأورب أقل من 2 درجة (< 2.0°) للاقتران والمقابلة فقط[cite: 7].
    التصنيفات المحدثة:
    - 1 ميد بوينت = عدم ارتياح في العلاقة
    - 2 ميد بوينت = غضب داخلي
    - 3 ميد بوينت = مشاكل زوجية حادة
    - 4 ميد بوينت = تفكير في الطلاق
    - 5 ميد بوينت فما فوق = طلاق
    """
    activated_details = []
    activated_mp_names = set()

    for mp_name, mp_lon in midpoints_dict.items():
        for p_name, p_data in sr_planets.items():
            p_lon = p_data["lon"]
            is_act, aspect_label, diff_val = check_conjunction_or_opposition(p_lon, mp_lon, orb=2.0)
            if is_act:
                p_sign_idx = int(p_lon / 30)
                activated_details.append(
                    f"تفعيل [{mp_name}] بواسطة كوكب **{p_name}** السنوي ببرج {ZODIAC_NAMES[p_sign_idx]} عبر ({aspect_label}) بفارق دقيق: {diff_val:.2f}°"
                )
                activated_mp_names.add(mp_name)

    count = len(activated_mp_names)

    if count == 0:
        status = "استقرار أو أزمة عابرة"
    elif count == 1:
        status = "عدم ارتياح في العلاقة"
    elif count == 2:
        status = "غضب داخلي"
    elif count == 3:
        status = "مشاكل زوجية حادة"
    elif count == 4:
        status = "تفكير في الطلاق"
    else:
        status = "طلاق"

    return activated_details, count, status

# =============================================================================
# 5. بناء واجهة المستخدم
# =============================================================================
st.markdown("""
<div class="main-header">
    <h1>حاسبة الأزمات الزوجية، الطلاق، الانفصال والشراكات (50 دلالة فلكية + جميع ميد بوينت الطلاق)</h1>
    <p>محرك تحليل فلكي متقدم يعتمد على جميع ميد بوينت الطلاق والانفصال بمعايير دقيقة (أورب < 2° للاقتران والمقابلة فقط)</p>
    <p>تطوير: الفلكي الدكتور استرو رادار</p>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

default_b_country_idx = country_list.index("Syria") if "Syria" in country_list else 0
default_sr_country_idx = country_list.index("United Arab Emirates") if "United Arab Emirates" in country_list else 0

with col1:
    name = st.text_input("اسم صاحب/ة الخريطة", "ملهم")
    birth_date = st.date_input("تاريخ الميلاد", value=datetime.date(1985, 4, 17), min_value=datetime.date(1950, 1, 1))
    birth_time = st.time_input("ساعة الميلاد بدقة", value=datetime.time(14, 30), step=datetime.timedelta(minutes=1))

with col2:
    st.markdown("### 🌍 مكان الميلاد")
    b_country_name = st.selectbox("دولة الميلاد", country_list, index=default_b_country_idx, key="b_country_select")
    b_c_code = country_map[b_country_name]
    b_city_objects = cities_by_country.get(b_c_code, [])
    b_city_names = [c["name"] for c in b_city_objects] if b_city_objects else [b_country_name]
    b_city_name = st.selectbox("مدينة الميلاد", b_city_names, index=0, key="b_city_select")

with col3:
    st.markdown("### 📍 مكان السنوية (المكان الحالي)")
    sr_country_name = st.selectbox("دولة السنوية", country_list, index=default_sr_country_idx, key="sr_country_select")
    sr_c_code = country_map[sr_country_name]
    sr_city_objects = cities_by_country.get(sr_c_code, [])
    sr_city_names = [c["name"] for c in sr_city_objects] if sr_city_objects else [sr_country_name]
    sr_city_name = st.selectbox("مدينة السنوية", sr_city_names, index=0, key="sr_city_select")

submit = st.button("🚀 بدء الفحص الشامل للسنوات الحرجة والطلاق (50 دلالة وميد بوينت شامل)", type="primary")

# =============================================================================
# 6. المحرك الأساسي ومعالجة البيانات الفلكية الشاملة
# =============================================================================
if submit:
    b_city_obj = next((c for c in b_city_objects if c["name"] == b_city_name), None)
    sr_city_obj = next((c for c in sr_city_objects if c["name"] == sr_city_name), None)

    b_lat, b_lon = (b_city_obj["latitude"], b_city_obj["longitude"]) if b_city_obj else (33.5138, 36.2765)
    sr_lat, sr_lon = (sr_city_obj["latitude"], sr_city_obj["longitude"]) if sr_city_obj else (25.2048, 55.2708)

    b_tz = get_timezone_for_city(b_city_obj) if b_city_obj else None
    if not b_tz: b_tz = tf.timezone_at(lng=b_lon, lat=b_lat) or "UTC"

    sr_tz = get_timezone_for_city(sr_city_obj) if sr_city_obj else None
    if not sr_tz: sr_tz = tf.timezone_at(lng=sr_lon, lat=sr_lat) or "UTC"

    jd_birth = get_utc_julian_day(birth_date, birth_time, b_tz)

    natal_planets = {}
    for p_name, p_id in PLANETS.items():
        res = swe.calc_ut(jd_birth, p_id)
        natal_planets[p_name] = res[0][0]

    # حساب البيوت الميلادية بنظام ريغومونتانوس (b'R')[cite: 7]
    natal_cusps, _ = swe.houses(jd_birth, b_lat, b_lon, b"R")

    # جمع كافة ميد بوينت الطلاق، الانفصال والأزمات الزوجية (شامل لكل المحاور الحساسة)[cite: 7]
    natal_midpoints = {
        "زحل/الزهرة": calc_midpoint(natal_planets["Saturn"], natal_planets["Venus"]),
        "زحل/المريخ": calc_midpoint(natal_planets["Saturn"], natal_planets["Mars"]),
        "زحل/القمر": calc_midpoint(natal_planets["Saturn"], natal_planets["Moon"]),
        "زحل/الشمس": calc_midpoint(natal_planets["Saturn"], natal_planets["Sun"]),
        "زحل/أورانوس": calc_midpoint(natal_planets["Saturn"], natal_planets["Uranus"]),
        "زحل/بلوتو": calc_midpoint(natal_planets["Saturn"], natal_planets["Pluto"]),
        "أورانوس/الزهرة": calc_midpoint(natal_planets["Uranus"], natal_planets["Venus"]),
        "أورانوس/المريخ": calc_midpoint(natal_planets["Uranus"], natal_planets["Mars"]),
        "أورانوس/القمر": calc_midpoint(natal_planets["Uranus"], natal_planets["Moon"]),
        "أورانوس/الشمس": calc_midpoint(natal_planets["Uranus"], natal_planets["Sun"]),
        "بلوتو/الزهرة": calc_midpoint(natal_planets["Pluto"], natal_planets["Venus"]),
        "بلوتو/المريخ": calc_midpoint(natal_planets["Pluto"], natal_planets["Mars"]),
        "بلوتو/القمر": calc_midpoint(natal_planets["Pluto"], natal_planets["Moon"]),
        "بلوتو/الشمس": calc_midpoint(natal_planets["Pluto"], natal_planets["Sun"]),
        "المريخ/الزهرة": calc_midpoint(natal_planets["Mars"], natal_planets["Venus"]),
        "زحل/راهو": calc_midpoint(natal_planets["Saturn"], natal_planets["Rahu"]),
        "أورانوس/راهو": calc_midpoint(natal_planets["Uranus"], natal_planets["Rahu"]),
        "بلوتو/راهو": calc_midpoint(natal_planets["Pluto"], natal_planets["Rahu"]),
    }

    st.info("📌 تم استخراج المواقع الميلادية وجميع نقاط المنتصف الشاملة للطلاق بدقة. جاري مسح العبور السنوي وفقاً لشرط تفعيل 1 ميد بوينت على الأقل (أورب < 2°) و5 الدلالات السنوية المطلوبة...")

    start_year = birth_date.year + 18
    end_year = birth_date.year + 65
    years_list = list(range(start_year, end_year + 1))
    total_years = len(years_list)

    divorce_years = []
    progress_bar = st.progress(0.0)

    for i, target_year in enumerate(years_list):
        progress_val = min(1.0, (i + 1) / total_years)

        jd_sr = find_exact_solar_return(
            target_year, natal_planets["Sun"],
            birth_date.month, birth_date.day, birth_time, b_tz
        )

        sr_cusps, _ = swe.houses(jd_sr, sr_lat, sr_lon, b"R")
        sr_asc = sr_cusps[0]

        sr_planets = {}
        for p_name, p_id in PLANETS.items():
            res = swe.calc_ut(jd_sr, p_id)
            lon = res[0][0]
            speed = res[0][3]
            sr_planets[p_name] = {
                "lon": lon,
                "sign": int(lon / 30),
                "house": get_house_of_planet(lon, sr_cusps),
                "is_retro": speed < 0,
            }

        # 1. فحص تفعيل الميد بوينت (بشرط تفعيل 1 ميد بوينت على الأقل بفارق < 2.0° لاقتراب نفس البرج أو المقابلة)
        mp_details, mp_count, mp_status = check_midpoints_activation(sr_planets, natal_midpoints)

        if mp_count < 1:
            progress_bar.progress(progress_val)
            continue

        # حساب الأشهر المتوقعة للحدث خلال سنة العودة الشمسية[cite: 7]
        active_h_crisis = [7, 8, 12, 4, 1]
        expected_months_str, _ = calculate_expected_months(target_year, birth_date, active_h_crisis)

        # =====================================================================
        # 2. تقييم دلالات الطلاق والانفصال السنوية الـ 50 الكاملة
        # =====================================================================
        dallalat_details = []
        dallalat_count = 0

        ruler_7 = SIGN_RULERS[int(sr_cusps[6] / 30)]
        ruler_1 = SIGN_RULERS[int(sr_cusps[0] / 30)]

        # --- مجموعة الأوتاد والبيوت (من 1 إلى 12) ---
        sr_asc_in_natal = get_house_of_planet(sr_asc, natal_cusps)
        if sr_asc_in_natal in [8, 12]:
            dallalat_count += 1
            dallalat_details.append(f"1. طالع العودة الشمسية في **البيت {sr_asc_in_natal} الميلادي** (بيت النهايات والأزمات).")

        sr_h7_in_natal = get_house_of_planet(sr_cusps[6], natal_cusps)
        if sr_h7_in_natal in [8, 12]:
            dallalat_count += 1
            dallalat_details.append(f"2. البيت السابع السنوي في **البيت {sr_h7_in_natal} الميلادي** (تحولات جذرية بالشراكة).")

        if sr_planets["Uranus"]["house"] == 7:
            dallalat_count += 1
            dallalat_details.append("3. أورانوس السنوي في **البيت 7** (قطيعة مفاجئة وتمرد وانفصال).")

        if sr_planets["Saturn"]["house"] == 7:
            dallalat_count += 1
            dallalat_details.append("4. زحل السنوي في **البيت 7** (جفاء عاطفي ومسؤوليات ثقيلة تقتل العلاقة).")

        if sr_planets["Pluto"]["house"] == 7:
            dallalat_count += 1
            dallalat_details.append("5. بلوتو السنوي في **البيت 7** (صراعات سيطرة قوية وهدم أركان الزواج).")

        if sr_planets["Mars"]["house"] == 7:
            dallalat_count += 1
            dallalat_details.append("6. المريخ السنوي في **البيت 7** (نزاعات حادة ومشاجرات ومعارك قانونية).")

        if sr_planets["Venus"]["house"] in [8, 12]:
            dallalat_count += 1
            dallalat_details.append(f"7. الزهرة غارقة في **البيت {sr_planets['Venus']['house']} السنوي** (فقدان الشغف والأحزان).")

        if sr_planets["Moon"]["house"] in [8, 12] or sr_planets["Moon"]["sign"] == 7:
            dallalat_count += 1
            dallalat_details.append(f"8. القمر السنوي في وضع حرج (البيت {sr_planets['Moon']['house']} / برج العقرب).")

        if sr_planets["Sun"]["house"] in [8, 12]:
            dallalat_count += 1
            dallalat_details.append(f"9. الشمس السنوية في **البيت {sr_planets['Sun']['house']}** (استنزاف الهوية وضغوط نفسية).")

        if sr_planets[ruler_7]["house"] in [8, 12]:
            dallalat_count += 1
            dallalat_details.append(f"10. حاكم السابع السنوي ({ruler_7}) في **البيت {sr_planets[ruler_7]['house']}** (ابتعاد الشريك).")

        if sr_planets[ruler_7]["is_retro"]:
            dallalat_count += 1
            dallalat_details.append(f"11. حاكم البيت السابع السنوي ({ruler_7}) **متراجع** (تردد، إعادة نظر، أو تراجع الشريك).")

        if sr_planets[ruler_1]["is_retro"] or sr_planets[ruler_1]["house"] in [8, 12]:
            dallalat_count += 1
            dallalat_details.append(f"12. حاكم الطالع السنوي ({ruler_1}) **متراجع أو بالبيت {sr_planets[ruler_1]['house']}**.")

        # --- مجموعة الاتصالات النحسة (من 13 إلى 25) ---
        if get_aspect(sr_planets["Mars"]["lon"], sr_planets["Venus"]["lon"], orb=6) in ["Square", "Opposition"]:
            dallalat_count += 1
            dallalat_details.append("13. تربيع أو مقابلة بين **المريخ والزهرة** (تصادم الرغبات وتفجر الخلافات).")

        if get_aspect(sr_planets["Saturn"]["lon"], sr_planets["Venus"]["lon"], orb=6) in ["Square", "Opposition"]:
            dallalat_count += 1
            dallalat_details.append("14. تربيع أو مقابلة بين **زحل والزهرة** (برود شديد وشعور بالحرمان).")

        if get_aspect(sr_planets["Uranus"]["lon"], sr_planets["Venus"]["lon"], orb=6) in ["Square", "Opposition"]:
            dallalat_count += 1
            dallalat_details.append("15. تربيع أو مقابلة بين **أورانوس والزهرة** (صدمة ورغبة مفاجئة بالقطيعة).")

        if get_aspect(sr_planets["Pluto"]["lon"], sr_planets["Venus"]["lon"], orb=6) in ["Square", "Opposition"]:
            dallalat_count += 1
            dallalat_details.append("16. تربيع أو مقابلة بين **بلوتو والزهرة** (غيرة مرضية وشكوك مدمرة).")

        if get_aspect(sr_planets["Saturn"]["lon"], sr_planets["Moon"]["lon"], orb=6) in ["Square", "Opposition"]:
            dallalat_count += 1
            dallalat_details.append("17. تربيع أو مقابلة بين **زحل والقمر** (حزن واحباط عائلي عميق).")

        if get_aspect(sr_planets["Uranus"]["lon"], sr_planets["Moon"]["lon"], orb=6) in ["Square", "Opposition"]:
            dallalat_count += 1
            dallalat_details.append("18. تربيع أو مقابلة بين **أورانوس والقمر** (تقلبات وانزعاج من الاستقرار).")

        if get_aspect(sr_planets["Mars"]["lon"], sr_planets["Moon"]["lon"], orb=6) in ["Square", "Opposition"]:
            dallalat_count += 1
            dallalat_details.append("19. تربيع أو مقابلة بين **المريخ والقمر** (حدة انفعالية وغضب مكتوم).")

        if sr_planets["Rahu"]["house"] == 7:
            dallalat_count += 1
            dallalat_details.append("20. عقدة راهو في **البيت 7** (أحداث قدرية وصدمات غير متوقعة في الشراكة).")

        if sr_planets["Jupiter"]["is_retro"]:
            dallalat_count += 1
            dallalat_details.append("21. المشتري السنوي **متراجع** (تعثر في التسويات القانونية وتأجيل حل النزاعات).")

        malefics_in_7th = [p for p in ["Saturn", "Mars", "Uranus", "Pluto"] if sr_planets[p]["house"] == 7]
        if len(malefics_in_7th) >= 2:
            dallalat_count += 1
            dallalat_details.append(f"22. تجمع نحس متعدد في البيت 7: (**{', '.join(malefics_in_7th)}**).")

        malefics_in_angles = [p for p in ["Saturn", "Mars", "Uranus", "Pluto"] if sr_planets[p]["house"] in [1, 4, 7, 10]]
        if len(malefics_in_angles) >= 3:
            dallalat_count += 1
            dallalat_details.append("23. هيمنة نحسة مكثفة على الأوتاد السنوية (أكثر من 3 كواكب ثقيلة).")

        target_malefics = ["Uranus", "Saturn", "Pluto", "Mars"]
        target_cusps = [sr_cusps[0], sr_cusps[3], sr_cusps[6], sr_cusps[9]]
        cusp_contacts = []
        for p_name in target_malefics:
            p_lon = sr_planets[p_name]["lon"]
            for cusp_idx, cusp in enumerate(target_cusps):
                if is_conjunct_cusp(p_lon, cusp, orb=6):
                    h_num = 1 if cusp_idx == 0 else (4 if cusp_idx == 1 else (7 if cusp_idx == 2 else 10))
                    cusp_contacts.append(f"{p_name} مع وِتْد البيت {h_num}")
                    break
        if cusp_contacts:
            dallalat_count += 1
            dallalat_details.append(f"24. اقتران كواكب الهدم بأوتاد السنوية (أورب ≤ 6°): ({', '.join(cusp_contacts)}).")

        conj_ruler7_malefic = [
            p for p in ["Saturn", "Mars", "Uranus", "Pluto"]
            if p != ruler_7 and get_aspect(sr_planets[ruler_7]["lon"], sr_planets[p]["lon"], orb=6) == "Conjunction"
        ]
        if conj_ruler7_malefic:
            dallalat_count += 1
            dallalat_details.append(f"25. حاكم السابع ({ruler_7}) مقترن بنحس (**{', '.join(conj_ruler7_malefic)}**).")

        # --- تكملة الدلالات التخصصية الـ 25 الإضافية لتصبح المنظومة 50 دلالة متكاملة ---
        # 26
        if sr_planets["Mercury"]["house"] in [8, 12]:
            dallalat_count += 1
            dallalat_details.append("26. عطارد السنوي في البيت 8 أو 12 (مراسلات قانونية سلبية أو نزاع بالكلام والكتابة).")

        # 27
        if get_aspect(sr_planets["Mercury"]["lon"], sr_planets["Saturn"]["lon"], orb=6) in ["Square", "Opposition"]:
            dallalat_count += 1
            dallalat_details.append("27. تربيع أو مقابلة بين عطارد وزحل (انقطاع التواصل، جفاء الحوار، والكلمات القاسية).")

        # 28
        if get_aspect(sr_planets["Mercury"]["lon"], sr_planets["Mars"]["lon"], orb=6) in ["Square", "Opposition"]:
            dallalat_count += 1
            dallalat_details.append("28. تربيع أو مقابلة بين عطارد والمريخ (مشادّات كلامية حادة جداً وشتائم).")

        # 29
        if sr_planets["Sun"]["is_retro"]:
            dallalat_count += 1
            dallalat_details.append("29. الشمس متراجعة في العودة الشمسية (انطفاء لهيب العلاقة وتهميش دور أحد الزوجين).")

        # 30
        if sr_planets["Venus"]["is_retro"]:
            dallalat_count += 1
            dallalat_details.append("30. الزهرة متراجعة في العودة الشمسية (أزمة عاطفية خانقة وعودة لآلام الماضي).")

        # 31
        if sr_planets["Mars"]["is_retro"]:
            dallalat_count += 1
            dallalat_details.append("31. المريخ متراجع في العودة الشمسية (غضب مكتوم، عجز عن المبادرة، أو انفجار مفاجئ).")

        # 32
        if sr_planets["Saturn"]["is_retro"]:
            dallalat_count += 1
            dallalat_details.append("32. زحل متراجع (فترة اختبارات قاسية جداً للالتزامات الزوجية وانهيار العقود).")

        # 33
        if sr_planets["Uranus"]["is_retro"]:
            dallalat_count += 1
            dallalat_details.append("33. أورانوس متراجع (ثورة داخلية مكبوتة تنفجر بشكل مفاجئ لإنهاء الشراكة).")

        # 34
        if sr_planets["Pluto"]["is_retro"]:
            dallalat_count += 1
            dallalat_details.append("34. بلوتو متراجع (تحولات نفسية عميقة وهدم جذري للبنية التحتية للبيت والزواج).")

        # 35
        if sr_planets["Neptune"]["house"] in [7, 8, 12]:
            dallalat_count += 1
            dallalat_details.append("35. نبتون في بيوت الشراكة أو النهايات (خداع، أوهام، اكتشاف حقائق مخفية أو خيانة).")

        # 36
        if get_aspect(sr_planets["Neptune"]["lon"], sr_planets["Venus"]["lon"], orb=6) in ["Square", "Opposition", "Conjunction"]:
            dallalat_count += 1
            dallalat_details.append("36. اتصال نحس بين نبتون والزهرة (خيبة أمل كبرى في الشريك وانكشاف الأكاذيب).")

        # 37
        if sr_planets["Neptune"]["is_retro"]:
            dallalat_count += 1
            dallalat_details.append("37. نبتون متراجع (انقشاع الضباب ورؤية الواقع المرير للشراكة بوضوح تام).")

        # 38
        sr_h4_in_natal = get_house_of_planet(sr_cusps[3], natal_cusps)
        if sr_h4_in_natal in [8, 12]:
            dallalat_count += 1
            dallalat_details.append(f"38. البيت الرابع السنوي في البيت {sr_h4_in_natal} الميلادي (انهيار الاستقرار المنزلي وخراب البيت).")

        # 39
        if sr_planets["Saturn"]["house"] == 4:
            dallalat_count += 1
            dallalat_details.append("39. زحل في البيت الرابع السنوي (ثقل الأجواء المنزلية، البرود، والمسؤوليات الضاغطة).")

        # 40
        if sr_planets["Mars"]["house"] == 4:
            dallalat_count += 1
            dallalat_details.append("40. المريخ في البيت الرابع السنوي (جِجار عائلي مستمر واشتعال النزاعات تحت السقف الواحد).")

        # 41
        if sr_planets["Uranus"]["house"] == 4:
            dallalat_count += 1
            dallalat_details.append("41. أورانوس في البيت الرابع السنوي (مغادرة مفاجئة للمنزل أو تغيير مسكن قهري).")

        # 42
        if sr_planets["Pluto"]["house"] == 4:
            dallalat_count += 1
            dallalat_details.append("42. بلوتو في البيت الرابع السنوي (أزمات جذرية تهز أساس العائلة والكيان الأسري).")

        # 43
        ruler_4 = SIGN_RULERS[int(sr_cusps[3] / 30)]
        if sr_planets[ruler_4]["house"] in [8, 12]:
            dallalat_count += 1
            dallalat_details.append(f"43. حاكم البيت الرابع ({ruler_4}) في بيت الأزمات (8 أو 12) (تصدع جدران العائلة).")

        # 44
        if sr_planets["Rahu"]["house"] in [8, 12]:
            dallalat_count += 1
            dallalat_details.append("44. راهو في البيت 8 أو 12 السنوي (أسرار مظلمة ومخاوف وجودية متعلقة بالنهايات).")

        # 45
        if get_aspect(sr_planets["Moon"]["lon"], sr_planets["Rahu"]["lon"], orb=6) in ["Conjunction", "Square", "Opposition"]:
            dallalat_count += 1
            dallalat_details.append("45. اتصال سلبي بين القمر وراهو (اضطراب نفسي حاد وهواجس متعلقة بالانفصال).")

        # 46
        if get_aspect(sr_planets["Sun"]["lon"], sr_planets["Rahu"]["lon"], orb=6) in ["Conjunction", "Square", "Opposition"]:
            dallalat_count += 1
            dallalat_details.append("46. اتصال سلبي بين الشمس وراهو (فقدان الاعتبار والتقدير داخل الشراكة).")

        # 47
        if sr_planets["Jupiter"]["house"] in [8, 12]:
            dallalat_count += 1
            dallalat_details.append("47. المشتري في البيت 8 أو 12 السنوي (خسائر مالية كبرى مرتبطة بالطلاق أو تقسيم التركات).")

        # 48
        if get_aspect(sr_planets["Jupiter"]["lon"], sr_planets["Saturn"]["lon"], orb=6) in ["Square", "Opposition"]:
            dallalat_count += 1
            dallalat_details.append("48. تربيع أو مقابلة بين المشتري وزحل (تعارض بين التوسع والقيود، أزمة قانونية وعقود متعثرة).")

        # 49
        if sr_planets["Mercury"]["house"] == 7:
            dallalat_count += 1
            dallalat_details.append("49. عطارد في البيت السابع السنوي (كثرة النقاشات العقيمّة والجدل القانوني المستمر مع الشريك).")

        # 50
        if sr_planets["Sun"]["house"] == 7:
            dallalat_count += 1
            dallalat_details.append("50. الشمس في البيت السابع السنوي بصورة سلبيّة أو محترقة (صراع إرادات وتصادم مباشر لا يمكن التسوية فيه).")

        # الشرط المحدث: تحقق 5 دلالات طلاق فما فوق + تفعيل 1 ميد بوينت على الأقل
        if dallalat_count >= 5 and mp_count >= 1:
            divorce_years.append({
                "year": target_year,
                "age": target_year - birth_date.year,
                "mp_status": mp_status,
                "mp_count": mp_count,
                "dallalat_count": dallalat_count,
                "mp_details": mp_details,
                "details": dallalat_details,
                "expected_months": expected_months_str,
            })

        progress_bar.progress(progress_val)

    # =============================================================================
    # 7. عرض النتائج وتصدير التقرير
    # =============================================================================
    st.subheader(f"السنوات الحرجة المرصودة لـ ({name}) وفقاً لشرط 5 دلالات سنوية وتفعيل ميد بوينت فأكثر:")

    if divorce_years:
        html_content = f"""
        <html dir="rtl" lang="ar">
        <head>
            <meta charset="utf-8">
            <title>تقرير السنوات الحرجة والانفصال (50 دلالة) - {name}</title>
            <style>
                body {{ font-family: 'Cairo', Tahoma, sans-serif; direction: rtl; text-align: right; padding: 30px; background: #f8fafc; color: #1e293b; }}
                h1, h2, h3 {{ color: #b91c1c; }}
                .card {{ background: #fff; border: 1px solid #cbd5e1; padding: 20px; margin-bottom: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
                ul {{ margin-top: 5px; line-height: 1.6; }}
            </style>
        </head>
        <body>
            <h1>تقرير الأزمات الزوجية والطلاق الفلكي الشامل (50 دلالة)</h1>
            <p><strong>الاسم:</strong> {name}</p>
            <p><strong>تاريخ الميلاد:</strong> {birth_date} | <strong>الوقت:</strong> {birth_time}</p>
            <hr>
        """
        for m in divorce_years:
            html_content += f"""
            <div class="card">
                <h3>سنة {m['year']} (العمر: {m['age']} سنة) — التصنيف: {m['mp_status']} | الدلالات: {m['dallalat_count']}/50</h3>
                <p><strong>📅 الأشهر المتوقعة للأزمة أو الانفصال:</strong> {m['expected_months']}</p>
                <p><strong>تفاصيل تفعيل نقاط المنتصف (Midpoints):</strong></p>
                <ul>
            """
            for act in m['mp_details']:
                html_content += f"<li>{act}</li>"
            html_content += """
                </ul>
                <p><strong>دلالات الانفصال والمشاكل المتحققة (من أصل 50):</strong></p>
                <ul>
            """
            for d in m['details']:
                html_content += f"<li>{d}</li>"
            html_content += """
                </ul>
            </div>
            """
        html_content += """
        </body>
        </html>
        """

        st.download_button(
            label="🖨️ تحميل تقرير الأزمات الزوجية (50 دلالة مع الأشهر المتوقعة والميد بوينت) كملف HTML للطباعة",
            data=html_content,
            file_name=f"divorce_report_50_{name.replace(' ', '_')}.html",
            mime="text/html",
        )

        for m in divorce_years:
            with st.expander(f"💥 سنة {m['year']} (العمر: {m['age']} سنة) — التصنيف: [{m['mp_status']}] | عدد الدلالات: ({m['dallalat_count']}/50)"):
                st.error(f"**حالة الميد بوينت:** {m['mp_status']} (تم تفعيل {m['mp_count']} نقاط منتصف)")
                st.info(f"📅 **الأشهر المتوقعة للحدث خلال السنة:** {m['expected_months']}")

                st.write("**تفاصيل تفعيل نقاط المنتصف (أورب < 2° للاقتران والمقابلة فقط):**")
                for act in m["mp_details"]:
                    st.write(f"  * {act}")

                st.markdown("---")
                st.write("**دلالات الانفصال والمشاكل المتحققة في العودة الشمسية:**")
                for d in m["details"]:
                    st.write(f"- {d}")
    else:
        st.success("لم يتم العثور على سنوات تتطابق فيها الشروط الصارمة (تحقق 5 دلالات طلاق فما فوق + تفعيل 1 ميد بوينت على الأقل). الخريطة تشير إلى استقرار تام أو غياب الأزمات المدمرة.")
