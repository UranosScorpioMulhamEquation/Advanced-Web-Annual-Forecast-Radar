from datetime import datetime, date, time
import os
from typing import Dict, List, Tuple, Any
import base64
import geonamescache
import pytz
import streamlit as st
import swisseph as swe
from timezonefinder import TimezoneFinder

# ==========================================
# 0. تهيئة الصفحة ومسار ملفات الـ Ephemeris
# ==========================================
st.set_page_config(
    page_title="النظام المتقدم لتنجيم الحدث العاطفي",
    layout="wide",
)

EPHE_PATH = "./ephe"
if not os.path.exists(EPHE_PATH):
    os.makedirs(EPHE_PATH)

swe.set_ephe_path(EPHE_PATH)

st.title("النظام المتقدم لتحليل خارطة الحدث العاطفي 💖 (برمجة الفلكي استرو رادار)")
st.markdown("تحليل فلكي دقيق وشامل يغطي دلالات الانفصال، الانسحاب، المشاجرات، والوقت المتوقع للرجوع وفق الأصول الكلاسيكية المعتبرة.")
st.markdown("---")

# ==========================================
# 1. خدمات البيانات الجغرافية والزمنية
# ==========================================
@st.cache_data
def load_geo_data() -> Tuple[geonamescache.GeonamesCache, Dict[str, str], List[str], Dict[str, List[Dict[str, Any]]]]:
    gc = geonamescache.GeonamesCache()
    countries = gc.get_countries()
    cities = gc.get_cities()

    country_map = {c["name"]: code for code, c in countries.items()}
    sorted_countries = sorted(list(country_map.keys()))

    cities_by_country: Dict[str, List[Dict[str, Any]]] = {}
    for c_code in country_map.values():
        c_cities = [city for city in cities.values() if city["countrycode"] == c_code]
        c_cities_sorted = sorted(c_cities, key=lambda x: x["population"], reverse=True)
        cities_by_country[c_code] = c_cities_sorted

    return gc, country_map, sorted_countries, cities_by_country

gc, country_map, country_list, cities_by_country = load_geo_data()

@st.cache_resource
def get_tz_finder() -> TimezoneFinder:
    return TimezoneFinder()

tf = get_tz_finder()

def get_utc_julian_day(date_obj: date, time_obj: time, tz_str: str) -> float:
    local_tz = pytz.timezone(tz_str)
    dt = datetime.combine(date_obj, time_obj)
    local_dt = local_tz.localize(dt, is_dst=False)
    utc_dt = local_dt.astimezone(pytz.utc)
    return swe.julday(
        utc_dt.year,
        utc_dt.month,
        utc_dt.day,
        utc_dt.hour + utc_dt.minute / 60.0 + utc_dt.second / 3600.0,
    )

# ==========================================
# القواميس الفلكية والكويكبات العاطفية (بالمصطلحات الكلاسيكية)
# ==========================================
SIGN_NAMES = [
    "الحمل", "الثور", "الجوزاء", "السرطان", "الأسد", "العذراء",
    "الميزان", "العقرب", "القوس", "الجدي", "الدلو", "الحوت"
]

SIGN_MODALITY = {
    "الحمل": "منقلب", "الثور": "ثابت", "الجوزاء": "ذو جسدين",
    "السرطان": "منقلب", "الأسد": "ثابت", "العذراء": "ذو جسدين",
    "الميزان": "منقلب", "العقرب": "ثابت", "القوس": "ذو جسدين",
    "الجدي": "منقلب", "الدلو": "ثابت", "الحوت": "ذو جسدين"
}

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

# ==========================================
# الشريط الجانبي للإدخالات
# ==========================================
st.sidebar.header("⚙️ إعدادات حدث اللحظة العاطفية")

selected_event_key = st.sidebar.selectbox(
    "اختر غرض الحدث العاطفي:", list(EVENT_TYPES.keys())
)
event_purpose = EVENT_TYPES[selected_event_key]

