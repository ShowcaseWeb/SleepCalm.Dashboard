"""
================================================================================
SLEEP CALM - LOGISTICS ENTERPRISE
Sistema Corporativo de Monitoramento de Entregas
Versao: 10.5 - SLA Corrigido (PT/ES)
================================================================================
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# =============================================================================
# 1. CONSTANTES GLOBAIS
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

MESES_NOMES = ["Jan","Fev","Mar","Abr","Mai","Jun",
               "Jul","Ago","Set","Out","Nov","Dez"]

# =============================================================================
# 2. SISTEMA DE TRADUCAO
# =============================================================================

_TEXTS = {
    "title":              {"pt": "Sleep Calm - Logistics Enterprise",             "es": "Sleep Calm - Logistics Enterprise"},
    "subtitle":           {"pt": "Sistema Corporativo de Monitoramento de Entregas","es": "Sistema Corporativo de Monitoreo de Entregas"},
    "period":             {"pt": "Periodo",         "es": "Periodo"},
    "meta_sla":           {"pt": "Meta SLA",         "es": "Meta SLA"},
    "total_orders":       {"pt": "TOTAL PEDIDOS",    "es": "TOTAL PEDIDOS"},
    "sla":                {"pt": "SLA",              "es": "SLA"},
    "on_time":            {"pt": "ENTREGAS NO PRAZO","es": "ENTREGAS A TIEMPO"},
    "delayed":            {"pt": "ATRASADOS",        "es": "ATRASADOS"},
    "in_process":         {"pt": "EM PROCESSO",      "es": "EN PROCESO"},
    "shipped":            {"pt": "DESPACHADOS",      "es": "DESPACHADOS"},
    "not_delivered":      {"pt": "NAO ENTREGUES",    "es": "NO ENTREGADOS"},
    "chart_sla_monthly":  {"pt": "SLA por Mes - Comparativo Anual",              "es": "SLA por Mes - Comparativo Anual"},
    "chart_sla_trend":    {"pt": "Tendencia do SLA",  "es": "Tendencia del SLA"},
    "chart_sla_carrier":  {"pt": "SLA por Transportadora",                       "es": "SLA por Transportadora"},
    "chart_comparison":   {"pt": "No Prazo vs Atrasado por Transportadora",      "es": "A Tiempo vs Atrasado por Transportadora"},
    "chart_sla_state":    {"pt": "SLA por Estado (UF)",                          "es": "SLA por Estado (UF)"},
    "chart_top_skus":     {"pt": "Top 10 SKUs Mais Vendidos",                    "es": "Top 10 SKUs Mas Vendidos"},
    "chart_status":       {"pt": "Distribuicao de Status",                       "es": "Distribucion de Estados"},
    "chart_delay_dist":   {"pt": "Distribuicao de Dias de Atraso",               "es": "Distribucion de Dias de Atraso"},
    "chart_aging":        {"pt": "Aging de Pedidos Abertos",                     "es": "Aging de Pedidos Abiertos"},
    "chart_avg_time":     {"pt": "Tempo Medio de Entrega por Transportadora",    "es": "Tiempo Promedio de Entrega por Transportadora"},
    "critical_orders":    {"pt": "Pedidos Criticos (Nao Entregues)",             "es": "Pedidos Criticos (No Entregados)"},
    "no_pending":         {"pt": "Nenhum pedido pendente de entrega!",           "es": "Ningun pedido pendiente de entrega!"},
    "filters":            {"pt": "Filtros",           "es": "Filtros"},
    "year":               {"pt": "Ano",               "es": "Ano"},
    "month":              {"pt": "Mes",               "es": "Mes"},
    "all":                {"pt": "Todos",             "es": "Todos"},
    "compare":            {"pt": "Comparar com ano anterior",                    "es": "Comparar con ano anterior"},
    "carrier":            {"pt": "Transportadora",    "es": "Transportadora"},
    "state":              {"pt": "UF",                "es": "Estado"},
    "returns":            {"pt": "Devolucao",         "es": "Devolucion"},
    "how_sla":            {"pt": "Como o SLA e calculado?",                      "es": "Como se calcula el SLA?"},
    "sla_formula":        {"pt": "SLA = (Entregues no Prazo / Total Entregues) x 100",
                                                                                 "es": "SLA = (Entregas a Tiempo / Total Entregas) x 100"},
    "sla_note":           {"pt": "Apenas pedidos com status 'wc-completed' sao considerados",
                                                                                 "es": "Solo pedidos con estado 'wc-completed' son considerados"},
    "footer":             {"pt": "Sleep Calm - Logistics Enterprise",            "es": "Sleep Calm - Logistics Enterprise"},
    "updated":            {"pt": "Atualizado",        "es": "Actualizado"},
    "data_warnings":      {"pt": "Alertas de Qualidade de Dados",                "es": "Alertas de Calidad de Datos"},
    "avg_delivery_days":  {"pt": "Tempo Medio de Entrega",                       "es": "Tiempo Promedio de Entrega"},
    "days":               {"pt": "dias",              "es": "dias"},
    "ranking_carrier":    {"pt": "Ranking de Transportadoras",                   "es": "Ranking de Transportadoras"},
    "on_hold":            {"pt": "ON-HOLD",           "es": "EN ESPERA"},
}

def t(key):
    lang = st.session_state.get("language", "pt")
    return _TEXTS.get(key, {}).get(lang, key)

# =============================================================================
# 3. CAMADA DE DADOS
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

@st.cache_data(ttl=300, show_spinner="Carregando dados...")
def load_data():
    audit = {"warnings": [], "duplicates_removed": 0, "invalid_ontime": 0}

    try:
        df = pd.read_csv(SHEET_URL)
    except Exception as e:
        st.error(f"Erro ao carregar planilha: {e}")
        return pd.DataFrame(), audit

    missing = _validate_columns(df)
    if missing:
        audit["warnings"].append(f"Colunas ausentes: {missing}")

    df = _parse_dates(df)

    if "On Time" in df.columns:
        original_ontime = df["On Time"].copy()
        df["On Time"] = _normalize_ontime(df["On Time"])
        invalid_count = int((df["On Time"].isna() & original_ontime.notna()).sum())
        if invalid_count:
            audit["warnings"].append(f"{invalid_count} valor(es) invalido(s) em 'On Time' foram ignorados.")

    if "numero_pedido" in df.columns:
        before = len(df)
        df = df.drop_duplicates(subset=["numero_pedido"], keep="last")
        removed = before - len(df)
        if removed:
            audit["duplicates_removed"] = removed
            audit["warnings"].append(f"{removed} pedido(s) duplicado(s) removido(s).")

    df["ano"] = df["fecha"].dt.year
    df["mes"] = df["fecha"].dt.month
    df["mes_nome"] = df["fecha"].dt.strftime("%b")

    if "Compromiso de entrega" in df.columns:
        df["dias_ate_entrega"] = (df["Compromiso de entrega"] - df["fecha"]).dt.days

    return df, audit

# =============================================================================
# 4. CAMADA DE METRICAS (CORRIGIDA - SLA REAL)
# =============================================================================

def calcular_sla(df_):
    """
    Calcula SLA considerando que:
    - Pedidos wc-completed SEM classificação em 'On Time' são contados como ATRASADOS
    - Isso porque se o pedido foi entregue (completed), precisa ser avaliado
    """
    resultado = {"sla": 0.0, "no_prazo": 0, "total_entregues": 0, "atrasados": 0, "sem_classificacao": 0, "valido": False, "alerta": None}

    if df_.empty or "estado" not in df_.columns:
        return resultado

    entregues = df_[df_["estado"] == STATUS_COMPLETED].copy()
    total_entregues = len(entregues)

    if total_entregues == 0:
        return resultado

    no_prazo = int((entregues["On Time"] == "On Time").sum())
    atrasados_classificados = int((entregues["On Time"] == "No ontime").sum())
    sem_classificacao = total_entregues - no_prazo - atrasados_classificados

    # REGRA DE NEGÓCIO: pedidos sem classificação contam como ATRASADOS
    atrasados = atrasados_classificados + sem_classificacao

    resultado["sem_classificacao"] = sem_classificacao
    if sem_classificacao > 0:
        resultado["alerta"] = f"⚠️ {sem_classificacao} pedido(s) entregues sem classificação 'On Time' - contados como ATRASADOS."

    sla = round(no_prazo / total_entregues * 100, 2)

    if sla > 100:
        resultado["alerta"] = f"SLA invalido: {sla}% > 100%."
        sla = 100.0
    if sla < 0:
        resultado["alerta"] = f"SLA invalido: {sla}% < 0%."
        sla = 0.0

    resultado.update({
        "sla": sla, 
        "no_prazo": no_prazo, 
        "total_entregues": total_entregues, 
        "atrasados": atrasados,
        "valido": True
    })
    return resultado

def calcular_sla_mensal(df_, ano, ufs=None, transportadoras=None):
    """
    Calcula SLA mensal para UM ano específico.
    Pedidos sem classificação contam como ATRASADOS.
    """
    mask = df_["ano"] == ano
    if ufs:
        mask &= df_["UF"].isin(ufs)
    if transportadoras:
        mask &= df_["Proveedor"].isin(transportadoras)

    sub = df_[mask & (df_["estado"] == STATUS_COMPLETED)].copy()
    if sub.empty:
        return pd.Series(0.0, index=range(1, 13))

    def calc_sla_grupo(g):
        total = len(g)
        if total == 0:
            return 0.0
        no_prazo = (g["On Time"] == "On Time").sum()
        # sem classificação contam como atrasado (não entram no no_prazo)
        return round(no_prazo / total * 100, 2)

    grp = sub.groupby("mes").apply(calc_sla_grupo)
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
        SemClassif = ("On Time", lambda x: x.isna().sum()),
    ).reset_index()

    # Ajusta atrasados para incluir sem classificação
    grp["Atrasados"] = grp["Atrasados"] + grp["SemClassif"]
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
# 5. CAMADA DE VISUALIZACAO
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

def fig_sla_mensal(sla_atual, sla_ant, ano_sel, comparar):
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
    lang = st.session_state.get("language", "pt")
    labels_map = {
        "pt": {STATUS_COMPLETED: "Entregue", STATUS_PROCESSING: "Em Processo", STATUS_SHIPPED: "Despachado",
               STATUS_ON_HOLD: "On-Hold", STATUS_CANCELLED: "Cancelado"},
        "es": {STATUS_COMPLETED: "Entregado", STATUS_PROCESSING: "En Proceso", STATUS_SHIPPED: "Despachado",
               STATUS_ON_HOLD: "En Espera", STATUS_CANCELLED: "Cancelado"},
    }
    counts = df_["estado"].value_counts().reset_index()
    counts.columns = ["Status", "Quantidade"]
    counts["Status"] = counts["Status"].map(labels_map[lang]).fillna(counts["Status"])
    fig = px.pie(counts, values="Quantidade", names="Status", hole=0.45,
                 color_discrete_sequence=[COLOR_SUCCESS, COLOR_WARNING, COLOR_CYAN, COLOR_DANGER, COLOR_NEUTRAL])
    fig.update_traces(textinfo="label+percent", textfont_size=12)
    _apply_layout(fig, height=420, showlegend=True)
    return fig

def fig_delay_distribution(df_):
    if "Dias de demora" not in df_.columns:
        return None
    
    atrasos_raw = pd.to_numeric(df_["Dias de demora"], errors='coerce')
    # Inclui todos os entregues que estão atrasados (classificados OU sem classificação)
    mask_atrasados = (df_["estado"] == STATUS_COMPLETED) & (df_["On Time"] != "On Time")
    atrasos = atrasos_raw[mask_atrasados].dropna()
    
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
# 6. CONFIGURACAO DA PAGINA E CSS
# =============================================================================

st.set_page_config(page_title="Sleep Calm - Logistics", page_icon="📦", layout="wide", initial_sidebar_state="expanded")

if "language" not in st.session_state:
    st.session_state.language = "pt"

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
    st.error("Nao foi possivel carregar os dados. Verifique a conexao com a planilha.")
    st.stop()

hoje = datetime.now()

# =============================================================================
# 8. SIDEBAR
# =============================================================================

with st.sidebar:
    st.markdown("""<div style="text-align:center;padding:1rem 0 0.5rem">
      <div style="font-size:2.8rem">📦</div>
      <div style="font-weight:700;font-size:1.1rem;color:white">Sleep Calm</div>
      <div style="font-size:0.7rem;color:#64748b">Logistics Enterprise v10.5</div>
    </div>""", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### 🌐 Idioma / Language")
    col_pt, col_es = st.columns(2)
    with col_pt:
        if st.button("Portugues", use_container_width=True):
            st.session_state.language = "pt"
            st.rerun()
    with col_es:
        if st.button("Espanol", use_container_width=True):
            st.session_state.language = "es"
            st.rerun()
    st.markdown("---")
    st.markdown(f"### Filtros")
    anos_disp = sorted(df_raw["ano"].dropna().unique().astype(int))
    ano_sel = st.selectbox("Ano", anos_disp, index=len(anos_disp) - 1)
    meses_disp = ["Todos"] + MESES_NOMES
    mes_sel = st.selectbox("Mes", meses_disp, index=0)
    comparar = st.checkbox("Comparar com ano anterior", value=True)
    st.markdown("---")
    ufs_disp = sorted(df_raw["UF"].dropna().unique()) if "UF" in df_raw.columns else []
    transp_disp = sorted(df_raw["Proveedor"].dropna().unique()) if "Proveedor" in df_raw.columns else []
    ufs_sel = st.multiselect("UF", ufs_disp, placeholder="Todos")
    transp_sel = st.multiselect("Transportadora", transp_disp, placeholder="Todas")
    st.markdown("---")
    st.link_button("Registrar Devolucao", "https://script.google.com/a/macros/sleepcalm.com.br/s/AKfycbzyOsb6FzdRee9Mn88h86fPx7B7ZmZoxNZLP-brNgUZr9-BRFhW3Dt49_QeRe59Mhg6yg/exec", use_container_width=True)
    
    st.markdown("---")
    st.markdown("### 📊 Regra do SLA")
    st.info("Pedidos entregues (wc-completed) sem classificação em 'On Time' são contados como **ATRASADOS**.")

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
sem_classif = metricas.get("sem_classificacao", 0)
delta_sla = round(sla - metricas_ant["sla"], 1) if metricas_ant else 0.0
cor_sla = _color_sla(sla)

periodo_txt = f"{mes_sel} de {ano_sel}" if mes_sel != "Todos" else f"Ano {ano_sel}"
st.markdown(f"""
<div class="sc-header">
  <div style="display:flex;justify-content:space-between;align-items:center">
    <div><h1>📦 Sleep Calm - Logistics Enterprise</h1>
    <p>Sistema Corporativo de Monitoramento de Entregas | Periodo: <strong>{periodo_txt}</strong> | Meta SLA: <strong>{META_SLA}%</strong></p></div>
    <div style="font-size:0.7rem;background:rgba(255,255,255,0.15);padding:0.4rem 1rem;border-radius:20px;color:white">v10.5</div>
  </div>
