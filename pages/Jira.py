import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from requests.auth import HTTPBasicAuth
import requests
from datetime import datetime, timedelta
import json
import os
import sqlite3
from pathlib import Path
import hashlib
import time
import sys

# Adiciona o diretório raiz ao path para permitir importações
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Importa o módulo de backend
from utils.jira_db import (initialize_db, save_jira_config, 
                          get_saved_jira_configs, get_jira_projects, 
                          save_jira_projects)


# Configuração da página
st.set_page_config(
    page_title="Métricas Jira",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Constantes e configuração
DB_PATH = Path("./jira_config.db")
COLOR_THEME = {
    "primary": "#6366F1",    # Indigo
    "secondary": "#A5B4FC",  # Lighter indigo
    "success": "#10B981",    # Emerald
    "warning": "#F59E0B",    # Amber
    "danger": "#EF4444",     # Red
    "neutral": "#6B7280",    # Gray
    "background": "#F9FAFB", # Light gray
}

# Status mapping para categorias padrão
STATUS_MAPPING = {
    # To Do e backlog
    "To Do": "Pendente",
    "Backlog": "Pendente",
    "Open": "Pendente",
    "Aberto": "Pendente",
    
    # Em progresso
    "In Progress": "Em Progresso",
    "Em Andamento": "Em Progresso",
    "Em Progresso": "Em Progresso",
    
    # Em revisão
    "Review": "Em Revisão",
    "Em Revisão": "Em Revisão",
    "Pull Request": "Em Revisão",
    "Reviewing": "Em Revisão",
    
    # Completo
    "Done": "Concluído",
    "Concluído": "Concluído",
    "Completo": "Concluído",
    "Closed": "Concluído",
    "Fechado": "Concluído",
    "Resolved": "Concluído"
}

# Cores para as categorias
STATUS_COLORS = {
    "Pendente": "#EF4444",  # Vermelho
    "Em Progresso": "#F59E0B",  # Laranja
    "Em Revisão": "#3B82F6",  # Azul
    "Concluído": "#10B981",  # Verde
}

# Função para CSS personalizado
def set_custom_css():
    st.markdown("""
    <style>
    /* Base */
    .main {
        background-color: #F9FAFB;
        padding: 1.5rem;
    }
    
    /* Sidebar */
    .css-1d391kg {
        background-color: #FFF;
    }
    
    /* Cards */
    .metric-card {
        background-color: white;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        padding: 1.5rem;
        text-align: center;
        height: 100%;
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    .metric-title {
        font-size: 0.9rem;
        color: #6B7280;
        font-weight: 500;
    }
    
    /* Status colors */
    .status-pendente { color: #EF4444; }
    .status-progresso { color: #F59E0B; }
    .status-revisao { color: #3B82F6; }
    .status-concluido { color: #10B981; }
    
    /* Project header */
    .project-header {
        background-color: white;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }
    .project-title {
        font-size: 1.5rem;
        margin: 0;
        color: #111827;
    }
    .project-subtitle {
        font-size: 0.9rem;
        color: #6B7280;
    }
    
    /* Section titles */
    .section-title {
        font-size: 1.2rem;
        color: #111827;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #E5E7EB;
    }
    
    /* Container padronizado */
    .content-container {
        background-color: white;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }
    
    /* Badges */
    .badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 500;
    }
    .badge-pendente {
        background-color: #FEE2E2;
        color: #B91C1C;
    }
    .badge-progresso {
        background-color: #FEF3C7;
        color: #92400E;
    }
    .badge-revisao {
        background-color: #DBEAFE;
        color: #1E40AF;
    }
    .badge-concluido {
        background-color: #D1FAE5;
        color: #065F46;
    }
    
    /* Progresso */
    .progress-container {
        background-color: #E5E7EB;
        border-radius: 8px;
        height: 0.5rem;
        overflow: hidden;
        margin-top: 0.5rem;
    }
    .progress-bar {
        height: 100%;
        border-radius: 8px;
    }
    
    /* Tabs customizadas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: white;
        border-radius: 4px 4px 0 0;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #6366F1;
        color: white;
    }
    
    /* Data picker */
    .date-filters {
        display: flex;
        gap: 1rem;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)


## Backend para persistência de conexão Jira

# Funções para gerenciar o banco de dados de configuração
def initialize_db():
    """Inicializa o banco de dados para armazenar configurações do Jira"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS jira_config (
        id INTEGER PRIMARY KEY,
        url TEXT NOT NULL,
        email TEXT NOT NULL,
        token_hash TEXT NOT NULL,
        last_used TIMESTAMP
    )
    ''')
    
    c.execute('''
    CREATE TABLE IF NOT EXISTS jira_projects (
        id INTEGER PRIMARY KEY,
        config_id INTEGER,
        project_key TEXT NOT NULL,
        project_name TEXT NOT NULL,
        FOREIGN KEY (config_id) REFERENCES jira_config (id)
    )
    ''')
    
    conn.commit()
    conn.close()

def save_jira_config(url, email, token):
    """Salva as configurações do Jira no banco de dados"""
    # Hash do token para não armazenar em texto puro
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Verifica se já existe configuração com mesmo email
    c.execute('SELECT id FROM jira_config WHERE email = ?', (email,))
    result = c.fetchone()
    
    if result:
        # Atualiza configuração existente
        c.execute('''
        UPDATE jira_config
        SET url = ?, token_hash = ?, last_used = ?
        WHERE id = ?
        ''', (url, token_hash, datetime.now(), result[0]))
        config_id = result[0]
    else:
        # Insere nova configuração
        c.execute('''
        INSERT INTO jira_config (url, email, token_hash, last_used)
        VALUES (?, ?, ?, ?)
        ''', (url, email, token_hash, datetime.now()))
        config_id = c.lastrowid
    
    conn.commit()
    conn.close()
    
    # Salva o token na session_state para uso sem precisar solicitar novamente
    st.session_state.jira_token = token
    
    return config_id

def get_saved_jira_configs():
    """Recupera as configurações salvas do Jira"""
    if not os.path.exists(DB_PATH):
        return []
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
    SELECT id, url, email, last_used
    FROM jira_config
    ORDER BY last_used DESC
    ''')
    
    configs = []
    for row in c.fetchall():
        configs.append({
            'id': row[0],
            'url': row[1],
            'email': row[2],
            'last_used': row[3]
        })
    
    conn.close()
    return configs

def get_jira_config(config_id):
    """Recupera uma configuração específica do Jira"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT url, email FROM jira_config WHERE id = ?', (config_id,))
    result = c.fetchone()
    conn.close()
    
    if result:
        return {'url': result[0], 'email': result[1]}
    return None

def save_jira_projects(config_id, projects):
    """Salva os projetos do Jira no banco de dados"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Remove projetos existentes para esta configuração
    c.execute('DELETE FROM jira_projects WHERE config_id = ?', (config_id,))
    
    # Insere novos projetos
    for project in projects:
        c.execute('''
        INSERT INTO jira_projects (config_id, project_key, project_name)
        VALUES (?, ?, ?)
        ''', (config_id, project.get('key'), project.get('name')))
    
    conn.commit()
    conn.close()

