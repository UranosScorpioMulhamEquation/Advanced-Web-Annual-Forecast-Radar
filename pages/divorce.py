import datetime
import os
from dataclasses import dataclass
import geonamescache
import pytz
import streamlit as st
import swisseph as swe
from timezonefinder import TimezoneFinder
import uuid

# ==================== 1. Security & License ====================
KEY_FILE = "license.key"

def get_machine_id():
    return hex(uuid.getnode())

def generate_password(mid):
    digits = ''.join(filter(str.isdigit, mid))
    num = int(digits[:8]) if digits else int(mid.encode().hex(), 16)
    return str(round(abs(num / 2 * 3.14)))[:6]

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = os.path.exists(KEY_FILE)

if not st.session_state['authenticated']:
    st.set_page_config(page_title="Security Activation", layout="centered")
    st.title("🔑 Security Activation")
    st.warning("Send your Machine ID to programmer email : mulham81ahmed@gmail.com")

    mid = get_machine_id()
    st.info(f"Machine ID: {mid}")
    pwd = st.text_input("Enter Activation Key:", type="password")
    if st.button("Activate"):
        if pwd == generate_password(mid):
            with open(KEY_FILE, "w") as f: f.write(pwd)
            st.session_state['authenticated'] = True
            st.rerun()
        else:
            st.error("Invalid Activation Key.")
    st.stop()

# ==================== إعدادات Swiss Ephemeris ====================
swe.set_ephe_path('')  # استخدام وضع Moshier الافتراضي للتقويم الفلكي الدقيق
# ==========================================

# 1. إعدادات واجهة المستخدم وتكوين التطبيق
# ==========================================
st.set_page_config(
    page_title="حاسبة الأزمات الزوجية/الشراكات",
    layout="wide",
    page_icon="💔",
)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif;
        direction: rtl;
        text-align: right;
    }
    .main-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 25px;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 25px;
    }
    .stCard {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 15px;
    }
    .badge-health { background-color: #ffcccc; color: #990000; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .badge-career { background-color: #cce5ff; color: #004085; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .badge-family { background-color: #d4edda; color: #155724; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .badge-partner { background-color: #f8d7da; color: #721c24; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .badge-finance { background-color: #fff3cd; color: #856404; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .badge-eco { background-color: #e2e3e5; color: #383d41; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .badge-comprehensive { background-color: #d1ecf1; color: #0c5460; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .badge-popular { background-color: #fce4ec; color: #880e4f; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .badge-military { background-color: #efebe9; color: #3e2723; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    .badge-normal { background-color: #e8f5e9; color: #2e7d32; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. تعريف فئة المدن وتحميل البيانات الجغرافية
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

# ==========================================
# 3. الثوابت الفلكية وحكام البروج
# ==========================================
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
    "Rahu": swe.TRUE_NODE,
    "Chiron": swe.CHIRON,
}

ZODIAC_NAMES = [
    "الحمل",
    "الثور",
    "الجوزاء",
    "السرطان",
    "الأسد",
    "العذراء",
    "الميزان",
    "العقرب",
    "القوس",
    "الجدي",
    "الدلو",
    "الحوت",
]

# حكام البروج (التنجيم الحديث)
SIGN_RULERS = {
    0: "Mars",  # الحمل
    1: "Venus",  # الثور
    2: "Mercury",  # الجوزاء
    3: "Moon",  # السرطان
    4: "Sun",  # الأسد
    5: "Mercury",  # العذراء
    6: "Venus",  # الميزان
    7: "Pluto",  # العقرب
    8: "Jupiter",  # القوس
    9: "Saturn",  # الجدي
    10: "Uranus",  # الدلو
    11: "Neptune",  # الحوت
}


# ==========================================
# 4. الدوال الفلكية والرياضية الأساسية
# ==========================================
def get_utc_julian_day(date_obj, time_obj, tz_str):
    """تحويل الوقت المحلي إلى توقيت جوليان العالمي"""
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


