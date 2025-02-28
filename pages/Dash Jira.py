import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import os
import sys
import json
import requests
from io import BytesIO
import time
import base64

# Adiciona o diretório raiz ao path para importar arquivos de outros diretórios
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuração da página
st.set_page_config(
    page_title="Dashboard Jira - Dashboard da Empresa",
    page_icon="📊",
    layout="wide"
)

# Função para adicionar CSS personalizado
def local_css():
    st.markdown("""
    <style>
    .main {
        padding: 1rem;
    }
    .dashboard-container {
        margin-top: 20px;
        border-radius: 5px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        padding: 15px;
        background-color: white;
    }
    .stButton>button {
        width: 100%;
    }
    .metric-card {
        background-color: white;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        text-align: center;
    }
    .data-table {
        background-color: white;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .config-form {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        border: 1px solid #e9ecef;
    }
    .alert {
        color: #721c24;
        background-color: #f8d7da;
        padding: 10px;
        border-radius: 4px;
        margin-bottom: 15px;
    }
    .green-text {
        color: #28a745;
    }
    .yellow-text {
        color: #ffc107;
    }
    .red-text {
        color: #dc3545;
    }
    </style>
    """, unsafe_allow_html=True)

# Aplicar CSS
local_css()

# ======= FUNÇÕES DE UTILIDADE =======

@st.cache_data(ttl=3600)  # Cache por 1 hora
def conectar_jira(url, email, token):
    """Tenta conectar à API do Jira e retorna o status da conexão"""
    try:
        # Endpoint básico para testar a conexão
        auth = (email, token)
        response = requests.get(f"{url}/rest/api/3/myself", auth=auth)
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, f"Erro: {response.status_code} - {response.text}"
    except Exception as e:
        return False, f"Erro ao conectar ao Jira: {str(e)}"

@st.cache_data(ttl=300)  # Cache por 5 minutos
def buscar_dados_jira(url, email, token, project_key, dias_atras=30):
    """Busca dados de tarefas do Jira com um JQL específico"""
    try:
        auth = (email, token)
        data_inicio = (datetime.now() - timedelta(days=dias_atras)).strftime("%Y-%m-%d")
        
        # JQL query para buscar tarefas
        jql = f'project = "{project_key}" AND created >= "{data_inicio}" ORDER BY created DESC'
        
        # Parâmetros para a consulta
        params = {
            'jql': jql,
            'maxResults': 100,  # Ajuste conforme necessário
            'fields': 'summary,status,assignee,duedate,created,updated,priority'
        }
        
        response = requests.get(
            f"{url}/rest/api/3/search",
            params=params,
            auth=auth
        )
        
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, f"Erro: {response.status_code} - {response.text}"
    except Exception as e:
        return False, f"Erro ao buscar dados do Jira: {str(e)}"

def processar_dados_jira(dados_raw):
    """Processa os dados brutos do Jira e retorna um DataFrame"""
    if not dados_raw or 'issues' not in dados_raw:
        return pd.DataFrame()
    
    issues = dados_raw['issues']
    dados_processados = []
    
    for issue in issues:
        # Extrair dados básicos
        issue_id = issue.get('key', 'N/A')
        summary = issue.get('fields', {}).get('summary', 'Sem título')
        
        # Status
        status = issue.get('fields', {}).get('status', {}).get('name', 'Sem status')
        
        # Atribuído a
        assignee = "Não atribuído"
        if issue.get('fields', {}).get('assignee'):
            assignee = issue.get('fields', {}).get('assignee', {}).get('displayName', 'Não atribuído')
        
        # Datas
        created = issue.get('fields', {}).get('created', None)
        if created:
            created = datetime.strptime(created.split('T')[0], "%Y-%m-%d")
        
        updated = issue.get('fields', {}).get('updated', None)
        if updated:
            updated = datetime.strptime(updated.split('T')[0], "%Y-%m-%d")
        
        due_date = issue.get('fields', {}).get('duedate', None)
        if due_date:
            due_date = datetime.strptime(due_date, "%Y-%m-%d")
        
        # Cálculo de atraso
        hoje = datetime.now().date()
        is_atrasada = False
        dias_restantes = None
        
        if due_date:
            dias_restantes = (due_date.date() - hoje).days
            is_atrasada = dias_restantes < 0 and status != 'Done' and status != 'Concluído'
        
        # Prioridade
        priority = issue.get('fields', {}).get('priority', {}).get('name', 'Normal')
        
        # Adicionar ao dataset
        dados_processados.append({
            'ID': issue_id,
            'Resumo': summary,
            'Status': status,
            'Responsável': assignee,
            'Criada': created,
            'Atualizada': updated,
            'Prazo': due_date,
            'Dias Restantes': dias_restantes,
            'Atrasada': is_atrasada,
            'Prioridade': priority
        })
    
    return pd.DataFrame(dados_processados)