def get_jira_projects(config_id):
    """Recupera os projetos salvos para uma configuração do Jira"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
    SELECT project_key, project_name
    FROM jira_projects
    WHERE config_id = ?
    ''', (config_id,))
    
    projects = []
    for row in c.fetchall():
        projects.append({
            'key': row[0],
            'name': row[1]
        })
    
    conn.close()
    return projects


## API Jira - Funções para interagir com a API Jira

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
        st.error(f"Erro ao conectar com o Jira: {str(e)}")
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
        st.error(f"Erro ao buscar projetos: {str(e)}")
        return False, []

def buscar_issues(url, auth, headers, jql, campos=None, max_results=500):
    """Busca issues com base em uma query JQL."""
    if campos is None:
        campos = ["summary", "status", "assignee", "priority", "created", 
                  "updated", "resolutiondate", "issuetype", "description", 
                  "duedate", "timeoriginalestimate", "timespent", "parent"]
        
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

def buscar_sprints(url, auth, headers, project_key):
    """Busca as sprints de um projeto."""
    try:
        # Primeiro precisamos buscar os boards do projeto
        response = requests.get(
            f"{url}/rest/agile/1.0/board?projectKeyOrId={project_key}",
            headers=headers,
            auth=auth
        )
        
        if response.status_code != 200:
            return False, []
        
        boards = response.json().get("values", [])
        if not boards:
            return False, []
        
        # Usamos o primeiro board encontrado para buscar as sprints
        board_id = boards[0].get("id")
        
        sprint_response = requests.get(
            f"{url}/rest/agile/1.0/board/{board_id}/sprint",
            headers=headers,
            auth=auth
        )
        
        if sprint_response.status_code == 200:
            sprints = sprint_response.json().get("values", [])
            return True, sprints
        else:
            return False, []
    except Exception as e:
        st.error(f"Erro ao buscar sprints: {str(e)}")
        return False, []

def buscar_epics(url, auth, headers, project_key):
    """Busca as epics de um projeto."""
    try:
        jql = f'project = {project_key} AND issuetype = Epic'
        
        response = requests.get(
            f"{url}/rest/api/3/search",
            headers=headers,
            params={"jql": jql, "fields": "summary,status,key"},
            auth=auth
        )
        
        if response.status_code == 200:
            epics = response.json().get("issues", [])
            return True, epics
        else:
            return False, []
    except Exception as e:
        st.error(f"Erro ao buscar epics: {str(e)}")
        return False, []


## Processamento de Dados

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
            "status_original": campos.get("status", {}).get("name", "") if campos.get("status") else "",
            "tipo": campos.get("issuetype", {}).get("name", "") if campos.get("issuetype") else "",
            "prioridade": campos.get("priority", {}).get("name", "") if campos.get("priority") else "",
            "data_criacao": campos.get("created", ""),
            "data_atualizacao": campos.get("updated", ""),
            "data_resolucao": campos.get("resolutiondate", ""),
            "data_vencimento": campos.get("duedate", ""),
            "tempo_estimado": campos.get("timeoriginalestimate", 0),
            "tempo_gasto": campos.get("timespent", 0)
        }
        
        # Mapeia o status para categorias padronizadas
        item["status"] = STATUS_MAPPING.get(item["status_original"], "Pendente")
        
        # Adiciona informações do pai (para subtasks)
        if campos.get("parent"):
            item["parent_key"] = campos.get("parent", {}).get("key", "")
            item["parent_summary"] = campos.get("parent", {}).get("fields", {}).get("summary", "")
        else:
            item["parent_key"] = ""
            item["parent_summary"] = ""
        
        # Adiciona o responsável se existir
        if campos.get("assignee"):
            item["responsavel"] = campos["assignee"].get("displayName", "")
            item["responsavel_email"] = campos["assignee"].get("emailAddress", "")
            item["responsavel_id"] = campos["assignee"].get("accountId", "")
        else:
            item["responsavel"] = "Não atribuído"
            item["responsavel_email"] = ""
            item["responsavel_id"] = ""
        
        issues.append(item)
    
    # Cria DataFrame
    if issues:
        df = pd.DataFrame(issues)
        
        # Converte datas para datetime
        for coluna in ["data_criacao", "data_atualizacao", "data_resolucao", "data_vencimento"]:
            if coluna in df.columns:
                df[coluna] = pd.to_datetime(df[coluna], errors="coerce")
                
        # Calcula tempo de resolução (em dias) onde aplicável
        if "data_criacao" in df.columns and "data_resolucao" in df.columns:
            df["tempo_resolucao"] = (df["data_resolucao"] - df["data_criacao"]).dt.total_seconds() / (3600 * 24)
            
        # Calcula semana e mês
        if "data_criacao" in df.columns:
            df["semana_criacao"] = df["data_criacao"].dt.isocalendar().week
            df["mes_criacao"] = df["data_criacao"].dt.month
            df["ano_criacao"] = df["data_criacao"].dt.year
            
        if "data_resolucao" in df.columns:
            df["semana_resolucao"] = df["data_resolucao"].dt.isocalendar().week
            df["mes_resolucao"] = df["data_resolucao"].dt.month
            df["ano_resolucao"] = df["data_resolucao"].dt.year
        
        return df
    else:
        return pd.DataFrame()

def calcular_metricas_gerais(df):
    """Calcula métricas gerais para o dashboard."""
    metricas = {}
    
    if not df.empty:
        # Total de issues
        metricas["total_issues"] = len(df)
        
        # Issues por status
        metricas["issues_por_status"] = df["status"].value_counts().to_dict()
        
        # Percentual concluído
        metricas["percentual_concluido"] = (df["status"] == "Concluído").mean() * 100
        
        # Tempo médio de resolução
        df_resolvidas = df[df["data_resolucao"].notna()]
        if not df_resolvidas.empty and "tempo_resolucao" in df_resolvidas.columns:
            metricas["tempo_medio_resolucao"] = df_resolvidas["tempo_resolucao"].mean()
        else:
            metricas["tempo_medio_resolucao"] = None
            
        # Issues sem responsável
        metricas["sem_responsavel"] = (df["responsavel"] == "Não atribuído").sum()
        
        # Issues vencidas
        if "data_vencimento" in df.columns:
            hoje = pd.Timestamp.now().normalize()
            metricas["issues_vencidas"] = ((df["data_vencimento"] < hoje) & 
                                          (df["status"] != "Concluído") & 
                                          (df["data_vencimento"].notna())).sum()
        else:
            metricas["issues_vencidas"] = 0
            
        # Issues por tipo
        metricas["issues_por_tipo"] = df["tipo"].value_counts().to_dict()
    
    return metricas

def calcular_metricas_usuario(df):
    """Calcula métricas por usuário."""
    if df.empty or "responsavel" not in df.columns:
        return pd.DataFrame()
    
    # Remove issues sem responsável
    df_com_resp = df[df["responsavel"] != "Não atribuído"].copy()
    
    if df_com_resp.empty:
        return pd.DataFrame()
    
    # Agrupa por responsável
    metricas_usuario = df_com_resp.groupby("responsavel").agg({
        "key": "count",  # Total de issues
        "tempo_resolucao": lambda x: x.mean() if not x.isnull().all() else None,  # Tempo médio de resolução
        "status": lambda x: (x == "Concluído").mean() * 100  # Percentual concluído
    }).reset_index()
    
    # Renomeia colunas
    metricas_usuario.columns = ["responsavel", "total_issues", "tempo_medio_resolucao", "percentual_concluido"]
    
    # Calcula issues por status
    status_por_usuario = df_com_resp.pivot_table(
        index="responsavel", 
        columns="status", 
        values="key", 
        aggfunc="count", 
        fill_value=0
    ).reset_index()
    
    # Mescla os dataframes
    if not status_por_usuario.empty:
        metricas_usuario = pd.merge(metricas_usuario, status_por_usuario, on="responsavel", how="left")
    
    return metricas_usuario

def calcular_metricas_usuario_periodo(df, periodo="semana"):
    """Calcula métricas por usuário por período (semana ou mês)."""
    if df.empty or "responsavel" not in df.columns:
        return pd.DataFrame()
    
    # Remove issues sem responsável
    df_com_resp = df[df["responsavel"] != "Não atribuído"].copy()
    
    if df_com_resp.empty:
        return pd.DataFrame()
    
    # Define as colunas de período
    if periodo == "semana":
        periodo_criacao = "semana_criacao"
        periodo_resolucao = "semana_resolucao"
        ano_criacao = "ano_criacao"
        ano_resolucao = "ano_resolucao"
    else:  # mês
        periodo_criacao = "mes_criacao"
        periodo_resolucao = "mes_resolucao"
        ano_criacao = "ano_criacao"
        ano_resolucao = "ano_resolucao"
    
    # Verifica se as colunas necessárias existem
    colunas_requeridas = [periodo_criacao, ano_criacao]
    if not all(col in df_com_resp.columns for col in colunas_requeridas):
        return pd.DataFrame()
    
    # Issues criadas por período
    criadas_periodo = df_com_resp.groupby(["responsavel", ano_criacao, periodo_criacao]).size().reset_index(name="issues_criadas")
    
    # Issues resolvidas por período (se tiver data de resolução)
    if periodo_resolucao in df_com_resp.columns and ano_resolucao in df_com_resp.columns:
        df_resolvidas = df_com_resp[df_com_resp["data_resolucao"].notna()].copy()
        if not df_resolvidas.empty:
            resolvidas_periodo = df_resolvidas.groupby(["responsavel", ano_resolucao, periodo_resolucao]).size().reset_index(name="issues_resolvidas")
            
            # Mescla criadas e resolvidas
            periodo_completo = pd.merge(
                criadas_periodo, 
                resolvidas_periodo, 
                left_on=["responsavel", ano_criacao, periodo_criacao], 
                right_on=["responsavel", ano_resolucao, periodo_resolucao], 
                how="outer"
            ).fillna(0)
        else:
            periodo_completo = criadas_periodo
            periodo_completo["issues_resolvidas"] = 0
    else:
        periodo_completo = criadas_periodo
        periodo_completo["issues_resolvidas"] = 0
    
    return periodo_completo

def agrupar_por_semana(df, coluna_data="data_criacao", valor="key", operacao="count"):
    """Agrupa dados por semana para visualização de tendências."""
    if df.empty or coluna_data not in df.columns:
        return pd.DataFrame()
    
    # Cria coluna de semana e ano
    df_temp = df.copy()
    df_temp["ano"] = df_temp[coluna_data].dt.isocalendar().year
    df_temp["semana"] = df_temp[coluna_data].dt.isocalendar().week
    
    # Aplica a operação de agregação
    if operacao == "count":
        resultado = df_temp.groupby(["ano", "semana"]).size().reset_index(name="contagem")
    elif operacao == "mean" and valor in df_temp.columns:
        resultado = df_temp.groupby(["ano", "semana"])[valor].mean().reset_index(name="media")
    else:
        return pd.DataFrame()
    
    # Formata a data para exibição
    resultado["periodo"] = resultado.apply(
        lambda x: f"{x['ano']}-W{x['semana']:02d}", axis=1
    )
    
    return resultado

def agrupar_por_mes(df, coluna_data="data_criacao", valor="key", operacao="count"):
    """Agrupa dados por mês para visualização de tendências."""
    if df.empty or coluna_data not in df.columns:
        return pd.DataFrame()
    
    # Cria coluna de mês e ano
    df_temp = df.copy()
    df_temp["ano"] = df_temp[coluna_data].dt.year
    df_temp["mes"] = df_temp[coluna_data].dt.month
    
    # Aplica a operação de agregação
    if operacao == "count":
        resultado = df_temp.groupby(["ano", "mes"]).size().reset_index(name="contagem")
    elif operacao == "mean" and valor in df_temp.columns:
        resultado = df_temp.groupby(["ano", "mes"])[valor].mean().reset_index(name="media")
    else:
        return pd.DataFrame()
    
    # Formata a data para exibição
    resultado["periodo"] = resultado.apply(
        lambda x: f"{x['ano']}-{x['mes']:02d}", axis=1
    )
    
    return resultado


## Visualizações e Gráficos

def criar_card_metrica(valor, titulo, cor="#6366F1", tooltip=None):
    """Cria um card para exibir uma métrica."""
    if isinstance(valor, float):
        valor_formatado = f"{valor:.1f}"
    else:
        valor_formatado = str(valor)
    
    tooltip_attr = f'title="{tooltip}"' if tooltip else ''
    
    return f"""
    <div class="metric-card" {tooltip_attr}>
        <div class="metric-value" style="color: {cor};">{valor_formatado}</div>
        <div class="metric-title">{titulo}</div>
    </div>
    """

def criar_barra_progresso(percentual, cor="#6366F1"):
    """Cria uma barra de progresso."""
    return f"""
    <div class="progress-container">
        <div class="progress-bar" style="width: {percentual}%; background-color: {cor};"></div>
    </div>
    """

def criar_grafico_status(df_status, titulo="Distribuição por Status"):
    """Cria um gráfico de barras para distribuição por status."""
    if not isinstance(df_status, pd.DataFrame) or df_status.empty:
        return go.Figure()
    
    # Cores padrão para status
    cores_status = df_status["status"].map(lambda x: STATUS_COLORS.get(x, "#6B7280")).tolist()
    
    fig = px.bar(
        df_status, 
        x="status", 
        y="contagem",
        title=titulo,
        color="status",
        color_discrete_map={status: cor for status, cor in zip(df_status["status"], cores_status)}
    )
    
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis_title="",
        yaxis_title="Quantidade",
        legend_title_text=""
    )
    
    return fig

def criar_grafico_burndown(df, inicio_sprint, fim_sprint, titulo="Burndown Chart"):
    """Cria um gráfico de burndown para a sprint."""
    if not isinstance(df, pd.DataFrame) or df.empty:
        return go.Figure()
    
    # Converte para datetime
    inicio = pd.to_datetime(inicio_sprint)
    fim = pd.to_datetime(fim_sprint)
    
    # Filtra issues na sprint
    df_sprint = df[
        (df["data_criacao"] >= inicio) & 
        (df["data_criacao"] <= fim)
    ].copy()
    
    if df_sprint.empty:
        return go.Figure()
    
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
        line=dict(color=COLOR_THEME["primary"], width=3)
    ))
    
    # Adiciona linha ideal
    fig.add_trace(go.Scatter(
        x=df_ideal["data"], 
        y=df_ideal["ideal"],
        mode="lines",
        name="Ideal",
        line=dict(color=COLOR_THEME["success"], width=2, dash="dash")
    ))
    
    fig.update_layout(
        title=titulo,
        xaxis_title="Data",
        yaxis_title="Issues Pendentes",
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig

def criar_grafico_tendencia(df_tendencia, titulo="Tendência de Issues"):
    """Cria um gráfico de tendência."""
    if not isinstance(df_tendencia, pd.DataFrame) or df_tendencia.empty:
        return go.Figure()
    
    fig = px.line(
        df_tendencia, 
        x="periodo", 
        y="contagem",
        title=titulo,
        markers=True,
        line_shape="linear"
    )
    
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis_title="",
        yaxis_title="Quantidade",
        xaxis_tickangle=-45
    )
    
    return fig

def criar_grafico_velocidade_equipe(df, titulo="Velocidade da Equipe"):
    """Cria um gráfico de velocidade da equipe."""
    if not isinstance(df, pd.DataFrame) or df.empty:
        return go.Figure()
    
    # Primeiro agrupa por semana
    df_semana = agrupar_por_semana(df, "data_resolucao")
    
    if df_semana.empty:
        return go.Figure()
    
    fig = px.bar(
        df_semana,
        x="periodo",
        y="contagem",
        title=titulo,
        color_discrete_sequence=[COLOR_THEME["primary"]]
    )
    
    # Adiciona linha de média
    media = df_semana["contagem"].mean()
    fig.add_hline(
        y=media,
        line_dash="dash",
        line_color=COLOR_THEME["warning"],
        annotation_text=f"Média: {media:.1f}",
        annotation_position="bottom right"
    )
    
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis_title="",
        yaxis_title="Issues Concluídas",
        xaxis_tickangle=-45
    )
    
    return fig

def criar_heatmap_atividade_usuario(df, periodo="semana", titulo="Atividade por Usuário"):
    """Cria um heatmap de atividade por usuário."""
    if not isinstance(df, pd.DataFrame) or df.empty:
        return go.Figure()
    
    # Remove issues sem responsável
    df_com_resp = df[df["responsavel"] != "Não atribuído"].copy()
    
    if df_com_resp.empty:
        return go.Figure()
    
    # Define as colunas de período
    if periodo == "semana":
        periodo_col = "semana_resolucao"
        ano_col = "ano_resolucao"
    else:  # mês
        periodo_col = "mes_resolucao"
        ano_col = "ano_resolucao"
    
    # Verifica se as colunas necessárias existem
    if periodo_col not in df_com_resp.columns or ano_col not in df_com_resp.columns:
        return go.Figure()
    
    # Filtra apenas issues resolvidas
    df_resolvidas = df_com_resp[df_com_resp["data_resolucao"].notna()].copy()
    
    if df_resolvidas.empty:
        return go.Figure()
    
    # Formata o período
    if periodo == "semana":
        df_resolvidas["periodo_formatado"] = df_resolvidas.apply(
            lambda x: f"{x[ano_col]}-W{x[periodo_col]:02d}", axis=1
        )
    else:
        df_resolvidas["periodo_formatado"] = df_resolvidas.apply(
            lambda x: f"{x[ano_col]}-{x[periodo_col]:02d}", axis=1
        )
    
    # Conta issues por usuário e período
    heatmap_data = df_resolvidas.groupby(["responsavel", "periodo_formatado"]).size().reset_index(name="contagem")
    
    # Pivota os dados para formato de matriz
    heatmap_pivot = heatmap_data.pivot(
        index="responsavel",
        columns="periodo_formatado",
        values="contagem"
    ).fillna(0)
    
    # Cria o heatmap
    fig = px.imshow(
        heatmap_pivot,
        labels=dict(x="Período", y="Responsável", color="Issues Concluídas"),
        x=heatmap_pivot.columns,
        y=heatmap_pivot.index,
        color_continuous_scale="Blues",
        title=titulo
    )
    
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis_tickangle=-45
    )
    
    return fig

def criar_grafico_desempenho_usuario(df_usuario, metrica="total_issues", top_n=10, titulo="Desempenho por Usuário"):
    """Cria um gráfico de desempenho por usuário."""
    if not isinstance(df_usuario, pd.DataFrame) or df_usuario.empty or metrica not in df_usuario.columns:
        return go.Figure()
    
    # Ordenar e pegar os top N
    df_top = df_usuario.sort_values(metrica, ascending=False).head(top_n)
    
    fig = px.bar(
        df_top,
        x="responsavel",
        y=metrica,
        title=titulo,
        color_discrete_sequence=[COLOR_THEME["primary"]]
    )
    
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis_title="",
        yaxis_title=metrica.replace("_", " ").title(),
        xaxis_tickangle=-45
    )
    
    return fig

def criar_grafico_distribuicao_trabalho(df):
    """Cria um gráfico de distribuição de trabalho pela equipe."""
    if not isinstance(df, pd.DataFrame) or df.empty:
        return go.Figure()
    
    # Remove issues sem responsável
    df_com_resp = df[df["responsavel"] != "Não atribuído"].copy()
    
    if df_com_resp.empty:
        return go.Figure()
    
    # Conta issues por responsável e status
    df_dist = df_com_resp.groupby(["responsavel", "status"]).size().reset_index(name="contagem")
    
    fig = px.bar(
        df_dist,
        x="responsavel",
        y="contagem",
        color="status",
        title="Distribuição de Issues por Equipe",
        color_discrete_map=STATUS_COLORS
    )
    
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis_title="",
        yaxis_title="Quantidade de Issues",
        xaxis_tickangle=-45,
        legend_title_text=""
    )
    
    return fig

def criar_grafico_previsao_conclusao(df):
    """Cria um gráfico de previsão de conclusão de projeto com base na velocidade atual."""
    if not isinstance(df, pd.DataFrame) or df.empty:
        return go.Figure(), None
    
    # Calcula a velocidade média de resolução (issues por semana)
    df_resolvidas = df[df["data_resolucao"].notna()].copy()
    
    if df_resolvidas.empty:
        return go.Figure(), None
    
    # Agrupa por semana
    df_semana = agrupar_por_semana(df_resolvidas, "data_resolucao")
    
    if df_semana.empty:
        return go.Figure(), None
    
    # Calcula a velocidade média
    velocidade_media = df_semana["contagem"].mean()
    
    # Calcula quantas issues ainda estão pendentes
    pendentes = df[df["status"] != "Concluído"].shape[0]
    
    # Calcula semanas necessárias para concluir
    if velocidade_media > 0:
        semanas_restantes = pendentes / velocidade_media
    else:
        semanas_restantes = float('inf')
    
    # Calcula data estimada de conclusão
    hoje = pd.Timestamp.now()
    if semanas_restantes != float('inf'):
        data_conclusao = hoje + pd.Timedelta(weeks=semanas_restantes)
        data_conclusao_str = data_conclusao.strftime("%d/%m/%Y")
    else:
        data_conclusao = None
        data_conclusao_str = "Indeterminada"
    
    # Cria gráfico de projeção
    fig = go.Figure()
    
    # Histórico
    df_historico = agrupar_por_semana(df, "data_criacao")
    df_historico_resolucao = agrupar_por_semana(df_resolvidas, "data_resolucao")
    
    if not df_historico.empty and not df_historico_resolucao.empty:
        fig.add_trace(go.Scatter(
            x=df_historico["periodo"],
            y=df_historico["contagem"].cumsum(),
            mode="lines+markers",
            name="Acumulado Criadas",
            line=dict(color=COLOR_THEME["danger"], width=2)
        ))
        
        fig.add_trace(go.Scatter(
            x=df_historico_resolucao["periodo"],
            y=df_historico_resolucao["contagem"].cumsum(),
            mode="lines+markers",
            name="Acumulado Resolvidas",
            line=dict(color=COLOR_THEME["success"], width=2)
        ))
        
        # Projeção
        if velocidade_media > 0 and semanas_restantes != float('inf'):
            ultima_semana = df_historico_resolucao["periodo"].iloc[-1]
            total_resolvidas = df_historico_resolucao["contagem"].sum()
            
            # Cria semanas futuras
            semanas_futuras = []
            for i in range(1, int(semanas_restantes) + 2):
                ultima_semana_partes = ultima_semana.split("-W")
                if len(ultima_semana_partes) == 2:
                    ano = int(ultima_semana_partes[0])
                    semana = int(ultima_semana_partes[1])
                    
                    semana += i
                    # Ajuste simples de ano (não lida com todas as situações de virada de ano)
                    if semana > 52:
                        semana = semana - 52
                        ano += 1
                    
                    semanas_futuras.append(f"{ano}-W{semana:02d}")
            
            # Cria projeção
            projecao_y = list(range(
                total_resolvidas, 
                total_resolvidas + int(velocidade_media * len(semanas_futuras)) + 1, 
                int(velocidade_media)
            ))
            
            if len(projecao_y) > len(semanas_futuras):
                projecao_y = projecao_y[:len(semanas_futuras)]
            elif len(projecao_y) < len(semanas_futuras):
                semanas_futuras = semanas_futuras[:len(projecao_y)]
            
            fig.add_trace(go.Scatter(
                x=semanas_futuras,
                y=projecao_y,
                mode="lines",
                name="Projeção",
                line=dict(color=COLOR_THEME["primary"], width=2, dash="dash")
            ))
    
    fig.update_layout(
        title="Projeção de Conclusão do Projeto",
        xaxis_title="Período",
        yaxis_title="Quantidade Acumulada",
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis_tickangle=-45,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig, data_conclusao_str


## Interface de Usuário

def configurar_sidebar():
    """Configura a barra lateral com opções de conexão e filtros."""
    st.sidebar.title("📊 Métricas Jira")
    
    # Inicializa o banco de dados
    initialize_db()
    
    # Verifica se já existe uma conexão
    configs_salvas = get_saved_jira_configs()
    
    if configs_salvas:
        st.sidebar.subheader("Conexões Salvas")
        
        nomes_config = [f"{cfg['email']} ({cfg['url']})" for cfg in configs_salvas]
        indice_selecionado = st.sidebar.selectbox(
            "Selecione uma conexão",
            range(len(nomes_config)),
            format_func=lambda i: nomes_config[i]
        )
        
        config_selecionada = configs_salvas[indice_selecionado]
        
        # Carregar configuração selecionada
        if st.sidebar.button("Carregar conexão"):
            st.session_state.config_id = config_selecionada["id"]
            st.session_state.jira_url = config_selecionada["url"]
            st.session_state.jira_email = config_selecionada["email"]
            
            # Solicitar o token (não é armazenado em texto puro)
            st.session_state.mostrar_token = True
    
    # Exibe campos para nova conexão
    st.sidebar.subheader("Nova Conexão")
    
    # Campos de conexão
    if "jira_url" not in st.session_state:
        st.session_state.jira_url = ""
    
    if "jira_email" not in st.session_state:
        st.session_state.jira_email = ""
    
    if "mostrar_token" not in st.session_state:
        st.session_state.mostrar_token = False
    
    # URL e Email
    jira_url = st.sidebar.text_input("URL do Jira", value=st.session_state.jira_url, placeholder="https://seudominio.atlassian.net")
    jira_email = st.sidebar.text_input("Email de acesso", value=st.session_state.jira_email)
    
    # Token
    if "mostrar_token" in st.session_state and st.session_state.mostrar_token:
        jira_token = st.sidebar.text_input("Token API", type="password")
        
        if st.sidebar.button("Conectar"):
            with st.spinner("Conectando ao Jira..."):
                sucesso, auth, headers = conectar_jira(jira_url, jira_email, jira_token)
                
                if sucesso:
                    # Salva a configuração no banco
                    config_id = save_jira_config(jira_url, jira_email, jira_token)
                    st.session_state.config_id = config_id
                    st.session_state.jira_autenticado = True
                    st.session_state.jira_auth = auth
                    st.session_state.jira_headers = headers
                    
                    # Busca projetos
                    sucesso_proj, projetos = buscar_projetos(jira_url, auth, headers)
                    if sucesso_proj:
                        save_jira_projects(config_id, projetos)
                        st.session_state.jira_projetos = projetos
                        st.sidebar.success(f"Conectado com sucesso! {len(projetos)} projetos encontrados.")
                    else:
                        st.sidebar.warning("Conectado, mas não foi possível listar projetos.")
                else:
                    st.sidebar.error("Falha na conexão. Verifique as credenciais.")
    else:
        if st.sidebar.button("Adicionar nova conexão"):
            st.session_state.mostrar_token = True
    
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

def exibir_filtros(projeto_key=None):
    """Exibe filtros de data e outros filtros relevantes."""
    st.markdown("""
    <h3 class="section-title">Filtros</h3>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        data_inicio = st.date_input(
            "Data Inicial",
            value=datetime.now() - timedelta(days=90),
            key="data_inicio"
        )
    
    with col2:
        data_fim = st.date_input(
            "Data Final",
            value=datetime.now(),
            key="data_fim"
        )
    
    # Sprint para burndown
    st.markdown("### Sprint (para Burndown)")
    col1, col2 = st.columns(2)
    
    with col1:
        sprint_inicio = st.date_input(
            "Início da Sprint",
            value=datetime.now() - timedelta(days=14),
            key="sprint_inicio"
        )
    
    with col2:
        sprint_fim = st.date_input(
            "Fim da Sprint",
            value=datetime.now() + timedelta(days=14),
            key="sprint_fim"
        )
    
    # Constrói o filtro JQL
    jql_filtro = f'created >= "{data_inicio.strftime("%Y-%m-%d")}" AND created <= "{data_fim.strftime("%Y-%m-%d")}"'
    
    if projeto_key:
        jql_filtro = f'project = "{projeto_key}" AND {jql_filtro}'
    
    return jql_filtro, data_inicio, data_fim, sprint_inicio, sprint_fim