</div>""", unsafe_allow_html=True)

if audit_log["warnings"]:
    with st.expander("Alertas de Qualidade de Dados", expanded=False):
        for w in audit_log["warnings"]:
            st.markdown(f'<div class="warn-badge">{w}</div>', unsafe_allow_html=True)
if metricas.get("alerta"):
    st.markdown(f'<div class="alert-badge">{metricas["alerta"]}</div>', unsafe_allow_html=True)
if sem_classif > 0:
    st.markdown(f'<div class="warn-badge">⚠️ {sem_classif} pedido(s) entregues sem classificaÃ§Ã£o em "On Time" foram contados como ATRASADOS.</div>', unsafe_allow_html=True)

# =============================================================================
# 11. KPI CARDS
# =============================================================================

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""<div class="kpi-card"><div class="kpi-label">TOTAL PEDIDOS</div>
    <div class="kpi-value">{metricas['total_pedidos']:,}</div>
    <div class="kpi-detail">Entregues: {total_ent:,} | Cancelados: {metricas['cancelados']:,}</div></div>""", unsafe_allow_html=True)
with c2:
    trend_html = f'<span style="color:#10b981">▲ {delta_sla:+.1f}pp</span>' if delta_sla >= 0 else f'<span style="color:#ef4444">▼ {abs(delta_sla):.1f}pp</span>'
    st.markdown(f"""<div class="kpi-card"><div class="kpi-label">SLA</div>
    <div class="kpi-value" style="color:{cor_sla}">{sla:.1f}%</div>
    <div class="kpi-detail">Meta: {META_SLA}% {trend_html}</div></div>""", unsafe_allow_html=True)
