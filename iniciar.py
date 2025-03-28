import streamlit as st
from streamlit.runtime.scriptrunner import RerunException, RerunData
import os
import sys

# Função interna para forçar rerun (substitui st.experimental_rerun())
def force_rerun():
    raise RerunException(RerunData(None))

# Dicionário de usuários (NÃO use em produção sem hashing de senhas)
USERS = {
    "admin@grupochegou.com": {"password": "admgc2025", "cargo": "Administrador"},
    "usuario@grupochegou.com": {"password": "gc2025", "cargo": "Usuário"},
}

def login_page():
    """Página de Login."""
    st.title("Grupo Chegou - Dashboard")
    
    # Adicionar imagem ou logo da empresa aqui
    st.markdown('<div style="text-align: center; margin-bottom: 30px;"><img src="https://via.placeholder.com/250x100" alt="Logo Grupo Chegou"></div>', 
                unsafe_allow_html=True)
    
    st.subheader("Faça seu login")

    col1, col2 = st.columns([3, 2])
    
    with col1:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Senha", type="password")
            submit = st.form_submit_button("Entrar")
            
            if submit:
                if email in USERS and USERS[email]["password"] == password:
                    st.session_state["logged_in"] = True
                    st.session_state["cargo"] = USERS[email]["cargo"]
                    st.session_state["email"] = email
                    force_rerun()
                else:
                    st.error("Credenciais inválidas. Tente novamente.")
    
    with col2:
        st.markdown("""
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 10px; margin-top: 52px;">
            <h4>Acesso ao Sistema</h4>
            <p>Esta é a plataforma de gestão interna do Grupo Chegou.</p>
            <p>Se você não possui acesso, entre em contato com o administrador.</p>
        </div>
        """, unsafe_allow_html=True)

def show_logout_button():
    """Exibe informações do usuário e botão de logout na sidebar."""
    st.sidebar.markdown(f"""
    <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 20px;">
        <p><strong>Usuário:</strong> {st.session_state.get('email')}</p>
        <p><strong>Cargo:</strong> {st.session_state.get('cargo')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.sidebar.button("Sair do Sistema"):
        st.session_state["logged_in"] = False
        st.session_state["cargo"] = None
        st.session_state["email"] = None
        force_rerun()

def main():
    # Configuração da página
    st.set_page_config(
        page_title="Dashboard Grupo Chegou",
        page_icon="🏢",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Inicializa variáveis de sessão
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if "cargo" not in st.session_state:
        st.session_state["cargo"] = None

    # Se NÃO estiver logado, exibe apenas a página de login
    if not st.session_state["logged_in"]:
        login_page()
    else:
        # Define páginas de acordo com o cargo
        if st.session_state["cargo"] == "Administrador":
            pages = {
                "Principal": [
                    st.Page("Principal/Home.py", title="Home", icon="🏠"),
                    st.Page("Principal/Calendário.py", title="Calendário", icon="📅")
                ],
                "Dashboard": [
                    st.Page("Dashboard/Dash Jira.py", title="Dashboard Jira", icon="📊"),
                    st.Page("Dashboard/ia.py", title="Projetos IA", icon="🤖")
                ]
            }
        else:
            # Usuário comum
            pages = {
                "Principal": [
                    st.Page("Principal/Home.py", title="Home", icon="🏠"),
                    st.Page("Principal/Calendário.py", title="Calendário", icon="📅")
                ],
                "Dashboard": [
                    st.Page("Dashboard/Dash Jira.py", title="Dashboard Jira", icon="📊")
                ]
            }

        # Cria a barra de navegação
        pg = st.navigation(pages, position="sidebar", expanded=False)
        # Exibe botão de logout
        show_logout_button()
        # Executa a página selecionada
        pg.run()

if __name__ == "__main__":
    main()