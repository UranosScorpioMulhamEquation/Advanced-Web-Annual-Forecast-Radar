import os
from datetime import datetime, date, time
from typing import Dict, List, Tuple, Any, Optional

import geonamescache
import pandas as pd
import pytz
import streamlit as st
import swisseph as swe
from timezonefinder import TimezoneFinder

# ==============================================================================
# 0. تهيئة الصفحة، التنسيق البصري (CSS)، ومسار ملفات الـ Ephemeris
# ==============================================================================
st.set_page_config(
    page_title="النظام المتقدم لتنجيم الحدث العاطفي | أسترو رادار",
    page_icon="💖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# حقن تنسيقات CSS احترافية لدعم الاتجاه من اليمين لليسار وتحسين البطاقات
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Cairo', 'Tahoma', sans-serif;
    }
    .astro-card {
        background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%);
        border-right: 5px solid #8e24aa;
        padding: 18px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.06);
        margin-bottom: 15px;
    }
    .astro-card h4 {
        color: #4a148c;
        margin-top: 0;
        margin-bottom: 10px;
    }
    .badge-pos {
        background-color: #e8f5e9;
        color: #2e7d32;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.85em;
    }
    .badge-neg {
        background-color: #ffebee;
        color: #c62828;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.85em;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

EPHE_PATH = "./ephe"
if not os.path.exists(EPHE_PATH):
    os.makedirs(EPHE_PATH)
swe.set_ephe_path(EPHE_PATH)

# ==============================================================================
# 1. وحدة الخدمات الجغرافية والزمنية (Geo & Timezone Engine)
# ==============================================================================
@st.cache_data
def load_geo_data() -> Tuple[Dict[str, str], List[str], Dict[str, List[Dict[str, Any]]]]:
    """تحميل بيانات الدول والمدن وترتيبها حسب الكثافة السكانية."""
    gc = geonamescache.GeonamesCache()
    countries = gc.get_countries()
    cities = gc.get_cities()

    country_map = {c["name"]: code for code, c in countries.items()}
    sorted_countries = sorted(list(country_map.keys()))

    cities_by_country: Dict[str, List[Dict[str, Any]]] = {}
    for c_code in country_map.values():
        c_cities = [city for city in cities.values() if city["countrycode"] == c_code]
        cities_by_country[c_code] = sorted(
            c_cities, key=lambda x: x["population"], reverse=True
        )

    return country_map, sorted_countries, cities_by_country


@st.cache_resource
def get_tz_finder() -> TimezoneFinder:
    """تهيئة محرك البحث عن المناطق الزمنية."""
    return TimezoneFinder()


def get_utc_julian_day(date_obj: date, time_obj: time, tz_str: str) -> Tuple[float, datetime]:
    """
    تحويل التاريخ والوقت المحلي إلى التوقيت العالمي (UTC) ثم إلى اليوم اليولياني (JD)
    مع معالجة التوقيت الصيفي (DST) بدقة.
    """
    local_tz = pytz.timezone(tz_str)
    naive_dt = datetime.combine(date_obj, time_obj)
    try:
        local_dt = local_tz.localize(naive_dt, is_dst=None)
    except pytz.AmbiguousTimeError:
        local_dt = local_tz.localize(naive_dt, is_dst=False)
    except pytz.NonExistentTimeError:
        local_dt = local_tz.localize(naive_dt, is_dst=True)

    utc_dt = local_dt.astimezone(pytz.utc)
    decimal_hour = (
        utc_dt.hour
        + (utc_dt.minute / 60.0)
        + (utc_dt.second / 3600.0)
    )
    jd = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, decimal_hour)
    return jd, utc_dt


country_map, country_list, cities_by_country = load_geo_data()
tf = get_tz_finder()

# ==============================================================================
# 2. القواميس والثوابت الفلكية (Astrological Constants & Classical Rulers)
# ==============================================================================
SIGN_NAMES = [
    "الحمل", "الثور", "الجوزاء", "السرطان", "الأسد", "العذراء",
    "الميزان", "العقرب", "القوس", "الجدي", "الدلو", "الحوت"
]

SIGN_SYMBOLS = ["♈", "♉", "♊", "♋", "♌", "♍", "♎", "♏", "♐", "♑", "♒", "♓"]

SIGN_MODALITY = {
    "الحمل": "منقلب", "الثور": "ثابت", "الجوزاء": "ذو جسدين",
    "السرطان": "منقلب", "الأسد": "ثابت", "العذراء": "ذو جسدين",
    "الميزان": "منقلب", "العقرب": "ثابت", "القوس": "ذو جسدين",
    "الجدي": "منقلب", "الدلو": "ثابت", "الحوت": "ذو جسدين"
}

# الأرباب الكلاسيكيون السبعة المعتمدون في التنجيم الساعي وتنجيم الحدث
RULERS = {
    "الحمل": "المريخ", "الثور": "الزهرة", "الجوزاء": "عطارد",
    "السرطان": "القمر", "الأسد": "الشمس", "العذراء": "عطارد",
    "الميزان": "الزهرة", "العقرب": "المريخ", "القوس": "المشتري",
    "الجدي": "زحل", "الدلو": "زحل", "الحوت": "المشتري"
}

