import streamlit as st
from datetime import datetime
from streamlit.components.v1 import html

# Configuração da página
st.set_page_config(
    page_title="Calendários - Dashboard da Empresa",
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
    .calendar-container {
        margin-top: 20px;
        border-radius: 5px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        padding: 10px;
        background-color: white;
    }
    .stButton>button {
        width: 100%;
    }
    .email-form {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        border: 1px solid #e9ecef;
    }
    .email-list {
        background-color: white;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .email-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 0;
        border-bottom: 1px solid #f1f1f1;
    }
    </style>
    """, unsafe_allow_html=True)

# Aplicar CSS
local_css()

# ======= FUNÇÕES PARA GERENCIAR CALENDÁRIOS =======

def exibir_iframe_calendario(calendario_email):
    """Exibe o iframe com o calendário especificado"""
    iframe_html = f"""
    <div class="calendar-container">
        <iframe src="https://calendar.google.com/calendar/embed?src={calendario_email}&ctz=America%2FSao_Paulo" 
                style="border: 0" width="100%" height="600" frameborder="0" scrolling="no"></iframe>
    </div>
    """
    html(iframe_html, height=650)


# ======= INTERFACE STREAMLIT =======

def main():
    st.title("📅 Calendários da Empresa")
    
    # Inicializa estado da sessão para armazenar emails dos calendários
    if 'calendarios' not in st.session_state:
        st.session_state.calendarios = ["viniciuschegouoperacional@gmail.com"]  # Calendário inicial
    
    # Área de gerenciamento de calendários (movida da barra lateral)
    st.subheader("Gerenciar Calendários")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Form para adicionar novo calendário
        st.markdown('<div class="email-form">', unsafe_allow_html=True)
        novo_calendario = st.text_input("Adicionar novo calendário (email):")
        adicionar = st.button("Adicionar Calendário")
        st.markdown('</div>', unsafe_allow_html=True)
        
        if adicionar:
            if novo_calendario and novo_calendario not in st.session_state.calendarios:
                st.session_state.calendarios.append(novo_calendario)
                st.success(f"Calendário {novo_calendario} adicionado!")
                st.rerun()
    
    with col2:
        # Lista de calendários adicionados
        st.markdown('<div class="email-list">', unsafe_allow_html=True)
        st.write("Calendários adicionados:")
        
        for i, cal in enumerate(st.session_state.calendarios):
            st.markdown(f'<div class="email-item">', unsafe_allow_html=True)
            col_a, col_b = st.columns([3, 1])
            col_a.write(f"{cal}")
            if col_b.button("Remover", key=f"remove_{i}"):
                st.session_state.calendarios.pop(i)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Área de visualização de calendários
    st.header("Visualização de Calendários")
    
    # Seleção de calendário para visualizar
    calendario_selecionado = st.selectbox(
        "Selecione um calendário para visualizar:",
        st.session_state.calendarios
    )
    
    # Exibir o calendário usando iframe
    exibir_iframe_calendario(calendario_selecionado)
    
    # Opção para visualizar todos os calendários juntos (modo de grupo)
    if st.checkbox("Visualizar todos os calendários juntos"):
        calendarios_encoded = ",".join([cal.replace("@", "%40") for cal in st.session_state.calendarios])
        iframe_todos = f"""
        <div class="calendar-container">
            <iframe src="https://calendar.google.com/calendar/embed?src={calendarios_encoded}&ctz=America%2FSao_Paulo" 
                    style="border: 0" width="100%" height="600" frameborder="0" scrolling="no"></iframe>
        </div>
        """
        html(iframe_todos, height=650)


if __name__ == "__main__":
    main()