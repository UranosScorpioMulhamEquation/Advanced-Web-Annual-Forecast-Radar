import streamlit as st
import pandas as pd
from supabase import create_client, Client

# ==========================================================
# 1. إعدادات الصفحة الأساسية
# ==========================================================
st.set_page_config(
    page_title="المنظومة الفلكية المطورة - استرو رادار",
    page_icon="🪐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# تهيئة حالة المصادقة
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

# دالة الاتصال بـ Supabase
@st.cache_resource
def init_supabase() -> Client:
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"خطأ في الاتصال بقاعدة البيانات: {e}")
        return None

supabase = init_supabase()

# قراءة معاملات الرابط
query_params = st.query_params
url_token = query_params.get("token", "")

# ==========================================================
# 2. التحقق الأمني من التوكن المؤقت في حال لم يتم المصادقة بعد
# ==========================================================
if not st.session_state['authenticated']:
    if url_token and supabase is not None:
        try:
            # البحث عن السجل المطابق للتوكن في السحابة
            response = supabase.table("licenses").select("*").eq("token", url_token).execute()
            rows = response.data
            
            if len(rows) > 0:
                customer = rows[0]
                phone_num = customer.get("phone")
                
                # مسح التوكن من القاعدة فوراً لمنع إعادة استخدام الرابط أو مشاركته
                supabase.table("licenses").update({"token": None}).eq("phone", phone_num).execute()
                
                # توثيق الجلسة وفتح التطبيق
                st.session_state['authenticated'] = True
                st.query_params.clear()
                st.rerun()
            else:
                # توكن وهمي أو تم استخدامه من قبل - واجهة داكنة احترافية
                st.markdown("""
                <style>
                @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap');
                [data-testid="stSidebar"] { display: none !important; }
                [data-testid="stAppViewContainer"] {
                    background: radial-gradient(circle at 50% 20%, #1a0b0e 0%, #0b070a 60%, #050304 100%) !important;
                    font-family: 'Cairo', Tahoma, sans-serif !important;
                    direction: rtl !important;
                    color: #f1f5f9 !important;
                }
                .security-card-danger {
                    background: rgba(26, 12, 16, 0.75);
                    border: 1px solid rgba(239, 68, 68, 0.4);
                    box-shadow: 0 20px 50px -10px rgba(239, 68, 68, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(16px);
                    -webkit-backdrop-filter: blur(16px);
                    padding: 45px 35px;
                    border-radius: 22px;
                    text-align: center;
                    direction: rtl;
                    max-width: 680px;
                    margin: 60px auto 30px auto;
                    animation: fadeIn 0.6s cubic-bezier(0.16, 1, 0.3, 1);
                }
                .shield-glow {
                    width: 75px;
                    height: 75px;
                    line-height: 75px;
                    font-size: 38px;
                    background: radial-gradient(circle, rgba(239, 68, 68, 0.25) 0%, rgba(239, 68, 68, 0.05) 70%);
                    border: 1px solid rgba(239, 68, 68, 0.4);
                    border-radius: 50%;
                    margin: 0 auto 20px auto;
                    box-shadow: 0 0 25px rgba(239, 68, 68, 0.4);
                }
                .badge-ip {
                    display: inline-flex;
                    align-items: center;
                    gap: 8px;
                    background: rgba(239, 68, 68, 0.12);
                    border: 1px solid rgba(239, 68, 68, 0.3);
                    color: #fca5a5;
                    padding: 8px 18px;
                    border-radius: 30px;
                    font-size: 14px;
                    font-weight: 600;
                    margin-top: 25px;
                }
                .code-pill {
                    background: rgba(255, 255, 255, 0.07);
                    border: 1px solid rgba(255, 255, 255, 0.15);
                    padding: 3px 10px;
                    border-radius: 8px;
                    color: #38bdf8;
                    font-family: monospace;
                    direction: ltr;
                    display: inline-block;
                }
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(15px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                </style>
                <div class="security-card-danger">
                    <div class="shield-glow">⚠️</div>
                    <h2 style="color: #f87171; font-weight: 800; font-size: 26px; margin-bottom: 12px; letter-spacing: -0.5px;">تنبيه أمني: رابط غير صالح أو منتهي الصلاحية</h2>
                    <p style="font-size: 18px; color: #fca5a5; margin-top: 15px; font-weight: 600; line-height: 1.6;">هذا الرابط تم استخدامه مسبقاً أو غير مصرح به.</p>
                    <p style="font-size: 16px; color: #94a3b8; margin-top: 10px; line-height: 1.7;">الرجاء تشغيل ملف التفعيل الخاص بك (<span class="code-pill">launcher.bat</span>) لفتح المنظومة.</p>
                    <div class="badge-ip">
                        <span>🛡️</span>
                        <span>تنويه : المنظومة محمية بشهادة ملكية فكرية رقم 2026-4630.</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                st.stop()
        except Exception as e:
            st.error(f"حدث خطأ أثناء التحقق من الأمان: {e}")
            st.stop()
    else:
        # في حال فتح الرابط العام مباشرة بدون ملف التفعيل - واجهة داكنة متميزة
        st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap');
        [data-testid="stSidebar"] { display: none !important; }
        [data-testid="stAppViewContainer"] {
            background: radial-gradient(circle at 50% 15%, #15141f 0%, #090a10 60%, #040508 100%) !important;
            font-family: 'Cairo', Tahoma, sans-serif !important;
            direction: rtl !important;
            color: #f1f5f9 !important;
        }
        .security-card-warning {
            background: rgba(22, 19, 13, 0.75);
            border: 1px solid rgba(245, 158, 11, 0.35);
            box-shadow: 0 20px 50px -10px rgba(245, 158, 11, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            padding: 45px 35px;
            border-radius: 22px;
            text-align: center;
            direction: rtl;
            max-width: 680px;
            margin: 50px auto 25px auto;
            animation: fadeIn 0.6s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .lock-glow {
            width: 75px;
            height: 75px;
            line-height: 75px;
            font-size: 36px;
            background: radial-gradient(circle, rgba(245, 158, 11, 0.25) 0%, rgba(245, 158, 11, 0.05) 70%);
            border: 1px solid rgba(245, 158, 11, 0.4);
            border-radius: 50%;
            margin: 0 auto 20px auto;
            box-shadow: 0 0 25px rgba(245, 158, 11, 0.35);
        }
        .badge-ip-warn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: rgba(245, 158, 11, 0.12);
            border: 1px solid rgba(245, 158, 11, 0.3);
            color: #fde68a;
            padding: 8px 18px;
            border-radius: 30px;
            font-size: 14px;
            font-weight: 600;
            margin-top: 25px;
        }
        .code-pill {
            background: rgba(255, 255, 255, 0.07);
            border: 1px solid rgba(255, 255, 255, 0.15);
            padding: 3px 10px;
            border-radius: 8px;
            color: #38bdf8;
            font-family: monospace;
            direction: ltr;
            display: inline-block;
        }
        .portal-card {
            background: rgba(15, 18, 28, 0.7);
            border: 1px solid rgba(139, 92, 246, 0.25);
            box-shadow: 0 15px 35px -5px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            border-radius: 18px;
            padding: 30px 25px;
            margin-top: 15px;
        }
        .stTextInput input {
            background-color: rgba(11, 15, 25, 0.85) !important;
            border: 1px solid rgba(139, 92, 246, 0.35) !important;
            color: #f8fafc !important;
            border-radius: 12px !important;
            padding: 12px 16px !important;
            font-family: 'Cairo', sans-serif !important;
            text-align: center !important;
            font-size: 16px !important;
            transition: all 0.3s ease !important;
        }
        .stTextInput input:focus {
            border-color: #8b5cf6 !important;
            box-shadow: 0 0 20px rgba(139, 92, 246, 0.4) !important;
        }
        .stButton button {
            background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%) !important;
            color: #ffffff !important;
            border: 1px solid rgba(255, 255, 255, 0.18) !important;
            border-radius: 12px !important;
            font-weight: 700 !important;
            font-size: 16px !important;
            padding: 10px 24px !important;
            font-family: 'Cairo', sans-serif !important;
            box-shadow: 0 8px 25px -5px rgba(124, 58, 237, 0.5) !important;
            transition: all 0.3s ease !important;
        }
        .stButton button:hover {
            background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%) !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 12px 30px -5px rgba(139, 92, 246, 0.65) !important;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(15px); }
            to { opacity: 1; transform: translateY(0); }
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="security-card-warning">
            <div class="lock-glow">🔒</div>
            <h2 style="color: #fbbf24; font-weight: 800; font-size: 26px; margin-bottom: 12px; letter-spacing: -0.5px;">وصول غير مصرح به</h2>
            <p style="font-size: 18px; color: #fde68a; margin-top: 15px; font-weight: 600; line-height: 1.6;">لا يمكن تشغيل المنظومة الفلكية مباشرة عبر هذا الرابط العام.</p>
            <p style="font-size: 16px; color: #94a3b8; margin-top: 10px; line-height: 1.7;">الرجاء تشغيل ملف التفعيل الخاص بك (<span class="code-pill">launcher.bat</span>) للوصول إلى البرنامج.</p>
            <div class="badge-ip-warn">
                <span>🛡️</span>
                <span>تنويه : المنظومة محمية بشهادة ملكية فكرية رقم 2026-4630.</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # --- بوابة دخول المبرمج السرية من الهاتف ---
        st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            <div class="portal-card">
                <div style="text-align: center; margin-bottom: 15px;">
                    <span style="font-size: 32px; display: block; margin-bottom: 8px;">🛠️</span>
                    <h4 style="color: #c4b5fd; font-weight: 800; font-size: 20px; margin: 0;">بوابة دخول المبرمج</h4>
                    <p style="color: #64748b; font-size: 13px; margin-top: 4px;">خاصة بالإدارة والتطوير السحابي</p>
                </div>
            """, unsafe_allow_html=True)
            
            admin_pass = st.text_input("أدخل كلمة مرور المبرمج السرية:", type="password", key="admin_secret_input")
            if st.button("دخول المشرف", use_container_width=True):
                if admin_pass and admin_pass == st.secrets.get("ADMIN_PASSWORD"):
                    st.session_state['authenticated'] = True
                    st.success("تم التحقق بنجاح! جاري فتح المنظومة...")
                    st.rerun()
                else:
                    st.error("كلمة المرور غير صحيحة!")
            
            st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