now_local = datetime.now()
ev_date = st.sidebar.date_input(
    "تاريخ وقوع الحدث:",
    value=now_local.date(),
    min_value=date(1800, 1, 1),
    max_value=date(2100, 12, 31)
)

st.sidebar.markdown("🕒 **وقت وقوع الحدث (المحلي):**")
col_h, col_m, col_s = st.sidebar.columns(3)
with col_h:
    ev_hour = st.number_input("الساعة", min_value=0, max_value=23, value=now_local.hour, step=1)
with col_m:
    ev_minute = st.number_input("الدقيقة", min_value=0, max_value=59, value=now_local.minute, step=1)
with col_s:
    ev_second = st.number_input("الثانية", min_value=0, max_value=59, value=now_local.second, step=1)

ev_time = time(int(ev_hour), int(ev_minute), int(ev_second))

default_country_idx = country_list.index("United Arab Emirates") if "United Arab Emirates" in country_list else 0
selected_country_name = st.sidebar.selectbox("اختر الدولة:", country_list, index=default_country_idx)
country_code = country_map[selected_country_name]

country_cities = cities_by_country.get(country_code, [])
city_names = [c["name"] for c in country_cities]

if city_names:
    selected_city_name = st.sidebar.selectbox("اختر المدينة:", city_names)
    selected_city = next((c for c in country_cities if c["name"] == selected_city_name), country_cities[0])
    lat = float(selected_city["latitude"])
    lon = float(selected_city["longitude"])
    tz_str = tf.timezone_at(lng=lon, lat=lat) or "UTC"
else:
    lat = st.sidebar.number_input("خط العرض (Latitude):", value=25.2048, format="%.4f")
    lon = st.sidebar.number_input("خط الطول (Longitude):", value=55.2708, format="%.4f")
    tz_str = st.sidebar.text_input("المنطقة الزمنية (Timezone):", value="Asia/Dubai")

st.sidebar.write(f"🌍 الإحداثيات: {lat:.2f}, {lon:.2f} | التوقيت: {tz_str}")

def get_sign_and_deg(lon_deg):
    lon_deg = lon_deg % 360
    sign_idx = int(lon_deg / 30)
    deg_in_sign = lon_deg % 30
    sign_name = SIGN_NAMES[sign_idx % 12]
    return sign_name, deg_in_sign