def find_exact_solar_return(
    target_year, natal_sun_lon, birth_month, birth_day, birth_time, b_tz
):
    """حساب العودة الشمسية بدقة متناهية"""
    guess_dt = datetime.datetime(
        target_year, birth_month, birth_day, birth_time.hour, birth_time.minute
    )
    local_tz = pytz.timezone(b_tz)
    utc_dt = local_tz.localize(guess_dt).astimezone(pytz.utc)
    jd_guess = swe.julday(
        utc_dt.year,
        utc_dt.month,
        utc_dt.day,
        utc_dt.hour + utc_dt.minute / 60.0,
    )

    for _ in range(15):
        sun_lon = swe.calc_ut(jd_guess, swe.SUN)[0][0]
        diff = natal_sun_lon - sun_lon
        if diff > 180:
            diff -= 360
        if diff < -180:
            diff += 360
        jd_guess += diff / 0.985647
        if abs(diff) < 0.000001:
            break
    return jd_guess


def get_house_of_planet(p_lon, cusps):
    """حساب البيت الذي يقع فيه الكوكب بناءً على درجات الأوتاد والبيوت"""
    for i in range(12):
        c1 = cusps[i]
        c2 = cusps[(i + 1) % 12]
        if c1 < c2:
            if c1 <= p_lon < c2:
                return i + 1
        else:
            if p_lon >= c1 or p_lon < c2:
                return i + 1
    return 1


def calc_midpoint(p1_lon, p2_lon):
    """حساب نقطة المنتصف رياضياً مع مراعاة الشكل الدائري 360 درجة"""
    mp = (p1_lon + p2_lon) / 2.0
    if abs(p1_lon - p2_lon) > 180:
        mp = (mp + 180) % 360
    return mp


def is_conjunct_cusp(p_lon, cusp_lon, orb=6):
    """
    حساب الاتصال الفعال باستخدام أقصر مسافة على الدائرة.
    الأورب تم تعديله ليكون 6 درجات بناءً على الشروط.
    """
    diff = abs((cusp_lon - p_lon + 180) % 360 - 180)
    return diff <= orb


def get_aspect(lon1, lon2, orb=6):
    """حساب الاتصالات الفلكية الأساسية بين كوكبين بأورب 6 درجات"""
    diff = abs((lon1 - lon2 + 180) % 360 - 180)
    if diff <= orb:
        return "Conjunction"
    if abs(diff - 90) <= orb:
        return "Square"
    if abs(diff - 180) <= orb:
        return "Opposition"
    return None


def check_midpoints_activation(sr_planets, midpoints_dict):
    """
    فحص تفعيل الميد بوينت الميلادية بواسطة الكواكب السنوية.
    الشروط: الفرق الفلكي الصافي أقل من درجتين (diff < 2.0°).
    """
    activated_details = []
    activated_mp_names = set()

    for mp_name, mp_lon in midpoints_dict.items():
        for p_name, p_data in sr_planets.items():
            p_lon = p_data["lon"]
            diff = abs((p_lon - mp_lon + 180) % 360 - 180)
            if diff < 2.0:
                p_sign_idx = int(p_lon / 30)
                activated_details.append(
                    f"تفعيل [{mp_name}] بواسطة {p_name} السنوي ببرج {ZODIAC_NAMES[p_sign_idx]} (فرق: {diff:.2f}°)"
                )
                activated_mp_names.add(mp_name)

    count = len(activated_mp_names)

    if count == 0:
        status = "لا يوجد"
    elif count == 1:
        status = "غضب داخلي"
    elif count == 2:
        status = "مشاكل زوجية/شراكات"
    else:
        status = "طلاق محتمل/قضاء"

    return activated_details, count, status


# ==========================================
# 5. بناء واجهة المستخدم
# ==========================================
st.title("حاسبة الأزمات الزوجية و الطلاق / الشراكات التجارية / القضاء : ميد بوينت - ريجومونتانوس")
st.caption("برمجة و تطوير: الفلكي الدكتور ملهم احمد")
st.markdown("---")

col1, col2, col3 = st.columns(3)