# ==========================================================
# 🚀 [التطبيق الرئيسي الموحد - يعمل فقط بعد نجاح المصادقة الأمنية]
# ==========================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800;900&family=Tajawal:wght@400;500;700;800&display=swap');

/* --- الضبط العام للغة العربية والخلفية الكونية الداكنة --- */
html, body, [class*="css"], .stApp {
    direction: rtl !important;
    text-align: right !important;
    font-family: 'Cairo', 'Tajawal', Tahoma, sans-serif !important;
    background-color: #07090e !important;
    color: #e2e8f0 !important;
}

/* خلفية التطبيق الرئيسية بتدرج سديمي فلكي */
[data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at 15% 15%, rgba(124, 58, 237, 0.08) 0%, transparent 45%),
                radial-gradient(circle at 85% 85%, rgba(245, 158, 11, 0.05) 0%, transparent 45%),
                radial-gradient(circle at 50% 50%, rgba(14, 165, 233, 0.04) 0%, transparent 60%),
                #07090e !important;
}

/* شريط الهيدر العلوي شفاف بالكامل */
[data-testid="stHeader"] {
    background: transparent !important;
}

/* تخصيص شريط التمرير Scrollbar بنمط أنيق داكن */
::-webkit-scrollbar {
    width: 7px;
    height: 7px;
}
::-webkit-scrollbar-track {
    background: #090c14;
}
::-webkit-scrollbar-thumb {
    background: #242c3d;
    border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
    background: #7c3aed;
}

