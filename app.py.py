"""
================================================================================
SLEEP CALM - LOGISTICS ENTERPRISE
Sistema Corporativo de Monitoreo de Entregas
Versión: 10.3 - Solo Idioma Español
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

MESES_NOMES = ["Ene","Feb","Mar","Abr","May","Jun",
               "Jul","Ago","Sep","Oct","Nov","Dic"]

# =============================================================================
# 2. TEXTO EN ESPAÑOL
# =============================================================================

_TEXTS = {
    "title":              {"es": "Sleep Calm - Logistics Enterprise"},
    "subtitle":           {"es": "Sistema Corporativo de Monitoreo de Entregas"},
    "period":             {"es": "Periodo"},
    "meta_sla":           {"es": "Meta SLA"},
    "total_orders":       {"es": "TOTAL PEDIDOS"},
    "sla":                {"es": "SLA"},
    "on_time":            {"es": "ENTREGAS A TIEMPO"},
    "delayed":            {"es": "ATRASADOS"},
    "in_process":         {"es": "EN PROCESO"},
    "shipped":            {"es": "DESPACHADOS"},
    "not_delivered":      {"es": "NO ENTREGADOS"},
    "chart_sla_monthly":  {"es": "SLA por Mes - Comparativo Anual"},
    "chart_sla_trend":    {"es": "Tendencia del SLA"},
    "chart_sla_carrier":  {"es": "SLA por Transportadora"},
    "chart_comparison":   {"es": "A Tiempo vs Atrasado por Transportadora"},
    "chart_sla_state":    {"es": "SLA por Estado (UF)"},
    "chart_top_skus":     {"es": "Top 10 SKUs Más Vendidos"},
    "chart_status":       {"es": "Distribucion de Estados"},
    "chart_delay_dist":   {"es": "Distribucion de Dias de Atraso"},
    "chart_aging":        {"es": "Aging de Pedidos Abiertos"},
    "chart_avg_time":     {"es": "Tiempo Promedio de Entrega por Transportadora"},
    "critical_orders":    {"es": "Pedidos Criticos (No Entregados)"},
    "no_pending":         {"es": "¡Ningun pedido pendiente de entrega!"},
    "filters":            {"es": "Filtros"},
    "year":               {"es": "Año"},
    "month":              {"es": "Mes"},
    "all":                {"es": "Todos"},
    "compare":            {"es": "Comparar con año anterior"},
    "carrier":            {"es": "Transportadora"},
    "state":              {"es": "UF"},
    "returns":            {"es": "Devolucion"},
    "how_sla":            {"es": "¿Como se calcula el SLA?"},
    "sla_formula":        {"es": "SLA = (Entregas a Tiempo / Total Entregas) x 100"},
    "sla_note":           {"es": "Solo pedidos con estado 'wc-completed' son considerados"},
    "footer":             {"es": "Sleep Calm - Logistics Enterprise"},
    "updated":            {"es": "Actualizado"},
    "data_warnings":      {"es": "Alertas de Calidad de Datos"},
    "avg_delivery_days":  {"es": "Tiempo Promedio de Entrega"},
    "days":               {"es": "dias"},
    "ranking_carrier":    {"es": "Ranking de Transportadoras"},
    "on_hold":            {"es": "EN ESPERA"},
}

def t(key):
    lang = st.session_state.get("language", "es")
    return _TEXTS.get(key, {}).get(lang, key)

# =============================================================================
# 3. CAMADA DE DADOS (EXACTAMENTE IGUAL)
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
            audit["warnings"].append(f"{invalid_count} valor(es) invalido(s) en 'On Time' fueron ignorados.")

    if "numero_pedido" in df.columns:
        before = len(df)
        df = df.drop_duplicates(subset=["numero_pedido"], keep="last")
        removed = before - len(df)
        if removed:
            audit["duplicates_removed"] = removed
            audit["warnings"].append(f"{removed} pedido(s) duplicado(s) eliminado(s).")

    df["ano"] = df["fecha"].dt.year
    df["mes"] = df["fecha"].dt.month
    df["mes_nome"] = df["fecha"].dt.strftime("%b")

    if "Compromiso de entrega" in df.columns:
        df["dias_ate_entrega"] = (df["Compromiso de entrega"] - df["fecha"]).dt.days

    return df, audit

# =============================================================================
# 4. CAMADA DE METRICAS (EXACTAMENTE IGUAL - NO CAMBIA NADA)
# =============================================================================

def calcular_sla(df_):
    resultado = {"sla": 0.0, "no_prazo": 0, "total_entregues": 0, "atrasados": 0, "valido": False, "alerta": None}

    if df_.empty or "estado" not in df_.columns:
        return resultado

    entregues = df_[df_["estado"] == STATUS_COMPLETED].copy()
    total = len(entregues)

    if total == 0:
        return resultado

    no_prazo = int((entregues["On Time"] == "On Time").sum())
    atrasados = int((entregues["On Time"] == "No ontime").sum())

    sem_classificacao = total - no_prazo - atrasados
    if sem_classificacao > 0:
        resultado["alerta"] = f"{sem_classificacao} entrega(s) sin clasificacion en 'On Time'."

    sla = round(no_prazo / total * 100, 2)

    if sla > 100:
        resultado["alerta"] = f"SLA invalido: {sla}% > 100%."
        sla = 100.0
    if sla < 0:
        resultado["alerta"] = f"SLA invalido: {sla}% < 0%."
        sla = 0.0

    resultado.update({"sla": sla, "no_prazo": no_prazo, "total_entregues": total, "atrasados": atrasados, "valido": True})
    return resultado

def calcular_sla_mensal(df_, ano, ufs=None, transportadoras=None):
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

def calcular_sla_por_grupo(df_, coluna):
    if df_.empty or coluna not in df_.columns:
        return pd.DataFrame()

    entregues = df_[df_["estado"] == STATUS_COMPLETED].copy()
    if entregues.empty:
        return pd.DataFrame()

    grp = entregues.groupby(coluna).agg(
        Entregues = ("On Time", "count"),
        NoPrazo   = ("On Time", lambda x: (x == "On Time").sum()),
        Atrasados = ("On Time", lambda x: (x == "No ontime").sum()),
    ).reset_index()

    grp["SLA"] = (grp["NoPrazo"] / grp["Entregues"] * 100).round(1)
    return grp.sort_values("SLA", ascending=True)

def calcular_metricas_principais(df_):
    sla_info = calcular_sla(df_)
    hoje = datetime.now()
    pedidos_abertos = df_[~df_["estado"].isin([STATUS_COMPLETED, STATUS_CANCELLED])]
    entregues = df_[df_["estado"] == STATUS_COMPLETED]
    avg_days = entregues["dias_ate_entrega"].dropna().mean() if "dias_ate_entrega" in df_.columns else None

    return {
        "total_pedidos": len(df_),
        "processando": int((df_["estado"] == STATUS_PROCESSING).sum()),
        "despachado": int((df_["estado"] == STATUS_SHIPPED).sum()),
        "on_hold": int((df_["estado"] == STATUS_ON_HOLD).sum()),
        "cancelados": int((df_["estado"] == STATUS_CANCELLED).sum()),
        "em_aberto": len(pedidos_abertos),
        "avg_delivery_days": avg_days,
        **sla_info,
    }

# =============================================================================
# 5. CAMADA DE VISUALIZACAO (EXACTAMENTE IGUAL)
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

def fig_sla_mensual(sla_atual, sla_ant, ano_sel, comparar):
    fig = go.Figure()
    textos_atual = [f"{v:.1f}%" if v > 0 else "" for v in sla_atual.values]
    fig.add_trace(go.Bar(x=MESES_NOMES, y=sla_atual.values, name=str(ano_sel), marker_color=COLOR_PRIMARY,
                         marker=dict(cornerradius=6), text=textos_atual, textposition="outside"))
    if comparar and sla_ant is not None:
        textos_ant = [f"{v:.1f}%" if v > 0 else "" for v in sla_ant.values]
        fig.add_trace(go.Bar(x=MESES_NOMES, y=sla_ant.values, name=str(ano_sel - 1), marker_color=COLOR_NEUTRAL,
                             marker=dict(cornerradius=6), opacity=0.7, text=textos_ant, textposition="outside"))
    fig.add_hline(y=META_SLA, line_dash="dash", line_color=COLOR_SUCCESS, line_width=2,
                  annotation_text=f"Meta {META_SLA}%", annotation_font=dict(size=11, color=COLOR_SUCCESS))
    _apply_layout(fig, height=420, barmode="group", xaxis=dict(title="", gridcolor=GRID_COLOR),
                  yaxis=dict(title="SLA (%)", gridcolor=GRID_COLOR, range=[0, 100], ticksuffix="%"))
    return fig

def fig_tendencia(sla_atual):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=MESES_NOMES, y=sla_atual.values, mode="lines+markers", name="SLA Real",
                             line=dict(color=COLOR_PRIMARY, width=3), marker=dict(size=10, color=COLOR_CYAN, symbol="circle"),
                             fill="tozeroy", fillcolor="rgba(37,99,235,0.1)",
                             text=[f"{v:.1f}%" for v in sla_atual], textposition="top center"))
    if len(sla_atual) >= 3:
        mm = pd.Series(sla_atual.values).rolling(3, min_periods=1).mean()
        fig.add_trace(go.Scatter(x=MESES_NOMES, y=mm.values, mode="lines", name="Tendencia (3m)",
                                 line=dict(color=COLOR_WARNING, width=2, dash="dash")))
    fig.add_hline(y=META_SLA, line_dash="dash", line_color=COLOR_SUCCESS, line_width=2,
                  annotation_text=f"Meta {META_SLA}%", annotation_font=dict(size=11, color=COLOR_SUCCESS))
    _apply_layout(fig, height=420, xaxis=dict(gridcolor=GRID_COLOR), yaxis=dict(gridcolor=GRID_COLOR, range=[0, 100], ticksuffix="%"))
    return fig

def fig_sla_horizontal(df_grp, col_label):
    cores = [_color_sla(v) for v in df_grp["SLA"]]
    fig = go.Figure(go.Bar(x=df_grp["SLA"], y=df_grp[col_label], orientation="h", marker_color=cores,
                           marker=dict(cornerradius=6), text=df_grp["SLA"].apply(lambda x: f"{x:.1f}%"),
                           textposition="outside", customdata=df_grp["Entregues"],
                           hovertemplate="<b>%{y}</b><br>SLA: %{x:.1f}%<br>Entregues: %{customdata}<extra></extra>"))
    fig.add_vline(x=META_SLA, line_dash="dash", line_color=COLOR_SUCCESS, line_width=2,
                  annotation_text=f"Meta {META_SLA}%", annotation_font=dict(size=11, color=COLOR_SUCCESS))
    _apply_layout(fig, height=max(350, len(df_grp) * 35), xaxis=dict(title="SLA (%)", gridcolor=GRID_COLOR, range=[0, 100], ticksuffix="%"),
                  yaxis=dict(title="", gridcolor=GRID_COLOR))
    return fig

def fig_comparacao_transp(df_grp):
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_grp["Proveedor"], y=df_grp["NoPrazo"], name=t("on_time"), marker_color=COLOR_SUCCESS,
                         marker=dict(cornerradius=6), text=df_grp["NoPrazo"], textposition="outside"))
    fig.add_trace(go.Bar(x=df_grp["Proveedor"], y=df_grp["Atrasados"], name=t("delayed"), marker_color=COLOR_DANGER,
                         marker=dict(cornerradius=6), text=df_grp["Atrasados"], textposition="outside"))
    _apply_layout(fig, height=420, barmode="group", xaxis=dict(title="", tickangle=30, gridcolor=GRID_COLOR),
                  yaxis=dict(title="Qtd", gridcolor=GRID_COLOR))
    return fig

def fig_top_skus(df_):
    if "sku" not in df_.columns:
        return None
    top = df_["sku"].value_counts().head(10).reset_index()
    top.columns = ["SKU", "Volume"]
    top = top.sort_values("Volume", ascending=True)
    fig = go.Figure(go.Bar(x=top["Volume"], y=top["SKU"], orientation="h", marker_color=COLOR_PRIMARY,
                           marker=dict(cornerradius=6), text=top["Volume"], textposition="outside"))
    _apply_layout(fig, height=400, xaxis=dict(title="Quantidade", gridcolor=GRID_COLOR), yaxis=dict(title="SKU", gridcolor=GRID_COLOR))
    return fig

def fig_status_pie(df_):
    lang = st.session_state.get("language", "es")
    labels_map = {
        "es": {STATUS_COMPLETED: "Entregado", STATUS_PROCESSING: "En Proceso", STATUS_SHIPPED: "Despachado",
               STATUS_ON_HOLD: "En Espera", STATUS_CANCELLED: "Cancelado"},
    }
    counts = df_["estado"].value_counts().reset_index()
    counts.columns = ["Estado", "Quantidade"]
    counts["Estado"] = counts["Estado"].map(labels_map[lang]).fillna(counts["Estado"])
    fig = px.pie(counts, values="Quantidade", names="Estado", hole=0.45,
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
                       title=f"Distribuicao de Dias de Atraso (n={len(atrasos)})")
    fig.add_vline(x=media, line_dash="dash", line_color=COLOR_WARNING,
                  annotation_text=f"Media: {media:.1f} dias", annotation_font=dict(color=COLOR_WARNING, size=11))
    fig.add_vline(x=mediana, line_dash="dot", line_color=COLOR_CYAN,
                  annotation_text=f"Mediana: {mediana:.0f} dias", annotation_font=dict(color=COLOR_CYAN, size=11),
                  annotation_position="top right")
    
    _apply_layout(fig, height=400, xaxis=dict(title="Dias de Atraso", gridcolor=GRID_COLOR),
                  yaxis=dict(title="N Pedidos", gridcolor=GRID_COLOR))
    
    st.caption(f"Estatisticas: Media: {media:.1f} dias | Mediana: {mediana:.0f} dias | Maximo: {maximo:.0f} dias | Total: {len(atrasos)} pedidos")
    return fig

def fig_aging(df_abertos):
    if df_abertos.empty or "dias_em_aberto" not in df_abertos.columns:
        return None
    bins = [0, 3, 7, 15, 30, 60, float("inf")]
    labels = ["0-3d", "4-7d", "8-15d", "16-30d", "31-60d", ">60d"]
    df_abertos = df_abertos.copy()
    df_abertos["faixa"] = pd.cut(df_abertos["dias_em_aberto"], bins=bins, labels=labels, right=True)
    aging = df_abertos["faixa"].value_counts().reindex(labels, fill_value=0)
    cores = [COLOR_SUCCESS, COLOR_SUCCESS, COLOR_WARNING, COLOR_WARNING, COLOR_DANGER, COLOR_DANGER]
    fig = go.Figure(go.Bar(x=aging.index, y=aging.values, marker_color=cores, marker=dict(cornerradius=6),
                           text=aging.values, textposition="outside"))
    _apply_layout(fig, height=380, xaxis=dict(title="Faixa de Dias em Aberto", gridcolor=GRID_COLOR),
                  yaxis=dict(title="N Pedidos", gridcolor=GRID_COLOR))
    return fig

def fig_tempo_medio_transportadora(df_):
    if "Proveedor" not in df_.columns or "dias_ate_entrega" not in df_.columns:
        return None
    entregues = df_[df_["estado"] == STATUS_COMPLETED].copy()
    if entregues.empty:
        return None
    avg = entregues.groupby("Proveedor")["dias_ate_entrega"].mean().dropna().round(1).sort_values(ascending=True).reset_index()
    avg.columns = ["Transportadora", "Media (dias)"]
    fig = go.Figure(go.Bar(x=avg["Media (dias)"], y=avg["Transportadora"], orientation="h", marker_color=COLOR_CYAN,
                           marker=dict(cornerradius=6), text=avg["Media (dias)"].apply(lambda x: f"{x:.1f}d"), textposition="outside"))
    _apply_layout(fig, height=max(320, len(avg) * 35), xaxis=dict(title="Dias", gridcolor=GRID_COLOR), yaxis=dict(title="", gridcolor=GRID_COLOR))
    return fig

# =============================================================================
# 6. CONFIGURACION DE LA PAGINA Y CSS (IGUAL)
# =============================================================================

st.set_page_config(page_title="Sleep Calm - Logistics", page_icon="📦", layout="wide", initial_sidebar_state="expanded")

if "language" not in st.session_state:
    st.session_state.language = "es"

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
# 7. CARREGAR DADOS
# =============================================================================

df_raw, audit_log = load_data()

if df_raw.empty:
    st.error("No fue posible cargar los datos. Verifique la conexion con la planilla.")
    st.stop()

hoje = datetime.now()

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
    st.markdown(f"### {t('filters')}")
    anos_disp = sorted(df_raw["ano"].dropna().unique().astype(int))
    ano_sel = st.selectbox(t("year"), anos_disp, index=len(anos_disp) - 1)
    meses_disp = ["Todos"] + MESES_NOMES
    mes_sel = st.selectbox(t("month"), meses_disp, index=0)
    comparar = st.checkbox(t("compare"), value=True)
    st.markdown("---")
    ufs_disp = sorted(df_raw["UF"].dropna().unique()) if "UF" in df_raw.columns else []
    transp_disp = sorted(df_raw["Proveedor"].dropna().unique()) if "Proveedor" in df_raw.columns else []
    ufs_sel = st.multiselect(t("state"), ufs_disp, placeholder="Todos")
    transp_sel = st.multiselect(t("carrier"), transp_disp, placeholder="Todas")
    st.markdown("---")
    st.link_button(t("returns"), "https://script.google.com/a/macros/sleepcalm.com.br/s/AKfycbzyOsb6FzdRee9Mn88h86fPx7B7ZmZoxNZLP-brNgUZr9-BRFhW3Dt49_QeRe59Mhg6yg/exec", use_container_width=True)

# =============================================================================
# 9. APLICAR FILTROS
# =============================================================================

def _apply_filters(df, ano, mes, ufs, transportadoras):
    mask = df["ano"] == ano
    if mes != "Todos":
        mes_num = MESES_NOMES.index(mes) + 1
        mask &= df["mes"] == mes_num
    if ufs:
        mask &= df["UF"].isin(ufs)
    if transportadoras:
        mask &= df["Proveedor"].isin(transportadoras)
    return df[mask].copy()

df = _apply_filters(df_raw, ano_sel, mes_sel, ufs_sel, transp_sel)
df_ant = _apply_filters(df_raw, ano_sel - 1, mes_sel, ufs_sel, transp_sel) if comparar else None

# =============================================================================
# 10. METRICAS
# =============================================================================

metricas = calcular_metricas_principais(df)
metricas_ant = calcular_metricas_principais(df_ant) if df_ant is not None else None

sla = metricas["sla"]
no_prazo = metricas["no_prazo"]
total_ent = metricas["total_entregues"]
atrasados = metricas["atrasados"]
delta_sla = round(sla - metricas_ant["sla"], 1) if metricas_ant else 0.0
cor_sla = _color_sla(sla)

periodo_txt = f"{mes_sel} de {ano_sel}" if mes_sel != "Todos" else f"Año {ano_sel}"
st.markdown(f"""
<div class="sc-header">
  <div style="display:flex;justify-content:space-between;align-items:center">
    <div><h1>📦 {t('title')}</h1>
    <p>{t('subtitle')} | Periodo: <strong>{periodo_txt}</strong> | Meta SLA: <strong>{META_SLA}%</strong></p></div>
    <div style="font-size:0.7rem;background:rgba(255,255,255,0.15);padding:0.4rem 1rem;border-radius:20px;color:white">v10.3</div>
  </div>