default_b_country_idx = (
    country_list.index("Syria") if "Syria" in country_list else 0
)
default_sr_country_idx = (
    country_list.index("United Arab Emirates")
    if "United Arab Emirates" in country_list
    else 0
)

with col1:
    name = st.text_input("الاسم", "New Name")
    birth_date = st.date_input(
        "تاريخ الميلاد",
        value=datetime.date(2005, 1, 1),
        min_value=datetime.date(1960, 1, 1),
    )
    birth_time = st.time_input(
        "ساعة الميلاد",
        value=datetime.time(12, 0),
        step=datetime.timedelta(minutes=1),
    )

with col2:
    st.markdown("### مكان الميلاد")
    b_country_name = st.selectbox(
        "دولة الميلاد",
        country_list,
        index=default_b_country_idx,
        key="b_country_select",
    )
    b_c_code = country_map[b_country_name]
    b_city_objects = cities_by_country.get(b_c_code, [])
    b_city_names = (
        [c.name for c in b_city_objects]
        if b_city_objects
        else [b_country_name]
    )
    b_city_name = st.selectbox(
        "مدينة الميلاد", b_city_names, index=0, key="b_city_select"
    )

with col3:
    st.markdown("### مكان السنوية (المكان الحالي)")
    sr_country_name = st.selectbox(
        "دولة السنوية",
        country_list,
        index=default_sr_country_idx,
        key="sr_country_select",
    )
    sr_c_code = country_map[sr_country_name]
    sr_city_objects = cities_by_country.get(sr_c_code, [])
    sr_city_names = (
        [c.name for c in sr_city_objects]
        if sr_city_objects
        else [sr_country_name]
    )
    sr_city_name = st.selectbox(
        "مدينة السنوية", sr_city_names, index=0, key="sr_city_select"
    )

submit = st.button("حساب سنوات الانفصال والمشاكل المحتملة", type="primary")