/* --- تصميم القائمة الجانبية الفاخرة --- */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0e1322 0%, #080a12 100%) !important;
    border-left: 1px solid rgba(139, 92, 246, 0.18) !important;
    box-shadow: -5px 0 25px rgba(0, 0, 0, 0.4) !important;
}

[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    color: #f8fafc !important;
    font-weight: 800 !important;
    font-size: 22px !important;
    text-shadow: 0 0 15px rgba(139, 92, 246, 0.4);
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    padding-bottom: 12px;
}

/* تخصيص خيارات القائمة الراديوية كأزرار تفاعلية زجاجية */
div[data-testid="stRadio"] > div[role="radiogroup"] {
    gap: 8px;
}

div[data-testid="stRadio"] > div[role="radiogroup"] > label {
    background: rgba(255, 255, 255, 0.025) !important;
    border: 1px solid rgba(255, 255, 255, 0.06) !important;
    border-radius: 12px !important;
    padding: 10px 16px !important;
    margin-bottom: 6px !important;
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
    cursor: pointer !important;
    color: #cbd5e1 !important;
}

div[data-testid="stRadio"] > div[role="radiogroup"] > label:hover {
    background: rgba(139, 92, 246, 0.12) !important;
    border-color: rgba(139, 92, 246, 0.35) !important;
    color: #ffffff !important;
    transform: translateX(-4px);
    box-shadow: 0 4px 15px rgba(124, 58, 237, 0.2);
}

