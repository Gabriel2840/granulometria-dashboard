import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date
import json
import os

try:
    from fpdf import FPDF
    PDF_OK = True
except ImportError:
    PDF_OK = False

st.set_page_config(
    page_title="Granulometria de Moagem | Aura Minerals",
    page_icon="⛏️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

PRIMARY = "#1a3a52"
SECONDARY = "#ff6b35"
TL_COLORS = ["#e74c3c", "#1abc9c", "#9b59b6", "#e67e22", "#3498db", "#2ecc71", "#f39c12", "#e91e63"]
SIEVE_COLORS = ["#1a3a52", "#2e6da4", "#3aa0c0", "#4caf50", "#ff9800", "#ff6b35", "#9c27b0"]
ABERTURAS = ["50.8", "38.1", "25.4", "15.9", "9.52", "6.35", "<6.35"]
DATA_FILE = "granulometria_dados.json"

st.markdown("""
<style>
    .main { background-color: #eef1f6; }
    [data-testid="stHeader"] { background-color: #1a3a52; }

    .agilidade-text {
        cursor: pointer;
        transition: all 0.3s ease;
        display: inline-block;
    }

    .agilidade-text:hover {
        color: #1a3a52 !important;
        font-size: 14px;
        text-shadow: 0 0 10px #ff6b35;
        transform: scale(1.05);
    }
</style>
""", unsafe_allow_html=True)


# ── Dados ────────────────────────────────────────────────────────────────────

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"ensaios": []}


def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar dados: {e}")
        return False


def get_sorted(ensaios):
    def parse(e):
        try:
            return datetime.strptime(e.get("data", "01/01/2000"), "%d/%m/%Y")
        except Exception:
            return datetime.min
    return sorted(ensaios, key=parse)


# ── Cálculos ─────────────────────────────────────────────────────────────────

def calcular_granulometria(massas_dict):
    ordered = [k for k in ABERTURAS if k in massas_dict]
    total = sum(to_float(massas_dict.get(k, 0)) for k in ordered)
    if total == 0:
        return None, 0.0
    rows = []
    ac_retido = 0.0
    for ab in ordered:
        massa = to_float(massas_dict.get(ab, 0))
        freq = (massa / total) * 100.0
        ac_retido = min(ac_retido + freq, 100.0)
        ac_pass = max(100.0 - ac_retido, 0.0)
        rows.append({
            "Malha (mm)": ab,
            "Massa (g)": round(massa, 2),
            "Freq. Simples (%)": round(freq, 2),
            "Ac. Retido (%)": round(ac_retido, 2),
            "Ac. Passante (%)": round(ac_pass, 2),
        })
    rows.append({
        "Malha (mm)": "TOTAL",
        "Massa (g)": round(total, 2),
        "Freq. Simples (%)": 100.0,
        "Ac. Retido (%)": None,
        "Ac. Passante (%)": None,
    })
    return pd.DataFrame(rows), total


def format_pct(x):
    if x is None:
        return "—"
    try:
        v = float(x)
        return "—" if v != v else f"{v:.2f}%"
    except Exception:
        return "—"


def highlight_table(df):
    s = pd.DataFrame("", index=df.index, columns=df.columns)
    tm = df["Malha (mm)"] == "TOTAL"
    om = ~tm
    for col in df.columns:
        s.loc[tm, col] = f"background-color:{PRIMARY};color:white;font-weight:bold"
    s.loc[om, "Ac. Retido (%)"] = f"color:{SECONDARY};font-weight:bold"
    s.loc[om, "Ac. Passante (%)"] = "color:#2e6da4;font-weight:bold"
    return s


def get_freq(df, malha):
    if df is None:
        return 0.0
    row = df[df["Malha (mm)"] == malha]
    return float(row["Freq. Simples (%)"].values[0]) if len(row) else 0.0


def to_float(val):
    """Converte valor com virgula ou ponto para float"""
    if val is None or val == "" or str(val).lower() == "none":
        return 0.0
    try:
        s = str(val).strip().replace(",", ".")
        if not s or s.lower() == "none":
            return 0.0
        return float(s)
    except (ValueError, TypeError):
        return 0.0


# ── PDF ───────────────────────────────────────────────────────────────────────