with c3:
    pct = f"{no_prazo/total_ent*100:.1f}%" if total_ent > 0 else "--"
    st.markdown(f"""<div class="kpi-card" style="border-left-color:{COLOR_SUCCESS}">
    <div class="kpi-label">ENTREGAS NO PRAZO</div>
    <div class="kpi-value" style="color:{COLOR_SUCCESS}">{no_prazo:,}</div>
    <div class="kpi-detail">{pct} de {total_ent:,} entregues</div></div>""", unsafe_allow_html=True)
with c4:
    pct_a = f"{atrasados/total_ent*100:.1f}%" if total_ent > 0 else "--"
    st.markdown(f"""<div class="kpi-card" style="border-left-color:{COLOR_DANGER}">
    <div class="kpi-label">ATRASADOS</div>
    <div class="kpi-value" style="color:{COLOR_DANGER}">{atrasados:,}</div>
    <div class="kpi-detail">{pct_a} de {total_ent:,} entregues</div></div>""", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""<div class="kpi-card"><div class="kpi-label">EM PROCESSO</div>
    <div class="kpi-value">{metricas['processando']}</div></div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<div class="kpi-card"><div class="kpi-label">DESPACHADOS</div>
    <div class="kpi-value">{metricas['despachado']}</div></div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""<div class="kpi-card"><div class="kpi-label">ON-HOLD</div>
    <div class="kpi-value">{metricas['on_hold']}</div></div>""", unsafe_allow_html=True)
with c4:
    avg_d = metricas.get("avg_delivery_days")
    avg_txt = f"{avg_d:.1f} dias" if avg_d is not None and not np.isnan(avg_d) else "--"
    st.markdown(f"""<div class="kpi-card" style="border-left-color:{COLOR_CYAN}">
    <div class="kpi-label">TEMPO MEDIO DE ENTREGA</div>
    <div class="kpi-value" style="color:{COLOR_CYAN}">{avg_txt}</div>
    <div class="kpi-detail">entregues no prazo</div></div>""", unsafe_allow_html=True)

st.markdown("---")

# =============================================================================
# 12. GRAFICOS
# =============================================================================

st.markdown('<div class="section-title">1. SLA por Mes - Comparativo Anual</div>', unsafe_allow_html=True)
sla_atual = calcular_sla_mensal(df_raw, ano_sel, ufs_sel, transp_sel)
sla_ant_s = calcular_sla_mensal(df_raw, ano_sel - 1, ufs_sel, transp_sel) if comparar else None
st.plotly_chart(fig_sla_mensal(sla_atual, sla_ant_s, ano_sel, comparar), use_container_width=True)

st.markdown('<div class="section-title">2. Tendencia do SLA</div>', unsafe_allow_html=True)
st.plotly_chart(fig_tendencia(sla_atual), use_container_width=True)

st.markdown('<div class="section-title">3. SLA por Transportadora</div>', unsafe_allow_html=True)
df_transp_grp = calcular_sla_por_grupo(df, "Proveedor")
if not df_transp_grp.empty:
    st.plotly_chart(fig_sla_horizontal(df_transp_grp, "Proveedor"), use_container_width=True)
else:
    st.info("Sem dados de transportadora para o periodo selecionado.")

st.markdown('<div class="section-title">4. No Prazo vs Atrasado por Transportadora</div>', unsafe_allow_html=True)
if not df_transp_grp.empty:
    st.plotly_chart(fig_comparacao_transp(df_transp_grp), use_container_width=True)

st.markdown('<div class="section-title">5. SLA por Estado (UF)</div>', unsafe_allow_html=True)
df_uf_grp = calcular_sla_por_grupo(df, "UF")
if not df_uf_grp.empty:
    st.plotly_chart(fig_sla_horizontal(df_uf_grp, "UF"), use_container_width=True)
else:
    st.info("Sem dados de UF para o periodo selecionado.")

st.markdown('<div class="section-title">6. Top 10 SKUs Mais Vendidos</div>', unsafe_allow_html=True)
f_skus = fig_top_skus(df)
if f_skus:
    st.plotly_chart(f_skus, use_container_width=True)
else:
    st.info("Coluna 'sku' nao encontrada.")

st.markdown('<div class="section-title">7. Distribuicao de Status</div>', unsafe_allow_html=True)
st.plotly_chart(fig_status_pie(df), use_container_width=True)

st.markdown('<div class="section-title">8. Distribuicao de Dias de Atraso</div>', unsafe_allow_html=True)
f_delay = fig_delay_distribution(df)
if f_delay:
    st.plotly_chart(f_delay, use_container_width=True)
else:
    st.info("Sem dados de atraso para o periodo selecionado.")

st.markdown('<div class="section-title">9. Aging de Pedidos Abertos</div>', unsafe_allow_html=True)
df_abertos = df[~df["estado"].isin([STATUS_COMPLETED, STATUS_CANCELLED])].copy()
if not df_abertos.empty and "fecha" in df_abertos.columns:
    df_abertos["dias_em_aberto"] = (hoje - df_abertos["fecha"]).dt.days.clip(lower=0)
    f_aging = fig_aging(df_abertos)
    if f_aging:
        st.plotly_chart(f_aging, use_container_width=True)
    else:
        st.success("Nenhum pedido pendente de entrega!")
else:
    st.success("Nenhum pedido pendente de entrega!")

st.markdown('<div class="section-title">10. Tempo Medio de Entrega por Transportadora</div>', unsafe_allow_html=True)
f_avg = fig_tempo_medio_transportadora(df)
if f_avg:
    st.plotly_chart(f_avg, use_container_width=True)
else:
    st.info("Dados insuficientes para calcular tempo medio de entrega.")

st.markdown("---")

# =============================================================================
# 13. PEDIDOS CRITICOS
# =============================================================================

st.markdown('<div class="section-title">11. Pedidos Criticos (Nao Entregues)</div>', unsafe_allow_html=True)

if not df_abertos.empty:
    colunas_exibir = [c for c in ["numero_pedido", "Proveedor", "UF", "sku", "Compromiso de entrega", "dias_em_aberto", "estado"] if c in df_abertos.columns]
    df_abertos_display = df_abertos.copy()
    if "Compromiso de entrega" in df_abertos_display.columns:
        df_abertos_display["Compromiso de entrega"] = df_abertos_display["Compromiso de entrega"].dt.strftime("%d/%m/%Y")
    st.dataframe(df_abertos_display[colunas_exibir].sort_values("dias_em_aberto", ascending=False).head(50), use_container_width=True)
    st.caption(f"Total: {len(df_abertos)} pedidos criticos")
    csv_bytes = df_abertos.to_csv(index=False).encode("utf-8")
    st.download_button("Download Pedidos Criticos", csv_bytes, f"critical_orders_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")
else:
    st.success("Nenhum pedido pendente de entrega!")

# =============================================================================
# 14. RANKING DE TRANSPORTADORAS
# =============================================================================

st.markdown('<div class="section-title">12. Ranking de Transportadoras</div>', unsafe_allow_html=True)
if not df_transp_grp.empty:
    df_rank = df_transp_grp.sort_values("SLA", ascending=False).reset_index(drop=True)
    df_rank.index = df_rank.index + 1
    df_rank["SLA"] = df_rank["SLA"].apply(lambda x: f"{x:.1f}%")
    st.dataframe(df_rank[["Proveedor", "SLA", "Entregues", "NoPrazo", "Atrasados"]], use_container_width=True)

# =============================================================================
# 15. EXPLICACAO DO SLA
# =============================================================================

with st.expander("Como o SLA e calculado?"):
    st.markdown(f"""
**Formula do SLA:** SLA = (Entregues no Prazo / Total Entregues) x 100

**O que e considerado:** Apenas pedidos com status 'wc-completed'

**Meta atual:** {META_SLA}%

**⚠️ Regra importante:** Pedidos entregues (wc-completed) que NAO possuem classificacao na coluna 'On Time' sao contados como **ATRASADOS**.

**Regras de negocio aplicadas:**
- Pedidos com estado wc-cancelled sao excluidos do calculo.
- A coluna On Time e normalizada antes do calculo.
- Pedidos duplicados por numero_pedido sao removidos na carga.
- Alertas automaticos sao emitidos quando ha dados ausentes.
    """)

# =============================================================================
# 16. RODAPE
# =============================================================================

st.markdown(f"""
<div style="text-align:center;padding:1.5rem 0 0.5rem;color:#64748b;font-size:0.7rem;border-top:1px solid {GRID_COLOR};margin-top:1.5rem">
  Sleep Calm - Logistics Enterprise | Meta SLA: {META_SLA}% | Atualizado: {hoje.strftime('%d/%m/%Y %H:%M')}
</div>
""", unsafe_allow_html=True)
