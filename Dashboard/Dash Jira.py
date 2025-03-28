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
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        text-align: center;
    }
    .data-table {
        background-color: #f8f9fa;
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
    .insights-container {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .insight-card {
        background-color: #f1f3f5;
        padding: 12px;
        border-radius: 6px;
        margin-bottom: 10px;
        border-left: 4px solid #4682B4;
    }
    
    /* Fix para barras brancas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f8f9fa;
        border-radius: 4px 4px 0 0;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    
    /* Removendo barras brancas dos Filtros Adicionais (selectbox) */
    div[data-baseweb="select"] div {
        background-color: transparent;
        border: none;
    }
    
    div[data-baseweb="select"] {
        margin-top: 0 !important;
    }
    
    div[data-baseweb="base-input"] {
        background-color: transparent;
        border-radius: 4px;
    }
    
    /* Remove espaços em branco acima dos selectbox */
    div[role="listbox"] {
        margin-top: 0;
    }
    
    /* Remove barras e espaços em componentes de seleção */
    div[data-testid="stSelectbox"] {
        margin-top: 0;
    }
    
    div[data-testid="stSelectbox"] > div:first-child {
        border: none;
        background: none;
    }
    
    /* Reduzir espaço vertical */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    
    /* Correção para espaços entre elementos */
    div[data-testid="stVerticalBlock"] > div {
        padding-bottom: 0.5rem;
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
def buscar_dados_jira(url, email, token, project_key, data_inicio=None, data_fim=None):
    """Busca dados de tarefas do Jira com um JQL específico e datas personalizadas"""
    try:
        auth = (email, token)

        # Configurar JQL com datas personalizadas ou usar padrão
        if data_inicio and data_fim:
            data_inicio_str = data_inicio.strftime("%Y-%m-%d")
            data_fim_str = data_fim.strftime("%Y-%m-%d")
            jql = f'project = "{project_key}" AND created >= "{data_inicio_str}" AND created <= "{data_fim_str}" ORDER BY created DESC'
        else:
            # Padrão: últimos 30 dias
            data_inicio_padrao = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            jql = f'project = "{project_key}" AND created >= "{data_inicio_padrao}" ORDER BY created DESC'

        # Implementação de paginação para buscar até 500 tarefas
        start_at = 0
        max_per_page = 100  # API Jira geralmente limita a 100 itens por página
        max_results = 500  # Limitar a 500 tarefas no total
        
        all_issues = []
        total_fetched = 0
        
        while total_fetched < max_results:
            # Parâmetros para a consulta
            params = {
                'jql': jql,
                'maxResults': max_per_page,
                'startAt': start_at,
                'fields': 'summary,status,assignee,duedate,created,updated,priority,timetracking,worklog'
            }

            response = requests.get(
                f"{url}/rest/api/3/search",
                params=params,
                auth=auth
            )

            if response.status_code != 200:
                return False, f"Erro: {response.status_code} - {response.text}"
            
            data = response.json()
            issues = data.get('issues', [])
            
            # Se não há mais resultados, sair do loop
            if not issues:
                break
                
            all_issues.extend(issues)
            total_fetched += len(issues)
            
            # Se já buscamos todos os resultados disponíveis, sair do loop
            total_issues = data.get('total', 0)
            if start_at + len(issues) >= total_issues or len(issues) < max_per_page:
                break
                
            # Avançar para a próxima página
            start_at += len(issues)
        
        # Montar a resposta final no mesmo formato esperado pelo código existente
        final_response = {
            'issues': all_issues,
            'total': total_fetched
        }
        
        return True, final_response
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

        # Tempo estimado e gasto (em segundos)
        original_estimate = issue.get('fields', {}).get('timetracking', {}).get('originalEstimateSeconds', 0) or 0
        time_spent = issue.get('fields', {}).get('timetracking', {}).get('timeSpentSeconds', 0) or 0

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
            'Prioridade': priority,
            'Tempo Estimado (h)': round(original_estimate / 3600, 1) if original_estimate else 0,
            'Tempo Gasto (h)': round(time_spent / 3600, 1) if time_spent else 0
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
            'proximas_vencer': 0,
            'tempo_total_gasto': 0,
            'tempo_medio_tarefa': 0
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

    # Calcular tempo total gasto e tempo médio por tarefa
    tempo_total_gasto = df['Tempo Gasto (h)'].sum()
    tempo_medio_tarefa = df['Tempo Gasto (h)'].mean() if df.shape[0] > 0 else 0

    return {
        'total_tarefas': df.shape[0],
        'concluidas': concluidas,
        'andamento': andamento,
        'atrasadas': atrasadas,
        'percentual_prazo': percentual_prazo,
        'media_dias_conclusao': media_dias,
        'proximas_vencer': proximas_vencer,
        'tempo_total_gasto': tempo_total_gasto,
        'tempo_medio_tarefa': tempo_medio_tarefa
    }

def gerar_insights(df, periodo='semana'):
    """Gera insights a partir dos dados para um determinado período"""
    if df.empty:
        return []

    insights = []

    # Filtrar pelo período
    hoje = datetime.now().date()
    if periodo == 'semana':
        inicio_periodo = hoje - timedelta(days=hoje.weekday())  # Segunda-feira da semana atual
        nome_periodo = "semana"
    else:  # mês
        inicio_periodo = hoje.replace(day=1)  # Primeiro dia do mês atual
        nome_periodo = "mês"

    df_periodo = df[df['Atualizada'] >= pd.Timestamp(inicio_periodo)]

    # Análise por responsável
    responsaveis = df_periodo['Responsável'].dropna().unique()

    for responsavel in responsaveis:
        df_resp = df_periodo[df_periodo['Responsável'] == responsavel]

        # Tarefas concluídas
        concluidas = df_resp[df_resp['Status'].isin(['Done', 'Concluído'])]
        n_concluidas = concluidas.shape[0]

        if n_concluidas > 0:
            tempo_gasto = concluidas['Tempo Gasto (h)'].sum()
            insights.append(
                f"{responsavel} concluiu {n_concluidas} tarefas nesta {nome_periodo}, " +
                f"gastando um total de {tempo_gasto:.1f}h ({(tempo_gasto/n_concluidas):.1f}h por tarefa)."
            )

        # Tarefas em andamento
        em_andamento = df_resp[df_resp['Status'].isin(['In Progress', 'Em andamento'])]
        n_andamento = em_andamento.shape[0]

        if n_andamento > 0:
            insights.append(
                f"{responsavel} está trabalhando em {n_andamento} tarefas atualmente."
            )

        # Tarefas atrasadas
        atrasadas = df_resp[df_resp['Atrasada'] == True]
        n_atrasadas = atrasadas.shape[0]

        if n_atrasadas > 0:
            insights.append(
                f"{responsavel} tem {n_atrasadas} tarefas atrasadas que precisam de atenção."
            )

    # Insights gerais
    tempo_total = df_periodo['Tempo Gasto (h)'].sum()
    if not df_periodo.empty:
        insights.append(
            f"No total, a equipe gastou {tempo_total:.1f}h trabalhando em tarefas nesta {nome_periodo}."
        )

    # Tarefas que mudaram de prazo
    df_com_mudanca = df_periodo[df_periodo['Prazo'].notna()]
    tarefas_com_mudanca = 0

    # Aqui precisaria de dados históricos para detectar mudanças de prazo
    # Como simplificação, podemos apenas contar tarefas atualizadas recentemente

    return insights

def gerar_grafico_status(df):
    """Gera um gráfico de barras por status com cores personalizadas"""
    if df.empty:
        return None

    # Contar tarefas por status
    status_counts = df['Status'].value_counts().reset_index()
    status_counts.columns = ['Status', 'Quantidade']

    # Definir ordem personalizada de status (adicionar mais status se necessário)
    status_ordem = ['To Do', 'A Fazer', 'Backlog', 'In Progress', 'Em andamento', 'Em Andamento', 'Review', 'In Review', 'Done', 'Concluído']

    # Adiciona status não reconhecidos
    outros_status = [s for s in status_counts['Status'] if s not in status_ordem]
    status_ordem.extend(outros_status)

    # Esquema de cores melhorado
    status_cores = {
        'To Do': '#1E88E5',       # Azul
        'A Fazer': '#1E88E5',     # Azul
        'Backlog': '#64B5F6',     # Azul claro
        'In Progress': '#FFA726',  # Laranja
        'Em andamento': '#FFA726', # Laranja
        'Em Andamento': '#FFA726', # Laranja
        'Review': '#FFCC80',      # Laranja claro
        'In Review': '#FFCC80',   # Laranja claro
        'Done': '#66BB6A',        # Verde
        'Concluído': '#66BB6A'    # Verde
    }

    # Definir cor padrão para outros status
    cor_padrao = '#9E9E9E'  # Cinza

    # Criar lista de cores na ordem correta
    cores = [status_cores.get(s, cor_padrao) for s in status_counts['Status']]

    # Criar o gráfico com Altair
    chart = alt.Chart(status_counts).mark_bar(
        cornerRadiusTopLeft=4,
        cornerRadiusTopRight=4
    ).encode(
        x=alt.X('Status:N', sort=status_ordem, title='Status'),
        y=alt.Y('Quantidade:Q', title='Quantidade de Tarefas'),
        color=alt.Color('Status:N', scale=alt.Scale(domain=list(status_counts['Status']), range=cores), legend=None),
        tooltip=['Status', 'Quantidade']
    ).properties(
        title='Tarefas por Status',
        width=600,
        height=400
    ).configure_axis(
        labelFontSize=12,
        titleFontSize=14
    ).configure_title(
        fontSize=16,
        font='Arial',
        anchor='start',
        color='#333333'
    )

    return chart

def gerar_grafico_prioridades(df):
    """Gera um gráfico de pizza para prioridades"""
    if df.empty:
        return None

    # Contar tarefas por prioridade
    prioridade_counts = df['Prioridade'].value_counts().reset_index()
    prioridade_counts.columns = ['Prioridade', 'Quantidade']

    # Cores para prioridades
    cores_prioridades = {
        'Highest': '#D50000',     # Vermelho escuro
        'High': '#FF5252',        # Vermelho
        'Medium': '#FFC107',      # Amarelo
        'Low': '#81C784',         # Verde claro
        'Lowest': '#4CAF50',      # Verde
        # Versões em português
        'Altíssima': '#D50000',   # Vermelho escuro
        'Alta': '#FF5252',        # Vermelho
        'Média': '#FFC107',       # Amarelo
        'Baixa': '#81C784',       # Verde claro
        'Baixíssima': '#4CAF50'   # Verde
    }

    # Cor padrão para outras prioridades
    cor_padrao = '#9E9E9E'  # Cinza

    # Criar lista de cores
    cores = [cores_prioridades.get(p, cor_padrao) for p in prioridade_counts['Prioridade']]

    # Criar o gráfico com Altair
    chart = alt.Chart(prioridade_counts).mark_arc(innerRadius=50).encode(
        theta=alt.Theta(field="Quantidade", type="quantitative"),
        color=alt.Color('Prioridade:N', scale=alt.Scale(domain=list(prioridade_counts['Prioridade']), range=cores)),
        tooltip=['Prioridade', 'Quantidade']
    ).properties(
        title='Distribuição por Prioridade',
        width=400,
        height=400
    ).configure_view(
        strokeOpacity=0
    ).configure_title(
        fontSize=16,
        font='Arial',
        anchor='middle',
        color='#333333'
    )

    return chart

def gerar_grafico_responsaveis(df):
    """Gera um gráfico de barras horizontal para responsáveis"""
    if df.empty or df['Responsável'].nunique() <= 1:
        return None

    # Contar tarefas por responsável
    resp_counts = df['Responsável'].value_counts().reset_index()
    resp_counts.columns = ['Responsável', 'Quantidade']
    
    # Limitar a 10 responsáveis mais ativos
    if len(resp_counts) > 10:
        resp_counts = resp_counts.head(10)

    # Gerar cores diferentes para cada responsável
    n_cores = len(resp_counts)
    import colorsys
    
    cores = []
    for i in range(n_cores):
        # Gerar cores HSL espaçadas uniformemente no espectro
        h = i / n_cores
        s = 0.7  # Saturação fixa
        l = 0.6  # Luminosidade fixa
        
        # Converter HSL para RGB
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        
        # Converter RGB para hex
        cor_hex = "#{:02x}{:02x}{:02x}".format(int(r*255), int(g*255), int(b*255))
        cores.append(cor_hex)

    # Criar o gráfico com Altair
    chart = alt.Chart(resp_counts).mark_bar(
        cornerRadiusEnd=4
    ).encode(
        y=alt.Y('Responsável:N', sort='-x', title='Responsável'),
        x=alt.X('Quantidade:Q', title='Quantidade de Tarefas'),
        color=alt.Color('Responsável:N', scale=alt.Scale(domain=list(resp_counts['Responsável']), range=cores), legend=None),
        tooltip=['Responsável', 'Quantidade']
    ).properties(
        title='Tarefas por Responsável',
        width=600,
        height=400
    ).configure_axis(
        labelFontSize=12,
        titleFontSize=14
    ).configure_title(
        fontSize=16,
        font='Arial',
        anchor='start',
        color='#333333'
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
        filename = f'dadosjira{datetime.now().strftime("%Y%m%d")}.csv'
    else:  # excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Dados Jira')
        excel_data = output.getvalue()
        b64 = base64.b64encode(excel_data).decode()
        href = f'data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}'
        filename = f'dadosjira{datetime.now().strftime("%Y%m%d")}.xlsx'

    return href, filename

# ======= INTERFACE DA APLICAÇÃO =======

def pagina_configuracao():
    """Mostra a página de configuração do Jira"""
    st.subheader("Configurar Conexão com Jira")

    with st.form("config_jira_form"):
        st.markdown("Conexão com o Jira")
        jira_url = st.text_input("URL do Jira (ex: https://seu-dominio.atlassian.net)", 
                                value=st.session_state.get('jira_url', ''))
        jira_email = st.text_input("Email", value=st.session_state.get('jira_email', ''))
        jira_token = st.text_input("Token API", type="password", 
                                 value=st.session_state.get('jira_token', ''))

        st.markdown("Configurações de Projeto")
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
    df_original = st.session_state.jira_df.copy()

    # Inicializar filtros na sessão se não existirem
    if 'filtro_responsavel' not in st.session_state:
        st.session_state.filtro_responsavel = "Todos"
    if 'filtro_status' not in st.session_state:
        st.session_state.filtro_status = "Todos"
        
    # Função para atualizar filtros
    def atualizar_filtro_responsavel():
        st.session_state.filtro_responsavel = st.session_state.novo_filtro_responsavel
        
    def atualizar_filtro_status():
        st.session_state.filtro_status = st.session_state.novo_filtro_status

    # Seletor de período personalizado
    st.markdown("### Filtros de Data")
    col1, col2 = st.columns(2)

    with col1:
        if 'data_inicio' not in st.session_state:
            st.session_state.data_inicio = datetime.now().date() - timedelta(days=30)
        
        data_inicio = st.date_input(
            "Data de Início",
            value=st.session_state.data_inicio,
            max_value=datetime.now().date(),
            key="input_data_inicio"
        )
        st.session_state.data_inicio = data_inicio

    with col2:
        if 'data_fim' not in st.session_state:
            st.session_state.data_fim = datetime.now().date()
            
        data_fim = st.date_input(
            "Data de Fim",
            value=st.session_state.data_fim,
            max_value=datetime.now().date(),
            key="input_data_fim"
        )
        st.session_state.data_fim = data_fim

    # Botão para atualizar dados com filtro de data
    if st.button("Atualizar dados com filtro de data"):
        if data_inicio and data_fim:
            if data_inicio > data_fim:
                st.error("A data de início não pode ser posterior à data de fim.")
            else:
                with st.spinner("Buscando dados com filtro de data..."):
                    sucesso, dados_jira = buscar_dados_jira(
                        st.session_state.jira_url, 
                        st.session_state.jira_email, 
                        st.session_state.jira_token, 
                        st.session_state.jira_project,
                        data_inicio=data_inicio,
                        data_fim=data_fim
                    )

                    if sucesso:
                        st.session_state.jira_dados = dados_jira
                        st.session_state.jira_df = processar_dados_jira(dados_jira)
                        st.success(f"Dados atualizados com sucesso! {len(st.session_state.jira_df)} tarefas encontradas.")
                        # Atualizar a referência ao DataFrame
                        df_original = st.session_state.jira_df.copy()
                    else:
                        st.error(f"Erro ao buscar dados filtrados: {dados_jira}")

    # Filtros adicionais
    st.markdown("### Filtros Adicionais")
    col1, col2 = st.columns(2)

    with col1:
        responsaveis = ["Todos"] + sorted(df_original['Responsável'].unique().tolist())
        st.selectbox(
            "Responsável", 
            responsaveis, 
            key="novo_filtro_responsavel",
            on_change=atualizar_filtro_responsavel,
            index=responsaveis.index(st.session_state.filtro_responsavel) if st.session_state.filtro_responsavel in responsaveis else 0
        )

    with col2:
        status_filtro = ["Todos"] + sorted(df_original['Status'].unique().tolist())
        st.selectbox(
            "Status", 
            status_filtro, 
            key="novo_filtro_status",
            on_change=atualizar_filtro_status,
            index=status_filtro.index(st.session_state.filtro_status) if st.session_state.filtro_status in status_filtro else 0
        )

    # Filtrar os dados conforme seleção
    df_filtrado = df_original.copy()

    # Filtro de responsável
    if st.session_state.filtro_responsavel != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Responsável'] == st.session_state.filtro_responsavel]

    # Filtro de status
    if st.session_state.filtro_status != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Status'] == st.session_state.filtro_status]

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
    st.markdown("### Análise Visual")
    
    # Layout de gráficos em tabs
    tab1, tab2, tab3 = st.tabs(["Status", "Prioridades", "Responsáveis"])
    
    with tab1:
        chart_status = gerar_grafico_status(df_filtrado)
        if chart_status:
            st.altair_chart(chart_status, use_container_width=True)
        else:
            st.info("Dados insuficientes para gerar o gráfico de status")
    
    with tab2:
        chart_prioridades = gerar_grafico_prioridades(df_filtrado)
        if chart_prioridades:
            st.altair_chart(chart_prioridades, use_container_width=True)
        else:
            st.info("Dados insuficientes para gerar o gráfico de prioridades")
    
    with tab3:
        chart_responsaveis = gerar_grafico_responsaveis(df_filtrado)
        if chart_responsaveis:
            st.altair_chart(chart_responsaveis, use_container_width=True)
        else:
            st.info("Dados insuficientes para gerar o gráfico de responsáveis")

    # Seção de insights
    st.markdown("### Insights de Produtividade")

    tab1, tab2 = st.tabs(["Insights da Semana", "Insights do Mês"])

    with tab1:
        insights_semana = gerar_insights(df_filtrado, 'semana')
        if insights_semana:
            st.markdown("<div class='insights-container'>", unsafe_allow_html=True)
            for insight in insights_semana:
                st.markdown(f"<div class='insight-card'>{insight}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("Não há insights disponíveis para a semana atual com os filtros aplicados.")

    with tab2:
        insights_mes = gerar_insights(df_filtrado, 'mes')
        if insights_mes:
            st.markdown("<div class='insights-container'>", unsafe_allow_html=True)
            for insight in insights_mes:
                st.markdown(f"<div class='insight-card'>{insight}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("Não há insights disponíveis para o mês atual com os filtros aplicados.")

    # Alertas para tarefas próximas do vencimento
    if metricas['proximas_vencer'] > 0:
        st.markdown("<div class='alert'>", unsafe_allow_html=True)
        st.warning(f"Atenção: {metricas['proximas_vencer']} tarefas com prazo para vencer nos próximos 7 dias")

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
                for key in ['jira_url', 'jira_email', 'jira_token', 'jira_project', 'jira_conectado', 'jira_dados', 'jira_df', 'filtro_responsavel', 'filtro_status', 'data_inicio', 'data_fim']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.success("Configurações removidas com sucesso!")
                st.rerun()

if __name__ == "__main__":
    main()