def exibir_visao_geral(df, metricas):
    """Exibe visão geral do projeto com métricas principais."""
    if not isinstance(df, pd.DataFrame) or df.empty:
        st.info("Não há dados para exibir. Tente ajustar os filtros ou atualizar os dados.")
        return
    
    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(
            criar_card_metrica(
                metricas["total_issues"], 
                "Total de Issues", 
                COLOR_THEME["primary"]
            ), 
            unsafe_allow_html=True
        )
    
    with col2:
        st.markdown(
            criar_card_metrica(
                metricas["issues_por_status"].get("Pendente", 0), 
                "Issues Pendentes", 
                STATUS_COLORS["Pendente"]
            ), 
            unsafe_allow_html=True
        )
    
    with col3:
        st.markdown(
            criar_card_metrica(
                metricas["issues_por_status"].get("Em Progresso", 0) + metricas["issues_por_status"].get("Em Revisão", 0), 
                "Em Andamento", 
                STATUS_COLORS["Em Progresso"]
            ), 
            unsafe_allow_html=True
        )
    
    with col4:
        st.markdown(
            criar_card_metrica(
                metricas["issues_por_status"].get("Concluído", 0), 
                "Concluídas", 
                STATUS_COLORS["Concluído"]
            ), 
            unsafe_allow_html=True
        )
    
    # Segunda linha de métricas
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(
            criar_card_metrica(
                f"{metricas['percentual_concluido']:.1f}%", 
                "Progresso do Projeto", 
                COLOR_THEME["primary"]
            ), 
            unsafe_allow_html=True
        )
        st.markdown(criar_barra_progresso(metricas["percentual_concluido"], COLOR_THEME["primary"]), unsafe_allow_html=True)
    
    with col2:
        if metricas["tempo_medio_resolucao"] is not None:
            st.markdown(
                criar_card_metrica(
                    f"{metricas['tempo_medio_resolucao']:.1f}", 
                    "Tempo Médio de Resolução (dias)", 
                    COLOR_THEME["secondary"]
                ), 
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                criar_card_metrica(
                    "N/A", 
                    "Tempo Médio de Resolução (dias)", 
                    COLOR_THEME["neutral"]
                ), 
                unsafe_allow_html=True
            )
    
    # Gráficos principais
    col1, col2 = st.columns(2)
    
    with col1:
        # Distribuição por status
        df_status = df["status"].value_counts().reset_index(name="contagem")
        if not df_status.empty:
            fig_status = criar_grafico_status(df_status)
            st.plotly_chart(fig_status, use_container_width=True)
    
    with col2:
        # Tendência de criação vs resolução
        col_a, col_b = st.columns(2)
        with col_a:
            periodo = st.radio("Agrupar por:", ["Semana", "Mês"], horizontal=True)
        
        agrupar_func = agrupar_por_semana if periodo == "Semana" else agrupar_por_mes
        
        df_criacao = agrupar_func(df, "data_criacao")
        df_resolucao = agrupar_func(df[df["data_resolucao"].notna()], "data_resolucao")
        
        if not df_criacao.empty:
            # Cria um gráfico combinado
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=df_criacao["periodo"],
                y=df_criacao["contagem"],
                name="Criadas",
                marker_color=COLOR_THEME["primary"]
            ))
            
            if not df_resolucao.empty:
                fig.add_trace(go.Bar(
                    x=df_resolucao["periodo"],
                    y=df_resolucao["contagem"],
                    name="Resolvidas",
                    marker_color=COLOR_THEME["success"]
                ))
            
            fig.update_layout(
                title=f"Issues Criadas vs Resolvidas por {periodo}",
                barmode='group',
                xaxis_title="",
                yaxis_title="Quantidade",
                plot_bgcolor="white",
                paper_bgcolor="white",
                margin=dict(l=10, r=10, t=40, b=10),
                xaxis_tickangle=-45,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            st.plotly_chart(fig, use_container_width=True)

def exibir_progresso_projeto(df):
    """Exibe detalhes sobre o progresso do projeto."""
    if not isinstance(df, pd.DataFrame) or df.empty:
        st.info("Não há dados para exibir. Tente ajustar os filtros ou atualizar os dados.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Burndown de todo o projeto
        fig_burndown, data_conclusao = criar_grafico_previsao_conclusao(df)
        st.plotly_chart(fig_burndown, use_container_width=True)
        
        if data_conclusao:
            st.info(f"**Data estimada de conclusão:** {data_conclusao}")
    
    with col2:
        # Velocidade da equipe
        fig_velocidade = criar_grafico_velocidade_equipe(df)
        st.plotly_chart(fig_velocidade, use_container_width=True)
    
    # Distribuição por tipo
    col1, col2 = st.columns(2)
    
    with col1:
        # Distribuição por tipo de issue
        df_tipo = df["tipo"].value_counts().reset_index(name="contagem")
        if not df_tipo.empty:
            fig_tipo = px.pie(
                df_tipo,
                names="index",
                values="contagem",
                title="Distribuição por Tipo de Issue",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_tipo.update_layout(
                plot_bgcolor="white",
                paper_bgcolor="white",
                margin=dict(l=10, r=10, t=40, b=10)
            )
            st.plotly_chart(fig_tipo, use_container_width=True)
    
    with col2:
        # Distribuição por prioridade
        if "prioridade" in df.columns:
            df_prioridade = df["prioridade"].value_counts().reset_index(name="contagem")
            if not df_prioridade.empty:
                fig_prioridade = px.pie(
                    df_prioridade,
                    names="index",
                    values="contagem",
                    title="Distribuição por Prioridade",
                    color_discrete_sequence=px.colors.qualitative.Bold
                )
                fig_prioridade.update_layout(
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                    margin=dict(l=10, r=10, t=40, b=10)
                )
                st.plotly_chart(fig_prioridade, use_container_width=True)
    
    # Distribuição do trabalho pela equipe
    st.markdown("### Distribuição do Trabalho")
    fig_dist = criar_grafico_distribuicao_trabalho(df)
    st.plotly_chart(fig_dist, use_container_width=True)

def exibir_metricas_sprint(df, sprint_inicio, sprint_fim):
    """Exibe métricas específicas da sprint."""
    if not isinstance(df, pd.DataFrame) or df.empty:
        st.info("Não há dados para exibir. Tente ajustar os filtros ou atualizar os dados.")
        return
    
    # Filtra issues da sprint
    df_sprint = df[
        (df["data_criacao"] >= pd.to_datetime(sprint_inicio)) & 
        (df["data_criacao"] <= pd.to_datetime(sprint_fim))
    ].copy()
    
    if df_sprint.empty:
        st.info("Não há issues na sprint selecionada. Tente ajustar as datas da sprint.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Burndown chart
        fig_burndown = criar_grafico_burndown(df, sprint_inicio, sprint_fim)
        st.plotly_chart(fig_burndown, use_container_width=True)
    
    with col2:
        # Métricas da sprint
        total_sprint = len(df_sprint)
        concluidas = df_sprint[df_sprint["status"] == "Concluído"].shape[0]
        percentual = (concluidas / total_sprint * 100) if total_sprint > 0 else 0
        
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown(
                criar_card_metrica(
                    total_sprint, 
                    "Total de Issues na Sprint", 
                    COLOR_THEME["primary"]
                ), 
                unsafe_allow_html=True
            )
        
        with col_b:
            st.markdown(
                criar_card_metrica(
                    concluidas, 
                    "Issues Concluídas", 
                    STATUS_COLORS["Concluído"]
                ), 
                unsafe_allow_html=True
            )
        
        st.markdown("### Progresso da Sprint")
        st.markdown(
            criar_card_metrica(
                f"{percentual:.1f}%", 
                "Progresso da Sprint", 
                COLOR_THEME["primary"]
            ), 
            unsafe_allow_html=True
        )
        st.markdown(criar_barra_progresso(percentual, COLOR_THEME["primary"]), unsafe_allow_html=True)
        
        # Status na sprint
        df_status_sprint = df_sprint["status"].value_counts().reset_index(name="contagem")
        if not df_status_sprint.empty:
            fig_status_sprint = criar_grafico_status(df_status_sprint, "Status das Issues na Sprint")
            st.plotly_chart(fig_status_sprint, use_container_width=True)
    
    # Distribuição por responsável na sprint
    st.markdown("### Distribuição por Responsável na Sprint")
    df_resp_sprint = df_sprint[df_sprint["responsavel"] != "Não atribuído"].copy()
    
    if not df_resp_sprint.empty:
        fig_resp = px.bar(
            df_resp_sprint.groupby("responsavel").size().reset_index(name="contagem"),
            x="responsavel",
            y="contagem",
            title="Issues por Responsável na Sprint",
            color_discrete_sequence=[COLOR_THEME["primary"]]
        )
        fig_resp.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(l=10, r=10, t=40, b=10),
            xaxis_title="",
            yaxis_title="Quantidade",
            xaxis_tickangle=-45
        )
        st.plotly_chart(fig_resp, use_container_width=True)

def exibir_metricas_usuario(df):
    """Exibe métricas por usuário."""
    if not isinstance(df, pd.DataFrame) or df.empty:
        st.info("Não há dados para exibir. Tente ajustar os filtros ou atualizar os dados.")
        return
    
    # Calcula métricas por usuário
    df_usuario = calcular_metricas_usuario(df)
    
    if df_usuario.empty:
        st.info("Não há dados de usuários para exibir.")
        return
    
    # Seleção de período
    col1, col2 = st.columns([1, 3])
    
    with col1:
        periodo = st.radio("Visualizar por:", ["Geral", "Semana", "Mês"])
    
    # Exibe métricas gerais
    if periodo == "Geral":
        col1, col2 = st.columns(2)
        
        with col1:
            # Top usuários por total de issues
            fig_total = criar_grafico_desempenho_usuario(
                df_usuario, 
                "total_issues", 
                10, 
                "Top Usuários por Volume de Issues"
            )
            st.plotly_chart(fig_total, use_container_width=True)
        
        with col2:
            # Top usuários por percentual concluído
            if "percentual_concluido" in df_usuario.columns:
                fig_perc = criar_grafico_desempenho_usuario(
                    df_usuario, 
                    "percentual_concluido", 
                    10, 
                    "Top Usuários por % de Conclusão"
                )
                st.plotly_chart(fig_perc, use_container_width=True)
        
        # Tempo médio de resolução por usuário
        if "tempo_medio_resolucao" in df_usuario.columns:
            fig_tempo = criar_grafico_desempenho_usuario(
                df_usuario.dropna(subset=["tempo_medio_resolucao"]), 
                "tempo_medio_resolucao", 
                10, 
                "Tempo Médio de Resolução por Usuário (dias)"
            )
            st.plotly_chart(fig_tempo, use_container_width=True)
    
    # Exibe métricas por período
    else:
        # Métricas por período selecionado
        titulo = f"Atividade por Usuário (por {periodo.lower()})"
        fig_heatmap = criar_heatmap_atividade_usuario(df, periodo.lower(), titulo)
        st.plotly_chart(fig_heatmap, use_container_width=True)
        
        # Calculando resumo por período
        df_periodo = calcular_metricas_usuario_periodo(df, periodo.lower())
        
        if not df_periodo.empty and "responsavel" in df_periodo.columns:
            col1, col2 = st.columns(2)
            
            with col1:
                # Issues criadas por período
                fig_criadas = px.bar(
                    df_periodo.sort_values("issues_criadas", ascending=False).head(10),
                    x="responsavel",
                    y="issues_criadas",
                    title=f"Top Usuários por Issues Criadas ({periodo})",
                    color_discrete_sequence=[COLOR_THEME["primary"]]
                )
                fig_criadas.update_layout(
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                    margin=dict(l=10, r=10, t=40, b=10),
                    xaxis_title="",
                    yaxis_title="Quantidade",
                    xaxis_tickangle=-45
                )
                st.plotly_chart(fig_criadas, use_container_width=True)
            
            with col2:
                # Issues resolvidas por período
                if "issues_resolvidas" in df_periodo.columns:
                    fig_resolvidas = px.bar(
                        df_periodo.sort_values("issues_resolvidas", ascending=False).head(10),
                        x="responsavel",
                        y="issues_resolvidas",
                        title=f"Top Usuários por Issues Resolvidas ({periodo})",
                        color_discrete_sequence=[COLOR_THEME["success"]]
                    )
                    fig_resolvidas.update_layout(
                        plot_bgcolor="white",
                        paper_bgcolor="white",
                        margin=dict(l=10, r=10, t=40, b=10),
                        xaxis_title="",
                        yaxis_title="Quantidade",
                        xaxis_tickangle=-45
                    )
                    st.plotly_chart(fig_resolvidas, use_container_width=True)
    
    # Exibe tabela de detalhes
    with st.expander("Ver detalhes de desempenho por usuário"):
        if not df_usuario.empty:
            st.dataframe(df_usuario.sort_values("total_issues", ascending=False), use_container_width=True)

def exibir_detalhes_issues(df):
    """Exibe dados brutos e detalhes das issues."""
    if not isinstance(df, pd.DataFrame) or df.empty:
        st.info("Não há dados para exibir. Tente ajustar os filtros ou atualizar os dados.")
        return
    
    # Filtros para a tabela
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.multiselect(
            "Filtrar por Status",
            options=sorted(df["status"].unique()),
            default=[]
        )
    
    with col2:
        if "tipo" in df.columns:
            tipo_filter = st.multiselect(
                "Filtrar por Tipo",
                options=sorted(df["tipo"].unique()),
                default=[]
            )
        else:
            tipo_filter = []
    
    with col3:
        if "responsavel" in df.columns:
            resp_filter = st.multiselect(
                "Filtrar por Responsável",
                options=sorted(df["responsavel"].unique()),
                default=[]
            )
        else:
            resp_filter = []
    
    # Aplica filtros
    df_filtrado = df.copy()
    
    if status_filter:
        df_filtrado = df_filtrado[df_filtrado["status"].isin(status_filter)]
    
    if tipo_filter:
        df_filtrado = df_filtrado[df_filtrado["tipo"].isin(tipo_filter)]
    
    if resp_filter:
        df_filtrado = df_filtrado[df_filtrado["responsavel"].isin(resp_filter)]
    
    # Exibe dados filtrados
    st.markdown(f"### Issues ({len(df_filtrado)} resultados)")
    
    if not df_filtrado.empty:
        # Seleciona colunas para exibir
        colunas = ["key", "summary", "status", "tipo", "responsavel", "data_criacao", "data_resolucao"]
        colunas_disponiveis = [col for col in colunas if col in df_filtrado.columns]
        
        st.dataframe(df_filtrado[colunas_disponiveis], use_container_width=True)
        
        # Botão para download
        csv = df_filtrado.to_csv(index=False).encode('utf-8')
        st.download_button(
            "Download CSV",
            csv,
            "jira_issues.csv",
            "text/csv",
            key='download-csv'
        )

def main():
    """Função principal do dashboard."""
    set_custom_css()
    
    # Configura a barra lateral
    configurar_sidebar()
    
    # Verifica se está autenticado
    if "jira_autenticado" not in st.session_state:
        st.session_state.jira_autenticado = False
    
    if not st.session_state.jira_autenticado:
        # Define informações sobre configuração e projetos
        if ("config_id" in st.session_state and 
            "jira_token" in st.session_state and 
            "jira_url" in st.session_state and 
            "jira_email" in st.session_state):
            
            # Tenta autenticar
            sucesso, auth, headers = conectar_jira(
                st.session_state.jira_url, 
                st.session_state.jira_email, 
                st.session_state.jira_token
            )
            
            if sucesso:
                st.session_state.jira_autenticado = True
                st.session_state.jira_auth = auth
                st.session_state.jira_headers = headers
                
                # Carrega projetos
                if "jira_projetos" not in st.session_state:
                    projetos = get_jira_projects(st.session_state.config_id)
                    if projetos:
                        st.session_state.jira_projetos = projetos
                    else:
                        # Tenta buscar projetos da API
                        sucesso_proj, projetos = buscar_projetos(
                            st.session_state.jira_url, 
                            auth, 
                            headers
                        )
                        if sucesso_proj:
                            save_jira_projects(st.session_state.config_id, projetos)
                            st.session_state.jira_projetos = projetos
    
    # Se autenticado, exibe o dashboard
    if st.session_state.jira_autenticado:
        # Título principal
        st.markdown("# 📊 Métricas Jira")
        
        # Seleciona projeto
        if "jira_projetos" in st.session_state and st.session_state.jira_projetos:
            projeto_options = {p.get("name"): p.get("key") for p in st.session_state.jira_projetos}
            projeto_selecionado = st.selectbox(
                "Selecione um Projeto",
                options=list(projeto_options.keys())
            )
            
            projeto_key = projeto_options.get(projeto_selecionado)
            
            # Exibe cabeçalho do projeto
            st.markdown(f"""
            <div class="project-header">
                <h3 class="project-title">{projeto_selecionado}</h3>
                <p class="project-subtitle">Chave: {projeto_key}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Exibe filtros e obtém JQL
            jql_filtro, data_inicio, data_fim, sprint_inicio, sprint_fim = exibir_filtros(projeto_key)
            
            # Botão para atualizar dados
            if st.button("Atualizar Dados"):
                with st.spinner("Buscando dados do Jira..."):
                    sucesso, dados_issues = buscar_issues(
                        st.session_state.jira_url, 
                        st.session_state.jira_auth, 
                        st.session_state.jira_headers, 
                        jql_filtro
                    )
                    
                    if sucesso:
                        # Extrair dados e armazenar no state
                        df_issues = extrair_campos_issues(dados_issues)
                        st.session_state.df_issues = df_issues
                        st.success(f"{len(df_issues)} issues encontradas!")
                    else:
                        st.error("Falha ao buscar issues. Verifique o filtro JQL.")
            
            # Exibe o dashboard se houver dados
            if "df_issues" in st.session_state and not st.session_state.df_issues.empty:
                df = st.session_state.df_issues
                
                # Calcula métricas gerais
                metricas = calcular_metricas_gerais(df)
                
                # Tabs para diferentes visualizações
                tab_geral, tab_progresso, tab_sprint, tab_equipe, tab_dados = st.tabs([
                    "Visão Geral",
                    "Progresso do Projeto",
                    "Sprint",
                    "Desempenho da Equipe",
                    "Dados"
                ])
                
                with tab_geral:
                    exibir_visao_geral(df, metricas)
                
                with tab_progresso:
                    exibir_progresso_projeto(df)
                
                with tab_sprint:
                    exibir_metricas_sprint(df, sprint_inicio, sprint_fim)
                
                with tab_equipe:
                    exibir_metricas_usuario(df)
                
                with tab_dados:
                    exibir_detalhes_issues(df)
            
            elif st.session_state.jira_autenticado:
                # Exibe mensagem se não há dados
                st.info("Selecione um projeto e clique em 'Atualizar Dados' para visualizar as métricas.")
        
        else:
            st.warning("Não foi possível encontrar projetos. Verifique sua conexão com o Jira.")
    
    else:
        # Exibe tela inicial com instruções
        st.markdown("""
        <div class="content-container">
            <h3>Dashboard de Métricas do Jira</h3>
            <p>Este dashboard permite visualizar métricas e estatísticas de projetos do Jira, incluindo:</p>
            <ul>
                <li>Visão geral do projeto com distribuição por status e tendências</li>
                <li>Progresso do projeto e previsão de conclusão</li>
                <li>Burndown chart para acompanhamento de sprints</li>
                <li>Desempenho individual e por equipe</li>
                <li>Resumos semanais e mensais por usuário</li>
            </ul>
            <p>Para começar, configure a conexão com a API do Jira no painel lateral.</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div class="content-container">
                <h4>Recursos principais:</h4>
                <ul>
                    <li>Conexão persistente com o Jira (sem necessidade de reconectar)</li>
                    <li>Interface limpa e minimalista</li>
                    <li>Gráficos interativos</li>
                    <li>Análise por usuário</li>
                    <li>Previsão de conclusão do projeto</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="content-container">
                <h4>Como usar:</h4>
                <ol>
                    <li>Conecte-se ao Jira com suas credenciais</li>
                    <li>Selecione um projeto</li>
                    <li>Defina o período de análise</li>
                    <li>Clique em "Atualizar Dados"</li>
                    <li>Navegue pelas diferentes abas para explorar as métricas</li>
                </ol>
            </div>
            """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()