/* العنصر النشط المختار */
div[data-testid="stRadio"] > div[role="radiogroup"] > label:has(input:checked) {
    background: linear-gradient(90deg, rgba(124, 58, 237, 0.28) 0%, rgba(79, 70, 229, 0.18) 100%) !important;
    border: 1px solid #8b5cf6 !important;
    box-shadow: 0 0 18px rgba(139, 92, 246, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.15) !important;
    color: #ffffff !important;
    font-weight: 700 !important;
}

div[data-testid="stRadio"] > label {
    color: #94a3b8 !important;
    font-size: 14px !important;
    font-weight: 600 !important;
    margin-bottom: 10px !important;
}

/* --- تخصيص الأزرار الرئيسية --- */
.stButton button {
    background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%) !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    font-size: 16px !important;
    border-radius: 12px !important;
    border: 1px solid rgba(255, 255, 255, 0.18) !important;
    padding: 0.65rem 1.6rem !important;
    box-shadow: 0 6px 20px -3px rgba(124, 58, 237, 0.45) !important;
    transition: all 0.3s ease !important;
}

.stButton button:hover {
    background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%) !important;
    box-shadow: 0 10px 28px -3px rgba(139, 92, 246, 0.6) !important;
    transform: translateY(-2px) !important;
    color: #ffffff !important;
}

/* تخصيص زر التحميل */
.stDownloadButton button {
    background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
    color: white !important;
    font-weight: 700 !important;
    font-size: 16px !important;
    border-radius: 12px !important;
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
    box-shadow: 0 6px 20px -3px rgba(2, 132, 199, 0.45) !important;
    transition: all 0.3s ease !important;
}

.stDownloadButton button:hover {
    background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 10px 28px -3px rgba(14, 165, 233, 0.6) !important;
}

/* تخصيص حقول الإدخال */
.stTextInput input, .stSelectbox [data-baseweb="select"], .stDateInput input, .stTimeInput input {
    background-color: rgba(17, 24, 39, 0.8) !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    color: #f8fafc !important;
    border-radius: 10px !important;
    font-family: 'Cairo', sans-serif !important;
}

