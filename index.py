# coding: utf-8
"""
Script para download, processamento e visualização de dados do JotForm
em mapa interativo (Folium) com menu accordion dinâmico por Núcleo de Atuação.
Autor: Assis
Data: 2025-09-15
"""

import os
import requests
import pandas as pd
import folium
from io import BytesIO
from datetime import datetime
from folium.plugins import Fullscreen

# ---------------------------------------------------------------------
# Configurações
# ---------------------------------------------------------------------
URL_OCORRENCIAS = "https://www.jotform.com/excel/242924996615066"
URL_AREA_ATUACAO = "https://www.jotform.com/excel/243393249284060"
OUTPUT_PATH = os.path.join(os.getcwd(), "mapa_tamanduatei.html")

# ---------------------------------------------------------------------
# Funções utilitárias
# ---------------------------------------------------------------------
def baixar_excel(url: str) -> pd.DataFrame:
    """Baixa um arquivo Excel do JotForm e retorna um DataFrame Pandas."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return pd.read_excel(BytesIO(response.content))
    except requests.RequestException as e:
        print(f"[ERRO] Falha ao baixar arquivo: {url}\nDetalhes: {e}")
        return pd.DataFrame()

def converter_coluna_numerica(df: pd.DataFrame, coluna: str) -> pd.Series:
    """Converte coluna de string com vírgula em número float."""
    if coluna in df.columns:
        return pd.to_numeric(
            df[coluna].astype(str).str.replace(",", ".", regex=False),
            errors="coerce"
        )
    return pd.Series(dtype="float64")

# ---------------------------------------------------------------------
# Processamento de dados
# ---------------------------------------------------------------------
print("[INFO] Baixando dados de ocorrências...")
df_ocorrencias = baixar_excel(URL_OCORRENCIAS)
print("[INFO] Baixando dados de área de atuação...")
df_area = baixar_excel(URL_AREA_ATUACAO)

if df_ocorrencias.empty or df_area.empty:
    raise SystemExit("[ERRO] Não foi possível carregar os dados necessários.")

# Filtrar ocorrências válidas
df_ocorrencias = df_ocorrencias.dropna(subset=["NÚCLEO_DE_ATUAÇÃO"])

# Totais principais
total_ocorrencias = df_ocorrencias["OCORRÊNCIA DE CAMPO CADASTRO"].notna().sum()
soma_caixa_uma = df_ocorrencias["OCORRÊNCIA DE CAMPO CAIXA UMA"].notna().sum()
total_quantidade_instalacao = df_ocorrencias["OCORRÊNCIA DE CAMPO LIGAÇÃO"].notna().sum()

# Totais de redes
df_area["TOTAL DE REDE ESGOTO 200"] = converter_coluna_numerica(df_area, "TOTAL DE REDE ESGOTO 200")
df_area["TOTAL DE REDE 110 ÁGUA"] = converter_coluna_numerica(df_area, "TOTAL DE REDE 110 ÁGUA")
total_rede_esgoto = df_area["TOTAL DE REDE ESGOTO 200"].sum()
total_rede_agua = df_area["TOTAL DE REDE 110 ÁGUA"].sum()

# Resumo por núcleo
resumo_nucleo = df_ocorrencias.groupby("NÚCLEO_DE_ATUAÇÃO")["OCORRÊNCIA DE CAMPO CADASTRO"].count().to_dict()

# Resumo por data
df_ocorrencias["DATA CADASTRO"] = pd.to_datetime(df_ocorrencias["DATA CADASTRO"], errors="coerce")
resumo_data = df_ocorrencias.groupby(df_ocorrencias["DATA CADASTRO"].dt.date).size().to_dict()

# ---------------------------------------------------------------------
# Construção do Mapa
# ---------------------------------------------------------------------
m = folium.Map(location=[-23.55, -46.63], zoom_start=12, tiles="cartodbpositron")
Fullscreen(position='topright').add_to(m)

# Menu accordion dinâmico
html_menu = f"""
<div style="
    position: fixed;
    top: 80px;
    left: 20px;
    width: 360px;
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    font-family: Arial, sans-serif;
    font-size: 14px;
    z-index:9999;
