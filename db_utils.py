# db_utils.py
import os
import datetime
import pandas as pd

def get_connection():
    """
    Returns database connection (PostgreSQL on Railway or SQLite locally)
    """
    DATABASE_URL = os.getenv("DATABASE_URL")
    if DATABASE_URL:
        import psycopg2
        return psycopg2.connect(DATABASE_URL)
    else:
        import sqlite3
        return sqlite3.connect("projetos.db", check_same_thread=False)

def execute_query(cursor, query, params=None):
    """
    Executes a query with proper placeholders for PostgreSQL/SQLite
    """
    if params is None:
        params = ()
    if os.getenv("DATABASE_URL"):
        query = query.replace("?", "%s")
    cursor.execute(query, params)

def init_db():
    """
    Initializes database with projects table
    """
    conn = get_connection()
    c = conn.cursor()
    query = '''
        CREATE TABLE IF NOT EXISTS projetos (
            id SERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            data_projeto TEXT NOT NULL,
            data_finalizacao TEXT,
            descricao TEXT,
            status TEXT,
            link_projeto TEXT,
            ferramentas TEXT,
            versao TEXT,
            criadores TEXT
        )
    '''
    execute_query(c, query)
    conn.commit()
    conn.close()

def load_data():
    """
    Loads project data as DataFrame
    """
    conn = get_connection()
    query = '''
        SELECT 
            id,
            nome, 
            data_projeto as data, 
            data_finalizacao, 
            descricao, 
            status, 
            link_projeto, 
            ferramentas, 
            versao, 
            criadores
        FROM projetos
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if not df.empty:
        df['data'] = pd.to_datetime(df['data'], errors='coerce')
        data_padrao = pd.Timestamp(datetime.date.today())
        df['data'] = df['data'].fillna(data_padrao)
        df['data'] = df['data'].dt.date
        
    return df

def insert_project(nome, data_projeto, data_finalizacao, descricao, status, link_projeto, ferramentas, versao, criadores):
    data_projeto_str = data_projeto.isoformat() if data_projeto else None
    data_finalizacao_str = data_finalizacao.isoformat() if data_finalizacao else None

    if isinstance(criadores, list):
        criadores_str = ", ".join(criadores)
    else:
        criadores_str = criadores

    conn = get_connection()
    c = conn.cursor()
    query = '''
        INSERT INTO projetos (
            nome, 
            data_projeto, 
            data_finalizacao, 
            descricao, 
            status, 
            link_projeto, 
            ferramentas, 
            versao, 
            criadores
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    execute_query(c, query, (nome, data_projeto_str, data_finalizacao_str, descricao, status, link_projeto, ferramentas, versao, criadores_str))
    conn.commit()
    conn.close()

def update_project_status(project_id, new_status):
    conn = get_connection()
    c = conn.cursor()
    query = 'UPDATE projetos SET status = ? WHERE id = ?'
    execute_query(c, query, (new_status, project_id))
    conn.commit()
    conn.close()

def delete_project(project_id):
    conn = get_connection()
    c = conn.cursor()
    query = 'DELETE FROM projetos WHERE id = ?'
    execute_query(c, query, (project_id,))
    conn.commit()
    conn.close()

def update_project(project_id, changes):
    if "data" in changes:
        changes["data_projeto"] = changes.pop("data")
    
    for key in list(changes.keys()):
        if key in ["data_projeto", "data_finalizacao"]:
            value = changes[key]
            if isinstance(value, (datetime.date, datetime.datetime)):
                changes[key] = value.isoformat()
    
    set_clause = ", ".join([f"{col} = ?" for col in changes.keys()])
    values = list(changes.values())
    values.append(project_id)
    
    conn = get_connection()
    c = conn.cursor()
    query = f"UPDATE projetos SET {set_clause} WHERE id = ?"
    execute_query(c, query, tuple(values))
    conn.commit()
    conn.close()

def create_feedback_table():
    conn = get_connection()
    c = conn.cursor()
    query = '''
        CREATE TABLE IF NOT EXISTS feedback (
            id SERIAL PRIMARY KEY,
            feedback TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    '''
    execute_query(c, query)
    conn.commit()
    conn.close()

def insert_feedback(feedback):
    conn = get_connection()
    c = conn.cursor()
    query = 'INSERT INTO feedback (feedback, timestamp) VALUES (?, ?)'
    execute_query(c, query, (feedback, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()

def load_feedbacks():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM feedback ORDER BY timestamp DESC", conn)
    conn.close()
    return df

def delete_feedback(feedback_id):
    conn = get_connection()
    c = conn.cursor()
    query = 'DELETE FROM feedback WHERE id = ?'
    execute_query(c, query, (feedback_id,))
    conn.commit()
    conn.close()