def calcular_metricas(df):
    """Calcula métricas a partir do DataFrame de tarefas"""
    if df.empty:
        return {
            'total_tarefas': 0,
            'concluidas': 0,
            'andamento': 0,
            'atrasadas': 0,
            'percentual_prazo': 0,
            'media_dias_conclusao': 0,
            'proximas_vencer': 0
        }
    
    # Identificar tarefas por status
    concluidas = df[df['Status'].isin(['Done', 'Concluído'])].shape[0]
    andamento = df[df['Status'].isin(['In Progress', 'Em andamento'])].shape[0]
    atrasadas = df[df['Atrasada'] == True].shape[0]
    
    # Calcular percentual de tarefas entregues no prazo
    tarefas_prazo = 0
    if concluidas > 0:
        df_concluidas = df[df['Status'].isin(['Done', 'Concluído'])]
        tarefas_prazo = df_concluidas[df_concluidas['Atrasada'] == False].shape[0]
        percentual_prazo = (tarefas_prazo / concluidas) * 100
    else:
        percentual_prazo = 0
    
    # Calcular média de dias para conclusão (se houver dados suficientes)
    media_dias = 0
    df_com_datas = df[df['Criada'].notna() & df['Atualizada'].notna() & df['Status'].isin(['Done', 'Concluído'])]
    if not df_com_datas.empty:
        df_com_datas['Dias_Conclusao'] = (df_com_datas['Atualizada'] - df_com_datas['Criada']).dt.days
        media_dias = df_com_datas['Dias_Conclusao'].mean()
    
    # Identificar tarefas próximas do vencimento (próximos 7 dias)
    proximas_vencer = df[(df['Dias Restantes'] >= 0) & (df['Dias Restantes'] <= 7) & 
                          ~df['Status'].isin(['Done', 'Concluído'])].shape[0]
    
    return {
        'total_tarefas': df.shape[0],
        'concluidas': concluidas,
        'andamento': andamento,
        'atrasadas': atrasadas,
        'percentual_prazo': percentual_prazo,
        'media_dias_conclusao': media_dias,
        'proximas_vencer': proximas_vencer
    }

def gerar_grafico_status(df):
    """Gera um gráfico de barras por status"""
    if df.empty:
        return None
    
    # Contar tarefas por status
    status_counts = df['Status'].value_counts().reset_index()
    status_counts.columns = ['Status', 'Quantidade']
    
    # Definir ordem personalizada de status
    status_ordem = ['To Do', 'A Fazer', 'In Progress', 'Em andamento', 'Done', 'Concluído']
    
    # Adiciona uma categoria para status não reconhecidos
    outros_status = [s for s in status_counts['Status'] if s not in status_ordem]
    status_ordem.extend(outros_status)
    
    # Mapear cores por status
    status_cores = {
        'To Do': '#1E88E5',       # Azul
        'A Fazer': '#1E88E5',     # Azul
        'In Progress': '#FFA726',  # Laranja
        'Em andamento': '#FFA726', # Laranja
        'Done': '#66BB6A',         # Verde
        'Concluído': '#66BB6A'     # Verde
    }
    
    # Definir cor padrão para outros status
    cor_padrao = '#9E9E9E'  # Cinza
    
    # Criar lista de cores na ordem correta
    cores = [status_cores.get(s, cor_padrao) for s in status_counts['Status']]
    
    # Criar o gráfico com Altair
    chart = alt.Chart(status_counts).mark_bar().encode(
        x=alt.X('Status:N', sort=status_ordem, title='Status'),
        y=alt.Y('Quantidade:Q', title='Quantidade de Tarefas'),
        color=alt.Color('Status:N', scale=alt.Scale(range=cores), legend=None),
        tooltip=['Status', 'Quantidade']
    ).properties(
        title='Tarefas por Status',
        width=600,
        height=400
    ).configure_axis(
        labelFontSize=12,
        titleFontSize=14
    )
    
    return chart

