import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime

# Configuração da página inicial
st.set_page_config(
    page_title="Dashboard de Calendários da Empresa",
    page_icon="📅",
    layout="wide"
)

# Função para adicionar CSS personalizado
def local_css():
    st.markdown("""
    <style>
    .main {
        padding: 1rem;
    }
    .stCard {
        margin-top: 20px;
        border-radius: 10px !important;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1) !important;
    }
    .card-container {
        display: flex;
        gap: 20px;
        flex-wrap: wrap;
    }
    .card {
        background-color: white;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        padding: 20px;
        margin-bottom: 20px;
        transition: transform 0.3s;
    }
    .card:hover {
        transform: translateY(-5px);
    }
    .card-title {
        font-size: 1.2rem;
        font-weight: bold;
        margin-bottom: 10px;
        color: #1E88E5;
    }
    .card-value {
        font-size: 2rem;
        font-weight: bold;
        color: #333;
    }
    .highlight {
        background-color: #f0f7ff;
        border-left: 5px solid #1E88E5;
        padding: 20px;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# Aplicar CSS
local_css()

# Página inicial
st.title("📅 Dashboard de Calendários da Empresa")

# Introdução
st.markdown("""
<div class="highlight">
    <h3>Bem-vindo ao Dashboard de Calendários da Empresa</h3>
    <p>Esta aplicação permite visualizar e gerenciar os calendários de todos os funcionários em um único lugar.
    Navegue até a página de Calendários para ver todas as agendas e estatísticas.</p>
</div>
""", unsafe_allow_html=True)

# Métricas principais
st.subheader("Resumo")

# Dados simulados para a página inicial
total_calendarios = 5  # Simulado
total_eventos_mes = 42  # Simulado
eventos_hoje = 8  # Simulado

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("""
    <div class="card">
        <div class="card-title">Total de Calendários</div>
        <div class="card-value">{}</div>
    </div>
    """.format(total_calendarios), unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="card">
        <div class="card-title">Eventos este mês</div>
        <div class="card-value">{}</div>
    </div>
    """.format(total_eventos_mes), unsafe_allow_html=True)
    
with col3:
    st.markdown("""
    <div class="card">
        <div class="card-title">Eventos hoje</div>
        <div class="card-value">{}</div>
    </div>
    """.format(eventos_hoje), unsafe_allow_html=True)

# Gráfico simulado
st.subheader("Eventos por departamento")

# Dados simulados para o gráfico
dados_grafico = pd.DataFrame({
    'Departamento': ['TI', 'Marketing', 'Vendas', 'RH', 'Financeiro'],
    'Eventos': [12, 8, 15, 7, 10]
})

chart = alt.Chart(dados_grafico).mark_bar().encode(
    x='Departamento',
    y='Eventos',
    color=alt.Color('Departamento', scale=alt.Scale(scheme='category10'))
).properties(
    title='Distribuição de Eventos por Departamento',
    width=600
)

st.altair_chart(chart, use_container_width=True)

# Informações de uso
st.subheader("Como usar este dashboard")
st.markdown("""
1. **Navegue para a página de Calendários** usando a barra lateral
2. **Adicione emails** dos calendários que deseja acompanhar
3. **Visualize agendas** individuais ou de toda a equipe
4. **Analise estatísticas** e distribuição de eventos

Para adicionar seu calendário ao sistema, forneça seu email do Google Calendario.
""")

# Data da última atualização
st.sidebar.markdown(f"**Última atualização:** {datetime.now().strftime('%d/%m/%Y %H:%M')}")
