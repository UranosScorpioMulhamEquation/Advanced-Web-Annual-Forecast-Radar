import streamlit as st

# إعدادات الصفحة الرئيسية
st.set_page_config(
    page_title="المنظومة الفلكية المركزية",
    page_icon="🪐",
    layout="wide",
    initial_sidebar_state="expanded"
)
# تطبيق اتجاه اليمين والخط العربي
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap');
html, body, [class*="css"] {
    direction: rtl;
    text-align: right;
    font-family: 'Cairo', Tahoma, sans-serif;
}
.stDownloadButton button {
    background-color: #1e3a8a !important;
    color: white !important;
    font-weight: bold;
    font-size: 16px;
}
.stButton button {
    background-color: #6D28D9;
    color: white;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)


# تصميم الواجهة الرئيسية
st.title("🪐 المنظومة الفلكية الحسابية والتحليلية")
st.markdown("---")

st.markdown("""
### مرحباً بك في المنظومة المركزية الخاصة بالتحليلات الفلكية
""")
st.markdown("""
### تم تطوير هذه المنظومة بواسطة الباحث الفلكي استرو رادار
""")

st.markdown("---")

# تعريف وتسمية الصفحات باللغة العربية
pg = st.navigation([
    st.Page("app.py", title="الرئيسية", icon="🏠"),
    st.Page("solar.py", title="برنامج خريطة العودة الشمسية أو السنوية للأفراد و الشركات و الدول", icon="🪐"),
    st.Page("matrix.py", title="مصفوفة القدر للأفراد", icon="📊"),
    st.Page("aura.py", title="برنامج الكشف الطاقي و علاج الهالة", icon="✨"),
    st.Page("dan.py", title="نظرية الدكتور ملهم احمد المطورة لكشف سنوات الخطر للأفراد و الشركات و الدول", icon="📁"),
    st.Page("divorce.py", title="برنامج كشف سنوات الأزمات الزوجية و الشراكة التجارية", icon="⚖️"),
    st.Page("fullastro.py", title=" المنظومة الفلكية الشاملة لتحليل الخارطة الميلادية و السنوية و توقعات خمسة سنوات للأفراد", icon="🔭"),
    st.Page("graph.py", title="برنامج التنجيم الجغرافي", icon="📈"),
    st.Page("intmatrix.py", title="مصفوفة القدر المدمج مع السنوات الخطرة للدول", icon="🔢"),
    st.Page("mrg.py", title="برنامج كشف سنوات الزواج و صفات الشريك المحتمله ", icon="🔗"),
    st.Page("nhe.py", title="نظرية الدكتور ملهم احمد المطورة لكشف سنوات التغيير للأفراد و الشركات و الدول", icon="🌌"),
])

pg.run()
