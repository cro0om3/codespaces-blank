import base64
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

# =========================
# BASIC CONFIG
# =========================

st.set_page_config(
    page_title="SNOW LIWA",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =========================
# SETTINGS
# =========================

BASE_DIR = Path(__file__).resolve().parent
BACKGROUND_IMAGE_PATH = BASE_DIR / "assets" / "snow_liwa_bg.jpg"
HERO_IMAGE_PATH = BACKGROUND_IMAGE_PATH
DATA_DIR = BASE_DIR / "data"
BOOKINGS_FILE = DATA_DIR / "bookings.xlsx"

TICKET_PRICE = 175  # AED per ticket

# Ziina API config
ZIINA_API_BASE = "https://api-v2.ziina.com/api"

# Read Ziina config (bypass secrets for now)
ZIINA_ACCESS_TOKEN = "FAKE_ACCESS_TOKEN"
APP_BASE_URL = "https://snow-liwa.streamlit.app"
ZIINA_TEST_MODE = True

PAGES = {
    "Welcome": "welcome",
    "Who we are": "who",
    "Experience": "experience",
    "Contact": "contact",
    "Dashboard (Admin)": "dashboard",
}

ADMIN_PASSWORD = "snowadmin123"  # Legacy; login removed

# =========================
# DATA HELPERS
# =========================


def ensure_data_file():
    DATA_DIR.mkdir(exist_ok=True)
    if not BOOKINGS_FILE.is_file():
        df = pd.DataFrame(
            columns=[
                "booking_id",
                "created_at",
                "name",
                "phone",
                "tickets",
                "ticket_price",
                "total_amount",
                "status",  # pending / paid / cancelled
                "payment_intent_id",  # from Ziina
                "payment_status",  # requires_payment_instrument / completed / failed...
                "redirect_url",  # Ziina hosted page
                "notes",
            ]
        )
        df.to_excel(BOOKINGS_FILE, index=False)


def load_bookings():
    ensure_data_file()
    return pd.read_excel(BOOKINGS_FILE)


def save_bookings(df: pd.DataFrame):
    df.to_excel(BOOKINGS_FILE, index=False)


def get_next_booking_id(df: pd.DataFrame) -> str:
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"SL-{today}-"
    todays = df[df["booking_id"].astype(str).str.startswith(prefix)]
    if todays.empty:
        seq = 1
    else:
        last = todays["booking_id"].iloc[-1]
        try:
            seq = int(str(last).split("-")[-1]) + 1
        except Exception:
            seq = len(todays) + 1
    return prefix + f"{seq:03d}"


# =========================
# ZIINA API HELPERS
# =========================


def has_ziina_configured() -> bool:
    return bool(ZIINA_ACCESS_TOKEN) and ZIINA_ACCESS_TOKEN != "PUT_YOUR_ZIINA_ACCESS_TOKEN_IN_SECRETS"


def create_payment_intent(amount_aed: float, booking_id: str, customer_name: str) -> dict | None:
    """Create Payment Intent via Ziina API and return JSON."""
    if not has_ziina_configured():
        st.error("Ziina API token not configured. Add it to .streamlit/secrets.toml under [ziina].")
        return None

    amount_fils = int(round(amount_aed * 100))  # Ziina expects amount in fils (cents equivalent)

    url = f"{ZIINA_API_BASE}/payment_intent"
    headers = {
        "Authorization": f"Bearer {ZIINA_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    # From Ziina docs: using {PAYMENT_INTENT_ID} in URLs
    base_return = APP_BASE_URL.rstrip("/")
    success_url = f"{base_return}/?result=success&pi_id={{PAYMENT_INTENT_ID}}"
    cancel_url = f"{base_return}/?result=cancel&pi_id={{PAYMENT_INTENT_ID}}"
    failure_url = f"{base_return}/?result=failure&pi_id={{PAYMENT_INTENT_ID}}"

    payload = {
        "amount": amount_fils,
        "currency_code": "AED",
        "message": f"Snow Liwa booking {booking_id} - {customer_name}",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "failure_url": failure_url,
        "test": ZIINA_TEST_MODE,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
    except requests.RequestException as e:
        st.error(f"Error talking to Ziina API: {e}")
        return None

    if resp.status_code >= 400:
        st.error(f"Ziina API error ({resp.status_code}): {resp.text}")
        return None

    return resp.json()


def get_payment_intent(pi_id: str) -> dict | None:
    """Fetch payment intent from Ziina."""
    if not has_ziina_configured():
        st.error("Ziina API token not configured. Add it to .streamlit/secrets.toml under [ziina].")
        return None

    url = f"{ZIINA_API_BASE}/payment_intent/{pi_id}"
    headers = {"Authorization": f"Bearer {ZIINA_ACCESS_TOKEN}"}

    try:
        resp = requests.get(url, headers=headers, timeout=15)
    except requests.RequestException as e:
        st.error(f"Error talking to Ziina API: {e}")
        return None

    if resp.status_code >= 400:
        st.error(f"Ziina API error ({resp.status_code}): {resp.text}")
        return None

    return resp.json()


def sync_payments_from_ziina(df: pd.DataFrame) -> pd.DataFrame:
    """Loop pending bookings and update payment status from Ziina."""
    if not has_ziina_configured():
        st.error("Ziina API not configured.")
        return df

    updated = False
    for idx, row in df.iterrows():
        pi_id = str(row.get("payment_intent_id") or "").strip()
        if not pi_id:
            continue

        pi = get_payment_intent(pi_id)
        if not pi:
            continue

        status = pi.get("status")
        if not status:
            continue

        df.at[idx, "payment_status"] = status

        if status == "completed":
            df.at[idx, "status"] = "paid"
            updated = True
        elif status in ("failed", "canceled"):
            df.at[idx, "status"] = "cancelled"
            updated = True

    if updated:
        save_bookings(df)
    return df


# =========================
# UI HELPERS
# =========================


def encode_image_base64(image_path: Path) -> str | None:
    if not image_path.is_file():
        return None
    try:
        return base64.b64encode(image_path.read_bytes()).decode()
    except Exception:
        return None


def set_background(image_path: Path):
    css = """
    <style>
    .stApp {
        background: linear-gradient(180deg, #f4f8ff 0%, #ffffff 48%, #eaf2fd 100%);
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def inject_base_css():
    st.markdown(
        """ <style>
        .page-container {
        max-width: 1180px;
        margin: 0 auto;
        padding: 0.8rem 0.75rem 1.6rem;
        }
        .page-card {
        max-width: 1180px;
        width: 100%;
        background: transparent;
        box-shadow: none;
        padding: 0;
        }

        @media (max-width: 800px) {
            .page-card {
                padding: 0;
            }
        }

        .hero-card {
            position: relative;
            border-radius: 30px;
            overflow: hidden;
            min-height: 480px;
            background-size: cover;
            background-position: center;
            box-shadow: 0 18px 48px rgba(14, 59, 110, 0.26);
            isolation: isolate;
        }
        .sticker {
            position: absolute;
            z-index: 3;
            font-size: 2.8rem;
            opacity: 0.9;
            filter: drop-shadow(0 6px 12px rgba(0,0,0,0.18));
            pointer-events: none;
        }
        .sticker.kid { top: 62%; left: 12%; font-size: 3.1rem; }
        .sticker.snowman { top: 24%; right: 14%; }
        .sticker.deer { bottom: 12%; right: 30%; }
        .sticker.mitten { top: 12%; left: 8%; }
        .hero-layer {
            position: absolute;
            inset: 0;
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.0) 0%, rgba(220, 235, 255, 0.45) 100%);
            z-index: 1;
        }
        .hero-content {
            position: relative;
            z-index: 2;
            width: 100%;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            gap: 1.5rem;
            padding: 2.8rem 2rem;
            color: #0d2a4f;
            text-align: center;
        }
        .hero-nav {
            display: flex;
            gap: 1.8rem;
            letter-spacing: 0.18em;
            font-size: 0.9rem;
            text-transform: uppercase;
            color: #0f2f54;
        }
        .hero-title {
            font-size: 3.6rem;
            line-height: 1.05;
            letter-spacing: 0.18em;
            font-weight: 800;
            color: #0d2a4f;
            text-shadow: 0 10px 24px rgba(0, 0, 0, 0.14);
        }
        .hero-tags {
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
            justify-content: center;
        }
        .hero-pill {
            background: rgba(255, 255, 255, 0.92);
            color: #123764;
            padding: 0.6rem 1.4rem;
            border-radius: 999px;
            font-weight: 700;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.16);
            letter-spacing: 0.08em;
        }

        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1rem;
            margin: 1.1rem 0 1.0rem 0;
        }
        .info-card {
            background: #fdfdff;
            border: 1px solid #e1e8f4;
            border-radius: 18px;
            padding: 1.1rem 1.25rem;
            box-shadow: 0 12px 30px rgba(10, 48, 96, 0.08);
        }
        .info-card h3 {
            margin: 0 0 0.4rem 0;
            font-size: 1.1rem;
            letter-spacing: 0.08em;
            color: #1f3551;
        }
        .info-card p {
            margin: 0;
            color: #4f6077;
            line-height: 1.5;
        }

        .section-card {
            background: #ffffff;
            border: 1px solid #e3ecf8;
            border-radius: 18px;
            padding: 1.4rem 1.4rem 1.2rem 1.4rem;
            box-shadow: 0 14px 34px rgba(8, 46, 102, 0.1);
            margin-top: 1rem;
        }

        .snow-title {
            text-align: center;
            font-size: 3rem;
            font-weight: 700;
            letter-spacing: 0.30em;
            margin-bottom: 0.4rem;
        }
        .subheading {
            text-align: center;
            font-size: 0.95rem;
            opacity: 0.8;
            margin-bottom: 2rem;
        }
        .arabic {
            direction: rtl;
            text-align: right;
            font-size: 1rem;
            line-height: 1.8;
        }
        .english {
            direction: ltr;
            text-align: left;
            font-size: 0.98rem;
            line-height: 1.7;
        }

        .dual-column {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2.25rem;
        }

        @media (max-width: 800px) {
            .dual-column {
                grid-template-columns: 1fr;
            }
            .hero-card {
                min-height: 360px;
            }
            .hero-title {
                font-size: 2.6rem;
            }
            .hero-nav {
                gap: 0.7rem;
                font-size: 0.78rem;
            }
            .hero-content {
                padding: 2rem 1.2rem;
                gap: 1rem;
            }
        }

        .ticket-price {
            font-size: 1.2rem;
            font-weight: 700;
            margin-top: 1rem;
        }

        .stButton>button {
            border-radius: 999px;
            padding: 0.7rem 1.6rem;
            font-weight: 600;
            letter-spacing: 0.08em;
        }

        .center-btn {
            display: flex;
            justify-content: center;
            margin-top: 0.5rem;
            margin-bottom: 0.5rem;
        }

        .footer-note {
            text-align: center;
            font-size: 0.8rem;
            opacity: 0.75;
            margin-top: 1.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_state():
    if "page" not in st.session_state:
        st.session_state.page = "welcome"


def page_nav():
    pass


def get_query_params() -> dict:
    """Handle query params in both new and old Streamlit."""
    try:
        qp = st.query_params
        if hasattr(qp, "to_dict"):
            return qp.to_dict()
        return dict(qp)
    except Exception:
        try:
            return st.experimental_get_query_params()
        except Exception:
            return {}


def _normalize_query_value(value):
    if isinstance(value, list):
        return value[0] if value else None
    return value


# =========================
# PAGE CONTENT
# =========================


def render_welcome():
    hero_image = HERO_IMAGE_PATH if HERO_IMAGE_PATH.is_file() else BACKGROUND_IMAGE_PATH
    hero_style = (
        f"background-image: url('{hero_image.as_posix()}');"
        if hero_image.is_file()
        else "background: linear-gradient(180deg, #dfeffd 0%, #c8d9f0 100%);"
    )

    st.markdown(
        f"""
        <div class="hero-card" style="{hero_style}">
            <div class="hero-layer"></div>
            <div class="sticker kid">🧒🏻</div>
            <div class="sticker snowman">⛄️</div>
            <div class="sticker deer">🦌</div>
            <div class="sticker mitten">🧤</div>
            <div class="hero-content">
                <div class="hero-nav">
                    <span>NAME</span>
                    <span>ABOUT</span>
                    <span>ACTIVITIES</span>
                    <span>INVYS</span>
                    <span>CONTACT</span>
                </div>
                <div class="hero-title">SNOW<br>LIWA</div>
                <div class="hero-tags">
                    <span class="hero-pill">ICE SKATING</span>
                    <span class="hero-pill">SLADDING</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="info-grid">
            <div class="info-card">
                <h3>ACTIVITIES</h3>
                <p>Snow play, warm drinks, chocolate fountain, and winter vibes for friends & family.</p>
            </div>
            <div class="info-card">
                <h3>EVENTS</h3>
                <p>Group bookings, private sessions, and curated winter moments at our secret Liwa spot.</p>
            </div>
            <div class="info-card">
                <h3>CONTACT</h3>
                <p>Reach us on WhatsApp or Instagram <strong>snowliwa</strong>. We’ll share the exact location after booking.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("### 🎟️ Book your ticket")
    st.write(f"Entrance ticket: **{TICKET_PRICE} AED** per person.")

    with st.form("booking_form"):
        name = st.text_input("Name / الاسم الكامل")
        phone = st.text_input("Phone / رقم الهاتف (واتساب)")
        tickets = st.number_input("Number of tickets / عدد التذاكر", 1, 20, 1)
        notes = st.text_area("Notes (optional) / ملاحظات اختيارية", height=70)
        submitted = st.form_submit_button("Proceed to payment with Ziina")

    st.markdown("</div>", unsafe_allow_html=True)

    if submitted:
        if not name or not phone:
            st.error("❗ الرجاء إدخال الاسم ورقم الهاتف.")
            return

        df = load_bookings()
        booking_id = get_next_booking_id(df)
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total_amount = tickets * TICKET_PRICE

        # 1) Create Payment Intent
        pi_json = create_payment_intent(total_amount, booking_id, name)

        if pi_json:
            payment_intent_id = pi_json.get("id", "")
            redirect_url = pi_json.get("redirect_url", "")
            payment_status = pi_json.get("status", "requires_payment_instrument")
        else:
            payment_intent_id = ""
            redirect_url = ""
            payment_status = "error"

        # 2) Save booking
        new_row = {
            "booking_id": booking_id,
            "created_at": created_at,
            "name": name,
            "phone": phone,
            "tickets": int(tickets),
            "ticket_price": TICKET_PRICE,
            "total_amount": float(total_amount),
            "status": "pending",
            "payment_intent_id": payment_intent_id,
            "payment_status": payment_status,
            "redirect_url": redirect_url,
            "notes": notes,
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        save_bookings(df)

        st.success(
            f"✅ Booking created!\n\n"
            f"**Booking ID:** {booking_id}\n\n"
            f"Total amount: **{total_amount} AED** for {tickets} ticket(s)."
        )

        if redirect_url:
            st.info(
                "1️⃣ اضغط على زر الدفع بالأسفل لفتح صفحة Ziina.\n"
                "2️⃣ أكمل الدفع.\n"
                "3️⃣ بعد الدفع، سيتم إعادتك تلقائيًا لصفحة النتيجة في SNOW LIWA.\n"
                "4️⃣ بعدها تواصل معنا على الواتساب مع رقم الحجز لاستلام التذكرة ولوكيشن الموقع السري 🫣"
            )
            st.markdown('<div class="center-btn">', unsafe_allow_html=True)
            st.link_button("Pay with Ziina", redirect_url, use_container_width=False)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.error(
                "لم نتمكن من إنشاء رابط الدفع من Ziina. الحجز مسجل، "
                "الرجاء التواصل معنا لإتمام عملية الدفع يدويًا."
            )

        st.markdown(
            '<div class="footer-note">*يمكن لاحقًا تطوير التدفق أكثر باستخدام Webhooks أو صفحات مخصصة*</div>',
            unsafe_allow_html=True,
        )


def render_who_we_are():
    st.markdown('<div class="snow-title">SNOW LIWA</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subheading">من نحن ؟ · Who are we</div>',
        unsafe_allow_html=True,
    )

    ar_text = """
مشروع شبابي إماراتي من قلب منطقة الظفرة ، 

يقدم تجربة شتوية فريدة تجمع بين أجواء ليوا الساحرة ولمسات من البساطة والجمال . 

يهدف المشروع إلى خلق مساحة ترفيهية ودية للعائلات والشباب تجمع بين الديكور الشتوي الفخم والضيافة الراقية من مشروب الشوكولاتة الساخنة الي نافورة الشوكولاتة والفراولة الطازجة نحن نعمل على تطوير باستمرار بدعم من الجهات المحلية وروح الشباب الإماراتي الطموح .
"""

    en_title = "? Who are we"
    en_text = """
Emirati youth project from the heart of Al Dhafra region,

It offers a unique winter experience that combines the charming atmosphere of Liwa
with touches of simplicity and beauty.

The project aims to create a friendly entertainment space for families and young people
that combines luxurious winter decoration and high-end hospitality from hot chocolate
drink to the fresh chocolate and strawberry fountain. We are constantly developing
with the support of local authorities and the spirit of ambitious Emirati youth.
"""

    st.markdown('<div class="dual-column">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="arabic"><strong>من نحن ؟</strong><br><br>{ar_text}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="english"><strong>{en_title}</strong><br><br>{en_text}</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


def render_experience():
    st.markdown('<div class="snow-title">SNOW LIWA</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subheading">Snow Experience · تجربة الثلج</div>',
        unsafe_allow_html=True,
    )

    ar_block_1 = """
تجربة الثلج ❄️ 

في مبادرةٍ فريدةٍ تمنح الزوّار أجواءً ثلجية ممتعة وتجربةً استثنائية لا تُنسى، يمكنكم الاستمتاع بمشاهدة تساقط الثلج، وتجربة مشروب الشوكولاتة الساخنة، مع ضيافةٍ راقية تشمل الفراولة ونافورة الشوكولاتة.

تذكرة الدخول فقط بـ 175 درهمًا 
"""

    en_block_1 = """
In a unique initiative that gives visitors a pleasant snowy
atmosphere and an exceptional and unforgettable experience,
you can enjoy watching the snowfall, and try a hot chocolate
drink, with high-end hospitality including strawberries and a
chocolate fountain.

The entrance ticket is only AED 175
"""

    ar_block_2 = """
SNOW Liwa

بعد الدفع عن طريق تصوير الباركود تواصلو معانا واستلمو تذكرتكم ولوكيشن موقعنا السري 🫣
"""

    en_block_2 = """
SNOW Liwa

After paying by photographing the barcode, contact us and receive
your ticket and the location of our secret website 🫣
"""

    st.markdown('<div class="dual-column">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="arabic">{ar_block_1}<br><br>{ar_block_2}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="english">{en_block_1}<br><br>{en_block_2}</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        f'<div class="ticket-price">🎟️ Entrance Ticket: <strong>{TICKET_PRICE} AED</strong> per person</div>',
        unsafe_allow_html=True,
    )


def render_contact():
    st.markdown('<div class="snow-title">SNOW LIWA</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subheading">Contact · تواصل معنا</div>',
        unsafe_allow_html=True,
    )

    st.markdown("### 📞 Contact Us / تواصل معنا")

    ar_contact = """
**رقم الهاتف**

050 113 8781

للتواصل عبر الواتساب فقط أو من خلال حسابنا في الإنستغرام:
**snowliwa**
"""

    en_contact = """
**Phone**

050 113 8781

To contact WhatsApp only or on our Instagram account:

**snowliwa**
"""

    st.markdown('<div class="dual-column">', unsafe_allow_html=True)
    st.markdown(f'<div class="arabic">{ar_contact}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="english">{en_contact}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.write("You can later add direct WhatsApp links or Instagram buttons here.")


def render_dashboard():
    st.markdown('<div class="snow-title">SNOW LIWA</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subheading">Dashboard · لوحة التحكم</div>',
        unsafe_allow_html=True,
    )

    df = load_bookings()
    if df.empty:
        st.info("No bookings yet.")
        return

    # Sync from Ziina
    if st.button("🔄 Sync payment status from Ziina"):
        with st.spinner("Syncing with Ziina..."):
            df = sync_payments_from_ziina(df)
        st.success("Sync completed.")

    # KPIs
    total_bookings = len(df)
    total_tickets = df["tickets"].sum()
    total_amount = df["total_amount"].sum()
    total_paid = df[df["status"] == "paid"]["total_amount"].sum()
    total_pending = df[df["status"] == "pending"]["total_amount"].sum()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total bookings", int(total_bookings))
    c2.metric("Total tickets", int(total_tickets))
    c3.metric("Total amount (AED)", f"{total_amount:,.0f}")
    c4.metric("Paid (AED)", f"{total_paid:,.0f}")
    c5.metric("Pending (AED)", f"{total_pending:,.0f}")

    st.markdown("### Update booking status manually")
    booking_ids = df["booking_id"].tolist()
    selected_id = st.selectbox("Select booking", booking_ids)
    new_status = st.selectbox("New status", ["pending", "paid", "cancelled"])
    if st.button("Save status"):
        df.loc[df["booking_id"] == selected_id, "status"] = new_status
        save_bookings(df)
        st.success(f"Updated {selected_id} to status: {new_status}")

    st.markdown("### Last 25 bookings")
    st.dataframe(
        df.sort_values("created_at", ascending=False).head(25),
        use_container_width=True,
    )


def render_payment_result(result: str, pi_id: str):
    """Page shown when user returns from Ziina with pi_id in URL."""
    st.markdown('<div class="snow-title">SNOW LIWA</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subheading">Payment result · نتيجة الدفع</div>',
        unsafe_allow_html=True,
    )

    st.write(f"**Payment Intent ID:** `{pi_id}`")

    df = load_bookings()
    row = df[df["payment_intent_id"].astype(str) == str(pi_id)]
    booking_id = row["booking_id"].iloc[0] if not row.empty else None
    if booking_id:
        st.write(f"**Booking ID:** `{booking_id}`")

    pi_status = None
    if pi_id:
        pi = get_payment_intent(pi_id)
        if pi:
            pi_status = pi.get("status")
            if not row.empty:
                idx = row.index[0]
                df.at[idx, "payment_status"] = pi_status
                if pi_status == "completed":
                    df.at[idx, "status"] = "paid"
                elif pi_status in ("failed", "canceled"):
                    df.at[idx, "status"] = "cancelled"
                save_bookings(df)

    final_status = pi_status or result

    if final_status == "completed":
        st.success(
            "✅ تم الدفع بنجاح!\n\n"
            "شكرًا لاختياركم **SNOW LIWA** ❄️\n\n"
            "تواصلوا معنا عبر الواتساب مع رقم الحجز لاستلام التذكرة ولوكيشن الموقع."
        )
    elif final_status in ("pending", "requires_payment_instrument", "requires_user_action"):
        st.info(
            "ℹ️ عملية الدفع قيد المعالجة أو لم تكتمل بعد.\n\n"
            "لو تأكدت أن المبلغ تم خصمه، أرسل لنا رقم الحجز لنراجع الحالة."
        )
    elif final_status in ("failed", "canceled"):
        st.error(
            "❌ لم تتم عملية الدفع أو تم إلغاؤها.\n\n"
            "يمكنك إعادة المحاولة من صفحة الحجز أو التواصل معنا للمساعدة."
        )
    else:
        st.warning(
            "تعذر التأكد من حالة الدفع.\n\n"
            "يرجى التواصل معنا على الواتساب مع رقم الحجز للتحقق من العملية."
        )

    st.markdown("---")
    st.markdown(
        "📱 للتواصل: واتساب أو إنستغرام **snowliwa** مع ذكر رقم الحجز.",
    )

    st.markdown('<div class="center-btn">', unsafe_allow_html=True)
    st.link_button("Back to SNOW LIWA home", APP_BASE_URL, use_container_width=False)
    st.markdown("</div>", unsafe_allow_html=True)


# =========================
# MAIN APP
# =========================


def main():
    init_state()
    ensure_data_file()
    set_background(BACKGROUND_IMAGE_PATH)
    inject_base_css()

    query = get_query_params()
    result_param = _normalize_query_value(query.get("result")) if query else None
    pi_id_param = _normalize_query_value(query.get("pi_id")) if query else None

    # If coming back from Ziina with pi_id -> show payment result
    if result_param and pi_id_param:
        st.markdown(
            '<div class="page-container"><div class="page-card">',
            unsafe_allow_html=True,
        )
        render_payment_result(result_param, pi_id_param)
        st.markdown("</div></div>", unsafe_allow_html=True)
        return

    # Normal navigation
    st.markdown(
        '<div class="page-container"><div class="page-card">',
        unsafe_allow_html=True,
    )

    render_welcome()
    st.markdown("<hr>", unsafe_allow_html=True)
    render_who_we_are()
    st.markdown("<hr>", unsafe_allow_html=True)
    render_experience()
    st.markdown("<hr>", unsafe_allow_html=True)
    render_contact()
    st.markdown("<hr>", unsafe_allow_html=True)
    # Dashboard is now a separate page (dashboard.py)

    st.markdown("</div></div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
