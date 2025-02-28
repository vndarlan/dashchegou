import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta

# Obter variáveis de ambiente para o PostgreSQL (Railway)
DB_URL = os.getenv("DATABASE_URL", "")

# Estrutura da tabela de configurações Jira
CREATE_CONFIG_TABLE_QUERY = """
CREATE TABLE IF NOT EXISTS jira_configs (
    id SERIAL PRIMARY KEY,
    jira_url VARCHAR(255) NOT NULL,
    jira_token VARCHAR(255) NOT NULL,
    jira_email VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Estrutura da tabela de projetos monitorados
CREATE_PROJECTS_TABLE_QUERY = """
CREATE TABLE IF NOT EXISTS jira_projects (
    id SERIAL PRIMARY KEY,
    project_key VARCHAR(50) NOT NULL,
    project_name VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Estrutura da tabela de cache de dados Jira (para otimização)
CREATE_CACHE_TABLE_QUERY = """
CREATE TABLE IF NOT EXISTS jira_cache (
    id SERIAL PRIMARY KEY,
    query_hash VARCHAR(64) NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    UNIQUE(query_hash)
);
"""

class JiraDatabase:
    def __init__(self):
        self.conn = None
        
    def connect(self):
        """Conecta ao banco de dados PostgreSQL"""
        try:
            # Se estiver rodando localmente e não tiver variável de ambiente
            if not DB_URL:
                # Configurações locais de fallback
                self.conn = psycopg2.connect(
                    host="localhost",
                    database="jira_dashboard",
                    user="postgres",
                    password="postgres"
                )
            else:
                # Conectar usando DATABASE_URL do Railway
                self.conn = psycopg2.connect(DB_URL)
                
            # Criar tabelas se não existirem
            cursor = self.conn.cursor()
            cursor.execute(CREATE_CONFIG_TABLE_QUERY)
            cursor.execute(CREATE_PROJECTS_TABLE_QUERY)
            cursor.execute(CREATE_CACHE_TABLE_QUERY)
            self.conn.commit()
            cursor.close()
            
            return True
        except Exception as e:
            print(f"Erro ao conectar ao banco de dados: {e}")
            # Se não conseguir conectar, vamos usar o modo local
            return False
    
    def close(self):
        """Fecha a conexão com o banco de dados"""
        if self.conn:
            self.conn.close()
    
    # ====== MÉTODOS PARA CONFIGURAÇÃO JIRA ======
    
    def get_jira_config(self):
        """Retorna a configuração do Jira (apenas a mais recente)"""
        try:
            if not self.conn:
                self.connect()
                
            cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT id, jira_url, jira_email, jira_token FROM jira_configs ORDER BY created_at DESC LIMIT 1")
            config = cursor.fetchone()
            cursor.close()
            
            if config:
                return dict(config)
            return None
        except Exception as e:
            print(f"Erro ao obter configuração Jira: {e}")
            return None
    
    def save_jira_config(self, jira_url, jira_email, jira_token):
        """Salva ou atualiza a configuração do Jira"""
        try:
            if not self.conn:
                self.connect()
                
            # Verificar se já existe uma configuração
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM jira_configs")
            count = cursor.fetchone()[0]
            
            if count > 0:
                # Atualizar a configuração existente
                cursor.execute(
                    """
                    UPDATE jira_configs 
                    SET jira_url = %s, jira_email = %s, jira_token = %s, updated_at = %s 
                    WHERE id = (SELECT id FROM jira_configs ORDER BY created_at DESC LIMIT 1)
                    """,
                    (jira_url, jira_email, jira_token, datetime.now())
                )
            else:
                # Inserir nova configuração
                cursor.execute(
                    "INSERT INTO jira_configs (jira_url, jira_email, jira_token) VALUES (%s, %s, %s)",
                    (jira_url, jira_email, jira_token)
                )
            
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            print(f"Erro ao salvar configuração Jira: {e}")
            self.conn.rollback()
            return False
    
    # ====== MÉTODOS PARA PROJETOS ======
    
    def get_all_projects(self):
        """Retorna todos os projetos cadastrados"""
        try:
            if not self.conn:
                self.connect()
                
            cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT id, project_key, project_name, is_active FROM jira_projects ORDER BY project_name")
            projects = cursor.fetchall()
            cursor.close()
            
            # Converter para lista de dicionários
            result = [dict(project) for project in projects]
            return result
        except Exception as e:
            print(f"Erro ao obter projetos: {e}")
            return []
    
    def add_project(self, project_key, project_name):
        """Adiciona um novo projeto para monitoramento"""
        try:
            if not self.conn:
                self.connect()
                
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO jira_projects (project_key, project_name) VALUES (%s, %s) RETURNING id",
                (project_key, project_name)
            )
            project_id = cursor.fetchone()[0]
            self.conn.commit()
            cursor.close()
            
            return project_id
        except psycopg2.errors.UniqueViolation:
            # Projeto já existe
            self.conn.rollback()
            return -1
        except Exception as e:
            print(f"Erro ao adicionar projeto: {e}")
            self.conn.rollback()
            return 0
    
    def remove_project(self, project_id):
        """Remove um projeto pelo ID"""
        try:
            if not self.conn:
                self.connect()
                
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM jira_projects WHERE id = %s", (project_id,))
            self.conn.commit()
            cursor.close()
            
            return True
        except Exception as e:
            print(f"Erro ao remover projeto: {e}")
            self.conn.rollback()
            return False
            
    def toggle_project_status(self, project_id, is_active):
        """Altera o status de um projeto (ativo/inativo)"""
        try:
            if not self.conn:
                self.connect()
                
            cursor = self.conn.cursor()
            cursor.execute(
                "UPDATE jira_projects SET is_active = %s WHERE id = %s",
                (is_active, project_id)
            )
            self.conn.commit()
            cursor.close()
            
            return True
        except Exception as e:
            print(f"Erro ao atualizar status do projeto: {e}")
            self.conn.rollback()
            return False
    
    # ====== MÉTODOS PARA CACHE ======
    
    def get_cache(self, query_hash):
        """Recupera dados em cache se não estiverem expirados"""
        try:
            if not self.conn:
                self.connect()
                
            cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                "SELECT data FROM jira_cache WHERE query_hash = %s AND expires_at > %s",
                (query_hash, datetime.now())
            )
            cache = cursor.fetchone()
            cursor.close()
            
            if cache:
                return cache["data"]
            return None
        except Exception as e:
            print(f"Erro ao recuperar cache: {e}")
            return None
    
    def set_cache(self, query_hash, data, expires_in_hours=24):
        """Armazena dados em cache com expiração"""
        try:
            if not self.conn:
                self.connect()
                
            expires_at = datetime.now() + timedelta(hours=expires_in_hours)
            
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO jira_cache (query_hash, data, expires_at) 
                VALUES (%s, %s, %s)
                ON CONFLICT (query_hash) 
                DO UPDATE SET data = %s, expires_at = %s, created_at = %s
                """,
                (query_hash, psycopg2.extras.Json(data), expires_at, 
                 psycopg2.extras.Json(data), expires_at, datetime.now())
            )
            self.conn.commit()
            cursor.close()
            
            return True
        except Exception as e:
            print(f"Erro ao definir cache: {e}")
            self.conn.rollback()
            return False
    
    def clear_cache(self):
        """Limpa todo o cache armazenado"""
        try:
            if not self.conn:
                self.connect()
                
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM jira_cache")
            self.conn.commit()
            cursor.close()
            
            return True
        except Exception as e:
            print(f"Erro ao limpar cache: {e}")
            self.conn.rollback()
            return False