def _hr(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _table_header(pdf, cw, hdrs, pr):
    pdf.set_fill_color(*pr)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    for i, h in enumerate(hdrs):
        # Remover caracteres especiais
        h_clean = h.replace("á", "a").replace("é", "e").replace("ó", "o").replace("í", "i").replace("ú", "u")
        pdf.cell(cw[i], 8, h_clean, fill=True, border=1, align="C")
    pdf.ln()


def _table_row(pdf, cw, row, pr, row_idx):
    is_tot = row["Malha (mm)"] == "TOTAL"
    if is_tot:
        pdf.set_fill_color(*pr)
        pdf.set_text_color(255, 255, 255)
    else:
        bg = 248 if row_idx % 2 == 0 else 255
        pdf.set_fill_color(bg, bg, bg)
        pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", size=9)
    ret = format_pct(row["Ac. Retido (%)"]) if not is_tot else "-"
    pas = format_pct(row["Ac. Passante (%)"]) if not is_tot else "-"

    malha = str(row["Malha (mm)"])
    massa = f"{row['Massa (g)']:.2f}"
    freq = f"{row['Freq. Simples (%)']:.2f}%"

    pdf.cell(cw[0], 7, malha, border=1, fill=True, align="C")
    pdf.cell(cw[1], 7, massa, border=1, fill=True, align="C")
    pdf.cell(cw[2], 7, freq, border=1, fill=True, align="C")
    pdf.cell(cw[3], 7, ret, border=1, fill=True, align="C")
    pdf.cell(cw[4], 7, pas, border=1, fill=True, align="C")
    pdf.ln()


def gerar_pdf_dados(ensaios):
    if not PDF_OK:
        return None
    pr = _hr(PRIMARY)
    cw = [32, 32, 44, 44, 44]
    hdrs = ["Malha (mm)", "Massa (g)", "Freq. Simples (%)", "Ac. Retido (%)", "Ac. Passante (%)"]
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    for ensaio in get_sorted(ensaios):
        pdf.add_page()
        pdf.set_fill_color(*pr)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 13, "Aura Minerals | Granulometria de Moagem | 1025 TC 02",
                 fill=True, ln=True, align="C")
        pdf.ln(4)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "B", 10)
        amostra = ensaio.get('amostra', '').replace("á", "a")
        data = ensaio.get('data', '')
        pdf.cell(0, 8,
                 f"Amostra: {amostra}  Data: {data}  Umidade: {ensaio.get('umidade', 0):.2f}%",
                 ln=True)
        pdf.ln(3)
        df, total = calcular_granulometria(ensaio["massas"])
        if df is not None:
            pdf.set_font("Helvetica", size=9)
            pdf.cell(0, 7, f"Massa Total: {total:.2f} g", ln=True)
            pdf.ln(2)
            _table_header(pdf, cw, hdrs, pr)
            for j, (_, row) in enumerate(df.iterrows()):
                _table_row(pdf, cw, row, pr, j)
        pdf.set_y(-15)
        pdf.set_font("Helvetica", size=8)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 8,
                 f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')} | Aura Minerals",
                 align="C")
    return bytes(pdf.output())


