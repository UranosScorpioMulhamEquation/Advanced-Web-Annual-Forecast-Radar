import datetime
import html as html_lib
import math
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Tuple

import geonamescache
import pandas as pd
import pytz
import streamlit as st
import swisseph as swe
from timezonefinder import TimezoneFinder

# ==========================================
# إعدادات تقويم سويس إفيميريس (Swiss Ephemeris)
# ==========================================
swe.set_ephe_path("")  # وضع Moshier المدمج (لا يحتاج ملفات خارجية)

st.set_page_config(
    page_title="النظام المتقدم الشامل للأستروكارتوغرافيا المجالية",
    page_icon="🌟",
    layout="wide",
)

# ==========================================
# دعم اللغة العربية والاتجاه من اليمين لليسار (RTL)
# ==========================================
st.markdown(
    """
    <style>
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"],
    [data-testid="stToolbar"], [data-testid="stSidebar"] {
        direction: rtl;
        text-align: right;
        font-family: 'Tahoma', sans-serif;
    }
    .stSelectbox, .stTextInput, .stDateInput, .stTimeInput, .stNumberInput,
    .stButton, .stRadio, .stCheckbox, .stMarkdown, label, p {
        direction: rtl;
        text-align: right;
    }
    div[data-baseweb="base-input"] { direction: rtl; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================
# 0. الثوابت والإعدادات الفلكية
# ==========================================
COUNTRY_ORB = 3.0      # أوربت الدول
CITY_ORB = 1.0         # أوربت المدن (التأثير المباشر)
FAR_LIMIT = 2 * COUNTRY_ORB   # حتى هذا البعد يُحسب الأثر الخافت تلقائياً
MIN_LINES = 3          # أقل عدد خطوط يُكتب أثره لكل مدينة/دولة حتى لو كانت الخطوط بعيدة
MIN_POPULATION = 15000

# حدود أوروبا الجغرافية (لاستبعاد الجزر الأفريقية والأقاليم البعيدة وسيبيريا)
EUROPE_LAT = (34.0, 72.0)
EUROPE_LON = (-25.0, 60.0)

ARAB_ME_CODES = ["SA", "AE", "QA", "KW", "BH", "OM", "YE", "IQ", "SY", "LB", "JO", "PS", "EG"]
OTHER_ME_CODES = ["TR", "IR", "IL", "GE", "AM", "AZ"]
EUROPE_CODES = [
    "AL", "AD", "AT", "BY", "BE", "BA", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "GR", "HU", "IS", "IE", "IT", "XK", "LV", "LI", "LT", "LU", "MT", "MD", "MC",
    "ME", "NL", "MK", "NO", "PL", "PT", "RO", "RU", "SM", "RS", "SK", "SI", "ES", "SE",
    "CH", "UA", "GB", "VA",
]

ARABIC_NAMES = {
    "SA": "السعودية", "AE": "الإمارات", "QA": "قطر", "KW": "الكويت", "BH": "البحرين",
    "OM": "عُمان", "YE": "اليمن", "IQ": "العراق", "SY": "سوريا", "LB": "لبنان",
    "JO": "الأردن", "PS": "فلسطين", "EG": "مصر", "TR": "تركيا", "IR": "إيران",
    "IL": "إسرائيل", "GE": "جورجيا", "AM": "أرمينيا", "AZ": "أذربيجان", "CY": "قبرص",
    "AL": "ألبانيا", "AD": "أندورا", "AT": "النمسا", "BY": "بيلاروسيا", "BE": "بلجيكا",
    "BA": "البوسنة والهرسك", "BG": "بلغاريا", "HR": "كرواتيا", "CZ": "التشيك",
    "DK": "الدنمارك", "EE": "إستونيا", "FI": "فنلندا", "FR": "فرنسا", "DE": "ألمانيا",
    "GR": "اليونان", "HU": "المجر", "IS": "آيسلندا", "IE": "أيرلندا", "IT": "إيطاليا",
    "XK": "كوسوفو", "LV": "لاتفيا", "LI": "ليختنشتاين", "LT": "ليتوانيا",
    "LU": "لوكسمبورغ", "MT": "مالطا", "MD": "مولدوفا", "MC": "موناكو",
    "ME": "الجبل الأسود", "NL": "هولندا", "MK": "مقدونيا الشمالية", "NO": "النرويج",
    "PL": "بولندا", "PT": "البرتغال", "RO": "رومانيا", "RU": "روسيا (الأوروبية)",
    "SM": "سان مارينو", "RS": "صربيا", "SK": "سلوفاكيا", "SI": "سلوفينيا",
    "ES": "إسبانيا", "SE": "السويد", "CH": "سويسرا", "UA": "أوكرانيا",
    "GB": "المملكة المتحدة", "VA": "الفاتيكان",
}

REGION_TITLES = {
    "arab_me": "🕌 الدول العربية في الشرق الأوسط",
    "other_me": "🧭 بقية دول الشرق الأوسط والقوقاز",
    "europe": "🏰 أوروبا",
}

ANGLE_AR = {
    "MC": "MC (وسط السماء)",
    "AC": "AC (الطالع)",
    "DC": "DC (الغارب)",
    "IC": "IC (جذر السماء)",
}

PLANETS = {
    "الشمس (Sun)": swe.SUN,
    "القمر (Moon)": swe.MOON,
    "عطارد (Mercury)": swe.MERCURY,
    "الزهرة (Venus)": swe.VENUS,
    "المريخ (Mars)": swe.MARS,
    "المشتري (Jupiter)": swe.JUPITER,
    "زحل (Saturn)": swe.SATURN,
}

PLANET_META = {
    "الشمس (Sun)": {"type": "benefic", "weight": 0.8},
    "القمر (Moon)": {"type": "benefic", "weight": 0.6},
    "عطارد (Mercury)": {"type": "benefic", "weight": 0.5},
    "الزهرة (Venus)": {"type": "benefic", "weight": 1.0},
    "المشتري (Jupiter)": {"type": "benefic", "weight": 1.0},
    "المريخ (Mars)": {"type": "malefic", "weight": 0.8},
    "زحل (Saturn)": {"type": "malefic", "weight": 1.0},
}

GENERAL_TIPS = [
    f"أقوى تأثير يكون ضمن {CITY_ORB:g}° من الخط (مباشر)، ثم يضعف تدريجياً حتى {COUNTRY_ORB:g}° (متوسط) ثم {FAR_LIMIT:g}° (خافت).",
    "الخطوط البعيدة لا تُلغى بل تُحسب كأثر خلفي خافت يُضاف إلى الصورة الطاقية العامة للمدينة.",
    "للزواج والشراكات ركّز على خط DC للزهرة والمشتري، وللمسار المهني ركّز على خط MC للشمس والمشتري والزهرة، وللسكن خط IC للقمر والزهرة.",
    "جرّب الإقامة القصيرة قبل القرار الكبير، وقارن المدينة بما يناسب أهدافك الحالية (عمل، استقرار، علاقات).",
]
GENERAL_WARNINGS = [
    "خطوط زحل والمريخ لا تعني الشر بل اختبارات وضغوطاً: تحتاج انضباطاً وصبراً وإدارة للاندفاع.",
    "الخط الداعم قد يضخّم الإفراط أيضاً (إنفاق، غرور، توسّع زائد)؛ التوازن مطلوب.",
    "هذا التحليل أداة استرشادية ولا يغني عن الاعتبارات العملية: القانون، التكلفة، الأمان، الصحة، والأسرة.",
    "حسابات القمر جيومركزية (دون تصحيح اختلاف المنظر)، لذا قد يتحرك خط القمر قليلاً (حتى نحو درجة).",
]

# ==========================================
# 1. قاعدة بيانات الخطوط: الوصف + المجالات + النصيحة + التحذير
# ==========================================
def _l(desc: str, domains: List[str], advice: str, warning: str) -> Dict[str, Any]:
    return {"desc": desc, "domains": domains, "advice": advice, "warning": warning}


LINES_DB: Dict[str, Dict[str, Dict[str, Any]]] = {
    "الشمس (Sun)": {
        "MC": _l("خط وسط السماء: ذروة الشهرة، الصعود المهني والقيادة الظاهرة والنجاح العام.",
                 ["شهرة", "عمل", "مال"],
                 "اطلب المناصب القيادية والظهور العلني؛ هذا موضع مناسب لبناء اسم وسمعة.",
                 "احذر الغرور والتصادم مع أصحاب السلطة، فالأضواء تكشف الأخطاء أيضاً."),
        "AC": _l("خط الطالع: تعزيز الثقة الشخصية، الحيوية الجسدية وهيبة الحضور.",
                 ["شهرة", "صحة"],
                 "ابنِ حضورك الشخصي وعلامتك الخاصة وابدأ مشاريع تعتمد على شخصك.",
                 "قد تظهر الأنانية أو الإفراط في الحماس؛ وازن بين الثقة والتواضع."),
        "DC": _l("خط الغارب: شراكات مع شخصيات نافذة ومرموقة وعلاقات علنية بارزة.",
                 ["زواج و حب", "شهرة"],
                 "ابحث عن شراكات مع شخصيات مؤثرة؛ مناسب للارتباط والتعاقد العلني.",
                 "انتبه من الاعتماد على الشريك في تحديد هويتك أو الانجذاب لشخصيات متسلطة."),
        "IC": _l("خط جذر السماء: استقرار داخلي وتصالح مع الهوية والعائلة والجذور.",
                 ["استقرار"],
                 "مناسب للاستقرار الأسري وشراء بيت والتصالح مع الجذور.",
                 "قد تنشغل بالماضي والعائلة على حساب الطموح الخارجي."),
    },
    "القمر (Moon)": {
        "MC": _l("خط وسط السماء: نجاح في مهن الجمهور، الإعلام، التغذية والرأي العام.",
                 ["شهرة", "عمل"],
                 "ممتاز للمهن الجماهيرية والإعلام والضيافة والغذاء والرعاية.",
                 "تقلبات في السمعة والرأي العام؛ لا تبنِ قراراتك المهنية على مزاج لحظي."),
        "AC": _l("خط الطالع: حساسية عالية، جاذبية شعبية وتفاعل وجداني مع المحيط.",
                 ["استقرار", "شهرة"],
                 "تتقبلك البيئة المحلية بسهولة وتكسب شعبية؛ ثق بحدسك.",
                 "حساسية زائدة وتأثر بالمحيط؛ احمِ طاقتك النفسية."),
        "DC": _l("خط الغارب: علاقات عميقة تعتمد على الألفة العاطفية والحدس المشترك.",
                 ["زواج و حب", "استقرار"],
                 "علاقات دافئة وعميقة؛ مناسب للزواج والشراكات القائمة على الألفة.",
                 "تعلق عاطفي زائد أو اعتماد متبادل مرهق؛ حافظ على استقلالك."),
        "IC": _l("خط جذر السماء: أفضل خط للاستقرار العاطفي، السكن، وشراء العقارات والأمان النفسي.",
                 ["استقرار"],
                 "الأفضل للسكن وشراء العقار وتكوين أسرة وبناء الأمان النفسي.",
                 "خطر الانغلاق والحنين المفرط والتعلق بالماضي؛ لا تعزل نفسك."),
    },
    "عطارد (Mercury)": {
        "MC": _l("خط وسط السماء: نجاح في التجارة، الأعمال الحرة، الإعلام، والكتابة والتدريس.",
                 ["عمل", "مال"],
                 "مناسب للتجارة والكتابة والتدريس والإعلام والعقود والعمل الحر.",
                 "تشتت وكثرة الالتزامات وتسرع في التوقيع؛ راجع الوثائق جيداً."),
        "AC": _l("خط الطالع: نشاط ذهني متوقد، سرعة في البديهة والتواصل الفعّال.",
                 ["عمل"],
                 "استفد من سرعة التعلم والتواصل لبناء شبكة علاقات ودراسة وسفر.",
                 "عصبية وقلق وإرهاق ذهني؛ نظّم أوقات الراحة."),
        "DC": _l("خط الغارب: نقاشات مثمرة، عقود تجارية ناجحة وشراكات فكرية.",
                 ["عمل", "زواج و حب"],
                 "ممتاز لعقد الصفقات والتفاوض والشراكات الفكرية.",
                 "احذر الجدال والالتباس في الاتفاقات؛ اكتب كل شيء بوضوح."),
        "IC": _l("خط جذر السماء: بيئة منزلية محفزة للبحث، الدراسة والتواصل.",
                 ["استقرار", "عمل"],
                 "بيئة جيدة للدراسة والعمل من المنزل والبحث.",
                 "كثرة الضجيج أو الانشغال الذهني تؤثر على الراحة؛ خصص مساحة هادئة."),
    },
    "الزهرة (Venus)": {
        "MC": _l("خط وسط السماء: ازدهار مالي، مشاريع فنية أو تجارية مربحة وذوق رفيع.",
                 ["مال", "شهرة", "عمل"],
                 "ازدهار في الفنون والجمال والموضة والعلاقات العامة والتجارة الراقية.",
                 "احذر الإسراف والاعتماد على الجاذبية بدل الكفاءة."),
        "AC": _l("خط الطالع: سحر شخصي أخاذ، جاذبية عالية وحب وتقدير من المحيط.",
                 ["زواج و حب", "شهرة"],
                 "جاذبية شخصية عالية؛ مناسب للتعارف وبناء العلاقات الاجتماعية.",
                 "الدلال والكسل والانغماس في الملذات."),
        "DC": _l("خط الغارب: أقوى وأفضل خط للحب، الزواج السعيد والشراكات العاطفية والانسجام.",
                 ["زواج و حب"],
                 "أقوى خط للارتباط والزواج وللشراكات المنسجمة.",
                 "ميل لتجاهل العلامات التحذيرية طلباً للسلام؛ لا تتنازل عن حدودك."),
        "IC": _l("خط جذر السماء: منزل جميل مريح، بحبوحة عيش وراحة نفسية عميقة.",
                 ["استقرار", "زواج و حب"],
                 "منزل جميل ومريح وحياة أسرية هانئة.",
                 "الراحة الزائدة قد تخفض الطموح؛ حافظ على نشاطك."),
    },
    "المريخ (Mars)": {
        "MC": _l("خط وسط السماء: طموح جريء، إنجاز مهني سريع، تنافسية عالية وقيادة ميدانية.",
                 ["عمل"],
                 "طاقة تنافسية للإنجاز السريع والقيادة الميدانية والمهن النشطة.",
                 "صدامات مع الرؤساء والمنافسين وإرهاق مهني؛ اضبط الاندفاع."),
        "AC": _l("خط الطالع: طاقة جسدية عالية وحماس، قد يصاحبها اندفاع أو صدامات.",
                 ["عمل", "صحة"],
                 "وجّه الطاقة نحو الرياضة والمشاريع الجريئة.",
                 "اندفاع وانفعال وحوادث وجروح؛ تجنب المخاطرة غير المحسوبة."),
        "DC": _l("خط الغارب: توتر محتمل أو احتكاك في الشراكات، ومواجهات تنافسية.",
                 ["زواج و حب"],
                 "اجعلها للمنافسة الشريفة والشراكات القائمة على النشاط والحركة.",
                 "خلافات وصراعات في الشراكات والزواج ونزاعات قانونية؛ تجنب التعاقد وقت التوتر."),
        "IC": _l("خط جذر السماء: أجواء متوترة في البيت وعدم استقرار أو إصلاحات منزلية مستمرة.",
                 ["استقرار"],
                 "مناسب لأعمال الإصلاح والبناء والتجديد.",
                 "توتر منزلي وعدم استقرار وخلافات عائلية وحوادث منزلية."),
    },
    "المشتري (Jupiter)": {
        "MC": _l("خط وسط السماء: قمة النجاح الوظيفي، الحظ الوافر، الترقيات والسمعة الطيبة الواسعة.",
                 ["مال", "شهرة", "عمل"],
                 "فرص ترقية وتوسع وسمعة طيبة؛ ابدأ مشاريع كبيرة وانشر اسمك.",
                 "تفاؤل مفرط وتوسع أكبر من الطاقة؛ احسب المخاطر جيداً."),
        "AC": _l("خط الطالع: تفاؤل، انفتاح، صحة ممتازة وفرص توسع شخصي واسعة.",
                 ["مال", "صحة"],
                 "تفاؤل وانفتاح وفرص نمو؛ مناسب للهجرة والبدايات الجديدة.",
                 "زيادة الوزن والإفراط والمبالغة في الوعود."),
        "DC": _l("خط الغارب: شراكات مباركة، عقود دولية ناجحة وزواج سعيد ومثمر.",
                 ["زواج و حب", "مال"],
                 "شراكات مباركة وعقود دولية وزواج مثمر.",
                 "لا توقّع التزامات مالية كبيرة دون مراجعة؛ سخاء زائد."),
        "IC": _l("خط جذر السماء: منزل واسع، استقرار مادي ومعنوي عميق وبركة في السكن.",
                 ["استقرار", "مال"],
                 "بيت واسع وبركة في السكن واستقرار مادي ومعنوي.",
                 "توسع في الإنفاق على العقار والكماليات."),
    },
    "زحل (Saturn)": {
        "MC": _l("خط وسط السماء: مسؤوليات ثقيلة، ضغوط مهنية وجهود مضنية تؤتي ثمارها ببطء شديد.",
                 ["عمل"],
                 "يكافئ الجهد المنظم؛ مناسب للمناصب الإدارية بعيدة المدى.",
                 "ضغوط وبطء وقيود؛ لا تتوقع نتائج سريعة."),
        "AC": _l("خط الطالع: جدية مفرطة، شعور بالثقل، اختبارات في التحمل والصبر الشخصي.",
                 ["صحة", "استقرار"],
                 "اعتمد الانضباط والتخطيط وروتيناً صحياً ثابتاً.",
                 "ثقل نفسي وتعب وانطواء."),
        "DC": _l("خط الغارب: شراكات جادة، جافة، أو تأخر وتحديات في الارتباط والزواج.",
                 ["زواج و حب"],
                 "مناسب للعلاقات الناضجة الجادة طويلة الأمد.",
                 "تأخر في الزواج وبرود وانفصال؛ شراكات صعبة."),
        "IC": _l("خط جذر السماء: أعباء عائلية ثقيلة، شعور بالوحدة أو جفاء عاطفي في بيئة السكن.",
                 ["استقرار"],
                 "قد يناسب بناء أساس متين طويل المدى بصبر.",
                 "وحدة وأعباء عائلية وسكن قاسٍ."),
    },
}

# ==========================================
# 2. البيانات الجغرافية
# ==========================================
@st.cache_data(show_spinner=False)
def load_cities() -> List[Dict[str, Any]]:
    gc = geonamescache.GeonamesCache()
    out: List[Dict[str, Any]] = []
    for cid, d in gc.get_cities().items():
        pop = int(d.get("population", 0) or 0)
        if pop < MIN_POPULATION:
            continue
        try:
            lat = float(d.get("latitude"))
            lon = float(d.get("longitude"))
        except (TypeError, ValueError):
            continue
        out.append({
            "id": str(cid),
            "name": d.get("name", ""),
            "country_code": d.get("countrycode", ""),
            "lat": lat,
            "lon": lon,
            "admin1": d.get("admin1code", ""),
            "population": pop,
            "timezone": d.get("timezone", ""),
        })
    return out


@st.cache_data(show_spinner=False)
def load_countries() -> Dict[str, Dict[str, Any]]:
    return geonamescache.GeonamesCache().get_countries()


@st.cache_resource
def get_tz_finder() -> TimezoneFinder:
    return TimezoneFinder()


def region_of(code: str) -> Optional[str]:
    if code in ARAB_ME_CODES:
        return "arab_me"
    if code in OTHER_ME_CODES:
        return "other_me"
    if code in EUROPE_CODES:
        return "europe"
    return None


def city_in_scope(c: Dict[str, Any]) -> bool:
    reg = region_of(c["country_code"])
    if reg is None:
        return False
    if reg == "europe":
        return (EUROPE_LAT[0] <= c["lat"] <= EUROPE_LAT[1]
                and EUROPE_LON[0] <= c["lon"] <= EUROPE_LON[1])
    return True


@st.cache_data(show_spinner=False)
def load_scope_cities() -> List[Dict[str, Any]]:
    return [c for c in load_cities() if city_in_scope(c)]


def get_cities_by_country(country_code: str) -> List[Dict[str, Any]]:
    return sorted(
        [c for c in load_cities() if c["country_code"] == country_code],
        key=lambda c: c["population"],
        reverse=True,
    )


tf = get_tz_finder()
countries_data = load_countries()
country_name_to_code = {info["name"]: code for code, info in countries_data.items()}
sorted_country_names = sorted(country_name_to_code.keys())


def country_ar(code: str) -> str:
    return ARABIC_NAMES.get(code, countries_data.get(code, {}).get("name", code))


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
# 3. محرك الحسابات الفلكية (خطوط الأستروكارتوغرافيا الحقيقية)
# ==========================================
def ang_diff(a: float, b: float) -> float:
    d = (a - b) % 360.0
    return d if d <= 180.0 else 360.0 - d


def compute_planet_positions(jd: float) -> Tuple[Dict[str, Tuple[float, float]], float]:
    """المطالع المستقيمة (RA) والميل (Dec) لكل كوكب + زمن غرينتش النجمي بالدرجات."""
    flags = swe.FLG_MOSEPH | swe.FLG_EQUATORIAL
    positions: Dict[str, Tuple[float, float]] = {}
    for pname, pid in PLANETS.items():
        res = swe.calc_ut(jd, pid, flags)
        xx = res[0]
        positions[pname] = (float(xx[0]), float(xx[1]))
    gmst_deg = (swe.sidtime(jd) * 15.0) % 360.0
    return positions, gmst_deg


def line_orbs(lat: float, lon: float,
              positions: Dict[str, Tuple[float, float]],
              gmst_deg: float) -> List[Tuple[str, str, float]]:
    """
    المسافة (بالدرجات الطولية) بين موقع المدينة وكل خط كوكبي:
      MC/IC: بين الطول المحلي وخط عبور الكوكب للنصف النهاري.
      AC/DC: بين الطول المحلي وخط شروق/غروب الكوكب عند نفس دائرة العرض.
    """
    ramc = (gmst_deg + lon) % 360.0
    tan_lat = math.tan(math.radians(lat))
    out: List[Tuple[str, str, float]] = []
    for pname, (ra, dec) in positions.items():
        out.append((pname, "MC", ang_diff(ra, ramc)))
        out.append((pname, "IC", ang_diff(ra + 180.0, ramc)))
        x = -tan_lat * math.tan(math.radians(dec))
        if -1.0 < x < 1.0:  # خارج هذا النطاق الكوكب لا يشرق/يغرب (حول قطبي)
            h0 = math.degrees(math.acos(x))
            out.append((pname, "AC", ang_diff(ra - h0, ramc)))
            out.append((pname, "DC", ang_diff(ra + h0, ramc)))
    return out


def scan_cities(cities: List[Dict[str, Any]],
                positions: Dict[str, Tuple[float, float]],
                gmst_deg: float) -> Dict[str, List[Tuple[str, str, float]]]:
    """كل خطوط كل مدينة (بدون قطع بالأوربت) كي نكتب الأثر حتى للخطوط البعيدة."""
    return {c["id"]: line_orbs(c["lat"], c["lon"], positions, gmst_deg) for c in cities}

# ==========================================
# 4. التقييم والتجميع (دول / مدن)
# ==========================================
def short_planet(p: str) -> str:
    return p.split(" ")[0]


def level_of(orb: float) -> str:
    if orb <= CITY_ORB:
        return "مباشر"
    if orb <= COUNTRY_ORB:
        return "متوسط"
    if orb <= FAR_LIMIT:
        return "خافت"
    return "بعيد جداً"


def influence(orb: float, scale: float) -> float:
    """قوة الأثر: 100 عند الخط نفسه، وتتناقص بسلاسة مع البعد (50 عند orb = scale)."""
    return 100.0 / (1.0 + (orb / scale) ** 2)


def select_nearest(items: List[Any], key: Callable[[Any], float]) -> List[Any]:
    """نُبقي الخطوط ضمن FAR_LIMIT، ولو قلّت عن MIN_LINES نأخذ أقرب MIN_LINES خطوط مهما بعدت."""
    ordered = sorted(items, key=key)
    kept = [i for i in ordered if key(i) <= FAR_LIMIT]
    if len(kept) < MIN_LINES:
        kept = ordered[:MIN_LINES]
    return kept


def fmt_line(it: Dict[str, Any], with_city: bool = False) -> str:
    s = f"{short_planet(it['planet'])} على {ANGLE_AR[it['angle']]} (±{it['orb']:.2f}° · {it['level']})"
    if with_city:
        s += f" عند {it['city']}"
    return s


def top_domains(items: List[Dict[str, Any]], n: int = 4) -> List[str]:
    acc: Dict[str, float] = defaultdict(float)
    for it in items:
        for d in LINES_DB[it["planet"]][it["angle"]]["domains"]:
            acc[d] += it["score"]
    return [d for d, _ in sorted(acc.items(), key=lambda kv: -kv[1])[:n]]


def tier_of(summary: Dict[str, Any]) -> str:
    r = summary["ratio"]
    if r >= 0.5:
        base = "🌟 داعمة بقوة"
    elif r >= 0.2:
        base = "✅ داعمة"
    elif r > -0.2:
        base = "⚖️ مختلطة"
    elif r > -0.5:
        base = "⚠️ ضاغطة"
    else:
        base = "🚫 ضاغطة بقوة"
    if summary["nearest"]["orb"] > COUNTRY_ORB:
        base += " (أثر خافت)"
    return base


def summarize_lines(lines: List[Dict[str, Any]], scale: float) -> Dict[str, Any]:
    benefic: List[Dict[str, Any]] = []
    malefic: List[Dict[str, Any]] = []
    for h in lines:
        p = influence(h["orb"], scale)
        item = dict(h)
        item["power"] = round(p, 1)
        item["score"] = p * h["weight"]
        item["level"] = level_of(h["orb"])
        (benefic if h["type"] == "benefic" else malefic).append(item)
    benefic.sort(key=lambda x: -x["score"])
    malefic.sort(key=lambda x: -x["score"])
    b_total = sum(x["score"] for x in benefic)
    m_total = sum(x["score"] for x in malefic)
    total = b_total + m_total
    all_items = benefic + malefic
    summary = {
        "lines": all_items,
        "benefic": benefic,
        "malefic": malefic,
        "benefic_total": b_total,
        "malefic_total": m_total,
        "net": b_total - m_total,
        "ratio": (b_total - m_total) / total if total > 0 else 0.0,
        "support_domains": top_domains(benefic),
        "pressure_domains": top_domains(malefic),
        "nearest": min(all_items, key=lambda x: x["orb"]),
    }
    summary["tier"] = tier_of(summary)
    return summary


def make_line(c: Dict[str, Any], pname: str, ang: str, orb: float) -> Dict[str, Any]:
    meta = PLANET_META[pname]
    return {
        "city_id": c["id"],
        "city": c["name"],
        "country_code": c["country_code"],
        "planet": pname,
        "angle": ang,
        "orb": orb,
        "type": meta["type"],
        "weight": meta["weight"],
    }


def build_country_entries(cities: List[Dict[str, Any]],
                          city_lines: Dict[str, List[Tuple[str, str, float]]],
                          scope_codes: List[str]) -> Dict[str, Dict[str, Any]]:
    # لكل دولة: أقرب مدينة لكل خط (كوكب+وتد) كي لا يُحسب الخط الواحد مرات متعددة
    best: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for c in cities:
        cc = c["country_code"]
        for pname, ang, orb in city_lines[c["id"]]:
            key = (cc, pname, ang)
            cur = best.get(key)
            if cur is None or orb < cur["orb"]:
                best[key] = make_line(c, pname, ang, orb)
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for (cc, _, _), h in best.items():
        grouped[cc].append(h)

    entries: Dict[str, Dict[str, Any]] = {}
    for code in scope_codes:
        lines = grouped.get(code, [])
        if not lines:
            continue
        sel = select_nearest(lines, key=lambda x: x["orb"])
        e = summarize_lines(sel, COUNTRY_ORB)
        e.update({
            "kind": "country",
            "code": code,
            "name_ar": country_ar(code),
            "region": region_of(code),
        })
        entries[code] = e
    return entries


def build_city_entries(cities: List[Dict[str, Any]],
                       city_lines: Dict[str, List[Tuple[str, str, float]]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for c in cities:
        tuples = select_nearest(city_lines[c["id"]], key=lambda t: t[2])
        lines = [make_line(c, p, a, o) for p, a, o in tuples]
        e = summarize_lines(lines, CITY_ORB)
        e.update({
            "kind": "city",
            "city": c["name"],
            "city_id": c["id"],
            "country_code": c["country_code"],
            "country_ar": country_ar(c["country_code"]),
            "population": c["population"],
        })
        out.append(e)
    return out


def rank_cities(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ranked = sorted(entries, key=lambda e: e["net"], reverse=True)
    for i, e in enumerate(ranked, 1):
        e["rank"] = i
    return ranked


def order_entries(entries: Dict[str, Dict[str, Any]], codes: List[str],
                  birth_code: str) -> List[Dict[str, Any]]:
    lst = [entries[c] for c in codes if c in entries]
    lst.sort(key=lambda e: e["net"], reverse=True)
    for i, e in enumerate(lst, 1):
        e["rank"] = i
    lst.sort(key=lambda e: 0 if e["code"] == birth_code else 1)  # دولة الميلاد أولاً
    return lst


def top_cities_by_country(city_entries: List[Dict[str, Any]], limit: int = 3) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for c in city_entries:
        grouped[c["country_code"]].append(c)
    out: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for code, lst in grouped.items():
        out[code] = {
            "best": sorted([c for c in lst if c["net"] > 0], key=lambda c: -c["net"])[:limit],
            "worst": sorted([c for c in lst if c["net"] < 0], key=lambda c: c["net"])[:limit],
        }
    return out


def energy_summary(e: Dict[str, Any]) -> str:
    n = e["nearest"]
    who = e["city"] if e.get("kind") == "city" else e["name_ar"]
    r = e["ratio"]
    if r >= 0.2:
        kind = "الطاقة العامة داعمة"
    elif r <= -0.2:
        kind = "الطاقة العامة ضاغطة"
    else:
        kind = "الطاقة العامة مختلطة"
    s = (f"أقرب خط لـ {who}: {short_planet(n['planet'])} على {ANGLE_AR[n['angle']]} "
         f"على بعد {n['orb']:.2f}° ({n['level']}). {kind}")
    if e["support_domains"]:
        s += "؛ الدعم في: " + "، ".join(e["support_domains"][:3])
    if e["pressure_domains"]:
        s += "؛ الضغط في: " + "، ".join(e["pressure_domains"][:3])
    if n["orb"] > COUNTRY_ORB:
        s += "؛ الأثر عام وخلفي لأن الخطوط بعيدة نسبياً"
    return s + "."


def entry_texts(e: Dict[str, Any]) -> Dict[str, Any]:
    with_city = e.get("kind") == "country"
    ben, mal = e["benefic"], e["malefic"]
    src_adv = ben[:3] if ben else mal[:2]
    src_warn = mal[:3] if mal else ben[:2]

    def tag(it: Dict[str, Any]) -> str:
        return f"{short_planet(it['planet'])} {it['angle']} [{it['level']}]"

    return {
        "summary": energy_summary(e),
        "benefic_lines": [fmt_line(it, with_city) for it in ben],
        "malefic_lines": [fmt_line(it, with_city) for it in mal],
        "advice": [f"{tag(it)}: {LINES_DB[it['planet']][it['angle']]['advice']}" for it in src_adv],
        "warnings": [f"{tag(it)}: {LINES_DB[it['planet']][it['angle']]['warning']}" for it in src_warn],
    }

# ==========================================
# 5. بناء الجداول والعرض داخل Streamlit
# ==========================================
def show_df(df: pd.DataFrame) -> None:
    try:
        st.dataframe(df, width="stretch", hide_index=True)
    except Exception:
        st.dataframe(df, use_container_width=True, hide_index=True)


def countries_df(lst: List[Dict[str, Any]], birth_code: str) -> pd.DataFrame:
    rows = []
    for e in lst:
        rows.append({
            "الترتيب": e["rank"],
            "الدولة": ("🏠 " if e["code"] == birth_code else "") + e["name_ar"],
            "التصنيف": e["tier"],
            "الميزان": round(e["net"]),
            "الدعم": round(e["benefic_total"]),
            "الضغط": round(e["malefic_total"]),
            "أقرب خط": fmt_line(e["nearest"], True),
            "أقوى خط داعم": fmt_line(e["benefic"][0], True) if e["benefic"] else "—",
            "أقوى خط ضاغط": fmt_line(e["malefic"][0], True) if e["malefic"] else "—",
            "مجالات الدعم": "، ".join(e["support_domains"]) or "—",
            "مجالات الضغط": "، ".join(e["pressure_domains"]) or "—",
        })
    return pd.DataFrame(rows)


def cities_df(lst: List[Dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for e in lst:
        t = entry_texts(e)
        rows.append({
            "الترتيب": e["rank"],
            "المدينة": e["city"],
            "التصنيف": e["tier"],
            "الميزان": round(e["net"]),
            "أقرب خط": fmt_line(e["nearest"]),
            "أقوى خط داعم": fmt_line(e["benefic"][0]) if e["benefic"] else "—",
            "أقوى خط ضاغط": fmt_line(e["malefic"][0]) if e["malefic"] else "—",
            "مجالات الدعم": "، ".join(e["support_domains"]) or "—",
            "مجالات الضغط": "، ".join(e["pressure_domains"]) or "—",
            "الأثر الطاقي": t["summary"],
            "أهم نصيحة": t["advice"][0] if t["advice"] else "—",
            "أهم تحذير": t["warnings"][0] if t["warnings"] else "—",
        })
    return pd.DataFrame(rows)


def render_entry_markdown(e: Dict[str, Any],
                          best_cities: Optional[List[Dict[str, Any]]] = None,
                          worst_cities: Optional[List[Dict[str, Any]]] = None) -> None:
    t = entry_texts(e)
    parts = [f"**التصنيف:** {e['tier']} — **الميزان:** {e['net']:.0f} "
             f"(دعم {e['benefic_total']:.0f} / ضغط {e['malefic_total']:.0f})",
             f"🔮 **الأثر الطاقي:** {t['summary']}"]
    if t["benefic_lines"]:
        parts.append("**✅ الخطوط الداعمة:**\n" + "\n".join(f"- {x}" for x in t["benefic_lines"]))
    if t["malefic_lines"]:
        parts.append("**⚠️ الخطوط الضاغطة:**\n" + "\n".join(f"- {x}" for x in t["malefic_lines"]))
    if t["advice"]:
        parts.append("**💡 أهم النصائح:**\n" + "\n".join(f"- {x}" for x in t["advice"]))
    if t["warnings"]:
        parts.append("**🚨 أهم التحذيرات:**\n" + "\n".join(f"- {x}" for x in t["warnings"]))
    if best_cities:
        parts.append("**🏙️ أفضل المدن داخل الدولة:** "
                     + "، ".join(f"{c['city']} ({c['net']:.0f})" for c in best_cities))
    if worst_cities:
        parts.append("**🏚️ المدن الأكثر ضغطاً:** "
                     + "، ".join(f"{c['city']} ({c['net']:.0f})" for c in worst_cities))
    st.markdown("\n\n".join(parts))

# ==========================================
# 6. تقرير HTML (جاهز للطباعة / PDF)
# ==========================================
REPORT_CSS = """
body { font-family: 'Tahoma', sans-serif; margin: 40px; background: #f4f6f7; color: #2c3e50; line-height: 1.7; }
.header { text-align: center; border-bottom: 3px solid #2c3e50; background: #fff; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
h1 { color: #1a252f; margin-bottom: 5px; }
.section { background: #fff; padding: 25px; margin-top: 25px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
.card { padding: 15px; margin: 15px 0; border-radius: 6px; }
.card-best { border-right: 6px solid #27ae60; background: #f1f9f5; }
.card-worst { border-right: 6px solid #c0392b; background: #fdf3f2; }
.card-mixed { border-right: 6px solid #f39c12; background: #fef9ec; }
.card h3 { margin-top: 0; }
.badge { display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 12px; margin: 3px 0 3px 5px; background: #e2e8f0; color: #1e293b; }
.badge-best { background: #dcfce7; color: #166534; }
.badge-worst { background: #fee2e2; color: #991b1b; }
.muted { color: #7f8c8d; }
ul { margin: 4px 0 8px 0; padding-right: 22px; }
.footer { text-align: center; margin-top: 40px; color: #7f8c8d; font-size: 13px; }
@media print { .card { page-break-inside: avoid; } }
"""


def esc(x: Any) -> str:
    return html_lib.escape(str(x))


def ul_html(items: List[str]) -> str:
    if not items:
        return "<p class='muted'>—</p>"
    return "<ul>" + "".join(f"<li>{esc(i)}</li>" for i in items) + "</ul>"


def badges_html(items: List[str], cls: str) -> str:
    if not items:
        return "<span class='muted'>—</span>"
    return "".join(f"<span class='badge {cls}'>{esc(i)}</span>" for i in items)


def card_class(e: Dict[str, Any]) -> str:
    if e["ratio"] >= 0.2:
        return "card-best"
    if e["ratio"] <= -0.2:
        return "card-worst"
    return "card-mixed"


def entry_card_html(e: Dict[str, Any], title: str,
                    best_cities: Optional[List[Dict[str, Any]]] = None,
                    worst_cities: Optional[List[Dict[str, Any]]] = None) -> str:
    t = entry_texts(e)
    h = [f"<div class='card {card_class(e)}'>",
         f"<h3>{esc(title)}</h3>",
         f"<p><b>التصنيف:</b> {esc(e['tier'])} | <b>الميزان:</b> {e['net']:.0f} "
         f"(دعم {e['benefic_total']:.0f} / ضغط {e['malefic_total']:.0f})</p>",
         f"<p><b>🔮 الأثر الطاقي:</b> {esc(t['summary'])}</p>"]
    if t["benefic_lines"]:
        h.append("<b>✅ الخطوط الداعمة:</b>" + ul_html(t["benefic_lines"]))
    if t["malefic_lines"]:
        h.append("<b>⚠️ الخطوط الضاغطة:</b>" + ul_html(t["malefic_lines"]))
    h.append("<p><b>مجالات الدعم:</b> " + badges_html(e["support_domains"], "badge-best") + "</p>")
    h.append("<p><b>مجالات الضغط:</b> " + badges_html(e["pressure_domains"], "badge-worst") + "</p>")
    if t["advice"]:
        h.append("<b>💡 أهم النصائح:</b>" + ul_html(t["advice"]))
    if t["warnings"]:
        h.append("<b>🚨 أهم التحذيرات:</b>" + ul_html(t["warnings"]))
    if best_cities:
        h.append("<p><b>🏙️ أفضل المدن:</b> "
                 + esc("، ".join(f"{c['city']} ({c['net']:.0f})" for c in best_cities)) + "</p>")
    if worst_cities:
        h.append("<p><b>🏚️ المدن الأكثر ضغطاً:</b> "
                 + esc("، ".join(f"{c['city']} ({c['net']:.0f})" for c in worst_cities)) + "</p>")
    h.append("</div>")
    return "".join(h)


def build_html_report(r: Dict[str, Any]) -> str:
    name = esc(r["name"])
    out = [
        "<!DOCTYPE html><html lang='ar' dir='rtl'><head><meta charset='UTF-8'>",
        f"<title>تقرير الأستروكارتوغرافيا - {name}</title>",
        f"<style>{REPORT_CSS}</style></head><body>",
        "<div class='header'>",
        "<h1>تقرير الأستروكارتوغرافيا المجالية (الشرق الأوسط + أوروبا)</h1>",
        f"<p>المستفيد: <strong>{name}</strong> | الميلاد: {esc(r['birth_date'])} {esc(r['birth_time'])} "
        f"| {esc(r['place_label'])} ({esc(r['tz'])})</p>",
        f"<p>أوربت الدول: {COUNTRY_ORB:g}° | أوربت المدن: {CITY_ORB:g}° | "
        f"الأثر الخافت يُحسب حتى {FAR_LIMIT:g}° وأقرب {MIN_LINES} خطوط مهما بعدت</p>",
        "</div>",
    ]

    if r["target_code"]:
        code = r["target_code"]
        e = r["country_entries"].get(code)
        out.append(f"<div class='section'><h2>📍 ملخص دولة {esc(country_ar(code))}</h2>")
        if e:
            tc = r["top_cities"].get(code, {"best": [], "worst": []})
            out.append(entry_card_html(e, country_ar(code), tc["best"], tc["worst"]))
        out.append("</div>")
        out.append(f"<div class='section'><h2>🏙️ جميع مدن {esc(country_ar(code))} مرتبة من الأفضل إلى الأضعف "
                   f"({len(r['city_entries'])} مدينة)</h2>")
        for c in r["city_entries"]:
            out.append(entry_card_html(c, f"المركز {c['rank']}: {c['city']}"))
        out.append("</div>")
    else:
        for reg in ("arab_me", "other_me", "europe"):
            lst = r["ordered"][reg]
            if not lst:
                continue
            out.append(f"<div class='section'><h2>{esc(REGION_TITLES[reg])}</h2>")
            for e in lst:
                tc = r["top_cities"].get(e["code"], {"best": [], "worst": []})
                prefix = "🏠 (دولة الميلاد) " if e["code"] == r["birth_code"] else ""
                out.append(entry_card_html(e, f"{prefix}المركز {e['rank']}: {e['name_ar']}",
                                           tc["best"], tc["worst"]))
            out.append("</div>")

    out.append("<div class='section'><h2>💡 نصائح عامة</h2>" + ul_html(GENERAL_TIPS)
               + "<h2>🚨 تحذيرات عامة</h2>" + ul_html(GENERAL_WARNINGS) + "</div>")
    out.append("<div class='footer'>تم إعداد هذا التقرير عبر محرك الأستروكارتوغرافيا المتقدم - "
               "جميع الحقوق محفوظة للفلكي استرو رادار.</div></body></html>")
    return "".join(out)

# ==========================================
# 7. بناء التقرير الكامل
# ==========================================
def build_report(name: str, birth_date: datetime.date, birth_time: datetime.time,
                 place_label: str, tz_str: str, jd: float, birth_code: str,
                 target_code: Optional[str]) -> Dict[str, Any]:
    positions, gmst = compute_planet_positions(jd)
    scope = load_scope_cities()
    cities = [c for c in scope if target_code is None or c["country_code"] == target_code]
    city_lines = scan_cities(cities, positions, gmst)

    scope_codes = sorted({c["country_code"] for c in cities})
    country_entries = build_country_entries(cities, city_lines, scope_codes)
    city_entries = build_city_entries(cities, city_lines)
    top_cities = top_cities_by_country(city_entries)

    ordered = {
        "arab_me": order_entries(country_entries, ARAB_ME_CODES, birth_code),
        "other_me": order_entries(country_entries, OTHER_ME_CODES, birth_code),
        "europe": order_entries(country_entries, EUROPE_CODES, birth_code),
    }

    report = {
        "name": name,
        "birth_date": str(birth_date),
        "birth_time": birth_time.strftime("%H:%M"),
        "place_label": place_label,
        "tz": tz_str,
        "birth_code": birth_code,
        "target_code": target_code,
        "country_entries": country_entries,
        "city_entries": rank_cities(city_entries) if target_code else [],
        "top_cities": top_cities,
        "ordered": ordered,
        "positions": dict(positions),
        "scanned_cities": len(cities),
    }
    report["html"] = build_html_report(report)
    return report

# ==========================================
# 8. عرض النتائج
# ==========================================
def render_region_mode(r: Dict[str, Any]) -> None:
    birth_code = r["birth_code"]
    arab = r["ordered"]["arab_me"]
    if arab:
        ranked = sorted(arab, key=lambda e: e["rank"])
        st.info(f"🏆 أفضل دولة عربية فلكياً لك: **{ranked[0]['name_ar']}** — "
                f"🚧 أكثرها اختباراً: **{ranked[-1]['name_ar']}**")

    for reg in ("arab_me", "other_me", "europe"):
        lst = r["ordered"][reg]
        if not lst:
            continue
        st.markdown(f"## {REGION_TITLES[reg]}")
        if reg == "arab_me" and birth_code in ARAB_ME_CODES:
            st.caption("🏠 دولة الميلاد تُعرض أولاً ثم بقية الدول، والترتيب الرقمي حسب الميزان الفلكي.")
        show_df(countries_df(lst, birth_code))
        for e in lst:
            is_birth = e["code"] == birth_code
            label = f"{'🏠 ' if is_birth else ''}{e['rank']}. {e['name_ar']} — {e['tier']}"
            with st.expander(label, expanded=is_birth):
                tc = r["top_cities"].get(e["code"], {"best": [], "worst": []})
                render_entry_markdown(e, tc["best"], tc["worst"])


def render_country_mode(r: Dict[str, Any]) -> None:
    code = r["target_code"]
    st.markdown(f"### 📍 تحليل جميع مدن دولة: **{country_ar(code)}**")
    e = r["country_entries"].get(code)
    if e:
        with st.expander(f"ملخص الدولة — {e['tier']}", expanded=True):
            tc = r["top_cities"].get(code, {"best": [], "worst": []})
            render_entry_markdown(e, tc["best"], tc["worst"])

    cities = r["city_entries"]
    if not cities:
        st.warning(f"⚠️ لا توجد مدن مرصودة (سكانها ≥ {MIN_POPULATION:,}) في {country_ar(code)}.")
        return

    st.caption(f"تُكتب الصورة الطاقية لكل مدينة ({len(cities)} مدينة) حتى لو كانت الخطوط بعيدة؛ "
               f"المباشر ≤ {CITY_ORB:g}°، المتوسط ≤ {COUNTRY_ORB:g}°، الخافت ≤ {FAR_LIMIT:g}°، وإلا يُؤخذ أقرب "
               f"{MIN_LINES} خطوط.")
    show_df(cities_df(cities))

    best = [c for c in cities if c["net"] > 0]
    worst = [c for c in cities if c["net"] < 0][::-1]

    st.markdown("---")
    st.markdown("### 💎 الخلاصة: أفضل وأسوأ مدينة")
    cb, cw = st.columns(2)
    with cb:
        if best:
            t = entry_texts(best[0])
            st.success(
                f"**🌟 أفضل مدينة: {best[0]['city']}**\n\n"
                f"🔮 {t['summary']}\n\n"
                + "".join(f"- 💡 {x}\n" for x in t["advice"])
                + "".join(f"- 🚨 {x}\n" for x in t["warnings"])
            )
        else:
            st.info("لا توجد مدينة ذات ميزان إيجابي.")
    with cw:
        if worst:
            t = entry_texts(worst[0])
            st.error(
                f"**⚠️ أسوأ مدينة: {worst[0]['city']}**\n\n"
                f"🔮 {t['summary']}\n\n"
                + "".join(f"- 💡 {x}\n" for x in t["advice"])
                + "".join(f"- 🚨 {x}\n" for x in t["warnings"])
            )
        else:
            st.success("لا توجد مدينة ذات ميزان سلبي.")

    st.markdown("### 🔎 تفاصيل أي مدينة (نصائح وتحذيرات كاملة)")
    idx = st.selectbox(
        "اختر المدينة",
        options=list(range(len(cities))),
        format_func=lambda i: f"{cities[i]['rank']}. {cities[i]['city']} — {cities[i]['tier']}",
        key="city_detail_select",
    )
    render_entry_markdown(cities[idx])


def render_report(r: Dict[str, Any]) -> None:
    st.success("✨ تم إنجاز التحليل الفلكي المعمق بنجاح!")
    st.markdown(f"## 🌍 تقرير الأستروكارتوغرافيا الشامل لـ: {r['name']}")
    st.markdown(
        f"**أوربت الدول:** {COUNTRY_ORB:g}° | **أوربت المدن:** {CITY_ORB:g}° | "
        f"**عدد المدن المفحوصة:** {r['scanned_cities']}"
    )

    if r["target_code"]:
        render_country_mode(r)
    else:
        render_region_mode(r)

    st.markdown("---")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### 💡 نصائح عامة")
        st.markdown("\n".join(f"- {x}" for x in GENERAL_TIPS))
    with col_b:
        st.markdown("#### 🚨 تحذيرات عامة")
        st.markdown("\n".join(f"- {x}" for x in GENERAL_WARNINGS))

    with st.expander("📐 المعطيات الفلكية المحسوبة (المطالع المستقيمة والميل)"):
        rows = [{"الكوكب": p, "RA (°)": round(ra, 3), "Dec (°)": round(dec, 3)}
                for p, (ra, dec) in r["positions"].items()]
        show_df(pd.DataFrame(rows))

    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in r["name"]) or "report"
    scope_tag = r["target_code"] or "ME_Europe"
    st.download_button(
        "📥 تنزيل تقرير HTML الشامل (جاهز للطباعة والـ PDF)",
        data=r["html"].encode("utf-8"),
        file_name=f"AstroCartography_{scope_tag}_{safe}.html",
        mime="text/html",
    )

# ==========================================
# 9. واجهة المستخدم
# ==========================================
st.title("🌟 النظام المتقدم الشامل للأستروكارتوغرافيا المجالية")
st.markdown("### الشرق الأوسط (الدول العربية أولاً) + أوروبا — برمجة الفلكي استرو رادار")
st.markdown("---")

MODE_REGION = f"مسح إقليمي: الدول العربية + الشرق الأوسط + أوروبا (أوربت {COUNTRY_ORB:g}°)"
MODE_COUNTRY = f"تحليل كل مدن دولة محددة (أوربت {CITY_ORB:g}° + الأثر الخافت للخطوط البعيدة)"

with st.sidebar:
    st.header("👤 بيانات المستفيد")
    name = st.text_input("اسم المستفيد", "ميار")

    current_year = datetime.date.today().year
    birth_date = st.date_input(
        "تاريخ الميلاد",
        value=datetime.date(1981, 4, 17),
        min_value=datetime.date(1900, 1, 1),
        max_value=datetime.date(current_year, 12, 31),
    )
    birth_time = st.time_input(
        "ساعة الميلاد (التوقيت المحلي)",
        datetime.time(11, 30),
        step=datetime.timedelta(minutes=1),
    )

    st.header("🌍 مكان الولادة الجغرافي")
    default_idx = sorted_country_names.index("Syria") if "Syria" in sorted_country_names else 0
    birth_country_name = st.selectbox("دولة الميلاد", sorted_country_names, index=default_idx)
    birth_c_code = country_name_to_code.get(birth_country_name, "SY")

    birth_cities = get_cities_by_country(birth_c_code)
    city_label_map = {
        c["id"]: f"{c['name']} — {c['admin1']} ({c['population']:,})" if c["admin1"]
        else f"{c['name']} ({c['population']:,})"
        for c in birth_cities
    }

    use_manual = st.checkbox(
        "إدخال إحداثيات مكان الميلاد يدوياً",
        value=not birth_cities,
        disabled=not birth_cities,
    )
    if use_manual or not birth_cities:
        b_lat = st.number_input("خط العرض", min_value=-90.0, max_value=90.0, value=33.5138, format="%.4f")
        b_lon = st.number_input("خط الطول", min_value=-180.0, max_value=180.0, value=36.2765, format="%.4f")
        place_label = f"{birth_country_name} ({b_lat:.3f}, {b_lon:.3f})"
        city_tz = ""
    else:
        sel_id = st.selectbox(
            "مدينة الميلاد",
            options=[c["id"] for c in birth_cities],
            format_func=lambda i: city_label_map[i],
        )
        b_city = next(c for c in birth_cities if c["id"] == sel_id)
        b_lat, b_lon = b_city["lat"], b_city["lon"]
        place_label = f"{b_city['name']}، {birth_country_name}"
        city_tz = b_city.get("timezone", "")

    tz_auto = tf.timezone_at(lng=b_lon, lat=b_lat) or city_tz or "UTC"
    tz_options = list(pytz.common_timezones)
    if tz_auto not in tz_options:
        tz_options.insert(0, tz_auto)
    with st.expander("🕒 المنطقة الزمنية (تُكتشف تلقائياً)"):
        tz_str = st.selectbox(
            "المنطقة الزمنية",
            tz_options,
            index=tz_options.index(tz_auto),
            key=f"tz_{round(b_lat, 3)}_{round(b_lon, 3)}",
        )

    st.markdown("---")
    st.header("🔍 نطاق ونوع البحث")
    search_mode = st.radio("خيارات البحث الجغرافي", [MODE_REGION, MODE_COUNTRY])

    selected_code: Optional[str] = None
    if search_mode == MODE_COUNTRY:
        region_codes = ARAB_ME_CODES + OTHER_ME_CODES + EUROPE_CODES
        idx0 = region_codes.index(birth_c_code) if birth_c_code in region_codes else 0
        selected_code = st.selectbox(
            "اختر الدولة المستهدفة للتحليل",
            region_codes,
            index=idx0,
            format_func=lambda c: f"{country_ar(c)} ({c})",
        )

    st.markdown("---")
    if search_mode == MODE_COUNTRY:
        st.info(f"ℹ️ الأوربت المباشر للمدن: **{CITY_ORB:g}°**. وتُكتب لكل مدينة صورتها الطاقية "
                f"حتى لو كانت الخطوط بعيدة (أثر خافت حتى {FAR_LIMIT:g}° وأقرب {MIN_LINES} خطوط دائماً).")
    else:
        st.info(f"ℹ️ الأوربت المعتمد للدول: **{COUNTRY_ORB:g}°** مع كتابة الأثر الخافت لأقرب الخطوط، "
                f"فتشمل النتائج كل الدول العربية في الشرق الأوسط.")

    analyze_btn = st.button("🚀 بدء التحليل الفلكي الجغرافي", type="primary")

if analyze_btn:
    with st.spinner("جاري إجراء الحسابات الفلكية المكثفة وتحليل الأثر الكوكبي ومجالات الحياة..."):
        jd_value = get_utc_julian_day(birth_date, birth_time, tz_str)
        st.session_state["report"] = build_report(
            name=name,
            birth_date=birth_date,
            birth_time=birth_time,
            place_label=place_label,
            tz_str=tz_str,
            jd=jd_value,
            birth_code=birth_c_code,
            target_code=selected_code if search_mode == MODE_COUNTRY else None,
        )

if "report" in st.session_state:
    render_report(st.session_state["report"])
else:
    st.info("أدخل بيانات الميلاد من القائمة الجانبية ثم اضغط «بدء التحليل الفلكي الجغرافي».")
