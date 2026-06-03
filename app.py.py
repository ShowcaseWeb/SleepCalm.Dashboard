# =============================================================================
# 🛏️ Sleep Calm - Dashboard de Compras (VERSIÓN CORREGIDA)
# =============================================================================
# INSTALACIÓN:
#   pip install streamlit pandas plotly requests openpyxl
#
# EJECUCIÓN:
#   streamlit run sleep_calm_dashboard.py
# =============================================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import requests
import io
import re
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")

# -----------------------------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="🛏️ Sleep Calm - Dashboard de Compras",
    page_icon="🛏️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# PALETA DE COLORES
# -----------------------------------------------------------------------------
AMARILLO = "#F5C518"
AZUL = "#3B82F6"
VERDE = "#10B981"
ROJO = "#EF4444"
GRIS = "#6B7280"
BLANCO = "#FFFFFF"
TEXTO = "#1F2937"

# -----------------------------------------------------------------------------
# FUNCIONES DE CONVERSIÓN
# -----------------------------------------------------------------------------
def parse_brl(valor):
    if pd.isna(valor) or str(valor).strip() in ("", "-", "nan"):
        return 0.0
    s = str(valor).strip()
    s = re.sub(r"R?\$?\s*", "", s)
    if '.' in s and ',' in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except:
        return 0.0

def parse_descuento(valor, valor_bruto=0):
    if pd.isna(valor) or str(valor).strip() in ("", "0", "nan"):
        return 0.0
    s = str(valor).strip()
    if "%" in s:
        pct = parse_brl(s.replace("%", ""))
        return valor_bruto * (pct / 100)
    return parse_brl(s)

def parse_fecha(fecha_str):
    try:
        return pd.to_datetime(fecha_str, format="%d/%m/%Y", errors="coerce")
    except:
        return pd.NaT

# -----------------------------------------------------------------------------
# CARGA DE DATOS DESDE GOOGLE SHEETS
# -----------------------------------------------------------------------------
@st.cache_data(ttl=300)
def cargar_datos():
    sheet_id = "1xW_gzy06SLHdTEsASx8rSDr1Um4dkEy5R92G2VLN7k8"
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
    
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(csv_url, headers=headers, timeout=30)
        response.raise_for_status()
        df = pd.read_csv(io.StringIO(response.text))
        
        if df.empty:
            raise ValueError("CSV vacío")
        
        return df, "Google Sheets (datos reales) ✅"
    except Exception as e:
        return None, f"Error: {str(e)[:50]}"

# -----------------------------------------------------------------------------
# DATOS DE RESPALDO
# -----------------------------------------------------------------------------
def datos_respaldo():
    datos = [
        ["23/01/2026", 169, "SEBIAN INDUSTRIA DE COLCHOES LTDA", "Atendido", "COLELEESP088000", "Colchão elemental Solteiro 88x188", 100, "R$393,86", "0"],
        ["23/01/2026", 169, "SEBIAN INDUSTRIA DE COLCHOES LTDA", "Atendido", "COLELEESP138000", "Colchão elemental Casal 138x188", 75, "R$585,62", "0"],
        ["02/02/2026", 171, "SEBIAN INDUSTRIA DE COLCHOES LTDA", "Atendido", "COLELEESP088000", "Colchão elemental Solteiro 88x188", 207, "R$393,86", "5%"],
        ["25/03/2026", 178, "SEBIAN INDUSTRIA DE COLCHOES LTDA", "Cancelado", "COLELEESP088000", "Colchão elemental Solteiro 88x188", 30, "R$393,86", "5%"],
        ["10/03/2026", 175, "SEBIAN INDUSTRIA DE COLCHOES LTDA", "Atendido", "COLELEESP088000", "Colchão elemental Solteiro 88x188", 240, "R$362,94", "0"],
        ["05/06/2026", 199, "SEBIAN INDUSTRIA DE COLCHOES LTDA", "Em aberto", "COLELEESP138000", "Colchão elemental Casal 138x188", 2, "R$611,97", "0"],
        ["13/04/2026", 180, "TRAVESSEIROS ELEVA COMERCIO LTDA", "Atendido", "TRADESINFFIB000", "Travesseiro ajustável Fibra", 20, "R$82,00", "0"],
        ["20/04/2026", 191, "SEBIAN INDUSTRIA DE COLCHOES LTDA", "Atendido", "COLELEESP088000", "Colchão elemental Solteiro 88x188", 129, "R$374,17", "3%"],
        ["20/04/2026", 192, "SEBIAN INDUSTRIA DE COLCHOES LTDA", "Atendido", "COLELEESP088000", "Colchão elemental Solteiro 88x188", 2, "R$374,17", "R$80,64"],
        ["10/06/2026", 201, "SEBIAN INDUSTRIA DE COLCHOES LTDA", "Em aberto", "COLELEESP088000", "Colchão elemental Solteiro 88x188", 62, "R$411,58", "0"],
    ]
    df = pd.DataFrame(datos, columns=["Data", "N° do pedido", "Nome do contato", "Situação", "Código", "Descrição", "Quantidade", "Valor unitário", "Desconto"])
    return df

