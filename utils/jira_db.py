import sqlite3
import os
from pathlib import Path
import hashlib
from datetime import datetime
import json

# Caminho para o banco de dados
DB_PATH = Path("./jira_config.db")

def initialize_db():
    """Inicializa o banco de dados para armazenar configurações do Jira"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Tabela para armazenar configurações de conexão
    c.execute('''
    CREATE TABLE IF NOT EXISTS jira_config (
        id INTEGER PRIMARY KEY,
        url TEXT NOT NULL,
        email TEXT NOT NULL,
        token_hash TEXT NOT NULL,
        last_used TIMESTAMP
    )
    ''')
    
    # Tabela para armazenar projetos por configuração
    c.execute('''
    CREATE TABLE IF NOT EXISTS jira_projects (
        id INTEGER PRIMARY KEY,
        config_id INTEGER,
        project_key TEXT NOT NULL,
        project_name TEXT NOT NULL,
        FOREIGN KEY (config_id) REFERENCES jira_config (id)
    )
    ''')
    
    # Tabela para armazenar sprints por projeto
    c.execute('''
    CREATE TABLE IF NOT EXISTS jira_sprints (
        id INTEGER PRIMARY KEY,
        config_id INTEGER,
        project_key TEXT NOT NULL,
        sprint_id TEXT NOT NULL,
        sprint_name TEXT NOT NULL,
        start_date TIMESTAMP,
        end_date TIMESTAMP,
        FOREIGN KEY (config_id) REFERENCES jira_config (id)
    )
    ''')
    
    # Tabela para cache de dados
    c.execute('''
    CREATE TABLE IF NOT EXISTS jira_cache (
        id INTEGER PRIMARY KEY,
        config_id INTEGER,
        project_key TEXT NOT NULL,
        query_hash TEXT NOT NULL,
        data BLOB,
        timestamp TIMESTAMP,
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

def update_last_used(config_id):
    """Atualiza a data de último uso de uma configuração"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE jira_config SET last_used = ? WHERE id = ?', (datetime.now(), config_id))
    conn.commit()
    conn.close()

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

def save_jira_sprints(config_id, project_key, sprints):
    """Salva as sprints do Jira no banco de dados"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Remove sprints existentes para este projeto
    c.execute('DELETE FROM jira_sprints WHERE config_id = ? AND project_key = ?', (config_id, project_key))
    
    # Insere novas sprints
    for sprint in sprints:
        start_date = sprint.get('startDate')
        end_date = sprint.get('endDate')
        
        c.execute('''
        INSERT INTO jira_sprints (config_id, project_key, sprint_id, sprint_name, start_date, end_date)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (config_id, project_key, sprint.get('id'), sprint.get('name'), start_date, end_date))
    
    conn.commit()
    conn.close()

def get_jira_sprints(config_id, project_key):
    """Recupera as sprints salvas para um projeto"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
    SELECT sprint_id, sprint_name, start_date, end_date
    FROM jira_sprints
    WHERE config_id = ? AND project_key = ?
    ORDER BY start_date DESC
    ''', (config_id, project_key))
    
    sprints = []
    for row in c.fetchall():
        sprints.append({
            'id': row[0],
            'name': row[1],
            'startDate': row[2],
            'endDate': row[3]
        })
    
    conn.close()
    return sprints

def cache_jira_data(config_id, project_key, query, data):
    """Armazena dados do Jira em cache"""
    # Cria hash da query para identificação
    query_hash = hashlib.md5(query.encode()).hexdigest()
    
    # Serializa os dados
    data_blob = json.dumps(data).encode()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Verifica se já existe cache para esta query
    c.execute('''
    SELECT id FROM jira_cache 
    WHERE config_id = ? AND project_key = ? AND query_hash = ?
    ''', (config_id, project_key, query_hash))
    
    result = c.fetchone()
    
    if result:
        # Atualiza cache existente
        c.execute('''
        UPDATE jira_cache
        SET data = ?, timestamp = ?
        WHERE id = ?
        ''', (data_blob, datetime.now(), result[0]))
    else:
        # Insere novo cache
        c.execute('''
        INSERT INTO jira_cache (config_id, project_key, query_hash, data, timestamp)
        VALUES (?, ?, ?, ?, ?)
        ''', (config_id, project_key, query_hash, data_blob, datetime.now()))
    
    conn.commit()
    conn.close()

def get_cached_jira_data(config_id, project_key, query, max_age_minutes=60):
    """Recupera dados em cache do Jira se não estiverem expirados"""
    # Cria hash da query para identificação
    query_hash = hashlib.md5(query.encode()).hexdigest()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Busca cache não expirado
    c.execute('''
    SELECT data, timestamp FROM jira_cache
    WHERE config_id = ? AND project_key = ? AND query_hash = ?
    ''', (config_id, project_key, query_hash))
    
    result = c.fetchone()
    
    if result:
        data_blob, timestamp = result
        cache_time = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f')
        age_minutes = (datetime.now() - cache_time).total_seconds() / 60
        
        # Verifica se o cache não expirou
        if age_minutes <= max_age_minutes:
            try:
                # Deserializa e retorna os dados
                return json.loads(data_blob.decode())
            except:
                pass
    
    conn.close()
    return None

def clear_expired_cache(max_age_days=7):
    """Limpa cache expirado"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Calcula timestamp limite
    limit_date = datetime.now() - datetime.timedelta(days=max_age_days)
    
    # Remove caches antigos
    c.execute('''
    DELETE FROM jira_cache
    WHERE timestamp < ?
    ''', (limit_date,))
    
    conn.commit()
    conn.close()

# Inicializa o banco de dados ao importar o módulo
if __name__ == "__main__":
    initialize_db()
    print(f"Banco de dados inicializado em {DB_PATH}")