/* بطاقات وتنبيهات مخصصة */
.sidebar-footer-badge {
    background: rgba(139, 92, 246, 0.1);
    border: 1px solid rgba(139, 92, 246, 0.25);
    border-radius: 12px;
    padding: 12px;
    margin-top: 25px;
    text-align: center;
    font-size: 13px;
    color: #c4b5fd;
}
</style>
""", unsafe_allow_html=True)

# القائمة الجانبية للمنظومة الفلكية
st.sidebar.markdown("""
<div style="text-align: center; padding: 10px 0 15px 0;">
    <div style="font-size: 34px; margin-bottom: 6px; filter: drop-shadow(0 0 10px rgba(139, 92, 246, 0.5));">🪐</div>
    <div style="font-size: 20px; font-weight: 800; color: #ffffff; letter-spacing: -0.5px;">منظومة استرو رادار</div>
    <div style="font-size: 12px; color: #a78bfa; font-weight: 600; margin-top: 4px;">المنظومة الفلكية المركزية المطورة v2.6</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.title("🪐 منظومة استرو رادار")
menu = st.sidebar.radio("اختر البرنامج:", [
    "🏠 الرئيسية",
    "📊 برنامج تحليل الخريطة الساعية",
    "🔭 السنوية التفصيلية للأفراد أو الشركات أو الدول",
    "✨ التوافقية العاطفية للشخصيات",
    "📁 نظريتي لكشف سنوات الخطر أفراد/دول",
    "⚖️ كشف سنوات الأزمات الزوجية / التجارية",
    "🔭 منظومة تحليل ميلادية/سنوية/توقعات",
    "📈 برنامج التنجيم الجغرافي",
    "🔢 برنامج خريطة الحدث العاطفية",
    "🔗 كشف سنوات الزواج-الإنجاب/صفات الشريك",
    "🌌 نظريتي لكشف سنوات التغيير أفراد/دول"
])

# شارة أمان وترخيص في أسفل القائمة الجانبية
st.sidebar.markdown("""
<div class="sidebar-footer-badge">
    <div style="display: flex; align-items: center; justify-content: center; gap: 6px; margin-bottom: 4px; font-weight: 700; color: #10b981;">
        <span style="font-size: 10px;">🟢</span> جلسة نشطة وموثقة
    </div>
    <div style="font-size: 11px; color: #94a3b8;">رقم الاعتماد: 2026-4630</div>
</div>
""", unsafe_allow_html=True)

# تشغيل الملف الفرعي مباشرة دون أي تعديل بداخله
if menu == "🏠 الرئيسية":
    with open("subpages/home.py", encoding="utf-8") as f:
        exec(f.read())
elif menu == "📊 برنامج تحليل الخريطة الساعية":
    with open("subpages/matrix.py", encoding="utf-8") as f:
        exec(f.read())
elif menu == "🔭 السنوية التفصيلية للأفراد أو الشركات أو الدول":
    with open("subpages/solar.py", encoding="utf-8") as f:
        exec(f.read())
elif menu == "✨ التوافقية العاطفية للشخصيات":
    with open("subpages/aura.py", encoding="utf-8") as f:
        exec(f.read())
elif menu == "📁 نظريتي لكشف سنوات الخطر أفراد/دول":
    with open("subpages/dan.py", encoding="utf-8") as f:
        exec(f.read())
elif menu == "⚖️ كشف سنوات الأزمات الزوجية / التجارية":
    with open("subpages/divorce.py", encoding="utf-8") as f:
        exec(f.read())
elif menu == "🔭 منظومة تحليل ميلادية/سنوية/توقعات":
    with open("subpages/fullastro.py", encoding="utf-8") as f:
        exec(f.read())
elif menu == "📈 برنامج التنجيم الجغرافي":
    with open("subpages/graph.py", encoding="utf-8") as f:
        exec(f.read())
elif menu == "🔢 برنامج خريطة الحدث العاطفية":
    with open("subpages/intmatrix.py", encoding="utf-8") as f:
        exec(f.read())
elif menu == "🔗 كشف سنوات الزواج-الإنجاب/صفات الشريك":
    with open("subpages/mrg.py", encoding="utf-8") as f:
        exec(f.read())
elif menu == "🌌 نظريتي لكشف سنوات التغيير أفراد/دول":
    with open("subpages/nhe.py", encoding="utf-8") as f:
        exec(f.read())
