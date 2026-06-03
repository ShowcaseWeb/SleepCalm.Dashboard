# =============================================================================
# DEBUG FORÇADO - Analisar Maio/2025
# =============================================================================

with st.expander("🔍 DEBUG - Análise detalhada de Maio/2025", expanded=True):
    st.markdown("### Análise do mês de MAIO/2025")
    
    # Filtra dados de maio do ano selecionado
    mask_maio = (df_raw["ano"] == ano_sel) & (df_raw["mes"] == 5)
    
    # Aplica filtros de UF e transportadora se existirem
    if ufs_sel:
        mask_maio &= df_raw["UF"].isin(ufs_sel)
    if transp_sel:
        mask_maio &= df_raw["Proveedor"].isin(transp_sel)
    
    df_maio = df_raw[mask_maio]
    
    # Separa entregues
    entregues_maio = df_maio[df_maio["estado"] == STATUS_COMPLETED]
    
    total_entregues = len(entregues_maio)
    on_time = (entregues_maio["On Time"] == "On Time").sum()
    no_ontime = (entregues_maio["On Time"] == "No ontime").sum()
    sem_classificacao = entregues_maio["On Time"].isna().sum()
    
    st.write(f"**Total de pedidos em Maio/{ano_sel}:** {len(df_maio)}")
    st.write(f"**Total de entregues (wc-completed):** {total_entregues}")
    st.write(f"**- No Prazo (On Time = 'On Time'):** {on_time}")
    st.write(f"**- Atrasado (On Time = 'No ontime'):** {no_ontime}")
    st.write(f"**- SEM CLASSIFICAÇÃO (On Time vazio):** {sem_classificacao}")
    
    st.markdown("---")
    
    # Cálculo do SLA pelas duas regras
    sla_antigo = round(on_time / (on_time + no_ontime) * 100, 2) if (on_time + no_ontime) > 0 else 0
    sla_novo = round(on_time / total_entregues * 100, 2) if total_entregues > 0 else 0
    
    st.write(f"**SLA com regra ANTIGA (ignorar sem classificação):** {sla_antigo}%")
    st.write(f"**SLA com regra NOVA (sem classificação = atrasado):** {sla_novo}%")
    
    if sem_classificacao > 0:
        st.warning(f"⚠️ {sem_classificacao} pedidos entregues sem classificação em 'On Time'!")
        
        # Mostra amostra dos pedidos sem classificação
        st.markdown("**Amostra dos pedidos sem classificação:**")
        sem_classif_df = entregues_maio[entregues_maio["On Time"].isna()][["numero_pedido", "Proveedor", "UF", "fecha"]].head(10)
        st.dataframe(sem_classif_df)
    
    st.markdown("---")
    st.markdown("### Verificação de valores únicos em 'On Time'")
    st.write(entregues_maio["On Time"].value_counts(dropna=False))
