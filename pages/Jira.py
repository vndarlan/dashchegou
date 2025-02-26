import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import requests
from datetime import datetime, timedelta
import json
import plotly.express as px
import plotly.graph_objects as go
from requests.auth import HTTPBasicAuth
import time

# Configuração da página
st.set_page_config(
    page_title="Métricas Jira - Dashboard da Empresa",
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
    .metric-card {
        background-color: white;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        padding: 20px;
        text-align: center;
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        color: #3F51B5;
    }
    .metric-title {
        font-size: 1rem;
        color: #666;
    }
    .status-open {
        color: #F44336;
    }
    .status-progress {
        color: #FF9800;
    }
    .status-review {
        color: #2196F3;
    }
    .status-done {
        color: #4CAF50;
    }
    .highlight-box {
        background-color: #f0f7ff;
        border-left: 5px solid #3F51B5;
        padding: 20px;
        margin-bottom: 20px;
    }
    .filters-section {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# Aplicar CSS
local_css()

# ======= FUNÇÕES PARA API DO JIRA =======

def conectar_jira(url, email, token):
    """Testa a conexão com a API do Jira."""
    try:
        auth = HTTPBasicAuth(email, token)
        headers = {
            "Accept": "application/json"
        }
        
        response = requests.get(
            f"{url}/rest/api/3/myself",
            headers=headers,
            auth=auth
        )
        
        if response.status_code == 200:
            return True, auth, headers
        else:
            return False, None, None
    except Exception as e:
        return False, None, None

def buscar_projetos(url, auth, headers):
    """Busca a lista de projetos disponíveis."""
    try:
        response = requests.get(
            f"{url}/rest/api/3/project",
            headers=headers,
            auth=auth
        )
        
        if response.status_code == 200:
            projetos = response.json()
            return True, projetos
        else:
            return False, []
    except Exception as e:
        return False, []

def buscar_issues(url, auth, headers, jql, campos=None, max_results=100):
    """Busca issues com base em uma query JQL."""
    if campos is None:
        campos = ["summary", "status", "assignee", "priority", "created", "updated", "resolutiondate", "issuetype"]
        
    try:
        params = {
            "jql": jql,
            "maxResults": max_results,
            "fields": ",".join(campos)
        }
        
        response = requests.get(
            f"{url}/rest/api/3/search",
            headers=headers,
            params=params,
            auth=auth
        )
        
        if response.status_code == 200:
            dados = response.json()
            return True, dados
        else:
            st.error(f"Erro ao buscar issues: {response.status_code} - {response.text}")
            return False, {}
    except Exception as e:
        st.error(f"Exceção ao buscar issues: {str(e)}")
        return False, {}

def extrair_campos_issues(dados_issues):
    """Extrai campos das issues e formata em um DataFrame."""
    issues = []
    
    for issue in dados_issues.get("issues", []):
        campos = issue.get("fields", {})
        
        # Extrai informações básicas
        item = {
            "key": issue.get("key", ""),
            "id": issue.get("id", ""),
            "summary": campos.get("summary", ""),
            "status": campos.get("status", {}).get("name", "") if campos.get("status") else "",
            "tipo": campos.get("issuetype", {}).get("name", "") if campos.get("issuetype") else "",
            "prioridade": campos.get("priority", {}).get("name", "") if campos.get("priority") else "",
            "data_criacao": campos.get("created", ""),
            "data_atualizacao": campos.get("updated", ""),
            "data_resolucao": campos.get("resolutiondate", "")
        }
        
        # Adiciona o responsável se existir
        if campos.get("assignee"):
            item["responsavel"] = campos["assignee"].get("displayName", "")
            item["responsavel_email"] = campos["assignee"].get("emailAddress", "")
        else:
            item["responsavel"] = "Não atribuído"
            item["responsavel_email"] = ""
        
        issues.append(item)
    
    # Cria DataFrame
    if issues:
        df = pd.DataFrame(issues)
        
        # Converte datas para datetime
        for coluna in ["data_criacao", "data_atualizacao", "data_resolucao"]:
            if coluna in df.columns:
                df[coluna] = pd.to_datetime(df[coluna], errors="coerce")
                
        # Calcula tempo de resolução (em dias) onde aplicável
        if "data_criacao" in df.columns and "data_resolucao" in df.columns:
            df["tempo_resolucao"] = (df["data_resolucao"] - df["data_criacao"]).dt.total_seconds() / (3600 * 24)
        
        return df
    else:
        return pd.DataFrame()

def resumo_status(df):
    """Gera um resumo das issues por status."""
    if "status" in df.columns:
        return df["status"].value_counts().reset_index(name="contagem")
    return pd.DataFrame()

def resumo_responsaveis(df):
    """Gera um resumo das issues por responsável."""
    if "responsavel" in df.columns:
        return df["responsavel"].value_counts().reset_index(name="contagem")
    return pd.DataFrame()

def resumo_prioridade(df):
    """Gera um resumo das issues por prioridade."""
    if "prioridade" in df.columns:
        return df["prioridade"].value_counts().reset_index(name="contagem")
    return pd.DataFrame()

def tempo_medio_resolucao(df):
    """Calcula o tempo médio de resolução por status ou tipo."""
    if "tempo_resolucao" in df.columns and not df["tempo_resolucao"].isnull().all():
        return df.groupby("status")["tempo_resolucao"].mean().reset_index()
    return pd.DataFrame()

def issues_por_periodo(df, coluna_data="data_criacao", periodo="semana"):
    """Agrupa issues por período."""
    if coluna_data in df.columns:
        if periodo == "dia":
            df[periodo] = df[coluna_data].dt.date
        elif periodo == "semana":
            df[periodo] = df[coluna_data].dt.isocalendar().week
        elif periodo == "mes":
            df[periodo] = df[coluna_data].dt.month
        
        return df.groupby(periodo).size().reset_index(name="contagem")
    return pd.DataFrame()

# ======= VISUALIZAÇÕES E MÉTRICAS =======

def criar_card_metrica(valor, titulo, cor="#3F51B5"):
    """Cria um card para exibir uma métrica."""
    return f"""
    <div class="metric-card">
        <div class="metric-value" style="color: {cor};">{valor}</div>
        <div class="metric-title">{titulo}</div>
    </div>
    """

def criar_grafico_status(df_status):
    """Cria um gráfico de barras para distribuição por status."""
    if not df_status.empty:
        # Definir cores comuns para status
        cores = {
            "To Do": "#F44336",
            "Backlog": "#9C27B0",
            "Em Progresso": "#FF9800",
            "Em Andamento": "#FF9800",
            "In Progress": "#FF9800",
            "Em Revisão": "#2196F3",
            "Review": "#2196F3",
            "Concluído": "#4CAF50",
            "Done": "#4CAF50"
        }
        
        # Cores padrão para status não encontrados
        cores_status = df_status["index"].map(lambda x: cores.get(x, "#607D8B")).tolist()
        
        fig = px.bar(
            df_status, 
            x="index", 
            y="contagem",
            title="Distribuição de Issues por Status",
            labels={"index": "Status", "contagem": "Quantidade de Issues"},
            color="index",
            color_discrete_map={status: cor for status, cor in zip(df_status["index"], cores_status)}
        )
        
        fig.update_layout(xaxis_tickangle=-45)
        return fig
    
    # Retorna gráfico vazio se não houver dados
    return go.Figure()

def criar_grafico_burndown(df, inicio_sprint, fim_sprint):
    """Cria um gráfico de burndown para a sprint atual."""
    if not df.empty and "data_criacao" in df.columns and "data_resolucao" in df.columns:
        # Converte para datetime
        inicio = pd.to_datetime(inicio_sprint)
        fim = pd.to_datetime(fim_sprint)
        
        # Filtra issues na sprint
        df_sprint = df[
            (df["data_criacao"] >= inicio) & 
            (df["data_criacao"] <= fim)
        ].copy()
        
        if not df_sprint.empty:
            # Cria range de datas da sprint
            dias_sprint = pd.date_range(start=inicio, end=fim)
            
            # Para cada dia, conta issues pendentes
            burndown_data = []
            total_issues = len(df_sprint)
            
            for dia in dias_sprint:
                # Conta issues resolvidas até este dia
                resolvidas = df_sprint[
                    (df_sprint["data_resolucao"].notna()) & 
                    (df_sprint["data_resolucao"] <= dia)
                ].shape[0]
                
                # Calcula pendentes
                pendentes = total_issues - resolvidas
                
                burndown_data.append({
                    "data": dia,
                    "pendentes": pendentes
                })
            
            # Cria DataFrame do burndown
            df_burndown = pd.DataFrame(burndown_data)
            
            # Linha ideal/esperada
            df_ideal = pd.DataFrame({
                "data": [inicio, fim],
                "ideal": [total_issues, 0]
            })
            
            # Cria gráfico
            fig = go.Figure()
            
            # Adiciona linha real
            fig.add_trace(go.Scatter(
                x=df_burndown["data"], 
                y=df_burndown["pendentes"],
                mode="lines+markers",
                name="Real",
                line=dict(color="#FF5722", width=3)
            ))
            
            # Adiciona linha ideal
            fig.add_trace(go.Scatter(
                x=df_ideal["data"], 
                y=df_ideal["ideal"],
                mode="lines",
                name="Ideal",
                line=dict(color="#4CAF50", width=2, dash="dash")
            ))
            
            fig.update_layout(
                title="Burndown Chart da Sprint",
                xaxis_title="Data",
                yaxis_title="Issues Pendentes",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            return fig
    
    # Retorna gráfico vazio se não houver dados
    return go.Figure()

def criar_grafico_tendencia(df, coluna_data="data_criacao"):
    """Cria um gráfico de tendência de issues ao longo do tempo."""
    if not df.empty and coluna_data in df.columns:
        # Agrupa por mês
        df["mes"] = df[coluna_data].dt.to_period("M")
        tendencia = df.groupby("mes").size().reset_index(name="contagem")
        tendencia["mes"] = tendencia["mes"].astype(str)
        
        fig = px.line(
            tendencia, 
            x="mes", 
            y="contagem",
            title="Tendência de Issues ao Longo do Tempo",
            labels={"mes": "Mês", "contagem": "Quantidade de Issues"},
            markers=True
        )
        
        fig.update_layout(xaxis_tickangle=-45)
        return fig
    
    # Retorna gráfico vazio se não houver dados
    return go.Figure()

# ======= INTERFACE STREAMLIT =======

def main():
    st.title("📊 Métricas Jira")
    
    # Sidebar para configurações
    st.sidebar.title("Configurações da API Jira")
    
    # Configurações da conexão com o Jira
    jira_url = st.sidebar.text_input("URL do Jira", "https://seudominio.atlassian.net")
    jira_email = st.sidebar.text_input("Email de acesso")
    jira_token = st.sidebar.text_input("Token API", type="password", help="Token de API gerado nas configurações do Jira")
    
    # Define o estado da sessão para autenticação e projetos
    if "jira_autenticado" not in st.session_state:
        st.session_state.jira_autenticado = False
        
    if "jira_auth" not in st.session_state:
        st.session_state.jira_auth = None
        
    if "jira_headers" not in st.session_state:
        st.session_state.jira_headers = None
        
    if "jira_projetos" not in st.session_state:
        st.session_state.jira_projetos = []
    
    # Botão de conexão
    if st.sidebar.button("Conectar ao Jira"):
        with st.spinner("Conectando ao Jira..."):
            sucesso, auth, headers = conectar_jira(jira_url, jira_email, jira_token)
            
            if sucesso:
                st.session_state.jira_autenticado = True
                st.session_state.jira_auth = auth
                st.session_state.jira_headers = headers
                
                # Busca projetos
                sucesso_proj, projetos = buscar_projetos(jira_url, auth, headers)
                if sucesso_proj:
                    st.session_state.jira_projetos = projetos
                    st.sidebar.success(f"Conectado com sucesso! {len(projetos)} projetos encontrados.")
                else:
                    st.sidebar.warning("Conectado, mas não foi possível listar projetos.")
            else:
                st.sidebar.error("Falha na conexão. Verifique as credenciais.")
    
    # Exibe instruções para Jira Cloud
    with st.sidebar.expander("Como obter um Token API do Jira"):
        st.markdown("""
        1. Faça login no Atlassian Account: [id.atlassian.com](https://id.atlassian.com/)
        2. No canto superior direito, clique em Gerenciar Perfil
        3. Clique em Segurança
        4. Em "Tokens de API", clique em "Criar e gerenciar tokens de API"
        5. Clique em "Criar token de API"
        6. Dê um nome ao seu token e clique em "Criar"
        7. Copie o token gerado e cole no campo acima
        """)
    
    # Exibe projetos disponíveis se autenticado
    if st.session_state.jira_autenticado and st.session_state.jira_projetos:
        projeto_selecionado = st.sidebar.selectbox(
            "Selecione um Projeto",
            options=[p.get("name") for p in st.session_state.jira_projetos],
            index=0
        )
        
        # Obtém a chave do projeto selecionado
        projeto_key = next((p.get("key") for p in st.session_state.jira_projetos if p.get("name") == projeto_selecionado), None)
        
        # Parâmetros adicionais para filtragem
        st.sidebar.subheader("Filtros")
        
        periodo_padrao = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        data_inicio = st.sidebar.date_input("Data Inicial", datetime.strptime(periodo_padrao, "%Y-%m-%d"))
        data_fim = st.sidebar.date_input("Data Final", datetime.now())
        
        st.sidebar.subheader("Sprint (para Burndown)")
        sprint_inicio = st.sidebar.date_input("Início da Sprint", datetime.now() - timedelta(days=14))
        sprint_fim = st.sidebar.date_input("Fim da Sprint", datetime.now() + timedelta(days=14))
        
        # JQL filter
        jql_filtro = f'project = "{projeto_key}" AND created >= "{data_inicio.strftime("%Y-%m-%d")}" AND created <= "{data_fim.strftime("%Y-%m-%d")}"'
        
        # Buscar dados
        if st.sidebar.button("Atualizar Dados"):
            with st.spinner("Buscando dados do Jira..."):
                sucesso, dados_issues = buscar_issues(
                    jira_url, 
                    st.session_state.jira_auth, 
                    st.session_state.jira_headers, 
                    jql_filtro
                )
                
                if sucesso:
                    # Extrair dados e armazenar no state
                    df_issues = extrair_campos_issues(dados_issues)
                    st.session_state.df_issues = df_issues
                    st.sidebar.success(f"{len(df_issues)} issues encontradas!")
                else:
                    st.error("Falha ao buscar issues. Verifique o filtro JQL.")
        
        # Exibe o dashboard se houver dados
        if "df_issues" in st.session_state and not st.session_state.df_issues.empty:
            df = st.session_state.df_issues
            
            # Cabeçalho com métricas principais
            st.markdown(f"""
            <div class="highlight-box">
                <h3>Visão Geral de {projeto_selecionado}</h3>
                <p>Período: {data_inicio.strftime("%d/%m/%Y")} a {data_fim.strftime("%d/%m/%Y")}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Métricas principais
            col1, col2, col3, col4 = st.columns(4)
            
            total_issues = len(df)
            abertas = df[~df["status"].isin(["Done", "Concluído", "Fechado", "Resolved"])].shape[0]
            fechadas = total_issues - abertas
            
            # Calcular tempo médio de resolução
            tempo_medio = None
            df_resolvidas = df[df["data_resolucao"].notna()]
            if not df_resolvidas.empty and "tempo_resolucao" in df_resolvidas.columns:
                tempo_medio = df_resolvidas["tempo_resolucao"].mean()
            
            with col1:
                st.markdown(criar_card_metrica(total_issues, "Total de Issues"), unsafe_allow_html=True)
                
            with col2:
                st.markdown(criar_card_metrica(abertas, "Issues Abertas", "#F44336"), unsafe_allow_html=True)
                
            with col3:
                st.markdown(criar_card_metrica(fechadas, "Issues Fechadas", "#4CAF50"), unsafe_allow_html=True)
                
            with col4:
                if tempo_medio is not None:
                    st.markdown(criar_card_metrica(f"{tempo_medio:.1f} dias", "Tempo Médio de Resolução", "#FF9800"), unsafe_allow_html=True)
                else:
                    st.markdown(criar_card_metrica("N/A", "Tempo Médio de Resolução", "#9E9E9E"), unsafe_allow_html=True)
            
            # Tabs para diferentes visualizações
            tab_geral, tab_tendencias, tab_sprint, tab_dados = st.tabs([
                "Visão Geral", "Tendências", "Burndown Sprint", "Dados Brutos"
            ])
            
            with tab_geral:
                col1, col2 = st.columns(2)
                
                with col1:
                    # Gráfico de Status
                    df_status = resumo_status(df)
                    if not df_status.empty:
                        fig_status = criar_grafico_status(df_status)
                        st.plotly_chart(fig_status, use_container_width=True)
                
                with col2:
                    # Gráfico de Prioridade
                    df_prioridade = resumo_prioridade(df)
                    if not df_prioridade.empty:
                        fig_prioridade = px.pie(
                            df_prioridade, 
                            names="index", 
                            values="contagem",
                            title="Distribuição por Prioridade"
                        )
                        st.plotly_chart(fig_prioridade, use_container_width=True)
                
                # Gráfico de Responsáveis
                df_resp = resumo_responsaveis(df)
                if not df_resp.empty:
                    if len(df_resp) > 10:
                        df_resp = df_resp.sort_values("contagem", ascending=False).head(10)
                        
                    fig_resp = px.bar(
                        df_resp, 
                        x="index", 
                        y="contagem",
                        title="Top 10 Responsáveis por Número de Issues",
                        labels={"index": "Responsável", "contagem": "Quantidade de Issues"}
                    )
                    st.plotly_chart(fig_resp, use_container_width=True)
            
            with tab_tendencias:
                col1, col2 = st.columns(2)
                
                with col1:
                    # Tendência de criação
                    fig_tendencia = criar_grafico_tendencia(df, "data_criacao")
                    st.plotly_chart(fig_tendencia, use_container_width=True)
                
                with col2:
                    # Tendência de resolução
                    if "data_resolucao" in df.columns and not df["data_resolucao"].isnull().all():
                        df_resolucao = df[df["data_resolucao"].notna()].copy()
                        fig_resolucao = criar_grafico_tendencia(df_resolucao, "data_resolucao")
                        st.plotly_chart(fig_resolucao, use_container_width=True)
                
                # Tempo médio de resolução por tipo
                if "tempo_resolucao" in df.columns and not df["tempo_resolucao"].isnull().all():
                    df_tempo = df[df["tempo_resolucao"].notna()].copy()
                    
                    fig_tempo = px.bar(
                        df_tempo.groupby("tipo")["tempo_resolucao"].mean().reset_index(),
                        x="tipo",
                        y="tempo_resolucao",
                        title="Tempo Médio de Resolução por Tipo (dias)",
                        labels={"tipo": "Tipo de Issue", "tempo_resolucao": "Tempo Médio (dias)"}
                    )
                    st.plotly_chart(fig_tempo, use_container_width=True)
            
            with tab_sprint:
                # Burndown chart
                fig_burndown = criar_grafico_burndown(df, sprint_inicio, sprint_fim)
                st.plotly_chart(fig_burndown, use_container_width=True)
                
                # Informações da sprint
                col1, col2 = st.columns(2)
                
                with col1:
                    # Filtra issues da sprint
                    df_sprint = df[
                        (df["data_criacao"] >= pd.to_datetime(sprint_inicio)) & 
                        (df["data_criacao"] <= pd.to_datetime(sprint_fim))
                    ].copy()
                    
                    total_sprint = len(df_sprint)
                    concluidas = df_sprint[df_sprint["status"].isin(["Done", "Concluído", "Fechado", "Resolved"])].shape[0]
                    
                    st.metric("Total de Issues na Sprint", total_sprint)
                    st.metric("Issues Concluídas", concluidas)
                    
                    if total_sprint > 0:
                        st.metric("Progresso", f"{(concluidas / total_sprint * 100):.1f}%")
                
                with col2:
                    # Status na sprint
                    if not df_sprint.empty:
                        status_sprint = df_sprint["status"].value_counts().reset_index(name="contagem")
                        fig_status_sprint = px.pie(
                            status_sprint, 
                            names="index", 
                            values="contagem",
                            title="Status das Issues na Sprint"
                        )
                        st.plotly_chart(fig_status_sprint, use_container_width=True)
            
            with tab_dados:
                # Exibe dados brutos
                st.dataframe(df)
                
                # Opção para exportar
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "Baixar dados como CSV",
                    csv,
                    f"jira_issues_{projeto_key}_{data_inicio.strftime('%Y%m%d')}_{data_fim.strftime('%Y%m%d')}.csv",
                    "text/csv",
                    key='download-csv'
                )
        
        elif st.session_state.jira_autenticado:
            # Exibe mensagem se não há dados
            st.info("Conectado ao Jira. Selecione um projeto e clique em 'Atualizar Dados' para visualizar as métricas.")
            
    else:
        # Exibe tela inicial com instruções
        st.markdown("""
        <div class="highlight-box">
            <h3>Dashboard de Métricas do Jira</h3>
            <p>Esta página permite visualizar métricas e estatísticas de projetos do Jira, incluindo:</p>
            <ul>
                <li>Visão geral de issues por status, prioridade e responsável</li>
                <li>Tendências de criação e resolução de issues</li>
                <li>Burndown chart para acompanhamento de sprints</li>
                <li>Tempo médio de resolução por tipo de issue</li>
            </ul>
            <p>Para começar, configure a conexão com a API do Jira no painel lateral.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Exemplo de visualização
        st.subheader("Exemplo de visualização")
        
        # Dados simulados para demonstração
        dados_demo = {
            "Status": ["To Do", "In Progress", "Review", "Done"],
            "Quantidade": [12, 8, 5, 20]
        }
        
        df_demo = pd.DataFrame(dados_demo)
        
        fig = px.bar(
            df_demo, 
            x="Status", 
            y="Quantidade",
            title="Exemplo: Distribuição de Issues por Status",
            color="Status",
            color_discrete_map={
                "To Do": "#F44336",
                "In Progress": "#FF9800",
                "Review": "#2196F3",
                "Done": "#4CAF50"
            }
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Instruções para gerar token API
        st.markdown("""
        ### Como conectar ao Jira

        1. No painel lateral, insira a URL do seu Jira (ex: https://seudominio.atlassian.net)
        2. Insira o email associado à sua conta do Jira
        3. Gere um token API no seu perfil do Atlassian e insira no campo "Token API"
        4. Clique em "Conectar ao Jira"
        
        Após conectar, você poderá selecionar projetos e visualizar suas métricas.
        """)

if __name__ == "__main__":
    main()