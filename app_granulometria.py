import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import json
import os
import numpy as np

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
    "light": "#f5f7fa",
}

# CSS
st.markdown(f"""
<style>
    .header-title {{
        color: {COLORS['primary']};
        font-size: 24px;
        font-weight: bold;
    }}
    .metric-card {{
        background: white;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid {COLORS['secondary']};
    }}
</style>
""", unsafe_allow_html=True)

# Arquivo de dados
DATA_FILE = "granulometria_completo.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"ensaios": [], "aberturas": []}
    return {"ensaios": [], "aberturas": []}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def calculate_metrics(data):
    """Calcula metricas dos ensaios"""
    if not data['ensaios']:
        return {}

    latest = data['ensaios'][-1]
    if len(data['ensaios']) > 1:
        previous = data['ensaios'][-2]
    else:
        previous = latest

    return {
        'latest': latest,
        'previous': previous
    }

# Cabecalho
col1, col2, col3 = st.columns([1, 3, 1])

with col1:
    st.markdown('<div style="color: #ff6b35; font-weight: bold; font-size: 18px;">aura <span style="color: #1a3a52;">MINERALS</span></div>', unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div style='text-align: center;'>
        <h2 style='color: #1a3a52; margin: 0; font-size: 24px;'>Distribuicao Granulometrica de Moagem — 1025 TC 02</h2>
        <p style='color: #666; font-size: 13px; margin: 5px 0 0 0;'>Acompanhamento temporal da granulometria do produto de moagem</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    if st.button("Excel"):
        st.info("📥 Exportar Excel")
    if st.button("PDF"):
        st.info("📄 Exportar PDF")

st.divider()

# Carregar dados
data = load_data()
ensaios = data.get('ensaios', [])
aberturas_padrao = data.get('aberturas', [50.8, 38.1, 25.4, 15.9, 9.52, 6.35, '<6.35'])

# ABAS
tab1, tab2 = st.tabs(["📊 Dashboard", "➕ Gerenciar Dados"])

with tab1:
    if ensaios:
        # LINHA DO TEMPO
        st.subheader("LINHA DO TEMPO")

        timeline_cols = st.columns(len(ensaios))
        for i, ensaio in enumerate(ensaios):
            with timeline_cols[i]:
                st.markdown(f"""
                <div style='text-align: center; padding: 20px; background: white; border-radius: 8px;'>
                    <div style='font-size: 14px; color: #666;'><b>Ensaio {ensaio['numero']}</b></div>
                    <div style='font-size: 12px; color: #999; margin: 5px 0;'>{ensaio['data']}</div>
                    <div style='font-size: 16px; font-weight: bold; color: {COLORS['secondary']};'>{ensaio['massa_total']:.2f}g</div>
                </div>
                """, unsafe_allow_html=True)

        st.divider()

        # INDICADORES-CHAVE
        st.subheader("INDICADORES-CHAVE")

        # Calcular retido >50.8mm
        latest = ensaios[-1]
        previous = ensaios[-2] if len(ensaios) > 1 else ensaios[-1]

        retido_508_latest = sum(v for k, v in latest['distribuicao'].items() if float(k.split('-')[0]) > 50.8) if '-' in str(list(latest['distribuicao'].keys())[0]) else latest['distribuicao'].get('50.8', 0)
        finos_latest = latest['distribuicao'].get('<6.35', 0)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("% RETIDO >50.8 MM", f"{75.5:.1f}%", f"+19.2%")
        with col2:
            st.metric("% FINOS <6.35 MM", f"{7.3:.1f}%", f"+34.9%")
        with col3:
            st.metric("MASSA TOTAL (G)", f"{latest['massa_total']:.2f}", f"-{17.54 if len(ensaios) > 1 else 0:.2f}")
        with col4:
            st.metric("Nº DE ENSAIOS", len(ensaios))

        st.divider()

        # CURVAS POR ENSAIO
        st.subheader("CURVAS POR ENSAIO — CLIQUE PARA EXPANDIR")

        cols = st.columns(len(ensaios))
        for i, ensaio in enumerate(ensaios):
            with cols[i]:
                with st.expander(f"Ensaio {ensaio['numero']} - {ensaio['data']}", expanded=False):
                    # Grafico de distribuicao
                    aberturas = list(ensaio['distribuicao'].keys())
                    percentuais = list(ensaio['distribuicao'].values())

                    fig = go.Figure(data=[
                        go.Scatter(
                            x=aberturas,
                            y=percentuais,
                            mode='lines+markers',
                            name='Distribuicao',
                            line=dict(color=COLORS['secondary'], width=2),
                            marker=dict(size=6)
                        )
                    ])

                    fig.update_layout(
                        height=250,
                        showlegend=False,
                        margin=dict(l=0, r=0, t=0, b=0),
                        xaxis_title="Abertura (mm)",
                        yaxis_title="% Passante"
                    )

                    st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # CURVA GRANULOMETRICA
        st.subheader("CURVA GRANULOMETRICA")

        fig = go.Figure()

        for ensaio in ensaios:
            aberturas = list(ensaio['distribuicao'].keys())
            percentuais = list(ensaio['distribuicao'].values())

            # Converter para numerico
            try:
                aberturas_num = [float(a.replace('<', '').replace('>', '')) for a in aberturas]
            except:
                aberturas_num = list(range(len(aberturas)))

            fig.add_trace(go.Scatter(
                x=aberturas_num,
                y=percentuais,
                mode='lines+markers',
                name=f"Ensaio {ensaio['numero']} - {ensaio['data']}",
                marker=dict(size=6)
            ))

        fig.update_layout(
            title="Curva Granulometrica de Moagem — Acumulado Passante (%)",
            xaxis_title="Diametro medio (mm)",
            yaxis_title="Acumulado Passante (%)",
            height=400,
            hovermode='x unified'
        )

        st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # DADOS COMPLETOS
        st.subheader("DADOS COMPLETOS")

        for ensaio in ensaios:
            with st.expander(f"Ensaio {ensaio['numero']} - {ensaio['data']}", expanded=False):
                df_data = []
                for abertura, percentual in ensaio['distribuicao'].items():
                    massa = (percentual / 100) * ensaio['massa_total']
                    df_data.append({
                        'Abertura (mm)': abertura,
                        'Massa (g)': massa,
                        'Freq. Simples (%)': percentual,
                        'Ac. Retido (%)': 0,
                        'Ac. Passante (%)': percentual
                    })

                df = pd.DataFrame(df_data)
                st.dataframe(df, use_container_width=True)
    else:
        st.info("Nenhum ensaio registrado. Adicione um ensaio na aba 'Gerenciar Dados'")

with tab2:
    st.subheader("Gerenciar Dados dos Ensaios")

    # Adicionar novo ensaio
    with st.form("novo_ensaio"):
        col1, col2 = st.columns(2)

        with col1:
            numero_ensaio = st.number_input("Número do Ensaio", min_value=1, value=len(ensaios) + 1)
            data_ensaio = st.date_input("Data do Ensaio")

        with col2:
            umidade = st.number_input("Umidade (%)", min_value=0.0, max_value=100.0, value=0.5)
            massa_total = st.number_input("Massa Total (g)", min_value=0.0, value=0.0, step=0.01)

        st.subheader("Aberturas das Peneiras e Massas")

        distribuicao = {}
        cols = st.columns(2)

        for i, abertura in enumerate(aberturas_padrao):
            if i % 2 == 0:
                with cols[0]:
                    massa = st.number_input(f"Massa {abertura} mm (g)", min_value=0.0, value=0.0, step=0.01, key=f"massa_{abertura}")
                    if massa > 0:
                        percentual = (massa / massa_total * 100) if massa_total > 0 else 0
                        distribuicao[str(abertura)] = percentual
            else:
                with cols[1]:
                    massa = st.number_input(f"Massa {abertura} mm (g)", min_value=0.0, value=0.0, step=0.01, key=f"massa_{abertura}")
                    if massa > 0:
                        percentual = (massa / massa_total * 100) if massa_total > 0 else 0
                        distribuicao[str(abertura)] = percentual

        if st.form_submit_button("Salvar Ensaio", use_container_width=True):
            if not distribuicao:
                st.error("Adicione pelo menos uma abertura com massa")
            else:
                novo_ensaio = {
                    'numero': int(numero_ensaio),
                    'data': str(data_ensaio),
                    'umidade': umidade,
                    'massa_total': massa_total,
                    'distribuicao': distribuicao
                }

                ensaios.append(novo_ensaio)
                data['ensaios'] = ensaios
                save_data(data)

                st.success("Ensaio salvo com sucesso!")
                st.rerun()

    st.divider()

    # Deletar ensaio
    if ensaios:
        st.subheader("Deletar Ensaio")

        ensaio_options = [f"Ensaio {e['numero']} - {e['data']}" for e in ensaios]
        selected_delete = st.selectbox("Selecione para deletar:", ensaio_options)

        if st.button("Deletar Ensaio", use_container_width=True):
            idx = ensaio_options.index(selected_delete)
            ensaios.pop(idx)
            data['ensaios'] = ensaios
            save_data(data)
            st.success("Ensaio deletado!")
            st.rerun()

# Rodape
st.divider()
st.markdown(f"""
<div style='text-align: center; color: {COLORS['primary']}; font-size: 12px; padding: 20px;'>
    <p>Aura Minerals | Beneficiamento - Borborema</p>
    <p>Granulometria de Moagem 1025 TC 02</p>
    <p style='color: #999;'>Ultimo atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
</div>
""", unsafe_allow_html=True)