if st.button("🔮 تحليل خريطة الحدث العاطفي", type="primary"):
    try:
        jd = get_utc_julian_day(ev_date, ev_time, tz_str)
    except Exception as e:
        st.error(f"خطأ في حساب التوقيت والمنطقة الزمنية: {e}")
        st.stop()

    planets = {
        "الشمس": swe.SUN,
        "القمر": swe.MOON,
        "عطارد": swe.MERCURY,
        "الزهرة": swe.VENUS,
        "المريخ": swe.MARS,
        "المشتري": swe.JUPITER,
        "زحل": swe.SATURN,
        "أورانوس (Uranus)": swe.URANUS,
        "نبتون (Neptune)": swe.NEPTUNE,
        "بلوتو (Pluto)": swe.PLUTO,
        "تشيرون (Chiron)": swe.CHIRON,
    }

    ast_offset = getattr(swe, 'SE_AST_OFFSET', 10000)
    asteroid_ids = {
        "إيروس (Eros - الشغف والرغبة)": ast_offset + 433,
        "بسايكي (Psyche - الارتباط الروحي)": ast_offset + 16,
    }

    planet_data = {}
    for p_name, p_id in planets.items():
        res, _ = swe.calc_ut(jd, p_id, swe.FLG_SWIEPH | swe.FLG_SPEED)
        planet_data[p_name] = {
            "lon": res[0],
            "sign": get_sign_and_deg(res[0])[0],
            "deg": get_sign_and_deg(res[0])[1],
            "retro": res[3] < 0,
            "speed": res[3]
        }
    for a_name, a_id in asteroid_ids.items():
        try:
            res, _ = swe.calc_ut(jd, a_id, swe.FLG_SWIEPH | swe.FLG_SPEED)
            planet_data[a_name] = {
                "lon": res[0],
                "sign": get_sign_and_deg(res[0])[0],
                "deg": get_sign_and_deg(res[0])[1],
                "retro": res[3] < 0,
                "speed": res[3]
            }
        except:
            continue

    # ==========================================
    # معالجة مصفوفة البيوت وطول الـ Tuple بأمان تام
    # ==========================================
    houses_cusps, ascmc = swe.houses_ex(jd, lat, lon, b"R")
    
    asc_lon = ascmc[0]  
    asc_sign, asc_deg = get_sign_and_deg(asc_lon)

    if len(houses_cusps) >= 13:
        cusps = list(houses_cusps[1:13])
    else:
        cusps = list(houses_cusps[:12])

    def find_house(p_lon):
        p_lon = p_lon % 360
        for i in range(12):
            c_start = cusps[i] % 360
            c_end = cusps[(i + 1) % 12] % 360
            if c_start < c_end:
                if c_start <= p_lon < c_end:
                    return i + 1
            else:
                if p_lon >= c_start or p_lon < c_end:
                    return i + 1
        return 1

    for p_name in planet_data:
        planet_data[p_name]["house"] = find_house(planet_data[p_name]["lon"])

    party1_ruler = RULERS[asc_sign]
    desc_cusp_lon = cusps[6]  
    desc_sign, _ = get_sign_and_deg(desc_cusp_lon)
    party2_ruler = RULERS[desc_sign]

    st.success("✨ تم حساب الخريطة الفلكية وتوزيع البيوت بدقة تامة بنظام ريغومونتانوس!")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"### 🧑 الطرف الأول (صاحب الحدث / الطالع)")
        st.write(f"- **الطالع:** {asc_sign} ({asc_deg:.2f}°)")
        st.write(f"- **حاكم الطرف الأول:** {party1_ruler} (في البرج: {planet_data[party1_ruler]['sign']}، البيت {planet_data[party1_ruler]['house']})")
        st.write(f"- **القمر (المشاعر الحالية):** {planet_data['القمر']['sign']} ({planet_data['القمر']['deg']:.2f}°) في البيت {planet_data['القمر']['house']}")

    with col2:
        st.markdown(f"### 👩‍❤️‍👨 الطرف الثاني (الشريك / البيت السابع)")
        st.write(f"- **رأس السابع:** {desc_sign}")
        st.write(f"- **حاكم الطرف الثاني:** {party2_ruler} (في البرج: {planet_data[party2_ruler]['sign']}، البيت {planet_data[party2_ruler]['house']})")
        st.write(f"- **الزهرة (دلالة الحب):** {planet_data['الزهرة']['sign']} (البيت {planet_data['الزهرة']['house']})")

    st.markdown("---")
    st.markdown("### 🔬 محرك التشخيص الفلكي الدقيق للأسباب")

    # ==========================================
    # دالة محرك الاتصالات المتقدمة والدقيقة (Delta-Time)
    # ==========================================
    def check_aspect(p1_name, p2_name):
        if p1_name not in planet_data or p2_name not in planet_data:
            return False, None, None, 0.0, None
        
        lon1 = planet_data[p1_name]["lon"]
        lon2 = planet_data[p2_name]["lon"]
        speed1 = planet_data[p1_name]["speed"]
        speed2 = planet_data[p2_name]["speed"]
        
        diff = abs(lon1 - lon2) % 360
        if diff > 180:
            diff = 360 - diff
        
        aspects_def = [
            ("اقتران (Conjunction)", 0, 6.0, "positive"),
            ("تثليث (Trine)", 120, 6.0, "positive"),
            ("تسديس (Sextile)", 60, 5.0, "positive"),
            ("تربيع (Square)", 90, 6.0, "negative"),
            ("مقابلة (Opposition)", 180, 6.0, "negative")
        ]
        
        for asp_name, target_angle, max_orb, asp_type in aspects_def:
            orb = abs(diff - target_angle)
            if orb <= max_orb:
                # خوارزمية الدلتا الزمنية المضمونة 100% لتحديد Applying / Separating
                dt = 0.01
                f_lon1 = (lon1 + speed1 * dt) % 360
                f_lon2 = (lon2 + speed2 * dt) % 360
                f_diff = abs(f_lon1 - f_lon2) % 360
                if f_diff > 180:
                    f_diff = 360 - f_diff
                f_orb = abs(f_diff - target_angle)

                status = "Applying" if f_orb < orb else "Separating"
                return True, asp_name, asp_type, orb, status
                
        return False, None, None, 0.0, None

    p1_name = party1_ruler
    p2_name = party2_ruler
    
    has_aspect, asp_name, asp_type, asp_orb, asp_status = check_aspect(p1_name, p2_name)
    has_moon_asp, moon_asp_name, moon_asp_type, moon_orb, moon_status = check_aspect("القمر", p2_name)

    detailed_causes = []

    if event_purpose == "لقاء":
        if not planet_data["عطارد"]["retro"]:
            detailed_causes.append({
                "category": "انسجام الحوار والتواصل",
                "desc": "حركة عطارد المباشرة تعكس حواراً سلساً وتفاهماً واضحاً أثناء اللقاء."
            })
        else:
            detailed_causes.append({
                "category": "استرجاع ذكريات سابقة",
                "desc": "تراجع عطارد يشير إلى فتح مواضيع قديمة واسترجاع ذكريات بين الطرفين."
            })
        if has_aspect:
            detailed_causes.append({
                "category": "توافق النوايا",
                "desc": f"وجود اتصال فلكي ({asp_name} - {asp_status}) بين حاكم الطالع وحاكم الشريك يعكس رغبة صادقة في اللقاء."
            })
    elif event_purpose == "مشاجرة":
        detailed_causes.append({
            "category": "احتكاك لفظي واختلاف وجهات نظر",
            "desc": "طبيعة الخريطة تشير إلى توتر لفظي لحظي واختلاف في التوقعات أدى لاحتكاك مباشر."
        })
    elif event_purpose == "انسحاب":
        detailed_causes.append({
            "category": "رغبة بالهدوء المؤقت",
            "desc": "الانسحاب جاء نتيجة حاجة ملحة لالتقاط الأنفاس وتفادي تفاقم النقاشات."
        })
    else:
        detailed_causes.append({
            "category": "فراق أو جفاء في التواصل",
            "desc": "وجود ضغوط فلكية تعكس جفاءً أو سوء فهم لفظي متكرر أدى لقرار الانفصال."
        })

    st.info(f"📌 **طبيعة الحدث المحدد:** {selected_event_key}")
    st.markdown("#### ⚙️ التشخيص التفصيلي:")
    for cause in detailed_causes:
        st.markdown(f"- **{cause['category']}:** {cause['desc']}")

    st.markdown("---")
    st.markdown("### 👥 تحليل الأطراف الثالثة (مفلتر وصارم)")

    third_parties_found = []
    target_tp_houses = {
        5: ("علاقة عاطفية بديلة أو طرف منافس (البيت الخامس)", "وجود كواكب في البيت الخامس قد يشير لمنافسة أو اهتمام عاطفي خارجي."),
        12: ("أسرار مخفية أو تأثير خفي (البيت الثاني عشر)", "وجود كواكب في البيت الثاني عشر يعكس أسراراً غير معلومة أو وشاية سرية."),
        11: ("ضغط المحيط الاجتماعي أو الأصدقاء (البيت الحادي عشر)", "تدخلات واضحة من شبكة المعارف والأصدقاء المشتركين.")
    }

    for h_num, (tp_title, tp_desc) in target_tp_houses.items():
        h_planets = [p for p, info in planet_data.items() if info["house"] == h_num and p not in [party1_ruler, party2_ruler, "الشمس", "القمر"]]
        if h_planets:
            confirmed = False
            for hp in h_planets:
                has_asp, _, asp_t, _, _ = check_aspect(hp, party1_ruler)
                if has_asp and asp_t == "negative":
                    confirmed = True
                has_asp2, _, asp_t2, _, _ = check_aspect(hp, party2_ruler)
                if has_asp2 and asp_t2 == "negative":
                    confirmed = True
            
            if confirmed or len(h_planets) >= 2:
                third_parties_found.append((tp_title, f"{tp_desc} الكواكب المرصودة: ({', '.join(h_planets)})."))

    if third_parties_found:
        st.warning("⚠️ **تم رصد أطراف ثالثة مؤثرة ومؤكدة فلكياً:**")
        for tp_title, tp_desc in third_parties_found:
            st.markdown(f"- **{tp_title}:** {tp_desc}")
    else:
        st.success("✅ الخريطة خالية من أي تدخلات حقيقية للأطراف الثالثة؛ الحدث ثنائي ومحصور كلياً بين الطرفين.")

    # ==========================================
    # 🔄 التحليل المتطور للعودة والزمن المتوقع
    # ==========================================
    can_return = False
    return_reasons = []
    timing_res = "غير متاح"

    if event_purpose in ["فراق", "انسحاب", "مشاجرة"]:
        st.markdown("---")
        st.markdown("### 🔄 تحليل إمكانية عودة التواصل (Reconciliation Analysis)")

        if planet_data[party2_ruler]["retro"]:
            can_return = True
            return_reasons.append(f"حاكم الشريك ({party2_ruler}) في حالة تراجع، وهي دلالة تقليدية قوية على رغبة الشريك في مراجعة قرار الابتعاد.")

        if has_aspect and asp_type == "positive" and asp_status == "Applying":
            can_return = True
            return_reasons.append(f"وجود اتصال إيجابي قادم ومنطبق ({asp_name}) بين حاكم الطالع وحاكم الشريك يمهد حتماً للصلح.")

        if has_moon_asp and moon_asp_type == "positive" and moon_status == "Applying":
            can_return = True
            return_reasons.append(f"القمر يصنع اتصالاً إيجابياً مقبلاً ({moon_asp_name}) مع حاكم الشريك، مما يسارع في تقريب وجهات النظر.")

        if can_return:
            st.success("🌟 **إمكانية العودة والتواصل: واردة وبقوة وفق المعطيات الفلكية الدقيقة!**")
            for rr in return_reasons:
                st.markdown(f"- {rr}")

            def calculate_precise_timing(orb_val, sign_name):
                mod = SIGN_MODALITY.get(sign_name, "منقلب")
                if mod == "منقلب":
                    unit = "أيام (سريعة التطور)"
                elif mod == "ذو جسدين":
                    unit = "أسابيع قليلة"
                else:
                    unit = "أشهر (تطور بطيء ومتأني)"
                days_est = max(1, int(orb_val * 1.5))
                return f"حوالي {days_est} إلى {days_est + 3} {unit} (استناداً لدرجة الانطباخ Orb: {orb_val:.2f}°)"

            target_orb = moon_orb if (has_moon_asp and moon_status == "Applying") else asp_orb
            timing_res = calculate_precise_timing(target_orb, planet_data["القمر"]["sign"])
            st.info(f"⏳ **الوقت المتوقع لعودة التواصل والصلح:** {timing_res}")
        else:
            st.error("🛑 **إمكانية العودة والتواصل: ضعيفة أو متعذرة في الوقت الحالي.**")
            st.markdown("- غياب الاتصالات الإيجابية المقبلة (Applying) أو وجود اتصالات منصرفة يعكس تمسك كل طرف بموقفه الحالي.")

    # ==========================================
    # تصدير تقرير HTML
    # ==========================================
    st.markdown("---")
    st.markdown("### 🖨️ تصدير التقرير الفلكي المصحح لخريطة الحدث العاطفي")

    causes_html = "".join([f"<li><strong>{c['category']}:</strong> {c['desc']}</li>" for c in detailed_causes])
    tp_html = "".join([f"<li><strong>{title}:</strong> {desc}</li>" for title, desc in third_parties_found]) if third_parties_found else "<li>لا توجد أطراف ثالثة مؤثرة؛ الحدث ثنائي وبحت.</li>"
    return_html = f"""
    <div class='box'>
        <h3>🔄 إمكانية العودة والتواصل والوقت المتوقع</h3>
        <p><strong>الحالة:</strong> {'واردة وبقوة' if can_return else 'ضعيفة أو متعذرة'}</p>
        <p><strong>الوقت المتوقع للعودة:</strong> {timing_res}</p>
        <ul>{"".join([f"<li>{rr}</li>" for rr in return_reasons])}</ul>
    </div>
    """ if event_purpose in ["فراق", "انسحاب", "مشاجرة"] else ""

    html_content = f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>التقرير الفلكي المتقدم والمصحح للحدث العاطفي</title>
        <style>
            body {{ font-family: 'Tahoma', Arial, sans-serif; margin: 40px; color: #222; line-height: 1.8; background: #fff; }}
            h1, h2, h3 {{ color: #3b093c; }}
            .header {{ text-align: center; border-bottom: 3px solid #3b093c; padding-bottom: 20px; margin-bottom: 30px; }}
            .box {{ background: #fdfdfd; border: 1px solid #e0e0e0; padding: 20px; border-radius: 8px; margin-bottom: 25px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
            .footer {{ text-align: center; margin-top: 50px; font-size: 13px; color: #666; border-top: 1px solid #ddd; padding-top: 15px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>💖 التقرير الفلكي الاحترافي والمصحح للحدث العاطفي</h1>
            <p><strong>برمجة استرو رادار</strong></p>
            <p>تاريخ ووقت الحدث: {ev_date} {ev_time} | الموقع الجغرافي: {selected_country_name}</p>
        </div>

        <div class="box">
            <h3>📌 معطيات الخريطة الفلكية الأساسية</h3>
            <p><strong>نوع الحدث العاطفي:</strong> {selected_event_key}</p>
            <p><strong>الطالع:</strong> {asc_sign} ({asc_deg:.2f}°)</p>
            <p><strong>حاكم الطرف الأول (الطالع):</strong> {party1_ruler} (في برج {planet_data[party1_ruler]['sign']} - البيت {planet_data[party1_ruler]['house']})</p>
            <p><strong>رأس البيت السابع (الشريك):</strong> {desc_sign}</p>
            <p><strong>حاكم الطرف الثاني (الشريك):</strong> {party2_ruler} (في برج {planet_data[party2_ruler]['sign']} - البيت {planet_data[party2_ruler]['house']})</p>
        </div>

        <div class="box">
            <h3>⚙️ التشخيص الفلكي والنفسي لحدث اللحظة العاطفية</h3>
            <ul>{causes_html}</ul>
        </div>

        <div class="box">
            <h3>👥 تقرير الأطراف الثالثة والمحيط</h3>
            <ul>{tp_html}</ul>
        </div>

        {return_html}

        <div class="footer">
            <p>تم استخراج هذا التقرير الفلكي وفق أصول التنجيم الساعي الغربي ونظام ريغومونتانوس.</p>
        </div>
    </body>
    </html>
    """

    st.download_button(
        label="📥 تحميل التقرير الكامل المصحح (HTML)",
        data=html_content,
        file_name=f"Expert_Correct_Report_{ev_date}.html",
        mime="text/html",
        use_container_width=True
    )