</div>""", unsafe_allow_html=True)

if audit_log["warnings"]:
    with st.expander(t("data_warnings"), expanded=False):
        for w in audit_log["warnings"]:
            st.markdown(f'<div class="warn-badge">{w}</div>', unsafe_allow_html=True)
if metricas.get("alerta"):
    st.markdown(f'<div class="alert-badge">{metricas["alerta"]}</div>', unsafe_allow_html=True)

# =============================================================================
# 11. KPI CARDS
# =============================================================================

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""<div class="kpi-card"><div class="kpi-label">{t('total_orders')}</div>
    <div class="kpi-value">{metricas['total_pedidos']:,}</div>
    <div class="kpi-detail">Entregas: {total_ent:,} | Cancelados: {metricas['cancelados']:,}</div></div>""", unsafe_allow_html=True)
with c2:
    trend_html = f'<span style="color:#10b981">▲ {delta_sla:+.1f}pp</span>' if delta_sla >= 0 else f'<span style="color:#ef4444">▼ {abs(delta_sla):.1f}pp</span>'
    st.markdown(f"""<div class="kpi-card"><div class="kpi-label">{t('sla')}</div>
    <div class="kpi-value" style="color:{cor_sla}">{sla:.1f}%</div>
    <div class="kpi-detail">Meta: {META_SLA}% {trend_html}</div></div>""", unsafe_allow_html=True)
