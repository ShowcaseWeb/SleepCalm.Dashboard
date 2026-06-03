"""
================================================================================
SLEEP CALM - LOGISTICS ENTERPRISE
Sistema Corporativo de Monitoreo de Entregas
Versión: 10.3 - Totalmente en Español
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

STATUS_COMPLETED  = "wc-completed"
STATUS_PROCESSING = "wc-processing"
STATUS_SHIPPED    = "wc-despachado"
STATUS_ON_HOLD    = "wc-on-hold"
STATUS_CANCELLED  = "wc-cancelled"

COLOR_PRIMARY   = "#2563eb"
COLOR_SUCCESS   = "#10b981"
COLOR_WARNING   = "#f59e0b"
COLOR_DANGER    = "#ef4444"
COLOR_NEUTRAL   = "#64748b"
COLOR_CYAN      = "#06b6d4"
BG_CARD         = "#1e293b"
BG_APP          = "#0f172a"
GRID_COLOR      = "#334155"

MESES_NOMBRES = ["Ene","Feb","Mar","Abr","May","Jun",
                 "Jul","Ago","Sep","Oct","Nov","Dic"]

# =============================================================================
# 2. TEXTOS EN ESPAÑOL
# =============================================================================

TEXTO = {
    "title":              "Sleep Calm - Logistics Enterprise",
    "subtitle":           "Sistema Corporativo de Monitoreo de Entregas",
    "period":             "Período",
    "meta_sla":           "Meta SLA",
    "total_orders":       "TOTAL PEDIDOS",
    "sla":                "SLA",
    "on_time":            "ENTREGAS A TIEMPO",
    "delayed":            "ATRASADOS",
    "in_process":         "EN PROCESO",
    "shipped":            "DESPACHADOS",
    "not_delivered":      "NO ENTREGADOS",
    "chart_sla_monthly":  "SLA por Mes - Comparativo Anual",
    "chart_sla_trend":    "Tendencia del SLA",
    "chart_sla_carrier":  "SLA por Transportadora",
    "chart_comparison":   "A Tiempo vs Atrasado por Transportadora",
    "chart_sla_state":    "SLA por Estado (UF)",
    "chart_top_skus":     "Top 10 SKUs Más Vendidos",
    "chart_status":       "Distribución de Estados",
    "chart_delay_dist":   "Distribución de Días de Atraso",
    "chart_aging":        "Aging de Pedidos Abiertos",
    "chart_avg_time":     "Tiempo Promedio de Entrega por Transportadora",
    "critical_orders":    "Pedidos Críticos (No Entregados)",
    "no_pending":         "¡Ningún pedido pendiente de entrega!",
    "filters":            "Filtros",
    "year":               "Año",
    "month":              "Mes",
    "all":                "Todos",
    "compare":            "Comparar con año anterior",
    "carrier":            "Transportadora",
    "state":              "Estado (UF)",
    "returns":            "Devolución",
    "how_sla":            "¿Cómo se calcula el SLA?",
    "sla_formula":        "SLA = (Entregas a Tiempo / Total Entregas) x 100",
    "sla_note":           "Solo pedidos con estado 'wc-completed' son considerados",
    "footer":             "Sleep Calm - Logistics Enterprise",
    "updated":            "Actualizado",
    "data_warnings":      "Alertas de Calidad de Datos",
    "avg_delivery_days":  "Tiempo Promedio de Entrega",
    "days":               "días",
    "ranking_carrier":    "Ranking de Transportadoras",
    "on_hold":            "EN ESPERA",
}

# =============================================================================
# 3. CAPA DE DATOS
# =============================================================================

def _normalize_ontime(series):
    s = series.astype(str).str.strip().str.lower()
    result = pd.Series("unknown", index=series.index)
    result[s == "on time"]   = "On Time"
    result[s == "no ontime"] = "No ontime"
    result[series.isna() | (s == "nan") | (s == "none") | (s == "")] = np.nan
    return result

def _parse_dates(df):
    for col in ["fecha", "Compromiso de entrega"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
    return df

def _validate_columns(df):
    return [c for c in REQUIRED_COLS if c not in df.columns]

@st.cache_data(ttl=300, show_spinner="Cargando datos...")
def load_data():
    audit = {"warnings": [], "duplicates_removed": 0, "invalid_ontime": 0}

    try:
        df = pd.read_csv(SHEET_URL)
    except Exception as e:
        st.error(f"Error al cargar planilla: {e}")
        return pd.DataFrame(), audit

    missing = _validate_columns(df)
    if missing:
        audit["warnings"].append(f"Columnas ausentes: {missing}")

    df = _parse_dates(df)

    if "On Time" in df.columns:
        original_ontime = df["On Time"].copy()
        df["On Time"] = _normalize_ontime(df["On Time"])
        invalid_count = int((df["On Time"].isna() & original_ontime.notna()).sum())
        if invalid_count:
            audit["warnings"].append(f"{invalid_count} valor(es) inválido(s) en 'On Time' fueron ignorados.")

    if "numero_pedido" in df.columns:
        before = len(df)
        df = df.drop_duplicates(subset=["numero_pedido"], keep="last")
        removed = before - len(df)
        if removed:
            audit["duplicates_removed"] = removed
            audit["warnings"].append(f"{removed} pedido(s) duplicado(s) eliminado(s).")

    df["ano"] = df["fecha"].dt.year
    df["mes"] = df["fecha"].dt.month
    df["mes_nombre"] = df["fecha"].dt.strftime("%b")

    if "Compromiso de entrega" in df.columns:
        df["dias_hasta_entrega"] = (df["Compromiso de entrega"] - df["fecha"]).dt.days

    return df, audit

# =============================================================================
# 4. CAPA DE MÉTRICAS
# =============================================================================

def calcular_sla(df_):
    resultado = {"sla": 0.0, "a_tiempo": 0, "total_entregas": 0, "atrasados": 0, "valido": False, "alerta": None}

    if df_.empty or "estado" not in df_.columns:
        return resultado

    entregas = df_[df_["estado"] == STATUS_COMPLETED].copy()
    total = len(entregas)

    if total == 0:
        return resultado

    a_tiempo = int((entregas["On Time"] == "On Time").sum())
    atrasados = int((entregas["On Time"] == "No ontime").sum())

    sin_clasificar = total - a_tiempo - atrasados
    if sin_clasificar > 0:
        resultado["alerta"] = f"{sin_clasificar} entrega(s) sin clasificación en 'On Time'."

    sla = round(a_tiempo / total * 100, 2)

    if sla > 100:
        resultado["alerta"] = f"SLA inválido: {sla}% > 100%."
        sla = 100.0
    if sla < 0:
        resultado["alerta"] = f"SLA inválido: {sla}% < 0%."
        sla = 0.0

    resultado.update({"sla": sla, "a_tiempo": a_tiempo, "total_entregas": total, "atrasados": atrasados, "valido": True})
    return resultado

def calcular_sla_mensual(df_, ano, ufs=None, transportadoras=None):
    mask = df_["ano"] == ano
    if ufs:
        mask &= df_["UF"].isin(ufs)
    if transportadoras:
        mask &= df_["Proveedor"].isin(transportadoras)

    sub = df_[mask & (df_["estado"] == STATUS_COMPLETED)].copy()
    if sub.empty:
        return pd.Series(0.0, index=range(1, 13))

    grp = sub.groupby("mes").apply(lambda g: (g["On Time"] == "On Time").sum() / len(g) * 100 if len(g) > 0 else 0.0)
    return grp.reindex(range(1, 13), fill_value=0.0)

def calcular_sla_por_grupo(df_, columna):
    if df_.empty or columna not in df_.columns:
        return pd.DataFrame()

    entregas = df_[df_["estado"] == STATUS_COMPLETED].copy()
    if entregas.empty:
        return pd.DataFrame()

    grp = entregas.groupby(columna).agg(
        Entregas = ("On Time", "count"),
        ATiempo  = ("On Time", lambda x: (x == "On Time").sum()),
        Atrasados = ("On Time", lambda x: (x == "No ontime").sum()),
    ).reset_index()

    grp["SLA"] = (grp["ATiempo"] / grp["Entregas"] * 100).round(1)
    return grp.sort_values("SLA", ascending=True)

def calcular_metricas_principales(df_):
    sla_info = calcular_sla(df_)
    hoy = datetime.now()
    pedidos_abiertos = df_[~df_["estado"].isin([STATUS_COMPLETED, STATUS_CANCELLED])]
    entregas = df_[df_["estado"] == STATUS_COMPLETED]
    avg_days = entregas["dias_hasta_entrega"].dropna().mean() if "dias_hasta_entrega" in df_.columns else None

    return {
        "total_pedidos": len(df_),
        "procesando": int((df_["estado"] == STATUS_PROCESSING).sum()),
        "despachado": int((df_["estado"] == STATUS_SHIPPED).sum()),
        "on_hold": int((df_["estado"] == STATUS_ON_HOLD).sum()),
        "cancelados": int((df_["estado"] == STATUS_CANCELLED).sum()),
        "abiertos": len(pedidos_abiertos),
        "avg_delivery_days": avg_days,
        **sla_info,
    }

# =============================================================================
# 5. CAPA DE VISUALIZACIÓN
# =============================================================================

_LAYOUT_DEFAULTS = dict(
    paper_bgcolor=BG_CARD,
    plot_bgcolor=BG_CARD,
    font=dict(color="white", family="Inter, sans-serif"),
    margin=dict(l=10, r=10, t=40, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, bgcolor="rgba(0,0,0,0)"),
)

def _apply_layout(fig, height=400, **extra):
    fig.update_layout(height=height, **_LAYOUT_DEFAULTS, **extra)
    return fig

def _color_sla(sla):
    if sla >= META_SLA: return COLOR_SUCCESS
    if sla >= 85: return COLOR_WARNING
    return COLOR_DANGER

def fig_sla_mensual(sla_actual, sla_ant, año_sel, comparar):
    fig = go.Figure()
    textos_actual = [f"{v:.1f}%" if v > 0 else "" for v in sla_actual.values]
    fig.add_trace(go.Bar(x=MESES_NOMBRES, y=sla_actual.values, name=str(año_sel), marker_color=COLOR_PRIMARY,
                         marker=dict(cornerradius=6), text=textos_actual, textposition="outside"))
    if comparar and sla_ant is not None:
        textos_ant = [f"{v:.1f}%" if v > 0 else "" for v in sla_ant.values]
        fig.add_trace(go.Bar(x=MESES_NOMBRES, y=sla_ant.values, name=str(año_sel - 1), marker_color=COLOR_NEUTRAL,
                             marker=dict(cornerradius=6), opacity=0.7, text=textos_ant, textposition="outside"))
    fig.add_hline(y=META_SLA, line_dash="dash", line_color=COLOR_SUCCESS, line_width=2,
                  annotation_text=f"Meta {META_SLA}%", annotation_font=dict(size=11, color=COLOR_SUCCESS))
    _apply_layout(fig, height=420, barmode="group", xaxis=dict(title="", gridcolor=GRID_COLOR),
                  yaxis=dict(title="SLA (%)", gridcolor=GRID_COLOR, range=[0, 100], ticksuffix="%"))
    return fig

def fig_tendencia(sla_actual):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=MESES_NOMBRES, y=sla_actual.values, mode="lines+markers", name="SLA Real",
                             line=dict(color=COLOR_PRIMARY, width=3), marker=dict(size=10, color=COLOR_CYAN, symbol="circle"),
                             fill="tozeroy", fillcolor="rgba(37,99,235,0.1)",
                             text=[f"{v:.1f}%" for v in sla_actual], textposition="top center"))
    if len(sla_actual) >= 3:
        mm = pd.Series(sla_actual.values).rolling(3, min_periods=1).mean()
        fig.add_trace(go.Scatter(x=MESES_NOMBRES, y=mm.values, mode="lines", name="Tendencia (3m)",
                                 line=dict(color=COLOR_WARNING, width=2, dash="dash")))
    fig.add_hline(y=META_SLA, line_dash="dash", line_color=COLOR_SUCCESS, line_width=2,
                  annotation_text=f"Meta {META_SLA}%", annotation_font=dict(size=11, color=COLOR_SUCCESS))
    _apply_layout(fig, height=420, xaxis=dict(gridcolor=GRID_COLOR), yaxis=dict(gridcolor=GRID_COLOR, range=[0, 100], ticksuffix="%"))
    return fig

def fig_sla_horizontal(df_grp, col_label):
    cores = [_color_sla(v) for v in df_grp["SLA"]]
    fig = go.Figure(go.Bar(x=df_grp["SLA"], y=df_grp[col_label], orientation="h", marker_color=cores,
                           marker=dict(cornerradius=6), text=df_grp["SLA"].apply(lambda x: f"{x:.1f}%"),
                           textposition="outside", customdata=df_grp["Entregas"],
                           hovertemplate="<b>%{y}</b><br>SLA: %{x:.1f}%<br>Entregas: %{customdata}<extra></extra>"))
    fig.add_vline(x=META_SLA, line_dash="dash", line_color=COLOR_SUCCESS, line_width=2,
                  annotation_text=f"Meta {META_SLA}%", annotation_font=dict(size=11, color=COLOR_SUCCESS))
    _apply_layout(fig, height=max(350, len(df_grp) * 35), xaxis=dict(title="SLA (%)", gridcolor=GRID_COLOR, range=[0, 100], ticksuffix="%"),
                  yaxis=dict(title="", gridcolor=GRID_COLOR))
    return fig

def fig_comparacion_transp(df_grp):
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_grp["Proveedor"], y=df_grp["ATiempo"], name="A Tiempo", marker_color=COLOR_SUCCESS,
                         marker=dict(cornerradius=6), text=df_grp["ATiempo"], textposition="outside"))
    fig.add_trace(go.Bar(x=df_grp["Proveedor"], y=df_grp["Atrasados"], name="Atrasados", marker_color=COLOR_DANGER,
                         marker=dict(cornerradius=6), text=df_grp["Atrasados"], textposition="outside"))
    _apply_layout(fig, height=420, barmode="group", xaxis=dict(title="", tickangle=30, gridcolor=GRID_COLOR),
                  yaxis=dict(title="Cantidad", gridcolor=GRID_COLOR))
    return fig

def fig_top_skus(df_):
    if "sku" not in df_.columns:
        return None
    top = df_["sku"].value_counts().head(10).reset_index()
    top.columns = ["SKU", "Volumen"]
    top = top.sort_values("Volumen", ascending=True)
    fig = go.Figure(go.Bar(x=top["Volumen"], y=top["SKU"], orientation="h", marker_color=COLOR_PRIMARY,
                           marker=dict(cornerradius=6), text=top["Volumen"], textposition="outside"))
    _apply_layout(fig, height=400, xaxis=dict(title="Cantidad", gridcolor=GRID_COLOR), yaxis=dict(title="SKU", gridcolor=GRID_COLOR))
    return fig

def fig_status_pie(df_):
    labels_map = {
        STATUS_COMPLETED: "Entregado",
        STATUS_PROCESSING: "En Proceso",
        STATUS_SHIPPED: "Despachado",
        STATUS_ON_HOLD: "En Espera",
        STATUS_CANCELLED: "Cancelado",
    }
    counts = df_["estado"].value_counts().reset_index()
    counts.columns = ["Estado", "Cantidad"]
    counts["Estado"] = counts["Estado"].map(labels_map).fillna(counts["Estado"])
    fig = px.pie(counts, values="Cantidad", names="Estado", hole=0.45,
                 color_discrete_sequence=[COLOR_SUCCESS, COLOR_WARNING, COLOR_CYAN, COLOR_DANGER, COLOR_NEUTRAL])
    fig.update_traces(textinfo="label+percent", textfont_size=12)
    _apply_layout(fig, height=420, showlegend=True)
    return fig

def fig_delay_distribution(df_):
    if "Dias de demora" not in df_.columns:
        return None
    
    atrasos_raw = pd.to_numeric(df_["Dias de demora"], errors='coerce')
    mask = (df_["estado"] == STATUS_COMPLETED) & (df_["On Time"] == "No ontime")
    atrasos = atrasos_raw[mask].dropna()
    
    if atrasos.empty:
        return None
    
    media = atrasos.mean()
    mediana = atrasos.median()
    maximo = atrasos.max()
    
    fig = px.histogram(atrasos, nbins=25, color_discrete_sequence=[COLOR_DANGER],
                       title=f"Distribución de Días de Atraso (n={len(atrasos)})")
    fig.add_vline(x=media, line_dash="dash", line_color=COLOR_WARNING,
                  annotation_text=f"Media: {media:.1f} días", annotation_font=dict(color=COLOR_WARNING, size=11))
    fig.add_vline(x=mediana, line_dash="dot", line_color=COLOR_CYAN,
                  annotation_text=f"Mediana: {mediana:.0f} días", annotation_font=dict(color=COLOR_CYAN, size=11),
                  annotation_position="top right")
    
    _apply_layout(fig, height=400, xaxis=dict(title="Días de Atraso", gridcolor=GRID_COLOR),
                  yaxis=dict(title="N Pedidos", gridcolor=GRID_COLOR))
    
    st.caption(f"Estadísticas: Media: {media:.1f} días | Mediana: {mediana:.0f} días | Máximo: {maximo:.0f} días | Total: {len(atrasos)} pedidos")
    return fig

def fig_aging(df_abiertos):
    if df_abiertos.empty or "dias_en_abierto" not in df_abiertos.columns:
        return None
    bins = [0, 3, 7, 15, 30, 60, float("inf")]
    labels = ["0-3d", "4-7d", "8-15d", "16-30d", "31-60d", ">60d"]
    df_abiertos = df_abiertos.copy()
    df_abiertos["rango"] = pd.cut(df_abiertos["dias_en_abierto"], bins=bins, labels=labels, right=True)
    aging = df_abiertos["rango"].value_counts().reindex(labels, fill_value=0)
    cores = [COLOR_SUCCESS, COLOR_SUCCESS, COLOR_WARNING, COLOR_WARNING, COLOR_DANGER, COLOR_DANGER]
    fig = go.Figure(go.Bar(x=aging.index, y=aging.values, marker_color=cores, marker=dict(cornerradius=6),
                           text=aging.values, textposition="outside"))
    _apply_layout(fig, height=380, xaxis=dict(title="Rango de Días Abiertos", gridcolor=GRID_COLOR),
                  yaxis=dict(title="N Pedidos", gridcolor=GRID_COLOR))
    return fig

def fig_tiempo_medio_transportadora(df_):
    if "Proveedor" not in df_.columns or "dias_hasta_entrega" not in df_.columns:
        return None
    entregas = df_[df_["estado"] == STATUS_COMPLETED].copy()
    if entregas.empty:
        return None
    avg = entregas.groupby("Proveedor")["dias_hasta_entrega"].mean().dropna().round(1).sort_values(ascending=True).reset_index()
    avg.columns = ["Transportadora", "Media (días)"]
    fig = go.Figure(go.Bar(x=avg["Media (días)"], y=avg["Transportadora"], orientation="h", marker_color=COLOR_CYAN,
                           marker=dict(cornerradius=6), text=avg["Media (días)"].apply(lambda x: f"{x:.1f}d"), textposition="outside"))
    _apply_layout(fig, height=max(320, len(avg) * 35), xaxis=dict(title="Días", gridcolor=GRID_COLOR), yaxis=dict(title="", gridcolor=GRID_COLOR))
    return fig

# =============================================================================
# 6. CONFIGURACIÓN DE PÁGINA Y CSS
# =============================================================================

st.set_page_config(page_title="Sleep Calm - Logistics", page_icon="📦", layout="wide", initial_sidebar_state="expanded")

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  html, body, .stApp {{ background: {BG_APP}; font-family: 'Inter', sans-serif; }}
  [data-testid="stSidebar"] {{ background: {BG_APP}; border-right: 1px solid {GRID_COLOR}; }}
  .sc-header {{
    background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 50%, #1e40af 100%);
    border-radius: 16px; padding: 1.4rem 2rem; margin-bottom: 1.5rem;
    box-shadow: 0 8px 32px rgba(37,99,235,0.3);
  }}
  .sc-header h1 {{ color: white; margin: 0; font-size: 1.5rem; font-weight: 700; }}
  .sc-header p {{ color: rgba(255,255,255,0.75); margin: 0.3rem 0 0; font-size: 0.8rem; }}
  .kpi-card {{
    background: linear-gradient(145deg, #1e293b 0%, #162032 100%);
    border-radius: 16px; padding: 1.1rem 1.3rem; margin-bottom: 0.8rem;
    border-left: 4px solid {COLOR_PRIMARY};
    transition: transform 0.2s, box-shadow 0.2s;
    box-shadow: 0 2px 8px rgba(0,0,0,0.25);
  }}
  .kpi-card:hover {{ transform: translateY(-3px); box-shadow: 0 8px 24px rgba(0,0,0,0.4); }}
  .kpi-value {{ font-size: 2rem; font-weight: 700; color: white; line-height: 1.2; }}
  .kpi-label {{ font-size: 0.65rem; text-transform: uppercase; letter-spacing: 1.5px; color: #94a3b8; }}
  .kpi-detail {{ font-size: 0.7rem; color: #64748b; margin-top: 0.4rem; }}
  .section-title {{ font-size: 1rem; font-weight: 600; margin: 1.5rem 0 0.8rem; padding-left: 0.9rem;
                    border-left: 4px solid {COLOR_PRIMARY}; color: white; }}
  .alert-badge {{ background: rgba(239,68,68,0.15); border: 1px solid {COLOR_DANGER};
                  border-radius: 10px; padding: 0.6rem 1rem; margin-bottom: 0.6rem; font-size: 0.8rem; color: #fca5a5; }}
  .warn-badge {{ background: rgba(245,158,11,0.15); border: 1px solid {COLOR_WARNING};
                 border-radius: 10px; padding: 0.6rem 1rem; margin-bottom: 0.6rem; font-size: 0.8rem; color: #fde68a; }}
  footer {{ visibility: hidden; }} #MainMenu {{ visibility: hidden; }}
  .stButton > button {{ border-radius: 10px; font-weight: 500; }}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 7. CARGAR DATOS
# =============================================================================

df_raw, audit_log = load_data()

if df_raw.empty:
    st.error("No fue posible cargar los datos. Verifique la conexión con la planilla.")
    st.stop()

hoy = datetime.now()

# =============================================================================
# 8. SIDEBAR
# =============================================================================

with st.sidebar:
    st.markdown("""<div style="text-align:center;padding:1rem 0 0.5rem">
      <div style="font-size:2.8rem">📦</div>
      <div style="font-weight:700;font-size:1.1rem;color:white">Sleep Calm</div>
      <div style="font-size:0.7rem;color:#64748b">Logistics Enterprise v10.3</div>
    </div>""", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(f"### {TEXTO['filters']}")
    años_disp = sorted(df_raw["ano"].dropna().unique().astype(int))
    año_sel = st.selectbox(TEXTO['year'], años_disp, index=len(años_disp) - 1)
    meses_disp = ["Todos"] + MESES_NOMBRES
    mes_sel = st.selectbox(TEXTO['month'], meses_disp, index=0)
    comparar = st.checkbox(TEXTO['compare'], value=True)
    st.markdown("---")
    ufs_disp = sorted(df_raw["UF"].dropna().unique()) if "UF" in df_raw.columns else []
    transp_disp = sorted(df_raw["Proveedor"].dropna().unique()) if "Proveedor" in df_raw.columns else []
    ufs_sel = st.multiselect(TEXTO['state'], ufs_disp, placeholder="Todos")
    transp_sel = st.multiselect(TEXTO['carrier'], transp_disp, placeholder="Todas")
    st.markdown("---")
    st.link_button("Registrar Devolución", "https://script.google.com/a/macros/sleepcalm.com.br/s/AKfycbzyOsb6FzdRee9Mn88h86fPx7B7ZmZoxNZLP-brNgUZr9-BRFhW3Dt49_QeRe59Mhg6yg/exec", use_container_width=True)

# =============================================================================
# 9. APLICAR FILTROS
# =============================================================================

def _apply_filters(df, año, mes, ufs, transportadoras):
    mask = df["ano"] == año
    if mes != "Todos":
        mes_num = MESES_NOMBRES.index(mes) + 1
        mask &= df["mes"] == mes_num
    if ufs:
        mask &= df["UF"].isin(ufs)
    if transportadoras:
        mask &= df["Proveedor"].isin(transportadoras)
    return df[mask].copy()

df = _apply_filters(df_raw, año_sel, mes_sel, ufs_sel, transp_sel)
df_ant = _apply_filters(df_raw, año_sel - 1, mes_sel, ufs_sel, transp_sel) if comparar else None

# =============================================================================
# 10. MÉTRICAS
# =============================================================================

metricas = calcular_metricas_principales(df)
metricas_ant = calcular_metricas_principales(df_ant) if df_ant is not None else None

sla = metricas["sla"]
a_tiempo = metricas["a_tiempo"]
total_ent = metricas["total_entregas"]
atrasados = metricas["atrasados"]
delta_sla = round(sla - metricas_ant["sla"], 1) if metricas_ant else 0.0
cor_sla = _color_sla(sla)

periodo_txt = f"{mes_sel} de {año_sel}" if mes_sel != "Todos" else f"Año {año_sel}"
st.markdown(f"""
<div class="sc-header">
  <div style="display:flex;justify-content:space-between;align-items:center">
    <div><h1>📦 {TEXTO['title']}</h1>
    <p>{TEXTO['subtitle']} | Período: <strong>{periodo_txt}</strong> | Meta SLA: <strong>{META_SLA}%</strong></p></div>
    <div style="font-size:0.7rem;background:rgba(255,255,255,0.15);padding:0.4rem 1rem;border-radius:20px;color:white">v10.3</div>
  </div>
