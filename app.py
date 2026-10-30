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