with c3:
    pct = f"{no_prazo/total_ent*100:.1f}%" if total_ent > 0 else "--"
    st.markdown(f"""<div class="kpi-card" style="border-left-color:{COLOR_SUCCESS}">
    <div class="kpi-label">{t('on_time')}</div>
    <div class="kpi-value" style="color:{COLOR_SUCCESS}">{no_prazo:,}</div>
    <div class="kpi-detail">{pct} de {total_ent:,} entregas</div></div>""", unsafe_allow_html=True)
with c4:
    pct_a = f"{atrasados/total_ent*100:.1f}%" if total_ent > 0 else "--"
    st.markdown(f"""<div class="kpi-card" style="border-left-color:{COLOR_DANGER}">
    <div class="kpi-label">{t('delayed')}</div>
    <div class="kpi-value" style="color:{COLOR_DANGER}">{atrasados:,}</div>
    <div class="kpi-detail">{pct_a} de {total_ent:,} entregas</div></div>""", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""<div class="kpi-card"><div class="kpi-label">{t('in_process')}</div>
    <div class="kpi-value">{metricas['processando']}</div></div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<div class="kpi-card"><div class="kpi-label">{t('shipped')}</div>
    <div class="kpi-value">{metricas['despachado']}</div></div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""<div class="kpi-card"><div class="kpi-label">{t('on_hold')}</div>
    <div class="kpi-value">{metricas['on_hold']}</div></div>""", unsafe_allow_html=True)
with c4:
    avg_d = metricas.get("avg_delivery_days")
    avg_txt = f"{avg_d:.1f} {t('days')}" if avg_d is not None and not np.isnan(avg_d) else "--"
    st.markdown(f"""<div class="kpi-card" style="border-left-color:{COLOR_CYAN}">
    <div class="kpi-label">{t('avg_delivery_days')}</div>
    <div class="kpi-value" style="color:{COLOR_CYAN}">{avg_txt}</div>
    <div class="kpi-detail">entregas a tiempo</div></div>""", unsafe_allow_html=True)

st.markdown("---")

# =============================================================================
# 12. GRAFICOS
# =============================================================================

st.markdown(f'<div class="section-title">1. {t("chart_sla_monthly")}</div>', unsafe_allow_html=True)
sla_atual = calcular_sla_mensual(df_raw, ano_sel, ufs_sel, transp_sel)
sla_ant_s = calcular_sla_mensual(df_raw, ano_sel - 1, ufs_sel, transp_sel) if comparar else None
st.plotly_chart(fig_sla_mensual(sla_atual, sla_ant_s, ano_sel, comparar), use_container_width=True)

st.markdown(f'<div class="section-title">2. {t("chart_sla_trend")}</div>', unsafe_allow_html=True)
st.plotly_chart(fig_tendencia(sla_atual), use_container_width=True)

st.markdown(f'<div class="section-title">3. {t("chart_sla_carrier")}</div>', unsafe_allow_html=True)
df_transp_grp = calcular_sla_por_grupo(df, "Proveedor")
if not df_transp_grp.empty:
    st.plotly_chart(fig_sla_horizontal(df_transp_grp, "Proveedor"), use_container_width=True)
else:
    st.info("Sin datos de transportadora para el periodo seleccionado.")

st.markdown(f'<div class="section-title">4. {t("chart_comparison")}</div>', unsafe_allow_html=True)
if not df_transp_grp.empty:
    st.plotly_chart(fig_comparacao_transp(df_transp_grp), use_container_width=True)

st.markdown(f'<div class="section-title">5. {t("chart_sla_state")}</div>', unsafe_allow_html=True)
df_uf_grp = calcular_sla_por_grupo(df, "UF")
if not df_uf_grp.empty:
    st.plotly_chart(fig_sla_horizontal(df_uf_grp, "UF"), use_container_width=True)
else:
    st.info("Sin datos de UF para el periodo seleccionado.")

st.markdown(f'<div class="section-title">6. {t("chart_top_skus")}</div>', unsafe_allow_html=True)
f_skus = fig_top_skus(df)
if f_skus:
    st.plotly_chart(f_skus, use_container_width=True)
else:
    st.info("Columna 'sku' no encontrada.")

st.markdown(f'<div class="section-title">7. {t("chart_status")}</div>', unsafe_allow_html=True)
st.plotly_chart(fig_status_pie(df), use_container_width=True)

st.markdown(f'<div class="section-title">8. {t("chart_delay_dist")}</div>', unsafe_allow_html=True)
f_delay = fig_delay_distribution(df)
if f_delay:
    st.plotly_chart(f_delay, use_container_width=True)
else:
    st.info("Sin datos de atraso para el periodo seleccionado.")

st.markdown(f'<div class="section-title">9. {t("chart_aging")}</div>', unsafe_allow_html=True)
df_abertos = df[~df["estado"].isin([STATUS_COMPLETED, STATUS_CANCELLED])].copy()
if not df_abertos.empty and "fecha" in df_abertos.columns:
    df_abertos["dias_em_aberto"] = (hoje - df_abertos["fecha"]).dt.days.clip(lower=0)
    f_aging = fig_aging(df_abertos)
    if f_aging:
        st.plotly_chart(f_aging, use_container_width=True)
    else:
        st.success(t("no_pending"))
else:
    st.success(t("no_pending"))

st.markdown(f'<div class="section-title">10. {t("chart_avg_time")}</div>', unsafe_allow_html=True)
f_avg = fig_tempo_medio_transportadora(df)
if f_avg:
    st.plotly_chart(f_avg, use_container_width=True)
else:
    st.info("Datos insuficientes para calcular tiempo promedio de entrega.")

st.markdown("---")

# =============================================================================
# 13. PEDIDOS CRITICOS
# =============================================================================

st.markdown(f'<div class="section-title">11. {t("critical_orders")}</div>', unsafe_allow_html=True)

if not df_abertos.empty:
    colunas_exibir = [c for c in ["numero_pedido", "Proveedor", "UF", "sku", "Compromiso de entrega", "dias_em_aberto", "estado"] if c in df_abertos.columns]
    df_abertos_display = df_abertos.copy()
    if "Compromiso de entrega" in df_abertos_display.columns:
        df_abertos_display["Compromiso de entrega"] = df_abertos_display["Compromiso de entrega"].dt.strftime("%d/%m/%Y")
    st.dataframe(df_abertos_display[colunas_exibir].sort_values("dias_em_aberto", ascending=False).head(50), use_container_width=True)
    st.caption(f"Total: {len(df_abertos)} pedidos criticos")
    csv_bytes = df_abertos.to_csv(index=False).encode("utf-8")
    st.download_button("Descargar Pedidos Criticos", csv_bytes, f"critical_orders_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")
else:
    st.success(t("no_pending"))

# =============================================================================
# 14. RANKING DE TRANSPORTADORAS
# =============================================================================

st.markdown(f'<div class="section-title">12. {t("ranking_carrier")}</div>', unsafe_allow_html=True)
if not df_transp_grp.empty:
    df_rank = df_transp_grp.sort_values("SLA", ascending=False).reset_index(drop=True)
    df_rank.index = df_rank.index + 1
    df_rank["SLA"] = df_rank["SLA"].apply(lambda x: f"{x:.1f}%")
    st.dataframe(df_rank[["Proveedor", "SLA", "Entregues", "NoPrazo", "Atrasados"]], use_container_width=True)

# =============================================================================
# 15. EXPLICACION DEL SLA
# =============================================================================

with st.expander(t("how_sla")):
    st.markdown(f"""
**Formula del SLA:** {t('sla_formula')}

**Que se considera?** {t('sla_note')}

**Meta actual:** {META_SLA}%

**Reglas de negocio aplicadas:**
- Pedidos con estado wc-cancelled son excluidos del calculo.
- La columna On Time es normalizada antes del calculo.
- Pedidos duplicados por numero_pedido son eliminados en la carga.
- Alertas automaticas se emiten cuando hay datos ausentes.
    """)

# =============================================================================
# 16. RODAPE
# =============================================================================

st.markdown(f"""
<div style="text-align:center;padding:1.5rem 0 0.5rem;color:#64748b;font-size:0.7rem;border-top:1px solid {GRID_COLOR};margin-top:1.5rem">
  {t('footer')} | Meta SLA: {META_SLA}% | {t('updated')}: {hoje.strftime('%d/%m/%Y %H:%M')}
</div>
""", unsafe_allow_html=True)