def gerar_grafico_tendencia(df, periodo='semana'):
    """Gera um gráfico de linha de tendência de conclusão de tarefas ao longo do tempo"""
    if df.empty or 'Atualizada' not in df.columns:
        return None
    
    # Filtrar apenas tarefas concluídas e com data de atualização
    df_concluidas = df[df['Status'].isin(['Done', 'Concluído']) & df['Atualizada'].notna()].copy()
    
    if df_concluidas.empty:
        return None
    
    # Agrupar por período
    if periodo == 'semana':
        df_concluidas['Periodo'] = df_concluidas['Atualizada'].dt.strftime('%Y-%U')
        periodo_format = 'Semana %U de %Y'
    elif periodo == 'mes':
        df_concluidas['Periodo'] = df_concluidas['Atualizada'].dt.strftime('%Y-%m')
        periodo_format = '%b %Y'
    else:  # trimestre
        df_concluidas['Periodo'] = df_concluidas['Atualizada'].dt.to_period('Q').astype(str)
        periodo_format = 'Q%q %Y'
    
    # Contar tarefas concluídas por período
    tendencia_data = df_concluidas.groupby('Periodo').size().reset_index()
    tendencia_data.columns = ['Periodo', 'Tarefas Concluídas']
    
    # Ordenar por período
    tendencia_data = tendencia_data.sort_values('Periodo')
    
    # Criar o gráfico com Altair
    chart = alt.Chart(tendencia_data).mark_line(point=True).encode(
        x=alt.X('Periodo:N', title='Período', sort=None),
        y=alt.Y('Tarefas Concluídas:Q', title='Tarefas Concluídas'),
        tooltip=['Periodo', 'Tarefas Concluídas']
    ).properties(
        title=f'Tendência de Conclusão de Tarefas por {periodo.capitalize()}',
        width=600,
        height=400
    ).configure_axis(
        labelFontSize=12,
        titleFontSize=14
    )
    
    return chart

def exportar_dataframe(df, formato='csv'):
    """Exporta o DataFrame para CSV ou Excel"""
    if df.empty:
        return None, None
    
    if formato == 'csv':
        csv = df.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        href = f'data:file/csv;base64,{b64}'
        filename = f'dados_jira_{datetime.now().strftime("%Y%m%d")}.csv'
    else:  # excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Dados Jira')
        excel_data = output.getvalue()
        b64 = base64.b64encode(excel_data).decode()
        href = f'data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}'
        filename = f'dados_jira_{datetime.now().strftime("%Y%m%d")}.xlsx'
    
    return href, filename

# ======= INTERFACE DA APLICAÇÃO =======

