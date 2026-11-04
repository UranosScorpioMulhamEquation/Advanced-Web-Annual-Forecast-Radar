from __future__ import annotations

import io
import math

import geonamescache
import pandas as pd
import streamlit as st
import swisseph as swe
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import NamedTuple
from timezonefinder import TimezoneFinder
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import os
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

# ==================== الثوابت وقوائم الكواكب والحكام ====================

TARGET_PLANETS = ['Mars', 'Rahu', 'Ketu', 'Saturn', 'Neptune', 'Uranus', 'Pluto']
SLOW_PLANETS = ['Jupiter', 'Saturn', 'Uranus', 'Neptune', 'Pluto']
HAZARD_CONJUNCT_PLANETS = ['Rahu', 'Ketu', 'Mars', 'Pluto', 'Neptune', 'Uranus', 'Saturn']

ORB = 3.0             # 3 درجات قوسية للكواكب حسب معايير اللجنة
ANGULAR_ORB = 6.0     # 0 إلى 6 درجات أقصى حد مسموح للاقتران بالأوتاد والبيوت (1، 6، 8، 12)
URANUS_CYCLE_DIVISOR = 4.2857  # معامل التقسيم الخاص بالنظرية (دورة أورانوس ~84 سنة)

PLANET_IDS = {
    'Sun': swe.SUN,
    'Moon': swe.MOON,
    'Mars': swe.MARS,
    'Jupiter': swe.JUPITER,
    'Saturn': swe.SATURN,
    'Uranus': swe.URANUS,
    'Neptune': swe.NEPTUNE,
    'Pluto': swe.PLUTO,
    'Rahu': swe.MEAN_NODE,
    'Ketu': -1,  # يُحسب تلقائياً بإضافة 180 درجة لـ Rahu
}

PLANET_NAMES_AR = {
    'Sun': 'الشمس',
    'Moon': 'القمر',
    'Mars': 'المريخ',
    'Jupiter': 'المشتري',
    'Saturn': 'زحل',
    'Uranus': 'أورانوس',
    'Neptune': 'نبتون',
    'Pluto': 'بلوتو',
    'Rahu': 'راخو (العقدة الشمالية)',
    'Ketu': 'كيتو (العقدة الجنوبية)'
}

SIGN_NAMES_AR = [
    'الحمل', 'الثور', 'الجوزاء', 'السرطان',
    'الأسد', 'العذراء', 'الميزان', 'العقرب',
    'القوس', 'الجدي', 'الدلو', 'الحوت'
]

# جدول حكام الأبراج للتحقق من حاكم الطالع
SIGN_RULERS = {
    0: ['Mars'],               # الحمل
    1: ['Venus'],              # الثور
    2: ['Mercury'],            # الجوزاء
    3: ['Moon'],               # السرطان
    4: ['Sun'],                # الأسد
    5: ['Mercury'],            # العذراء
    6: ['Venus'],              # الميزان
    7: ['Mars', 'Pluto'],      # العقرب
    8: ['Jupiter'],            # القوس
    9: ['Saturn'],             # الجدي
    10: ['Saturn', 'Uranus'],  # الدلو
    11: ['Jupiter', 'Neptune'] # الحوت
}

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
    risk_year: int             # السنة الحرجة كعدد صحيح
    risk_power: str            # قوة الخطر (عالي جداً / متوسط)
    trigger_planets: str       # الكواكب مسببة الخطر
    mechanism: str             # كيفية الخطر والاتصالات الفلكية
    risk_type: str             # نمط الخطر المالي / الصحي / الساسي / الهيكلي
    astrological_details: str  # التفاصيل والاتصالات الفلكية الدقيقة
    quarter: str               # الربع السنوي المتوقع الخطر داخله
    exact_date: date
    age: float
    cycle_type: str
    condition_2_met: bool
    is_priority_planet: bool

# ==================== تحميل البيانات الجغرافية ====================

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

# ==================== الحسابات الفلكية والأدوات المساعدة ====================

def get_quarter_string(month: int) -> str:
    """تحديد الربع السنوي بناءً على الشهر"""
    if 1 <= month <= 3:
        return "الربع الأول (Q1)"
    elif 4 <= month <= 6:
        return "الربع الثاني (Q2)"
    elif 7 <= month <= 9:
        return "الربع الثالث (Q3)"
    else:
        return "الربع الرابع (Q4)"

