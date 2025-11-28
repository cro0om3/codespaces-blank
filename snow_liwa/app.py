import base64
import io
import json
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import pandas as pd
import requests
import streamlit as st

try:
    import qrcode  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    qrcode = None

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
ASSETS_DIR = BASE_DIR / "assets"
UI_CONFIG_FILE = DATA_DIR / "ui_config.json"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a"}
PROTECTED_ASSETS = {"snow_liwa_bg.jpg", "snow_liwa_bg.png"}

TICKET_PRICE = 175  # AED per ticket

# Ziina API config
ZIINA_API_BASE = "https://api-v2.ziina.com/api"

# Read Ziina config (bypass secrets for now)
ZIINA_ACCESS_TOKEN = "FAKE_ACCESS_TOKEN"
APP_BASE_URL = "https://snow-liwa.streamlit.app"
ZIINA_TEST_MODE = True

DEFAULT_UI_CONFIG: dict[str, Any] = {
    "background": {
        "page_style": "gradient",  # solid | gradient | image
        "solid_color": "#f4f8ff",
        "gradient": {
            "start": "#f4f8ff",
            "end": "#ffffff",
            "angle": 180,
        },
        "image_name": "snow_liwa_bg.jpg",
        "overlay_opacity": 45,
        "is_fixed": True,
        "blur": 0,
        "brightness": 100,
        "contrast": 100,
    },
    "hero": {
        "background_type": "image",  # image | solid
        "image_name": "snow_liwa_bg.jpg",
        "solid_color": "#dfeffd",
        "height": "medium",  # small | medium | large
        "overlay_opacity": 55,
    },
    "sections": {
        "background_type": "inherit",  # inherit | image | solid
        "image_name": None,
        "solid_color": "#ffffff",
        "overlay_opacity": 18,
    },
    "theme": {
        "primary_color": "#0d2a4f",
        "secondary_color": "#89b4ff",
        "card_background": "#ffffff",
        "card_border": "#e3ecf8",
        "card_radius": "large",  # small | medium | large
        "shadow": "soft",  # none | soft | strong
        "mode": "light",  # light | dark
        "section_background": "#ffffff",
        "field_background": "#f7f9fd",
        "field_border": "#d2dbe8",
        "field_text": "#143A66",
    },
    "typography": {
        "heading_font": "'Bebas Neue', 'Inter Tight', sans-serif",
        "body_font": "'Inter', 'SF Pro Display', sans-serif",
        "arabic_font": "'Dubai', 'Cairo', sans-serif",
        "scale": "default",  # small | default | large
    },
    "language": {
        "direction": "ltr",
        "form_language": "bilingual",  # bilingual | english | arabic
    },
    "content": {
        "nav": {
            "name": "NAME",
            "about": "ABOUT",
            "activities": "ACTIVITIES",
            "invites": "INVITES",
            "contact": "CONTACT",
        },
        "cards": {
            "activities": {
                "title": "ACTIVITIES",
                "description": "Snow play, warm drinks, chocolate fountain, and winter vibes for friends & family.",
            },
            "events": {
                "title": "EVENTS",
                "description": "Group bookings, private sessions, and curated winter moments at our secret Liwa spot.",
            },
            "contact": {
                "title": "CONTACT",
                "description": "Reach us on WhatsApp or Instagram snowliwa. Exact location shared after booking.",
            },
        },
        "booking": {
            "title": "🎟️ Book your ticket",
            "price_text": "Entrance ticket: 175 AED per person.",
            "button_text": "Proceed to payment with Ziina",
        },
    },
    "icons": {
        "enabled": True,
        "size": "medium",  # small | medium | large
        "animation": "medium",  # none | slow | medium | fast
    },
    "form": {
        "show_notes": True,
        "label_position": "top",  # top | placeholder
        "button_width": "auto",  # auto | full
        "show_ticket_icon": True,
        "success_message": "✅ تم إنشاء الحجز! سنرسل لك التفاصيل بعد الدفع.",
    },
    "effects": {
        "snow": {
            "enabled": True,
            "flakes": 36,
            "size": "medium",  # small | medium | large
            "speed": "medium",  # slow | medium | fast
            "symbol": "sparkle",  # sparkle | flake | dot | emoji
        }
    },
    "branding": {
        "show_logo": False,
        "logo_image": None,
        "logo_width": 140,
        "tagline_en": "SNOW LIWA",
        "tagline_ar": "ثلج ليوا",
    },
    "social": {
        "whatsapp_number": "050 113 8781",
        "instagram_handle": "snowliwa",
        "instagram_url": "https://instagram.com/snowliwa",
        "whatsapp_message": "Hi SNOW LIWA!",
        "show_whatsapp_button": True,
        "show_whatsapp_qr": True,
    },
    "hero_cta": [
        {"label": "Book your slot", "url": "https://wa.me/971501138781", "style": "primary"},
        {"label": "View Instagram", "url": "https://instagram.com/snowliwa", "style": "secondary"},
    ],
    "audio": {
        "enabled": True,
        "file_name": "babanuail.mp3",
    },
    "seasonal_theme": "custom",
    "stickers": {
        "contact_collage": {
            "enabled": False,
            "image_name": None,
            "width": 340,
        },
        "hero": {
            "enabled": True,
            "images": [],
        },
        "sections": {
            "who": {"image": None, "position": "top-left", "width": 160, "opacity": 0.18},
            "experience": {"image": None, "position": "bottom-right", "width": 180, "opacity": 0.18},
            "contact": {"image": None, "position": "top-right", "width": 200, "opacity": 0.18},
        },
    },
    "security": {
        "admin_pin": "1234",
    },
}

THEME_PRESETS = {
    "custom": None,
    "snowday": {
        "background": {
            "page_style": "gradient",
            "gradient": {"start": "#f1f6ff", "end": "#ffffff", "angle": 180},
            "overlay_opacity": 35,
        },
        "theme": {
            "primary_color": "#143A66",
            "secondary_color": "#54A9FF",
            "card_background": "#ffffff",
            "card_border": "#dfe8f5",
            "section_background": "#ffffff",
        },
    },
    "arctic-night": {
        "background": {
            "page_style": "gradient",
            "gradient": {"start": "#0d1b2a", "end": "#1b263b", "angle": 180},
            "overlay_opacity": 20,
        },
        "theme": {
            "primary_color": "#c9f0ff",
            "secondary_color": "#4ea8de",
            "card_background": "rgba(13,27,42,0.85)",
            "card_border": "rgba(201,240,255,0.3)",
            "section_background": "rgba(27,38,59,0.9)",
            "field_background": "rgba(13,27,42,0.8)",
            "field_border": "rgba(78,168,222,0.6)",
            "field_text": "#e1f5ff",
        },
    },
    "festive": {
        "background": {
            "page_style": "gradient",
            "gradient": {"start": "#fff6f0", "end": "#ffe7e0", "angle": 180},
            "overlay_opacity": 30,
        },
        "theme": {
            "primary_color": "#b22335",
            "secondary_color": "#f5a623",
            "card_background": "#fffdf8",
            "card_border": "#ffd9cc",
            "section_background": "#fffaf2",
        },
    },
}