def gerar_pdf_dashboard(ensaios):
    if not PDF_OK:
        return None
    pr = _hr(PRIMARY)
    sr = _hr(SECONDARY)
    sorted_ens = get_sorted(ensaios)
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=12)

    # Pagina 1 - Cabecalho e Resumo
    pdf.add_page()
    pdf.set_fill_color(*pr)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 12, "DASHBOARD GRANULOMETRIA DE MOAGEM",
             fill=True, ln=True, align="C")
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_fill_color(100, 130, 160)
    pdf.cell(0, 8, "Aura Minerals | 1025 TC 02 | Beneficiamento Borborema",
             fill=True, ln=True, align="C")
    pdf.ln(4)

    # Data e resumo
    pdf.set_text_color(80, 80, 80)
    pdf.set_font("Helvetica", size=9)
    pdf.cell(0, 6,
             f"Relatorio gerado: {datetime.now().strftime('%d/%m/%Y %H:%M')} | "
             f"Total de ensaios: {len(sorted_ens)}",
             ln=True)
    pdf.ln(3)

    # Indicadores do ultimo ensaio
    if sorted_ens:
        ultimo = sorted_ens[-1]
        df_u, tot_u = calcular_granulometria(ultimo["massas"])

        pdf.set_text_color(*pr)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, "ULTIMO ENSAIO - INDICADORES-CHAVE", ln=True)
        pdf.set_draw_color(*sr)
        pdf.set_line_width(0.7)
        pdf.line(12, pdf.get_y(), 198, pdf.get_y())
        pdf.ln(3)

        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", size=9)

        # Dados do ensaio em duas colunas
        x_col1 = 15
        x_col2 = 110
        y_pos = pdf.get_y()

        amostra = ultimo.get('amostra', 'N/A').replace("á", "a")
        pdf.text(x_col1, y_pos, f"Amostra: {amostra}")
        pdf.text(x_col2, y_pos, f"Data: {ultimo.get('data', 'N/A')}")
        pdf.ln(5)

        pdf.text(x_col1, pdf.get_y(), f"Umidade: {ultimo.get('umidade', 0):.2f}%")
        pdf.text(x_col2, pdf.get_y(), f"Massa Total: {tot_u:.2f} g")
        pdf.ln(5)

        if df_u is not None:
            ret = get_freq(df_u, "50.8")
            fin = get_freq(df_u, "<6.35")
            pdf.text(x_col1, pdf.get_y(), f"Retido >50.8 mm: {ret:.2f}%")
            pdf.text(x_col2, pdf.get_y(), f"Finos <6.35 mm: {fin:.2f}%")
            pdf.ln(5)

        pdf.ln(2)

    # Linha do tempo
    pdf.set_text_color(*pr)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "LINHA DO TEMPO DOS ENSAIOS", ln=True)
    pdf.set_draw_color(*sr)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)
    cw_tl = [55, 32, 32, 35, 28]
    hdrs_tl = ["Amostra", "Data", "Umidade (%)", "Massa Total (g)", "N"]
    _table_header(pdf, cw_tl, hdrs_tl, pr)
    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(0, 0, 0)
    for i, e in enumerate(sorted_ens):
        _, tm = calcular_granulometria(e["massas"])
        bg = 248 if i % 2 == 0 else 255
        pdf.set_fill_color(bg, bg, bg)
        amostra_tl = e.get("amostra", "").replace("á", "a")
        pdf.cell(cw_tl[0], 7, amostra_tl, fill=True, border=1)
        pdf.cell(cw_tl[1], 7, e.get("data", ""), fill=True, border=1, align="C")
        pdf.cell(cw_tl[2], 7, f"{e.get('umidade', 0):.2f}%", fill=True, border=1, align="C")
        pdf.cell(cw_tl[3], 7, f"{tm:.2f}", fill=True, border=1, align="C")
        pdf.cell(cw_tl[4], 7, str(i + 1), fill=True, border=1, align="C")
        pdf.ln()

    # Rodape
    pdf.set_y(-20)
    pdf.set_font("Helvetica", size=8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 8,
             f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}  |  Aura Minerals - Beneficiamento",
             align="C")

    return bytes(pdf.output())


# ── Cabeçalho ────────────────────────────────────────────────────────────────

col_logo, col_titulo, col_hora = st.columns([1, 4, 1])
with col_logo:
    st.markdown(
        '<div style="color:#ff6b35;font-weight:bold;font-size:20px;padding-top:30px;">'
        'aura <span style="color:#1a3a52;">MINERALS</span></div>',
        unsafe_allow_html=True,
    )
with col_titulo:
    st.markdown("""
    <div style='text-align:center;'>
        <h2 style='color:#1a3a52;margin:0;font-size:22px;'>Distribuicao Granulometrica de Moagem — 1025 TC 02</h2>
        <p style='color:#666;font-size:12px;margin:4px 0 0 0;'>Acompanhamento temporal | Borborema</p>
        <p style='margin:6px 0 0 0;'><span class='agilidade-text' style='color:#ff6b35;font-size:13px;font-weight:600;'>✓ Agilidade e Simplicidade</span></p>
    </div>
    """, unsafe_allow_html=True)
with col_hora:
    st.markdown(
        f'<div style="text-align:right;color:#999;font-size:11px;padding-top:10px;">'
        f'{datetime.now().strftime("%d/%m/%Y %H:%M")}</div>',
        unsafe_allow_html=True,
    )