def pagina_configuracao():
    """Mostra a página de configuração do Jira"""
    st.subheader("Configurar Conexão com Jira")
    
    with st.form("config_jira_form"):
        st.markdown("**Conexão com o Jira**")
        jira_url = st.text_input("URL do Jira (ex: https://seu-dominio.atlassian.net)", 
                                value=st.session_state.get('jira_url', ''))
        jira_email = st.text_input("Email", value=st.session_state.get('jira_email', ''))
        jira_token = st.text_input("Token API", type="password", 
                                 value=st.session_state.get('jira_token', ''))
        
        st.markdown("**Configurações de Projeto**")
        jira_project = st.text_input("Chave do Projeto (ex: PROJ)", 
                                   value=st.session_state.get('jira_project', ''))
        
        st.info("O token API pode ser gerado em: Perfil > Configurações de Conta > Tokens de API")
        
        testar_btn = st.form_submit_button("Testar Conexão e Salvar")
    
    if testar_btn:
        if not jira_url or not jira_email or not jira_token or not jira_project:
            st.error("Preencha todos os campos para testar a conexão")
        else:
            # Teste de conexão
            with st.spinner("Testando conexão..."):
                sucesso, resultado = conectar_jira(jira_url, jira_email, jira_token)
            
            if sucesso:
                st.success(f"Conexão estabelecida com sucesso! Bem-vindo, {resultado.get('displayName', 'Usuário')}!")
                
                # Salvar configurações na session_state
                st.session_state.jira_url = jira_url
                st.session_state.jira_email = jira_email
                st.session_state.jira_token = jira_token
                st.session_state.jira_project = jira_project
                st.session_state.jira_conectado = True
                
                # Realizar busca inicial de dados
                with st.spinner("Buscando dados do projeto..."):
                    sucesso_busca, dados_jira = buscar_dados_jira(
                        jira_url, jira_email, jira_token, jira_project)
                
                if sucesso_busca:
                    st.session_state.jira_dados = dados_jira
                    st.session_state.jira_df = processar_dados_jira(dados_jira)
                    st.success(f"Dados carregados com sucesso! {len(st.session_state.jira_df)} tarefas encontradas.")
                else:
                    st.error(f"Erro ao buscar dados do projeto: {dados_jira}")
            else:
                st.error(f"Erro na conexão: {resultado}")