PAGES = {
    "Welcome": "welcome",
    "Who we are": "who",
    "Experience": "experience",
    "Contact": "contact",
    # Dashboard is a separate Streamlit page
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
                # requires_payment_instrument / completed / failed...
                "payment_status",
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


def _deep_merge(default: Any, override: Any) -> Any:
    if isinstance(default, dict):
        result = dict(default)
        if isinstance(override, dict):
            for key, value in override.items():
                result[key] = _deep_merge(default.get(key), value)
        elif override is not None:
            return override
        return result
    return override if override is not None else default


def ensure_ui_config():
    DATA_DIR.mkdir(exist_ok=True)
    if not UI_CONFIG_FILE.exists():
        UI_CONFIG_FILE.write_text(json.dumps(DEFAULT_UI_CONFIG, indent=2), encoding="utf-8")


def load_ui_config() -> dict[str, Any]:
    ensure_ui_config()
    try:
        raw = json.loads(UI_CONFIG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        raw = {}
    config = _deep_merge(DEFAULT_UI_CONFIG, raw)
    return config


def save_ui_config(config: dict[str, Any]):
    DATA_DIR.mkdir(exist_ok=True)
    UI_CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")


def set_config_value(config: dict[str, Any], keys: list[str], value: Any) -> bool:
    cursor = config
    for key in keys[:-1]:
        if key not in cursor or not isinstance(cursor[key], dict):
            cursor[key] = {}
        cursor = cursor[key]
    if cursor.get(keys[-1]) == value:
        return False
    cursor[keys[-1]] = value
    return True


def color_picker_value(value: Any, fallback: str) -> str:
    if isinstance(value, str) and value.startswith("#"):
        return value
    return fallback


def apply_theme_preset(config: dict[str, Any], preset_name: str) -> bool:
    preset = THEME_PRESETS.get(preset_name)
    if not preset:
        return False
    changed = False
    if "background" in preset:
        for key, value in preset["background"].items():
            changed |= set_config_value(config, ["background", key], value)
    if "theme" in preset:
        for key, value in preset["theme"].items():
            changed |= set_config_value(config, ["theme", key], value)
    return changed


def rerun_app():
    for attr in ("rerun", "experimental_rerun"):
        fn = getattr(st, attr, None)
        if callable(fn):
            try:
                fn()
            except Exception:
                pass
            break


def list_asset_images() -> list[str]:
    if not ASSETS_DIR.exists():
        return []
    return sorted(
        [p.name for p in ASSETS_DIR.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS]
    )


def resolve_asset_path(filename: str | None) -> Path | None:
    if not filename:
        return None
    candidate = ASSETS_DIR / filename
    return candidate if candidate.is_file() else None


def delete_asset_file(filename: str | None) -> bool:
    if not filename or filename in PROTECTED_ASSETS:
        return False
    candidate = ASSETS_DIR / filename
    if not candidate.is_file():
        return False
    try:
        candidate.unlink()
        return True
    except OSError:
        return False


def save_uploaded_asset(uploaded_file, prefix: str = "upload", allowed_exts: set[str] | None = None) -> str | None:
    if not uploaded_file:
        return None
    suffix = Path(uploaded_file.name).suffix.lower()
    allowed = allowed_exts or IMAGE_EXTENSIONS
    if suffix not in allowed:
        return None

    ASSETS_DIR.mkdir(exist_ok=True)
    safe_stem = re.sub(r"[^a-zA-Z0-9]+", "-", Path(uploaded_file.name).stem).strip("-") or "img"
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{prefix}-{safe_stem}-{timestamp}{suffix}"
    destination = ASSETS_DIR / filename
    destination.write_bytes(uploaded_file.getbuffer())
    return filename


def get_admin_pin(config: dict[str, Any]) -> str:
    secret_pin = None
    try:
        admin_section = st.secrets.get("admin")
        if isinstance(admin_section, dict):
            secret_pin = admin_section.get("pin") or admin_section.get("settings_pin")
    except Exception:
        pass

    if not secret_pin:
        try:
            secret_pin = st.secrets.get("admin_pin")
        except Exception:
            secret_pin = None

    if not secret_pin:
        secret_pin = (
            config.get("security", {}).get("admin_pin")
            if isinstance(config, dict)
            else None
        )

    return str(secret_pin or "1234")


# =========================
# ZIINA API HELPERS
# =========================


def has_ziina_configured() -> bool:
    return bool(ZIINA_ACCESS_TOKEN) and ZIINA_ACCESS_TOKEN != "PUT_YOUR_ZIINA_ACCESS_TOKEN_IN_SECRETS"


def create_payment_intent(amount_aed: float, booking_id: str, customer_name: str) -> dict | None:
    """Create Payment Intent via Ziina API and return JSON."""
    if not has_ziina_configured():
        st.error(
            "Ziina API token not configured. Add it to .streamlit/secrets.toml under [ziina].")
        return None

    # Ziina expects amount in fils (cents equivalent)
    amount_fils = int(round(amount_aed * 100))

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
        st.error(
            "Ziina API token not configured. Add it to .streamlit/secrets.toml under [ziina].")
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


def image_css_url(image_path: Path | None) -> str | None:
    if not image_path or not image_path.is_file():
        return None
    encoded = encode_image_base64(image_path)
    if not encoded:
        return None
    suffix = image_path.suffix.lower()
    if suffix in {".png"}:
        mime = "image/png"
    elif suffix in {".webp"}:
        mime = "image/webp"
    else:
        mime = "image/jpeg"
    return f"url('data:{mime};base64,{encoded}')"


def image_data_uri(image_path: Path | None) -> str | None:
    if not image_path or not image_path.is_file():
        return None
    encoded = encode_image_base64(image_path)
    if not encoded:
        return None
    suffix = image_path.suffix.lower()
    if suffix in {".png"}:
        mime = "image/png"
    elif suffix in {".webp"}:
        mime = "image/webp"
    else:
        mime = "image/jpeg"
    return f"data:{mime};base64,{encoded}"


def normalize_phone(number: str) -> str:
    digits = re.sub(r"\D", "", number or "")
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("0"):
        digits = "971" + digits[1:]
    if digits and not digits.startswith("971"):
        digits = "971" + digits
    return digits


QR_CACHE: dict[str, str] = {}


def build_whatsapp_link(number: str, message: str = "") -> str:
    normalized = normalize_phone(number)
    link = f"https://wa.me/{normalized}"
    if message:
        link += f"?text={quote_plus(message)}"
    return link


def generate_qr_data_uri(payload: str) -> str | None:
    if not payload or not qrcode:
        return None
    if payload in QR_CACHE:
        return QR_CACHE[payload]
    qr = qrcode.QRCode(version=1, box_size=5, border=2)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode()
    data_uri = f"data:image/png;base64,{encoded}"
    QR_CACHE[payload] = data_uri
    return data_uri


def apply_background(config: dict[str, Any]):
    bg_cfg = config.get("background", {})
    style = bg_cfg.get("page_style", "gradient")
    overlay_value = min(max(int(bg_cfg.get("overlay_opacity", 45)), 0), 100) / 100
    overlay_rgba = f"rgba(255, 255, 255, {overlay_value:.2f})"
    attachment = "fixed" if bg_cfg.get("is_fixed", True) else "scroll"
    background_layers = ""

    if style == "solid":
        base_color = bg_cfg.get("solid_color", "#f4f8ff")
        background_layers = f"linear-gradient(0deg, {overlay_rgba}, {overlay_rgba}), linear-gradient(0deg, {base_color}, {base_color})"
    elif style == "image":
        image_path = resolve_asset_path(bg_cfg.get("image_name")) or BACKGROUND_IMAGE_PATH
        img_uri = image_css_url(image_path)
        if img_uri:
            background_layers = f"linear-gradient(0deg, {overlay_rgba}, {overlay_rgba}), {img_uri}"
    if not background_layers:  # gradient default / fallback
        gradient_cfg = bg_cfg.get("gradient", {})
        start = gradient_cfg.get("start", "var(--sl-bg-offwhite)")
        end = gradient_cfg.get("end", "#ffffff")
        angle = gradient_cfg.get("angle", 180)
        background_layers = (
            f"linear-gradient(0deg, {overlay_rgba}, {overlay_rgba}), "
            f"linear-gradient({angle}deg, {start}, {end})"
        )

    sections_cfg = config.get("sections", {})
    section_layers = ""
    section_overlay = min(max(int(sections_cfg.get("overlay_opacity", 18)), 0), 100) / 100
    section_overlay_rgba = f"rgba(255, 255, 255, {section_overlay:.2f})"
    section_type = sections_cfg.get("background_type", "inherit")
    if section_type == "solid":
        sec_color = sections_cfg.get("solid_color", "#ffffff")
        section_layers = (
            f"linear-gradient(0deg, {section_overlay_rgba}, {section_overlay_rgba}), "
            f"linear-gradient(0deg, {sec_color}, {sec_color})"
        )
    elif section_type == "image":
        section_image = resolve_asset_path(sections_cfg.get("image_name")) or HERO_IMAGE_PATH
        sec_url = image_css_url(section_image)
        if sec_url:
            section_layers = f"linear-gradient(0deg, {section_overlay_rgba}, {section_overlay_rgba}), {sec_url}"

    if not section_layers:
        section_layers = background_layers

    css = f"""
    <style>
    :root {{
        --sl-page-bg-image: {background_layers};
        --sl-section-bg-image: {section_layers};
        --sl-page-blur: {bg_cfg.get("blur", 0)}px;
        --sl-page-brightness: {bg_cfg.get("brightness", 100) / 100:.2f};
        --sl-page-contrast: {bg_cfg.get("contrast", 100) / 100:.2f};
    }}
    .stApp {{
        background-image: var(--sl-page-bg-image);
        background-size: cover, cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: {attachment}, {attachment};
        backdrop-filter: blur(var(--sl-page-blur, 0px));
        filter: brightness(var(--sl-page-brightness, 1)) contrast(var(--sl-page-contrast, 1));
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def inject_base_css(config: dict[str, Any]):
    theme = config.get("theme", {})
    typography = config.get("typography", {})
    icons_cfg = config.get("icons", {})
    hero_cfg = config.get("hero", {})

    radius_map = {"small": "14px", "medium": "20px", "large": "28px"}
    shadow_map = {
        "none": "none",
        "soft": "0 14px 34px rgba(8, 46, 102, 0.12)",
        "strong": "0 24px 48px rgba(6, 24, 46, 0.28)",
    }
    icon_size_map = {"small": "2.2rem", "medium": "2.8rem", "large": "3.4rem"}
    animation_map = {
        "none": ("none", "0s"),
        "slow": ("float", "18s"),
        "medium": ("float", "12s"),
        "fast": ("float", "7s"),
    }
    hero_height_map = {"small": "360px", "medium": "480px", "large": "600px"}
    scale_map = {"small": 0.9, "default": 1.0, "large": 1.1}

    primary = theme.get("primary_color", "#0d2a4f")
    secondary = theme.get("secondary_color", "#89b4ff")
    card_bg = theme.get("card_background", "#ffffff")
    card_border = theme.get("card_border", "#e3ecf8")
    section_surface = theme.get("section_background", "rgba(255,255,255,0.94)")
    field_bg = theme.get("field_background", "rgba(255,255,255,0.85)")
    field_border = theme.get("field_border", "#d2dbe8")
    field_text = theme.get("field_text", "#143A66")
    card_radius = radius_map.get(theme.get("card_radius", "large"), "24px")
    card_shadow = shadow_map.get(theme.get("shadow", "soft"), shadow_map["soft"])
    icon_size = icon_size_map.get(icons_cfg.get("size", "medium"), icon_size_map["medium"])
    hero_height = hero_height_map.get(hero_cfg.get("height", "medium"), hero_height_map["medium"])
    animation_name, animation_duration = animation_map.get(
        icons_cfg.get("animation", "medium"), animation_map["medium"]
    )
    font_scale = scale_map.get(typography.get("scale", "default"), 1.0)
    heading_font = typography.get("heading_font", "'Bebas Neue', sans-serif")
    body_font = typography.get("body_font", "'Inter', sans-serif")
    arabic_font = typography.get("arabic_font", "'Dubai', sans-serif")
    hero_overlay_opacity = min(max(int(hero_cfg.get("overlay_opacity", 55)), 0), 100) / 100
    hero_overlay = f"linear-gradient(180deg, rgba(255,255,255,0.0) 0%, rgba(255,255,255,{hero_overlay_opacity:.2f}) 100%)"

    mode = theme.get("mode", "light")
    base_text = "#0d2a4f" if mode == "light" else "#f4f6ff"
    sub_text = "rgba(13,42,79,0.75)" if mode == "light" else "rgba(244,248,255,0.75)"


    css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Baloo+2:wght@600;700&family=DM+Serif+Display&family=Tajawal:wght@400;600;700&display=swap');

    :root {{
        --sl-logo-blue: #54A9FF;
        --sl-dark-blue: #143A66;
        --sl-text-gray: #4B627F;
        --sl-bg-offwhite: #F7F5EF;
        --sl-section-bg-image: none;
        --sl-page-blur: 0px;
        --sl-page-brightness: 1;
        --sl-page-contrast: 1;
        --primary-color: {primary};
        --secondary-color: {secondary};
        --card-bg: {card_bg};
        --card-border: {card_border};
        --card-radius: {card_radius};
        --card-shadow: {card_shadow};
        --sl-section-surface: {section_surface};
        --sl-field-bg: {field_bg};
        --sl-field-border: {field_border};
        --sl-field-text: {field_text};
        --hero-min-height: {hero_height};
        --icon-size: {icon_size};
        --font-scale: {font_scale};
        --hero-overlay: {hero_overlay};
    }}

    body, .stApp {{
        color: var(--sl-text-gray);
        background-color: var(--sl-bg-offwhite);
        font-family: {body_font};
        font-size: calc(1rem * var(--font-scale));
    }}
    .sl-logo-en {{
        font-family: 'Baloo 2', 'Fredoka', system-ui, sans-serif;
        color: var(--sl-logo-blue);
        letter-spacing: 0.16em;
        text-transform: uppercase;
    }}
    .sl-section-header {{
        display: flex;
        flex-direction: column;
        gap: 0.6rem;
        margin-bottom: 1.4rem;
    }}
    .sl-logo-mark {{
        display: block;
        margin: 0 auto 0.8rem auto;
        max-width: 200px;
        height: auto;
        filter: drop-shadow(0 8px 26px rgba(20, 58, 102, 0.25));
    }}
    .sl-hero-tagline {{
        text-align: center;
        font-family: 'Baloo 2', 'Tajawal', sans-serif;
        color: var(--sl-dark-blue);
        letter-spacing: 0.12em;
        display: flex;
        flex-direction: column;
        gap: 0.1rem;
        font-size: 1rem;
    }}
    .sl-section-header-row {{
        display: flex;
        flex-wrap: wrap;
        justify-content: space-between;
        align-items: center;
        gap: 0.6rem;
    }}
    .sl-kicker {{
        font-family: 'Baloo 2', 'Fredoka', system-ui, sans-serif;
        letter-spacing: 0.18em;
        font-size: 0.85rem;
        color: var(--sl-logo-blue);
    }}
    .sl-pill {{
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        padding: 0.35rem 0.9rem;
        border: 1px solid rgba(84, 169, 255, 0.45);
        border-radius: 999px;
        background: rgba(255,255,255,0.9);
        font-family: 'Tajawal', 'Cairo', system-ui, sans-serif;
        color: var(--sl-dark-blue);
        font-size: 1.05rem;
        font-weight: 600;
    }}
    .sl-pill-icon {{
        font-size: 1.2rem;
    }}
    .sl-section-title-wrapper {{
        padding: 0.55rem 1rem;
        border: 1px solid rgba(20, 58, 102, 0.15);
        border-radius: 16px;
        background: rgba(255,255,255,0.9);
    }}
    .sl-section-title {{
        font-family: 'DM Serif Display', 'Times New Roman', serif;
        font-size: clamp(1.4rem, 4vw, 2.2rem);
        letter-spacing: 0.1em;
        color: var(--sl-dark-blue);
    }}
    .sl-en-body {{
        font-family: 'DM Serif Display', 'Times New Roman', serif;
        color: var(--sl-dark-blue);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        line-height: 1.6;
    }}
    .sl-en-title {{
        font-family: 'DM Serif Display', 'Times New Roman', serif;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--sl-dark-blue);
    }}
    .sl-ar-title {{
        font-family: 'Tajawal', 'Cairo', system-ui, sans-serif;
        color: var(--sl-dark-blue);
        font-size: clamp(1.4rem, 3vw, 1.9rem);
        font-weight: 600;
        line-height: 1.4;
    }}
    .sl-ar-body {{
        font-family: 'Tajawal', 'Cairo', system-ui, sans-serif;
        color: var(--sl-text-gray);
        line-height: 1.8;
    }}
    h1, h2, h3, h4 {{
        color: var(--sl-dark-blue);
    }}
    .page-container {{
        max-width: 1180px;
        margin: 0 auto;
        padding: 0.8rem 0.75rem 1.6rem;
    }}
    .page-card {{
        max-width: 1180px;
        width: 100%;
        background: transparent;
        box-shadow: none;
        padding: 0;
    }}
    @media (max-width: 800px) {{
        .page-card {{
            padding: 0;
        }}
    }}

    .hero-card {{
        position: relative;
        border-radius: var(--card-radius);
        overflow: hidden;
        min-height: var(--hero-min-height);
        background-size: cover;
        background-position: center;
        box-shadow: 0 18px 48px rgba(14, 59, 110, 0.26);
        isolation: isolate;
    }}
    .sticker {{ display: none; }}
    .hero-sticker-img {{
        position: absolute;
        z-index: 3;
        width: clamp(60px, 9vw, 110px);
        opacity: 0.95;
        pointer-events: none;
        filter: drop-shadow(0 15px 30px rgba(0,0,0,0.2));
        animation: float 16s ease-in-out infinite;
    }}
    @keyframes float {{
        0% {{ transform: translateY(0px); }}
        50% {{ transform: translateY(-10px); }}
        100% {{ transform: translateY(0px); }}
    }}
    .hero-layer {{
        position: absolute;
        inset: 0;
        background: var(--hero-overlay);
        z-index: 1;
    }}
    .hero-content {{
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
        color: {base_text};
        text-align: center;
    }}
    .hero-nav {{
        display: flex;
        gap: 1.8rem;
        letter-spacing: 0.18em;
        font-size: 0.9rem;
        text-transform: uppercase;
        color: var(--sl-dark-blue);
        flex-wrap: wrap;
        justify-content: center;
    }}
    .hero-title {{
        font-size: calc(3.6rem * var(--font-scale));
        line-height: 1.05;
        letter-spacing: 0.18em;
        font-weight: 800;
        color: var(--sl-logo-blue);
        text-shadow: 0 10px 24px rgba(0, 0, 0, 0.14);
        font-family: {heading_font};
    }}
    .hero-tags {{
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
        justify-content: center;
    }}
    .sl-cta-group {{
        display: flex;
        gap: 0.75rem;
        flex-wrap: wrap;
        justify-content: center;
        margin-top: 0.5rem;
    }}
    .sl-cta {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 0.65rem 1.6rem;
        border-radius: 999px;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-decoration: none;
        border: 1px solid transparent;
        box-shadow: 0 15px 30px rgba(15, 37, 64, 0.15);
    }}
    .sl-cta.primary {{
        background: var(--sl-dark-blue);
        color: #fff;
    }}
    .sl-cta.secondary {{
        background: rgba(255,255,255,0.92);
        color: var(--sl-dark-blue);
        border-color: rgba(20,58,102,0.2);
    }}
    .hero-pill {{
        background: rgba(255, 255, 255, 0.92);
        color: {primary};
        padding: 0.6rem 1.4rem;
        border-radius: 999px;
        font-weight: 700;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.16);
        letter-spacing: 0.08em;
    }}
    .info-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 1rem;
        margin: 1.1rem 0 1.0rem 0;
    }}
    .info-card {{
        position: relative;
        overflow: hidden;
        background: var(--sl-section-surface);
        border: 1px solid var(--card-border);
        border-radius: var(--card-radius);
        padding: 1.1rem 1.25rem;
        box-shadow: var(--card-shadow);
        backdrop-filter: blur(4px);
    }}
    .info-card::before {{
        content: "";
        position: absolute;
        inset: 0;
        background-image: var(--sl-section-bg-image);
        background-size: cover, cover;
        background-position: center;
        background-repeat: no-repeat;
        opacity: 0.1;
        z-index: 0;
    }}
    .info-card > * {{
        position: relative;
        z-index: 1;
    }}
    .stTextInput input,
    .stNumberInput input,
    .stTextArea textarea,
    .stSelectbox div[data-baseweb="select"] input,
    .stSelectbox div[data-baseweb="select"] > div {{
        background: var(--sl-field-bg) !important;
        border-radius: 14px !important;
        border: 1px solid var(--sl-field-border) !important;
        color: var(--sl-field-text) !important;
        min-height: 44px;
    }}
    .stTextArea textarea {{ min-height: 94px; }}
    .stSelectbox div[data-baseweb="select"] > div {{
        display: flex;
        align-items: center;
    }}
    .stTextInput input:focus,
    .stNumberInput input:focus,
    .stTextArea textarea:focus,
    .stSelectbox div[data-baseweb="select"] > div:focus-within {{
        border: 1px solid var(--sl-logo-blue) !important;
        box-shadow: 0 0 0 2px rgba(84, 169, 255, 0.25) !important;
    }}
    .info-card h3 {{
        margin: 0 0 0.4rem 0;
        font-size: 1.1rem;
        letter-spacing: 0.08em;
        color: var(--sl-dark-blue);
    }}
    .info-card p {{
        margin: 0;
        color: {sub_text};
        line-height: 1.5;
    }}
    .section-card {{
        position: relative;
        overflow: hidden;
        background: var(--sl-section-surface);
        border: 1px solid var(--card-border);
        border-radius: var(--card-radius);
        padding: 1.4rem 1.4rem 1.2rem 1.4rem;
        box-shadow: var(--card-shadow);
        margin-top: 1rem;
        z-index: 1;
        backdrop-filter: blur(6px);
    }}
    .section-card::before {{
        content: "";
        position: absolute;
        inset: 0;
        background-image: var(--sl-section-bg-image);
        background-size: cover, cover;
        background-position: center;
        background-repeat: no-repeat;
        opacity: 0.16;
        z-index: 0;
    }}
    .section-card > * {{
        position: relative;
        z-index: 1;
    }}
    .section-with-sticker {{
        position: relative;
    }}
    .section-sticker {{
        position: absolute;
        pointer-events: none;
        z-index: 0;
    }}
    .section-sticker img {{
        filter: drop-shadow(0 20px 40px rgba(15,37,64,0.2));
    }}
    .section-top-left {{ top: -40px; left: -30px; }}
    .section-top-right {{ top: -40px; right: -30px; }}
    .section-bottom-left {{ bottom: -30px; left: -20px; }}
    .section-bottom-right {{ bottom: -30px; right: -20px; }}
    .contact-collage {{
        margin-top: 1.8rem;
        text-align: center;
    }}
    .contact-collage img {{
        max-width: min(90%, 420px);
        width: 100%;
        border-radius: 26px;
        box-shadow: 0 32px 58px rgba(18, 46, 80, 0.18);
    }}
    .whatsapp-cta {{
        margin-top: 1.5rem;
        display: flex;
        flex-wrap: wrap;
        gap: 1rem;
        align-items: center;
    }}
    .whatsapp-btn {{
        background: #1fa855;
        color: #fff;
        padding: 0.8rem 1.6rem;
        border-radius: 999px;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        box-shadow: 0 12px 28px rgba(31,168,85,0.35);
    }}
    .qr-frame {{
        border: 1px solid rgba(20,58,102,0.15);
        border-radius: 18px;
        padding: 0.8rem;
        background: rgba(255,255,255,0.96);
        box-shadow: 0 20px 38px rgba(15,37,64,0.12);
    }}
    .instagram-card {{
        margin-top: 1rem;
        padding: 1.2rem;
        border-radius: 22px;
        background: rgba(84,169,255,0.08);
        border: 1px solid rgba(84,169,255,0.2);
        display: flex;
        align-items: center;
        gap: 1rem;
    }}
    .snow-title {{
        text-align: center;
        font-size: calc(3rem * var(--font-scale));
        font-weight: 700;
        letter-spacing: 0.30em;
        margin-bottom: 0.4rem;
        font-family: {heading_font};
    }}
    .subheading {{
        text-align: center;
        font-size: 0.95rem;
        opacity: 0.8;
        margin-bottom: 2rem;
        color: {sub_text};
    }}
    .arabic {{
        direction: rtl;
        text-align: right;
        font-size: 1rem;
        line-height: 1.8;
        font-family: 'Tajawal', 'Cairo', system-ui, sans-serif;
        color: var(--sl-text-gray);
    }}
    .english {{
        direction: ltr;
        text-align: left;
        font-size: 0.98rem;
        line-height: 1.7;
        font-family: {body_font};
        color: var(--sl-text-gray);
    }}
    .dual-column {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 2.25rem;
    }}
    @media (max-width: 800px) {{
        .dual-column {{
            grid-template-columns: 1fr;
        }}
        .hero-card {{
            min-height: 360px;
        }}
        .hero-title {{
            font-size: calc(2.6rem * var(--font-scale));
        }}
        .hero-nav {{
            gap: 0.7rem;
            font-size: 0.78rem;
        }}
        .hero-content {{
            padding: 2rem 1.2rem;
            gap: 1rem;
        }}
    }}
    .ticket-price {{
        font-size: 1.2rem;
        font-weight: 700;
        margin-top: 1rem;
    }}
    .stButton>button, .stLinkButton>button {{
        border-radius: calc(var(--card-radius) / 1.3);
        padding: 0.7rem 1.6rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        background-color: var(--sl-dark-blue);
        color: #fff;
        border: none;
        box-shadow: 0 10px 24px rgba(0,0,0,0.18);
    }}
    .center-btn {{
        display: flex;
        justify-content: center;
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
    }}
    .footer-note {{
        text-align: center;
        font-size: 0.8rem;
        opacity: 0.75;
        margin-top: 1.5rem;
    }}
    .admin-gear {{
        position: fixed;
        top: 12px;
        right: 16px;
        z-index: 999;
    }}
    .admin-gear button {{
        background: rgba(0, 0, 0, 0.35) !important;
        color: #fff !important;
        border: none !important;
        border-radius: 999px !important;
        width: 42px;
        height: 42px;
        font-size: 1.1rem;
        backdrop-filter: blur(8px);
    }}
    .snow-overlay {{
        position: fixed;
        inset: 0;
        pointer-events: none;
        z-index: 5;
        overflow: hidden;
    }}
    .snowflake {{
        position: absolute;
        top: -5%;
        color: rgba(255,255,255,0.95);
        text-shadow: 0 0 6px rgba(20, 58, 102, 0.25);
        animation-name: sl-snow;
        animation-timing-function: linear;
        animation-iteration-count: infinite;
    }}
    @keyframes sl-snow {{
        0% {{ transform: translate3d(0, 0, 0) rotate(0deg); opacity: 0; }}
        10% {{ opacity: 1; }}
        100% {{ transform: translate3d(-20px, 110vh, 0) rotate(360deg); opacity: 0; }}
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def init_state():
    if "page" not in st.session_state:
        st.session_state.page = "welcome"
    st.session_state.setdefault("settings_panel_visible", False)
    st.session_state.setdefault("settings_unlocked", False)
    st.session_state.setdefault("show_pin_prompt", False)


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


def hero_background_style(config: dict[str, Any]) -> str:
    hero_cfg = config.get("hero", {})
    bg_type = hero_cfg.get("background_type", "image")
    if bg_type == "image":
        hero_image = resolve_asset_path(hero_cfg.get("image_name")) or HERO_IMAGE_PATH
        css_url = image_css_url(hero_image)
        if css_url:
            return f"background-image: {css_url};"
    solid = hero_cfg.get("solid_color", "#dfeffd")
    return f"background: {solid};"


def build_field_label(en_text: str, ar_text: str, mode: str) -> str:
    if mode == "english":
        return en_text
    if mode == "arabic":
        return ar_text
    return f"{en_text} / {ar_text}"


def build_input_meta(label_text: str, label_position: str) -> dict[str, Any]:
    if label_position == "placeholder":
        return {
            "label": "",
            "label_visibility": "collapsed",
            "placeholder": label_text,
        }
    return {"label": label_text, "label_visibility": "visible", "placeholder": None}


def option_index(options: list[str], value: str, default: int = 0) -> int:
    try:
        return options.index(value)
    except ValueError:
        return default


def render_admin_toggle():
    gear_placeholder = st.empty()
    with gear_placeholder.container():
        st.markdown('<div class="admin-gear">', unsafe_allow_html=True)
        clicked = st.button("⚙️", key="settings_toggle", help="Open admin settings")
        st.markdown("</div>", unsafe_allow_html=True)
    if clicked:
        if st.session_state.get("settings_unlocked"):
            st.session_state["settings_panel_visible"] = not st.session_state.get(
                "settings_panel_visible", False
            )
        else:
            st.session_state["settings_panel_visible"] = True
            st.session_state["show_pin_prompt"] = True


def render_pin_prompt(config: dict[str, Any]):
    st.warning("🔐 أدخل رمز الـ PIN الإداري لفتح إعدادات الواجهة.")
    with st.form("admin_pin_form"):
        pin_value = st.text_input("Admin PIN", type="password", max_chars=8)
        submitted = st.form_submit_button("Unlock")
    if submitted:
        if pin_value == get_admin_pin(config):
            st.session_state["settings_unlocked"] = True
            st.session_state["show_pin_prompt"] = False
            st.success("Settings unlocked.")
            rerun_app()
        else:
            st.error("Incorrect PIN. Try again.")


def render_section_header(en_title: str, ar_title: str, icon: str = "❄️", kicker: str = "SNOW LIWA"):
    st.markdown(
        f"""
        <div class="sl-section-header">
            <div class="sl-section-header-row">
                <span class="sl-kicker">{kicker}</span>
                <div class="sl-pill">
                    <span class="sl-pill-icon">{icon}</span>
                    <span class="sl-pill-text">{ar_title}</span>
                </div>
            </div>
            <div class="sl-section-title-wrapper">
                <span class="sl-section-title">{en_title}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_snow_overlay(config: dict[str, Any]):
    snow_cfg = config.get("effects", {}).get("snow", {})
    if not snow_cfg.get("enabled", True):
        return
    if st.session_state.get("snow_overlay_rendered"):
        return
    st.session_state["snow_overlay_rendered"] = True

    symbol_map = {
        "sparkle": "✦",
        "flake": "❄️",
        "dot": "•",
        "emoji": "🌨️",
    }
    size_map = {
        "small": (0.5, 1.0),
        "medium": (0.8, 1.5),
        "large": (1.2, 2.1),
    }
    speed_map = {
        "slow": (12, 20),
        "medium": (8, 16),
        "fast": (5, 12),
    }

    flakes = []
    count = int(snow_cfg.get("flakes", 36))
    size_range = size_map.get(snow_cfg.get("size", "medium"), size_map["medium"])
    speed_range = speed_map.get(snow_cfg.get("speed", "medium"), speed_map["medium"])
    glyph = symbol_map.get(snow_cfg.get("symbol", "sparkle"), "✦")

    for _ in range(max(count, 0)):
        left = random.randint(0, 100)
        delay = random.uniform(0, 8)
        duration = random.uniform(*speed_range)
        size = random.uniform(*size_range)
        flakes.append(
            f"<span class='snowflake' style='left:{left}%; animation-delay:{delay:.1f}s; animation-duration:{duration:.1f}s; font-size:{size:.2f}rem;'>{glyph}</span>"
        )
    st.markdown(f"<div class='snow-overlay'>{''.join(flakes)}</div>", unsafe_allow_html=True)


def render_background_music(filename: str = "babanuail.mp3"):
    if st.session_state.get("music_rendered"):
        return
    audio_path = resolve_asset_path(filename)
    if not audio_path:
        return
    try:
        encoded_audio = base64.b64encode(audio_path.read_bytes()).decode()
    except Exception:
        return
    st.session_state["music_rendered"] = True
    audio_html = f"""
    <audio autoplay loop hidden id="sl-bg-music">
        <source src="data:audio/mpeg;base64,{encoded_audio}" type="audio/mpeg">
    </audio>
    """
    st.markdown(audio_html, unsafe_allow_html=True)


def render_logo_image(config: dict[str, Any]) -> str:
    branding_cfg = config.get("branding", {})
    if not branding_cfg.get("show_logo"):
        return ""
    logo_path = resolve_asset_path(branding_cfg.get("logo_image"))
    data_uri = image_data_uri(logo_path)
    if not data_uri:
        return ""
    width = int(branding_cfg.get("logo_width", 140))
    return f"<img class='sl-logo-mark' src='{data_uri}' alt='SNOW LIWA logo' style='width:{width}px;'>"


def render_section_sticker(section_key: str, config: dict[str, Any]) -> str:
    sticker_cfg = config.get("stickers", {}).get("sections", {}).get(section_key)
    if not sticker_cfg:
        return ""
    img_uri = image_data_uri(resolve_asset_path(sticker_cfg.get("image")))
    if not img_uri:
        return ""
    position_class = sticker_cfg.get("position", "top-left")
    width = int(sticker_cfg.get("width", 180))
    opacity = min(max(float(sticker_cfg.get("opacity", 0.18)), 0.05), 1.0)
    return (
        f"<div class='section-sticker section-{position_class}' style='opacity:{opacity};'>"
        f"<img src='{img_uri}' style='width:{width}px;' alt='sticker'>"
        "</div>"
    )


def render_hero_ctas(config: dict[str, Any]) -> str:
    ctas = config.get("hero_cta", [])
    buttons = []
    for cta in ctas:
        label = cta.get("label")
        url = cta.get("url")
        style = cta.get("style", "primary")
        if not label or not url:
            continue
        buttons.append(
            f"<a class='sl-cta {style}' href='{url}' target='_blank' rel='noopener noreferrer'>{label}</a>"
        )
    if not buttons:
        return ""
    return "<div class='sl-cta-group'>" + "".join(buttons) + "</div>"


def render_futuristic_panel_fx():
    if st.session_state.get("future_fx_rendered"):
        return
    st.session_state["future_fx_rendered"] = True
    st.markdown(
        """
        <style>
        @keyframes panel-glow {
            0% { opacity: 0; transform: scale(0.95); }
            50% { opacity: 0.9; transform: scale(1.02); }
            100% { opacity: 0; transform: scale(1.05); }
        }
        .settings-holo {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 320px;
            height: 320px;
            pointer-events: none;
            border: 2px solid rgba(84,169,255,0.4);
            border-radius: 32px;
            box-shadow: 0 0 60px rgba(84,169,255,0.4);
            animation: panel-glow 3s ease-out forwards;
            z-index: 2000;
        }
        </style>
        <div class="settings-holo"></div>
        """,
        unsafe_allow_html=True,
    )


# =========================
# PAGE CONTENT
# =========================


def render_welcome(config: dict[str, Any]):
    hero_style = hero_background_style(config)
    branding_cfg = config.get("branding", {})
    stickers_cfg = config.get("stickers", {})
    nav_cfg = config.get("content", {}).get("nav", {})
    nav_items = [
        nav_cfg.get("name", "NAME"),
        nav_cfg.get("about", "ABOUT"),
        nav_cfg.get("activities", "ACTIVITIES"),
        nav_cfg.get("invites", "INVITES"),
        nav_cfg.get("contact", "CONTACT"),
    ]
    nav_html = "".join(
        f"<span class='sl-en-title'>{item}</span>" for item in nav_items if item
    )
    logo_html = render_logo_image(config)
    tagline_en = branding_cfg.get("tagline_en")
    tagline_ar = branding_cfg.get("tagline_ar")
    tagline_html = ""
    if tagline_en or tagline_ar:
        tagline_html = "<div class='sl-hero-tagline'>"
        if tagline_ar:
            tagline_html += f"<span class='sl-ar-title' style='font-size:1rem;'>{tagline_ar}</span>"
        if tagline_en:
            tagline_html += f"<span class='sl-en-title' style='font-size:0.9rem;'>{tagline_en}</span>"
        tagline_html += "</div>"

    hero_stickers_html = ""
    hero_sticker_positions = [
        "top: 12%; left: 6%;",
        "top: 26%; right: 8%;",
        "bottom: 16%; left: 14%;",
        "bottom: 8%; right: 24%;",
    ]
    hero_stickers_cfg = stickers_cfg.get("hero", {})
    if hero_stickers_cfg.get("enabled", True):
        images = hero_stickers_cfg.get("images", []) or []
        snippets = []
        for idx, filename in enumerate(images[: len(hero_sticker_positions)]):
            uri = image_data_uri(resolve_asset_path(filename))
            if not uri:
                continue
            snippets.append(
                f"<img class='hero-sticker-img' style='{hero_sticker_positions[idx]}' src='{uri}' alt='hero sticker {idx}'>"
            )
        hero_stickers_html = "".join(snippets)

    st.markdown(
        f"""
        <div class="hero-card" style="{hero_style}">
            <div class="hero-layer"></div>
            {hero_stickers_html}
            <div class="hero-content">
                {logo_html}
                <div class="hero-nav">
                    {nav_html}
                </div>
                <div class="hero-title sl-logo-en">SNOW<br>LIWA</div>
                {tagline_html}
                <div class="hero-tags">
                    <span class="hero-pill">ICE SKATING</span>
                    <span class="hero-pill">SLADDING</span>
                </div>
                {render_hero_ctas(config)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cards_cfg = config.get("content", {}).get("cards", {})
    info_sections = [
        cards_cfg.get(
            "activities",
            {
                "title": "ACTIVITIES",
                "description": "Snow play, warm drinks, chocolate fountain, and winter vibes for friends & family.",
            },
        ),
        cards_cfg.get(
            "events",
            {
                "title": "EVENTS",
                "description": "Group bookings, private sessions, and curated winter moments at our secret Liwa spot.",
            },
        ),
        cards_cfg.get(
            "contact",
            {
                "title": "CONTACT",
                "description": "Reach us on WhatsApp or Instagram snowliwa. Exact location shared after booking.",
            },
        ),
    ]
    card_markup = []
    for section in info_sections:
        title = section.get("title") or ""
        desc = section.get("description") or ""
        card_markup.append(
            f"<div class='info-card'><h3 class='sl-en-title'>{title}</h3><p>{desc}</p></div>"
        )
    cards_html = "<div class=\"info-grid\">" + "".join(card_markup) + "</div>"
    st.markdown(cards_html, unsafe_allow_html=True)

    render_booking_form(config)


def render_booking_form(config: dict[str, Any]):
    booking_cfg = config.get("content", {}).get("booking", {})
    form_cfg = config.get("form", {})
    language_mode = config.get("language", {}).get("form_language", "bilingual")
    label_position = form_cfg.get("label_position", "top")

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown(f"### {booking_cfg.get('title', '🎟️ Book your ticket')}")
    st.write(booking_cfg.get("price_text", f"Entrance ticket: {TICKET_PRICE} AED per person."))

    name_label = build_field_label("Name", "الاسم الكامل", language_mode)
    phone_label = build_field_label("Phone (WhatsApp)", "رقم الهاتف (واتساب)", language_mode)
    tickets_label = build_field_label("Number of tickets", "عدد التذاكر", language_mode)
    notes_label = build_field_label("Notes (optional)", "ملاحظات اختيارية", language_mode)

    name_meta = build_input_meta(name_label, label_position)
    phone_meta = build_input_meta(phone_label, label_position)
    notes_meta = build_input_meta(notes_label, label_position)

    button_label = booking_cfg.get("button_text", "Proceed to payment with Ziina")
    if form_cfg.get("show_ticket_icon", True):
        button_label = f"🎟️ {button_label}" if not button_label.startswith("🎟️") else button_label

    use_full_width = form_cfg.get("button_width", "auto") == "full"

    with st.form("booking_form"):
        name = st.text_input(
            name_meta["label"] or " ",
            placeholder=name_meta.get("placeholder"),
            label_visibility=name_meta["label_visibility"],
        )
        phone = st.text_input(
            phone_meta["label"] or " ",
            placeholder=phone_meta.get("placeholder"),
            label_visibility=phone_meta["label_visibility"],
        )
        tickets = st.number_input(
            tickets_label,
            min_value=1,
            max_value=20,
            value=1,
            step=1,
            label_visibility="visible" if label_position == "top" else "collapsed",
        )
        notes = ""
        if form_cfg.get("show_notes", True):
            notes = st.text_area(
                notes_meta["label"] or " ",
                height=70,
                placeholder=notes_meta.get("placeholder"),
                label_visibility=notes_meta["label_visibility"],
            )
        submitted = st.form_submit_button(button_label, use_container_width=use_full_width)

    st.markdown("</div>", unsafe_allow_html=True)

    if not submitted:
        return

    if not name or not phone:
        st.error("❗ الرجاء إدخال الاسم ورقم الهاتف.")
        return

    df = load_bookings()
    booking_id = get_next_booking_id(df)
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_amount = tickets * TICKET_PRICE

    pi_json = create_payment_intent(total_amount, booking_id, name)

    if pi_json:
        payment_intent_id = pi_json.get("id", "")
        redirect_url = pi_json.get("redirect_url", "")
        payment_status = pi_json.get("status", "requires_payment_instrument")
    else:
        payment_intent_id = ""
        redirect_url = ""
        payment_status = "error"

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

    custom_success = form_cfg.get("success_message")
    if custom_success:
        st.info(custom_success)

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


def render_who_we_are(config: dict[str, Any]):
    st.markdown("<div class='section-with-sticker'>" + render_section_sticker("who", config), unsafe_allow_html=True)
    render_section_header("WHO ARE WE ?", "من نحن ؟", icon="🤍")

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

    language_mode = config.get("language", {}).get("form_language", "bilingual")
    show_ar = language_mode in ("bilingual", "arabic")
    show_en = language_mode in ("bilingual", "english")

    sections = ["<div class=\"dual-column\">"]
    if show_ar:
        sections.append(
            f'<div class="arabic sl-ar-body"><div class="sl-ar-title">من نحن ؟</div><br><br>{ar_text}</div>'
        )
    if show_en:
        sections.append(
            f'<div class="english"><div class="sl-en-title">{en_title}</div><br><br><div class="sl-en-body">{en_text}</div></div>'
        )
    sections.append("</div>")
    st.markdown("".join(sections), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_experience(config: dict[str, Any]):
    st.markdown("<div class='section-with-sticker'>" + render_section_sticker("experience", config), unsafe_allow_html=True)
    render_section_header("EXPERIENCE", "تجربة الثلج", icon="❄️")

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

    language_mode = config.get("language", {}).get("form_language", "bilingual")
    show_ar = language_mode in ("bilingual", "arabic")
    show_en = language_mode in ("bilingual", "english")

    sections = ["<div class=\"dual-column\">"]
    if show_ar:
        sections.append(
            f'<div class="arabic sl-ar-body">{ar_block_1}<br><br>{ar_block_2}</div>'
        )
    if show_en:
        sections.append(
            f'<div class="english"><div class="sl-en-body">{en_block_1}<br><br>{en_block_2}</div></div>'
        )
    sections.append("</div>")
    st.markdown("".join(sections), unsafe_allow_html=True)

    st.markdown(
        f'<div class="ticket-price">🎟️ Entrance Ticket: <strong>{TICKET_PRICE} AED</strong> per person</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


def render_contact(config: dict[str, Any]):
    st.markdown("<div class='section-with-sticker'>" + render_section_sticker("contact", config), unsafe_allow_html=True)
    render_section_header("CONTACT", "تواصل معنا", icon="☎️")
    social_cfg = config.get("social", {})
    whatsapp = social_cfg.get("whatsapp_number", "050 113 8781")
    instagram = social_cfg.get("instagram_handle", "snowliwa")
    instagram_url = social_cfg.get("instagram_url") or f"https://instagram.com/{instagram}"
    whatsapp_message = social_cfg.get("whatsapp_message", "Hi SNOW LIWA!")
    whatsapp_link = build_whatsapp_link(whatsapp, whatsapp_message)

    ar_contact = f"""
**رقم الهاتف**

{whatsapp}

للتواصل عبر الواتساب فقط أو من خلال حسابنا في الإنستغرام:
**{instagram}**
"""

    en_contact = f"""
**Phone / WhatsApp**

{whatsapp}

Instagram: [{instagram}]({instagram_url})
"""

    language_mode = config.get("language", {}).get("form_language", "bilingual")
    show_ar = language_mode in ("bilingual", "arabic")
    show_en = language_mode in ("bilingual", "english")

    sections = ["<div class=\"dual-column\">"]
    if show_ar:
        sections.append(f'<div class="arabic sl-ar-body">{ar_contact}</div>')
    if show_en:
        sections.append(f'<div class="english sl-en-body">{en_contact}</div>')
    sections.append("</div>")
    st.markdown("".join(sections), unsafe_allow_html=True)

    if social_cfg.get("show_whatsapp_button", True):
        qr_html = ""
        if social_cfg.get("show_whatsapp_qr", True):
            qr_uri = generate_qr_data_uri(whatsapp_link)
            if qr_uri:
                qr_html = f"<div class='qr-frame'><img src='{qr_uri}' width='120' alt='WhatsApp QR'></div>"
        st.markdown(
            f"<div class='whatsapp-cta'><a class='whatsapp-btn' href='{whatsapp_link}' target='_blank'>"
            "📲 WhatsApp us" "</a>" f"{qr_html}</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        f"<div class='instagram-card'><div><div class='sl-en-title' style='font-size:1.1rem;'>Instagram</div>"
        f"<div class='sl-en-body' style='text-transform:none;'>{instagram}</div></div>"
        f"<a class='sl-cta secondary' href='{instagram_url}' target='_blank'>Visit profile</a></div>",
        unsafe_allow_html=True,
    )

    collage_cfg = config.get("stickers", {}).get("contact_collage", {})
    if collage_cfg.get("enabled"):
        collage_uri = image_data_uri(resolve_asset_path(collage_cfg.get("image_name")))
        if collage_uri:
            width = int(collage_cfg.get("width", 340))
            st.markdown(
                f"<div class='contact-collage'><img src='{collage_uri}' alt='Sticker collage' style='width:{width}px;'></div>",
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.write("You can later add direct WhatsApp links or Instagram buttons here.")
    st.markdown("</div>", unsafe_allow_html=True)


def render_dashboard():
    st.markdown('<div class="snow-title">SNOW LIWA</div>',
                unsafe_allow_html=True)
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
    st.markdown('<div class="snow-title">SNOW LIWA</div>',
                unsafe_allow_html=True)
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
    st.link_button("Back to SNOW LIWA home", APP_BASE_URL,
                   use_container_width=False)
    st.markdown("</div>", unsafe_allow_html=True)


# =========================
# MAIN APP
# =========================


def render_settings_panel(config: dict[str, Any]):
    st.markdown("---")
    st.subheader("🎛️ UI Settings")
    st.caption(
        "هذه الإعدادات تغير فقط الواجهة (CSS / النصوص / الصور). منطق الحجز وملف bookings.xlsx و Ziina API تبقى بدون أي تغيير."
    )

    tabs = st.tabs([
        "Backgrounds",
        "Theme",
        "Typography & Language",
        "Branding & Social",
        "Content",
        "Icons & Form",
        "Visual FX",
        "Security",
    ])

    config_changed = False

    bg_cfg = config.get("background", {})
    hero_cfg = config.get("hero", {})
    theme_cfg = config.get("theme", {})
    typo_cfg = config.get("typography", {})
    language_cfg = config.get("language", {})
    content_cfg = config.get("content", {})
    icons_cfg = config.get("icons", {})
    form_cfg = config.get("form", {})
    security_cfg = config.get("security", {})
    effects_cfg = config.get("effects", {})
    branding_cfg = config.get("branding", {})
    social_cfg = config.get("social", {})
    stickers_cfg = config.get("stickers", {})
    sections_cfg = config.get("sections", {})

    background_types = ["gradient", "solid", "image"]
    hero_types = ["image", "solid"]
    radius_options = ["small", "medium", "large"]
    shadow_options = ["none", "soft", "strong"]
    theme_modes = ["light", "dark"]
    scale_options = ["small", "default", "large"]
    direction_options = ["ltr", "rtl"]
    form_language_options = ["bilingual", "english", "arabic"]
    icon_size_options = ["small", "medium", "large"]
    icon_animation_options = ["none", "slow", "medium", "fast"]
    label_position_options = ["top", "placeholder"]
    button_width_options = ["auto", "full"]

    asset_images = list_asset_images()
    default_bg_image = bg_cfg.get("image_name") or BACKGROUND_IMAGE_PATH.name
    default_hero_image = hero_cfg.get("image_name") or HERO_IMAGE_PATH.name
    if default_bg_image and default_bg_image not in asset_images:
        asset_images.append(default_bg_image)
    if default_hero_image and default_hero_image not in asset_images:
        asset_images.append(default_hero_image)
    asset_images = sorted({img for img in asset_images if img})

    with tabs[0]:
        st.markdown("**Page background**")
        style_option = st.selectbox(
            "Background type",
            background_types,
            index=option_index(background_types, bg_cfg.get("page_style", "gradient")),
        )
        config_changed |= set_config_value(config, ["background", "page_style"], style_option)

        if style_option == "solid":
            color = st.color_picker("Solid color", bg_cfg.get("solid_color", "#f4f8ff"))
            config_changed |= set_config_value(config, ["background", "solid_color"], color)
        elif style_option == "gradient":
            col1, col2 = st.columns(2)
            with col1:
                start = st.color_picker("Gradient start", bg_cfg.get("gradient", {}).get("start", "#f4f8ff"))
                config_changed |= set_config_value(config, ["background", "gradient", "start"], start)
            with col2:
                end = st.color_picker("Gradient end", bg_cfg.get("gradient", {}).get("end", "#ffffff"))
                config_changed |= set_config_value(config, ["background", "gradient", "end"], end)
            angle = st.slider(
                "Gradient angle",
                min_value=0,
                max_value=360,
                value=int(bg_cfg.get("gradient", {}).get("angle", 180)),
            )
            config_changed |= set_config_value(config, ["background", "gradient", "angle"], angle)
        else:
            if asset_images:
                image = st.selectbox(
                    "Background image (assets/)",
                    asset_images,
                    index=option_index(asset_images, default_bg_image),
                )
                config_changed |= set_config_value(config, ["background", "image_name"], image)
            else:
                st.info("Add image files to the assets/ folder to use them here.")

            uploaded_bg = st.file_uploader(
                "Upload new background image",
                type=[ext.lstrip(".") for ext in IMAGE_EXTENSIONS],
                key="bg_image_uploader",
                help="Upload to assets/ and set as page background",
            )
            if uploaded_bg:
                saved_name = save_uploaded_asset(uploaded_bg, "bg")
                if saved_name:
                    config_changed |= set_config_value(config, ["background", "image_name"], saved_name)
                    st.success(f"Saved {uploaded_bg.name} to assets/{saved_name}")
                else:
                    st.error("Please upload PNG/JPG/WEBP files only.")

            if st.button("Reset background image to default", key="reset_bg_image"):
                config_changed |= set_config_value(config, ["background", "image_name"], None)

            if st.button("Delete selected background file", key="delete_bg_image_file"):
                current_img = config.get("background", {}).get("image_name")
                if delete_asset_file(current_img):
                    config_changed |= set_config_value(config, ["background", "image_name"], None)
                    st.success("Background image removed from assets.")
                else:
                    st.info("No custom background selected to delete.")

        overlay = st.slider(
            "Overlay intensity (white glaze)",
            min_value=0,
            max_value=100,
            value=int(bg_cfg.get("overlay_opacity", 45)),
        )
        config_changed |= set_config_value(config, ["background", "overlay_opacity"], overlay)

        is_fixed = st.toggle("Fix background while scrolling", value=bool(bg_cfg.get("is_fixed", True)))
        config_changed |= set_config_value(config, ["background", "is_fixed"], is_fixed)

        blur_value = st.slider(
            "Background blur (px)",
            min_value=0,
            max_value=20,
            value=int(bg_cfg.get("blur", 0)),
        )
        config_changed |= set_config_value(config, ["background", "blur"], blur_value)

        brightness_value = st.slider(
            "Background brightness",
            min_value=50,
            max_value=150,
            value=int(bg_cfg.get("brightness", 100)),
            help="100 = normal",
        )
        config_changed |= set_config_value(config, ["background", "brightness"], brightness_value)

        contrast_value = st.slider(
            "Background contrast",
            min_value=50,
            max_value=150,
            value=int(bg_cfg.get("contrast", 100)),
            help="100 = normal",
        )
        config_changed |= set_config_value(config, ["background", "contrast"], contrast_value)

        st.markdown("**Hero section**")
        hero_type = st.selectbox(
            "Hero background",
            hero_types,
            index=option_index(hero_types, hero_cfg.get("background_type", "image")),
        )
        config_changed |= set_config_value(config, ["hero", "background_type"], hero_type)
        if hero_type == "image" and asset_images:
            hero_image = st.selectbox(
                "Hero image",
                asset_images,
                index=option_index(asset_images, default_hero_image),
            )
            config_changed |= set_config_value(config, ["hero", "image_name"], hero_image)
            if st.button("Reset hero image to default", key="reset_hero_image"):
                config_changed |= set_config_value(config, ["hero", "image_name"], None)
        elif hero_type == "image" and not asset_images:
            st.info("Add hero images to the assets/ folder to use them here.")
        elif hero_type == "solid":
            hero_color = st.color_picker("Hero solid color", hero_cfg.get("solid_color", "#dfeffd"))
            config_changed |= set_config_value(config, ["hero", "solid_color"], hero_color)

        if hero_type == "image":
            uploaded_hero = st.file_uploader(
                "Upload new hero image",
                type=[ext.lstrip(".") for ext in IMAGE_EXTENSIONS],
                key="hero_image_uploader",
                help="Upload to assets/ and set as hero background",
            )
            if uploaded_hero:
                saved_name = save_uploaded_asset(uploaded_hero, "hero")
                if saved_name:
                    config_changed |= set_config_value(config, ["hero", "image_name"], saved_name)
                    st.success(f"Saved {uploaded_hero.name} to assets/{saved_name}")
                else:
                    st.error("Please upload PNG/JPG/WEBP files only.")

            if st.button("Delete hero image file", key="delete_hero_image_file"):
                current_img = config.get("hero", {}).get("image_name")
                if delete_asset_file(current_img):
                    config_changed |= set_config_value(config, ["hero", "image_name"], None)
                    st.success("Hero image removed from assets.")
                else:
                    st.info("No custom hero image selected to delete.")

        hero_height_labels = {"small": "Small (360px)", "medium": "Medium (480px)", "large": "Large (600px)"}
        hero_height = st.selectbox(
            "Hero height",
            radius_options,
            format_func=lambda x: hero_height_labels.get(x, x.title()),
            index=option_index(radius_options, hero_cfg.get("height", "medium")),
        )
        config_changed |= set_config_value(config, ["hero", "height"], hero_height)

        hero_overlay = st.slider(
            "Hero overlay (mist)",
            min_value=0,
            max_value=100,
            value=int(hero_cfg.get("overlay_opacity", 55)),
        )
        config_changed |= set_config_value(config, ["hero", "overlay_opacity"], hero_overlay)

        st.markdown("**Section / Card background**")
        section_types = ["inherit", "solid", "image"]
        section_type = st.selectbox(
            "Card background",
            section_types,
            index=option_index(section_types, sections_cfg.get("background_type", "inherit")),
            format_func=lambda x: "Inherit hero" if x == "inherit" else x.title(),
        )
        config_changed |= set_config_value(config, ["sections", "background_type"], section_type)

        if section_type == "solid":
            section_color = st.color_picker(
                "Card solid color",
                sections_cfg.get("solid_color", "rgba(255,255,255,0.94)"),
            )
            config_changed |= set_config_value(config, ["sections", "solid_color"], section_color)
        elif section_type == "image":
            if asset_images:
                section_image = st.selectbox(
                    "Card background image",
                    asset_images,
                    index=option_index(asset_images, sections_cfg.get("image_name") or default_hero_image),
                )
                config_changed |= set_config_value(config, ["sections", "image_name"], section_image)
            else:
                st.info("Add assets/ images to pick from.")

            uploaded_section = st.file_uploader(
                "Upload card background image",
                type=[ext.lstrip(".") for ext in IMAGE_EXTENSIONS],
                key="section_image_uploader",
                help="Uploads to assets/ and applies to cards",
            )
            if uploaded_section:
                saved_name = save_uploaded_asset(uploaded_section, "section")
                if saved_name:
                    config_changed |= set_config_value(config, ["sections", "image_name"], saved_name)
                    st.success(f"Saved {uploaded_section.name} to assets/{saved_name}")
                else:
                    st.error("Please upload PNG/JPG/WEBP files only.")

            if st.button("Reset card image to default", key="reset_section_image"):
                config_changed |= set_config_value(config, ["sections", "image_name"], None)

            if st.button("Delete card image file", key="delete_section_image_file"):
                current_img = config.get("sections", {}).get("image_name")
                if delete_asset_file(current_img):
                    config_changed |= set_config_value(config, ["sections", "image_name"], None)
                    st.success("Card background image removed from assets.")
                else:
                    st.info("No custom card image selected to delete.")

        section_overlay = st.slider(
            "Card overlay",
            min_value=0,
            max_value=100,
            value=int(sections_cfg.get("overlay_opacity", 18)),
        )
        config_changed |= set_config_value(config, ["sections", "overlay_opacity"], section_overlay)

    with tabs[1]:
        st.markdown("**Brand colors**")
        seasonal_options = list(THEME_PRESETS.keys())
        current_season = config.get("seasonal_theme", "custom")
        seasonal_choice = st.selectbox(
            "Seasonal preset",
            seasonal_options,
            index=option_index(seasonal_options, current_season),
            format_func=lambda x: "Custom" if x == "custom" else x.replace("-", " ").title(),
        )
        if seasonal_choice != current_season:
            config_changed |= set_config_value(config, ["seasonal_theme"], seasonal_choice)
            if seasonal_choice != "custom":
                if apply_theme_preset(config, seasonal_choice):
                    st.toast("Seasonal palette applied. ✨")

        manual_theme_change = False
        primary = st.color_picker("Primary color", theme_cfg.get("primary_color", "#0d2a4f"))
        secondary = st.color_picker("Secondary color", theme_cfg.get("secondary_color", "#89b4ff"))
        card_bg = st.color_picker("Card background", theme_cfg.get("card_background", "#ffffff"))
        card_border = st.color_picker("Card outline", theme_cfg.get("card_border", "#e3ecf8"))
        for path, value in [
            (["theme", "primary_color"], primary),
            (["theme", "secondary_color"], secondary),
            (["theme", "card_background"], card_bg),
            (["theme", "card_border"], card_border),
        ]:
            changed = set_config_value(config, path, value)
            manual_theme_change |= changed
            config_changed |= changed

        corner = st.selectbox(
            "Radius",
            radius_options,
            index=option_index(radius_options, theme_cfg.get("card_radius", "large")),
            format_func=lambda x: x.title(),
        )
        config_changed |= set_config_value(config, ["theme", "card_radius"], corner)

        shadow = st.selectbox(
            "Shadow",
            shadow_options,
            index=option_index(shadow_options, theme_cfg.get("shadow", "soft")),
            format_func=lambda x: x.title(),
        )
        config_changed |= set_config_value(config, ["theme", "shadow"], shadow)

        mode = st.selectbox(
            "Mode",
            theme_modes,
            index=option_index(theme_modes, theme_cfg.get("mode", "light")),
            format_func=lambda x: x.title(),
        )
        config_changed |= set_config_value(config, ["theme", "mode"], mode)

        st.markdown("**Surfaces & form fields**")
        section_surface_color = st.color_picker(
            "Section/card surface color",
            color_picker_value(theme_cfg.get("section_background"), "#ffffff"),
        )
        field_background_color = st.color_picker(
            "Field background",
            color_picker_value(theme_cfg.get("field_background"), "#f7f9fd"),
        )
        field_border_color = st.color_picker(
            "Field border",
            color_picker_value(theme_cfg.get("field_border"), "#d2dbe8"),
        )
        field_text_color = st.color_picker(
            "Field text",
            color_picker_value(theme_cfg.get("field_text"), "#143A66"),
        )
        for path, value in [
            (["theme", "section_background"], section_surface_color),
            (["theme", "field_background"], field_background_color),
            (["theme", "field_border"], field_border_color),
            (["theme", "field_text"], field_text_color),
        ]:
            changed = set_config_value(config, path, value)
            manual_theme_change |= changed
            config_changed |= changed

        if manual_theme_change:
            config_changed |= set_config_value(config, ["seasonal_theme"], "custom")

    with tabs[2]:
        st.markdown("**Typography**")
        heading_font = st.text_input("Heading font stack", typo_cfg.get("heading_font", "'Bebas Neue', sans-serif"))
        body_font = st.text_input("Body font stack", typo_cfg.get("body_font", "'Inter', sans-serif"))
        arabic_font = st.text_input("Arabic font stack", typo_cfg.get("arabic_font", "'Dubai', sans-serif"))
        config_changed |= set_config_value(config, ["typography", "heading_font"], heading_font)
        config_changed |= set_config_value(config, ["typography", "body_font"], body_font)
        config_changed |= set_config_value(config, ["typography", "arabic_font"], arabic_font)

        scale = st.selectbox(
            "Font scale",
            scale_options,
            index=option_index(scale_options, typo_cfg.get("scale", "default")),
            format_func=lambda x: x.title(),
        )
        config_changed |= set_config_value(config, ["typography", "scale"], scale)

        st.markdown("**Language & layout**")
        direction = st.selectbox(
            "Layout direction",
            direction_options,
            index=option_index(direction_options, language_cfg.get("direction", "ltr")),
            format_func=lambda x: x.upper(),
        )
        config_changed |= set_config_value(config, ["language", "direction"], direction)

        form_language = st.selectbox(
            "Form language mode",
            form_language_options,
            index=option_index(form_language_options, language_cfg.get("form_language", "bilingual")),
            format_func=lambda x: {
                "bilingual": "Bilingual",
                "english": "English only",
                "arabic": "Arabic only",
            }[x],
        )
        config_changed |= set_config_value(config, ["language", "form_language"], form_language)

    with tabs[3]:
        st.markdown("**Logo & Tagline**")
        show_logo = st.toggle("Show logo in hero", value=branding_cfg.get("show_logo", False))
        config_changed |= set_config_value(config, ["branding", "show_logo"], show_logo)

        if show_logo:
            if asset_images:
                logo_image = st.selectbox(
                    "Logo image",
                    asset_images,
                    index=option_index(asset_images, branding_cfg.get("logo_image") or default_hero_image),
                )
                config_changed |= set_config_value(config, ["branding", "logo_image"], logo_image)
            else:
                st.info("Upload sticker/logo images into assets/ to select them here.")

            uploaded_logo = st.file_uploader(
                "Upload logo image",
                type=[ext.lstrip(".") for ext in IMAGE_EXTENSIONS],
                key="logo_image_uploader",
                help="PNG/JPG/WEBP",
            )
            if uploaded_logo:
                saved_name = save_uploaded_asset(uploaded_logo, "logo")
                if saved_name:
                    config_changed |= set_config_value(config, ["branding", "logo_image"], saved_name)
                    st.success(f"Saved {uploaded_logo.name} to assets/{saved_name}")
                else:
                    st.error("Please upload PNG/JPG/WEBP files only.")

            if st.button("Delete logo image file", key="delete_logo_file"):
                current_img = config.get("branding", {}).get("logo_image")
                if delete_asset_file(current_img):
                    config_changed |= set_config_value(config, ["branding", "logo_image"], None)
                    st.success("Logo image removed from assets.")
                else:
                    st.info("No custom logo selected to delete.")

            logo_width = st.slider(
                "Logo width (px)",
                min_value=80,
                max_value=320,
                value=int(branding_cfg.get("logo_width", 140)),
            )
            config_changed |= set_config_value(config, ["branding", "logo_width"], logo_width)

        tagline_en = st.text_input("English tagline", branding_cfg.get("tagline_en", "SNOW LIWA"))
        tagline_ar = st.text_input("Arabic tagline", branding_cfg.get("tagline_ar", "ثلج ليوا"))
        config_changed |= set_config_value(config, ["branding", "tagline_en"], tagline_en)
        config_changed |= set_config_value(config, ["branding", "tagline_ar"], tagline_ar)

        st.markdown("**Social links**")
        whatsapp_number = st.text_input("WhatsApp number", social_cfg.get("whatsapp_number", "050 113 8781"))
        instagram_handle = st.text_input("Instagram handle", social_cfg.get("instagram_handle", "snowliwa"))
        instagram_url = st.text_input(
            "Instagram URL",
            social_cfg.get("instagram_url", f"https://instagram.com/{instagram_handle or 'snowliwa'}"),
        )
        whatsapp_message = st.text_input("WhatsApp greeting message", social_cfg.get("whatsapp_message", "Hi SNOW LIWA!"))
        show_whatsapp_button = st.toggle("Show WhatsApp button", value=social_cfg.get("show_whatsapp_button", True))
        show_whatsapp_qr = st.toggle("Show WhatsApp QR", value=social_cfg.get("show_whatsapp_qr", True))
        config_changed |= set_config_value(config, ["social", "whatsapp_number"], whatsapp_number)
        config_changed |= set_config_value(config, ["social", "instagram_handle"], instagram_handle)
        config_changed |= set_config_value(config, ["social", "instagram_url"], instagram_url)
        config_changed |= set_config_value(config, ["social", "whatsapp_message"], whatsapp_message)
        config_changed |= set_config_value(config, ["social", "show_whatsapp_button"], show_whatsapp_button)
        config_changed |= set_config_value(config, ["social", "show_whatsapp_qr"], show_whatsapp_qr)

        st.markdown("**Contact sticker collage**")
        collage_cfg = stickers_cfg.get("contact_collage", {})
        collage_enabled = st.toggle("Show sticker collage in Contact section", value=collage_cfg.get("enabled", False))
        config_changed |= set_config_value(config, ["stickers", "contact_collage", "enabled"], collage_enabled)
        if collage_enabled:
            if asset_images:
                collage_image = st.selectbox(
                    "Collage image",
                    asset_images,
                    index=option_index(asset_images, collage_cfg.get("image_name") or default_hero_image),
                )
                config_changed |= set_config_value(config, ["stickers", "contact_collage", "image_name"], collage_image)
            else:
                st.info("Upload sticker boards into assets/ to use them here.")

            uploaded_collage = st.file_uploader(
                "Upload collage image",
                type=[ext.lstrip(".") for ext in IMAGE_EXTENSIONS],
                key="collage_image_uploader",
                help="PNG/JPG/WEBP",
            )
            if uploaded_collage:
                saved_name = save_uploaded_asset(uploaded_collage, "collage")
                if saved_name:
                    config_changed |= set_config_value(config, ["stickers", "contact_collage", "image_name"], saved_name)
                    st.success(f"Saved {uploaded_collage.name} to assets/{saved_name}")
                else:
                    st.error("Please upload PNG/JPG/WEBP files only.")

            if st.button("Delete collage image file", key="delete_collage_file"):
                current_img = config.get("stickers", {}).get("contact_collage", {}).get("image_name")
                if delete_asset_file(current_img):
                    config_changed |= set_config_value(config, ["stickers", "contact_collage", "image_name"], None)
                    st.success("Collage image removed from assets.")
                else:
                    st.info("No collage image selected to delete.")

            collage_width = st.slider(
                "Collage width (px)",
                min_value=180,
                max_value=520,
                value=int(collage_cfg.get("width", 340)),
            )
            config_changed |= set_config_value(config, ["stickers", "contact_collage", "width"], collage_width)

        st.markdown("**Hero sticker pack**")
        hero_stickers_cfg = stickers_cfg.get("hero", {})
        hero_stickers_enabled = st.toggle("Enable hero sticker overlays", value=hero_stickers_cfg.get("enabled", True))
        config_changed |= set_config_value(config, ["stickers", "hero", "enabled"], hero_stickers_enabled)
        if hero_stickers_enabled:
            current_selection = hero_stickers_cfg.get("images", []) or []
            sticker_multiselect = st.multiselect(
                "Select up to 4 sticker images",
                asset_images,
                default=current_selection,
                help="Order determines placement",
            )
            cleaned_selection: list[str] = []
            for img in sticker_multiselect:
                if img not in cleaned_selection:
                    cleaned_selection.append(img)
            config_changed |= set_config_value(config, ["stickers", "hero", "images"], cleaned_selection[:4])

            uploaded_sticker = st.file_uploader(
                "Upload sticker image",
                type=[ext.lstrip(".") for ext in IMAGE_EXTENSIONS],
                key="hero_sticker_uploader",
            )
            if uploaded_sticker:
                saved_name = save_uploaded_asset(uploaded_sticker, "sticker")
                if saved_name:
                    updated_list = cleaned_selection + [saved_name]
                    deduped = []
                    for img in updated_list:
                        if img not in deduped:
                            deduped.append(img)
                    config_changed |= set_config_value(config, ["stickers", "hero", "images"], deduped[:4])
                    st.success(f"Saved {uploaded_sticker.name} to assets/{saved_name}")
                else:
                    st.error("Please upload PNG/JPG/WEBP files only.")

        st.markdown("**Section stickers**")
        section_labels = {"who": "Who we are", "experience": "Experience", "contact": "Contact"}
        position_options = ["top-left", "top-right", "bottom-left", "bottom-right"]
        for key, label in section_labels.items():
            cfg = stickers_cfg.get("sections", {}).get(key, {})
            with st.expander(f"{label} sticker", expanded=False):
                if asset_images:
                    options = ["(none)"] + asset_images
                    default_index = 0
                    if cfg.get("image") in asset_images:
                        default_index = asset_images.index(cfg.get("image")) + 1
                    selected = st.selectbox(
                        "Sticker image",
                        options,
                        index=default_index,
                        key=f"section_sticker_{key}",
                    )
                    image_value = None if selected == "(none)" else selected
                    config_changed |= set_config_value(config, ["stickers", "sections", key, "image"], image_value)
                else:
                    st.info("Upload sticker images into assets/ to use them.")

                uploaded_section_sticker = st.file_uploader(
                    f"Upload sticker for {label}",
                    type=[ext.lstrip(".") for ext in IMAGE_EXTENSIONS],
                    key=f"upload_sticker_{key}",
                )
                if uploaded_section_sticker:
                    saved_name = save_uploaded_asset(uploaded_section_sticker, f"{key}-sticker")
                    if saved_name:
                        config_changed |= set_config_value(config, ["stickers", "sections", key, "image"], saved_name)
                        st.success(f"Saved {uploaded_section_sticker.name} to assets/{saved_name}")
                    else:
                        st.error("Please upload PNG/JPG/WEBP files only.")

                if st.button(f"Delete {label} sticker file", key=f"delete_sticker_{key}"):
                    current_img = cfg.get("image")
                    if delete_asset_file(current_img):
                        config_changed |= set_config_value(config, ["stickers", "sections", key, "image"], None)
                        st.success("Sticker image removed from assets.")
                    else:
                        st.info("No sticker selected to delete.")

                position = st.selectbox(
                    "Position",
                    position_options,
                    index=option_index(position_options, cfg.get("position", "top-left")),
                    key=f"sticker_pos_{key}",
                )
                config_changed |= set_config_value(config, ["stickers", "sections", key, "position"], position)

                width = st.slider(
                    "Width (px)",
                    min_value=80,
                    max_value=360,
                    value=int(cfg.get("width", 180)),
                    key=f"sticker_width_{key}",
                )
                config_changed |= set_config_value(config, ["stickers", "sections", key, "width"], width)

                default_opacity = cfg.get("opacity", 0.18)
                slider_default = int(default_opacity * 100) if default_opacity <= 1 else int(default_opacity)
                opacity = st.slider(
                    "Opacity",
                    min_value=5,
                    max_value=100,
                    value=slider_default,
                    key=f"sticker_opacity_{key}",
                )
                config_changed |= set_config_value(config, ["stickers", "sections", key, "opacity"], opacity / 100)

        st.markdown("**Hero buttons**")
        hero_ctas = config.get("hero_cta", [])
        updated_ctas: list[dict[str, Any]] = []
        for idx in range(2):
            default_cta = hero_ctas[idx] if idx < len(hero_ctas) else {}
            col1, col2, col3 = st.columns([2, 3, 1])
            label = col1.text_input(f"CTA {idx+1} label", default_cta.get("label", ""), key=f"cta_label_{idx}")
            url = col2.text_input(f"CTA {idx+1} URL", default_cta.get("url", ""), key=f"cta_url_{idx}")
            style = col3.selectbox(
                "Style",
                ["primary", "secondary"],
                index=option_index(["primary", "secondary"], default_cta.get("style", "primary")),
                key=f"cta_style_{idx}",
            )
            if label and url:
                updated_ctas.append({"label": label, "url": url, "style": style})
        config_changed |= set_config_value(config, ["hero_cta"], updated_ctas)

        st.markdown("**Background music**")
        audio_cfg = config.get("audio", {})
        audio_enabled = st.toggle("Play background music", value=audio_cfg.get("enabled", True))
        config_changed |= set_config_value(config, ["audio", "enabled"], audio_enabled)
        audio_file = st.file_uploader(
            "Upload MP3/WAV",
            type=[ext.lstrip(".") for ext in AUDIO_EXTENSIONS],
            key="audio_file_uploader",
        )
        if audio_file:
            saved_name = save_uploaded_asset(audio_file, "audio", AUDIO_EXTENSIONS)
            if saved_name:
                config_changed |= set_config_value(config, ["audio", "file_name"], saved_name)
                st.success(f"Saved {audio_file.name} to assets/{saved_name}")
            else:
                st.error("Upload MP3/WAV/M4A files only.")

        if st.button("Delete audio file", key="delete_audio_file"):
            current_audio = audio_cfg.get("file_name")
            if delete_asset_file(current_audio):
                config_changed |= set_config_value(config, ["audio", "file_name"], None)
                st.success("Audio file removed from assets.")
            else:
                st.info("No custom audio file to delete.")

    with tabs[4]:
        st.markdown("**Navigation labels**")
        nav_fields = [
            ("name", "Name"),
            ("about", "About"),
            ("activities", "Activities"),
            ("invites", "Invites"),
            ("contact", "Contact"),
        ]
        nav_cfg = content_cfg.get("nav", {})
        nav_cols = st.columns(len(nav_fields))
        for (key, label), col in zip(nav_fields, nav_cols):
            value = col.text_input(label.upper(), nav_cfg.get(key, label.upper()))
            config_changed |= set_config_value(config, ["content", "nav", key], value)

        st.markdown("**Card content**")
        card_labels = [
            ("activities", "Activities"),
            ("events", "Events"),
            ("contact", "Contact"),
        ]
        for card_key, card_label in card_labels:
            card_cfg = content_cfg.get("cards", {}).get(card_key, {})
            st.write(f"_{card_label}_")
            title = st.text_input(f"{card_label} title", card_cfg.get("title", card_label.upper()), key=f"card_title_{card_key}")
            desc = st.text_area(
                f"{card_label} description",
                card_cfg.get("description", ""),
                key=f"card_desc_{card_key}",
            )
            config_changed |= set_config_value(config, ["content", "cards", card_key, "title"], title)
            config_changed |= set_config_value(config, ["content", "cards", card_key, "description"], desc)

        st.markdown("**Booking section copy**")
        booking_cfg_local = content_cfg.get("booking", {})
        booking_title = st.text_input("Section title", booking_cfg_local.get("title", "🎟️ Book your ticket"))
        price_text = st.text_input("Price text (display only)", booking_cfg_local.get("price_text", "Entrance ticket: 175 AED per person."))
        button_text = st.text_input("Payment button label", booking_cfg_local.get("button_text", "Proceed to payment with Ziina"))
        config_changed |= set_config_value(config, ["content", "booking", "title"], booking_title)
        config_changed |= set_config_value(config, ["content", "booking", "price_text"], price_text)
        config_changed |= set_config_value(config, ["content", "booking", "button_text"], button_text)

    with tabs[5]:
        st.markdown("**Hero emojis**")
        icons_enabled = st.toggle("Show floating emojis", value=icons_cfg.get("enabled", True))
        config_changed |= set_config_value(config, ["icons", "enabled"], icons_enabled)

        icon_size = st.selectbox(
            "Emoji size",
            icon_size_options,
            index=option_index(icon_size_options, icons_cfg.get("size", "medium")),
            format_func=lambda x: x.title(),
        )
        config_changed |= set_config_value(config, ["icons", "size"], icon_size)

        icon_animation = st.selectbox(
            "Emoji animation",
            icon_animation_options,
            index=option_index(icon_animation_options, icons_cfg.get("animation", "medium")),
            format_func=lambda x: {
                "none": "No animation",
                "slow": "Float · Slow",
                "medium": "Float · Medium",
                "fast": "Float · Fast",
            }[x],
        )
        config_changed |= set_config_value(config, ["icons", "animation"], icon_animation)

        st.markdown("**Form layout**")
        show_notes = st.toggle("Display notes field", value=form_cfg.get("show_notes", True))
        config_changed |= set_config_value(config, ["form", "show_notes"], show_notes)

        label_position = st.selectbox(
            "Label position",
            label_position_options,
            index=option_index(label_position_options, form_cfg.get("label_position", "top")),
            format_func=lambda x: "Placeholder" if x == "placeholder" else "Above field",
        )
        config_changed |= set_config_value(config, ["form", "label_position"], label_position)

        button_width = st.selectbox(
            "Button width",
            button_width_options,
            index=option_index(button_width_options, form_cfg.get("button_width", "auto")),
            format_func=lambda x: "Full width" if x == "full" else "Auto",
        )
        config_changed |= set_config_value(config, ["form", "button_width"], button_width)

        show_icon = st.toggle("Show ticket emoji on button", value=form_cfg.get("show_ticket_icon", True))
        config_changed |= set_config_value(config, ["form", "show_ticket_icon"], show_icon)

        success_msg = st.text_area(
            "Success message after form submission",
            form_cfg.get("success_message", ""),
        )
        config_changed |= set_config_value(config, ["form", "success_message"], success_msg)

    with tabs[6]:
        st.markdown("**Snow overlay**")
        snow_cfg = effects_cfg.get("snow", {})
        snow_enabled = st.toggle("Enable snow animation", value=snow_cfg.get("enabled", True))
        config_changed |= set_config_value(config, ["effects", "snow", "enabled"], snow_enabled)

        flakes = st.slider(
            "Number of flakes",
            min_value=0,
            max_value=80,
            value=int(snow_cfg.get("flakes", 36)),
        )
        config_changed |= set_config_value(config, ["effects", "snow", "flakes"], flakes)

        snow_size = st.selectbox(
            "Flake size",
            ["small", "medium", "large"],
            index=option_index(["small", "medium", "large"], snow_cfg.get("size", "medium")),
            format_func=lambda x: x.title(),
        )
        config_changed |= set_config_value(config, ["effects", "snow", "size"], snow_size)

        snow_speed = st.selectbox(
            "Fall speed",
            ["slow", "medium", "fast"],
            index=option_index(["slow", "medium", "fast"], snow_cfg.get("speed", "medium")),
            format_func=lambda x: x.title(),
        )
        config_changed |= set_config_value(config, ["effects", "snow", "speed"], snow_speed)

        snow_symbol_options = ["sparkle", "flake", "dot", "emoji"]
        snow_symbol_labels = {
            "sparkle": "Sparkle ✦",
            "flake": "Classic snow ❄️",
            "dot": "Soft dots •",
            "emoji": "Cloud emoji 🌨️",
        }
        snow_symbol = st.selectbox(
            "Snow style",
            snow_symbol_options,
            index=option_index(snow_symbol_options, snow_cfg.get("symbol", "sparkle")),
            format_func=lambda k: snow_symbol_labels.get(k, k),
        )
        config_changed |= set_config_value(config, ["effects", "snow", "symbol"], snow_symbol)

    with tabs[7]:
        st.markdown("**Access**")
        st.caption("PIN is stored in data/ui_config.json. Consider using Streamlit secrets in production.")
        admin_pin = st.text_input(
            "Admin PIN",
            value=security_cfg.get("admin_pin", "1234"),
            type="password",
        )
        config_changed |= set_config_value(config, ["security", "admin_pin"], admin_pin)

        if st.button("Lock settings"):
            st.session_state["settings_unlocked"] = False
            st.session_state["settings_panel_visible"] = False
            st.success("Settings locked.")

    if config_changed:
        save_ui_config(config)
        st.toast("UI config updated.")
        rerun_app()


def main():
    init_state()
    ensure_data_file()
    ensure_ui_config()
    config = load_ui_config()

    apply_background(config)
    inject_base_css(config)
    render_snow_overlay(config)
    if config.get("audio", {}).get("enabled", True):
        render_background_music(config.get("audio", {}).get("file_name", "babanuail.mp3"))
    render_admin_toggle()
    if st.session_state.get("settings_unlocked") and st.session_state.get("settings_panel_visible"):
        render_futuristic_panel_fx()

    if st.session_state.get("settings_panel_visible"):
        with st.container():
            if st.session_state.get("settings_unlocked"):
                render_settings_panel(config)
            else:
                render_pin_prompt(config)

    direction_attr = config.get("language", {}).get("direction", "ltr")

    query = get_query_params()
    result_param = _normalize_query_value(
        query.get("result")) if query else None
    pi_id_param = _normalize_query_value(query.get("pi_id")) if query else None

    # If coming back from Ziina with pi_id -> show payment result
    if result_param and pi_id_param:
        st.markdown(
            f'<div class="page-container" dir="{direction_attr}"><div class="page-card">',
            unsafe_allow_html=True,
        )
        render_payment_result(result_param, pi_id_param)
        st.markdown("</div></div>", unsafe_allow_html=True)
        return

    # Navigation
    page = st.sidebar.selectbox("Navigate", list(PAGES.keys()))
    st.session_state.page = PAGES[page]

    st.markdown(
        f'<div class="page-container" dir="{direction_attr}"><div class="page-card">',
        unsafe_allow_html=True,
    )

    if st.session_state.page == "welcome":
        render_welcome(config)
        st.markdown("<hr>", unsafe_allow_html=True)
        render_who_we_are(config)
        st.markdown("<hr>", unsafe_allow_html=True)
        render_experience(config)
        st.markdown("<hr>", unsafe_allow_html=True)
        render_contact(config)
        st.markdown("<hr>", unsafe_allow_html=True)
    elif st.session_state.page == "who":
        render_who_we_are(config)
    elif st.session_state.page == "experience":
        render_experience(config)
    elif st.session_state.page == "contact":
        render_contact(config)

    st.markdown("</div></div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
