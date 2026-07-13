from __future__ import annotations
import html
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import NamedTuple
from functools import lru_cache
import traceback

import geonamescache
import libephemeris as swe
from timezonefinder import TimezoneFinder
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import os
import streamlit as st

# ==================== إعدادات الصفحة ودعم العربية (Streamlit) ====================
st.set_page_config(page_title="رادار التوقعات المتقدم", page_icon="🔮", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
html, body, [class*="css"] {
    direction: rtl;
    text-align: right;
    font-family: 'Cairo', sans-serif;
}
.stDownloadButton button {
    background-color: #2e7d32 !important;
    color: white !important;
}
.stButton button {
    background-color: #6D28D9;
    color: white;
}
</style>
""", unsafe_allow_html=True)

# ==================== 1. Security & Paths (Mobile Optimized) ====================
# تحديد مجلد التطبيق لضمان صلاحيات القراءة والكتابة
# تم وضع try/except لضمان عمله في بيئات السيرفرات (Windows/Linux) بجانب الأندرويد
APP_DIR = "/storage/emulated/0/Download/Astro"
try:
    os.makedirs(APP_DIR, exist_ok=True)
except Exception:
    APP_DIR = os.getcwd() # كبديل آمن إذا تم تشغيله خارج الأندرويد

# ==================== إعدادات libephemeris ====================
swe.set_ephe_path(APP_DIR)

# ==================== البيانات والثوابت ====================
class City(NamedTuple):
    geonameid: str
    name: str
    country_code: str
    latitude: float
    longitude: float
    admin1: str
    population: int

@dataclass
class USMRow:
    age: int
    risk_date: date
    status: str
    homo_deviation: float
    eris_deviation: float
    neptune_deviation: float

@dataclass
class SolarChart:
    birth_local: datetime
    return_local: datetime
    solar_asc_deg: float
    solar_mc_deg: float
    solar_asc_sign: str
    planet_rows: list[dict]
    house_system: str = "Whole Sign (كل برج بيت)"

# ==================== تحميل البيانات الجغرافية ====================

@st.cache_data # تم استبدال lru_cache بـ cache_data لتلائم ستريملايت وتمنع التعليق
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

# ==================== الحسابات الفلكية ====================

def zodiac_info(longitude: float) -> tuple[str, int, float]:
    signs = ["الحمل", "الثور", "الجوزاء", "السرطان", "الأسد", "العذراء",
             "الميزان", "العقرب", "القوس", "الجدي", "الدلو", "الحوت"]
    sign_idx = int((longitude % 360) / 30)
    degree = (longitude % 30)
    return signs[sign_idx], sign_idx, degree

def find_solar_return_exact(birth_jd_utc: float, target_year: int) -> float:
    natal_sun_lon = swe.calc_ut(birth_jd_utc, swe.SUN)[0][0]
    jd_start = swe.julday(target_year, 1, 1, 0.0)
    jd_end = swe.julday(target_year, 12, 31, 23.999)
    
    for _ in range(50):
        jd_mid = (jd_start + jd_end) / 2.0
        mid_sun_lon = swe.calc_ut(jd_mid, swe.SUN)[0][0]
        diff = (mid_sun_lon - natal_sun_lon) % 360
        if diff > 180: diff -= 360
        if diff < 0: jd_start = jd_mid
        else: jd_end = jd_mid
            
    return (jd_start + jd_end) / 2.0

def calculate_chart(birth_date: date, birth_time_input, birth_city: City, return_city: City, target_year: int) -> SolarChart:
    is_unknown_time = (birth_time_input == "الساعة غير معروفة")
    actual_time = time(12, 0) if is_unknown_time else birth_time_input

    birth_tz_name = get_timezone_for_city(birth_city)
    return_tz_name = get_timezone_for_city(return_city)
    
    birth_tz = ZoneInfo(birth_tz_name) if birth_tz_name else timezone.utc
    return_tz = ZoneInfo(return_tz_name) if return_tz_name else timezone.utc
    
    birth_local = datetime.combine(birth_date, actual_time, tzinfo=birth_tz)
    birth_utc = birth_local.astimezone(timezone.utc)
    birth_jd_utc = swe.julday(birth_utc.year, birth_utc.month, birth_utc.day, birth_utc.hour + birth_utc.minute/60.0 + birth_utc.second/3600.0)
    
    return_jd_utc = find_solar_return_exact(birth_jd_utc, target_year)
    y, m, d, h_float = swe.revjul(return_jd_utc)
    hours = int(h_float)
    minutes = int((h_float - hours) * 60)
    seconds = int((((h_float - hours) * 60) - minutes) * 60)
    
    return_local = datetime(y, m, d, hours, minutes, seconds, tzinfo=timezone.utc).astimezone(return_tz)
    
    cusps, ascmc = swe.houses_ex(return_jd_utc, return_city.latitude, return_city.longitude, b'W')
    solar_asc_deg, solar_mc_deg = ascmc[0], ascmc[1]
    asc_sign_name, asc_sign_idx, _ = zodiac_info(solar_asc_deg)
    house_system_name = "Whole Sign (كل برج بيت)"

    if is_unknown_time:
        sun_coords, _ = swe.calc_ut(return_jd_utc, swe.SUN)
        sun_lon_deg = sun_coords[0]
        sun_sign_name, sun_sign_idx, _ = zodiac_info(sun_lon_deg)
        
        asc_sign_name = f"{sun_sign_name} (طالع شمسي افتراضي)"
        asc_sign_idx = sun_sign_idx 
        solar_asc_deg = sun_lon_deg 
        house_system_name = "Solar Sign (البيوت الشمسية)"

    planets_to_calc = {
        "الشمس": swe.SUN, "القمر": swe.MOON, "عطارد": swe.MERCURY,
        "الزهرة": swe.VENUS, "المريخ": swe.MARS, "المشتري": swe.JUPITER, 
        "زحل": swe.SATURN, "أورانوس": swe.URANUS, "نبتون": swe.NEPTUNE,
        "بلوتو": swe.PLUTO
    }
    
    planet_rows = []
    for name, p_id in planets_to_calc.items():
        coords, _ = swe.calc_ut(return_jd_utc, p_id)
        lon_deg, speed = coords[0], coords[3]
        sign_name, sign_idx, deg_rem = zodiac_info(lon_deg)
        
        house_num = ((sign_idx - asc_sign_idx) % 12) + 1
        
        planet_rows.append({
            "الكوكب": name,
            "الموقع": f"{sign_name} {deg_rem:.2f}°",
            "البيت": str(house_num),
            "الحركة": "متراجع" if speed < 0 else "مباشر",
            "درجة_البرج": deg_rem,
            "الطول_المطلق": lon_deg
        })
        
    return SolarChart(birth_local, return_local, solar_asc_deg, solar_mc_deg, asc_sign_name, planet_rows, house_system=house_system_name)

# ==================== محرك USM ====================

def run_usm_engine_daily(birth_date: date) -> list[USMRow]:
    homo_k, eris_k, neptune_k, tolerance = 6.18, 9.3, 10.77, 0.3
    results = []
    for i in range(1, 85):
        h_dev, e_dev, n_dev = abs((i/homo_k)-round(i/homo_k)), abs((i/eris_k)-round(i/eris_k)), abs((i/neptune_k)-round(i/neptune_k))
        status = "CRITICAL" if (h_dev <= tolerance and e_dev <= tolerance and n_dev <= tolerance) else "Normal"
        results.append(USMRow(age=i, risk_date=date(birth_date.year + i, 1, 1), status=status, homo_deviation=h_dev, eris_deviation=e_dev, neptune_deviation=n_dev))
    return results

# ==================== التقييم الديناميكي للبيوت ====================

houses_meaning_global = {
    "1": "ذاتك، هويتك، وطابعك العام", "2": "ممتلكاتك ومواردك المالية",
    "3": "تواصلك ومحيطك القريب", "4": "الأساسيات، السكن، والوضع الداخلي",
    "5": "إبداعك، المشاريع الخاصة، والأبناء/العاطفة", "6": "صحتك، العمل الروتيني، والخدمات",
    "7": "شراكاتك، العقود، والآخرين", "8": "أموال الشراكات، الأزمات، والتحول العميق",
    "9": "السفر، التوسع الخارجي، والمعتقدات", "10": "السمعة، المكانة الاجتماعية، والقرارات",
    "11": "التحالفات، العلاقات الاجتماعية، والأهداف", "12": "الأسرار، العزلة، وما خلف الكواليس"
}

def evaluate_houses(chart: SolarChart) -> dict:
    house_evals = {str(i): {"score": 0, "planets": [], "status": ""} for i in range(1, 13)}
    
    planet_weights = {
        "المشتري": 2, "الزهرة": 2, "الشمس": 1, "القمر": 1, "عطارد": 1,
        "المريخ": -2, "زحل": -2, "بلوتو": -2, "أورانوس": -1, "نبتون": -1
    }
    
    for row in chart.planet_rows:
        p_name = row["الكوكب"]
        h_num = row["البيت"]
        house_evals[h_num]["planets"].append(p_name)
        house_evals[h_num]["score"] += planet_weights.get(p_name, 0)
        
    for h_num, data in house_evals.items():
        if len(data["planets"]) == 0:
            data["status"] = "مستقر (فارغ من الكواكب السنوية، ليس محور ضغط هذا العام)"
        elif data["score"] >= 2:
            data["status"] = "ممتاز وداعم جداً (وفرة وفرص)"
        elif data["score"] == 1:
            data["status"] = "جيد (حركة نشطة وإيجابية)"
        elif data["score"] == 0:
            data["status"] = "مختلط (يحمل فرصاً وتحديات في نفس الوقت)"
        elif data["score"] == -1:
            data["status"] = "متقلب (يحتاج للتركيز والتعامل بحذر مع المفاجآت أو الضبابية)"
        else:
            data["status"] = "مليء بالتحديات والضغوط (يتطلب الصبر والحكمة في القرارات)"
            
    return house_evals

def generate_dynamic_predictions(chart: SolarChart) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    planets_meaning = {
        "الشمس": "تسليط الضوء، الشهرة، والوضوح التام",
        "القمر": "تقلبات وتغييرات مزاجية أو حالة من عدم الاستقرار",
        "عطارد": "تواصل ذكي، حركة سريعة، وتحليل منطقي",
        "الزهرة": "تجميل، تسهيلات، وتدفق مالي مريح",
        "المريخ": "تحدي، تنافس، طاقة عالية، ومواجهات",
        "المشتري": "وفرة، توسع، حظوظ، وتسهيل في الأمور",
        "زحل": "عراقيل، تقليص، صعوبات، وضرورة الصبر على التأخيرات",
        "أورانوس": "تغييرات مفاجئة، تمرد، والتعامل مع التكنولوجيا والوسائل الحديثة",
        "نبتون": "ضبابية، إلهام عالي، أو حيرة وعدم وضوح في الرؤية",
        "بلوتو": "تحول جذري، إنهاء مرحلة وبدء أخرى بقوة وعمق"
    }
    
    short_meanings = {
        "الشمس": "الشهرة والوضوح", "القمر": "المشاعر والتقلبات", 
        "عطارد": "التفكير والتواصل", "الزهرة": "المال والعلاقات", 
        "المريخ": "الطاقة والتحديات", "المشتري": "التوسع والوفرة", 
        "زحل": "المسؤولية والعراقيل", "أورانوس": "المفاجآت والتغيير", 
        "نبتون": "الإلهام والضبابية", "بلوتو": "التحول الجذري"
    }
    
    house_predictions = []
    for row in chart.planet_rows:
        planet, house, deg_rem = row["الكوكب"], row["البيت"], row["درجة_البرج"]
        
        if planet in planets_meaning and house in houses_meaning_global:
            title = f"{planet} في البيت {house} السنوي"
            desc = f"دلالة على حدوث **{planets_meaning[planet]}** فيما يخص **{houses_meaning_global[house]}**."
            
            if 0.0 <= deg_rem <= 0.99:
                desc += f"<br><span style='color:#d32f2f;'>⚠️ <b>تنشيط مكثف:</b> الكوكب يقترن ببداية البيت ({deg_rem:.2f}°)، مما يجعل تأثيره ملحوظاً جداً هذا العام!</span>"
            elif 29.0 <= deg_rem <= 29.99:
                next_house = str(int(house) + 1) if int(house) < 12 else "1"
                desc += f"<br><span style='color:#d32f2f;'>⚠️ <b>انتقال طاقة:</b> الكوكب في الدرجة ({deg_rem:.2f}°) يقترن بوتد البيت التالي ({next_house})، وينقل تأثيره إليه بقوة.</span>"
                
            house_predictions.append((title, desc))

    aspect_predictions = []
    orb = 6.0 
    num_planets = len(chart.planet_rows)
    
    for i in range(num_planets):
        for j in range(i + 1, num_planets):
            p1, p2 = chart.planet_rows[i], chart.planet_rows[j]
            lon1, lon2 = p1["الطول_المطلق"], p2["الطول_المطلق"]
            
            diff = abs(lon1 - lon2)
            if diff > 180:
                diff = 360 - diff
                
            aspect_name, aspect_effect = "", ""
            
            if diff <= orb:
                aspect_name, aspect_effect = "اقتران (0°)", "تنشيط مكثف ودمج قوي"
            elif abs(diff - 60) <= orb:
                aspect_name, aspect_effect = "تسديس (60°)", "انسجام وفرص مدعومة"
            elif abs(diff - 90) <= orb:
                aspect_name, aspect_effect = "تربيع (90°)", "تحديات وضغوط تحتاج لقرارات"
            elif abs(diff - 120) <= orb:
                aspect_name, aspect_effect = "تثليث (120°)", "تدفق إيجابي وتسهيلات"
            elif abs(diff - 180) <= orb:
                aspect_name, aspect_effect = "مقابلة (180°)", "مواجهة وشد وجذب يتطلب التوازن"
                
            if aspect_name:
                title = f"{aspect_name} بين {p1['الكوكب']} و {p2['الكوكب']}"
                mean1, mean2 = short_meanings.get(p1['الكوكب'], ''), short_meanings.get(p2['الكوكب'], '')
                desc = f"تتفاعل طاقة **[{mean1}]** المتركزة في (البيت {p1['البيت']}) مع طاقة **[{mean2}]** في (البيت {p2['البيت']}). هذا يخلق حالة من **{aspect_effect}** بين مجالات هذين البيتين."
                aspect_predictions.append((title, desc))
                
    return house_predictions, aspect_predictions

# ==================== التقرير HTML والواجهة ====================

def build_report_html(personal_info: dict, chart: SolarChart, usm_row: USMRow, house_evals: dict, house_preds: list, aspect_preds: list) -> str:
    usm_status_text = "⚠️ حرجة (سنة مفصلية تحمل تحولات هامة)" if usm_row.status == "CRITICAL" else "✅ اعتيادية (مسار طبيعي ومستقر نسبياً)"
    info_html = f"""
    <table class="info-table">
        <tr><th>الاسم</th><td>{html.escape(personal_info['name'])}</td><th>الجنس / النوع</th><td>{html.escape(personal_info['gender'])}</td></tr>
        <tr><th>تاريخ الميلاد</th><td>{personal_info['dob']}</td><th>ساعة الميلاد</th><td>{personal_info['time']}</td></tr>
        <tr><th>دولة/مدينة الميلاد</th><td>{html.escape(personal_info['birth_place'])}</td><th>سنة التوقع</th><td>{personal_info['target_year']}</td></tr>
        <tr><th>حالة السنة (Mulham Radar)</th><td colspan="3"><b>{usm_status_text}</b></td></tr>
        <tr><th>طالع السنوية</th><td>{chart.solar_asc_sign}</td><th>نظام البيوت</th><td>{chart.house_system}</td></tr>
    </table>
    """

    eval_html = ""
    for h_num in range(1, 13):
        h_str = str(h_num)
        data = house_evals[h_str]
        planets_str = "، ".join(data["planets"]) if data["planets"] else "فارغ"
        eval_html += f"""
        <div class="house-summary">
            <span class="house-title">البيت {h_num} ({houses_meaning_global[h_str]}):</span> 
            <span class="house-status">{data['status']}</span> 
            <div class="house-planets">الكواكب المتواجدة: {planets_str}</div>
        </div>
        """

    h_html = "".join(f'<div class="prediction"><b>{html.escape(t)}</b><br>{d}</div>' for t, d in house_preds)
    a_html = "".join(f'<div class="prediction aspect"><b>{html.escape(t)}</b><br>{d}</div>' for t, d in aspect_preds)
    rows = "".join(f'<tr><td>{html.escape(r["الكوكب"])}</td><td>{html.escape(r["الموقع"])}</td><td>{html.escape(r["البيت"])}</td><td>{html.escape(r["الحركة"])}</td></tr>' for r in chart.planet_rows)
    
    return f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>تقرير {html.escape(personal_info['name'])} — {personal_info['target_year']}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
body {{ font-family: 'Cairo', sans-serif; background: #f5f5f5; margin: 0; padding: 20px; color: #333; line-height: 1.8; }}
.container {{ max-width: 950px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
h1 {{ color: #1a1a1a; border-bottom: 3px solid #6D28D9; padding-bottom: 10px; text-align: center; }}
h2 {{ color: #4b1a9e; margin-top: 35px; border-bottom: 2px solid #eee; padding-bottom: 5px; }}
.info-table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; background: #fafafa; border-radius: 8px; overflow: hidden; }}
.info-table th, .info-table td {{ padding: 12px; border: 1px solid #ddd; text-align: right; font-size: 15px; }}
.info-table th {{ background: #f0ebf8; color: #4b1a9e; width: 20%; }}
.house-summary {{ background: #fff; padding: 12px; margin: 8px 0; border: 1px solid #e0e0e0; border-right: 4px solid #6D28D9; border-radius: 4px; }}
.house-title {{ font-weight: bold; color: #1a1a1a; }}
.house-status {{ font-weight: bold; color: #d32f2f; margin-right: 10px; }}
.house-planets {{ font-size: 14px; color: #555; margin-top: 5px; }}
.prediction {{ background: #fafafa; padding: 15px; margin: 15px 0; border-radius: 6px; border-right: 4px solid #6D28D9; border: 1px solid #eee; }}
.aspect {{ border-right-color: #00796b; background: #f4fbfb; }}
table.astro-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 15px; text-align: right; }}
table.astro-table th, table.astro-table td {{ padding: 12px; border-bottom: 1px solid #eee; }}
table.astro-table th {{ background: #6D28D9; color: white; }}
table.astro-table tr:hover {{ background-color: #f9f9f9; }}
</style></head><body><div class="container">
<h1>التقرير الفلكي الشامل - السنوية ({personal_info['target_year']})</h1>
{info_html}

<h2>ملخص حالة البيوت الفلكية</h2>
{eval_html}

<h2>تفاصيل التوقعات حسب الكواكب والبيوت</h2>
{h_html}

<h2>هندسة الاتصالات (الزوايا الفلكية)</h2>
{a_html if a_html else "<p>لا توجد اتصالات رئيسية دقيقة بين الكواكب السنوية هذا العام.</p>"}

<h2>هيكلة الخريطة السنوية</h2>
<table class="astro-table"><thead><tr><th>الكوكب</th><th>الموقع الفلكي</th><th>البيت السنوي</th><th>الحركة</th></tr></thead><tbody>{rows}</tbody></table>
</div></body></html>"""


# ==================== تطبيق Streamlit الواجهة الرئيسية ====================

def main():
    st.markdown("<h2 style='color: #4b1a9e;'>رادار التوقعات السنوية المتقدم - برمجة الفلكي و المبرمج : ملهم احمد حلبيه</h2>", unsafe_allow_html=True)
    
    # تحضير الخيارات الجغرافية والزمنية
    countries = load_countries()
    country_options = sorted([(f"{c['name']} ({c['iso']})", c['iso']) for c in countries.values()], key=lambda x: x[0])
    country_display = [x[0] for x in country_options]
    country_codes = [x[1] for x in country_options]
    
    time_options = ["الساعة غير معروفة"] + [time(h, m).strftime('%H:%M') for h in range(24) for m in range(0, 60, 5)]
    default_time_idx = time_options.index("11:40") if "11:40" in time_options else 0

    # إدخال البيانات الشخصية
    name_input = st.text_input("الاسم (دولة، مؤسسة، شخص)", value="Mulham Ahmad Halabieh")
    
    col1, col2 = st.columns(2)
    with col1:
        gender_select = st.selectbox("الجنس / النوع", ["ذكر", "أنثى", "كيان/مؤسسة/دولة"], index=0)
    with col2:
        target_year_select = st.selectbox("السنة المستهدفة", [str(y) for y in range(1910, 2091)], index=116) # 2026

    col3, col4 = st.columns(2)
    with col3:
        birth_date_val = st.date_input("تاريخ الميلاد", value=datetime(1981, 4, 17), min_value=datetime(1900, 1, 1), max_value=datetime(2100, 12, 31))
    with col4:
        time_select = st.selectbox("ساعة الميلاد", time_options, index=default_time_idx)

    # بيانات الولادة
    st.divider()
    st.markdown("#### بيانات الولادة")
    
    sy_index = country_codes.index("SY") if "SY" in country_codes else 0
    b_country_display = st.selectbox("دولة الميلاد / التأسيس", country_display, index=sy_index)
    b_country_code = country_codes[country_display.index(b_country_display)]
    
    b_cities = get_cities_by_country(b_country_code)
    b_city_names = [c.name for c in b_cities]
    default_b_city = "Ḩamāh"
    b_city_idx = b_city_names.index(default_b_city) if default_b_city in b_city_names else 0
    
    if b_city_names:
        b_city_name = st.selectbox("مدينة الميلاد", b_city_names, index=b_city_idx)
        b_city = b_cities[b_city_names.index(b_city_name)]
    else:
        st.warning("لا توجد مدن متاحة لهذه الدولة")
        b_city = None

    # بيانات السنوية
    st.divider()
    st.markdown("#### بيانات السنوية (المكان الحالي)")
    
    ae_index = country_codes.index("AE") if "AE" in country_codes else 0
    r_country_display = st.selectbox("دولة السنوية", country_display, index=ae_index)
    r_country_code = country_codes[country_display.index(r_country_display)]
    
    r_cities = get_cities_by_country(r_country_code)
    r_city_names = [c.name for c in r_cities]
    default_r_city = "Abu Dhabi"
    r_city_idx = r_city_names.index(default_r_city) if default_r_city in r_city_names else 0
    
    if r_city_names:
        r_city_name = st.selectbox("مدينة السنوية", r_city_names, index=r_city_idx)
        r_city = r_cities[r_city_names.index(r_city_name)]
    else:
        st.warning("لا توجد مدن متاحة لهذه الدولة")
        r_city = None

    st.divider()

    # زر توليد التقرير
    if st.button("تحليل واستخراج التقرير", use_container_width=True):
        if not b_city or not r_city:
            st.error("يرجى اختيار المدن أولاً.")
            return
            
        with st.spinner("جاري تحليل الخريطة والمعادلات الفلكية..."):
            try:
                t_year = int(target_year_select)
                b_date = birth_date_val
                
                # تحويل الوقت
                if time_select == "الساعة غير معروفة":
                    b_time = "الساعة غير معروفة"
                else:
                    h, m = map(int, time_select.split(":"))
                    b_time = time(h, m)
                
                # تشغيل الحسابات الأساسية
                chart = calculate_chart(b_date, b_time, b_city, r_city, t_year)
                usm_rows = run_usm_engine_daily(b_date)
                usm_row = next((r for r in usm_rows if r.age == (t_year - b_date.year)), usm_rows[0])
                
                house_evals = evaluate_houses(chart)
                house_preds, aspect_preds = generate_dynamic_predictions(chart)
                
                time_str = "غير معروفة" if isinstance(b_time, str) else b_time.strftime('%H:%M')
                personal_info = {
                    "name": name_input,
                    "gender": gender_select,
                    "dob": b_date.strftime('%Y-%m-%d'),
                    "time": time_str,
                    "birth_place": f"{b_city.name}، {b_city.country_code}",
                    "target_year": t_year
                }
                
                report_html_data = build_report_html(personal_info, chart, usm_row, house_evals, house_preds, aspect_preds)
                
                # عرض النتائج في واجهة Streamlit
                st.markdown(f"### ملخص التقرير لـ {name_input}")
                
                if usm_row.status == "CRITICAL":
                    st.error("⚠️ حالة السنة (Mulham Radar): حرجة (سنة مفصلية تحمل تحولات هامة).", icon="⚠️")
                else:
                    st.success("✅ حالة السنة (Mulham Radar): اعتيادية (مسار طبيعي ومستقر نسبياً).", icon="✅")
                    
                st.info(f"طالع السنوية: {chart.solar_asc_sign} | نظام البيوت: {chart.house_system}")
                
                st.markdown("#### ملخص حالة البيوت الفلكية")
                for h_num in range(1, 13):
                    h_str = str(h_num)
                    data = house_evals[h_str]
                    planets_str = "، ".join(data["planets"]) if data["planets"] else "فارغ"
                    st.markdown(f"- **البيت {h_num} ({houses_meaning_global[h_str]}):** <span style='color:red'>{data['status']}</span> *(الكواكب: {planets_str})*", unsafe_allow_html=True)
                
                st.markdown("#### التوقعات الدقيقة حسب الكواكب")
                for t, d in house_preds:
                    with st.expander(t):
                        # تنظيف الكود HTML لعرضه داخل Streamlit Expander بسلاسة
                        st.markdown(d, unsafe_allow_html=True)
                        
                if aspect_preds:
                    st.markdown("#### هندسة الاتصالات (الزوايا الفلكية)")
                    for t, d in aspect_preds:
                        with st.expander(t):
                            st.markdown(d, unsafe_allow_html=True)

                st.divider()
                # زر تحميل التقرير (HTML جاهز للطباعة والـ PDF)
                st.download_button(
                    label="💾 حفظ التقرير الكامل (HTML)",
                    data=report_html_data.encode("utf-8"),
                    file_name=f"Full_Report_{name_input}_{t_year}.html",
                    mime="text/html",
                    use_container_width=True
                )

            except Exception as ex:
                st.error(f"حدث خطأ أثناء الحساب: {ex}")
                st.code(traceback.format_exc())

if __name__ == "__main__":
    main()