# ==========================================
# 6. المحرك الأساسي ومعالجة البيانات
# ==========================================
if submit:
    b_city_obj = next(
        (c for c in b_city_objects if c.name == b_city_name), None
    )
    sr_city_obj = next(
        (c for c in sr_city_objects if c.name == sr_city_name), None
    )

    b_lat, b_lon = (
        (b_city_obj.latitude, b_city_obj.longitude)
        if b_city_obj
        else (25.2048, 55.2708)
    )
    sr_lat, sr_lon = (
        (sr_city_obj.latitude, sr_city_obj.longitude)
        if sr_city_obj
        else (25.2048, 55.2708)
    )

    tf = TimezoneFinder()
    b_tz = tf.timezone_at(lng=b_lon, lat=b_lat) or "UTC"
    sr_tz = tf.timezone_at(lng=sr_lon, lat=sr_lat) or "UTC"

    jd_birth = get_utc_julian_day(birth_date, birth_time, b_tz)

    # حساب جميع الكواكب الميلادية لتجهيز الميد بوينت
    natal_planets = {}
    for p_name, p_id in PLANETS.items():
        res = swe.calc_ut(jd_birth, p_id)
        natal_planets[p_name] = res[0][0]

    # حساب البيوت الميلادية بنظام ريغومونتانوس (b'R')
    natal_cusps, _ = swe.houses(jd_birth, b_lat, b_lon, b"R")

    # حساب الـ 7 ميد بوينت المرتبطة بالقيود والنهايات (زحل + بقية الكواكب)
    natal_midpoints = {
        "زحل/الزهرة": calc_midpoint(
            natal_planets["Saturn"], natal_planets["Venus"]
        ),
        "زحل/عطارد": calc_midpoint(
            natal_planets["Saturn"], natal_planets["Mercury"]
        ),
        "زحل/القمر": calc_midpoint(
            natal_planets["Saturn"], natal_planets["Moon"]
        ),
        "زحل/المريخ": calc_midpoint(
            natal_planets["Saturn"], natal_planets["Mars"]
        ),
        "زحل/الشمس": calc_midpoint(
            natal_planets["Saturn"], natal_planets["Sun"]
        ),
        "زحل/أورانوس": calc_midpoint(
            natal_planets["Saturn"], natal_planets["Uranus"]
        ),
        "زحل/بلوتو": calc_midpoint(
            natal_planets["Saturn"], natal_planets["Pluto"]
        ),
    }

    st.info(
        "تم حساب المواقع الميلادية ونقاط المنتصف السبعة (المقترنة بزحل) بنجاح. جاري فحص العبور السنوي..."
    )

    start_year = birth_date.year + 18
    end_year = birth_date.year + 60
    years_list = list(range(start_year, end_year + 1))
    total_years = len(years_list)

    divorce_years = []
    progress_bar = st.progress(0.0)

    for i, target_year in enumerate(years_list):
        progress_val = min(1.0, (i + 1) / total_years)

        jd_sr = find_exact_solar_return(
            target_year,
            natal_planets["Sun"],
            birth_date.month,
            birth_date.day,
            birth_time,
            b_tz,
        )

        # حساب البيوت السنوية بنظام ريغومونتانوس (b'R')
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

        rahu_lon = sr_planets["Rahu"]["lon"]
        ketu_lon = (rahu_lon + 180) % 360
        sr_planets["Ketu"] = {
            "lon": ketu_lon,
            "sign": int(ketu_lon / 30),
            "house": get_house_of_planet(ketu_lon, sr_cusps),
            "is_retro": True,
        }

        # 1. فحص تفعيل الميد بوينت بنفس البرج وبفرق أقل من درجتين
        mp_details, mp_count, mp_status = check_midpoints_activation(
            sr_planets, natal_midpoints
        )

        if mp_count == 0:
            progress_bar.progress(progress_val)
            continue

        # ==========================================
        # 2. تقييم دلالات الطلاق والانفصال السنوية الشاملة (25 دلالة من التنجيم الغربي)
        # ==========================================
        dallalat_details = []
        dallalat_count = 0

        ruler_7 = SIGN_RULERS[int(sr_cusps[6] / 30)]
        ruler_1 = SIGN_RULERS[int(sr_cusps[0] / 30)]

        # دلالة 1: طالع السنوية في بيوت النهايات والأزمات الميلادية (8 أو 12)
        sr_asc_in_natal = get_house_of_planet(sr_asc, natal_cusps)
        if sr_asc_in_natal in [8, 12]:
            dallalat_count += 1
            dallalat_details.append(
                f"1. طالع العودة الشمسية يقع في **البيت {sr_asc_in_natal} الميلادي** (بيت النهايات والأزمات)."
            )

        # دلالة 2: البيت السابع السنوي يقع في بيوت الخسائر الميلادية (8 أو 12)
        sr_h7_in_natal = get_house_of_planet(sr_cusps[6], natal_cusps)
        if sr_h7_in_natal in [8, 12]:
            dallalat_count += 1
            dallalat_details.append(
                f"2. البيت السابع السنوي يقع في **البيت {sr_h7_in_natal} الميلادي** (تحولات كبرى في الشراكة)."
            )

        # دلالة 3: أورانوس السنوي في البيت السابع
        if sr_planets["Uranus"]["house"] == 7:
            dallalat_count += 1
            dallalat_details.append(
                "3. أورانوس السنوي في **البيت 7** (مؤشر قوي للقطيعة المفاجئة والتمرد/الانفصال)."
            )

        # دلالة 4: زحل السنوي في البيت السابع
        if sr_planets["Saturn"]["house"] == 7:
            dallalat_count += 1
            dallalat_details.append(
                "4. زحل السنوي في **البيت 7** (برود عاطفي، جفاء، ومسؤوليات ثقيلة تهدد العلاقة)."
            )

        # دلالة 5: بلوتو السنوي في البيت السابع
        if sr_planets["Pluto"]["house"] == 7:
            dallalat_count += 1
            dallalat_details.append(
                "5. بلوتو السنوي في **البيت 7** (صراعات سيطرة، طلاق قسري، وهدم أركان الشراكة)."
            )

        # دلالة 6: المريخ السنوي في البيت السابع
        if sr_planets["Mars"]["house"] == 7:
            dallalat_count += 1
            dallalat_details.append(
                "6. المريخ السنوي في **البيت 7** (نزاعات حادة، مشادات، ومعارك قانونية مع الشريك)."
            )

        # دلالة 7: الزهرة في بيوت الخسارة والتهميش (8 أو 12)
        if sr_planets["Venus"]["house"] in [8, 12]:
            dallalat_count += 1
            dallalat_details.append(
                f"7. الزهرة غارقة في **البيت {sr_planets['Venus']['house']} السنوي** (فقدان الشغف، أحزان عاطفية، أو علاقات خفية)."
            )

        # دلالة 8: القمر في حالة حرجة (البيت 8 أو 12 أو برج العقرب)
        if (
            sr_planets["Moon"]["house"] in [8, 12]
            or sr_planets["Moon"]["sign"] == 7
        ):
            dallalat_count += 1
            dallalat_details.append(
                f"8. القمر السنوي في وضع حرج (البيت {sr_planets['Moon']['house']} / العقرب) - اضطراب وحزن عاطفي عميق."
            )

        # دلالة 9: الشمس السنوية في بيوت الضغوط والنهايات (8 أو 12)
        if sr_planets["Sun"]["house"] in [8, 12]:
            dallalat_count += 1
            dallalat_details.append(
                f"9. الشمس السنوية في **البيت {sr_planets['Sun']['house']}** (استنزاف الهوية الزوجية وضغوط نفسية شديدة)."
            )

        # دلالة 10: حاكم البيت السابع السنوي في بيت الخسارة (8 أو 12)
        if sr_planets[ruler_7]["house"] in [8, 12]:
            dallalat_count += 1
            dallalat_details.append(
                f"10. حاكم السابع السنوي ({ruler_7}) في **البيت {sr_planets[ruler_7]['house']}** (ضعف الشريك أو ابتعاده)."
            )

        # دلالة 11: حاكم البيت السابع السنوي متراجع (Retrograde)
        if sr_planets[ruler_7]["is_retro"]:
            dallalat_count += 1
            dallalat_details.append(
                f"11. حاكم البيت السابع السنوي ({ruler_7}) **متراجع** (تردد، إعادة نظر في الزواج، أو تراجع الشريك)."
            )

        # دلالة 12: حاكم طالع السنوية متراجع أو في بيوت الخسارة (8 أو 12)
        if sr_planets[ruler_1]["is_retro"] or sr_planets[ruler_1]["house"] in [
            8,
            12,
        ]:
            dallalat_count += 1
            dallalat_details.append(
                f"12. حاكم الطالع السنوي ({ruler_1}) **ضعيف/متراجع/بالبيت {sr_planets[ruler_1]['house']}** (عجز عن المواصلة أو رغبة بالانسحاب)."
            )

        # دلالة 13: تربيع أو مقابلة بين المريخ والزهرة (أورب ≤ 6°)
        if get_aspect(
            sr_planets["Mars"]["lon"], sr_planets["Venus"]["lon"], orb=6
        ) in ["Square", "Opposition"]:
            dallalat_count += 1
            dallalat_details.append(
                "13. اتصال نحس (تربيع/مقابلة) بين **المريخ والزهرة** (تصادم الرغبات، وانفجار الخلافات الزوجية)."
            )

        # دلالة 14: تربيع أو مقابلة بين زحل والزهرة (أورب ≤ 6°)
        if get_aspect(
            sr_planets["Saturn"]["lon"], sr_planets["Venus"]["lon"], orb=6
        ) in ["Square", "Opposition"]:
            dallalat_count += 1
            dallalat_details.append(
                "14. اتصال نحس (تربيع/مقابلة) بين **زحل والزهرة** (برود عاطفي شديد وشعور بالرفض والحرمان)."
            )

        # دلالة 15: تربيع أو مقابلة بين أورانوس والزهرة (أورب ≤ 6°)
        if get_aspect(
            sr_planets["Uranus"]["lon"], sr_planets["Venus"]["lon"], orb=6
        ) in ["Square", "Opposition"]:
            dallalat_count += 1
            dallalat_details.append(
                "15. اتصال نحس (تربيع/مقابلة) بين **أورانوس والزهرة** (صدمة عاطفية ورغبة مفاجئة في القطيعة)."
            )

        # دلالة 16: تربيع أو مقابلة بين بلوتو والزهرة (أورب ≤ 6°)
        if get_aspect(
            sr_planets["Pluto"]["lon"], sr_planets["Venus"]["lon"], orb=6
        ) in ["Square", "Opposition"]:
            dallalat_count += 1
            dallalat_details.append(
                "16. اتصال نحس (تربيع/مقابلة) بين **بلوتو والزهرة** (غيرة مرضية، شكوك، وهدم متبادل للعلاقة)."
            )

        # دلالة 17: تربيع أو مقابلة بين زحل والقمر (أورب ≤ 6°)
        if get_aspect(
            sr_planets["Saturn"]["lon"], sr_planets["Moon"]["lon"], orb=6
        ) in ["Square", "Opposition"]:
            dallalat_count += 1
            dallalat_details.append(
                "17. اتصال نحس (تربيع/مقابلة) بين **زحل والقمر** (حزن نفسي عميق وإحباط في الحياة العائلية)."
            )

        # دلالة 18: تربيع أو مقابلة بين أورانوس والقمر (أورب ≤ 6°)
        if get_aspect(
            sr_planets["Uranus"]["lon"], sr_planets["Moon"]["lon"], orb=6
        ) in ["Square", "Opposition"]:
            dallalat_count += 1
            dallalat_details.append(
                "18. اتصال نحس (تربيع/مقابلة) بين **أورانوس والقمر** (تقلبات مزاجية حادة وزعزعة الاستقرار المنزلي)."
            )

        # دلالة 19: تربيع أو مقابلة بين المريخ والقمر (أورب ≤ 6°)
        if get_aspect(
            sr_planets["Mars"]["lon"], sr_planets["Moon"]["lon"], orb=6
        ) in ["Square", "Opposition"]:
            dallalat_count += 1
            dallalat_details.append(
                "19. اتصال نحس (تربيع/مقابلة) بين **المريخ والقمر** (حدّة انفعالية، مشاجرات عائلية، وغضب مكتوم)."
            )

        # دلالة 20: العقدتان (راهو/كيتو) في محور البيت 1 / 7
        if sr_planets["Rahu"]["house"] in [1, 7] or sr_planets["Ketu"][
            "house"
        ] in [1, 7]:
            dallalat_count += 1
            dallalat_details.append(
                "20. العقد القمرية (**راهو/كيتو**) على محور الطالع/السابع (مصيرية في الشراكة وتغيير العهد الزوجي)."
            )

        # دلالة 21: كيرون في البيت السابع السنوي
        if sr_planets["Chiron"]["house"] == 7:
            dallalat_count += 1
            dallalat_details.append(
                "21. **كيرون** في البيت 7 السنوي (جراح عاطفية عميقة وصعوبة في مداواة الخلاف الزوجي)."
            )

        # دلالة 22: تجمع اثنين أو أكثر من الكواكب النحسة في البيت 7
        malefics_in_7th = [
            p
            for p in ["Saturn", "Mars", "Uranus", "Pluto"]
            if sr_planets[p]["house"] == 7
        ]
        if len(malefics_in_7th) >= 2:
            dallalat_count += 1
            dallalat_details.append(
                f"22. تجمع نحس متعدد في البيت 7: (**{', '.join(malefics_in_7th)}**)."
            )

        # دلالة 23: هيمنة الكواكب النحسة على الأوتاد السنوية (1، 4، 7، 10)
        malefics_in_angles = [
            p
            for p in ["Saturn", "Mars", "Uranus", "Pluto"]
            if sr_planets[p]["house"] in [1, 4, 7, 10]
        ]
        if len(malefics_in_angles) >= 3:
            dallalat_count += 1
            dallalat_details.append(
                "23. هيمنة نحسة مكثفة على الأوتاد السنوية (أكثر من 3 كواكب شديدة التأثير)."
            )

        # دلالة 24: اقتران الكواكب النحسة بأوتاد السنوية (أورب ≤ 6 درجات)
        target_malefics = ["Uranus", "Saturn", "Pluto", "Mars"]
        target_cusps = [
            sr_cusps[0],
            sr_cusps[3],
            sr_cusps[6],
            sr_cusps[9],
        ]  # 1, 4, 7, 10
        cusp_contacts = []

        for p_name in target_malefics:
            p_lon = sr_planets[p_name]["lon"]
            for cusp_idx, cusp in enumerate(target_cusps):
                if is_conjunct_cusp(p_lon, cusp, orb=6):
                    h_num = (
                        1
                        if cusp_idx == 0
                        else (4 if cusp_idx == 1 else (7 if cusp_idx == 2 else 10))
                    )
                    cusp_contacts.append(f"{p_name} مع وِتْد البيت {h_num}")
                    break

        if cusp_contacts:
            dallalat_count += 1
            dallalat_details.append(
                f"24. اقتران كواكب الهدم بأوتاد السنوية (أورب ≤ 6°): ({', '.join(cusp_contacts)})."
            )

        # دلالة 25: اقتران حاكم البيت السابع بأحد الكواكب النحسة (أورب ≤ 6°)
        conj_ruler7_malefic = [
            p
            for p in ["Saturn", "Mars", "Uranus", "Pluto"]
            if p != ruler_7
            and get_aspect(
                sr_planets[ruler_7]["lon"], sr_planets[p]["lon"], orb=6
            )
            == "Conjunction"
        ]
        if conj_ruler7_malefic:
            dallalat_count += 1
            dallalat_details.append(
                f"25. حاكم السابع ({ruler_7}) مقترن بكوكب نحس (**{', '.join(conj_ruler7_malefic)}**) (ضغط وتضرر مباشر للشريك)."
            )

        # 3. الفلترة النهائية: تحقق 4 دلالات فما فوق من أصل 25 مع وجود تفعيل للميد بوينت
        if dallalat_count >= 4:
            divorce_years.append({
                "year": target_year,
                "age": target_year - birth_date.year,
                "mp_status": mp_status,
                "mp_count": mp_count,
                "dallalat_count": dallalat_count,
                "mp_details": mp_details,
                "details": dallalat_details,
            })

        progress_bar.progress(progress_val)

    # ==========================================
    # 7. عرض النتائج النهائية
    # ==========================================
    st.subheader(
        "السنوات الحرجة (تحقق 4 دلالات طلاق فما فوق من أصل 25 + تفعيل للميد بوينت):"
    )

    if divorce_years:
        for m in divorce_years:
            emoji = (
                "⚠"
                if m["mp_count"] == 1
                else ("🚨" if m["mp_count"] == 2 else "💥")
            )

            with st.expander(
                f"{emoji} سنة {m['year']} (العمر: {m['age']} سنة) - الحالة: [{m['mp_status']}] | دلالات: ({m['dallalat_count']}/25)"
            ):
                st.error(
                    f"**التصنيف بناءً على الميد بوينت:** {m['mp_status']} (تم تفعيل {m['mp_count']} ميد بوينت)"
                )

                st.write("**تفاصيل التفعيل الدقيق للميد بوينت (فرق < 2°):**")
                for act in m["mp_details"]:
                    st.write(f"  * {act}")

                st.markdown("---")
                st.write(
                    "**دلالات الانفصال والمشاكل المتحققة في العودة الشمسية:**"
                )
                for d in m["details"]:
                    st.write(f"- {d}")
    else:
        st.success(
            "لم يتم العثور على سنوات تتطابق فيها الشروط (4 دلالات طلاق فما فوق + تفعيل ميد بوينت الخلافات)."
        )