def get_julian_day(dt_utc: datetime) -> float:
    """تحويل التاريخ والوقت (UTC) إلى التاريخ اليولياني (Julian Day)"""
    decimal_hour = dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, decimal_hour)

def get_planet_longitude(planet_name: str, dt_utc: datetime) -> float:
    """حساب درجة موقع الكوكب أو النقطة بدقة عالية من 0 الحمل"""
    jd = get_julian_day(dt_utc)
    if planet_name == 'Ketu':
        rahu_pos = swe.calc_ut(jd, swe.MEAN_NODE)[0][0]
        return (rahu_pos + 180.0) % 360.0
    
    planet_id = PLANET_IDS.get(planet_name)
    if planet_id is not None:
        res = swe.calc_ut(jd, planet_id)
        return res[0][0]
    
    raise ValueError(f"اسم الكوكب غير معروف: {planet_name}")

def calculate_whole_sign_houses(ascendant_longitude: float) -> dict[int, float]:
    """توزيع البيوت بنظام البرج الكامل (Whole Sign / كل برج بيت)"""
    ascendant_sign = int(ascendant_longitude // 30)
    houses = {}
    for i in range(12):
        house_number = i + 1
        sign_index = (ascendant_sign + i) % 12
        houses[house_number] = sign_index * 30.0
    return houses

def get_house_from_pos(pos: float, asc_longitude: float) -> int:
    """معرفة رقم البيت (1-12) بناءً على موقعه ونظام البرج الكامل"""
    asc_sign = int(asc_longitude // 30)
    target_sign = int(pos // 30)
    return ((target_sign - asc_sign) % 12) + 1

def is_within_orb(pos1: float, pos2: float, orb: float = ORB) -> bool:
    """التحقق مما إذا كانت المسافة القوسية ضمن الجرم المسموح"""
    diff = abs(pos1 - pos2)
    diff = min(diff, 360.0 - diff)
    return diff <= orb

def get_aspect(pos1: float, pos2: float, orb: float = ORB) -> str | None:
    """تحديد زاوية الاتصال الفلكي الرئيسية (اقتران، مقابلة، تربيع)"""
    diff = abs(pos1 - pos2)
    diff = min(diff, 360.0 - diff)
    
    if diff <= orb:
        return "اقتران (Conjunction)"
    elif abs(diff - 180.0) <= orb:
        return "مقابلة (Opposition)"
    elif abs(diff - 90.0) <= orb:
        return "تربيع (Square)"
    return None

def is_planet_ruler_or_near_asc(planet_name: str, transit_dt: datetime, natal_asc: float, natal_rulers: list[str]) -> bool:
    """التحقق مما إذا كان الكوكب العابر (أو مقترنه) حاكماً للطالع أو قريباً من درجة الطالع"""
    if planet_name in natal_rulers:
        return True
    
    planet_pos = get_planet_longitude(planet_name, transit_dt)
    if is_within_orb(planet_pos, natal_asc, ORB):
        return True
        
    for h_p in HAZARD_CONJUNCT_PLANETS:
        if h_p == planet_name:
            continue
        h_pos = get_planet_longitude(h_p, transit_dt)
        t_pos = get_planet_longitude(planet_name, transit_dt)
        if is_within_orb(h_pos, t_pos, ORB):
            if h_p in natal_rulers or is_within_orb(h_pos, natal_asc, ORB):
                return True
                
    return False

# ==================== المحرك الدقيق لتحديد نمط الخطر ====================

def determine_risk_pattern(entity_type: str, active_transits: list[str], target_houses: list[int], aspect_details: list[str]) -> tuple[str, str]:
    """
    تحديد نمط الخطر بدقة كاملة بناءً على نوع الكيان والبيوت المضروبة والكواكب المؤثرة والاتصالات.
    """
    houses_set = set(target_houses)
    transits_set = set(active_transits)
    
    if entity_type == "فرد":
        # 1. خطر صحي (البيت 6 أو 12 أو 1 مع حضور كواكب العنف والمرض زحل/مريخ/نبتون)
        if (6 in houses_set or 12 in houses_set) and ('Saturn' in transits_set or 'Mars' in transits_set or 'Neptune' in transits_set):
            pattern = "خطر صحي جسدي / استنزاف بدني ونفسي"
            desc = "تأثير عبور نحس على بيوت الصحة والمرض (البيت 6 أو 12) أو الطالع، يتطلب مراقبة الصحة والوقاية الجسدية."
        # 2. خطر على المنصب المهني والسمعة (البيت 10 أو 1 مع زحل/أورانوس/بلوتو)
        elif (10 in houses_set or 1 in houses_set) and ('Saturn' in transits_set or 'Uranus' in transits_set or 'Pluto' in transits_set):
            pattern = "خطر على المنصب المهني / السمعة الاجتماعية"
            desc = "ضغط شديد أو تغييرات راديكالية مفاجئة تمس الموقع الوظيفي، المكانة الإدارية، أو السمعة العامة."
        # 3. خطر عائلي لأحد أفراد العائلة (البيت 4 أو 8 أو 12)
        elif (4 in houses_set or 8 in houses_set) and ('Saturn' in transits_set or 'Ketu' in transits_set or 'Neptune' in transits_set):
            pattern = "خطر على أحد أفراد العائلة / استقرار المأوى"
            desc = "تأثير على بيوت الأصول والعائلة والجذور، قد يعكس اضطرابات عائلية، ممتلكات، أو ظروفاً تخص الأقارب."
        # 4. خطر مع الشريك / المشاكل الزوجية (البيت 7 أو المقابلة مع الطالع)
        elif 7 in houses_set or any("مقابلة" in asp for asp in aspect_details if "البيت (1)" in asp or "الطالع" in asp):
            pattern = "خطر مع الشريك / مشاكل وتوترات زوجية وتعاقدية"
            desc = "تعارض شديد وزوايا مواجهة مسلطة على بيت الشراكة والزواج، تهدد باتساع الفجوة أو انفصال عقدي/زوجي."
        # 5. خطر مالي وخسائر (البيت 2 أو 8 مع بلوتو/أورانوس/زحل)
        elif (2 in houses_set or 8 in houses_set) or ('Pluto' in transits_set or 'Uranus' in transits_set):
            pattern = "خطر مالي / خسائر وتغييرات نقدية مفاجئة"
            desc = "تقلبات مالية حادة، خسائر غير متوقعة، أو ديون وتزامات طارئة تؤثر على الاستقرار المالي والتراكمي."
        else:
            pattern = "خطر صحي ونفسي عام"
            desc = "ضغط فلكي عام ينعكس على الطاقة الحيوية والسلامة الشخصية."

    elif entity_type == "دولة":
        # 1. خطر أمني - عسكري (البيت 6 أو 8 أو 12 مع المريخ/بلوتو/أورانوس)
        if (6 in houses_set or 8 in houses_set or 12 in houses_set) and ('Mars' in transits_set or 'Pluto' in transits_set or 'Uranus' in transits_set):
            pattern = "خطر أمني - عسكري / اضطرابات وحوادث طارئة"
            desc = "عبور كواكب العنف والطاقة القاسية في بيوت الأزمات والطوارئ للدولة، مما يشير إلى توترات أمنية أو مواجهات."
        # 2. خطر تغيير شامل ونظام (البيت 1 أو 10 مع أورانوس/بلوتو)
        elif (1 in houses_set or 10 in houses_set) and ('Uranus' in transits_set or 'Pluto' in transits_set):
            pattern = "خطر تغيير شامل / إعادة هيكلة النظام والسلطة"
            desc = "تحولات سياسية جارفة، إعادة رسم الهيكلية الحاكمة، أو تغيّر حاد في رأس السلطة والقيادة العليا."
        # 3. خطر شعبي واضطرابات اجتماعية (البيت 4 أو 7 مع زحل/أورانوس)
        elif (4 in houses_set or 7 in houses_set) and ('Saturn' in transits_set or 'Uranus' in transits_set or 'Rahu' in transits_set):
            pattern = "خطر شعبي / حراك واضطرابات داخلية"
            desc = "ضغط على الأرض والشعب والأصول الوطنية، ينعكس في حالة سخط، احتجاجات، أو إعادة تشكيل المشهد الاجتماعي."
        # 4. خطر اقتصادي ومالي (البيت 2 أو 8 أو 10 مع زحل/نبتون/بلوتو)
        else:
            pattern = "خطر اقتصادي / أزمة مالية وتضخم"
            desc = "ضغوط شديدة على الخزانة الوطنية، تراجع في مؤشرات النمو، أو انخفاض العملة والقدرة الاقتصادية للدولة."

    else:  # شركة
        # 1. خطر هيكلي وإداري (البيت 1 أو 10 أو 4 مع أورانوس/زحل/بلوتو)
        if (10 in houses_set or 1 in houses_set or 4 in houses_set) and ('Uranus' in transits_set or 'Saturn' in transits_set or 'Pluto' in transits_set):
            pattern = "خطر هيكلي / إعادة تنظيم وإدارة المؤسسة"
            desc = "تغييرات قسرية في مجالس الإدارة، تفكيك أجزاء من الشركة، أو مخاطر تمس الهيكل التنفيذي والترخيص."
        # 2. خطر مالي على ميزانية الشركة (البيت 2 أو 8 أو 6 أو 12 مع أي من الكواكب النحسة)
        else:
            pattern = "خطر مالي على ميزانية الشركة / سيولة ومبيعات"
            desc = "عجز مالي، خسائر استثمارية، تراجع المبيعات، أو التزامات ضريبية وديون تهدد الاستقرار المالي للمؤسسة."

    return pattern, desc

# ==================== دالة توليد تقرير HTML للطباعة ====================

def generate_html_report(name: str, entity_type: str, dob: date, start_year: int, end_year: int, asc_deg: float, results: list[USMRow]) -> str:
    asc_sign = SIGN_NAMES_AR[int(asc_deg // 30)]
    rows_html = ""
    for r in results:
        badge_class = "danger" if "عالي" in r.risk_power or "شديد" in r.risk_power else "warning"
        rows_html += f"""
        <tr>
            <td style="font-weight: bold; text-align: center;">{r.risk_year}</td>
            <td style="text-align: center;"><span class="badge {badge_class}">{r.risk_power}</span></td>
            <td><strong style="color: #8b0000;">{r.risk_type}</strong></td>
            <td>{r.trigger_planets}</td>
            <td style="font-size: 0.9em; line-height: 1.4;">{r.astrological_details}</td>
            <td style="text-align: center;">{r.quarter}</td>
        </tr>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>تقرير استرو رادار - {name}</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap');
            body {{
                font-family: 'Cairo', sans-serif;
                background-color: #f4f6f9;
                color: #1a252f;
                margin: 0;
                padding: 20px;
                direction: rtl;
            }}
            .container {{
                max-width: 1100px;
                margin: 0 auto;
                background: #ffffff;
                padding: 30px;
                border-radius: 12px;
                box-shadow: 0 5px 25px rgba(0,0,0,0.08);
            }}
            .header {{
                text-align: center;
                border-bottom: 3px solid #1a365d;
                padding-bottom: 20px;
                margin-bottom: 25px;
            }}
            .header h1 {{
                color: #1a365d;
                margin: 0 0 10px 0;
                font-size: 26px;
            }}
            .header p {{
                color: #4a5568;
                margin: 5px 0;
                font-size: 14px;
            }}
            .meta-grid {{
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 15px;
                background: #edf2f7;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 25px;
                font-size: 14px;
            }}
            .meta-item strong {{
                color: #2b6cb0;
                display: block;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }}
            th {{
                background-color: #1a365d;
                color: white;
                padding: 12px;
                font-size: 14px;
                border: 1px solid #2b6cb0;
            }}
            td {{
                padding: 10px 12px;
                border: 1px solid #e2e8f0;
                font-size: 13px;
                vertical-align: middle;
            }}
            tr:nth-child(even) {{
                background-color: #f8fafc;
            }}
            .badge {{
                padding: 4px 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
                color: white;
                display: inline-block;
            }}
            .badge.danger {{
                background-color: #c53030;
            }}
            .badge.warning {{
                background-color: #dd6b20;
            }}
            .footer {{
                margin-top: 30px;
                text-align: center;
                font-size: 12px;
                color: #718096;
                border-top: 1px solid #e2e8f0;
                padding-top: 15px;
            }}
            .print-btn {{
                background-color: #2b6cb0;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 15px;
                font-family: 'Cairo', sans-serif;
                border-radius: 6px;
                cursor: pointer;
                margin-bottom: 20px;
            }}
            .print-btn:hover {{
                background-color: #2c5282;
            }}
            @media print {{
                .print-btn {{ display: none; }}
                body {{ padding: 0; background: white; }}
                .container {{ box-shadow: none; border-radius: 0; max-width: 100%; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <button class="print-btn" onclick="window.print()">🖨️ طباعة التقرير / حفظ PDF</button>
            
            <div class="header">
                <h1>📊 تقرير تحليل السنوات الحرجة والمخاطر (Astro Radar)</h1>
                <p>تطبيق خوارزمية دورة أورانوس (84 سنة) ونظام كل برج بيت - التنجيم الغربي التروبيكال</p>
            </div>

            <div class="meta-grid">
                <div class="meta-item"><strong>اسم الكيان/الشخص:</strong> {name}</div>
                <div class="meta-item"><strong>تصنيف الكيان:</strong> {entity_type}</div>
                <div class="meta-item"><strong>تاريخ الأساس:</strong> {dob.strftime('%Y-%m-%d')}</div>
                <div class="meta-item"><strong>برج الطالع (الشمسي):</strong> {asc_sign} ({asc_deg:.2f}°)</div>
            </div>

            <table>
                <thead>
                    <tr>
                        <th style="width: 10%;">السنة الحرجة</th>
                        <th style="width: 12%;">شدة الخطر</th>
                        <th style="width: 20%;">نمط الخطر المحدد</th>
                        <th style="width: 18%;">الكواكب المسببة</th>
                        <th style="width: 28%;">التفاصيل والاتصالات الفلكية</th>
                        <th style="width: 12%;">الربع المتوقع</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>

            <div class="footer">
                <p>تم استخراج التقرير بواسطة نظام استرو رادار المطور - إعداد الدكتور المبرمج ملهم أحمد © {datetime.now().year}</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html_content

# ==================== الدالة الرئيسية للتطبيق ====================

def libephemeris():
    st.set_page_config(page_title="استرو رادار- توقيت الخطر الجسيم", layout="wide")
    st.title("نظام نظرية استرو رادار المطور- توقيت الخطر الجسيم - نسخة الأفراد و الشركات و الدول")
    st.caption("نظام كل برج بيت - تثبيت 84 سنة دورة أورانوس الكاملة - أوربت 3.0 درجات - نطاق 0-6 درجات للأوتاد - تصنيف كامل للمخاطر - (تطوير الفلكي و المبرمج الدكتور : ملهم احمد)")
    st.markdown("---")

    # تحميل بيانات الدول والمدن
    countries_data = load_countries()
    country_options = {f"{c['name']} ({code})": code for code, c in countries_data.items()}
    sorted_country_names = sorted(country_options.keys())

    col1, col2, col3 = st.columns(3)

    with col1:
        name = st.text_input("اسم الفرد / الكيان / الدولة", "الاسم")
        entity_type = st.selectbox("نوع الكيان (محدد نمط الخطر)", ["فرد", "دولة", "شركة"])
        selected_country_label = st.selectbox("اختر الدولة", sorted_country_names)
        selected_country_code = country_options[selected_country_label]

    with col2:
        available_cities = get_cities_by_country(selected_country_code)
        if available_cities:
            city_names = [f"{c.name} (تعداد: {c.population:,})" for c in available_cities]
            selected_city_index = st.selectbox("اختر المدينة", range(len(city_names)), format_func=lambda x: city_names[x])
            selected_city = available_cities[selected_city_index]
        else:
            st.error("لم يتم العثور على مدن لهذه الدولة.")
            selected_city = None

        dob = st.date_input("تاريخ الميلاد / الاستقلال / التأسيس", min_value=date(1800, 1, 1), max_value=date(2100, 1, 1), value=date(1990, 1, 1))

    with col3:
        # إلغاء إدخال ساعة الميلاد واعتماد منتصف النهار افتراضياً وتثبيت نظام كل برج بيت
        tob = time(12, 0)
        st.info("تم اعتماد نظام (كل برج بيت - Whole Sign) برفع البرج الشمسي كطالع تلقائياً.")

        # تثبيت سنة التوقع لـ 84 سنة تلقائياً
        start_year = dob.year
        end_year = start_year + 84
        st.write(f"**نطاق التوقع الممتد تلقائياً (84 سنة - دورة أورانوس):** {start_year} - {end_year}")

    # زر التحليل والتنفيذ
    if st.button("تشغيل خوارزمية تحليل النظرية وتحديد نمط الخطر", type="primary", width='stretch'):
        if not name:
            st.warning("يرجى إدخال الاسم قبل بدء التحليل.")
            st.stop()
        if not selected_city:
            st.error("يرجى اختيار مدينة صحيحة.")
            st.stop()

        with st.spinner("جاري معالجة المواضع الفلكية وتحديد الاتصالات وأنماط المخاطر بدقة (84 سنة)..."):
            
            # ضبط التوقيت العالمي (UTC) افتراضياً عند منتصف النهار (12:00)
            tz_str = get_timezone_for_city(selected_city)
            if tz_str:
                try:
                    local_tz = ZoneInfo(tz_str)
                    local_dt = datetime.combine(dob, tob).replace(tzinfo=local_tz)
                    utc_dt = local_dt.astimezone(timezone.utc)
                except ZoneInfoNotFoundError:
                    utc_dt = datetime.combine(dob, tob).replace(tzinfo=timezone.utc)
            else:
                utc_dt = datetime.combine(dob, tob).replace(tzinfo=timezone.utc)

            # تحديد نظام البيوت والطالع بناءً على نظام (كل برج بيت - Whole Sign) اعتماداً على البرج الشمسي
            asc_degree = get_planet_longitude("Sun", utc_dt)
            houses = calculate_whole_sign_houses(asc_degree)
            house_system_name = "Whole Sign (كل برج بيت)"

            # تحديد حاكم الطالع
            asc_sign_index = int(asc_degree // 30)
            natal_rulers = SIGN_RULERS.get(asc_sign_index, ['Mars'])

            # حساب مواقع الكواكب ومسافة 0 الحمل
            natal_positions = {}
            distances_from_aries = {}
            for planet in TARGET_PLANETS:
                pos = get_planet_longitude(planet, utc_dt)
                natal_positions[planet] = pos
                distances_from_aries[planet] = pos % 360.0

            priority_planet = min(distances_from_aries, key=distances_from_aries.get)

            # بناء نقاط الأوتاد والبيوت الحساسة (1، 6، 8، 12)
            angular_houses = [1, 6, 8, 12]
            target_house_cusps = {h: houses[h] for h in angular_houses}

            usm_results: list[USMRow] = []

            # فحص دورات الكواكب
            for planet, natal_pos in natal_positions.items():
                base_age = distances_from_aries[planet] / URANUS_CYCLE_DIVISOR
                
                cycles_to_check = [
                    (base_age, "دورة أساسية"),
                    (base_age + 42.0, "دورة المعارضة (42 سنة)"),
                    (base_age + 84.0, "دورة العودة (84 سنة)")
                ]

                is_priority = (planet == priority_planet)

                for target_age, cycle_label in cycles_to_check:
                    days_to_add = target_age * 365.2425
                    target_utc_date = utc_dt + timedelta(days=days_to_add)
                    
                    # استخراج السنة كعدد صحيح
                    current_risk_year = int(target_utc_date.year)

                    # فحص نطاق الـ 84 سنة المعتمد
                    if start_year <= current_risk_year <= end_year:
                        condition_1_met = False
                        active_transits = []
                        matched_mechanisms = []
                        matched_houses = []
                        aspect_details = []

                        for t_planet in SLOW_PLANETS:
                            t_pos = get_planet_longitude(t_planet, target_utc_date)
                            hit_angle = False
                            t_ar = PLANET_NAMES_AR.get(t_planet, t_planet)

                            # تحديد رقم البيت الحاضن للكوكب العابر
                            h_num = get_house_from_pos(t_pos, asc_degree)

                            # فحص الاتصالات مع درجات الأوتاد والبيوت الحساسة (1، 6، 8، 12)
                            for target_h, cusp_deg in target_house_cusps.items():
                                aspect_type = get_aspect(t_pos, cusp_deg, ANGULAR_ORB)
                                if aspect_type:
                                    hit_angle = True
                                    matched_houses.append(target_h)
                                    asp_desc = f"{t_ar} في حالة {aspect_type} مع البيت ({target_h})"
                                    aspect_details.append(asp_desc)
                                    matched_mechanisms.append(asp_desc)

                            if hit_angle:
                                condition_1_met = True
                                if t_planet not in active_transits:
                                    active_transits.append(t_planet)

                        # فحص الشرط الإضافي للمخاطر الشديدة (الاقتران أو رهن حاكم الطالع)
                        condition_2_met = False
                        if condition_1_met:
                            for active_p in active_transits:
                                is_conjunct_hazard = active_p in HAZARD_CONJUNCT_PLANETS
                                if not is_conjunct_hazard:
                                    for h_c in HAZARD_CONJUNCT_PLANETS:
                                        if is_within_orb(get_planet_longitude(active_p, target_utc_date), get_planet_longitude(h_c, target_utc_date), ORB):
                                            is_conjunct_hazard = True
                                            break
                                
                                is_ruler_or_asc = is_planet_ruler_or_near_asc(active_p, target_utc_date, asc_degree, natal_rulers)

                                if is_conjunct_hazard and is_ruler_or_asc:
                                    condition_2_met = True
                                    matched_mechanisms.append("اقتران مباشر/اتصال قاسي بحاكم الطالع")
                                    break

                        if condition_1_met:
                            # تحديث قوة الخطر
                            risk_power = "خطر شديد جداً (تحول حاد)" if condition_2_met else "تنبيه خطر متوسط على البيوت"
                            
                            trigger_ar = PLANET_NAMES_AR.get(planet, planet)
                            active_ar_list = [PLANET_NAMES_AR.get(p, p) for p in active_transits]
                            trigger_planets_str = f"{trigger_ar} (عبور: {', '.join(active_ar_list)})"
                            
                            # تحديد نمط الخطر والتفاصيل
                            risk_pattern, risk_desc = determine_risk_pattern(entity_type, active_transits, matched_houses, aspect_details)

                            mechanism_str = " | ".join(set(matched_mechanisms)) if matched_mechanisms else "عبور كواكب بطيئة على البيوت الحساسة"
                            astrology_full_info = f"{mechanism_str}. {risk_desc}"
                            quarter_str = get_quarter_string(target_utc_date.month)

                            usm_results.append(
                                USMRow(
                                    risk_year=current_risk_year,
                                    risk_power=risk_power,
                                    trigger_planets=trigger_planets_str,
                                    mechanism=mechanism_str,
                                    risk_type=risk_pattern,
                                    astrological_details=astrology_full_info,
                                    quarter=quarter_str,
                                    exact_date=target_utc_date.date(),
                                    age=target_age,
                                    cycle_type=cycle_label,
                                    condition_2_met=condition_2_met,
                                    is_priority_planet=is_priority
                                )
                            )

            # ==================== عرض الجدول والمخرجات ====================
            st.subheader(f"📊 جدول نتائج تحليل النظرية: {name} ({entity_type})")
            st.write(f"**نطاق التوقع:** {start_year} - {end_year} (84 سنة) | **نظام البيوت:** {house_system_name} | **درجة الطالع:** {asc_degree:.2f}° | **الأوربت:** {ORB}°")

            if not usm_results:
                st.success("الوضع الفلكي مستقر: لم يتم رصد تقاطعات تطابق الشروط الحرجة ضمن نطاق الـ 84 سنة.")
            else:
                # ترتيب النتائج حسب السنة
                usm_results.sort(key=lambda x: x.risk_year)

                # بناء DataFrame يطابق جدول المخرجات المطلوبة
                table_data = []
                for r in usm_results:
                    table_data.append({
                        "السنوات الحرجة": r.risk_year,
                        "قوة الخطر": r.risk_power,
                        "نمط الخطر المحدد": r.risk_type,
                        "الكواكب مسببة الخطر": r.trigger_planets,
                        "توضيح الاتصالات والبيوت الفلكية": r.astrological_details,
                        "الربع السنوي المتوقع": r.quarter
                    })

                df_display = pd.DataFrame(table_data)

                # عرض الجدول بشكل منسق وأنيق على واجهة Streamlit
                st.dataframe(
                    df_display,
                    width='stretch',
                    hide_index=True,
                    column_config={
                        "السنوات الحرجة": st.column_config.NumberColumn("السنوات الحرجة", format="%d"),
                    }
                )

                # ==================== قسم تقرير HTML والطباعة ====================
                st.markdown("---")
                st.subheader("📄 تقرير HTML التفاعلي الجاهز للطباعة")
                
                html_report_code = generate_html_report(
                    name=name,
                    entity_type=entity_type,
                    dob=dob,
                    start_year=start_year,
                    end_year=end_year,
                    asc_deg=asc_degree,
                    results=usm_results
                )

                st.download_button(
                    label="🖨️ تحميل التقرير بصيغة HTML (قابل للطباعة المباشرة)",
                    data=html_report_code,
                    file_name=f"Astro_Radar_Report_{name}_{dob.year}.html",
                    mime="text/html",
                    type="primary",
                    width='stretch'
                )
# تشغيل التطبيق
if __name__ == "__main__":
    libephemeris()