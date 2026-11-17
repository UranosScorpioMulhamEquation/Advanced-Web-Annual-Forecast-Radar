from __future__ import annotations
import html
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import NamedTuple, List, Tuple, Dict, Any
import traceback
import os
import streamlit as st

import geonamescache
import libephemeris as swe
from timezonefinder import TimezoneFinder
from zoneinfo import ZoneInfo

# ==================== إعدادات الصفحة ودعم العربية (Streamlit) ====================
st.set_page_config(page_title="رادار التوقعات السنوية المتقدم والاستشاري", page_icon="🔮", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap');
html, body, [class*="css"] {
    direction: rtl;
    text-align: right;
    font-family: 'Cairo', sans-serif;
}
.stDownloadButton button {
    background-color: #1b5e20 !important;
    color: white !important;
    font-weight: bold;
    font-size: 16px;
}
.stButton button {
    background-color: #5b21b6;
    color: white;
    font-weight: bold;
}
.summary-card {
    background: #ffffff;
    border-right: 5px solid #6D28D9;
    padding: 18px;
    margin-bottom: 15px;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.month-badge {
    background-color: #ede9fe;
    color: #5b21b6;
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 13px;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# ==================== 1. Security & Paths (Mobile Optimized) ====================
# تحديد مجلد التطبيق لضمان صلاحيات القراءة والكتابة
APP_DIR = os.getcwd() # تعريف مبدئي آمن لتجنب NameError

try:
    os.makedirs(APP_DIR, exist_ok=True)
except Exception:
    APP_DIR = os.getcwd() # كبديل آمن إذا تم تشغيله خارج الأندرويد

# ==================== إعدادات libephemeris ====================
swe.set_ephe_path(APP_DIR)

# ==================== البيانات والثوابت والهياكل ====================
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

# ==================== الحسابات الفلكية الدقيقة ====================
AR_MONTHS = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]

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

# ==================== حساب التوقيت الشهري الفلكي الدقيق ====================
def get_solar_month_window(return_local: datetime, house_num: int) -> str:
    """
    تحسب الفترة الزمنية بالشهور الميلادية الحقيقية التي يتفعل فيها البيت السنوي
    وفق تقنية تسيير البيوت الشهرية للعودة الشمسية (Monthly Profections).
    البيت 1 يبدأ مع لحظة السنوية، والبيت 2 بعد شهر، وهكذا.
    """
    start_offset_days = (house_num - 1) * 30.4375
    end_offset_days = house_num * 30.4375
    
    start_dt = return_local + timedelta(days=start_offset_days)
    end_dt = return_local + timedelta(days=end_offset_days)
    
    m_start_name = AR_MONTHS[start_dt.month - 1]
    m_end_name = AR_MONTHS[end_dt.month - 1]
    
    if m_start_name == m_end_name:
        return f"{m_start_name} {start_dt.year}"
    return f"{m_start_name} - {m_end_name} {end_dt.year}"

# ==================== محرك رادار USM ====================
def run_usm_engine_daily(birth_date: date) -> list[USMRow]:
    homo_k, eris_k, neptune_k, tolerance = 6.18, 9.3, 10.77, 0.3
    results = []
    for i in range(1, 199):
        h_dev = abs((i/homo_k) - round(i/homo_k))
        e_dev = abs((i/eris_k) - round(i/eris_k))
        n_dev = abs((i/neptune_k) - round(i/neptune_k))
        status = "CRITICAL" if (h_dev <= tolerance and e_dev <= tolerance and n_dev <= tolerance) else "Normal"
        results.append(USMRow(age=i, risk_date=date(birth_date.year + i, 1, 1), status=status, homo_deviation=h_dev, eris_deviation=e_dev, neptune_deviation=n_dev))
    return results

# ==================== القواميس الدلالية ====================
houses_meanings = {
    "individual": {
        "1": "الذات، الطاقة الجسدية، المبادرات الشخصية",
        "2": "المال المكتسب، الممتلكات والسيولة",
        "3": "التنقل الداخلي، الإخوة، التواصل والدراسات القصيرة",
        "4": "الأسرة، الوالدين، السكن والعقارات",
        "5": "العاطفة، العلاقات العابرة، الأبناء والمشاريع الإبداعية",
        "6": "بيئة العمل اليومي، الصحة، والروتين اليومي",
        "7": "الشراكات، الزواج، العقود، والأعداء الظاهرون",
        "8": "أموال الشراكات والقروض، العمليات، والأزمات العميقة",
        "9": "السفر البعيد، الهجرة، التعليم العالي والتوسع الفكري",
        "10": "المكانة المهنية، الترقية، السمعة وعلاقتك بالمسؤولين",
        "11": "الأصدقاء، الدعم الاجتماعي، وتحقيق الأماني الكبرى",
        "12": "العزلة، المستشفيات، المؤامرات الخفية والراحة النفسية"
    },
    "country": {
        "1": "الشعب، الهوية الوطنية، وصورة الدولة العالمية",
        "2": "الخزينة العامة، الاقتصاد الوطني والقدرة الشرائية",
        "3": "الإعلام، النقل والمواصلات، والتجارة الداخلية",
        "4": "الأراضي، المحاصيل، المعارضة والنسيج الداخلي",
        "5": "قطاع الاستثمار والترفيه والأسواق المالية",
        "6": "القوات المسلحة (الأمن الداخلي)، الصحة العامة والنقابات",
        "7": "العلاقات الدبلوماسية، المعاهدات الدولية أو النزاعات",
        "8": "الديون السيادية، المخابرات، ومعدلات الوفيات والضرائب",
        "9": "القضاء الأعلى، التجارة الخارجية، والشحن الدولي",
        "10": "الحكومة، رئيس الدولة، والسلطة التنفيذية العليا",
        "11": "البرلمان، التحالفات الدولية والدول الصديقة",
        "12": "التهديدات السرية، السجون، وحركات التخريب الخفية"
    },
    "company": {
        "1": "العلامة التجارية (Brand)، مكانة الشركة التأسيسية",
        "2": "الإيرادات، السيولة النقدية، والأصول السائلة",
        "3": "التسويق والمبيعات اليومية، العلاقات العامة",
        "4": "المقر الرئيسي، الأصول العقارية والمخازن",
        "5": "الابتكار والبحث والتطوير (R&D) والاستثمارات الجريئة",
        "6": "فريق العمل التشغيلي، الروتين وظروف العمل الداخلية",
        "7": "الشراكات التجارية (B2B)، العقود، والمنافسين المباشرين",
        "8": "التمويل البنكي، الضرائب، الاندماجات والاستحواذات",
        "9": "التوسع الدولي، التراخيص القانونية، والملكية الفكرية",
        "10": "المدير التنفيذي (CEO)، مجلس الإدارة والقيادة",
        "11": "المساهمون، قاعدة العملاء المخلصين وشبكة العلاقات",
        "12": "الالتزامات الخفية، المنافسة غير الشريفة ومخاطر التسريب"
    }
}

planets_meanings = {
    "individual": {
        "الشمس": "الوضوح، التقدير، واكتساب الأهمية والريادة",
        "القمر": "تغيرات مشاعرية، تقلبات، وحاجة للأمان",
        "عطارد": "حركة فكرية سريعة، عقود، اتصالات ومفاوضات",
        "الزهرة": "وفرة مالية، بهجة، حب، تسهيل ومصالحات",
        "المريخ": "طاقة تنافسية عالية، شجاعة، توترات ومواجهات",
        "المشتري": "توسع استثنائي، حظوظ مباركة، وانفراجات كبرى",
        "زحل": "مسؤوليات ثقيلة، تأخيرات، إعادة تنظيم، وصبر مفروض",
        "أورانوس": "تغيرات مفاجئة غير متوقعة، ثورات وحرية جديدة",
        "نبتون": "إلهام روحي وفني، أو ضبابية وتشتت وغموض",
        "بلوتو": "تحولات جذرية، نهاية حاسمة لمرحلة وبداية جديدة"
    },
    "country": {
        "الشمس": "رئيس الدولة ومصدر القرار السيادي",
        "القمر": "المزاج الشعبي والجمهور العام",
        "عطارد": "الصحافة، الاتصالات، والتجارة",
        "الزهرة": "المناخ الدبلوماسي والثقافي الإيجابي",
        "المريخ": "المؤسسة العسكرية والجاهزية القتالية",
        "المشتري": "النمو الاقتصادي والازدهار والعدالة",
        "زحل": "القوانين الصارمة، البنية التحتية، والبيروقراطية",
        "أورانوس": "الابتكار الرقمي، أو الاضطرابات المفاجئة",
        "نبتون": "الموارد البحرية والنفط، أو الشائعات والبروباغندا",
        "بلوتو": "أجهزة الأمن السيادية والثروات الباطنية الاستراتيجية"
    },
    "company": {
        "الشمس": "الرئيس التنفيذي (CEO) والقيادة الإستراتيجية",
        "القمر": "رضا العملاء والمناخ العام للموظفين",
        "عطارد": "العقود والصفقات وتحليلات البيانات",
        "الزهرة": "تصميم المنتجات وراحة بيئة العمل",
        "المريخ": "الحملات الهجومية وقوة اختراق السوق",
        "المشتري": "جلب الاستثمارات والنمو المالي والانتشار",
        "زحل": "إدارة المخاطر، الالتزام المؤسسي والحوكمة",
        "أورانوس": "التحول التكنولوجي وإعادة الهيكلة السريعة",
        "نبتون": "الصورة الذهنية للعلامة التجارية والمسؤولية المجتمعية",
        "بلوتو": "الاستحواذات الكبرى أو الإنقاذ في الأزمات العاصفة"
    }
}

short_meanings_map = {
    "individual": {
        "الشمس": "الوضوح والريادة", "القمر": "المشاعر والحركة", 
        "عطارد": "التواصل والاتفاقات", "الزهرة": "المال والعاطفة", 
        "المريخ": "الجهد والمواجهة", "المشتري": "التوسع والوفرة", 
        "زحل": "الانضباط والتحدي", "أورانوس": "المفاجآت والتحول", 
        "نبتون": "الإلهام أو الحيرة", "بلوتو": "التحول الجذري"
    },
    "country": {
        "الشمس": "القيادة السياسية", "القمر": "الشعب", 
        "عطارد": "الإعلام والتجارة", "الزهرة": "الدبلوماسية", 
        "المريخ": "القوة العسكرية", "المشتري": "الازدهار المالي", 
        "زحل": "النظام والقانون", "أورانوس": "المتغيرات التقنية/الشعبية", 
        "نبتون": "الموارد والنفط", "بلوتو": "المخابرات والتحولات"
    },
    "company": {
        "الشمس": "الرؤية والقيادة", "القمر": "العملاء والموظفون", 
        "عطارد": "المبيعات والبيانات", "الزهرة": "التصميم والتجربة", 
        "المريخ": "المنافسة والسرعة", "المشتري": "الاستثمار والتوسع", 
        "زحل": "الحوكمة والمخاطر", "أورانوس": "الابتكار الرقمي", 
        "نبتون": "البراند والسمعة", "بلوتو": "إعادة الهيكلة والاندماج"
    }
}

# ==================== محرك بناء الملخص الاستشاري المبسط (لغير الفلكيين) ====================
def generate_plain_summary(chart: SolarChart, target_type: str, usm_row: USMRow) -> Dict[str, Any]:
    """
    محرك استشاري ذكي: يترجم البيانات الفلكية الجافة إلى إجابات مباشرة ومحددة بالشهور
    لكل سؤال من أسئلة المستخدم لغير الفلكيين.
    """
    # تصنيف الكواكب حسب البيوت
    h_planets: Dict[str, List[dict]] = {str(i): [] for i in range(1, 13)}
    for row in chart.planet_rows:
        h_planets[row["البيت"]].append(row)
        
    p_names_in_h = lambda h: [r["الكوكب"] for r in h_planets[str(h)]]
    
    summary: Dict[str, Any] = {}
    r_local = chart.return_local
    
    # ------------------ للأفراد (INDIVIDUAL) ------------------
    if target_type == "individual":
        # 1. الوضع العام والتطور
        asc_sign = chart.solar_asc_sign.split()[0]
        sun_house = next((r["البيت"] for r in chart.planet_rows if r["الكوكب"] == "الشمس"), "1")
        sun_period = get_solar_month_window(r_local, int(sun_house))
        
        has_evolution = any(p in p_names_in_h(1) + p_names_in_h(10) for p in ["المشتري", "الشمس", "الزهرة", "بلوتو"])
        evo_text = "تشهد هذه السنة **تطوراً ملحوظاً ونقلة إيجابية** في مكانتك ومسارك الشخصي." if has_evolution else "السنة سنة **تثبيت واستقرار وبناء هادئ**، وتتطلب منك تنظيماً بدون تسرع."
        if usm_row.status == "CRITICAL":
            evo_text += " (مع الأخذ بعين الاعتبار أن رادار التحولات الكبرى يُصنف هذه السنة كـ **سنة مفصلية تاريخية** في حياتك)."
            
        summary["الوضع العام والتطور"] = {
            "نص": f"طالع سنويتك هو **{asc_sign}**، ومحور التركيز الرئيسي يتمحور حول شؤون **(البيت {sun_house})**. {evo_text}",
            "ذروة_النشاط": f"أبرز فترات التوهج الشخصي تقع في: **{sun_period}** (تفعيل بيت الشمس)."
        }
        
        # 2. المال والوفرة
        h2 = p_names_in_h(2)
        h8 = p_names_in_h(8)
        money_active = []
        if any(p in h2 for p in ["المشتري", "الزهرة", "الشمس"]):
            money_active.append((2, "تدفق مالي ممتاز، زيادة دخل، أو أرباح ومكافآت شخصية"))
        elif any(p in h2 for p in ["زحل", "المريخ", "أورانوس"]):
            money_active.append((2, "تقلبات مالية، مصاريف مفاجئة، أو ضغوط تتطلب ترشيد الإنفاق"))
        else:
            money_active.append((2, "وضع مالي مستقر واعتيادي بدون هزات كبيرة"))
            
        if any(p in h8 for p in ["المشتري", "الزهرة"]):
            money_active.append((8, "مكاسب عبر قروض ميسرة، شراكات، تعويضات، أو أموال تأتي من طرف آخر"))
        elif any(p in h8 for p in ["زحل", "المريخ", "بلوتو"]):
            money_active.append((8, "ضرورة الحذر الشديد من الديون أو الالتزامات المالية والضرائب"))
            
        m_periods = [f"البيت {h_num} ({get_solar_month_window(r_local, h_num)}): {desc}" for h_num, desc in money_active]
        summary["المال والدخل"] = {
            "هل_يوجد_مال": "نعم، توجد فرص مكاسب مالية قوية" if any(p in h2+h8 for p in ["المشتري", "الزهرة"]) else "المال يتطلب مجهوداً وتنظيماً، وهناك تركيز على إدارة المصاريف.",
            "المواعيد": m_periods
        }
        
        # 3. العاطفة والارتباط والزواج أو الطلاق
        h5 = p_names_in_h(5)
        h7 = p_names_in_h(7)
        love_eval = []
        
        # الارتباط العاطفي
        if any(p in h5 for p in ["الزهرة", "المشتري", "الشمس"]):
            love_eval.append(f"**ارتباط عاطفي وإعجاب جديد:** فرصة ممتازة لدخول قصة حب مبهجة في الفترة **({get_solar_month_window(r_local, 5)})**.")
        elif "زحل" in h5:
            love_eval.append(f"**برود عاطفي أو علاقة تحتاج نضجاً:** تأني في التعبير عن المشاعر خلال **({get_solar_month_window(r_local, 5)})**.")
            
        # الزواج أو الطلاق أو الجدية
        if any(p in h7 for p in ["الزهرة", "المشتري"]):
            love_eval.append(f"**زواج أو خطوبة رسمية:** مؤشر قوي جداً على عقد قران أو ارتباط جدي ومريح يبلغ ذروته في **({get_solar_month_window(r_local, 7)})**.")
        elif any(p in h7 for p in ["المريخ", "أورانوس", "بلوتو"]):
            love_eval.append(f"**مشاكل زوجية أو مفترق طرق (انفصال/طلاق محتمل):** توتر في الشراكات أو قرارات مفاجئة في العلاقة تتطلب الهدوء في **({get_solar_month_window(r_local, 7)})**.")
        elif "زحل" in h7:
            love_eval.append(f"**التزام جدي أو اختبار لصلابة الزواج:** تحمل مسؤوليات ثقيلة تجاه الشريك أو توثيق رسمي لعلاقة ناضجة في **({get_solar_month_window(r_local, 7)})**.")
        else:
            if not love_eval:
                love_eval.append("العلاقات تسير بنسقها الطبيعي بدون تغييرات جذرية طارئة.")
                
        summary["العاطفة والزواج والانفصال"] = {
            "التفاصيل": love_eval,
            "أشهر_التفعيل_العاطفي": f"شهر العاطفة والتعارف: **{get_solar_month_window(r_local, 5)}** | شهر الشراكة والزواج: **{get_solar_month_window(r_local, 7)}**"
        }
        
        # 4. الوظيفة، الترقية، تغيير العمل، أو الفصل
        h10 = p_names_in_h(10)
        h6 = p_names_in_h(6)
        job_eval = []
        
        if any(p in h10 for p in ["المشتري", "الشمس"]):
            job_eval.append(f"**ترقية ومنصب جديد:** اعتراف كبير بكفاءتك، صعود مهني، أو تولي موقع قيادي رفيع يتبلور في **({get_solar_month_window(r_local, 10)})**.")
        elif "أورانوس" in h10 or "أورانوس" in h6:
            job_eval.append(f"**تغيير مفاجئ في الوظيفة:** ترك عمل، تحول مهني غير متوقع، أو بدء عمل حر/رقمي في **({get_solar_month_window(r_local, 10)})** أو **({get_solar_month_window(r_local, 6)})**.")
        elif "زحل" in h10:
            job_eval.append(f"**مسؤوليات وظيفية ثقيلة وضغط إداري:** ترقية مشروطة بتعب وجهد مضاعف في **({get_solar_month_window(r_local, 10)})**.")
        elif "المريخ" in h10 or "المريخ" in h6:
            job_eval.append(f"**خلافات في العمل أو خطر فصل ونزاع:** احذر الصدامات مع المدراء وزملاء العمل وتجنب التهور خاصة في **({get_solar_month_window(r_local, 10)})** و **({get_solar_month_window(r_local, 6)})**.")
        else:
            job_eval.append(f"استقرار في المسار الوظيفي الروتيني؛ أكثر أوقات الإنجاز في العمل اليومي ستكون في **({get_solar_month_window(r_local, 6)})** والتقييم السنوي في **({get_solar_month_window(r_local, 10)})**.")
            
        summary["الوظيفة والمسار المهني"] = {
            "التفاصيل": job_eval,
            "الشهور_الحاسمة": f"العمل الروتيني واليومي: **{get_solar_month_window(r_local, 6)}** | الترقية والمكانة الإدارية: **{get_solar_month_window(r_local, 10)}**"
        }
        
        # 5. السفر (داخلي أم خارجي وهجرة)
        h3 = p_names_in_h(3)
        h9 = p_names_in_h(9)
        travel_eval = []
        
        if any(p in h9 for p in ["المشتري", "الشمس", "الزهرة", "أورانوس"]):
            travel_eval.append(f"**سفر دولي هام أو هجرة/أوراق إقامة:** فرص ممتازة جداً للسفر خارج البلاد أو المعاملات الدولية وتسهيل التأشيرات في **({get_solar_month_window(r_local, 9)})**.")
        elif "زحل" in h9:
            travel_eval.append(f"**تأخير في السفر الخارجي أو معاملات فيزا معقدة:** يتطلب السفر إلى الخارج أوراقاً وصبر ومراجعات مكثفة في **({get_solar_month_window(r_local, 9)})**.")
            
        if any(p in h3 for p in ["المشتري", "عطارد", "المريخ", "القمر"]):
            travel_eval.append(f"**سفر داخلي وتنقلات محلية كثيرة:** حركة مستمرة بين المدن القريبة وزيارات متكررة في **({get_solar_month_window(r_local, 3)})**.")
            
        if not travel_eval:
            travel_eval.append("حركة السفر عادية واعتيادية دون سفر مصيري أو هجرة بعيدة.")
            
        summary["السفر والتنقل"] = {
            "التفاصيل": travel_eval,
            "الشهور_المقترحة": f"السفر الداخلي: **{get_solar_month_window(r_local, 3)}** | السفر الدولي والهجرة: **{get_solar_month_window(r_local, 9)}**"
        }
        
        # 6. التحذيرات الصحية
        h12 = p_names_in_h(12)
        h6_danger = any(p in h6 for p in ["المريخ", "زحل", "نبتون", "بلوتو"])
        h8_danger = any(p in h8 for p in ["المريخ", "زحل", "بلوتو"])
        h12_danger = any(p in h12 for p in ["المريخ", "زحل", "أورانوس", "نبتون"])        
        health_alerts = []
        if h6_danger:
            health_alerts.append(f"**انتبه لصحتك البدنية وإجهاد العمل:** مخاطر التهابات، إرهاق عصبي أو اضطراب في نمط المعيشة خلال **({get_solar_month_window(r_local, 6)})**.")
        if h8_danger:
            health_alerts.append(f"**فترة حساسة صحياً أو عمليات جراحية صغرى:** تجنب المخاطرة الجسدية واعتنِ بالفحوصات خلال **({get_solar_month_window(r_local, 8)})**.")
        if h12_danger:
            health_alerts.append(f"**حاجة للراحة النفسية وتجنب الإجهاد الخفي:** مراعاة النوم والصحة النفسية وتجنب الأدوية العشوائية خلال **({get_solar_month_window(r_local, 12)})**.")
            
        if not health_alerts:
            health_alerts.append("المؤشرات الصحية مستقرة ومطمئنة بوجه عام مع دعوة للحفاظ على اللياقة المعتادة.")
            
        summary["الصحة والتحذيرات البدنية"] = {
            "التفاصيل": health_alerts,
            "أشهر_الحذر_الصحي": f"شهور تتطلب مراقبة صحية: **{get_solar_month_window(r_local, 6)}** و **{get_solar_month_window(r_local, 8)}**"
        }
        
        # 7. العائلة، الأهل، الأبناء، ومخاطر الفقد
        h4 = p_names_in_h(4)
        family_eval = []
        
        if any(p in h4 for p in ["المشتري", "الزهرة"]):
            family_eval.append(f"**أفراح عائلية، تحسين مسكن أو عقار جديد:** راحة وسلام عائلي وتطورات مبهجة تخص الأهل في **({get_solar_month_window(r_local, 4)})**.")
        elif any(p in h4 for p in ["زحل", "المريخ", "بلوتو"]):
            family_eval.append(f"**قلق أو وعكة تخص أحد الوالدين/الأسرة أو إصلاحات منزلية شاقة:** يستدعي الأمر اهتماماً بصحة الأب/الأم وحفظ التوازن المنزلي في **({get_solar_month_window(r_local, 4)})**.")
            
        if any(p in h5 for p in ["المشتري", "الزهرة"]):
            family_eval.append(f"**أخبار سعيدة تخص الأبناء أو حمل وإنجاب:** فترة مبروكة للأطفال في **({get_solar_month_window(r_local, 5)})**.")
            
        if any(p in h3 for p in ["زحل", "المريخ"]):
            family_eval.append(f"**انتبه لعلاقتك بالإخوة أو وضع صحي يخص شقيقاً:** يتطلب الصبر والحكمة في **({get_solar_month_window(r_local, 3)})**.")
            
        if any(p in h8 for p in ["زحل", "بلوتو"]) or any(p in h12 for p in ["بلوتو", "زحل"]):
            family_eval.append(f"**تحذير من فقد عاطفي أو إغلاق صفحة هامة مع أحد المقربين:** ضرورة التماسك وتجاوز أي حزن عبر الصبر خلال **({get_solar_month_window(r_local, 8)})** أو **({get_solar_month_window(r_local, 12)})**.")
            
        if not family_eval:
            family_eval.append("الأجواء العائلية مستقرة ومتوازنة.")
            
        summary["العائلة والأهل والأبناء"] = {
            "التفاصيل": family_eval,
            "الشهور_المرتبطة": f"شؤون البيت والوالدين: **{get_solar_month_window(r_local, 4)}** | الأبناء: **{get_solar_month_window(r_local, 5)}** | الإخوة: **{get_solar_month_window(r_local, 3)}**"
        }
        
        # 8. أهم التحذيرات والفرص الذهبية
        warnings = []
        opportunities = []
        
        for r in chart.planet_rows:
            if r["الكوكب"] == "زحل":
                warnings.append(f"تحمّل التأخيرات والواجبات الإضافية في مجالات (البيت {r['البيت']}) بالصبر وعدم الجزع.")
            elif r["الكوكب"] == "المريخ":
                warnings.append(f"تجنب الانفعال، القيادة المتهورة، والجدال الحاد في مجالات (البيت {r['البيت']}).")
            elif r["الكوكب"] == "أورانوس":
                warnings.append(f"توقع ما هو غير متوقع وكن مرناً أمام المفاجآت في (البيت {r['البيت']}).")
            elif r["الكوكب"] == "المشتري":
                opportunities.append(f"استغل الحظوظ المطلقة وأبواب التوسع المفتوحة لك على مصراعيها في (البيت {r['البيت']}).")
            elif r["الكوكب"] == "الزهرة":
                opportunities.append(f"وظف الدبلوماسية والتصالح والجاذبية العالية لتحقيق مكاسب في (البيت {r['البيت']}).")
                
        summary["أهم التحذيرات العامة"] = warnings[:3] if warnings else ["تجنب التسرع في اتخاذ القرارات المصيرية أثناء تراجع الكواكب الشخصية."]
        summary["أهم الفرص الذهبية والنصائح"] = opportunities[:3] if opportunities else ["التركيز على تطوير المهارات والاعتماد على التخطيط المستمر."]

    # ------------------ للشركات والمؤسسات (COMPANY) ------------------
    elif target_type == "company":
        h2 = p_names_in_h(2)
        h8 = p_names_in_h(8)
        h10 = p_names_in_h(10)
        h6 = p_names_in_h(6)
        
        # 1. العناوين الرئيسية
        summary["العناوين الرئيسية للعام"] = f"سنة تركز بشكل جوهري على نمو العلامة التجارية وإعادة ضبط خطط التوسع في السوق. المحور القيادي يقع في (البيت {h10 or 'الرئيسي'})."
        
        # 2. الوضع المالي
        fin_text = "سيولة قوية وفرص استثمار وجلب تمويل خارجي واعد." if any(p in h2+h8 for p in ["المشتري", "الزهرة"]) else "تتطلب السنة تدقيقاً مالياً صارماً وحماية السيولة وضبط هوامش الربح ضد التقلبات."
        summary["الوضع المالي للشركة"] = {
            "التقييم": fin_text,
            "فترات_النشاط_المالي": f"الإيرادات المباشرة: **{get_solar_month_window(r_local, 2)}** | التمويل والقروض: **{get_solar_month_window(r_local, 8)}**"
        }
        
        # 3. الوضع الهيكلي والإداري
        org_text = "قرارات إدارية حاسمة تصدر من مجلس الإدارة وتغييرات في الإدارة العليا مع فرص ترقية للكوادر." if any(p in h10 for p in ["الشمس", "المشتري", "أورانوس"]) else "استقرار في الإدارة مع متطلبات لتحسين كفاءة سلاسل الإمداد وبيئة عمل الموظفين."
        summary["الوضع الهيكلي والإداري"] = {
            "التقييم": org_text,
            "فترات_القرارات_الكبرى": f"القرارات التنفيذية: **{get_solar_month_window(r_local, 10)}** | الكفاءة والعمليات اليومية: **{get_solar_month_window(r_local, 6)}**"
        }
        
        # 4. التحذيرات والفرص
        summary["أهم التحذيرات للشركة"] = [
            f"مراقبة المنافسة الشرسة وحماية العقود القانونية خاصة في ({get_solar_month_window(r_local, 7)}).",
            f"إدارة مخاطر السيولة والامتثال الضريبي والبنكي في ({get_solar_month_window(r_local, 8)}).",
            "تجنب النزاعات العمالية الداخلية أو تسرب الكفاءات عبر تحسين بيئة العمل."
        ]
        summary["أهم الفرص الذهبية والنصائح"] = [
            f"إطلاق منتجات مبتكرة أو حملات تسويقية كبرى في ({get_solar_month_window(r_local, 5)}) و ({get_solar_month_window(r_local, 3)}).",
            f"إبرام تحالفات استراتيجية وعقود كبرى نوعية في ({get_solar_month_window(r_local, 7)}).",
            "تسريع وتيرة التحول الرقمي والأتمتة لتخفيض النفقات التشغيلية."
        ]

    # ------------------ للدول والحكومات (COUNTRY) ------------------
    elif target_type == "country":
        h2 = p_names_in_h(2)
        h1 = p_names_in_h(1)
        h4 = p_names_in_h(4)
        h6 = p_names_in_h(6)
        h7 = p_names_in_h(7)
        h8 = p_names_in_h(8)
        
        # 1. الوضع الاقتصادي
        econ_good = any(p in h2 for p in ["المشتري", "الزهرة"])
        summary["الوضع الاقتصادي الوطني"] = {
            "التقييم": "مؤشرات نمو إيجابي، انتعاش في الخزينة العامة والمشاريع التنموية الكبرى." if econ_good else "ضغوط اقتصادية تتطلب سياسات نقدية حذرة ومكافحة للتضخم وحماية القدرة الشرائية.",
            "الشهور_الحرجة": f"مراجعة الموازنة العامة والنشاط التجاري: **{get_solar_month_window(r_local, 2)}** و **{get_solar_month_window(r_local, 8)}**"
        }
        
        # 2. الوضع الشعبي
        pop_mood = "ارتياح عام وحالة من التفاؤل والالتفاف الوطني." if any(p in h1+h4 for p in ["المشتري", "الزهرة", "الشمس"]) else "حالة من الترقب والمطالبات الشعبية بتحسين جودة المعيشة والخدمات."
        summary["الوضع الشعبي والرأي العام"] = {
            "التقييم": pop_mood,
            "الشهور_النشطة": f"الرأي العام والحراك الاجتماعي: **{get_solar_month_window(r_local, 1)}** و **{get_solar_month_window(r_local, 4)}**"
        }
        
        # 3. الوضع الأمني
        sec_stable = not any(p in h8+p_names_in_h(12) for p in ["المريخ", "بلوتو", "أورانوس"])
        summary["الوضع الأمني والاستقرار الداخلي"] = {
            "التقييم": "استقرار أمني عالي ويقظة استخباراتية تفشل المؤامرات والمخططات العبثية." if sec_stable else "حاجة لتكثيف اليقظة الأمنية الداخلية ومكافحة الجرائم الإلكترونية والتهديدات العابرة.",
            "الشهور_الحساسة": f"الشهور التي تتطلب جاهزية قصوى: **{get_solar_month_window(r_local, 8)}** و **{get_solar_month_window(r_local, 12)}**"
        }
        
        # 4. الوضع العسكري
        mil_active = any(p in h6+h7 for p in ["المريخ", "بلوتو", "الشمس"])
        summary["الوضع العسكري والجاهزية"] = {
            "التقييم": "جاهزية دفاعية عالية جداً، استعراض للقوة، ومناورات وتحديث نوعي للمنظومات القتالية." if mil_active else "هدوء عسكري وتركيز على الشراكات الدفاعية والاتفاقات الأمنية المتوازنة.",
            "الشهور_المحورية": f"الجاهزية والخدمة العسكرية: **{get_solar_month_window(r_local, 6)}** | الحدود والاتفاقات: **{get_solar_month_window(r_local, 7)}**"
        }
        
        # 5. الوضع الصحي العام
        health_state = "استقرار المنظومة الصحية ونهضة في المرافق الطبية والتأمين الصحي." if not any(p in h6 for p in ["زحل", "نبتون", "المريخ"]) else "ضغط على قطاع الرعاية الطبية وحاجة لليقظة من الأمراض التنفسية أو الوبائية الموسمية."
        summary["الوضع الصحي العام"] = {
            "التقييم": health_state,
            "الشهور_المتابعة": f"الفترة الأكثر تطلباً للرعاية الصحية: **{get_solar_month_window(r_local, 6)}**"
        }
        
        # 6. التحذيرات والفرص
        summary["أهم التحذيرات السيادية للدولة"] = [
            f"الحذر من الشائعات والحروب النفسية أو الدبلوماسية الموجهة في ({get_solar_month_window(r_local, 12)}).",
            f"تأمين سلاسل الإمداد الغذائي والدوائي وإدارة أزمات الموارد في ({get_solar_month_window(r_local, 6)}).",
            f"اليقظة في المنافذ الحدودية والاتفاقيات الدولية الثنائية في ({get_solar_month_window(r_local, 7)})."
        ]
        summary["أهم التوصيات والفرص الاستراتيجية"] = [
            f"تعزيز التحالفات الاقتصادية الثنائية وجلب استثمارات كبرى في ({get_solar_month_window(r_local, 11)}).",
            f"إطلاق مشاريع عملاقة في البنية التحتية والذكاء الاصطناعي في ({get_solar_month_window(r_local, 10)}).",
            "تطوير منظومة القضاء والتعليم العالي وتعزيز التجارة البحرية واللوجستية."
        ]
        
    return summary

# ==================== الدوال التقييمية وهندسة الاتصالات ====================
def evaluate_houses(chart: SolarChart) -> Dict[str, Any]:
    house_evals = {str(i): {"score": 0, "planets": [], "status": ""} for i in range(1, 13)}
    planet_weights = {
        "المشتري": 2, "الزهرة": 2, "الشمس": 1, "القمر": 1, "عطارد": 1,
        "المريخ": -2, "زحل": -2, "بلوتو": -2, "أورانوس": -1, "نبتون": -1
    }
    
    for row in chart.planet_rows:
        p_name = row["الكوكب"]
        h_num = str(row["البيت"])
        house_evals[h_num]["planets"].append(p_name)
        house_evals[h_num]["score"] += planet_weights.get(p_name, 0)
        
    for h_num, data in house_evals.items():
        if len(data["planets"]) == 0:
            data["status"] = "مستقر واعتيادي (فارغ من الكواكب، ليس بؤرة ضغط سنوية)"
        elif data["score"] >= 2:
            data["status"] = "ممتاز ومبارك جداً (وفرة وتسهيلات كبرى)"
        elif data["score"] == 1:
            data["status"] = "جيد ونشط (حركة بناءة وإيجابية)"
        elif data["score"] == 0:
            data["status"] = "مختلط (يحمل فرصاً وتحديات تتطلب التوازن)"
        elif data["score"] == -1:
            data["status"] = "متقلب (يتطلب التركيز واليقظة من المفاجآت أو الضبابية)"
        else:
            data["status"] = "ضاغط ومليء بالتحديات (يتطلب الصبر والحكمة في المعالجة)"
            
    return house_evals

def generate_dynamic_predictions(chart: SolarChart, target_type: str = "individual") -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    current_houses = houses_meanings.get(target_type, houses_meanings["individual"])
    current_planets = planets_meanings.get(target_type, planets_meanings["individual"])
    current_short_meanings = short_meanings_map.get(target_type, short_meanings_map["individual"])
    
    house_predictions = []
    for row in chart.planet_rows:
        planet, house, deg_rem = row["الكوكب"], str(row["البيت"]), row["درجة_البرج"]
        if planet in current_planets and house in current_houses:
            title = f"{planet} في البيت {house} السنوي"
            desc = f"دلالة على **{current_planets[planet]}** فيما يخص **{current_houses[house]}**."
            if 0.0 <= deg_rem <= 0.99:
                desc += f"<br><span style='color:#b91c1c;'>⚠️ <b>تنشيط مكثف:</b> الكوكب في بداية وتد البيت ({deg_rem:.2f}°)، وتأثيره مضاعف وملموس.</span>"
            elif 29.0 <= deg_rem <= 29.99:
                next_house = str(int(house) + 1) if int(house) < 12 else "1"
                desc += f"<br><span style='color:#b91c1c;'>⚠️ <b>انتقال طاقة:</b> الكوكب في درجة حرجة ({deg_rem:.2f}°)، ينقل تأثيره لوتد البيت ({next_house}).</span>"
            house_predictions.append((title, desc))

    aspect_predictions = []
    orb = 6.0 
    num_planets = len(chart.planet_rows)
    for i in range(num_planets):
        for j in range(i + 1, num_planets):
            p1, p2 = chart.planet_rows[i], chart.planet_rows[j]
            lon1, lon2 = p1["الطول_المطلق"], p2["الطول_المطلق"]
            diff = abs(lon1 - lon2)
            if diff > 180: diff = 360 - diff
                
            aspect_name, aspect_effect = "", ""
            if diff <= orb:
                aspect_name, aspect_effect = "اقتران (0°)", "تنشيط مكثف ودمج قوي للطاقات"
            elif abs(diff - 60) <= orb:
                aspect_name, aspect_effect = "تسديس (60°)", "انسجام وفرص مساعدة ميسرة"
            elif abs(diff - 90) <= orb:
                aspect_name, aspect_effect = "تربيع (90°)", "احتكاك وتحديات تدفع لاتخاذ قرارات حاسمة"
            elif abs(diff - 120) <= orb:
                aspect_name, aspect_effect = "تثليث (120°)", "تدفق إيجابي وتوافق وحظوظ طبيعية"
            elif abs(diff - 180) <= orb:
                aspect_name, aspect_effect = "مقابلة (180°)", "شد وجذب ومواجهة تتطلب إيجاد توازن دقيق"
                
            if aspect_name:
                title = f"{aspect_name} بين {p1['الكوكب']} و {p2['الكوكب']}"
                mean1 = current_short_meanings.get(p1['الكوكب'], '')
                mean2 = current_short_meanings.get(p2['الكوكب'], '')
                desc = f"تتفاعل طاقة **[{mean1}]** في (البيت {p1['البيت']}) مع طاقة **[{mean2}]** في (البيت {p2['البيت']}). هذا يولد حالة من **{aspect_effect}**."
                aspect_predictions.append((title, desc))
                
    return house_predictions, aspect_predictions

# ==================== التقرير الطباعي HTML القابل للحفظ كـ PDF ====================
def build_report_html(personal_info: dict, chart: SolarChart, usm_row: USMRow, house_evals: dict, house_preds: list, aspect_preds: list, plain_summary: dict) -> str:
    usm_status_text = "⚠️ حرجة واستثنائية (سنة مفصلية تاريخية)" if usm_row.status == "CRITICAL" else "✅ اعتيادية ومستقرة (مسار طبيعي)"
    target_type = personal_info.get("target_type", "individual")
    current_houses_meanings = houses_meanings.get(target_type, houses_meanings["individual"])
    
    info_html = f"""
    <table class="info-table">
        <tr><th>الاسم / الكيان</th><td><b>{html.escape(personal_info['name'])}</b></td><th>التصنيف</th><td>{html.escape(personal_info.get('gender', 'غير محدد'))}</td></tr>
        <tr><th>تاريخ الميلاد / التأسيس</th><td>{personal_info['dob']}</td><th>وقت الميلاد</th><td>{personal_info.get('time', 'غير محدد')}</td></tr>
        <tr><th>مكان الميلاد / الحدث</th><td>{html.escape(personal_info.get('birth_place', ''))}</td><th>السنة المستهدفة</th><td><b>{personal_info['target_year']}</b></td></tr>
        <tr><th>طالع العودة السنوية</th><td><b>{chart.solar_asc_sign}</b></td><th>نظام البيوت</th><td>{chart.house_system}</td></tr>
        <tr><th>رادار السنوات المفصلية (USM)</th><td colspan="3"><span style="color: {'#b91c1c' if usm_row.status == 'CRITICAL' else '#15803d'}; font-weight:bold;">{usm_status_text}</span></td></tr>
    </table>
    """

    # صياغة محتوى الملخص التنفيذي لغير الفلكيين داخل HTML
    summary_html = "<div class='summary-wrapper'>"
    for key, value in plain_summary.items():
        summary_html += f"<div class='summary-block'><h3>📌 {html.escape(key)}</h3>"
        if isinstance(value, dict):
            for sub_k, sub_v in value.items():
                if isinstance(sub_v, list):
                    summary_html += f"<p><b>{html.escape(sub_k)}:</b></p><ul>"
                    for item in sub_v:
                        summary_html += f"<li>{item}</li>"
                    summary_html += "</ul>"
                else:
                    summary_html += f"<p><b>{html.escape(sub_k)}:</b> {sub_v}</p>"
        elif isinstance(value, list):
            summary_html += "<ul>"
            for item in value:
                summary_html += f"<li>{item}</li>"
            summary_html += "</ul>"
        else:
            summary_html += f"<p>{value}</p>"
        summary_html += "</div>"
    summary_html += "</div>"

    eval_html = ""
    for h_num in range(1, 13):
        h_str = str(h_num)
        data = house_evals[h_str]
        planets_str = "، ".join(data["planets"]) if data["planets"] else "فارغ"
        m_window = get_solar_month_window(chart.return_local, h_num)
        eval_html += f"""
        <div class="house-summary">
            <span class="house-title">البيت {h_num} ({current_houses_meanings[h_str]}):</span> 
            <span class="house-status">{data['status']}</span> 
            <div class="house-planets"><b>الكواكب:</b> {planets_str} | <span class="month-pill">فترة التفعيل السنوي: {m_window}</span></div>
        </div>
        """

    h_html = "".join(f'<div class="prediction"><b>{html.escape(t)}</b><br>{d}</div>' for t, d in house_preds)
    a_html = "".join(f'<div class="prediction aspect"><b>{html.escape(t)}</b><br>{d}</div>' for t, d in aspect_preds)
    rows = "".join(f'<tr><td><b>{html.escape(r["الكوكب"])}</b></td><td>{html.escape(r["الموقع"])}</td><td>البيت {html.escape(str(r["البيت"]))}</td><td>{html.escape(r.get("الحركة", ""))}</td></tr>' for r in chart.planet_rows)
    
    return f"""<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<title>التقرير الاستشاري السنوي — {html.escape(personal_info['name'])} ({personal_info['target_year']})</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap');
body {{ font-family: 'Cairo', sans-serif; background: #f8fafc; margin: 0; padding: 25px; color: #1e293b; line-height: 1.8; }}
.container {{ max-width: 950px; margin: 0 auto; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.06); }}
h1 {{ color: #4c1d95; border-bottom: 3px solid #7c3aed; padding-bottom: 12px; text-align: center; margin-bottom: 25px; font-weight: 800; font-size: 26px; }}
h2 {{ color: #5b21b6; margin-top: 30px; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; font-size: 20px; font-weight: 700; }}
h3 {{ color: #334155; font-size: 17px; margin-top: 15px; margin-bottom: 8px; font-weight: 700; }}

.page {{ page-break-after: always; clear: both; }}
.info-table, .house-summary, .prediction, .summary-block, table {{ page-break-inside: avoid; }}
@media print {{
    body {{ background: white; padding: 0; }}
    .container {{ box-shadow: none; padding: 0; max-width: 100%; }}
    .page {{ page-break-after: always; padding-top: 15px; }}
    .page:last-child {{ page-break-after: auto; }}
}}
@media screen {{
    .page {{ border-bottom: 2px dashed #cbd5e1; padding-bottom: 35px; margin-bottom: 35px; }}
    .page:last-child {{ border-bottom: none; margin-bottom: 0; padding-bottom: 0; }}
}}

.info-table {{ width: 100%; border-collapse: collapse; margin-bottom: 25px; background: #f8fafc; border-radius: 8px; overflow: hidden; }}
.info-table th, .info-table td {{ padding: 10px 14px; border: 1px solid #cbd5e1; text-align: right; font-size: 14.5px; }}
.info-table th {{ background: #ede9fe; color: #4c1d95; width: 22%; }}

.summary-wrapper {{ display: flex; flex-direction: column; gap: 14px; }}
.summary-block {{ background: #ffffff; border: 1px solid #e2e8f0; border-right: 5px solid #7c3aed; padding: 15px 18px; border-radius: 6px; }}
.summary-block h3 {{ margin-top: 0; color: #4c1d95; border-bottom: 1px solid #f1f5f9; padding-bottom: 5px; }}
.summary-block p {{ margin: 6px 0; font-size: 14.5px; }}
.summary-block ul {{ margin: 5px 0 10px 0; padding-right: 22px; font-size: 14px; }}
.summary-block li {{ margin-bottom: 4px; }}

.house-summary {{ background: #fff; padding: 12px 16px; margin: 8px 0; border: 1px solid #e2e8f0; border-right: 4px solid #5b21b6; border-radius: 6px; }}
.house-title {{ font-weight: 700; color: #0f172a; }}
.house-status {{ font-weight: 700; color: #b91c1c; margin-right: 8px; }}
.house-planets {{ font-size: 13.5px; color: #475569; margin-top: 5px; }}
.month-pill {{ background: #ede9fe; color: #5b21b6; padding: 2px 6px; border-radius: 4px; font-weight: bold; }}

.prediction {{ background: #f8fafc; padding: 14px; margin: 12px 0; border-radius: 6px; border-right: 4px solid #7c3aed; border: 1px solid #e2e8f0; font-size: 14.5px; }}
.aspect {{ border-right-color: #0d9488; background: #f0fdfa; }}
table.astro-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 14.5px; text-align: right; }}
table.astro-table th, table.astro-table td {{ padding: 10px 12px; border-bottom: 1px solid #e2e8f0; }}
table.astro-table th {{ background: #5b21b6; color: white; }}
table.astro-table tr:hover {{ background-color: #f1f5f9; }}
</style>
</head>
<body>
<div class="container">

    <div class="page">
        <h1>التقرير الفلكي الاستشاري للعودة السنوية ({html.escape(str(personal_info['target_year']))})</h1>
        <h2>بيانات الخريطة والحالة الأساسية</h2>
        {info_html}
    </div>

    <div class="page">
        <h2>ملخص السنوية لغير الفلكيين (إجابات مباشرة ومحددة بالشهور)</h2>
        {summary_html}
    </div>

    <div class="page">
        <h2>تقييم بيوت السنوية ومواعيد تفعيلها الشهرية</h2>
        {eval_html}
    </div>

    <div class="page">
        <h2>التفاصيل الدقيقة لتأثير الكواكب في البيوت</h2>
        {h_html}
    </div>

    <div class="page">
        <h2>هندسة الاتصالات (الزوايا الفلكية)</h2>
        {a_html if a_html else "<p>لا توجد اتصالات رئيسية دقيقة بين الكواكب السنوية هذا العام.</p>"}
    </div>

    <div class="page">
        <h2>إحداثيات الكواكب في خريطة العودة السنوية</h2>
        <table class="astro-table">
            <thead>
                <tr><th>الكوكب</th><th>البرج والدرجة</th><th>البيت السنوي</th><th>حالة الحركة</th></tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    </div>

</div>
</body>
</html>"""

# ==================== الواجهة الرئيسية للتطبيق (Streamlit) ====================
def main():
    st.markdown("<h2 style='color: #4c1d95; font-weight:800;'>🔮 رادار التوقعات السنوية المتقدم والاستشاري</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #475569;'>استخراج خرائط العودة السنوية مع تقرير مبسط لغير الفلكيين يحدد التوقيت بالشهور للأفراد والشركات والدول.</p>", 
unsafe_allow_html=True)
    st.markdown("<p style='color: #475569;'>تطوير الفلكي استرو رادار.</p>", 
unsafe_allow_html=True)

    
    countries = load_countries()
    country_options = sorted([(f"{c['name']} ({c['iso']})", c['iso']) for c in countries.values()], key=lambda x: x[0])
    country_display = [x[0] for x in country_options]
    country_codes = [x[1] for x in country_options]
    
    time_options = ["الساعة غير معروفة"] + [time(h, m).strftime('%H:%M') for h in range(24) for m in range(0, 60, 5)]
    default_time_idx = time_options.index("11:40") if "11:40" in time_options else 0

    name_input = st.text_input("الاسم (دولة، مؤسسة/شركة، شخص)", value="New")
    
    col1, col2 = st.columns(2)
    with col1:
        gender_select = st.selectbox("الجنس / نوع الكيان", ["ذكر", "أنثى", "مؤسسة/دولة"], index=0)
    with col2:
        target_year_select = st.selectbox("السنة المستهدفة للتوقع", [str(y) for y in range(1900, 2100)], index=126) # 2026

    target_type = "individual"
    if gender_select == "مؤسسة/دولة":
        entity_type = st.radio("تصنيف الكيان لتحسين التحليل الفلكي دلالياً:", ["دولة", "شركة / مؤسسة"], horizontal=True)
        target_type = "country" if entity_type == "دولة" else "company"

    col3, col4 = st.columns(2)
    with col3:
        birth_date_val = st.date_input("تاريخ الميلاد / التأسيس", value=datetime(1990, 1, 17), min_value=datetime(1900, 1, 1), max_value=datetime(2100, 12, 31))
    with col4:
        time_select = st.selectbox("ساعة الميلاد", time_options, index=default_time_idx)

    st.divider()
    st.markdown("#### بيانات الولادة (أو التأسيس / الاستقلال)")
    
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

    st.divider()
    st.markdown("#### بيانات مكان السنوية (المكان المتواجد به الشخص أو مقر الكيان الحالي)")
    
    ae_index = country_codes.index("AE") if "AE" in country_codes else 0
    r_country_display = st.selectbox("دولة السنوية الحالية", country_display, index=ae_index)
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

    if st.button("🚀 تحليل واستخراج التقرير الاستشاري الشامل", use_container_width=True):
        if not b_city or not r_city:
            st.error("يرجى التأكد من اختيار المدن بشكل صحيح.")
            return
            
        with st.spinner("جاري حساب العودة الشمسية وتوقيت البيوت الشهرية وتوليد التحليل التنفيذي..."):
            try:
                t_year = int(target_year_select)
                b_date = birth_date_val
                
                b_time = "الساعة غير معروفة" if time_select == "الساعة غير معروفة" else time(*map(int, time_select.split(":")))
                
                chart = calculate_chart(b_date, b_time, b_city, r_city, t_year)
                usm_rows = run_usm_engine_daily(b_date)
                usm_row = next((r for r in usm_rows if r.age == (t_year - b_date.year)), usm_rows[0])
                
                house_evals = evaluate_houses(chart)
                house_preds, aspect_preds = generate_dynamic_predictions(chart, target_type=target_type)
                plain_summary = generate_plain_summary(chart, target_type, usm_row)
                
                time_str = "غير معروفة" if isinstance(b_time, str) else b_time.strftime('%H:%M')
                personal_info = {
                    "name": name_input,
                    "gender": gender_select,
                    "dob": b_date.strftime('%Y-%m-%d'),
                    "time": time_str,
                    "birth_place": f"{b_city.name}، {b_city.country_code}",
                    "target_year": t_year,
                    "target_type": target_type
                }
                
                report_html_data = build_report_html(personal_info, chart, usm_row, house_evals, house_preds, aspect_preds, plain_summary)
                
                # عرض الملخص المباشر في Streamlit
                st.markdown(f"### 📋 الملخص التنفيذي لـ {name_input} لسنة {t_year}")
                
                if usm_row.status == "CRITICAL":
                    st.error("⚠️ حالة السنة في رادار السنوات الكبرى: حرجة ومفصلية (تحولات كبرى)", icon="⚠️")
                else:
                    st.success("✅ حالة السنة في رادار السنوات الكبرى: مسار اعتيادي ومستقر", icon="✅")
                    
                st.info(f"طالع السنوية: **{chart.solar_asc_sign}** | تاريخ العودة الشمسية الدقيق: **{chart.return_local.strftime('%Y-%m-%d %H:%M')}**")
                
                # عرض بطاقات الملخص البشري
                for key, val in plain_summary.items():
                    with st.expander(f"📌 {key}", expanded=True):
                        if isinstance(val, dict):
                            for sub_k, sub_v in val.items():
                                if isinstance(sub_v, list):
                                    st.markdown(f"**{sub_k}:**")
                                    for item in sub_v:
                                        st.markdown(f"- {item}", unsafe_allow_html=True)
                                else:
                                    st.markdown(f"**{sub_k}:** {sub_v}", unsafe_allow_html=True)
                        elif isinstance(val, list):
                            for item in val:
                                st.markdown(f"- {item}", unsafe_allow_html=True)
                        else:
                            st.markdown(val, unsafe_allow_html=True)

                st.divider()
                st.download_button(
                    label="💾 تنزيل التقرير الاستشاري الكامل القابل للطباعة (HTML / PDF)",
                    data=report_html_data.encode("utf-8"),
                    file_name=f"Solar_Report_{name_input}_{t_year}.html",
                    mime="text/html",
                    use_container_width=True
                )

            except Exception as ex:
                st.error(f"حدث خطأ أثناء المعالجة: {ex}")
                st.code(traceback.format_exc())

if __name__ == "__main__":
    main()
