import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import json
import os

# Configuracao da pagina
st.set_page_config(
    page_title="Granulometria de Moagem — 1025 TC 02 | Aura Minerals",
    page_icon="⛏️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Cores da Aura Minerals
COLORS = {
    "primary": "#1a3a52",
    "secondary": "#ff6b35",
    "accent": "#ff8a50",
    "light": "#f5f7fa",
    "dark": "#0f2438",
}

# CSS customizado para manter design original
st.markdown(f"""
<style>
    * {{
        margin: 0;
        padding: 0;
    }}

    [data-testid="stHeader"] {{
        background-color: {COLORS['primary']};
    }}

    .main {{
        background-color: {COLORS['light']};
    }}

    .metric-card {{
        background: white;
        padding: 20px;
        border-radius: 8px;
        border-left: 4px solid {COLORS['secondary']};
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }}

    h1 {{
        color: {COLORS['primary']};
        border-bottom: 3px solid {COLORS['secondary']};
        padding-bottom: 10px;
    }}

    h2 {{
        color: {COLORS['primary']};
    }}
</style>
""", unsafe_allow_html=True)

# Arquivo de dados
DATA_FILE = "granulometria_data.json"

def load_data():
    """Carrega dados"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"measurements": []}
    return {"measurements": []}

def save_data(data):
    """Salva dados"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Cabecalho
col1, col2, col3 = st.columns([1, 3, 1])

with col1:
    st.markdown("""
    <div style='color: #ff6b35; font-weight: bold; font-size: 18px;'>
    aura <span style='color: #1a3a52;'>MINERALS</span>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div style='text-align: center;'>
        <h1 style='color: #1a3a52; margin: 0; font-size: 26px; border: none;'>Granulometria de Moagem — 1025 TC 02</h1>
        <p style='color: #666; font-size: 13px; margin: 5px 0 0 0;'>Acompanhamento temporal da granulometria do produto de moagem</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    if st.button("Excel"):
        st.info("📥 Exportar Excel - Em desenvolvimento")
    if st.button("PDF"):
        st.info("📄 Exportar PDF - Em desenvolvimento")

st.divider()

# Carregar dados
data = load_data()
measurements = data.get("measurements", [])

# Abas principais
tab1, tab2, tab3, tab4 = st.tabs(["📊 Distribuicao", "➕ Adicionar Medicao", "📋 Dados", "📈 Analise"])

with tab1:
    st.subheader("Distribuicao Granulometrica")

    if measurements:
        df = pd.DataFrame(measurements)

        # Selecionar medicao para visualizar
        med_options = [f"{m['date']} - {m['descricao']}" for m in measurements]
        selected = st.selectbox("Selecione uma medicao:", med_options)

        selected_idx = med_options.index(selected)
        current_measurement = measurements[selected_idx]

        # Exibir informacoes
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Data", current_measurement['date'])
        with col2:
            st.metric("Descricao", current_measurement['descricao'])
        with col3:
            st.metric("Moagem", current_measurement.get('moagem_id', '-'))

        st.divider()

        # Grafico de distribuicao
        if 'granulometria' in current_measurement:
            granulo = current_measurement['granulometria']

            # Preparar dados para grafico
            tamanhos = list(granulo.keys())
            percentuais = list(granulo.values())

            fig = go.Figure(data=[
                go.Bar(
                    x=tamanhos,
                    y=percentuais,
                    marker_color=COLORS['secondary'],
                    text=[f"{p}%" for p in percentuais],
                    textposition='outside',
                    hovertemplate='<b>%{x}</b><br>%{y}%<extra></extra>'
                )
            ])

            fig.update_layout(
                title="Distribuicao Granulometrica (%)",
                xaxis_title="Tamanho da Particula",
                yaxis_title="Percentual (%)",
                height=400,
                plot_bgcolor='rgba(240,244,242,0.5)',
                showlegend=False
            )

            st.plotly_chart(fig, use_container_width=True)

            # Tabela com valores
            st.subheader("Valores Detalhados")
            df_granulo = pd.DataFrame({
                'Tamanho': tamanhos,
                'Percentual (%)': percentuais
            })
            st.dataframe(df_granulo, use_container_width=True)
    else:
        st.info("Nenhuma medicao registrada. Adicione uma medicao na aba 'Adicionar Medicao'")

with tab2:
    st.subheader("Registrar Nova Medicao")

    col1, col2 = st.columns(2)

    with col1:
        data_medicao = st.date_input("Data da Medicao")
        moagem_id = st.text_input("ID Moagem", placeholder="Ex: 1025 TC 02")

    with col2:
        descricao = st.text_input("Descricao", placeholder="Ex: Medicao Horaria")
        unidade = st.selectbox("Unidade", ["mm", "micrometros", "mesh"])

    st.subheader("Tamanhos e Percentuais")

    # Inputs dinamicos
    col1, col2 = st.columns(2)

    granulo_data = {}

    # Tamanhos padrao
    tamanhos_padrao = [">1000", "500-1000", "250-500", "125-250", "63-125", "<63"]

    for i, tamanho in enumerate(tamanhos_padrao):
        with col1 if i % 2 == 0 else col2:
            percentual = st.number_input(f"{tamanho} {unidade}", min_value=0.0, max_value=100.0, value=0.0, step=0.1, key=f"granulo_{i}")
            granulo_data[tamanho] = percentual

    if st.button("Salvar Medicao", use_container_width=True):
        if not moagem_id:
            st.error("Preencha o ID Moagem")
        else:
            new_measurement = {
                'date': str(data_medicao),
                'moagem_id': moagem_id,
                'descricao': descricao,
                'granulometria': granulo_data
            }

            measurements.append(new_measurement)
            data['measurements'] = measurements
            save_data(data)

            st.success("Medicao registrada com sucesso!")
            st.rerun()

with tab3:
    st.subheader("Historico de Medicoes")

    if measurements:
        df = pd.DataFrame(measurements)

        # Expandir coluna granulometria para visualizacao
        display_df = df[['date', 'moagem_id', 'descricao']].copy()
        display_df.columns = ['Data', 'Moagem ID', 'Descricao']

        st.dataframe(display_df, use_container_width=True)

        # Deletar medicao
        st.divider()
        st.subheader("Deletar Medicao")

        options = [f"{m['date']} - {m['descricao']}" for m in measurements]
        selected_delete = st.selectbox("Selecione para deletar:", options, key="delete_select")

        if st.button("Deletar", use_container_width=True):
            idx = options.index(selected_delete)
            measurements.pop(idx)
            data['measurements'] = measurements
            save_data(data)
            st.success("Medicao deletada!")
            st.rerun()
    else:
        st.info("Nenhuma medicao registrada")

with tab4:
    st.subheader("Analise Temporal")

    if measurements and len(measurements) > 1:
        # Grafico de evolucao
        datas = [m['date'] for m in measurements]

        # Tentar plotar um tamanho especifico
        st.info("Selecione um tamanho de particula para ver a evolucao")

        if measurements[0].get('granulometria'):
            tamanhos = list(measurements[0]['granulometria'].keys())
            selected_size = st.selectbox("Tamanho:", tamanhos)

            valores = [m['granulometria'].get(selected_size, 0) for m in measurements]

            fig = go.Figure(data=[
                go.Scatter(
                    x=datas,
                    y=valores,
                    mode='lines+markers',
                    name=selected_size,
                    line=dict(color=COLORS['secondary'], width=3),
                    marker=dict(size=10)
                )
            ])

            fig.update_layout(
                title=f"Evolucao: {selected_size}",
                xaxis_title="Data",
                yaxis_title="Percentual (%)",
                height=400,
                hovermode='x unified'
            )

            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Adicione mais medicoes para ver a analise temporal")

# Rodape
st.divider()
st.markdown(f"""
<div style='text-align: center; color: {COLORS['primary']}; font-size: 12px; padding: 20px;'>
    <p>Aura Minerals | Beneficiamento - Borborema</p>
    <p>Granulometria de Moagem 1025 TC 02</p>
    <p style='color: #999;'>Ultimo atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
</div>
""", unsafe_allow_html=True)