">
<h4 style="
    margin: 0;
    padding: 10px;
    background: #2a5599;
    color: white;
    border-radius: 12px 12px 0 0;
    font-size: 16px;
    text-align: center;
">📊 Resumos</h4>
<div style="padding: 10px;">
    <details open>
        <summary style="cursor: pointer; font-weight: bold; margin-bottom: 5px;">
            📌 Resumo Geral
        </summary>
        <div style="margin-left: 10px; margin-top: 5px;">
            <table style="width: 100%; border-collapse: collapse; text-align: center;">
                <tr><th>Ocorrência</th><th>Caixa Uma</th><th>Ligações</th><th>Rede Água</th><th>Rede Esgoto</th></tr>
                <tr>
                    <td>{total_ocorrencias}</td>
                    <td>{soma_caixa_uma}</td>
                    <td>{total_quantidade_instalacao}</td>
                    <td>{total_rede_agua}</td>
                    <td>{total_rede_esgoto}</td>
                </tr>
            </table>
        </div>
    </details>
    <details>
        <summary style="cursor: pointer; font-weight: bold; margin-bottom: 5px;">
            🏙️ Resumo por Núcleo de Atuação
        </summary>
        <div style="margin-left: 10px; margin-top: 5px;">
            <table style="width: 100%; border-collapse: collapse; text-align: center;">
                <tr><th>Núcleo</th><th>Ocorrências</th></tr>
                {''.join([f"<tr><td>{n}</td><td>{q}</td></tr>" for n,q in resumo_nucleo.items()])}
            </table>
        </div>
    </details>
    <details>
        <summary style="cursor: pointer; font-weight: bold; margin-bottom: 5px;">
            📅 Resumo por Data
        </summary>
        <div style="margin-left: 10px; margin-top: 5px;">
            <table style="width: 100%; border-collapse: collapse; text-align: center;">
                <tr><th>Data</th><th>Executados</th></tr>
                {''.join([f"<tr><td>{d}</td><td>{q}</td></tr>" for d,q in resumo_data.items()])}
            </table>
        </div>
    </details>
</div>
</div>
"""
m.get_root().html.add_child(folium.Element(html_menu))

# ---------------------------------------------------------------------
# Criar FeatureGroups por núcleo e adicionar marcadores
# ---------------------------------------------------------------------
cores = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'cadetblue', 'darkgreen']
nucleos = df_ocorrencias["NÚCLEO_DE_ATUAÇÃO"].unique()
cores_nucleo = {nucleo: cores[i % len(cores)] for i, nucleo in enumerate(nucleos)}

for bairro in nucleos:
    fg = folium.FeatureGroup(name=bairro)
    
    # Filtrar ocorrências deste núcleo
    df_nucleo = df_ocorrencias[df_ocorrencias["NÚCLEO_DE_ATUAÇÃO"] == bairro]
    
    for _, row in df_nucleo.iterrows():
        if pd.notna(row.get("Geolocation", None)) and "," in row["Geolocation"]:
            try:
                lat, lng = map(float, row["Geolocation"].split(","))
                popup_html = f"""
                    <b>Núcleo:</b> {row['NÚCLEO_DE_ATUAÇÃO']}<br>
                    <b>Ocorrência:</b> {row['OCORRÊNCIA DE CAMPO CADASTRO']}<br>
                    <b>Funcionário:</b> {row.get('FUNCIONÁRIO CADASTRO','N/A')}
                """
                folium.Marker(
                    location=[lat, lng],
                    popup=popup_html,
                    icon=folium.Icon(color=cores_nucleo[bairro], icon='info-sign')
                ).add_to(fg)
            except ValueError:
                continue
    
    fg.add_to(m)

# LayerControl sem colapsar
folium.LayerControl(collapsed=False).add_to(m)

# ---------------------------------------------------------------------
# Exportação
# ---------------------------------------------------------------------
m.save(OUTPUT_PATH)
print(f"[SUCESSO] Mapa salvo em: {OUTPUT_PATH}")
