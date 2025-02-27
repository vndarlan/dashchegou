import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Obter variáveis de ambiente para o PostgreSQL (Railway)
DB_URL = os.getenv("DATABASE_URL", "")

# Estrutura da tabela de calendários
CREATE_TABLE_QUERY = """
CREATE TABLE IF NOT EXISTS calendarios (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

class Database:
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
                    database="calendario_app",
                    user="postgres",
                    password="postgres"
                )
            else:
                # Conectar usando DATABASE_URL do Railway
                self.conn = psycopg2.connect(DB_URL)
                
            # Criar tabela se não existir
            cursor = self.conn.cursor()
            cursor.execute(CREATE_TABLE_QUERY)
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
    
    def get_all_calendarios(self):
        """Retorna todos os calendários cadastrados"""
        try:
            if not self.conn:
                self.connect()
                
            cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT id, nome, email FROM calendarios ORDER BY nome")
            calendarios = cursor.fetchall()
            cursor.close()
            
            # Converter para lista de dicionários
            result = [dict(cal) for cal in calendarios]
            return result
        except Exception as e:
            print(f"Erro ao obter calendários: {e}")
            return []
    
    def add_calendario(self, nome, email):
        """Adiciona um novo calendário"""
        try:
            if not self.conn:
                self.connect()
                
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO calendarios (nome, email) VALUES (%s, %s) RETURNING id",
                (nome, email)
            )
            id_calendario = cursor.fetchone()[0]
            self.conn.commit()
            cursor.close()
            
            return id_calendario
        except psycopg2.errors.UniqueViolation:
            # Email já existe
            self.conn.rollback()
            return -1
        except Exception as e:
            print(f"Erro ao adicionar calendário: {e}")
            self.conn.rollback()
            return 0
    
    def remove_calendario(self, id_calendario):
        """Remove um calendário pelo ID"""
        try:
            if not self.conn:
                self.connect()
                
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM calendarios WHERE id = %s", (id_calendario,))
            self.conn.commit()
            cursor.close()
            
            return True
        except Exception as e:
            print(f"Erro ao remover calendário: {e}")
            self.conn.rollback()
            return False