st.divider()

data = load_data()
ensaios = data.get("ensaios", [])

tab_dash, tab_reg = st.tabs(["Dashboard", "Registrar Ensaio"])

# ═══════════════════════════════════════════════════════════════════════
#   DASHBOARD
# ═══════════════════════════════════════════════════════════════════════
with tab_dash:
    if not ensaios:
        st.info("Nenhum ensaio registrado. Use a aba 'Registrar Ensaio'.")
    else:
        sorted_ens = get_sorted(ensaios)

        # ── Botões PDF / CSV ────────────────────────────────────────────
        st.markdown("<b style='font-size:12px;color:#1a3a52;'>Exportar Dados:</b>", unsafe_allow_html=True)
        btn1, btn2, btn3 = st.columns(3)

        with btn1:
            csv_rows = []
            for e in sorted_ens:
                df_e, _ = calcular_granulometria(e["massas"])
                if df_e is not None:
                    for _, row in df_e.iterrows():
                        csv_rows.append({
                            "Amostra": e.get("amostra", ""),
                            "Data": e.get("data", ""),
                            "Umidade (%)": e.get("umidade", 0),
                            **row.to_dict(),
                        })
            if csv_rows:
                csv_bytes = pd.DataFrame(csv_rows).to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
                st.download_button(
                    "📊 Exportar CSV",
                    data=csv_bytes,
                    file_name=f"granulometria_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

        with btn2:
            if PDF_OK:
                pdf_dados = gerar_pdf_dados(sorted_ens)
                if pdf_dados:
                    st.download_button(
                        "📄 PDF Dados",
                        data=pdf_dados,
                        file_name=f"granulometria_dados_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )
                else:
                    st.warning("Erro ao gerar PDF")
            else:
                st.info("fpdf2 não instalado")

        with btn3:
            if PDF_OK:
                pdf_dash = gerar_pdf_dashboard(sorted_ens)
                if pdf_dash:
                    st.download_button(
                        "📋 PDF Dashboard",
                        data=pdf_dash,
                        file_name=f"granulometria_dashboard_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )
                else:
                    st.warning("Erro ao gerar PDF")
            else:
                st.info("fpdf2 não instalado")

        st.divider()

        # ── Linha do Tempo ──────────────────────────────────────────────
        st.markdown(
            f"<div style='font-size:11px;font-weight:500;color:{PRIMARY};"
            "letter-spacing:.6px;margin-bottom:8px;'>LINHA DO TEMPO</div>",
            unsafe_allow_html=True,
        )

        tl_items = ""
        for i, e in enumerate(sorted_ens):
            color = TL_COLORS[i % len(TL_COLORS)]
            massas_e = e.get("massas", {})
            total_tl = sum(float(v) for v in massas_e.values())
            tl_items += (
                f"<div style='display:flex;flex-direction:column;align-items:center;"
                f"gap:4px;z-index:1;min-width:110px;'>"
                f"<div style='width:36px;height:36px;border-radius:50%;border:3px solid {color};"
                f"background:white;display:flex;align-items:center;justify-content:center;'>"
                f"<div style='width:12px;height:12px;border-radius:50%;background:{color};'></div></div>"
                f"<div style='font-size:12px;font-weight:500;color:#1a3a52;text-align:center;'>"
                f"{e.get('amostra','')}</div>"
                f"<div style='font-size:10px;color:#888;'>{e.get('data','')}</div>"
                f"<div style='background:{color};color:white;border-radius:12px;"
                f"padding:2px 8px;font-size:10px;font-weight:500;'>{total_tl:.2f} g</div>"
                f"</div>"
            )

        st.markdown(
            f"<div style='background:white;border-radius:10px;border:0.5px solid #e0e5ec;"
            f"padding:16px 20px 12px;overflow-x:auto;'>"
            f"<div style='display:flex;justify-content:space-around;min-width:400px;"
            f"position:relative;'>"
            f"<div style='position:absolute;top:18px;left:8%;right:8%;height:2px;"
            f"background:#e0e5ec;'></div>"
            f"{tl_items}</div></div>",
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Indicadores-Chave ───────────────────────────────────────────
        st.markdown(
            f"<div style='font-size:11px;font-weight:500;color:{PRIMARY};"
            "letter-spacing:.6px;margin-bottom:8px;'>INDICADORES-CHAVE</div>",
            unsafe_allow_html=True,
        )

        ultimo = sorted_ens[-1]
        anterior = sorted_ens[-2] if len(sorted_ens) >= 2 else None
        df_u, tot_u = calcular_granulometria(ultimo["massas"])
        df_a, tot_a = calcular_granulometria(anterior["massas"]) if anterior else (None, 0.0)

        ret_u = get_freq(df_u, "50.8")
        ret_a = get_freq(df_a, "50.8")
        fin_u = get_freq(df_u, "<6.35")
        fin_a = get_freq(df_a, "<6.35")
        data_u = ultimo.get("data", "")
        data_a = anterior.get("data", "") if anterior else ""

        def ind_card(label, v_atual, color):
            return (
                f"<div style='background:white;border-radius:8px;"
                f"border:0.5px solid #e0e5ec;border-left:4px solid {color};"
                f"padding:12px;height:70px;display:flex;flex-direction:column;justify-content:center;'>"
                f"<div style='font-size:10px;font-weight:500;color:#888;"
                f"letter-spacing:.5px;margin-bottom:4px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;'>{label}</div>"
                f"<div style='font-size:28px;font-weight:600;color:{color};'>{v_atual}</div>"
                f"</div>"
            )

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(ind_card(
                "% Retido >50,8 mm",
                f"{ret_u:.1f}%",
                SECONDARY,
            ), unsafe_allow_html=True)
        with c2:
            st.markdown(ind_card(
                "% Finos <6,35 mm",
                f"{fin_u:.1f}%",
                "#1abc9c",
            ), unsafe_allow_html=True)
        with c3:
            st.markdown(ind_card(
                "Massa Total (g)",
                f"{tot_u:.2f}g",
                "#2e6da4",
            ), unsafe_allow_html=True)
        with c4:
            st.markdown(ind_card(
                "N° Ensaios",
                str(len(sorted_ens)),
                PRIMARY,
            ), unsafe_allow_html=True)

        st.divider()

        # ── Gráficos: Rosca + Umidade ───────────────────────────────────
        col_rosca, col_umid = st.columns(2)

        with col_rosca:
            st.markdown(
                f"<b style='color:{PRIMARY};font-size:13px;'>Distribuicao por Fracao — "
                f"Ultimo Ensaio ({data_u})</b>",
                unsafe_allow_html=True,
            )
            if df_u is not None:
                df_plot = df_u[df_u["Malha (mm)"] != "TOTAL"].copy()
                fig_r = go.Figure(go.Pie(
                    labels=[f"{m} mm" for m in df_plot["Malha (mm)"]],
                    values=df_plot["Freq. Simples (%)"].tolist(),
                    hole=0.5,
                    marker_colors=SIEVE_COLORS[: len(df_plot)],
                    textinfo="label+percent",
                    textfont_size=10,
                    hovertemplate="%{label}: %{value:.2f}%<extra></extra>",
                ))
                fig_r.update_layout(
                    showlegend=True, height=340,
                    margin=dict(l=0, r=10, t=10, b=0),
                )
                st.plotly_chart(fig_r, use_container_width=True)

        with col_umid:
            st.markdown(
                f"<b style='color:{PRIMARY};font-size:13px;'>Umidade do Material (%)</b>",
                unsafe_allow_html=True,
            )
            x_u = [f"{e.get('amostra','')} {e.get('data','')}" for e in sorted_ens]
            y_u = [float(e.get("umidade", 0)) for e in sorted_ens]
            colors_u = [TL_COLORS[i % len(TL_COLORS)] for i in range(len(sorted_ens))]
            fig_u = go.Figure(go.Bar(
                x=x_u, y=y_u,
                marker_color=colors_u,
                text=[f"{v:.1f}%" for v in y_u],
                textposition="outside",
                hovertemplate="%{x}<br>Umidade: %{y:.2f}%<extra></extra>",
            ))
            fig_u.update_layout(
                yaxis=dict(title="Umidade (%)", ticksuffix="%"),
                height=340,
                plot_bgcolor="rgba(240,244,248,0.5)",
                margin=dict(l=0, r=0, t=10, b=80),
                xaxis=dict(tickangle=-30),
                showlegend=False,
            )
            st.plotly_chart(fig_u, use_container_width=True)

        st.divider()

        # ── Curva Granulométrica ────────────────────────────────────────
        st.markdown(
            f"<b style='color:{PRIMARY};font-size:14px;'>Curva Granulometrica — Acumulado Passante (%)</b>",
            unsafe_allow_html=True,
        )

        if not sorted_ens:
            st.info("Nenhum dado disponível para plotar a curva.")
        else:
            fig_c = go.Figure()
            plot_count = 0
            for i, e in enumerate(sorted_ens):
                df_e, _ = calcular_granulometria(e["massas"])
                if df_e is None:
                    continue
                df_e = df_e[df_e["Malha (mm)"] != "TOTAL"].copy()
                # Remove o ponto "<6.35" (finos) do gráfico
                df_e = df_e[~df_e["Malha (mm)"].astype(str).str.startswith("<")].copy()
                if len(df_e) == 0:
                    continue
                x_num = []
                for m in df_e["Malha (mm)"]:
                    try:
                        x_num.append(float(str(m).replace("<", "").replace(">", "")))
                    except Exception:
                        pass
                if not x_num:
                    continue
                pares = sorted(zip(x_num, df_e["Ac. Passante (%)"].tolist()))
                xs = [p[0] for p in pares]
                ys = [p[1] for p in pares]
                color = TL_COLORS[i % len(TL_COLORS)]
                label = f"{e.get('amostra','')} — {e.get('data','')}"
                fig_c.add_trace(go.Scatter(
                    x=xs, y=ys, mode="lines+markers", name=label,
                    line=dict(width=2, color=color),
                    marker=dict(size=7, color=color),
                    hovertemplate=f"{label}<br>Malha: %{{x:.2f}} mm<br>Ac. Passante: %{{y:.2f}}%<extra></extra>",
                ))
                plot_count += 1

            if plot_count == 0:
                st.warning("Nenhum ensaio com dados suficientes para plotar.")
            else:
                fig_c.update_layout(
                    xaxis=dict(
                        title="Diâmetro médio (mm)",
                        type="log",
                        showgrid=True,
                        gridwidth=0.5,
                        gridcolor="rgba(180,180,180,0.2)",
                        range=[0, 2.1],
                    ),
                    yaxis=dict(
                        title="Acumulado Passante (%)",
                        showgrid=True,
                        gridwidth=0.5,
                        gridcolor="rgba(180,180,180,0.2)",
                        range=[0, 100],
                    ),
                    hovermode="x unified",
                    height=380,
                    plot_bgcolor="white",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                    margin=dict(l=50, r=20, t=20, b=60),
                )
                st.plotly_chart(fig_c, use_container_width=True)

        st.divider()

        # ── Tabelas por Ensaio ──────────────────────────────────────────
        st.markdown(
            f"<b style='color:{PRIMARY};font-size:14px;'>Tabelas por Ensaio</b>",
            unsafe_allow_html=True,
        )
        for i, ensaio in enumerate(reversed(sorted_ens)):
            df_e, total_m = calcular_granulometria(ensaio["massas"])
            label = f"{ensaio.get('amostra', 'Ensaio')} — {ensaio.get('data', '')}"
            with st.expander(label, expanded=(i == 0)):
                ci1, ci2, ci3 = st.columns(3)
                ci1.metric("Massa Total (g)", f"{total_m:.2f}")
                ci2.metric("Umidade (%)", f"{ensaio.get('umidade', 0):.2f}%")
                ci3.metric("Data", ensaio.get("data", "-"))
                if df_e is not None:
                    styled = df_e.style.apply(highlight_table, axis=None).format({
                        "Massa (g)": "{:.2f}",
                        "Freq. Simples (%)": "{:.2f}%",
                        "Ac. Retido (%)": format_pct,
                        "Ac. Passante (%)": format_pct,
                    })
                    st.dataframe(styled, use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════════════════
#   REGISTRAR ENSAIO
# ═══════════════════════════════════════════════════════════════════════
with tab_reg:
    st.subheader("Registrar Novo Ensaio")
    st.caption(
        "Preencha amostra, data, umidade e a tabela de aberturas/massas. "
        "O calculo é feito automaticamente ao salvar."
    )

    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        amostra = st.text_input("Identificacao da Amostra *", placeholder="Ex: 1025 TC 02")
    with fc2:
        data_ensaio = st.date_input("Data do Ensaio *", value=date.today())
    with fc3:
        umidade = st.number_input(
            "Umidade (%)", min_value=0.0, max_value=100.0,
            value=0.0, step=0.01, format="%.2f",
        )

    st.markdown("---")
    st.markdown("**Aberturas (mm) e Massas Retidas (g)**")
    st.caption("Informe apenas as MASSAS nas linhas das peneiras que usou. As aberturas já estão preenchidas.")

    # Criar DataFrame editável com aberturas padrão pré-preenchidas
    aberturas_padrao_full = ["50.8", "38.1", "25.4", "15.9", "9.52", "6.35", "<6.35", "", "", "", "", "", "", "", ""]
    df_input = pd.DataFrame({
        "Abertura (mm)": aberturas_padrao_full,
        "Massa (g)": [0.0] * 15,
    })

    edited_df = st.data_editor(
        df_input,
        num_rows="fixed",
        use_container_width=True,
        hide_index=True,
        key="sieve_table",
        column_config={
            "Abertura (mm)": st.column_config.TextColumn(
                "Abertura (mm)",
                width="medium",
                help="Ex: 50.8, 38.1, <6.35",
            ),
            "Massa (g)": st.column_config.NumberColumn(
                "Massa (g)",
                width="medium",
                min_value=0.0,
                step=0.01,
                format="%.2f",
                help="Massa retida em gramas",
            ),
        },
    )

    # Calcular total
    total_massa = 0.0
    for v in edited_df["Massa (g)"]:
        total_massa += to_float(v)

    # Mostra total em métrica
    col_tot1, col_tot2 = st.columns([3, 1])
    with col_tot2:
        st.metric("TOTAL (g)", f"{total_massa:.2f}")

    st.markdown("---")

    if st.button("Salvar Ensaio", use_container_width=True, type="primary"):
        if not amostra.strip():
            st.error("Informe a identificacao da amostra.")
        elif total_massa == 0:
            st.error("Informe ao menos uma massa maior que zero.")
        else:
            # Extrair dados da tabela
            massas_dict = {}
            for _, row in edited_df.iterrows():
                abertura = str(row["Abertura (mm)"]).strip()
                massa = to_float(row["Massa (g)"])
                if abertura and massa > 0:
                    massas_dict[abertura] = massa

            if not massas_dict:
                st.error("Informe ao menos uma abertura com massa > 0.")
            else:
                novo = {
                    "amostra": amostra.strip(),
                    "data": data_ensaio.strftime("%d/%m/%Y"),
                    "umidade": float(umidade),
                    "massas": massas_dict,
                }
                ensaios.append(novo)
                data["ensaios"] = ensaios

                if save_data(data):
                    df_novo, total_novo = calcular_granulometria(massas_dict)
                    st.success(
                        f"✅ Ensaio '{amostra.strip()}' salvo com sucesso! "
                        f"Massa total: {total_novo:.2f} g"
                    )
                else:
                    st.error("Erro ao salvar o ensaio no arquivo.")
                if df_novo is not None:
                    st.markdown("**Tabela Calculada:**")
                    styled_novo = df_novo.style.apply(highlight_table, axis=None).format({
                        "Massa (g)": "{:.2f}",
                        "Freq. Simples (%)": "{:.2f}%",
                        "Ac. Retido (%)": format_pct,
                        "Ac. Passante (%)": format_pct,
                    })
                    st.dataframe(styled_novo, use_container_width=True, hide_index=True)
                st.rerun()

    st.divider()
    st.markdown("**Gerenciar Ensaios Registrados**")
    if not ensaios:
        st.info("Nenhum ensaio registrado ainda.")
    else:
        opcoes = [f"{e.get('amostra','Ensaio')} — {e.get('data','')}" for e in ensaios]
        sel = st.selectbox("Selecione o ensaio:", opcoes, key="manage_sel")
        idx = opcoes.index(sel)
        ensaio_sel = ensaios[idx]

        # ── Editar ensaio selecionado ───────────────────────────────────
        with st.expander("✏️ Editar ensaio selecionado", expanded=False):
            st.caption("Altere os campos e a tabela; clique em Salvar Alteracoes para gravar por cima.")

            ec1, ec2, ec3 = st.columns(3)
            with ec1:
                e_amostra = st.text_input(
                    "Identificacao da Amostra *",
                    value=ensaio_sel.get("amostra", ""),
                    key=f"edit_amostra_{idx}",
                )
            with ec2:
                try:
                    d_val = datetime.strptime(ensaio_sel.get("data", ""), "%d/%m/%Y").date()
                except Exception:
                    d_val = date.today()
                e_data = st.date_input("Data do Ensaio *", value=d_val, key=f"edit_data_{idx}")
            with ec3:
                e_umid = st.number_input(
                    "Umidade (%)", min_value=0.0, max_value=100.0,
                    value=float(to_float(ensaio_sel.get("umidade", 0))),
                    step=0.01, format="%.2f", key=f"edit_umid_{idx}",
                )

            st.markdown("**Aberturas (mm) e Massas Retidas (g)**")

            # Pré-preenche a tabela com as massas existentes (mantendo a ordem padrão),
            # deixando linhas extras em branco para acrescentar peneiras se quiser.
            massas_sel = ensaio_sel.get("massas", {})
            ordered_keys = [k for k in ABERTURAS if k in massas_sel] + \
                           [k for k in massas_sel if k not in ABERTURAS]
            ab_list = list(ordered_keys)
            massa_list = [to_float(massas_sel.get(k, 0)) for k in ordered_keys]
            while len(ab_list) < 15:
                ab_list.append("")
                massa_list.append(0.0)
            df_edit = pd.DataFrame({"Abertura (mm)": ab_list, "Massa (g)": massa_list})

            edited_edit_df = st.data_editor(
                df_edit,
                num_rows="fixed",
                use_container_width=True,
                hide_index=True,
                key=f"edit_table_{idx}",
                column_config={
                    "Abertura (mm)": st.column_config.TextColumn(
                        "Abertura (mm)", width="medium", help="Ex: 50.8, 38.1, <6.35",
                    ),
                    "Massa (g)": st.column_config.NumberColumn(
                        "Massa (g)", width="medium", min_value=0.0, step=0.01,
                        format="%.2f", help="Massa retida em gramas",
                    ),
                },
            )

            total_edit = sum(to_float(v) for v in edited_edit_df["Massa (g)"])
            cole1, cole2 = st.columns([3, 1])
            with cole2:
                st.metric("TOTAL (g)", f"{total_edit:.2f}")

            if st.button("💾 Salvar Alteracoes", type="primary",
                         use_container_width=True, key=f"save_edit_{idx}"):
                if not str(e_amostra).strip():
                    st.error("Informe a identificacao da amostra.")
                elif total_edit == 0:
                    st.error("Informe ao menos uma massa maior que zero.")
                else:
                    novas_massas = {}
                    for _, row in edited_edit_df.iterrows():
                        ab = str(row["Abertura (mm)"]).strip()
                        m = to_float(row["Massa (g)"])
                        if ab and m > 0:
                            novas_massas[ab] = m
                    if not novas_massas:
                        st.error("Informe ao menos uma abertura com massa > 0.")
                    else:
                        ensaios[idx] = {
                            "amostra": str(e_amostra).strip(),
                            "data": e_data.strftime("%d/%m/%Y"),
                            "umidade": float(e_umid),
                            "massas": novas_massas,
                        }
                        data["ensaios"] = ensaios
                        if save_data(data):
                            st.success(f"✅ Ensaio '{str(e_amostra).strip()}' atualizado!")
                            st.rerun()
                        else:
                            st.error("Erro ao salvar as alteracoes.")

        # ── Deletar ensaio selecionado ──────────────────────────────────
        if st.button("🗑️ Deletar Ensaio Selecionado", type="secondary"):
            ensaios.pop(idx)
            data["ensaios"] = ensaios
            if save_data(data):
                st.success("Ensaio deletado!")
                st.rerun()
            else:
                st.error("Erro ao deletar ensaio.")

# ── Rodapé ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    f"<div style='text-align:center;color:{PRIMARY};font-size:11px;padding:10px;'>"
    "Aura Minerals | Beneficiamento - Borborema | Granulometria de Moagem 1025 TC 02"
    "</div>",
    unsafe_allow_html=True,
)