def pagina_dashboard():
    """Mostra o dashboard do Jira com os dados carregados"""
    st.subheader("Dashboard de Produtividade do Jira")
    
    # Verificar se temos dados carregados
    if 'jira_df' not in st.session_state or st.session_state.jira_df.empty:
        st.warning("Nenhum dado disponível. Por favor, configure a conexão com o Jira.")
        return
    
    # Obter dados do estado da sessão
    df = st.session_state.jira_df
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    
    with col1:
        periodo_filtro = st.selectbox(
            "Período de Análise",
            ["últimos 7 dias", "últimos 30 dias", "últimos 90 dias"],
            index=1
        )
    
    with col2:
        responsaveis = ["Todos"] + sorted(df['Responsável'].unique().tolist())
        responsavel_filtro = st.selectbox("Responsável", responsaveis)
    
    with col3:
        status_filtro = ["Todos"] + sorted(df['Status'].unique().tolist())
        status_selecionado = st.selectbox("Status", status_filtro)
    
    # Filtrar os dados conforme seleção
    df_filtrado = df.copy()
    
    # Filtro de período
    hoje = datetime.now().date()
    if periodo_filtro == "últimos 7 dias":
        data_limite = hoje - timedelta(days=7)
    elif periodo_filtro == "últimos 30 dias":
        data_limite = hoje - timedelta(days=30)
    else:  # últimos 90 dias
        data_limite = hoje - timedelta(days=90)
    
    df_filtrado = df_filtrado[df_filtrado['Criada'] >= pd.Timestamp(data_limite)]
    
    # Filtro de responsável
    if responsavel_filtro != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Responsável'] == responsavel_filtro]
    
    # Filtro de status
    if status_selecionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Status'] == status_selecionado]
    
    # Calcular métricas
    metricas = calcular_metricas(df_filtrado)
    
    # Mostrar métricas em cards
    st.markdown("<div class='dashboard-container'>", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        st.metric(
            "Total de Tarefas",
            metricas['total_tarefas'],
            delta=None
        )
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        st.metric(
            "Tarefas Concluídas",
            metricas['concluidas'],
            delta=f"{round((metricas['concluidas'] / metricas['total_tarefas']) * 100, 1)}%" if metricas['total_tarefas'] > 0 else None
        )
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col3:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        cor_class = "green-text" if metricas['percentual_prazo'] >= 80 else "yellow-text" if metricas['percentual_prazo'] >= 60 else "red-text"
        st.metric(
            "Entregues no Prazo",
            f"{round(metricas['percentual_prazo'], 1)}%",
        )
        st.markdown(f"<p class='{cor_class}'>Meta: 80%</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col4:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        st.metric(
            "Tarefas Atrasadas",
            metricas['atrasadas'],
            delta=f"{round((metricas['atrasadas'] / metricas['total_tarefas']) * 100, 1)}%" if metricas['total_tarefas'] > 0 else None,
            delta_color="inverse"
        )
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Gráficos
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("<div class='dashboard-container'>", unsafe_allow_html=True)
        chart_status = gerar_grafico_status(df_filtrado)
        if chart_status:
            st.altair_chart(chart_status, use_container_width=True)
        else:
            st.info("Dados insuficientes para gerar o gráfico de status")
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("<div class='dashboard-container'>", unsafe_allow_html=True)
        periodo_tendencia = "semana" if periodo_filtro == "últimos 7 dias" else "mes" if periodo_filtro == "últimos 30 dias" else "trimestre"
        chart_tendencia = gerar_grafico_tendencia(df_filtrado, periodo_tendencia)
        if chart_tendencia:
            st.altair_chart(chart_tendencia, use_container_width=True)
        else:
            st.info("Dados insuficientes para gerar o gráfico de tendência")
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Alertas para tarefas próximas do vencimento
    if metricas['proximas_vencer'] > 0:
        st.markdown("<div class='alert'>", unsafe_allow_html=True)
        st.warning(f"**Atenção:** {metricas['proximas_vencer']} tarefas com prazo para vencer nos próximos 7 dias")
        
        # Mostrar tarefas que estão próximas de vencer
        df_proximas = df_filtrado[(df_filtrado['Dias Restantes'] >= 0) & 
                                  (df_filtrado['Dias Restantes'] <= 7) & 
                                  ~df_filtrado['Status'].isin(['Done', 'Concluído'])]
        
        st.dataframe(
            df_proximas[['ID', 'Resumo', 'Responsável', 'Prazo', 'Dias Restantes']],
            hide_index=True,
            column_config={
                'Dias Restantes': st.column_config.NumberColumn(
                    'Dias Restantes',
                    help='Dias até o vencimento',
                    format='%d dias'
                )
            }
        )
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Tabela de tarefas atrasadas
    if metricas['atrasadas'] > 0:
        st.markdown("<div class='data-table'>", unsafe_allow_html=True)
        st.subheader("Tarefas Atrasadas")
        
        # Filtrar tarefas atrasadas
        df_atrasadas = df_filtrado[df_filtrado['Atrasada'] == True]
        
        st.dataframe(
            df_atrasadas[['ID', 'Resumo', 'Responsável', 'Prazo', 'Dias Restantes', 'Status']],
            hide_index=True,
            column_config={
                'Dias Restantes': st.column_config.NumberColumn(
                    'Dias Restantes',
                    help='Números negativos indicam dias de atraso',
                    format='%d dias'
                )
            }
        )
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Exportação de dados
    st.markdown("<div class='dashboard-container'>", unsafe_allow_html=True)
    st.subheader("Exportar Dados")
    formato = st.radio("Formato de exportação:", ["CSV", "Excel"], horizontal=True)
    
    if st.button("Exportar dados filtrados"):
        href, filename = exportar_dataframe(df_filtrado, formato.lower())
        if href:
            st.markdown(
                f'<a href="{href}" download="{filename}">Clique aqui para baixar o arquivo {formato}</a>',
                unsafe_allow_html=True
            )
        else:
            st.error("Não foi possível gerar o arquivo para exportação.")
    st.markdown("</div>", unsafe_allow_html=True)

# ======= FUNÇÃO PRINCIPAL =======

def main():
    st.title("📊 Dashboard Jira")
    
    # Inicializar estados da sessão se necessário
    if 'jira_conectado' not in st.session_state:
        st.session_state.jira_conectado = False
    
    # Usar abas do Streamlit para navegação
    tab1, tab2 = st.tabs(["📊 Dashboard", "⚙️ Configurações"])
    
    with tab1:
        pagina_dashboard()
    
    with tab2:
        pagina_configuracao()
        
        # Botão para limpar configurações
        if st.session_state.get('jira_conectado', False):
            if st.button("Limpar configurações"):
                for key in ['jira_url', 'jira_email', 'jira_token', 'jira_project', 'jira_conectado', 'jira_dados', 'jira_df']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.success("Configurações removidas com sucesso!")
                st.rerun()

if __name__ == "__main__":
    main()