# -----------------------------------------------------------------------------
# LIMPIEZA DE DATOS (CORREGIDA)
# -----------------------------------------------------------------------------
def limpiar_datos(df_raw):
    if df_raw is None or df_raw.empty:
        return pd.DataFrame()
    
    df = df_raw.copy()
    
    # Mostrar columnas disponibles para debug
    st.sidebar.write("📋 Columnas encontradas:", list(df.columns))
    
    # Mapeo flexible de columnas
    col_mapping = {}
    
    # Buscar cada columna por nombre aproximado
    for col in df.columns:
        col_lower = col.lower().strip()
        if "data" in col_lower:
            col_mapping["Data"] = col
        elif "pedido" in col_lower or "n°" in col_lower or "nro" in col_lower:
            col_mapping["Num_pedido"] = col
        elif "contato" in col_lower or "proveedor" in col_lower or "fornecedor" in col_lower or "nome" in col_lower:
            col_mapping["Proveedor"] = col
        elif "situação" in col_lower or "situacao" in col_lower or "estado" in col_lower:
            col_mapping["Situacao"] = col
        elif "código" in col_lower or "codigo" in col_lower:
            col_mapping["Codigo"] = col
        elif "produto" in col_lower and "id" in col_lower:
            col_mapping["ID_produto"] = col
        elif "descrição" in col_lower or "descricao" in col_lower:
            col_mapping["Descricao"] = col
        elif "quantidade" in col_lower or "qtd" in col_lower:
            col_mapping["Quantidade"] = col
        elif "valor unitário" in col_lower or "valor unitario" in col_lower or "preço" in col_lower:
            col_mapping["Valor_unitario"] = col
        elif "desconto" in col_lower:
            col_mapping["Desconto"] = col
    
    # Renombrar columnas encontradas
    for new_name, old_name in col_mapping.items():
        if old_name != new_name:
            df.rename(columns={old_name: new_name}, inplace=True)
    
    # Verificar columnas esenciales y crear si faltan
    if "Data" not in df.columns:
        st.error("❌ No se encontró columna de fecha")
        return pd.DataFrame()
    
    if "Num_pedido" not in df.columns:
        df["Num_pedido"] = range(1, len(df) + 1)
    
    if "Proveedor" not in df.columns:
        df["Proveedor"] = "Proveedor Desconocido"
    
    if "Situacao" not in df.columns:
        df["Situacao"] = "Atendido"
    
    if "Codigo" not in df.columns:
        df["Codigo"] = "SKU-" + df.index.astype(str)
    
    if "Descricao" not in df.columns:
        df["Descricao"] = "Producto " + df["Codigo"]
    
    if "Quantidade" not in df.columns:
        df["Quantidade"] = 1
    
    if "Valor_unitario" not in df.columns:
        df["Valor_unitario"] = 0
    
    if "Desconto" not in df.columns:
        df["Desconto"] = "0"
    
    # Convertir fecha
    df["Data"] = df["Data"].apply(parse_fecha)
    df = df.dropna(subset=["Data"])
    
    if df.empty:
        return df
    
    # Convertir cantidad
    df["Quantidade"] = pd.to_numeric(df["Quantidade"], errors="coerce").fillna(1).astype(int)
    
    # Convertir valor unitario
    df["Valor_unitario"] = df["Valor_unitario"].apply(parse_brl)
    
    # Calcular valor bruto
    df["Valor_bruto"] = df["Quantidade"] * df["Valor_unitario"]
    
    # Calcular descuento
    df["Desconto_valor"] = df.apply(lambda row: parse_descuento(row["Desconto"], row["Valor_bruto"]), axis=1)
    
    # Calcular valor total
    df["Valor_total"] = df["Valor_bruto"] - df["Desconto_valor"]
    df["Valor_total"] = df["Valor_total"].clip(lower=0)
    
    # Columnas de tiempo
    df["Ano"] = df["Data"].dt.year
    df["Mes"] = df["Data"].dt.month
    df["Ano_Mes"] = df["Data"].dt.to_period("M").astype(str)
    
    # Normalizar situación
    df["Situacao"] = df["Situacao"].fillna("Em aberto")
    df["Situacao"] = df["Situacao"].str.title()
    
    return df

