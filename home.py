import streamlit as st
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
    .highlight {
        background-color: #f0f7ff;
        border-left: 5px solid #1E88E5;
        padding: 20px;
        margin-bottom: 20px;
    }
    .feature-card {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    }
    .feature-icon {
        font-size: 2rem;
        color: #1E88E5;
        margin-bottom: 10px;
    }
    .feature-title {
        font-size: 1.2rem;
        font-weight: bold;
        margin-bottom: 10px;
        color: #1E88E5;
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
    Navegue até a página de Calendários para ver todas as agendas.</p>
</div>
""", unsafe_allow_html=True)

# Recursos do sistema
st.subheader("Recursos Disponíveis")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">📅</div>
        <div class="feature-title">Visualização de Calendários</div>
        <p>Visualize calendários individuais ou de toda a equipe em um único lugar</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-card">
        <div class="feature-icon">👥</div>
        <div class="feature-title">Gerenciamento Centralizado</div>
        <p>Adicione e gerencie múltiplos calendários de forma centralizada</p>
    </div>
    """, unsafe_allow_html=True)

# Instruções de uso
st.subheader("Como usar este dashboard")
st.markdown("""
1. **Navegue para a página de Calendários** usando a barra lateral
2. **Adicione emails** dos calendários que deseja acompanhar
3. **Visualize agendas** individuais ou de toda a equipe

Para adicionar um calendário ao sistema, basta fornecer o email do Google Calendário.
""")

# Data da última atualização
st.sidebar.markdown(f"**Última atualização:** {datetime.now().strftime('%d/%m/%Y %H:%M')}")
