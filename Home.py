import streamlit as st
import os
import pandas as pd
import plotly.express as px

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
    .admin-section {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        margin-top: 20px;
        border: 1px solid #e9ecef;
    }
    .admin-button {
        background-color: #6c757d;
        color: white;
        font-size: 0.8rem;
        padding: 0.3rem 0.6rem;
        border-radius: 5px;
        margin-bottom: 10px;
        cursor: pointer;
        text-align: center;
        display: inline-block;
        float: right;
    }
    </style>
    """, unsafe_allow_html=True)

# Função para obter os dados dos países
def get_countries_data():
    # Verificar se já existem países salvos na sessão
    if 'countries_data' not in st.session_state:
        # Dados iniciais
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
        st.session_state.countries_data = countries
    
    return st.session_state.countries_data

# Função para adicionar um novo país
def add_country(name, status, iso_alpha, description):
    if not name or not iso_alpha or not status or not description:
        return False, "Todos os campos são obrigatórios."
    
    # Verificar se o país já existe
    countries = get_countries_data()
    if any(c['iso_alpha'] == iso_alpha for c in countries):
        return False, f"País com código {iso_alpha} já existe."
    
    # Criar novo país
    new_country = {
        "id": iso_alpha,
        "name": name,
        "status": status,
        "iso_alpha": iso_alpha,
        "description": description
    }
    
    # Adicionar à lista
    st.session_state.countries_data.append(new_country)
    return True, f"País {name} adicionado com sucesso!"

# Função para obter o status label formatado
def get_status_badge(status):
    if status == "selling":
        return '<span class="status-badge selling">Vendendo</span>'
    elif status == "testing":
        return '<span class="status-badge testing">Em Teste</span>'
    else:  # discontinued
        return '<span class="status-badge discontinued">Descontinuado</span>'

# Função para criar o mapa com Plotly Express
def create_world_map_plotly(countries_data):
    # Preparar dados para o plotly
    df = pd.DataFrame(countries_data)
    
    # Mapeamento de status para cores e números (para o choropleth)
    status_map = {
        "selling": 3,       # Verde (atualmente vendendo)
        "testing": 2,       # Amarelo (em teste)
        "discontinued": 1   # Vermelho (descontinuado)
    }
    
    # Adicionar valor numérico para colorir o mapa
    df['status_value'] = df['status'].map(status_map)
    
    # Mapear status para texto legível
    status_text_map = {
        "selling": "Vendendo Atualmente",
        "testing": "Em Fase de Testes",
        "discontinued": "Descontinuado"
    }
    df['status_text'] = df['status'].map(status_text_map)
    
    # Criar o mapa choropleth
    fig = px.choropleth(
        df,
        locations="iso_alpha",  # Coluna com os códigos ISO Alpha-3
        color="status_value",   # Coluna com os valores para colorir
        hover_name="name",      # Nome ao passar o mouse
        color_continuous_scale=[[0, '#CCCCCC'], [0.25, '#dc2626'], [0.5, '#e6b405'], [0.75, '#0d9488']],
        range_color=[0, 3],
        labels={'status_value': 'Status'},
        custom_data=['name', 'status_text', 'description']  # Dados para mostrar no hover
    )
    
    # Configurar o hover template
    fig.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>Status: %{customdata[1]}<br>%{customdata[2]}"
    )
    
    # Configurações gerais do mapa
    fig.update_layout(
        geo=dict(
            showframe=False,
            showcoastlines=True,
            projection_type='natural earth'
        ),
        coloraxis_showscale=False,  # Esconder a barra de escala
        margin=dict(l=0, r=0, t=0, b=0),  # Remover margens
        height=600
    )
    
    return fig

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
        # Usar Plotly Express para renderizar o mapa
        fig = create_world_map_plotly(countries_data)
        st.plotly_chart(fig, use_container_width=True)
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
    tabs = st.tabs(["Vendendo Atualmente", "Em Fase de Testes", "Descontinuados", "Todos os Países"])
    
    with tabs[0]:  # Vendendo Atualmente
        selling_countries = [c for c in countries_data if c['status'] == 'selling']
        if selling_countries:
            for country in selling_countries:
                st.markdown(f"""
                <div class="country-card selling">
                    <div class="country-name">{country['name']} ({country['iso_alpha']}) {get_status_badge('selling')}</div>
                    <p>{country['description']}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Não há países nesta categoria.")
    
    with tabs[1]:  # Em Fase de Testes
        testing_countries = [c for c in countries_data if c['status'] == 'testing']
        if testing_countries:
            for country in testing_countries:
                st.markdown(f"""
                <div class="country-card testing">
                    <div class="country-name">{country['name']} ({country['iso_alpha']}) {get_status_badge('testing')}</div>
                    <p>{country['description']}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Não há países nesta categoria.")
    
    with tabs[2]:  # Descontinuados
        discontinued_countries = [c for c in countries_data if c['status'] == 'discontinued']
        if discontinued_countries:
            for country in discontinued_countries:
                st.markdown(f"""
                <div class="country-card discontinued">
                    <div class="country-name">{country['name']} ({country['iso_alpha']}) {get_status_badge('discontinued')}</div>
                    <p>{country['description']}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Não há países nesta categoria.")
    
    with tabs[3]:  # Todos os Países
        # Exibição em formato de tabela para fácil visualização
        if countries_data:
            # Preparar dados para a tabela
            data_for_table = []
            for country in countries_data:
                status_text = {
                    "selling": "Vendendo Atualmente",
                    "testing": "Em Fase de Testes", 
                    "discontinued": "Descontinuado"
                }.get(country['status'])
                
                data_for_table.append({
                    "Nome": country['name'],
                    "Código ISO": country['iso_alpha'],
                    "Status": status_text,
                    "Descrição": country['description']
                })
            
            # Criar DataFrame e mostrar como tabela
            df = pd.DataFrame(data_for_table)
            st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Botão de administração (discreto) na parte inferior da página
    st.markdown('<p class="admin-button" id="admin-button">Administração</p>', unsafe_allow_html=True)
    
    # Seção de administração (só aparece quando o expander é clicado)
    with st.expander("Administração de Países", expanded=False):
        st.subheader("📝 Cadastro de Novo País")
        
        with st.form("add_country_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                country_name = st.text_input("Nome do País")
                country_iso = st.text_input("Código ISO Alpha-3 (3 letras)", 
                                      help="Código de 3 letras do país, ex: BRA, USA, CAN")
            
            with col2:
                country_status = st.selectbox(
                    "Status",
                    options=["selling", "testing", "discontinued"],
                    format_func=lambda x: {
                        "selling": "Vendendo Atualmente",
                        "testing": "Em Fase de Testes",
                        "discontinued": "Descontinuado"
                    }.get(x)
                )
            
            country_description = st.text_area("Descrição")
            
            submitted = st.form_submit_button("Adicionar País")
            
            if submitted:
                success, message = add_country(
                    country_name, 
                    country_status, 
                    country_iso.upper() if country_iso else "", 
                    country_description
                )
                
                if success:
                    st.success(message)
                else:
                    st.error(message)
        
        # Lista de códigos ISO Comuns
        with st.expander("Lista de Códigos ISO Comuns"):
            st.markdown("""
            - Argentina: ARG
            - Bolívia: BOL
            - Brasil: BRA
            - Canadá: CAN
            - Chile: CHL
            - China: CHN
            - Colômbia: COL
            - Equador: ECU
            - Espanha: ESP
            - Estados Unidos: USA
            - França: FRA
            - Itália: ITA
            - México: MEX
            - Panamá: PAN
            - Peru: PER
            - Portugal: PRT
            - Reino Unido: GBR
            - Uruguai: URY
            - Venezuela: VEN
            """)

if __name__ == "__main__":
    main()