# -----------------------------------------------------------------------------
# CARGA PRINCIPAL
# -----------------------------------------------------------------------------
with st.spinner("⏳ Cargando datos desde Google Sheets..."):
    df_raw, fonte = cargar_datos()
    
    if df_raw is None:
        st.warning("⚠️ No se pudo conectar a Google Sheets. Usando datos de respaldo.")
        df_raw = datos_respaldo()
        fonte = "Datos de respaldo (sin conexión) ⚠️"

df = limpiar_datos(df_raw)

if df.empty:
    st.error("❌ No se pudieron procesar los datos")
    st.stop()

st.success(f"✅ Datos cargados correctamente: {len(df)} registros")

# -----------------------------------------------------------------------------
# HEADER
# -----------------------------------------------------------------------------
st.markdown(f"""
<div style="background: linear-gradient(135deg, {AMARILLO} 0%, #D4A800 100%); 
            padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem;">
    <h1 style="color: #1F2937; margin: 0;">🛏️ Sleep Calm — Dashboard de Compras</h1>
    <p style="color: #1F2937; margin: 0.5rem 0 0; opacity: 0.8;">
        📊 {fonte} | 📅 {df["Data"].min().strftime("%d/%m/%Y")} → {df["Data"].max().strftime("%d/%m/%Y")} | 
        📦 {len(df):,} ítems | 🧾 {df["Num_pedido"].nunique()} pedidos
    </p>
</div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# SIDEBAR - FILTROS
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🎯 Filtros")
    st.markdown("---")
    
    fecha_min = df["Data"].min().date()
    fecha_max = df["Data"].max().date()
    f_ini = st.date_input("📅 Desde", fecha_min)
    f_fin = st.date_input("📅 Hasta", fecha_max)
    
    pedidos_opts = ["Todos"] + sorted(df["Num_pedido"].dropna().unique().tolist())
    sel_pedido = st.selectbox("🧾 N° do pedido", pedidos_opts)
    
    proveedores_opts = ["Todos"] + sorted(df["Proveedor"].dropna().unique().tolist())
    sel_proveedor = st.selectbox("🏭 Proveedor", proveedores_opts)
    
    sit_opts = ["Todos"] + sorted(df["Situacao"].dropna().unique().tolist())
    sel_sit = st.selectbox("📌 Situación", sit_opts)
    
    busqueda = st.text_input("🔎 Buscar (código/producto)", "")
    
    st.markdown("---")
    if st.button("🔄 Actualizar datos"):
        st.cache_data.clear()
        st.rerun()

# -----------------------------------------------------------------------------
# APLICAR FILTROS
# -----------------------------------------------------------------------------
dff = df.copy()
dff = dff[(dff["Data"].dt.date >= f_ini) & (dff["Data"].dt.date <= f_fin)]

if sel_pedido != "Todos":
    dff = dff[dff["Num_pedido"] == sel_pedido]

if sel_proveedor != "Todos":
    dff = dff[dff["Proveedor"] == sel_proveedor]

if sel_sit != "Todos":
    dff = dff[dff["Situacao"] == sel_sit]

if busqueda.strip():
    mask = (dff["Codigo"].astype(str).str.contains(busqueda, case=False, na=False) |
            dff["Descricao"].astype(str).str.contains(busqueda, case=False, na=False))
    dff = dff[mask]

if dff.empty:
    st.warning("⚠️ No hay datos con los filtros seleccionados")
    st.stop()

# -----------------------------------------------------------------------------
# CÁLCULOS
# -----------------------------------------------------------------------------
total_valor = dff["Valor_total"].sum()
total_items = dff["Quantidade"].sum()
total_pedidos = dff["Num_pedido"].nunique()
total_proveedores = dff["Proveedor"].nunique()
ticket_medio = total_valor / total_pedidos if total_pedidos > 0 else 0

ped_grp = dff.groupby("Num_pedido")["Valor_total"].sum().reset_index()
mejor_valor = ped_grp["Valor_total"].max() if not ped_grp.empty else 0
mejor_pedido = ped_grp.loc[ped_grp["Valor_total"].idxmax(), "Num_pedido"] if not ped_grp.empty else "-"

atendidos = len(dff[dff["Situacao"].str.lower() == "atendido"])
taxa_cump = (atendidos / len(dff) * 100) if len(dff) > 0 else 0

# -----------------------------------------------------------------------------
# KPIs
# -----------------------------------------------------------------------------
st.markdown("## 📊 Indicadores Clave")

col1, col2, col3, col4, col5, col6 = st.columns(6)

with col1:
    st.metric("💰 Total Comprado", f"R$ {total_valor:,.0f}".replace(",", "."))

with col2:
    st.metric("📦 Total Ítems", f"{total_items:,}".replace(",", "."))

with col3:
    st.metric("🧾 Pedidos", f"{total_pedidos}")

with col4:
    st.metric("🏭 Proveedores", f"{total_proveedores}")

with col5:
    st.metric("🎯 Ticket Promedio", f"R$ {ticket_medio:,.0f}".replace(",", "."))

with col6:
    st.metric("✅ Cumplimiento", f"{taxa_cump:.0f}%")

# -----------------------------------------------------------------------------
# GRÁFICOS
# -----------------------------------------------------------------------------
st.markdown("## 📈 Análisis Visual")

# Gráfico 1 y 2
col1, col2 = st.columns(2)

with col1:
    top_pedidos = dff.groupby("Num_pedido")["Valor_total"].sum().nlargest(10)
    if not top_pedidos.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=top_pedidos.index.astype(str),
            y=top_pedidos.values,
            marker_color=AMARILLO,
            text=[f"R$ {v:,.0f}" for v in top_pedidos.values],
            textposition="outside"
        ))
        fig.update_layout(title="Top 10 Pedidos por Valor", height=400)
        st.plotly_chart(fig, use_container_width=True)

with col2:
    top_sku = dff.groupby(["Codigo", "Descricao"])["Quantidade"].sum().nlargest(10).reset_index()
    if not top_sku.empty:
        top_sku["label"] = top_sku["Codigo"].astype(str) + " - " + top_sku["Descricao"].astype(str).str[:30]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=top_sku["label"][::-1],
            x=top_sku["Quantidade"][::-1],
            orientation="h",
            marker_color=AZUL,
            text=top_sku["Quantidade"][::-1].apply(lambda x: f"{x:,}"),
            textposition="outside"
        ))
        fig.update_layout(title="Top 10 SKUs por Cantidad", height=400)
        st.plotly_chart(fig, use_container_width=True)

# Gráfico 3 y 4
col3, col4 = st.columns(2)

with col3:
    top_prov = dff.groupby("Proveedor")["Valor_total"].sum().nlargest(10).reset_index()
    if not top_prov.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=top_prov["Proveedor"][::-1],
            x=top_prov["Valor_total"][::-1],
            orientation="h",
            marker_color=VERDE,
            text=[f"R$ {v:,.0f}" for v in top_prov["Valor_total"][::-1]],
            textposition="outside"
        ))
        fig.update_layout(title="Top 10 Proveedores por Valor", height=400)
        st.plotly_chart(fig, use_container_width=True)

with col4:
    sit_data = dff.groupby("Situacao")["Valor_total"].sum().reset_index()
    if not sit_data.empty:
        colores = {"Atendido": VERDE, "Em aberto": AMARILLO, "Cancelado": ROJO}
        fig = go.Figure(data=[go.Pie(
            labels=sit_data["Situacao"],
            values=sit_data["Valor_total"],
            hole=0.4,
            marker_colors=[colores.get(s, GRIS) for s in sit_data["Situacao"]],
            textinfo="label+percent+value",
            textposition="auto"
        )])
        fig.update_layout(title="Distribución por Situación", height=400)
        st.plotly_chart(fig, use_container_width=True)

# Gráfico 5: Evolución Mensual
st.markdown("---")
mensual = dff.groupby("Ano_Mes").agg(Valor=("Valor_total", "sum"), Items=("Quantidade", "sum")).reset_index().sort_values("Ano_Mes")

if not mensual.empty:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=mensual["Ano_Mes"],
        y=mensual["Valor"],
        name="Valor (R$)",
        marker_color=AMARILLO,
        text=[f"R$ {v:,.0f}" for v in mensual["Valor"]],
        textposition="outside"
    ))
    fig.add_trace(go.Scatter(
        x=mensual["Ano_Mes"],
        y=mensual["Items"],
        name="Ítems",
        mode="lines+markers",
        line=dict(color=AZUL, width=3),
        marker=dict(size=8),
        text=mensual["Items"].apply(lambda x: f"{x:,}"),
        textposition="top center",
        yaxis="y2"
    ))
    fig.update_layout(
        title="Evolución Mensual de Compras",
        height=450,
        xaxis_title="Mes",
        yaxis_title="Valor (R$)",
        yaxis2=dict(title="Cantidad de Ítems", overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02)
    )
    st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------------------------------------------
# TABLAS
# -----------------------------------------------------------------------------
st.markdown("## 📋 Datos Detallados")

tab1, tab2, tab3 = st.tabs(["📄 Todos los Ítems", "🧾 Por Pedido", "🏭 Por Proveedor"])

with tab1:
    tabla = dff[["Data", "Num_pedido", "Proveedor", "Descricao", "Codigo", "Quantidade", "Valor_unitario", "Valor_total", "Situacao"]].copy()
    tabla["Data"] = tabla["Data"].dt.strftime("%d/%m/%Y")
    tabla["Valor_unitario"] = tabla["Valor_unitario"].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    tabla["Valor_total"] = tabla["Valor_total"].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    tabla.columns = ["Fecha", "Pedido", "Proveedor", "Descripción", "Código", "Cant.", "Valor Unit.", "Valor Total", "Situación"]
    st.dataframe(tabla, use_container_width=True)
    csv_data = tabla.to_csv(index=False, encoding="utf-8-sig")
    st.download_button("📥 Descargar CSV - Ítems", csv_data, "sleep_calm_items.csv", "text/csv")

with tab2:
    tabla2 = dff.groupby("Num_pedido").agg(
        Fecha=("Data", "first"),
        Proveedor=("Proveedor", "first"),
        Situacion=("Situacao", "first"),
        Items=("Quantidade", "sum"),
        Valor=("Valor_total", "sum")
    ).reset_index()
    tabla2["Fecha"] = tabla2["Fecha"].dt.strftime("%d/%m/%Y")
    tabla2["Valor"] = tabla2["Valor"].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    tabla2.columns = ["Pedido", "Fecha", "Proveedor", "Situación", "Total Items", "Valor Total"]
    st.dataframe(tabla2, use_container_width=True)
    csv_data2 = tabla2.to_csv(index=False, encoding="utf-8-sig")
    st.download_button("📥 Descargar CSV - Pedidos", csv_data2, "sleep_calm_pedidos.csv", "text/csv")

with tab3:
    tabla3 = dff.groupby("Proveedor").agg(
        Pedidos=("Num_pedido", "nunique"),
        Items=("Quantidade", "sum"),
        Valor=("Valor_total", "sum")
    ).reset_index().sort_values("Valor", ascending=False)
    tabla3["Valor"] = tabla3["Valor"].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    tabla3.columns = ["Proveedor", "Pedidos", "Total Items", "Valor Total"]
    st.dataframe(tabla3, use_container_width=True)
    csv_data3 = tabla3.to_csv(index=False, encoding="utf-8-sig")
    st.download_button("📥 Descargar CSV - Proveedores", csv_data3, "sleep_calm_proveedores.csv", "text/csv")

# -----------------------------------------------------------------------------
# RESUMEN EJECUTIVO
# -----------------------------------------------------------------------------
st.markdown("## 🌟 Resumen Ejecutivo")

col_r1, col_r2, col_r3, col_r4 = st.columns(4)

with col_r1:
    prod_top = dff.groupby("Descricao")["Quantidade"].sum().nlargest(1)
    if not prod_top.empty:
        st.info(f"⭐ **Producto Estrella**\n\n{prod_top.index[0][:35]}\n\n📦 {prod_top.values[0]:,} unidades")

with col_r2:
    mejor_mes = dff.groupby("Ano_Mes")["Valor_total"].sum().nlargest(1)
    if not mejor_mes.empty:
        st.success(f"📈 **Mejor Mes**\n\n{mejor_mes.index[0]}\n\n💰 R$ {mejor_mes.values[0]:,.0f}".replace(",", "."))

with col_r3:
    mejor_prov = dff.groupby("Proveedor")["Valor_total"].sum().nlargest(1)
    if not mejor_prov.empty:
        pct = (mejor_prov.values[0] / total_valor * 100) if total_valor > 0 else 0
        st.warning(f"🏆 **Principal Proveedor**\n\n{mejor_prov.index[0][:30]}\n\n{pct:.1f}% del total")

with col_r4:
    st.metric("✅ **Tasa de Cumplimiento**", f"{taxa_cump:.1f}%", f"{atendidos} de {len(dff)} ítems")

# -----------------------------------------------------------------------------
# FOOTER
# -----------------------------------------------------------------------------
st.markdown(f"""
<div style="text-align: center; color: #6B7280; font-size: 0.75rem; padding: 1.5rem 0; margin-top: 1rem; border-top: 1px solid #E5E7EB;">
    🛏️ Sleep Calm Dashboard | Actualizado: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")} | {len(dff):,} registros filtrados
</div>
""", unsafe_allow_html=True)
