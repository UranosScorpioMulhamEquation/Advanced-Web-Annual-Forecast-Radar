import datetime
import os
import base64
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass

import geonamescache
import pandas as pd
import pytz
import streamlit as st
import swisseph as swe
from timezonefinder import TimezoneFinder

# ==========================================
# إعدادات تقويم سويس إفيميريس (Swiss Ephemeris)
# ==========================================
swe.set_ephe_path('')  # استخدام وضع Moshier الافتراضي للتقويم الفلكي الدقيق

st.set_page_config(
    page_title="النظام المتقدم الشامل للأستروكارتوغرافيا المجالية",
    page_icon="🌟",
    layout="wide"
)

# ==========================================
# دعم اللغة العربية والاتجاه من اليمين لليسار (RTL)
# ==========================================
st.markdown(
    """
    <style>
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stSidebar"] {
        direction: rtl;
        text-align: right;
        font-family: 'Tahoma', sans-serif;
    }
    .stSelectbox, .stTextInput, .stDateInput, .stTimeInput, .stButton, div[data-baseweb="select"], .stMarkdown, p, span, label, div {
        direction: rtl;
        text-align: right;
    }
    div[data-baseweb="base-input"] {
        direction: rtl;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================
# 1. الهياكل والبيانات الجغرافية العالمية
# ==========================================
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
def load_cities() -> List[City]:
    gc = geonamescache.GeonamesCache()
    cities_dict = gc.get_cities()
    cities_list = []
    for city_id, city_data in cities_dict.items():
        if city_data.get("population", 0) >= 15000:
            lat = city_data.get("latitude", 0.0)
            lon = city_data.get("longitude", 0.0)
            if -65.0 <= lat <= 65.0:  # استبعاد الأقطاب لضمان دقة خطوط الأوتاد
                cities_list.append(
                    City(
                        geonameid=str(city_id),
                        name=city_data.get("name", ""),
                        country_code=city_data.get("countrycode", ""),
                        latitude=lat,
                        longitude=lon,
                        admin1=city_data.get("admin1code", ""),
                        population=city_data.get("population", 0),
                    )
                )
    return cities_list

@st.cache_data
def load_countries() -> Dict[str, Dict[str, Any]]:
    gc = geonamescache.GeonamesCache()
    return gc.get_countries()

def get_cities_by_country(country_code: str) -> List[City]:
    cities = load_cities()
    return sorted(
        [c for c in cities if c.country_code == country_code],
        key=lambda c: c.population,
        reverse=True,
    )

@st.cache_resource
def get_tz_finder() -> TimezoneFinder:
    return TimezoneFinder()

tf = get_tz_finder()

countries_data = load_countries()
all_cities_list = load_cities()

country_name_to_code = {c_info["name"]: c_code for c_code, c_info in countries_data.items()}
sorted_country_names = sorted(list(country_name_to_code.keys()))

def get_utc_julian_day(date_obj: datetime.date, time_obj: datetime.time, tz_str: str) -> float:
    try:
        local_tz = pytz.timezone(tz_str)
    except Exception:
        local_tz = pytz.utc
    dt = datetime.datetime.combine(date_obj, time_obj)
    local_dt = local_tz.localize(dt)
    utc_dt = local_dt.astimezone(pytz.utc)
    return swe.julday(
        utc_dt.year,
        utc_dt.month,
        utc_dt.day,
        utc_dt.hour + utc_dt.minute / 60.0 + utc_dt.second / 3600.0,
    )

# ==========================================
# 2. القواميس الفلكية وتحديد مجالات الحياة (الدعم)
# ==========================================
def get_life_domains(planet: str, angle: str) -> List[str]:
    domains = []
    p = planet.split(" ")[0]
    
    if p in ["الشمس", "Sun"]:
        if "MC" in angle: domains.extend(["الشهرة والنجاح الجماهيري", "العمل والمهنة", "الثراء والوفرة المالية"])
        elif "AC" in angle: domains.extend(["الشهرة والنجاح الجماهيري", "التعليم والدراسة"])
        elif "DC" in angle: domains.extend(["الحب والزواج والشراكات"])
        elif "IC" in angle: domains.extend(["الاستقرار والسكن"])
    elif p in ["القمر", "Moon"]:
        if "IC" in angle: domains.extend(["الاستقرار والسكن"])
        elif "MC" in angle: domains.extend(["الشهرة والنجاح الجماهيري"])
        elif "DC" in angle: domains.extend(["الحب والزواج والشراكات"])
        elif "AC" in angle: domains.extend(["الاستقرار والسكن"])
    elif p in ["عطارد", "Mercury"]:
        if "MC" in angle or "AC" in angle: domains.extend(["التعليم والدراسة", "العمل والمهنة"])
        elif "DC" in angle: domains.extend(["الحب والزواج والشراكات"])
        elif "IC" in angle: domains.extend(["التعليم والدراسة"])
    elif p in ["الزهرة", "Venus"]:
        if "DC" in angle: domains.extend(["الحب والزواج والشراكات"])
        elif "IC" in angle: domains.extend(["الاستقرار والسكن"])
        elif "MC" in angle: domains.extend(["الثراء والوفرة المالية", "الشهرة والنجاح الجماهيري"])
        elif "AC" in angle: domains.extend(["الحب والزواج والشراكات", "الشهرة والنجاح الجماهيري"])
    elif p in ["المشتري", "Jupiter"]:
        if "MC" in angle: domains.extend(["الثراء والوفرة المالية", "الشهرة والنجاح الجماهيري", "العمل والمهنة"])
        elif "DC" in angle: domains.extend(["الحب والزواج والشراكات"])
        elif "IC" in angle: domains.extend(["الاستقرار والسكن"])
        elif "AC" in angle: domains.extend(["التعليم والدراسة", "الثراء والوفرة المالية"])
    elif p in ["المريخ", "Mars"]:
        if "MC" in angle or "AC" in angle: domains.extend(["العمل والمهنة"])
    elif p in ["زحل", "Saturn"]:
        if "MC" in angle: domains.extend(["العمل والمهنة"])
        elif "IC" in angle: domains.extend(["الاستقرار والسكن"])
    
    return list(set(domains)) if domains else ["العمل والمهنة", "الاستقرار والسكن"]

PLANET_DICTIONARY = {
    "الشمس (Sun)": {
        "nature": "إيجابي/داعم",
        "MC": "خط وسط السماء: ذروة الشهرة، الصعود المهني والقيادة الظاهرة والنجاح العام.",
        "AC": "خط الطالع: تعزيز الثقة الشخصية، الحيوية الجسدية وهيبة الحضور.",
        "DC": "خط الغارب: شراكات مع شخصيات نافذة ومرموقة وعلاقات علنية بارزة.",
        "IC": "خط جذر السماء: استقرار داخلي وتصالح مع الهوية والعائلة والجذور."
    },
    "القمر (Moon)": {
        "nature": "إيجابي/عاطفي",
        "MC": "خط وسط السماء: نجاح في مهن الجمهور، الإعلام، التغذية والرأي العام.",
        "AC": "خط الطالع: حساسية عالية، جاذبية شعبية وتفاعل وجداني مع المحيط.",
        "DC": "خط الغارب: علاقات عميقة تعتمد على الألفة العاطفية والحدس المشترك.",
        "IC": "خط جذر السماء: أفضل خط على الإطلاق للاستقرار العاطفي، السكن، وشراء العقارات والأمان النفسي."
    },
    "عطارد (Mercury)": {
        "nature": "إيجابي/فكري",
        "MC": "خط وسط السماء: نجاح في التجارة، الأعمال الحرة، الإعلام، والكتابة والتدريس.",
        "AC": "خط الطالع: نشاط ذهني متوقد، سرعة في البديهة والتواصل الفعّال.",
        "DC": "خط الغارب: نقاشات مثمرة، عقود تجارية ناجحة وشراكات فكرية.",
        "IC": "خط جذر السماء: بيئة منزلية محفزة للبحث، الدراسة والتواصل."
    },
    "الزهرة (Venus)": {
        "nature": "إيجابي للغاية",
        "MC": "خط وسط السماء: ازدهار مالي، مشاريع فنية أو تجارية مربحة وذوق رفيع.",
        "AC": "خط الطالع: سحر شخصي أخاذ، جاذبية عالية وحب وتقدير من المحيط.",
        "DC": "خط الغارب: أقوى وأفضل خط للحب، الزواج السعيد والشراكات العاطفية والانسجام.",
        "IC": "خط جذر السماء: منزل جميل مريح، بحبوحة عيش وراحة نفسية عميقة."
    },
    "المريخ (Mars)": {
        "nature": "طاقي/متحارب",
        "MC": "خط وسط السماء: طموح جريء، إنجاز مهني سريع، تنافسية عالية وقيادة ميدانية.",
        "AC": "خط الطالع: طاقة جسدية عالية وحماس، قد يصاحبها اندفاع أو صدامات.",
        "DC": "خط الغارب: توتر محتمل أو احتكاك في الشراكات، ومواجهات تنافسية.",
        "IC": "خط جذر السماء: أجواء متوترة في البيت وعدم استقرار أو إصلاحات منزلية مستمرة."
    },
    "المشتري (Jupiter)": {
        "nature": "إيجابي/حظ ووفرة",
        "MC": "خط وسط السماء: قمة النجاح الوظيفي، الحظ الوافر، الترقيات والسمعة الطيبة الواسعة.",
        "AC": "خط الطالع: تفاؤل، انفتاح، صحة ممتازة وفرص توسع شخصي واسعة.",
        "DC": "خط الغارب: شراكات مباركة، عقود دولية ناجحة وزواج سعيد ومثمر.",
        "IC": "خط جذر السماء: منزل واسع، استقرار مادي ومعنوي عميق وبركة في السكن."
    },
    "زحل (Saturn)": {
        "nature": "ضاغطة/اختبارات",
        "MC": "خط وسط السماء: مسؤوليات ثقيلة، ضغوط مهنية وجهود مضنية تؤتي ثمارها ببطء شديد.",
        "AC": "خط الطالع: جدية مفرطة، شعور بالثقل، اختبارات في التحمل والصبر الشخصي.",
        "DC": "خط الغارب: شراكات جادة، جافة، أو تأخر وتحديات في الارتباط والزواج.",
        "IC": "خط جذر السماء: أعباء عائلية ثقيلة، شعور بالوحدة أو جفاء عاطفي في بيئة السكن."
    }
}

# ==========================================
# 3. واجهة المستخدم الاحترافية (Streamlit UI)
# ==========================================
st.title("🌟 النظام المتقدم الشامل للأستروكارتوغرافيا المجالية")
st.markdown("### المسح الفلكي الجغرافي (أوربت 6 عالمياً و 1 للمدن داخل الدولة) - برمجة الفلكي استرو رادار")
st.markdown("---")

with st.sidebar:
    st.header("👤 بيانات المستفيد")
    name = st.text_input("اسم المستفيد", "ميار")
    
    current_year = datetime.date.today().year
    birth_date = st.date_input(
        "تاريخ الميلاد", 
        value=datetime.date(1981, 4, 17),
        min_value=datetime.date(1900, 1, 1),
        max_value=datetime.date(current_year, 12, 31)
    )
    birth_time = st.time_input("ساعة الميلاد (التوقيت المحلي)", datetime.time(11, 30), step=datetime.timedelta(minutes=1))
    
    st.header("🌍 مكان الولادة الجغرافي")
    birth_country_name = st.selectbox("دولة الميلاد", sorted_country_names, index=sorted_country_names.index("Syria") if "Syria" in sorted_country_names else 0)
    birth_c_code = country_name_to_code.get(birth_country_name, 'SY')
    
    birth_cities = get_cities_by_country(birth_c_code)
    birth_city_names = [c.name for c in birth_cities] if birth_cities else ["Default"]
    birth_city_name = st.selectbox("مدينة الميلاد", birth_city_names)
    
    b_city_data = next((c for c in birth_cities if c.name == birth_city_name), None)
    if b_city_data:
        b_lat, b_lon = b_city_data.latitude, b_city_data.longitude
    else:
        b_lat, b_lon = 33.5138, 36.2765
    
    tz_str = tf.timezone_at(lng=b_lon, lat=b_lat) or "UTC"
    
    st.markdown("---")
    st.header("🔍 نطاق ونوع البحث")
    search_mode = st.radio("خيارات البحث الجغرافي", ["مسح عالمي شامل لكافة دول العالم (أوربت 6)", "البحث في دولة محددة لفحص المدن (أوربت 1)"])
    
    selected_target_country = None
    if search_mode == "البحث في دولة محددة لفحص المدن (أوربت 1)":
        selected_target_country = st.selectbox("اختر الدولة المستهدفة للتحليل", sorted_country_names)

    st.markdown("---")
    if selected_target_country:
        st.info("ℹ️ **الأوربت المعتمد:** تم ضبط الأوربت على **$1.0^\circ$** نظراً لاختيار فحص المدن داخل الدولة المحددة بدقة.")
    else:
        st.info("ℹ️ **الأوربت المعتمد:** تم ضبط الأوربت على **$6.0^\circ$** للمسح العالمي الشامل للدول.")

    analyze_btn = st.button("🚀 بدء التحليل الفلكي الجغرافي", type="primary")

# ==========================================
# 4. محرك الحسابات الفلكية وتحليل أداء الدول والمدن
# ==========================================
if analyze_btn:
    # التعديل المطلوب: الأوربت العالمي 6، وأوربت الدولة الواحدة للمدن 1
    FIXED_ORB = 1.0 if selected_target_country else 6.0
    
    with st.spinner("جاري إجراء الحسابات الفلكية المكثفة وتحليل الأثر الكوكبي ومجالات الحياة بدقة عالية..."):
        jd = get_utc_julian_day(birth_date, birth_time, tz_str)
        
        planets_to_calc = {
            "الشمس (Sun)": swe.SUN,
            "القمر (Moon)": swe.MOON,
            "عطارد (Mercury)": swe.MERCURY,
            "الزهرة (Venus)": swe.VENUS,
            "المريخ (Mars)": swe.MARS,
            "المشتري (Jupiter)": swe.JUPITER,
            "زحل (Saturn)": swe.SATURN
        }
        
        planet_longitudes = {}
        for p_name, p_id in planets_to_calc.items():
            res = swe.calc_ut(jd, p_id)
            planet_longitudes[p_name] = res[0][0]
        
        def angular_distance(l1, l2):
            diff = abs(l1 - l2)
            return diff if diff <= 180.0 else 360.0 - diff

        benefic_planets = ["الشمس (Sun)", "الزهرة (Venus)", "المشتري (Jupiter)", "القمر (Moon)", "عطارد (Mercury)"]
        
        cities_to_scan = all_cities_list
        if selected_target_country:
            target_c_code = country_name_to_code.get(selected_target_country, "")
            cities_to_scan = [c for c in all_cities_list if c.country_code == target_c_code]

        raw_hits = []

        for city in cities_to_scan:
            c_lat = city.latitude
            c_lon = city.longitude
            c_code = city.country_code
            country_eng_name = countries_data.get(c_code, {}).get("name", c_code)
            
            try:
                houses = swe.houses_ex(jd, c_lat, c_lon, b'P')
                asc = houses[0][0]  
                ic = houses[0][3]   
                dc = houses[0][6]   
                mc = houses[0][9]   
            except Exception:
                continue
            
            for p_name, p_lon in planet_longitudes.items():
                dict_info = PLANET_DICTIONARY[p_name]
                
                distances = [
                    ("MC (وسط السماء)", angular_distance(p_lon, mc), dict_info['MC']),
                    ("AC (الطالع)", angular_distance(p_lon, asc), dict_info['AC']),
                    ("DC (الغارب)", angular_distance(p_lon, dc), dict_info['DC']),
                    ("IC (جذر السماء)", angular_distance(p_lon, ic), dict_info['IC'])
                ]
                
                for angle_name, dist, desc in distances:
                    if dist <= FIXED_ORB:
                        power_score = round(100 - (dist / FIXED_ORB) * 50, 2)
                        hit_type = "benefic" if p_name in benefic_planets else "malefic"
                        domains = get_life_domains(p_name, angle_name)
                        
                        raw_hits.append({
                            "city_name": city.name,
                            "country_name": country_eng_name,
                            "planet": p_name,
                            "angle": angle_name,
                            "orb": round(dist, 3),
                            "power": power_score,
                            "type": hit_type,
                            "desc": desc,
                            "domains": domains
                        })

        st.success("✨ تم إنجاز التحليل الفلكي المعمق بنجاح!")
        st.markdown(f"## 🌍 تقرير الأستروكارتوغرافيا الشامل لـ: {name}")
        st.markdown(f"**نطاق التأثير المعتمد (Orb):** **${FIXED_ORB}^\\circ$**")

        if selected_target_country:
            st.markdown(f"### 📍 تحليل المدن داخل دولة: **{selected_target_country}**")
            if not raw_hits:
                st.warning(f"⚠️ **منطقة محايدة فلكياً:** لا يمر أي خط كوكبي رئيسي ضمن النطاق المؤثر ($\\le 1.0^\circ$) عبر مدن {selected_target_country}.")
            else:
                # فصل وترتيب أسوأ المدن (Malefic أولاً أو حسب الأورب والأثر)
                malefic_hits = [h for h in raw_hits if h["type"] == "malefic"]
                benefic_hits = [h for h in raw_hits if h["type"] == "benefic"]
                
                # ترتيب أسوأ المدن (حتى 25 مدينة)
                sorted_worst_cities = sorted(malefic_hits, key=lambda x: x["orb"])[:25]
                # إذا لم تكتمل الـ 25 من النحس، نضيف أقرب المدن الداعمة تنازلياً لتغطية جدول تحليلي شامل للمدن
                if len(sorted_worst_cities) < 25:
                    remaining_count = 25 - len(sorted_worst_cities)
                    sorted_benefic_fallback = sorted(benefic_hits, key=lambda x: x["orb"], reverse=True)[:remaining_count]
                    display_cities_list = sorted_worst_cities + sorted_benefic_fallback
                else:
                    display_cities_list = sorted_worst_cities

                st.markdown("#### ⚠️ جدول أسوأ المدن (حتى 25 مدينة متأثرة بالضغوط):")
                df_country = pd.DataFrame([{
                    "المدينة": h["city_name"],
                    "الكوكب المؤثر": h["planet"],
                    "الوتد": h["angle"],
                    "البعد (Orb)": f"{h['orb']}°",
                    "المجالات المتأثرة": ", ".join(h["domains"]),
                    "نوع التأثير": "ضاغط/تحدي" if h["type"] == "malefic" else "داعم/إيجابي"
                } for h in display_cities_list])
                st.dataframe(df_country, use_container_width=True)

                # تحديد أفضل مدينة وأسوأ مدينة مع السبب الفلكي التفصيلي
                best_city = min(benefic_hits, key=lambda x: x["orb"]) if benefic_hits else None
                worst_city = min(malefic_hits, key=lambda x: x["orb"]) if malefic_hits else None

                st.markdown("---")
                st.markdown("### 💎 الخلاصة التحليلية: أفضل وأسوأ مدينة في الدولة المختارة")
                
                col_b, col_w = st.columns(2)
                with col_b:
                    if best_city:
                        st.markdown(f"""
                        <div style="background: #f1f9f5; border-right: 5px solid #27ae60; padding: 15px; border-radius: 6px;">
                            <h4 style="color: #27ae60; margin-top:0;">🌟 أفضل مدينة: <b>{best_city['city_name']}</b></h4>
                            <p><b>الكوكب الداعم:</b> {best_city['planet']} على خط {best_city['angle']}</p>
                            <p><b>نطاق الدقة (Orb):</b> {best_city['orb']}°</p>
                            <p><b>مجالات الدعم:</b> {', '.join(best_city['domains'])}</p>
                            <p><b>السبب الفلكي:</b> تقاطع كوكب سعد (الشمس، الزهرة، أو المشتري) بدقة عالية يمنح تدفقاً وطاقة إيجابية في هذه المجالات دون عراقيل.</p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.info("لا توجد مدينة ذات تأثير داعم رئيسي ضمن الأوربت المحدد.")

                with col_w:
                    if worst_city:
                        st.markdown(f"""
                        <div style="background: #fdf3f2; border-right: 5px solid #c0392b; padding: 15px; border-radius: 6px;">
                            <h4 style="color: #c0392b; margin-top:0;">⚠️ أسوأ مدينة: <b>{worst_city['city_name']}</b></h4>
                            <p><b>الكوكب الضاغط:</b> {worst_city['planet']} على خط {worst_city['angle']}</p>
                            <p><b>نطاق الدقة (Orb):</b> {worst_city['orb']}°</p>
                            <p><b>المجالات المتأثرة:</b> {', '.join(worst_city['domains'])}</p>
                            <p><b>السبب الفلكي:</b> تأثير كوكب نحس أو ضاغط (زحل أو المريخ) يولد اختبارات قاسية وضغوطاً مستمرة في هذه المجالات الحياتية.</p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.success("لا توجد مدن ذات تأثيرات ضاغطة سلبية حادة داخل الدولة ضمن الأوربت المحدد.")

                # تجهيز تقرير الـ HTML الخاص بالدولة المحددة مع خيار الطباعة والتنزيل
                html_country_content = f"""
                <!DOCTYPE html>
                <html lang="ar" dir="rtl">
                <head>
                    <meta charset="UTF-8">
                    <title>تقرير التحليل الفلكي لـ {selected_target_country} - {name}</title>
                    <style>
                        body {{ font-family: 'Tahoma', sans-serif; margin: 40px; background: #f4f6f7; color: #2c3e50; line-height: 1.6; }}
                        .header {{ text-align: center; border-bottom: 3px solid #2c3e50; padding-bottom: 25px; background: #ffffff; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
                        h1 {{ color: #1a252f; margin-bottom: 5px; }}
                        .section {{ background: #ffffff; padding: 25px; margin-top: 25px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
                        .card-worst {{ border-right: 6px solid #c0392b; padding: 15px; margin: 15px 0; background: #fdf3f2; border-radius: 6px; }}
                        .domain-badge {{ background: #fee2e2; color: #991b1b; padding: 3px 8px; border-radius: 4px; font-size: 12px; margin-left: 5px; display: inline-block; margin-top: 4px; }}
                        .footer {{ text-align: center; margin-top: 40px; color: #7f8c8d; font-size: 13px; }}
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h1>تقرير أستروكارتوغرافيا المدن لـ: {selected_target_country}</h1>
                        <p>المستفيد: <strong>{name}</strong> | تاريخ الميلاد: {birth_date} ({birth_time}) | الأوربت: {FIXED_ORB}°</p>
                    </div>
                    
                    <div class="section">
                        <h2>⚠️ جدول أسوأ المدن في الدولة</h2>
                """
                
                for idx, h in enumerate(display_cities_list):
                    badges = "".join([f'<span class="domain-badge">⚠️ {d}</span>' for d in h['domains']])
                    html_country_content += f"""
                    <div class="card-worst">
                        <h3 style="margin-top:0; color: #c0392b;">المركز {idx+1}: مدينة {h['city_name']}</h3>
                        <p><b>الكوكب المؤثر:</b> {h['planet']} | <b>الوتد:</b> {h['angle']} | <b>Orb:</b> {h['orb']}°</p>
                        <p><b>المجالات المتأثرة:</b> {badges}</p>
                        <p style="margin-top: 8px;"><b>التأثير:</b> {h['desc']}</p>
                    </div>
                    """
                    
                html_country_content += f"""
                    </div>
                    <div class="footer">
                        تم إعداد هذا التقرير عبر محرك الأستروكارتوغرافيا المتقدم - جميع الحقوق محفوظة للفلكي استرو رادار.
                    </div>
                </body>
                </html>
                """

                st.markdown("---")
                b64_c_html = base64.b64encode(html_country_content.encode("utf-8")).decode("utf-8")
                c_href = f'<a href="data:text/html;base64,{b64_c_html}" download="AstroCartography_{selected_target_country}_{name.replace(" ", "_")}.html" style="text-decoration: none;"><button style="padding: 12px 25px; background-color: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; font-weight: bold;">📥 تنزيل تقرير HTML الخاص بـ {selected_target_country} (جاهز للطباعة والـ PDF)</button></a>'
                st.markdown(c_href, unsafe_allow_html=True)

        else:
            best_countries_dict = {}
            worst_countries_dict = {}

            for hit in raw_hits:
                c_name = hit["country_name"]
                if hit["type"] == "benefic":
                    if c_name not in best_countries_dict or hit["orb"] < best_countries_dict[c_name]["orb"]:
                        best_countries_dict[c_name] = hit
                else:
                    if c_name not in worst_countries_dict or hit["orb"] < worst_countries_dict[c_name]["orb"]:
                        worst_countries_dict[c_name] = hit

            sorted_best_countries = sorted(list(best_countries_dict.values()), key=lambda x: x["orb"])[:25]
            sorted_worst_countries = sorted(list(worst_countries_dict.values()), key=lambda x: x["orb"])[:25]

            st.markdown("### 🏆 أفضل 25 دولة داعمة عالمياً (مع تحديد مجالات الدعم):")
            if not sorted_best_countries:
                st.warning("⚠️ لم يتم رصد تقاطعات داعمة قوية ضمن الأوربت المحدد عالمياً.")
            else:
                df_best_c = pd.DataFrame([{
                    "الترتيب": idx + 1,
                    "الدولة": h["country_name"],
                    "أبرز مدينة متأثرة": h["city_name"],
                    "الكوكب الداعم": h["planet"],
                    "الوتد": h["angle"],
                    "البعد (Orb)": f"{h['orb']}°",
                    "مجالات الدعم الرئيسية": ", ".join(h["domains"])
                } for idx, h in enumerate(sorted_best_countries)])
                st.dataframe(df_best_c, use_container_width=True)

            st.markdown("### ⚠️ أكثر 25 دولة ضغطاً واختباراً عالمياً:")
            if not sorted_worst_countries:
                st.info("ℹ️ لم يتم رصد دول واقعة تحت تأثيرات ضاغطة لزحل والمريخ ضمن الأوربت المحدد عالمياً.")
            else:
                df_worst_c = pd.DataFrame([{
                    "الترتيب": idx + 1,
                    "الدولة": h["country_name"],
                    "أبرز مدينة متأثرة": h["city_name"],
                    "الكوكب الضاغط": h["planet"],
                    "الوتد": h["angle"],
                    "البعد (Orb)": f"{h['orb']}°",
                    "مجالات التحدي والضغط": ", ".join(h["domains"])
                } for idx, h in enumerate(sorted_worst_countries)])
                st.dataframe(df_worst_c, use_container_width=True)

            # تجهيز التقرير الـ HTML العالمي
            html_content = f"""
            <!DOCTYPE html>
            <html lang="ar" dir="rtl">
            <head>
                <meta charset="UTF-8">
                <title>التقرير الفلكي العالمي المجالي المعمق للأستروكارتوغرافيا - {name}</title>
                <style>
                    body {{ font-family: 'Tahoma', sans-serif; margin: 40px; background: #f4f6f7; color: #2c3e50; line-height: 1.6; }}
                    .header {{ text-align: center; border-bottom: 3px solid #2c3e50; padding-bottom: 25px; background: #ffffff; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
                    h1 {{ color: #1a252f; margin-bottom: 5px; }}
                    .section {{ background: #ffffff; padding: 25px; margin-top: 25px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
                    .card-best {{ border-right: 6px solid #27ae60; padding: 15px; margin: 15px 0; background: #f1f9f5; border-radius: 6px; }}
                    .card-worst {{ border-right: 6px solid #c0392b; padding: 15px; margin: 15px 0; background: #fdf3f2; border-radius: 6px; }}
                    .domain-badge {{ background: #e2e8f0; color: #1e293b; padding: 3px 8px; border-radius: 4px; font-size: 12px; margin-left: 5px; display: inline-block; margin-top: 4px; }}
                    .footer {{ text-align: center; margin-top: 40px; color: #7f8c8d; font-size: 13px; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>تقرير الأستروكارتوغرافيا العالمي المعمق (أوربت {FIXED_ORB}°)</h1>
                    <p>المستفيد: <strong>{name}</strong> | تاريخ الميلاد: {birth_date} ({birth_time})</p>
                </div>
                
                <div class="section">
                    <h2>🏆 أفضل 25 دولة داعمة عالمياً ومجالاتها</h2>
            """
            
            for idx, h in enumerate(sorted_best_countries):
                badges = "".join([f'<span class="domain-badge">✨ {d}</span>' for d in h['domains']])
                html_content += f"""
                <div class="card-best">
                    <h3 style="margin-top:0; color: #27ae60;">المركز {idx+1}: {h['country_name']} (مدينة {h['city_name']})</h3>
                    <p><b>الكوكب:</b> {h['planet']} | <b>الوتد:</b> {h['angle']} | <b>البعد الدقيق (Orb):</b> {h['orb']}°</p>
                    <p><b>مجالات الدعم:</b> {badges}</p>
                    <p style="margin-top: 8px;"><b>التأثير الإيجابي:</b> {h['desc']}</p>
                </div>
                """
                
            html_content += """
                </div>
                <div class="section">
                    <h2>⚠️ أكثر 25 دولة ضغطاً واختباراً عالمياً</h2>
            """
            
            for idx, h in enumerate(sorted_worst_countries):
                badges = "".join([f'<span class="domain-badge" style="background:#fee2e2; color:#991b1b;">⚠️ {d}</span>' for d in h['domains']])
                html_content += f"""
                <div class="card-worst">
                    <h3 style="margin-top:0; color: #c0392b;">المركز {idx+1}: {h['country_name']} (مدينة {h['city_name']})</h3>
                    <p><b>الكوكب الضاغط:</b> {h['planet']} | <b>الوتد:</b> {h['angle']} | <b>البعد الدقيق (Orb):</b> {h['orb']}°</p>
                    <p><b>المجالات المتأثرة:</b> {badges}</p>
                    <p style="margin-top: 8px;"><b>التأثير الضاغط:</b> {h['desc']}</p>
                </div>
                """
                
            html_content += """
                </div>
                <div class="footer">
                    تم إعداد هذا التقرير عبر محرك الأستروكارتوغرافيا المتقدم - جميع الحقوق محفوظة للفلكي استرو رادار.
                </div>
            </body>
            </html>
            """

            st.markdown("---")
            b64_html = base64.b64encode(html_content.encode("utf-8")).decode("utf-8")
            href = f'<a href="data:text/html;base64,{b64_html}" download="Global_25_Deep_AstroCartography_Report_{name.replace(" ", "_")}.html" style="text-decoration: none;"><button style="padding: 12px 25px; background-color: #27ae60; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 16px; font-weight: bold;">📥 تنزيل التقرير العالمي الكامل لـ 25 دولة (HTML جاهز للطباعة والـ PDF)</button></a>'
            st.markdown(href, unsafe_allow_html=True)
            st.success("🎉 تم توليد التقرير العالمي المعمق لـ 25 دولة بنجاح وجاهز للتحميل والتصدير!")
