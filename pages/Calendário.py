import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
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
    .calendar-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 20px;
        margin-top: 20px;
    }
    .calendar-item {
        background-color: white;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        padding: 15px;
    }
    .calendar-title {
        font-weight: bold;
        margin-bottom: 10px;
        color: #1E88E5;
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


def gerar_grafico_eventos_por_pessoa(dados_eventos):
    """Gera um gráfico de eventos por pessoa com dados simulados ou reais"""
    # Criar DataFrame para o gráfico
    df = pd.DataFrame({
        'Pessoa': list(dados_eventos.keys()),
        'Eventos': list(dados_eventos.values())
    })
    
    # Criar o gráfico com Altair
    chart = alt.Chart(df).mark_bar().encode(
        x='Pessoa',
        y='Eventos',
        color=alt.Color('Pessoa', scale=alt.Scale(scheme='category10'))
    ).properties(
        title='Eventos por Pessoa',
        width=600
    )
    
    return chart


# ======= INTERFACE STREAMLIT =======

def main():
    st.title("📅 Calendários da Empresa")
    
    # Sidebar para gerenciar calendários
    st.sidebar.title("Gerenciar Calendários")
    
    # Inicializa estado da sessão para armazenar emails dos calendários
    if 'calendarios' not in st.session_state:
        st.session_state.calendarios = ["viniciuschegouoperacional@gmail.com"]  # Calendário inicial
    
    # Adicionar novo calendário
    novo_calendario = st.sidebar.text_input("Adicionar novo calendário (email):")
    if st.sidebar.button("Adicionar"):
        if novo_calendario and novo_calendario not in st.session_state.calendarios:
            st.session_state.calendarios.append(novo_calendario)
            st.sidebar.success(f"Calendário {novo_calendario} adicionado!")
    
    # Lista de calendários adicionados
    st.sidebar.subheader("Calendários adicionados:")
    for i, cal in enumerate(st.session_state.calendarios):
        col1, col2 = st.sidebar.columns([3, 1])
        col1.write(f"{i+1}. {cal}")
        if col2.button("Remover", key=f"remove_{i}"):
            st.session_state.calendarios.pop(i)
            st.rerun()
    
    # Área principal
    tabs = st.tabs(["Visualização de Calendários", "Visão Geral", "Análise de Eventos"])
    
    with tabs[0]:
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
    
    with tabs[1]:
        st.header("Visão Geral dos Calendários")
        
        # Mostrar estatísticas básicas
        st.subheader("Estatísticas")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total de Calendários", len(st.session_state.calendarios))
        col2.metric("Próximos Dias", "30")
        col3.metric("Última Atualização", datetime.now().strftime("%d/%m/%Y %H:%M"))
        
        # Grid de mini-calendários
        st.subheader("Todos os Calendários")
        
        # Criar grid de calendários
        st.markdown('<div class="calendar-grid">', unsafe_allow_html=True)
        
        # Simula uma prévia de cada calendário
        for cal in st.session_state.calendarios:
            nome_exibicao = cal.split('@')[0]
            iframe_mini = f"""
            <div class="calendar-item">
                <div class="calendar-title">{nome_exibicao}</div>
                <iframe src="https://calendar.google.com/calendar/embed?src={cal}&ctz=America%2FSao_Paulo&mode=AGENDA" 
                        style="border: 0" width="100%" height="200" frameborder="0" scrolling="no"></iframe>
            </div>
            """
            st.markdown(iframe_mini, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tabs[2]:
        st.header("Análise de Eventos")
        
        # Como não temos mais autenticação, vamos usar dados simulados para a análise
        st.info("Esta seção mostra dados simulados para análise. Para dados reais, seria necessário implementar a API do Google Calendar.")
        
        # Dados simulados para análise
        dados_simulados = {}
        for cal in st.session_state.calendarios:
            nome = cal.split('@')[0]
            # Gera um número aleatório de eventos entre 5 e 15
            import random
            dados_simulados[nome] = random.randint(5, 15)
        
        # Mostrar gráficos e estatísticas
        if dados_simulados:
            # Gráfico de eventos por pessoa
            st.subheader("Quantidade de Eventos por Pessoa")
            chart = gerar_grafico_eventos_por_pessoa(dados_simulados)
            st.altair_chart(chart, use_container_width=True)
            
            # Timeline de eventos simulados
            st.subheader("Timeline de Próximos Eventos (Simulado)")
            
            # Gerar dados de exemplo para a timeline
            hoje = datetime.now()
            eventos_timeline = []
            
            for cal, num_eventos in dados_simulados.items():
                for i in range(num_eventos):
                    # Gera uma data aleatória nos próximos 30 dias
                    dias_aleatorios = random.randint(0, 30)
                    data_evento = hoje + timedelta(days=dias_aleatorios)
                    
                    eventos_timeline.append({
                        'Calendário': cal,
                        'Evento': f"Evento {i+1} de {cal}",
                        'Data': data_evento.strftime("%d/%m/%Y"),
                        'Hora': f"{random.randint(8, 17)}:{random.choice(['00', '15', '30', '45'])}"
                    })
            
            if eventos_timeline:
                df_timeline = pd.DataFrame(eventos_timeline)
                st.dataframe(df_timeline, use_container_width=True)


if __name__ == "__main__":
    main()