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
    # Configuração da página (deve ser a primeira chamada Streamlit)
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
        # Adiciona database ao path do sistema para que os scripts possam encontrar
        # Ajustes para PostgreSQL
        if "db_configured" not in st.session_state:
            # Configurar conexão com PostgreSQL
            os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL", "")
            st.session_state["db_configured"] = True
        
        # Define páginas customizadas sem usar st.set_page_config em cada página
        if st.session_state["cargo"] == "Administrador":
            st.sidebar.title("🏢 Grupo Chegou")
            st.sidebar.markdown("### Navegação")
            
            menu = st.sidebar.radio(
                "Selecione uma página:",
                ["Home", "Calendário", "Dashboard Jira", "Projetos IA"],
                label_visibility="collapsed"
            )
            
            # Exibe botão de logout
            show_logout_button()
            
            # Carrega a página selecionada mas evita chamar set_page_config
            if menu == "Home":
                # Importação customizada para evitar set_page_config
                with open("Principal/Home.py", "r", encoding="utf-8") as f:
                    home_code = f.read()
                # Remover chamadas a set_page_config
                home_code = "\n".join([line for line in home_code.split("\n") 
                                     if "set_page_config" not in line])
                # Executar código modificado
                exec(home_code, globals())
                
            elif menu == "Calendário":
                try:
                    # Configurar conexão com banco antes de importar
                    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                    from database.calendariodatabase import Database
                    
                    # Importação customizada
                    with open("Principal/Calendário.py", "r", encoding="utf-8") as f:
                        cal_code = f.read()
                    # Remover chamadas a set_page_config
                    cal_code = "\n".join([line for line in cal_code.split("\n") 
                                         if "set_page_config" not in line])
                    # Executar código modificado
                    exec(cal_code, globals())
                except Exception as e:
                    st.error(f"Erro ao carregar página Calendário: {str(e)}")
                    st.info("Verifique se a pasta 'database' existe com o arquivo calendariodatabase.py.")
                
            elif menu == "Dashboard Jira":
                # Importação customizada
                with open("Dashboard/Dash Jira.py", "r", encoding="utf-8") as f:
                    dash_code = f.read()
                # Remover chamadas a set_page_config
                dash_code = "\n".join([line for line in dash_code.split("\n") 
                                      if "set_page_config" not in line])
                # Executar código modificado
                exec(dash_code, globals())
                
            elif menu == "Projetos IA":
                try:
                    # Importação customizada
                    with open("Dashboard/ia.py", "r", encoding="utf-8") as f:
                        ia_code = f.read()
                    # Remover chamadas a set_page_config
                    ia_code = "\n".join([line for line in ia_code.split("\n") 
                                        if "set_page_config" not in line])
                    # Executar código modificado
                    exec(ia_code, globals())
                except FileNotFoundError:
                    st.title("Projetos de IA")
                    st.info("Módulo de Projetos de IA em desenvolvimento")
                
        else:
            # Menu para usuários comuns (acesso limitado)
            st.sidebar.title("🏢 Grupo Chegou")
            st.sidebar.markdown("### Navegação")
            
            menu = st.sidebar.radio(
                "Selecione uma página:",
                ["Home", "Calendário", "Dashboard Jira"],  # Sem acesso a Projetos IA
                label_visibility="collapsed"
            )
            
            # Exibe botão de logout
            show_logout_button()
            
            # Carrega a página selecionada evitando set_page_config
            if menu == "Home":
                # Importação customizada
                with open("Principal/Home.py", "r", encoding="utf-8") as f:
                    home_code = f.read()
                # Remover chamadas a set_page_config
                home_code = "\n".join([line for line in home_code.split("\n") 
                                     if "set_page_config" not in line])
                # Executar código modificado
                exec(home_code, globals())
                
            elif menu == "Calendário":
                try:
                    # Configurar conexão com banco antes de importar
                    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                    from database.calendariodatabase import Database
                    
                    # Importação customizada
                    with open("Principal/Calendário.py", "r", encoding="utf-8") as f:
                        cal_code = f.read()
                    # Remover chamadas a set_page_config
                    cal_code = "\n".join([line for line in cal_code.split("\n") 
                                         if "set_page_config" not in line])
                    # Executar código modificado
                    exec(cal_code, globals())
                except Exception as e:
                    st.error(f"Erro ao carregar página Calendário: {str(e)}")
                    st.info("Verifique se a pasta 'database' existe com o arquivo calendariodatabase.py.")
                
            elif menu == "Dashboard Jira":
                # Importação customizada
                with open("Dashboard/Dash Jira.py", "r", encoding="utf-8") as f:
                    dash_code = f.read()
                # Remover chamadas a set_page_config
                dash_code = "\n".join([line for line in dash_code.split("\n") 
                                      if "set_page_config" not in line])
                # Executar código modificado
                exec(dash_code, globals())

if __name__ == "__main__":
    main()