</div>""", unsafe_allow_html=True)

if audit_log["warnings"]:
    with st.expander(TEXTO['data_warnings'], expanded=False):
        for w in audit_log["warnings"]:
            st.markdown(f'<div class="warn-badge">{w}</div>', unsafe_allow_html=True)
if metricas.get("alerta"):
    st.markdown(f'<div class="alert-badge">{metricas["alerta"]}</div>', unsafe_allow_html=True)

# =============================================================================
# 11. KPI CARDS
# =============================================================================

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""<div class="kpi-card"><div class="kpi-label">{TEXTO['total_orders']}</div>
    <div class="kpi-value">{metricas['total_pedidos']:,}</div>
    <div class="kpi-detail">Entregas: {total_ent:,} | Cancelados: {metricas['cancelados']:,}</div></div>""", unsafe_allow_html=True)
with c2:
    trend_html = f'<span style="color:#10b981">▲ {delta_sla:+.1f}pp</span>' if delta_sla >= 0 else f'<span style="color:#ef4444">▼ {abs(delta_sla):.1f}pp</span>'
    st.markdown(f"""<div class="kpi-card"><div class="kpi-label">{TEXTO['sla']}</div>
    <div class="kpi-value" style="color:{cor_sla}">{sla:.1f}%</div>
    <div class="kpi-detail">Meta: {META_SLA}% {trend_html}</div></div>""", unsafe_allow_html=True)
