import streamlit as st
import os
import pandas as pd
import altair as alt
import json
from urllib.request import urlopen

# Nota: A configuração do servidor deve ser feita via command line ou config.toml
# e não pode ser alterada programaticamente no código

# Configuração da página inicial
st.set_page_config(
    page_title="Gestão Grupo Chegou",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
def add_custom_css():
    st.markdown("""
    <style>
    .main {
        padding: 1rem;
        background-color: #f8f9fa;
    }
    .block-container {
        max-width: 1200px;
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    h1 {
        color: #1e3a8a;
        font-weight: 700;
        margin-bottom: 1.5rem;
    }
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.875rem;
        font-weight: 600;
        margin-right: 0.5rem;
    }
    .selling {
        background-color: #0d9488;
        color: white;
    }
    .testing {
        background-color: #e6b405;
        color: white;
    }
    .discontinued {
        background-color: #dc2626;
        color: white;
    }
    .country-card {
        background-color: white;
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12), 0 1px 2px rgba(0, 0, 0, 0.24);
        border-left: 5px solid #ccc;
    }
    .country-card.selling {
        border-left-color: #0d9488;
    }
    .country-card.testing {
        border-left-color: #e6b405;
    }
    .country-card.discontinued {
        border-left-color: #dc2626;
    }
    .country-name {
        font-weight: 600;
        font-size: 1.1rem;
        margin-bottom: 0.5rem;
    }
    .map-container {
        background-color: white;
        border-radius: 0.5rem;
        padding: 1.5rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12), 0 1px 2px rgba(0, 0, 0, 0.24);
        margin-bottom: 1.5rem;
    }
    .header-info {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
        padding: 1rem;
        background-color: white;
        border-radius: 0.5rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12), 0 1px 2px rgba(0, 0, 0, 0.24);
    }
    .stats-container {
        display: flex;
        flex-wrap: wrap;
        gap: 1rem;
        margin-bottom: 1.5rem;
    }
    .stat-card {
        background-color: white;
        border-radius: 0.5rem;
        padding: 1rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12), 0 1px 2px rgba(0, 0, 0, 0.24);
        flex: 1;
        min-width: 200px;
        text-align: center;
    }
    .stat-value {
        font-size: 2rem;
        font-weight: 700;
        color: #1e3a8a;
    }
    .stat-label {
        font-size: 0.875rem;
        color: #6b7280;
        margin-top: 0.5rem;
    }
    .legend {
        display: flex;
        justify-content: center;
        gap: 1rem;
        margin-top: 1rem;
        margin-bottom: 1rem;
    }
    .legend-item {
        display: flex;
        align-items: center;
    }
    .legend-color {
        width: 16px;
        height: 16px;
        border-radius: 4px;
        margin-right: 0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)

# Função para obter os dados dos países
def get_countries_data():
    countries = [
        {"id": "BRA", "name": "Brasil", "status": "discontinued", "iso_alpha": "BRA", "description": "Foi um dos primeiros mercados internacionais, mas operações encerradas em 2022."},
        {"id": "PAN", "name": "Panamá", "status": "discontinued", "iso_alpha": "PAN", "description": "Operações iniciadas em 2019 e encerradas em 2023 devido a desafios logísticos."},
        {"id": "CHL", "name": "Chile", "status": "selling", "iso_alpha": "CHL", "description": "Mercado em crescimento desde 2020, com forte presença nas principais cidades."},
        {"id": "MEX", "name": "México", "status": "selling", "iso_alpha": "MEX", "description": "Um dos mercados mais importantes, com operações desde 2018."},
        {"id": "ECU", "name": "Equador", "status": "selling", "iso_alpha": "ECU", "description": "Operações estáveis e lucrativas desde 2021."},
        {"id": "COL", "name": "Colômbia", "status": "selling", "iso_alpha": "COL", "description": "Mercado em expansão com alto potencial de crescimento."},
        {"id": "ESP", "name": "Espanha", "status": "testing", "iso_alpha": "ESP", "description": "Fase de testes iniciada em 2024, avaliando viabilidade do mercado europeu."},
        {"id": "PRT", "name": "Portugal", "status": "testing", "iso_alpha": "PRT", "description": "Testes iniciais com potencial para ser porta de entrada para Europa."},
        {"id": "ARG", "name": "Argentina", "status": "testing", "iso_alpha": "ARG", "description": "Em fase de análise de mercado desde início de 2024."}
    ]
    return countries

# Função para obter o status label formatado
def get_status_badge(status):
    if status == "selling":
        return '<span class="status-badge selling">Vendendo</span>'
    elif status == "testing":
        return '<span class="status-badge testing">Em Teste</span>'
    else:  # discontinued
        return '<span class="status-badge discontinued">Descontinuado</span>'

# Função para obter a cor do país no mapa
def get_country_color(status):
    if status == "selling":
        return "#0d9488"  # Verde
    elif status == "testing":
        return "#e6b405"  # Amarelo
    else:  # discontinued
        return "#dc2626"  # Vermelho

# Função para criar o mapa com Vega-Altair
def create_world_map(countries_data):
    # Preparar os dados para o mapa
    countries_df = pd.DataFrame(countries_data)
    
    # Carregar o TopoJSON dos países do mundo
    url = "https://raw.githubusercontent.com/topojson/world-atlas/master/countries-110m.json"
    
    # Criar o gráfico com Altair
    countries_chart = alt.Chart(url).mark_geoshape(
        stroke='white',
        strokeWidth=0.5
    ).encode(
        color=alt.value('#CCCCCC')
    ).properties(
        width=900,
        height=500
    )
    
    # Adicionar os países destacados
    highlighted_countries = alt.Chart(url).mark_geoshape(
        stroke='white',
        strokeWidth=0.5
    ).encode(
        color=alt.condition(
            alt.datum.id.isin(countries_df['iso_alpha'].tolist()),
            alt.Color('status:N', 
                      scale=alt.Scale(
                          domain=['selling', 'testing', 'discontinued'],
                          range=['#0d9488', '#e6b405', '#dc2626']
                      ),
                      legend=None
                     ),
            alt.value('#CCCCCC')
        ),
        tooltip=['id:N', 'name:N', 'status:N']
    ).transform_lookup(
        lookup='id',
        from_=alt.LookupData(countries_df, 'iso_alpha', ['name', 'status'])
    )
    
    return (countries_chart + highlighted_countries).project('equalEarth')

# Função principal
def main():
    add_custom_css()
    
    # Cabeçalho com logo (placeholder)
    st.markdown('<div class="header-info">'
                '<div><h1>🏢 Gestão Grupo Chegou</h1></div>'
                '<div><img src="https://via.placeholder.com/150x50" alt="Logo Grupo Chegou"></div>'
                '</div>', 
                unsafe_allow_html=True)
    
    # Obter dados dos países
    countries_data = get_countries_data()
    
    # Calcular estatísticas
    total_countries = len(countries_data)
    selling_countries = len([c for c in countries_data if c['status'] == 'selling'])
    testing_countries = len([c for c in countries_data if c['status'] == 'testing'])
    discontinued_countries = len([c for c in countries_data if c['status'] == 'discontinued'])
    
    # Mostrar estatísticas
    st.markdown('<div class="stats-container">'
                '<div class="stat-card">'
                f'<div class="stat-value">{total_countries}</div>'
                '<div class="stat-label">Países</div>'
                '</div>'
                '<div class="stat-card">'
                f'<div class="stat-value" style="color: #0d9488">{selling_countries}</div>'
                '<div class="stat-label">Vendendo Atualmente</div>'
                '</div>'
                '<div class="stat-card">'
                f'<div class="stat-value" style="color: #e6b405">{testing_countries}</div>'
                '<div class="stat-label">Em Fase de Testes</div>'
                '</div>'
                '<div class="stat-card">'
                f'<div class="stat-value" style="color: #dc2626">{discontinued_countries}</div>'
                '<div class="stat-label">Descontinuados</div>'
                '</div>'
                '</div>', 
                unsafe_allow_html=True)
    
    # Container do mapa
    st.markdown('<div class="map-container">', unsafe_allow_html=True)
    st.subheader("🌎 Presença Internacional do Grupo Chegou")
    
    # Legenda
    st.markdown('<div class="legend">'
                '<div class="legend-item"><div class="legend-color" style="background-color: #0d9488;"></div>Vendendo Atualmente</div>'
                '<div class="legend-item"><div class="legend-color" style="background-color: #e6b405;"></div>Em Fase de Testes</div>'
                '<div class="legend-item"><div class="legend-color" style="background-color: #dc2626;"></div>Descontinuado</div>'
                '</div>', 
                unsafe_allow_html=True)
    
    # Exibir o mapa
    try:
        world_map = create_world_map(countries_data)
        st.altair_chart(world_map, use_container_width=True)
    except Exception as e:
        st.error(f"Não foi possível renderizar o mapa: {str(e)}")
        
        # Fallback para quando o mapa não puder ser renderizado
        st.markdown("### Distribuição Geográfica")
        for status in ["selling", "testing", "discontinued"]:
            status_label = "Vendendo Atualmente" if status == "selling" else "Em Fase de Testes" if status == "testing" else "Descontinuado"
            st.markdown(f"#### {status_label}")
            
            cols = st.columns(3)
            filtered_countries = [c for c in countries_data if c['status'] == status]
            
            for i, country in enumerate(filtered_countries):
                col_index = i % 3
                cols[col_index].markdown(f"🌎 **{country['name']}**")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Detalhar informações dos países por categoria
    st.subheader("📊 Detalhamento por Status")
    
    tab1, tab2, tab3 = st.tabs(["Vendendo Atualmente", "Em Fase de Testes", "Descontinuados"])
    
    with tab1:
        selling_countries = [c for c in countries_data if c['status'] == 'selling']
        if selling_countries:
            for country in selling_countries:
                st.markdown(f"""
                <div class="country-card selling">
                    <div class="country-name">{country['name']} {get_status_badge('selling')}</div>
                    <p>{country['description']}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Não há países nesta categoria.")
    
    with tab2:
        testing_countries = [c for c in countries_data if c['status'] == 'testing']
        if testing_countries:
            for country in testing_countries:
                st.markdown(f"""
                <div class="country-card testing">
                    <div class="country-name">{country['name']} {get_status_badge('testing')}</div>
                    <p>{country['description']}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Não há países nesta categoria.")
    
    with tab3:
        discontinued_countries = [c for c in countries_data if c['status'] == 'discontinued']
        if discontinued_countries:
            for country in discontinued_countries:
                st.markdown(f"""
                <div class="country-card discontinued">
                    <div class="country-name">{country['name']} {get_status_badge('discontinued')}</div>
                    <p>{country['description']}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Não há países nesta categoria.")

if __name__ == "__main__":
    main()