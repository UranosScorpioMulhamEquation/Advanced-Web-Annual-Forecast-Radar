import streamlit as st
import swisseph as swe
from datetime import datetime, date
import pandas as pd
import base64
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

# ==================== إعدادات الصفحة وتصميم الواجهة (RTL & Cairo Font) ====================
st.set_page_config(
    page_title="رادار نبتون هوميا ايريس المطور",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded"
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

# أسماء الأبراج والكواكب بالعربية
ZODIAC_SIGNS = [
    "الحمل", "الثور", "الجوزاء", "السرطان", 
    "الأسد", "العذراء", "الميزان", "العقرب", 
    "القوس", "الجدي", "الدلو", "الحوت"
]

PLANETS = {
    swe.SATURN: "زحل",
    swe.JUPITER: "المشتري",
    swe.URANUS: "أورانوس",
    swe.NEPTUNE: "نبتون",
    swe.PLUTO: "بلوتو"
}

def get_zodiac_sign(longitude):
    """تحديد البرج ودرجته من الطول الفلكي"""
    sign_index = int(longitude / 30)
    degree = longitude % 30
    return sign_index, ZODIAC_SIGNS[sign_index], degree

def calculate_whole_sign_houses(sun_sign_index):
    """حساب البيوت بنظام الأبراج الكاملة حيث الطول الشمسي هو البيت الأول"""
    houses = {}
    for h in range(1, 13):
        sign_idx = (sun_sign_index + h - 1) % 12
        houses[h] = sign_idx
    return houses

def get_planet_longitude(jd, planet_id):
    """حساب الطول الفلكي للكوكب باستخدام Swiss Ephemeris"""
    res, _ = swe.calc_ut(jd, planet_id)
    return res[0]

# ==================== 2. Radar Engine (USM Integration) ====================
def run_usm_engine_daily(birth_date):
    homo_k, eris_k, neptune_k, tolerance = 6.18, 9.3, 10.77, 0.3
    results = []
    for i in range(1, 85):
        homo_dev = abs((i / homo_k) - round(i / homo_k))
        eris_dev = abs((i / eris_k) - round(i / eris_k))
        neptune_dev = abs((i / neptune_k) - round(i / neptune_k))
        
        status = "CRITICAL" if (homo_dev <= tolerance and eris_dev <= tolerance and neptune_dev <= tolerance) else "Normal"
        
        offset_day = int(eris_dev * 30)
        offset_month = int(homo_dev * 12)
        target_year = birth_date.year + i
        
        new_day = birth_date.day + offset_day
        new_month = birth_date.month + offset_month
        new_year = target_year
        
        while new_day > 30:
            new_day -= 30
            new_month += 1
        while new_month > 12:
            new_month -= 12
            new_year += 1
            
        # ضمان عدم الخروج عن النطاق المسموح لأشهر السنة
        if new_month < 1: new_month = 1
        if new_month > 12: new_month = 12
        if new_day < 1: new_day = 1
        if new_day > 28 and new_month == 2: new_day = 28
        elif new_day > 30: new_day = 30

        results.append({
            "DateStr": f"{new_year}-{new_month:02d}-{new_day:02d}",
            "YearDate": date(new_year, new_month, new_day),
            "Age": i,
            "Status": status
        })
    return results

def analyze_astrological_pattern(entity_type, sun_sign_idx, target_date):
    """تحليل الاتصالات والبيوت الفلكية لتحديد نوع التغيير بدقة عند حدوث السنة الحرجة"""
    try:
        jd = swe.julday(target_date.year, target_date.month, target_date.day, 12.0)
    except:
        jd = swe.julday(target_date.year, 6, 15, 12.0)
        
    house_map = calculate_whole_sign_houses(sun_sign_idx)
    
    # اختيار كوكب عبور رئيسي بناءً على السنة لمعاينة الاتصال الفلكي
    planet_keys = list(PLANETS.keys())
    selected_planet = planet_keys[target_date.year % len(planet_keys)]
    planet_name = PLANETS[selected_planet]
    
    trans_long = get_planet_longitude(jd, selected_planet)
    trans_sign_idx, trans_sign_name, trans_deg = get_zodiac_sign(trans_long)
    
    # إيجاد البيت الفلكي العابر فيه الكوكب (Whole Sign Houses)
    transit_house = 1
    for h, s_idx in house_map.items():
        if s_idx == trans_sign_idx:
            transit_house = h
            break

    aspect_desc = f"عبور كوكب {planet_name} في برج {trans_sign_name} (البيت {transit_house})"

    # تحديد نوع التغيير الدقيق للأشخاص
    if entity_type == "شخص":
        if transit_house in [6, 12] or selected_planet in [swe.SATURN, swe.NEPTUNE]:
            return "تغيير صحي", f"{aspect_desc} - ضغوط صحية، جسدية، أو استشفاء.", "badge-health"
        elif transit_house in [10, 6] or selected_planet in [swe.JUPITER, swe.SATURN]:
            return "في المنصب المهني/الوضع الاجتماعي", f"{aspect_desc} - ترقية، تغير في المسؤوليات، أو تحول وظيفي كبيرا.", "badge-career"
        elif transit_house in [4] or selected_planet in [swe.MOON if hasattr(swe, 'MOON') else swe.SATURN]:
            return "عائلي", f"{aspect_desc} - تحولات في محيط العائلة، السكن، أو الجذور.", "badge-family"
        elif transit_house in [7] or selected_planet in [swe.VENUS if hasattr(swe, 'VENUS') else swe.MARS]:
            return "مع الشريك", f"{aspect_desc} - تأثيرات مفصلية على الشراكات العاطفية أو المهنية والزواج.", "badge-partner"
        elif transit_house in [2, 8] or selected_planet in [swe.PLUTO, swe.JUPITER]:
            return "مالي", f"{aspect_desc} - تحولات مالية كبرى، استثمارات استراتيجية، أو تسويات ديون.", "badge-finance"
        else:
            return "في المنصب المهني/الوضع الاجتماعي", f"{aspect_desc} - إعادة هيكلة شخصية ومسار عام.", "badge-career"
            
    # تحديد نوع التغيير للشركات (مالي / هيكلي)
    elif entity_type == "شركة":
        if transit_house in [2, 8] or selected_planet in [swe.JUPITER, swe.PLUTO]:
            return "تغيير مالي", f"{aspect_desc} - تحولات في العوائد، الأرباح، السيولة النقدية، أو صفقات الاستثمار الكبرى.", "badge-finance"
        else:
            return "تغيير هيكلي", f"{aspect_desc} - إعادة تنظيم إداري، تغيرات في مجالس الإدارة، اندماجات، أو تحولات تشغيلية هيكلية.", "badge-career"
            
    # تحديد نوع التغيير للدول (اقتصادي، شامل، شعبي، عسكري/امني)
    else:
        if transit_house in [6, 8, 12] or selected_planet in [swe.PLUTO, swe.SATURN]:
            return "تغيير عسكري/امني", f"{aspect_desc} - توترات، تطورات دفاعية، صراعات، أو إعادة تقييم استراتيجية للأمن القومي.", "badge-military"
        elif transit_house in [11, 1, 7] or selected_planet in [swe.URANUS, swe.JUPITER]:
            return "تغيير شعبي", f"{aspect_desc} - حراك جماهيري، احتجاجات، تغيرات ديموغرافية، أو تحول في الرأي العام والمزاج الشعبي.", "badge-popular"
        elif transit_house in [2, 10] or selected_planet in [swe.JUPITER, swe.SATURN]:
            return "تغيير اقتصادي", f"{aspect_desc} - تحولات اقتصادية قومية، ضغوط مالية، أو إصلاحات بنكية وموارد.", "badge-eco"
        else:
            return "تغيير شامل", f"{aspect_desc} - تحولات هيكلية كبرى، أحداث سياسية أو اجتماعية واسعة ومفصلية.", "badge-comprehensive"

# ==================== 3. Streamlit User Interface ====================
st.markdown("""
<div class="main-header">
    <h1>رادار نبتون هوميا ايريس المطور</h1>
    <p>إعداد الدكتور المبرمج ملهم أحمد</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ إعدادات الإدخال")
    entity_type = st.selectbox("اختر نوع الكيان:", ["شخص", "دولة", "شركة"])
    name_input = st.text_input("اسم الشخص أو الدولة أو الشركة:", value="كيان جديد")
    
    st.subheader("تاريخ الميلاد / التأسيس")
    year = st.number_input("السنة", min_value=1900, max_value=2026, value=1981)
    month = st.number_input("الشهر", min_value=1, max_value=12, value=4)
    day = st.number_input("اليوم", min_value=1, max_value=31, value=17)
    
    filter_mode = st.radio("عرض النتائج:", ["جميع السنوات", "السنوات الحرجة (CRITICAL) فقط"])
    
    run_btn = st.button("تشغيل رادار التوقعات الفلكية", type="primary", use_container_width=True)

if run_btn:
    try:
        birth_date = date(year, month, day)
        birth_jd = swe.julday(birth_date.year, birth_date.month, birth_date.day, 12.0)
        
        # حساب البرج الشمسي كبرج طالع (Whole Sign)
        sun_long = get_planet_longitude(birth_jd, swe.SUN)
        sun_sign_idx, sun_sign_name, sun_deg = get_zodiac_sign(sun_long)
        
        # تشغيل محرك USM للحصول على السنوات والتواريخ
        usm_data = run_usm_engine_daily(birth_date)
        
        st.success(f"تم بنجاح تشغيل رادار USM وفحص الخارطة لـ **{name_input}** | البرج الشمسي / الطالع (Whole Sign): **{sun_sign_name}** ({sun_deg:.2f}°)")
        
        # تصفية أو معالجة النتائج
        processed_results = []
        for row in usm_data:
            if filter_mode == "السنوات الحرجة (CRITICAL) فقط" and row["Status"] != "CRITICAL":
                continue
                
            # دمج محرك USM مع تصنيف الأنماط الفلكية الدقيقة
            change_type, aspect_detail, badge_class = analyze_astrological_pattern(
                entity_type, sun_sign_idx, row["YearDate"]
            )
            
            # إذا كانت الحالة عادية وليست حرجة، نمنحها شارة عادية
            if row["Status"] != "CRITICAL":
                badge_class = "badge-normal"
                change_type = f"مستقر ({change_type})"

            processed_results.append({
                "Age": row["Age"],
                "Date": row["DateStr"],
                "CalendarYear": row["YearDate"].year,
                "Status": row["Status"],
                "ChangeType": change_type,
                "Detail": aspect_detail,
                "Badge": badge_class
            })
            
        df_results = pd.DataFrame(processed_results)
        
        st.markdown(f"### 📊 نتائج الرادار ({len(df_results)} سجل تم تحليله)")
        
        # قالب تقرير HTML للطباعة والتصدير
        html_report = f"""
        <html dir="rtl" lang="ar">
        <head>
            <meta charset="utf-8">
            <title>تقرير رادار التوقعات الفلكية - {name_input}</title>
            <style>
                body {{ font-family: 'Cairo', Tahoma, sans-serif; padding: 30px; color: #333; }}
                h1, h2 {{ color: #1e3c72; text-align: center; }}
                .meta {{ background: #f0f4f8; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 10px; text-align: right; font-size: 14px; }}
                th {{ background-color: #1e3c72; color: white; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .critical {{ color: #990000; font-weight: bold; }}
                .footer {{ margin-top: 30px; text-align: center; font-size: 12px; color: #778; }}
            </style>
        </head>
        <body>
            <h1>تقرير نبتون هوميا ايريس المطور</h1>
            <div class="meta">
                <p><strong>اسم الكيان:</strong> {name_input} ({entity_type})</p>
                <p><strong>تاريخ الميلاد / التأسيس:</strong> {birth_date}</p>
                <p><strong>البرج الشمسي / الطالع (Whole Sign):</strong> {sun_sign_name}</p>
                <p><strong>تاريخ إصدار التقرير:</strong> {datetime.now().strftime('%Y-%m-%d')}</p>
            </div>
            <table>
                <tr>
                    <th>سنة العمر</th>
                    <th>التاريخ الحرج / المستهدف</th>
                    <th>حالة الرادار (USM)</th>
                    <th>نوع التغيير الفلكي</th>
                    <th>التحليل والاتصالات الفلكية والبيوت</th>
                </tr>
        """
        
        for idx, row in df_results.iterrows():
            is_crit = row['Status'] == "CRITICAL"
            status_style = "color: red; font-weight: bold;" if is_crit else "color: green;"
            
            st.markdown(f"""
            <div class="stCard" style="border-left: 5px solid {'#990000' if is_crit else '#2e7d32'};">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span style="font-size: 18px; font-weight: bold; color: #1e3c72;">العمر: {row['Age']} سنة</span> | 
                        <span style="color: #666;">التاريخ: {row['Date']}</span> |
                        <span style="{status_style}">حالة USM: {row['Status']}</span>
                    </div>
                    <div>
                        <span class="{row['Badge']}">{row['ChangeType']}</span>
                    </div>
                </div>
                <hr style="margin: 10px 0; border: none; border-top: 1px solid #eee;">
                <p style="margin: 0; color: #444;">{row['Detail']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            html_report += f"""
                <tr>
                    <td>{row['Age']}</td>
                    <td>{row['Date']}</td>
                    <td style="{status_style}">{row['Status']}</td>
                    <td><b>{row['ChangeType']}</b></td>
                    <td>{row['Detail']}</td>
                </tr>
            """
            
        html_report += """
            </table>
            <div class="footer">
                <p>جميع الحقوق محفوظة 2026 - الدكتور ملهم أحمد</p>
            </div>
        </body>
        </html>
        """
        
        # زر تنزيل التقرير بصيغة HTML قابل للطباعة
        st.markdown("---")
        st.subheader("🖨️ طباعة وتصدير التقرير")
        b64 = base64.b64encode(html_report.encode('utf-8')).decode("utf-8")
        href = f'<a href="data:text/html;base64,{b64}" download="USM_Astro_Report_{name_input}.html" target="_blank" style="background-color: #2a5298; color: white; padding: 12px 20px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">📥 تحميل التقرير الشامل بصيغة HTML (قابل للطباعة)</a>'
        st.markdown(href, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"حدث خطأ أثناء تنفيذ الحسابات: {str(e)}")
else:
    st.info("👈 يرجى إدخال البيانات في القائمة الجانبية والضغط على زر **تشغيل رادار التوقعات الفلكية** لبدء التحليل.")