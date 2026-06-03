```python
"""
================================================================================
SLEEP CALM - LOGISTICS ENTERPRISE
Sistema Corporativo de Monitoreo de Entregas
Versión: 10.3 - Español Completo
================================================================================
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# =============================================================================
# 1. CONSTANTES GLOBALES
# =============================================================================

META_SLA: float = 96.0

SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1QaRY5wlCMItP0Ulwfqp5PgJQvANh4hKVlozlWX2Od0c"
    "/export?format=csv&gid=970113433"
)

REQUIRED_COLS = {"fecha", "estado", "On Time"}

STATUS_COMPLETED = "wc-completed"
STATUS_PROCESSING = "wc-processing"
STATUS_SHIPPED = "wc-despachado"
STATUS_ON_HOLD = "wc-on-hold"
STATUS_CANCELLED = "wc-cancelled"

COLOR_PRIMARY = "#2563eb"
COLOR_SUCCESS = "#10b981"
COLOR_WARNING = "#f59e0b"
COLOR_DANGER = "#ef4444"
COLOR_NEUTRAL = "#64748b"
COLOR_CYAN = "#06b6d4"

BG_CARD = "#1e293b"
BG_APP = "#0f172a"
GRID_COLOR = "#334155"

MESES_NOMBRES = [
    "Ene", "Feb", "Mar", "Abr", "May", "Jun",
    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"
]

# =============================================================================
# 2. SISTEMA DE TRADUCCIÓN
# =============================================================================

_TEXTS = {
    "title": {"es": "Sleep Calm - Logistics Enterprise"},
    "subtitle": {"es": "Sistema Corporativo de Monitoreo de Entregas"},
    "period": {"es": "Período"},
    "meta_sla": {"es": "Meta SLA"},
    "total_orders": {"es": "TOTAL PEDIDOS"},
    "sla": {"es": "SLA"},
    "on_time": {"es": "ENTREGAS A TIEMPO"},
    "delayed": {"es": "ATRASADOS"},
    "in_process": {"es": "EN PROCESO"},
    "shipped": {"es": "DESPACHADOS"},
    "not_delivered": {"es": "NO ENTREGADOS"},
    "chart_sla_monthly": {"es": "SLA por Mes - Comparativo Anual"},
    "chart_sla_trend": {"es": "Tendencia del SLA"},
    "chart_sla_carrier": {"es": "SLA por Transportadora"},
    "chart_comparison": {"es": "A Tiempo vs Atrasado por Transportadora"},
    "chart_sla_state": {"es": "SLA por Estado (UF)"},
    "chart_top_skus": {"es": "Top 10 SKUs Más Vendidos"},
    "chart_status": {"es": "Distribución de Estados"},
    "chart_delay_dist": {"es": "Distribución de Días de Retraso"},
    "chart_aging": {"es": "Aging de Pedidos Abiertos"},
    "chart_avg_time": {"es": "Tiempo Promedio de Entrega por Transportadora"},
    "critical_orders": {"es": "Pedidos Críticos (No Entregados)"},
    "no_pending": {"es": "¡Ningún pedido pendiente de entrega!"},
    "filters": {"es": "Filtros"},
    "year": {"es": "Año"},
    "month": {"es": "Mes"},
    "all": {"es": "Todos"},
    "compare": {"es": "Comparar con año anterior"},
    "carrier": {"es": "Transportadora"},
    "state": {"es": "Estado"},
    "returns": {"es": "Devolución"},
    "how_sla": {"es": "¿Cómo se calcula el SLA?"},
    "sla_formula": {
        "es": "SLA = (Entregas a Tiempo / Total de Entregas) x 100"
    },
    "sla_note": {
        "es": "Solo pedidos con estado 'wc-completed' son considerados"
    },
    "footer": {"es": "Sleep Calm - Logistics Enterprise"},
    "updated": {"es": "Actualizado"},
    "data_warnings": {"es": "Alertas de Calidad de Datos"},
    "avg_delivery_days": {"es": "Tiempo Promedio de Entrega"},
    "days": {"es": "días"},
    "ranking_carrier": {"es": "Ranking de Transportadoras"},
    "on_hold": {"es": "EN ESPERA"},
}


def t(key):
    return _TEXTS.get(key, {}).get("es", key)


# =============================================================================
# 3. CONFIGURACIÓN DE PÁGINA
# =============================================================================

st.set_page_config(
    page_title="Sleep Calm - Logistics",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

if "language" not in st.session_state:
    st.session_state.language = "es"

# =============================================================================
# 4. ESTILOS CSS
# =============================================================================

st.markdown(f"""
<style>

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, .stApp {{
    background: {BG_APP};
    font-family: 'Inter', sans-serif;
}}

[data-testid="stSidebar"] {{
    background: {BG_APP};
    border-right: 1px solid {GRID_COLOR};
}}

.sc-header {{
    background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 50%, #1e40af 100%);
    border-radius: 16px;
    padding: 1.4rem 2rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 8px 32px rgba(37,99,235,0.3);
}}

.sc-header h1 {{
    color: white;
    margin: 0;
    font-size: 1.5rem;
    font-weight: 700;
}}

.sc-header p {{
    color: rgba(255,255,255,0.75);
    margin: 0.3rem 0 0;
    font-size: 0.8rem;
}}

.kpi-card {{
    background: linear-gradient(145deg, #1e293b 0%, #162032 100%);
    border-radius: 16px;
    padding: 1.1rem 1.3rem;
    margin-bottom: 0.8rem;
    border-left: 4px solid {COLOR_PRIMARY};
    transition: transform 0.2s, box-shadow 0.2s;
    box-shadow: 0 2px 8px rgba(0,0,0,0.25);
}}

.kpi-card:hover {{
    transform: translateY(-3px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.4);
}}

.kpi-value {{
    font-size: 2rem;
    font-weight: 700;
    color: white;
    line-height: 1.2;
}}

.kpi-label {{
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: #94a3b8;
}}

.kpi-detail {{
    font-size: 0.7rem;
    color: #64748b;
    margin-top: 0.4rem;
}}

.section-title {{
    font-size: 1rem;
    font-weight: 600;
    margin: 1.5rem 0 0.8rem;
    padding-left: 0.9rem;
    border-left: 4px solid {COLOR_PRIMARY};
    color: white;
}}

.alert-badge {{
    background: rgba(239,68,68,0.15);
    border: 1px solid {COLOR_DANGER};
    border-radius: 10px;
    padding: 0.6rem 1rem;
    margin-bottom: 0.6rem;
    font-size: 0.8rem;
    color: #fca5a5;
}}

.warn-badge {{
    background: rgba(245,158,11,0.15);
    border: 1px solid {COLOR_WARNING};
    border-radius: 10px;
    padding: 0.6rem 1rem;
    margin-bottom: 0.6rem;
    font-size: 0.8rem;
    color: #fde68a;
}}

footer {{
    visibility: hidden;
}}

#MainMenu {{
    visibility: hidden;
}}

.stButton > button {{
    border-radius: 10px;
    font-weight: 500;
}}

</style>
""", unsafe_allow_html=True)

# =============================================================================
# 5. FUNCIONES DE DATOS
# =============================================================================

def normalize_ontime(series):
    s = series.astype(str).str.strip().str.lower()

    result = pd.Series("unknown", index=series.index)

    result[s == "on time"] = "On Time"
    result[s == "no ontime"] = "No ontime"

    result[
        series.isna() |
        (s == "nan") |
        (s == "none") |
        (s == "")
    ] = np.nan

    return result


def parse_dates(df):
    for col in ["fecha", "Compromiso de entrega"]:
        if col in df.columns:
            df[col] = pd.to_datetime(
                df[col],
                errors="coerce",
                dayfirst=True
            )

    return df


@st.cache_data(ttl=300, show_spinner="Cargando datos...")
def load_data():

    audit = {
        "warnings": [],
        "duplicates_removed": 0
    }

    try:
        df = pd.read_csv(SHEET_URL)

    except Exception as e:
        st.error(f"Error al cargar la planilla: {e}")
        return pd.DataFrame(), audit

    df = parse_dates(df)

    if "On Time" in df.columns:
        df["On Time"] = normalize_ontime(df["On Time"])

    if "numero_pedido" in df.columns:

        before = len(df)

        df = df.drop_duplicates(
            subset=["numero_pedido"],
            keep="last"
        )

        removed = before - len(df)

        if removed:
            audit["duplicates_removed"] = removed
            audit["warnings"].append(
                f"{removed} pedido(s) duplicado(s) removido(s)."
            )

    df["ano"] = df["fecha"].dt.year
    df["mes"] = df["fecha"].dt.month
    df["mes_nome"] = df["fecha"].dt.strftime("%b")

    if "Compromiso de entrega" in df.columns:
        df["dias_ate_entrega"] = (
            df["Compromiso de entrega"] - df["fecha"]
        ).dt.days

    return df, audit

# =============================================================================
# 6. CARGAR DATOS
# =============================================================================

df_raw, audit_log = load_data()

if df_raw.empty:
    st.error(
        "No fue posible cargar los datos. Verifique la conexión."
    )
    st.stop()

hoje = datetime.now()

# =============================================================================
# 7. SIDEBAR
# =============================================================================

with st.sidebar:

    st.markdown("""
    <div style="text-align:center;padding:1rem 0 0.5rem">
      <div style="font-size:2.8rem">📦</div>
      <div style="font-weight:700;font-size:1.1rem;color:white">
        Sleep Calm
      </div>
      <div style="font-size:0.7rem;color:#64748b">
        Logistics Enterprise v10.3
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("### Filtros")

    anos_disp = sorted(
        df_raw["ano"].dropna().unique().astype(int)
    )

    ano_sel = st.selectbox(
        "Año",
        anos_disp,
        index=len(anos_disp) - 1
    )

    meses_disp = ["Todos"] + MESES_NOMBRES

    mes_sel = st.selectbox(
        "Mes",
        meses_disp,
        index=0
    )

    comparar = st.checkbox(
        "Comparar con año anterior",
        value=True
    )

    st.markdown("---")

    ufs_disp = sorted(
        df_raw["UF"].dropna().unique()
    ) if "UF" in df_raw.columns else []

    transp_disp = sorted(
        df_raw["Proveedor"].dropna().unique()
    ) if "Proveedor" in df_raw.columns else []

    ufs_sel = st.multiselect(
        "Estado",
        ufs_disp,
        placeholder="Todos"
    )

    transp_sel = st.multiselect(
        "Transportadora",
        transp_disp,
        placeholder="Todas"
    )

    st.markdown("---")

    st.link_button(
        "Registrar Devolución",
        "https://script.google.com/a/macros/sleepcalm.com.br/s/AKfycbzyOsb6FzdRee9Mn88h86fPx7B7ZmZoxNZLP-brNgUZr9-BRFhW3Dt49_QeRe59Mhg6yg/exec",
        use_container_width=True
    )

# =============================================================================
# 8. HEADER
# =============================================================================

periodo_txt = (
    f"{mes_sel} de {ano_sel}"
    if mes_sel != "Todos"
    else f"Año {ano_sel}"
)

st.markdown(f"""
<div class="sc-header">
  <div style="display:flex;justify-content:space-between;align-items:center">

    <div>
      <h1>📦 Sleep Calm - Logistics Enterprise</h1>

      <p>
      Sistema Corporativo de Monitoreo de Entregas |
      Período: <strong>{periodo_txt}</strong> |
      Meta SLA: <strong>{META_SLA}%</strong>
      </p>
    </div>

    <div style="
        font-size:0.7rem;
        background:rgba(255,255,255,0.15);
        padding:0.4rem 1rem;
        border-radius:20px;
        color:white">

        v10.3

    </div>

  </div>
</div>
""", unsafe_allow_html=True)

# =============================================================================
# 9. KPI EXAMPLE
# =============================================================================

st.markdown(
    '<div class="section-title">Dashboard Operacional</div>',
    unsafe_allow_html=True
)

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">TOTAL PEDIDOS</div>
        <div class="kpi-value">{len(df_raw):,}</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">EN PROCESO</div>
        <div class="kpi-value">
            {(df_raw["estado"] == STATUS_PROCESSING).sum()}
        </div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">DESPACHADOS</div>
        <div class="kpi-value">
            {(df_raw["estado"] == STATUS_SHIPPED).sum()}
        </div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">EN ESPERA</div>
        <div class="kpi-value">
            {(df_raw["estado"] == STATUS_ON_HOLD).sum()}
        </div>
    </div>
    """, unsafe_allow_html=True)

# =============================================================================
# 10. FOOTER
# =============================================================================

st.markdown(f"""
<div style="
    text-align:center;
    padding:1.5rem 0 0.5rem;
    color:#64748b;
    font-size:0.7rem;
    border-top:1px solid {GRID_COLOR};
    margin-top:1.5rem">

  Sleep Calm - Logistics Enterprise |
  Meta SLA: {META_SLA}% |
  Actualizado: {hoje.strftime('%d/%m/%Y %H:%M')}

</div>
""", unsafe_allow_html=True)
```