with c3:
    pct = f"{a_tiempo/total_ent*100:.1f}%" if total_ent > 0 else "--"
    st.markdown(f"""<div class="kpi-card" style="border-left-color:{COLOR_SUCCESS}">
    <div class="kpi-label">{TEXTO['on_time']}</div>
    <div class="kpi-value" style="color:{COLOR_SUCCESS}">{a_tiempo:,}</div>
    <div class="kpi-detail">{pct} de {total_ent:,} entregas</div></div>""", unsafe_allow_html=True)
with c4:
    pct_a = f"{atrasados/total_ent*100:.1f}%" if total_ent > 0 else "--"
    st.markdown(f"""<div class="kpi-card" style="border-left-color:{COLOR_DANGER}">
    <div class="kpi-label">{TEXTO['delayed']}</div>
    <div class="kpi-value" style="color:{COLOR_DANGER}">{atrasados:,}</div>
    <div class="kpi-detail">{pct_a} de {total_ent:,} entregas</div></div>""", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""<div class="kpi-card"><div class="kpi-label">{TEXTO['in_process']}</div>
    <div class="kpi-value">{metricas['procesando']}</div></div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<div class="kpi-card"><div class="kpi-label">{TEXTO['shipped']}</div>
    <div class="kpi-value">{metricas['despachado']}</div></div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""<div class="kpi-card"><div class="kpi-label">{TEXTO['on_hold']}</div>
    <div class="kpi-value">{metricas['on_hold']}</div></div>""", unsafe_allow_html=True)
with c4:
    avg_d = metricas.get("avg_delivery_days")
    avg_txt = f"{avg_d:.1f} días" if avg_d is not None and not np.isnan(avg_d) else "--"
    st.markdown(f"""<div class="kpi-card" style="border-left-color:{COLOR_CYAN}">
    <div class="kpi-label">{TEXTO['avg_delivery_days']}</div>
    <div class="kpi-value" style="color:{COLOR_CYAN}">{avg_txt}</div>
    <div class="kpi-detail">entregas a tiempo</div></div>""", unsafe_allow_html=True)

st.markdown("---")

# =============================================================================
# 12. GRÁFICOS
# =============================================================================

st.markdown(f'<div class="section-title">1. {TEXTO["chart_sla_monthly"]}</div>', unsafe_allow_html=True)
sla_actual = calcular_sla_mensual(df_raw, año_sel, ufs_sel, transp_sel)
sla_ant_s = calcular_sla_mensual(df_raw, año_sel - 1, ufs_sel, transp_sel) if comparar else None
st.plotly_chart(fig_sla_mensual(sla_actual, sla_ant_s, año_sel, comparar), use_container_width=True)

st.markdown(f'<div class="section-title">2. {TEXTO["chart_sla_trend"]}</div>', unsafe_allow_html=True)
st.plotly_chart(fig_tendencia(sla_actual), use_container_width=True)

st.markdown(f'<div class="section-title">3. {TEXTO["chart_sla_carrier"]}</div>', unsafe_allow_html=True)
df_transp_grp = calcular_sla_por_grupo(df, "Proveedor")
if not df_transp_grp.empty:
    st.plotly_chart(fig_sla_horizontal(df_transp_grp, "Proveedor"), use_container_width=True)
else:
    st.info("Sin datos de transportadora para el período seleccionado.")

st.markdown(f'<div class="section-title">4. {TEXTO["chart_comparison"]}</div>', unsafe_allow_html=True)
if not df_transp_grp.empty:
    st.plotly_chart(fig_comparacion_transp(df_transp_grp), use_container_width=True)

st.markdown(f'<div class="section-title">5. {TEXTO["chart_sla_state"]}</div>', unsafe_allow_html=True)
df_uf_grp = calcular_sla_por_grupo(df, "UF")
if not df_uf_grp.empty:
    st.plotly_chart(fig_sla_horizontal(df_uf_grp, "UF"), use_container_width=True)
else:
    st.info("Sin datos de UF para el período seleccionado.")

st.markdown(f'<div class="section-title">6. {TEXTO["chart_top_skus"]}</div>', unsafe_allow_html=True)
f_skus = fig_top_skus(df)
if f_skus:
    st.plotly_chart(f_skus, use_container_width=True)
else:
    st.info("Columna 'sku' no encontrada.")

st.markdown(f'<div class="section-title">7. {TEXTO["chart_status"]}</div>', unsafe_allow_html=True)
st.plotly_chart(fig_status_pie(df), use_container_width=True)

st.markdown(f'<div class="section-title">8. {TEXTO["chart_delay_dist"]}</div>', unsafe_allow_html=True)
f_delay = fig_delay_distribution(df)
if f_delay:
    st.plotly_chart(f_delay, use_container_width=True)
else:
    st.info("Sin datos de atraso para el período seleccionado.")

st.markdown(f'<div class="section-title">9. {TEXTO["chart_aging"]}</div>', unsafe_allow_html=True)
df_abiertos = df[~df["estado"].isin([STATUS_COMPLETED, STATUS_CANCELLED])].copy()
if not df_abiertos.empty and "fecha" in df_abiertos.columns:
    df_abiertos["dias_en_abierto"] = (hoy - df_abiertos["fecha"]).dt.days.clip(lower=0)
    f_aging = fig_aging(df_abiertos)
    if f_aging:
        st.plotly_chart(f_aging, use_container_width=True)
    else:
        st.success("¡Ningún pedido pendiente de entrega!")
else:
    st.success("¡Ningún pedido pendiente de entrega!")

st.markdown(f'<div class="section-title">10. {TEXTO["chart_avg_time"]}</div>', unsafe_allow_html=True)
f_avg = fig_tiempo_medio_transportadora(df)
if f_avg:
    st.plotly_chart(f_avg, use_container_width=True)
else:
    st.info("Datos insuficientes para calcular tiempo promedio de entrega.")

st.markdown("---")

# =============================================================================
# 13. PEDIDOS CRÍTICOS
# =============================================================================

st.markdown(f'<div class="section-title">11. {TEXTO["critical_orders"]}</div>', unsafe_allow_html=True)

if not df_abiertos.empty:
    columnas_exibir = [c for c in ["numero_pedido", "Proveedor", "UF", "sku", "Compromiso de entrega", "dias_en_abierto", "estado"] if c in df_abiertos.columns]
    df_abiertos_display = df_abiertos.copy()
    if "Compromiso de entrega" in df_abiertos_display.columns:
        df_abiertos_display["Compromiso de entrega"] = df_abiertos_display["Compromiso de entrega"].dt.strftime("%d/%m/%Y")
    st.dataframe(df_abiertos_display[columnas_exibir].sort_values("dias_en_abierto", ascending=False).head(50), use_container_width=True)
    st.caption(f"Total: {len(df_abiertos)} pedidos críticos")
    csv_bytes = df_abiertos.to_csv(index=False).encode("utf-8")
    st.download_button("Descargar Pedidos Críticos", csv_bytes, f"critical_orders_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")
else:
    st.success("¡Ningún pedido pendiente de entrega!")

# =============================================================================
# 14. RANKING DE TRANSPORTADORAS
# =============================================================================

st.markdown(f'<div class="section-title">12. {TEXTO["ranking_carrier"]}</div>', unsafe_allow_html=True)
if not df_transp_grp.empty:
    df_rank = df_transp_grp.sort_values("SLA", ascending=False).reset_index(drop=True)
    df_rank.index = df_rank.index + 1
    df_rank["SLA"] = df_rank["SLA"].apply(lambda x: f"{x:.1f}%")
    st.dataframe(df_rank[["Proveedor", "SLA", "Entregas", "ATiempo", "Atrasados"]], use_container_width=True)

# =============================================================================
# 15. EXPLICACIÓN DEL SLA
# =============================================================================

with st.expander(TEXTO["how_sla"]):
    st.markdown(f"""
**Fórmula del SLA:** {TEXTO['sla_formula']}

**¿Qué se considera?** {TEXTO['sla_note']}

**Meta actual:** {META_SLA}%

**Reglas de negocio aplicadas:**
- Pedidos con estado wc-cancelled son excluidos del cálculo.
- La columna On Time es normalizada antes del cálculo.
- Pedidos duplicados por numero_pedido son eliminados en la carga.
- Alertas automáticas se emiten cuando hay datos ausentes.
    """)

# =============================================================================
# 16. PIE DE PÁGINA
# =============================================================================

st.markdown(f"""
<div style="text-align:center;padding:1.5rem 0 0.5rem;color:#64748b;font-size:0.7rem;border-top:1px solid {GRID_COLOR};margin-top:1.5rem">
  {TEXTO['footer']} | Meta SLA: {META_SLA}% | {TEXTO['updated']}: {hoy.strftime('%d/%m/%Y %H:%M')}
</div>
""", unsafe_allow_html=True)
