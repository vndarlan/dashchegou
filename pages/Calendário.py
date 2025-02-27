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
    .custom-tabs {
        display: flex;
        gap: 10px;
        margin-bottom: 20px;
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

# ======= PÁGINAS DA APLICAÇÃO =======

def pagina_visualizar():
    st.header("Visualização de Calendários")
    
    if not st.session_state.calendarios:
        st.warning("Nenhum calendário cadastrado. Vá para a página de gerenciamento para adicionar calendários.")
        return
    
    # Criando uma lista de nomes para selecionar
    nomes = [cal["nome"] for cal in st.session_state.calendarios]
    
    # Seleção de calendário para visualizar pelo nome
    nome_selecionado = st.selectbox(
        "Selecione um calendário para visualizar:",
        nomes
    )
    
    # Encontrar o email correspondente ao nome selecionado
    email_selecionado = next(
        (cal["email"] for cal in st.session_state.calendarios if cal["nome"] == nome_selecionado),
        None
    )
    
    if email_selecionado:
        # Exibir o calendário usando iframe
        exibir_iframe_calendario(email_selecionado)
    
    # Opção para visualizar todos os calendários juntos (modo de grupo)
    if st.checkbox("Visualizar todos os calendários juntos"):
        todos_emails = [cal["email"].replace("@", "%40") for cal in st.session_state.calendarios]
        calendarios_encoded = ",".join(todos_emails)
        iframe_todos = f"""
        <div class="calendar-container">
            <iframe src="https://calendar.google.com/calendar/embed?src={calendarios_encoded}&ctz=America%2FSao_Paulo" 
                    style="border: 0" width="100%" height="600" frameborder="0" scrolling="no"></iframe>
        </div>
        """
        html(iframe_todos, height=650)

def pagina_gerenciar():
    st.header("Gerenciar Calendários")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Form para adicionar novo calendário
        st.markdown('<div class="email-form">', unsafe_allow_html=True)
        st.subheader("Adicionar Novo Calendário")
        
        novo_nome = st.text_input("Nome da pessoa ou departamento:")
        novo_email = st.text_input("Email do calendário:")
        
        adicionar = st.button("Adicionar Calendário")
        st.markdown('</div>', unsafe_allow_html=True)
        
        if adicionar:
            if novo_nome and novo_email:
                # Verificar se o email já existe
                email_existente = any(cal["email"] == novo_email for cal in st.session_state.calendarios)
                
                if not email_existente:
                    st.session_state.calendarios.append({
                        "nome": novo_nome,
                        "email": novo_email
                    })
                    st.success(f"Calendário de {novo_nome} adicionado com sucesso!")
                    st.rerun()
                else:
                    st.error("Este email já está cadastrado!")
            else:
                st.error("Por favor, preencha todos os campos!")
    
    with col2:
        # Lista de calendários adicionados
        st.markdown('<div class="email-list">', unsafe_allow_html=True)
        st.subheader("Calendários Cadastrados")
        
        if not st.session_state.calendarios:
            st.info("Nenhum calendário cadastrado ainda.")
        else:
            for i, cal in enumerate(st.session_state.calendarios):
                st.markdown(f'<div class="email-item">', unsafe_allow_html=True)
                col_a, col_b = st.columns([3, 1])
                col_a.write(f"**{cal['nome']}**  \n{cal['email']}")
                if col_b.button("Remover", key=f"remove_{i}"):
                    st.session_state.calendarios.pop(i)
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

# ======= INTERFACE STREAMLIT PRINCIPAL =======

def main():
    st.title("📅 Calendários da Empresa")
    
    # Inicializa estado da sessão para armazenar dados dos calendários
    if 'calendarios' not in st.session_state:
        # Novo formato: lista de dicionários com nome e email
        st.session_state.calendarios = [
            {"nome": "Calendário Operacional", "email": "viniciuschegouoperacional@gmail.com"}
        ]
    
    # Inicializa o estado para controlar a subpágina atual
    if 'subpagina' not in st.session_state:
        st.session_state.subpagina = "visualizar"
    
    # Navegação entre subpáginas usando abas do Streamlit
    tab1, tab2 = st.tabs(["📊 Visualizar Calendários", "⚙️ Gerenciar Calendários"])
    
    with tab1:
        if st.session_state.subpagina != "visualizar":
            st.session_state.subpagina = "visualizar"
        pagina_visualizar()
    
    with tab2:
        if st.session_state.subpagina != "gerenciar":
            st.session_state.subpagina = "gerenciar"
        pagina_gerenciar()


if __name__ == "__main__":
    main()
