import streamlit as st
from datetime import datetime
from streamlit.components.v1 import html
import os
import sys

# Adiciona o diretório raiz ao path para importar arquivos de outros diretórios
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importa o módulo de banco de dados
try:
    from database.calendariodatabase import Database
except ImportError:
    # Se o arquivo não estiver disponível, mostra um erro
    st.error("Não foi possível importar o módulo de banco de dados. Verifique se a pasta 'database' existe com o arquivo calendariodatabase.py.")

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
    
    # Atualiza a lista de calendários (para garantir que estamos com os dados mais recentes)
    if hasattr(st.session_state, 'db') and st.session_state.db.conn:
        st.session_state.calendarios = st.session_state.db.get_all_calendarios()
    
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
    
    # Criando duas seções lado a lado sem espaços vazios
    col_left, col_right = st.columns([2, 1], gap="small")
    
    with col_left:
        # Form para adicionar novo calendário
        st.markdown('<div class="email-form">', unsafe_allow_html=True)
        st.subheader("Adicionar Novo Calendário")
        
        novo_nome = st.text_input("Nome da pessoa ou departamento:")
        novo_email = st.text_input("Email do calendário:")
        
        adicionar = st.button("Adicionar Calendário")
        st.markdown('</div>', unsafe_allow_html=True)
        
        if adicionar:
            if novo_nome and novo_email:
                # Usar banco de dados se estiver conectado, caso contrário modo local
                if hasattr(st.session_state, 'db') and st.session_state.db.conn:
                    result = st.session_state.db.add_calendario(novo_nome, novo_email)
                    
                    if result > 0:
                        # Atualizar a lista de calendários da sessão
                        st.session_state.calendarios = st.session_state.db.get_all_calendarios()
                        st.success(f"Calendário de {novo_nome} adicionado com sucesso!")
                        st.rerun()
                    elif result == -1:
                        st.error("Este email já está cadastrado!")
                    else:
                        st.error("Erro ao adicionar calendário. Tente novamente.")
                else:
                    # Modo local (memória)
                    # Verificar se o email já existe
                    email_existente = any(cal["email"] == novo_email for cal in st.session_state.calendarios)
                    
                    if not email_existente:
                        # Gerar ID localmente
                        new_id = max([cal.get("id", 0) for cal in st.session_state.calendarios], default=0) + 1
                        
                        st.session_state.calendarios.append({
                            "id": new_id,
                            "nome": novo_nome,
                            "email": novo_email
                        })
                        st.success(f"Calendário de {novo_nome} adicionado com sucesso!")
                        st.rerun()
                    else:
                        st.error("Este email já está cadastrado!")
            else:
                st.error("Por favor, preencha todos os campos!")
    
    with col_right:
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
                    # Usar banco de dados se estiver conectado
                    if hasattr(st.session_state, 'db') and st.session_state.db.conn:
                        # Remover do banco de dados
                        if st.session_state.db.remove_calendario(cal["id"]):
                            # Atualizar a lista de calendários
                            st.session_state.calendarios = st.session_state.db.get_all_calendarios()
                            st.success(f"Calendário de {cal['nome']} removido com sucesso!")
                        else:
                            st.error("Erro ao remover calendário.")
                    else:
                        # Modo local (memória)
                        st.session_state.calendarios.pop(i)
                    
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

# ======= INTERFACE STREAMLIT PRINCIPAL =======

def main():
    st.title("📅 Calendários da Empresa")
    
    # Inicializa a conexão com o banco de dados
    if 'db' not in st.session_state:
        st.session_state.db = Database()
        db_connected = st.session_state.db.connect()
        
        # Se não conseguir conectar ao banco, usamos o modo local (na memória)
        if not db_connected:
            st.warning("Usando modo local (os dados não serão persistidos no banco de dados)")
            
            # Inicializa estado da sessão para armazenar dados dos calendários localmente
            if 'calendarios' not in st.session_state:
                st.session_state.calendarios = [
                    {"id": 1, "nome": "Calendário Operacional", "email": "viniciuschegouoperacional@gmail.com"}
                ]
        else:
            # Carrega os calendários do banco de dados
            st.session_state.calendarios = st.session_state.db.get_all_calendarios()
            
            # Se não houver calendários, adiciona um padrão
            if not st.session_state.calendarios:
                st.session_state.db.add_calendario(
                    "Calendário Operacional", 
                    "viniciuschegouoperacional@gmail.com"
                )
                st.session_state.calendarios = st.session_state.db.get_all_calendarios()
    
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