EVENT_TYPES = {
    "1 - حدث فراق (Separation)": "فراق",
    "2 - حدث لقاء (Meeting)": "لقاء",
    "3 - حدث مشاجرة (Dispute/Fight)": "مشاجرة",
    "4 - حدث عدم تواصل مؤقت / انسحاب (Withdrawal)": "انسحاب"
}

# ==============================================================================
# 3. الدوال الحسابية الفلكية (Astronomical Calculation Engine)
# ==============================================================================
def get_sign_info(lon_deg: float) -> Tuple[str, float, str]:
    """استخراج اسم البرج، الدرجة داخله، ورمزه من الطول البروجي (0 - 360)."""
    lon_deg = lon_deg % 360.0
    sign_idx = int(lon_deg // 30)
    deg_in_sign = lon_deg % 30.0
    return SIGN_NAMES[sign_idx], deg_in_sign, SIGN_SYMBOLS[sign_idx]


def format_deg_min(deg_float: float) -> str:
    """تنسيق الدرجات العشرية إلى درجات ودقائق قوسية."""
    d = int(deg_float)
    m = int((deg_float - d) * 60)
    return f"{d:02d}° {m:02d}'"


def calculate_planetary_positions(jd: float) -> Dict[str, Dict[str, Any]]:
    """حساب مواقع الكواكب والعقد القمرية والكويكبات العاطفية مع دعم Fallback."""
    bodies = {
        "الشمس": swe.SUN,
        "القمر": swe.MOON,
        "عطارد": swe.MERCURY,
        "الزهرة": swe.VENUS,
        "المريخ": swe.MARS,
        "المشتري": swe.JUPITER,
        "زحل": swe.SATURN,
        "أورانوس": swe.URANUS,
        "نبتون": swe.NEPTUNE,
        "بلوتو": swe.PLUTO,
        "الرأس (العقدة الشمالية)": swe.MEAN_NODE,
        "تشيرون (Chiron)": swe.CHIRON,
    }

    ast_offset = getattr(swe, "SE_AST_OFFSET", 10000)
    asteroids = {
        "إيروس (Eros)": ast_offset + 433,
        "بسايكي (Psyche)": ast_offset + 16,
    }

    planet_data: Dict[str, Dict[str, Any]] = {}
    calc_flags = swe.FLG_SWIEPH | swe.FLG_SPEED

    for name, body_id in {**bodies, **asteroids}.items():
        try:
            res, _ = swe.calc_ut(jd, body_id, calc_flags)
        except swe.Error:
            try:
                # التراجع التلقائي إلى خوارزمية Moshier المدمجة إذا لم تتوفر ملفات ephe
                res, _ = swe.calc_ut(jd, body_id, swe.FLG_MOSEPH | swe.FLG_SPEED)
            except swe.Error:
                continue

        lon_val = res[0] % 360.0
        speed_val = res[3]
        sign_name, deg_in_sign, symbol = get_sign_info(lon_val)

        planet_data[name] = {
            "lon": lon_val,
            "sign": sign_name,
            "symbol": symbol,
            "deg": deg_in_sign,
            "deg_formatted": format_deg_min(deg_in_sign),
            "retro": speed_val < 0,
            "speed": speed_val,
        }

    # إضافة الذنب (العقدة الجنوبية) بدقة 180 درجة مقابل الرأس
    if "الرأس (العقدة الشمالية)" in planet_data:
        rahu = planet_data["الرأس (العقدة الشمالية)"]
        ketu_lon = (rahu["lon"] + 180.0) % 360.0
        k_sign, k_deg, k_sym = get_sign_info(ketu_lon)
        planet_data["الذنب (العقدة الجنوبية)"] = {
            "lon": ketu_lon,
            "sign": k_sign,
            "symbol": k_sym,
            "deg": k_deg,
            "deg_formatted": format_deg_min(k_deg),
            "retro": rahu["retro"],
            "speed": rahu["speed"],
        }

    return planet_data


def calculate_houses_regiomontanus(
    jd: float, lat: float, lon: float
) -> Tuple[List[float], float, float]:
    """حساب أوتاد ورؤوس البيوت الاثني عشر بنظام ريغومونتانوس (Regiomontanus)."""
    houses_cusps, ascmc = swe.houses_ex(jd, lat, lon, b"R")
    asc_lon = ascmc[0] % 360.0
    mc_lon = ascmc[1] % 360.0

    # تأمين استخراج 12 بيتاً بغض النظر عن إصدار pyswisseph
    if len(houses_cusps) >= 13:
        cusps = [c % 360.0 for c in houses_cusps[1:13]]
    else:
        cusps = [c % 360.0 for c in houses_cusps[:12]]

    return cusps, asc_lon, mc_lon


def assign_planets_to_houses(
    planet_data: Dict[str, Dict[str, Any]], cusps: List[float]
) -> None:
    """تحديد البيت الفلكي لكل كوكب بدقة مع معالجة عبور نقطة الصفر الحمل (0° Aries)."""
    for p_name, info in planet_data.items():
        p_lon = info["lon"] % 360.0
        assigned_house = 1
        for i in range(12):
            c_start = cusps[i]
            c_end = cusps[(i + 1) % 12]
            if c_start < c_end:
                if c_start <= p_lon < c_end:
                    assigned_house = i + 1
                    break
            else:
                if p_lon >= c_start or p_lon < c_end:
                    assigned_house = i + 1
                    break
        info["house"] = assigned_house


def check_aspect(
    p1_name: str, p2_name: str, planet_data: Dict[str, Dict[str, Any]]
) -> Tuple[bool, Optional[str], Optional[str], float, Optional[str]]:
    """
    فحص الاتصالات الفلكية الرئيسية مع حساب الدلتا الزمنية (Delta-Time)
    لتحديد ما إذا كان الاتصال تقاربياً (Applying) أم منفصلاً (Separating).
    """
    if p1_name not in planet_data or p2_name not in planet_data:
        return False, None, None, 0.0, None

    lon1 = planet_data[p1_name]["lon"]
    lon2 = planet_data[p2_name]["lon"]
    speed1 = planet_data[p1_name]["speed"]
    speed2 = planet_data[p2_name]["speed"]

    diff = abs(lon1 - lon2) % 360.0
    if diff > 180.0:
        diff = 360.0 - diff

    aspects_def = [
        ("اقتران (Conjunction)", 0.0, 7.0, "positive"),
        ("تثليث (Trine)", 120.0, 6.5, "positive"),
        ("تسديس (Sextile)", 60.0, 5.5, "positive"),
        ("تربيع (Square)", 90.0, 6.5, "negative"),
        ("مقابلة (Opposition)", 180.0, 7.0, "negative"),
    ]

    for asp_name, target_angle, max_orb, asp_type in aspects_def:
        orb = abs(diff - target_angle)
        if orb <= max_orb:
            dt = 0.01  # خطوة زمنية صغيرة باليوم لاختبار التقارب والانفصال
            f_lon1 = (lon1 + speed1 * dt) % 360.0
            f_lon2 = (lon2 + speed2 * dt) % 360.0
            f_diff = abs(f_lon1 - f_lon2) % 360.0
            if f_diff > 180.0:
                f_diff = 360.0 - f_diff
            f_orb = abs(f_diff - target_angle)

            status = "Applying" if f_orb < orb else "Separating"
            return True, asp_name, asp_type, orb, status

    return False, None, None, 0.0, None


# ==============================================================================
# 4. الواجهة الرئيسية والشريط الجانبي (Streamlit UI & Sidebar)
# ==============================================================================
st.title("💖 النظام المتقدم لتحليل خارطة الحدث العاطفي")
st.markdown(
    "محرك فلكي احترافي يعمل وفق **نظام بيوت ريغومونتانوس** والأصول الكلاسيكية لتشخيص أحداث الفراق، اللقاء، المشاجرات، والانسحاب المؤقت."
)
st.markdown("---")

st.sidebar.header("⚙️ بيانات لحظة الحدث العاطفي")

client_ref = st.sidebar.text_input("اسم العميل أو رمز الحالة:", value="حالة استشارية")

selected_event_key = st.sidebar.selectbox(
    "اختر طبيعة الحدث العاطفي:", list(EVENT_TYPES.keys())
)
event_purpose = EVENT_TYPES[selected_event_key]

now_local = datetime.now()
ev_date = st.sidebar.date_input(
    "تاريخ وقوع الحدث:",
    value=now_local.date(),
    min_value=date(1800, 1, 1),
    max_value=date(2100, 12, 31),
)

st.sidebar.markdown("🕒 **وقت وقوع الحدث (بالتوقيت المحلي للمكان):**")
col_h, col_m, col_s = st.sidebar.columns(3)
with col_h:
    ev_hour = st.number_input("الساعة", min_value=0, max_value=23, value=now_local.hour, step=1)
with col_m:
    ev_minute = st.number_input("الدقيقة", min_value=0, max_value=59, value=now_local.minute, step=1)
with col_s:
    ev_second = st.number_input("الثانية", min_value=0, max_value=59, value=now_local.second, step=1)

ev_time = time(int(ev_hour), int(ev_minute), int(ev_second))

st.sidebar.markdown("---")
st.sidebar.subheader("🌍 الموقع الجغرافي للحدث")

use_manual_coords = st.sidebar.checkbox("إدخال الإحداثيات يدوياً (خط الطول والعرض)", value=False)

if not use_manual_coords:
    default_country_idx = (
        country_list.index("United Arab Emirates")
        if "United Arab Emirates" in country_list
        else 0
    )
    selected_country_name = st.sidebar.selectbox(
        "اختر الدولة:", country_list, index=default_country_idx
    )
    country_code = country_map[selected_country_name]
    country_cities = cities_by_country.get(country_code, [])
    city_names = [c["name"] for c in country_cities]

    if city_names:
        selected_city_name = st.sidebar.selectbox("اختر المدينة:", city_names)
        selected_city = next(
            (c for c in country_cities if c["name"] == selected_city_name),
            country_cities[0],
        )
        lat = float(selected_city["latitude"])
        lon = float(selected_city["longitude"])
        location_label = f"{selected_city_name}، {selected_country_name}"
    else:
        lat, lon = 25.2048, 55.2708
        location_label = selected_country_name
    tz_str = tf.timezone_at(lng=lon, lat=lat) or "UTC"
else:
    lat = st.sidebar.number_input("خط العرض (Latitude):", value=25.2048, min_value=-90.0, max_value=90.0, format="%.4f")
    lon = st.sidebar.number_input("خط الطول (Longitude):", value=55.2708, min_value=-180.0, max_value=180.0, format="%.4f")
    detected_tz = tf.timezone_at(lng=lon, lat=lat) or "UTC"
    tz_str = st.sidebar.text_input("المنطقة الزمنية (Timezone):", value=detected_tz)
    location_label = f"إحداثيات مخصصة ({lat:.2f}, {lon:.2f})"

st.sidebar.info(f"📍 **الموقع:** {location_label}\n\n🌐 **الإحداثيات:** {lat:.4f}°, {lon:.4f}°\n\n🕰️ **المنطقة الزمنية:** `{tz_str}`")

# ==============================================================================
# 5. تشغيل المحرك التحليلي وعرض النتائج
# ==============================================================================
if st.button("🔮 استخراج وتحليل خريطة الحدث العاطفي", type="primary", use_container_width=True):
    try:
        jd, utc_dt = get_utc_julian_day(ev_date, ev_time, tz_str)
    except Exception as e:
        st.error(f"حدث خطأ أثناء تحويل التوقيت المحلي إلى UTC: {e}")
        st.stop()

    planet_data = calculate_planetary_positions(jd)
    cusps, asc_lon, mc_lon = calculate_houses_regiomontanus(jd, lat, lon)
    assign_planets_to_houses(planet_data, cusps)

    asc_sign, asc_deg, asc_sym = get_sign_info(asc_lon)
    desc_sign, desc_deg, desc_sym = get_sign_info(cusps[6])
    mc_sign, mc_deg, mc_sym = get_sign_info(mc_lon)

    party1_ruler = RULERS[asc_sign]
    party2_ruler = RULERS[desc_sign]

    st.success(
        f"✅ تم بناء الخريطة الفلكية بنجاح | التوقيت العالمي (UTC): **{utc_dt.strftime('%Y-%m-%d %H:%M:%S')}** | اليوم اليولياني: **{jd:.5f}**"
    )

    # بطاقات المؤشرات الرئيسية (Metrics)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("الطالع (الطرف الأول)", f"{asc_sym} {asc_sign}", format_deg_min(asc_deg))
    m2.metric("حاكم الطرف الأول", party1_ruler, f"البيت {planet_data[party1_ruler]['house']} ({planet_data[party1_ruler]['sign']})")
    m3.metric("السابع (الشريك)", f"{desc_sym} {desc_sign}", format_deg_min(desc_deg))
    m4.metric("حاكم الشريك", party2_ruler, f"البيت {planet_data[party2_ruler]['house']} ({planet_data[party2_ruler]['sign']})")

    st.markdown("---")

    # عرض تفصيلي للطرفين
    col1, col2 = st.columns(2)
    with col1:
        p1_info = planet_data[party1_ruler]
        moon_info = planet_data["القمر"]
        st.markdown(
            f"""
            <div class="astro-card">
                <h4>🧑 دلالات الطرف الأول (صاحب الحدث / الطالع)</h4>
                <p><strong>برج الطالع:</strong> {asc_sign} ({format_deg_min(asc_deg)})</p>
                <p><strong>الدليل الرئيسي ({party1_ruler}):</strong> في برج {p1_info['sign']} ({p1_info['deg_formatted']}) - البيت {p1_info['house']} {'(متراجع 🔄)' if p1_info['retro'] else '(مستقيم ➡️)'}</p>
                <p><strong>القمر (الحالة النفسية والمشاعر):</strong> في برج {moon_info['sign']} ({moon_info['deg_formatted']}) - البيت {moon_info['house']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        p2_info = planet_data[party2_ruler]
        venus_info = planet_data["الزهرة"]
        st.markdown(
            f"""
            <div class="astro-card">
                <h4>👩‍❤️‍👨 دلالات الطرف الثاني (الشريك / البيت السابع)</h4>
                <p><strong>رأس البيت السابع:</strong> {desc_sign} ({format_deg_min(desc_deg)})</p>
                <p><strong>الدليل الرئيسي ({party2_ruler}):</strong> في برج {p2_info['sign']} ({p2_info['deg_formatted']}) - البيت {p2_info['house']} {'(متراجع 🔄)' if p2_info['retro'] else '(مستقيم ➡️)'}</p>
                <p><strong>الزهرة (دلالة المودة والجاذبية):</strong> في برج {venus_info['sign']} ({venus_info['deg_formatted']}) - البيت {venus_info['house']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ==========================================================================
    # محرك الاتصالات والتشخيص الديناميكي للأسباب
    # ==========================================================================
    has_aspect, asp_name, asp_type, asp_orb, asp_status = check_aspect(
        party1_ruler, party2_ruler, planet_data
    )
    has_moon_asp, moon_asp_name, moon_asp_type, moon_orb, moon_status = check_aspect(
        "القمر", party2_ruler, planet_data
    )
    has_mars_p1, mars_asp1, mars_type1, _, _ = check_aspect(
        "المريخ", party1_ruler, planet_data
    )
    has_mars_p2, mars_asp2, mars_type2, _, _ = check_aspect(
        "المريخ", party2_ruler, planet_data
    )

    st.markdown("### 🔬 محرك التشخيص الفلكي الدقيق لأسباب الحدث")
    detailed_causes = []

    # تحليل ديناميكي بناءً على مواقع الكواكب واتصالاتها الفعلية
    if has_aspect:
        status_ar = "تقاربي ومنطبق (يتجه للذروة)" if asp_status == "Applying" else "منفصل (وقع تأثيره للتو)"
        detailed_causes.append({
            "category": "العلاقة المباشرة بين الدليلين",
            "desc": f"يوجد اتصال ({asp_name}) بأورب {asp_orb:.2f}° وهو اتصال {status_ar} بين {party1_ruler} و{party2_ruler}."
        })
    else:
        detailed_causes.append({
            "category": "انقطاع الاتصال المباشر",
            "desc": f"عدم وجود اتصال هندسي رئيسي مباشر حالياً بين {party1_ruler} و{party2_ruler}، مما يشير إلى فجوة في التواصل أو اختلاف في الأولويات اللحظية."
        })

    if event_purpose == "لقاء":
        if not planet_data["عطارد"]["retro"]:
            detailed_causes.append({
                "category": "جودة الحوار والتفاهم",
                "desc": f"عطارد مستقيم في برج {planet_data['عطارد']['sign']} (البيت {planet_data['عطارد']['house']})، مما يدعم وضوح الحوار وتبادل الأفكار بسلاسة."
            })
        else:
            detailed_causes.append({
                "category": "استحضار الماضي",
                "desc": "تراجع عطارد لحظة اللقاء يشير إلى مناقشة ملفات سابقة أو إعادة تقييم مواقف قديمة."
            })
        if "إيروس (Eros)" in planet_data:
            eros = planet_data["إيروس (Eros)"]
            detailed_causes.append({
                "category": "الكيمياء العاطفية (إيروس)",
                "desc": f"يتواجد كويكب إيروس في برج {eros['sign']} بالبيت {eros['house']}، محدداً طابع الانجذاب والشغف في هذا اللقاء."
            })

    elif event_purpose == "مشاجرة":
        mars_info = planet_data["المريخ"]
        detailed_causes.append({
            "category": "بؤرة التوتر والانفعال (المريخ)",
            "desc": f"المريخ يتواجد في برج {mars_info['sign']} بالبيت {mars_info['house']}، مما يفسر حدة ردود الفعل وسرعة الاشتعال اللفظي."
        })
        if (has_mars_p1 and mars_type1 == "negative") or (has_mars_p2 and mars_type2 == "negative"):
            detailed_causes.append({
                "category": "ضغط مريخي مباشر",
                "desc": "وجود اتصال توتر (تربيع أو مقابلة) من المريخ لأحد الدليلين يؤكد أن الخلاف ناتج عن اندفاع أو عناد لحظي."
            })

    elif event_purpose == "انسحاب":
        saturn_info = planet_data["زحل"]
        detailed_causes.append({
            "category": "الحاجة للعزلة والحدود (زحل)",
            "desc": f"موقع زحل في برج {saturn_info['sign']} (البيت {saturn_info['house']}) يعكس رغبة في وضع حدود مؤقتة والتقاط الأنفاس بعيداً عن الضغوط."
        })

    else:  # فراق
        if planet_data[party2_ruler]["house"] in [6, 8, 12]:
            detailed_causes.append({
                "category": "موقع الشريك في بيت ساقط",
                "desc": f"تواجد حاكم الشريك ({party2_ruler}) في البيت {planet_data[party2_ruler]['house']} يعكس حالة من الانشغال الداخلي أو التراجع عن المواجهة."
            })
        if has_aspect and asp_type == "negative":
            detailed_causes.append({
                "category": "تصادم الرؤى",
                "desc": f"وجود {asp_name} بين الدليلين يوضح أن قرار الابتعاد جاء بعد احتكاك أو تعارض واضح في التوقعات."
            })

    for cause in detailed_causes:
        st.markdown(f"- **{cause['category']}:** {cause['desc']}")

    # ==========================================================================
    # تحليل الأطراف الثالثة (البيوت 5، 11، 12)
    # ==========================================================================
    st.markdown("---")
    st.markdown("### 👥 فحص تدخل الأطراف الثالثة والمحيط الخارجي")

    third_parties_found = []
    target_tp_houses = {
        5: ("طرف عاطفي منافس أو جاذبية خارجية (البيت 5)", "وجود كواكب متصلة بسلبية من البيت الخامس يشير إلى تشتت الانتباه العاطفي."),
        12: ("أسرار خفية أو وشاية غير معلنة (البيت 12)", "كواكب البيت الثاني عشر المتصلة بالدليلين تكشف عن مخاوف مكتومة أو تأثير من خلف الكواليس."),
        11: ("ضغط الأصدقاء أو المحيط الاجتماعي (البيت 11)", "تأثير آراء المحيطين أو الأصدقاء المشتركين على مجرى العلاقة.")
    }

    excluded_bodies = {party1_ruler, party2_ruler, "الشمس", "القمر", "الرأس (العقدة الشمالية)", "الذنب (العقدة الجنوبية)"}

    for h_num, (tp_title, tp_desc) in target_tp_houses.items():
        h_planets = [
            p for p, info in planet_data.items()
            if info["house"] == h_num and p not in excluded_bodies
        ]
        if h_planets:
            confirmed_planets = []
            for hp in h_planets:
                asp1, _, t1, _, _ = check_aspect(hp, party1_ruler, planet_data)
                asp2, _, t2, _, _ = check_aspect(hp, party2_ruler, planet_data)
                if (asp1 and t1 == "negative") or (asp2 and t2 == "negative"):
                    confirmed_planets.append(hp)

            if confirmed_planets:
                third_parties_found.append(
                    (tp_title, f"{tp_desc} الكواكب المتصلة بضغط: ({', '.join(confirmed_planets)}).")
                )

    if third_parties_found:
        st.warning("⚠️ **تم رصد مؤشرات فلكية مؤكدة لتدخل أو تأثير خارجي:**")
        for tp_title, tp_desc in third_parties_found:
            st.markdown(f"- **{tp_title}:** {tp_desc}")
    else:
        st.success("✅ الخريطة خالية من أي تدخل مؤكد لأطراف ثالثة؛ ديناميكية الحدث محصورة بين الطرفين فقط.")

    # ==========================================================================
    # تحليل إمكانية العودة والزمن المتوقع (Reconciliation & Timing)
    # ==========================================================================
    can_return = False
    return_reasons = []
    timing_res = "غير محدد حالياً"

    if event_purpose in ["فراق", "انسحاب", "مشاجرة"]:
        st.markdown("---")
        st.markdown("### 🔄 تقييم إمكانية عودة التواصل والصلح (Reconciliation)")

        # 1. تراجع حاكم الشريك أو الطرف الأول
        if planet_data[party2_ruler]["retro"]:
            can_return = True
            return_reasons.append(
                f"تراجع حاكم الشريك ({party2_ruler}) في برج {planet_data[party2_ruler]['sign']} يُعد من أقوى الدلالات الكلاسيكية على إعادة النظر والرجوع."
            )

        # 2. اتصال تقاربي إيجابي بين الدليلين
        if has_aspect and asp_type == "positive" and asp_status == "Applying":
            can_return = True
            return_reasons.append(
                f"وجود اتصال إيجابي تقاربي ({asp_name}) بين {party1_ruler} و{party2_ruler} يمهد لتجدد التواصل."
            )

        # 3. اتصال القمر التقاربي الإيجابي بحاكم الشريك
        if has_moon_asp and moon_asp_type == "positive" and moon_status == "Applying":
            can_return = True
            return_reasons.append(
                f"القمر ينقل النور ويصنع اتصالاً إيجابياً مقبلاً ({moon_asp_name}) مع {party2_ruler}."
            )

        # 4. الاستقبال المتبادل (Mutual Reception)
        p1_sign = planet_data[party1_ruler]["sign"]
        p2_sign = planet_data[party2_ruler]["sign"]
        if RULERS.get(p1_sign) == party2_ruler and RULERS.get(p2_sign) == party1_ruler:
            can_return = True
            return_reasons.append(
                f"وجود **استقبال متبادل (Mutual Reception)** بين {party1_ruler} و{party2_ruler} يدل على بقاء المودة والرغبة المشتركة رغم الخلاف."
            )

        if can_return:
            st.success("🌟 **مؤشرات العودة والتواصل: إيجابية وواردة وفق المعطيات الفلكية!**")
            for rr in return_reasons:
                st.markdown(f"- {rr}")

            def calculate_precise_timing(orb_val: float, house_num: int, sign_name: str) -> str:
                mod = SIGN_MODALITY.get(sign_name, "منقلب")
                is_angular = house_num in [1, 4, 7, 10]
                is_succedent = house_num in [2, 5, 8, 11]

                if is_angular and mod == "منقلب":
                    unit = "أيام (وتيرة سريعة)"
                elif (is_angular and mod == "ذو جسدين") or (is_succedent and mod == "منقلب"):
                    unit = "أسابيع (وتيرة متوسطة)"
                elif mod == "ثابت":
                    unit = "أشهر (وتيرة بطيئة وتدريجية)"
                else:
                    unit = "أسابيع إلى أشهر"

                est_num = max(1, round(orb_val))
                return f"حوالي {est_num} {unit} (بناءً على زاوية الانطباق Orb: {orb_val:.2f}°)"

            if has_moon_asp and moon_asp_type == "positive" and moon_status == "Applying":
                timing_res = calculate_precise_timing(
                    moon_orb, planet_data["القمر"]["house"], planet_data["القمر"]["sign"]
                )
            elif has_aspect and asp_type == "positive" and asp_status == "Applying":
                timing_res = calculate_precise_timing(
                    asp_orb, planet_data[party1_ruler]["house"], planet_data[party1_ruler]["sign"]
                )
            else:
                timing_res = "مرتبط بانتهاء فترة تراجع الكوكب أو تغير حركته"

            st.info(f"⏳ **الإطار الزمني المقدر للتحرك أو التواصل:** {timing_res}")
        else:
            st.error("🛑 **مؤشرات العودة والتواصل: ضعيفة أو متوقفة في المدى القريب.**")
            st.markdown(
                "- غياب الاتصالات التقاربية الإيجابية بين الأدلة الرئيسية يشير إلى ثبات الوضع الراهن وحاجة الطرفين لفترة هدوء أطول."
            )

    # ==========================================================================
    # جدول مواقع الكواكب والبيوت الكامل
    # ==========================================================================
    st.markdown("---")
    with st.expander("🪐 عرض الجدول الفلكي التفصيلي للكواكب والبيوت (Ephemeris Table)", expanded=False):
        table_rows = []
        for name, info in planet_data.items():
            table_rows.append({
                "الجرم السماوي": name,
                "البرج": f"{info['symbol']} {info['sign']}",
                "الدرجة": info["deg_formatted"],
                "البيت (ريغومونتانوس)": f"البيت {info['house']}",
                "الحركة": "متراجع (R)" if info["retro"] else "مستقيم (D)",
                "السرعة اليومية": f"{info['speed']:.4f}°",
            })
        df_planets = pd.DataFrame(table_rows)
        st.dataframe(df_planets, use_container_width=True, hide_index=True)

    # ==========================================================================
    # 6. توليد وتصدير تقرير HTML الاحترافي الجذاب للطباعة
    # ==========================================================================
    st.markdown("---")
    st.markdown("### 🖨️ تصدير التقرير الفلكي الاحترافي (HTML)")

    causes_html = "".join(
        [f"<li><strong>{c['category']}:</strong> {c['desc']}</li>" for c in detailed_causes]
    )
    tp_html = (
        "".join([f"<li><strong>{title}:</strong> {desc}</li>" for title, desc in third_parties_found])
        if third_parties_found
        else "<li>الخريطة خالية من أي تدخل مؤكد لأطراف ثالثة؛ الحدث ثنائي وبحت.</li>"
    )

    planets_table_html = "".join(
        [
            f"""
            <tr>
                <td><strong>{name}</strong></td>
                <td>{info['symbol']} {info['sign']}</td>
                <td>{info['deg_formatted']}</td>
                <td>البيت {info['house']}</td>
                <td>{'<span class="badge-retro">متراجع</span>' if info['retro'] else '<span class="badge-direct">مستقيم</span>'}</td>
            </tr>
            """
            for name, info in planet_data.items()
        ]
    )

    return_badge = (
        '<span class="status-yes">واردة وإيجابية</span>'
        if can_return
        else '<span class="status-no">ضعيفة حالياً</span>'
    )

    return_section_html = (
        f"""
        <div class="section-card highlight-box">
            <h3>🔄 تحليل إمكانية العودة والتواصل والزمن المتوقع</h3>
            <p><strong>تقييم العودة:</strong> {return_badge}</p>
            <p><strong>الإطار الزمني المقدر:</strong> {timing_res}</p>
            <ul>
                {"".join([f"<li>{rr}</li>" for rr in return_reasons]) if return_reasons else "<li>لا توجد اتصالات تقاربية إيجابية نشطة حالياً بين الدليلين.</li>"}
            </ul>
        </div>
        """
        if event_purpose in ["فراق", "انسحاب", "مشاجرة"]
        else ""
    )

    html_report = f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>التقرير الفلكي للحدث العاطفي - {client_ref}</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
            body {{
                font-family: 'Cairo', 'Tahoma', Arial, sans-serif;
                background-color: #f4f6f9;
                color: #2c3e50;
                margin: 0;
                padding: 30px 15px;
                line-height: 1.8;
            }}
            .report-wrapper {{
                max-width: 900px;
                margin: auto;
                background: #ffffff;
                border-radius: 16px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
                overflow: hidden;
                border: 1px solid #e1e8ed;
            }}
            .header-banner {{
                background: linear-gradient(135deg, #4a148c 0%, #880e4f 100%);
                color: #ffffff;
                padding: 35px 30px;
                text-align: center;
            }}
            .header-banner h1 {{
                margin: 0 0 10px 0;
                font-size: 26px;
                font-weight: 700;
            }}
            .header-banner p {{
                margin: 5px 0;
                font-size: 14px;
                opacity: 0.9;
            }}
            .meta-bar {{
                display: flex;
                flex-wrap: wrap;
                justify-content: space-between;
                background-color: #f8f9fa;
                padding: 15px 30px;
                border-bottom: 1px solid #e9ecef;
                font-size: 14px;
            }}
            .content-body {{
                padding: 30px;
            }}
            .grid-2 {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-bottom: 25px;
            }}
            .section-card {{
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-right: 5px solid #6a1b9a;
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 20px;
            }}
            .section-card h3 {{
                color: #4a148c;
                margin-top: 0;
                font-size: 18px;
                border-bottom: 1px solid #f1f5f9;
                padding-bottom: 8px;
            }}
            .highlight-box {{
                background-color: #fdf8ff;
                border-right-color: #ad1457;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
                font-size: 14px;
            }}
            th {{
                background-color: #4a148c;
                color: #ffffff;
                padding: 10px;
                text-align: right;
            }}
            td {{
                padding: 10px;
                border-bottom: 1px solid #edf2f7;
            }}
            tr:nth-child(even) {{
                background-color: #f8fafc;
            }}
            .status-yes {{
                background-color: #d4edda;
                color: #155724;
                padding: 4px 12px;
                border-radius: 20px;
                font-weight: bold;
            }}
            .status-no {{
                background-color: #f8d7da;
                color: #721c24;
                padding: 4px 12px;
                border-radius: 20px;
                font-weight: bold;
            }}
            .badge-retro {{
                color: #c62828;
                font-weight: bold;
            }}
            .badge-direct {{
                color: #2e7d32;
            }}
            .footer {{
                text-align: center;
                padding: 20px;
                background-color: #f8f9fa;
                color: #718096;
                font-size: 12px;
                border-top: 1px solid #e2e8f0;
            }}
            @media print {{
                body {{ background: #fff; padding: 0; }}
                .report-wrapper {{ box-shadow: none; border: none; }}
            }}
        </style>
    </head>
    <body>
        <div class="report-wrapper">
            <div class="header-banner">
                <h1>💖 التقرير الفلكي المتقدم لتحليل خريطة الحدث العاطفي</h1>
                <p>منظومة أسترو رادار الفلكية | حسابات الإيفيميريس الدقيقة ونظام بيوت ريغومونتانوس</p>
            </div>

            <div class="meta-bar">
                <div><strong>الحالة / المرجع:</strong> {client_ref}</div>
                <div><strong>نوع الحدث:</strong> {selected_event_key}</div>
                <div><strong>التاريخ والوقت المحلي:</strong> {ev_date} | {ev_time}</div>
                <div><strong>المكان:</strong> {location_label} ({tz_str})</div>
            </div>

            <div class="content-body">
                <div class="grid-2">
                    <div class="section-card">
                        <h3>🧑 الطرف الأول (الطالع)</h3>
                        <p><strong>الطالع:</strong> {asc_sym} {asc_sign} ({format_deg_min(asc_deg)})</p>
                        <p><strong>حاكم الطالع:</strong> {party1_ruler} في {planet_data[party1_ruler]['sign']} (البيت {planet_data[party1_ruler]['house']})</p>
                        <p><strong>القمر (المشاعر):</strong> {planet_data['القمر']['sign']} (البيت {planet_data['القمر']['house']})</p>
                    </div>
                    <div class="section-card">
                        <h3>👩‍❤️‍👨 الطرف الثاني (الشريك / السابع)</h3>
                        <p><strong>رأس السابع:</strong> {desc_sym} {desc_sign} ({format_deg_min(desc_deg)})</p>
                        <p><strong>حاكم السابع:</strong> {party2_ruler} في {planet_data[party2_ruler]['sign']} (البيت {planet_data[party2_ruler]['house']})</p>
                        <p><strong>الزهرة (الحب):</strong> {planet_data['الزهرة']['sign']} (البيت {planet_data['الزهرة']['house']})</p>
                    </div>
                </div>

                <div class="section-card">
                    <h3>⚙️ التشخيص الفلكي الدقيق لأسباب الحدث</h3>
                    <ul>{causes_html}</ul>
                </div>

                <div class="section-card">
                    <h3>👥 فحص الأطراف الثالثة والمحيط</h3>
                    <ul>{tp_html}</ul>
                </div>

                {return_section_html}

                <div class="section-card">
                    <h3>🪐 جدول المواقع الفلكية الكاملة لحظة الحدث</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>الجرم السماوي</th>
                                <th>البرج</th>
                                <th>الدرجة</th>
                                <th>البيت</th>
                                <th>الحركة</th>
                            </tr>
                        </thead>
                        <tbody>
                            {planets_table_html}
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="footer">
                تم توليد هذا التقرير آلياً عبر محرك الحسابات الفلكية المتقدم (Swiss Ephemeris - Regiomontanus Houses). للطباعة اضغط Ctrl+P.
            </div>
        </div>
    </body>
    </html>
    """

    st.download_button(
        label="📥 تحميل التقرير الفلكي الاحترافي للطباعة (HTML)",
        data=html_report,
        file_name=f"Emotional_Event_Report_{client_ref.replace(' ', '_')}_{ev_date}.html",
        mime="text/html",
        use_container_width=True,
    )
