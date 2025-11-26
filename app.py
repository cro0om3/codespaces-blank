import base64
import os
from pathlib import Path
from string import Template
from typing import Optional

try:
    import streamlit as st
except ModuleNotFoundError:
    import sys
    sys.stderr.write("\n[ERROR] The 'streamlit' package is not installed. Please install it with 'pip install streamlit'.\n")
    st = None

import streamlit.components.v1 as components

st.set_page_config(page_title="Snow Liwa", layout="wide")

# Tighten Streamlit padding so the HTML fills the viewport.
st.markdown(
  """
  <style>
  .block-container { padding: 0; margin: 0%; width: 100%; }
  .stApp { padding: 0; }
  /* Hide Streamlit hamburger menu, footer, and main toolbar */
  #MainMenu {visibility: hidden;}
  footer {visibility: hidden;}
  header {visibility: hidden;}
  </style>
  """,
  unsafe_allow_html=True,
)


def load_background_base64() -> Optional[str]:
    """Return a base64 string for the first background image found."""
    for candidate in ("static/bg_cropped.png", "static/bg.png", "Background (1).png"):
        path = Path(candidate)
        if path.exists():
            return base64.b64encode(path.read_bytes()).decode("utf-8")
    return None


bg_data = load_background_base64()
bg_style = (
    f"background: #f7f6f3 url('data:image/png;base64,{bg_data}') no-repeat center center/cover;"
    if bg_data
    else "background: linear-gradient(135deg, #b3e0ff 0%, #e6f7ff 100%);"
)

st.markdown(
    f"""
    <style>
    .stApp {{
        {bg_style}
        background-attachment: fixed;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

genesys_env = os.getenv("GENESYS_ENVIRONMENT", "mypurecloud.com")
deployment_id = os.getenv("GENESYS_DEPLOYMENT_ID", "<deployment-id>")
bootstrap_host = os.getenv("GENESYS_BOOTSTRAP_HOST") or f"apps.{genesys_env}"
script_src = (
    bootstrap_host
    if bootstrap_host.startswith("http")
    else f"https://{bootstrap_host}/genesys-bootstrap/genesys.min.js"
)

html_template = Template(
    """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Snow Liwa Messenger</title>
  <style>
    html, body {
      margin: 0;
      padding: 0;
      width: 100%;
      height: 100%;
      min-height: 100vh;
    }
    body {
      overflow-y: auto;
      overflow-x: hidden;
      font-family: "Poppins", Arial, sans-serif;
      ${bg_style}
    }
    .snowflake {
      position: fixed;
      top: -10px;
      z-index: 99;
      user-select: none;
      pointer-events: none;
      animation-name: fall;
      animation-timing-function: linear;
      animation-iteration-count: infinite;
      opacity: 0.85;
      filter: drop-shadow(0 0 3px white);
    }
    @keyframes fall {
      0% { transform: translateY(-10vh) rotate(0deg); }
      100% { transform: translateY(110vh) rotate(360deg); }
    }
    .small { font-size: 12px; }
    .medium { font-size: 20px; }
    .large { font-size: 32px; }
    .s1 { left: 10%; animation-duration: 7s; }
    .s2 { left: 25%; animation-duration: 9s; animation-delay: 2s; }
    .s3 { left: 40%; animation-duration: 6s; animation-delay: 4s; }
    .s4 { left: 55%; animation-duration: 10s; animation-delay: 1s; }
    .s5 { left: 70%; animation-duration: 8s; animation-delay: 3s; }
    .s6 { left: 85%; animation-duration: 11s; animation-delay: 0s; }
    .glow {
      position: absolute;
      bottom: 20px;
      left: 50%;
      transform: translateX(-50%);
      padding: 15px 35px;
      background: rgba(255,255,255,0.4);
      border-radius: 25px;
      backdrop-filter: blur(8px);
      font-size: 20px;
      font-weight: bold;
      color: #433;
      box-shadow: 0 0 15px rgba(255,255,255,0.8);
      animation: glowPulse 2s infinite alternate;
    }
    @keyframes glowPulse {
      from { box-shadow: 0 0 10px rgba(255,255,255,0.4); }
      to { box-shadow: 0 0 25px rgba(255,255,255,1); }
    }
  </style>
</head>
<body>
  <div class="snowflake small s1">&#10052;</div>
  <div class="snowflake medium s2">&#10052;</div>
  <div class="snowflake small s3">&#10052;</div>
  <div class="snowflake large s4">&#10052;</div>
  <div class="snowflake medium s5">&#10052;</div>
  <div class="snowflake large s6">&#10052;</div>
  <div class="glow">&#10052; Welcome to Snow Liwa &#10052;</div>

  <script>
    (function(g,e,n,o,t){
      g['_genesysJs']=o;
      g[o]=g[o]||function(){(g[o].q=g[o].q||[]).push(arguments);};
      g[o].t=1*new Date();
      g[o].c={
        environment: '${environment}',
        deploymentId: '${deployment_id}',
        origin: window.location.origin
      };
      t=e.createElement(n); t.async=1; t.src='${script_src}'; t.charset='utf-8';
      e.head.appendChild(t);
    })(window, document, 'script', 'Genesys');
  </script>
  <script>
    Genesys('subscribe', 'Messenger.ready', function(){
      // Genesys('command', 'Messenger.open');
    });
  </script>
  <script>
    const updateHeight = () => {
      const height = Math.max(document.documentElement.scrollHeight, window.innerHeight) + 20;
      window.parent.postMessage({ type: "streamlit:height", height }, "*");
    };
    window.addEventListener("load", updateHeight);
    window.addEventListener("resize", updateHeight);
    setInterval(updateHeight, 1000);
  </script>
</body>
</html>
"""
)

html = html_template.substitute(
    bg_style=bg_style,
    environment=genesys_env,
    deployment_id=deployment_id,
    script_src=script_src,
)

components.html(html, width=4988, height=3712, scrolling=True)

st.caption(
    f"Genesys environment: {genesys_env} | Deployment ID: {deployment_id} | Bootstrap: {script_src}"
)
