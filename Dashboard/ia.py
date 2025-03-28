import sys
import os
import streamlit as st
import altair as alt
import pandas as pd
import datetime

# Add root directory to path for db_utils import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import database functions
from db_utils import (
    init_db, 
    load_data, 
    insert_project, 
    update_project_status, 
    delete_project, 
    update_project,
    create_feedback_table,
    load_feedbacks,
    delete_feedback
)

# Initialize database
init_db()

# Status colors
status_domain = ["Ativo", "Em Manutenção", "Arquivado", "Backlog", "Em Construção", "Período de Validação"]
status_range = ["green", "orange", "red", "blue", "purple", "brown"]

def dashboard_page():
    st.header("Dashboard de Projetos")
    
    # Load project data
    if "df_projects" not in st.session_state:
        st.session_state.df_projects = load_data()
    df = st.session_state.df_projects

    if df.empty:
        st.info("Nenhum projeto cadastrado.")
        return
        
    # KPIs with status
    total_projects = len(df)
    active_projects = df[df['status'] == 'Ativo'].shape[0]
    maintenance_projects = df[df['status'] == 'Em Manutenção'].shape[0]
    archived_projects = df[df['status'] == 'Arquivado'].shape[0]
    backlog_projects = df[df['status'] == 'Backlog'].shape[0]
    construcao_projects = df[df['status'] == 'Em Construção'].shape[0]
    validacao_projects = df[df['status'] == 'Período de Validação'].shape[0]

    kpi_cols = st.columns(7)
    kpi_cols[0].metric("Total", total_projects)
    kpi_cols[1].metric("Ativo", active_projects)
    kpi_cols[2].metric("Em Manutenção", maintenance_projects)
    kpi_cols[3].metric("Arquivado", archived_projects)
    kpi_cols[4].metric("Backlog", backlog_projects)
    kpi_cols[5].metric("Em Construção", construcao_projects)
    kpi_cols[6].metric("Período de Validação", validacao_projects)

    st.markdown("---")

    # Filters
    with st.container():
        filter_cols = st.columns(4)
        with filter_cols[0]:
            nome_filter = st.text_input("Nome", placeholder="Buscar por nome")
        with filter_cols[1]:
            status_options = ["Todos"] + status_domain
            status_filter = st.selectbox("Status", options=status_options)
        with filter_cols[2]:
            try:
                df_temp = pd.to_datetime(df['data'], errors='coerce')
                min_date = df_temp.min().date() if pd.notna(df_temp.min()) else datetime.date.today()
                max_date = df_temp.max().date() if pd.notna(df_temp.max()) else datetime.date.today()
            except Exception:
                min_date = datetime.date.today()
                max_date = datetime.date.today()
            date_start = st.date_input("Data Início", value=min_date, key="date_start")
        with filter_cols[3]:
            date_end = st.date_input("Data Fim", value=max_date, key="date_end")

    # Apply filters
    df_filtered = df.copy()
    if nome_filter:
        df_filtered = df_filtered[df_filtered['nome'].str.contains(nome_filter, case=False)]
    if status_filter != "Todos":
        df_filtered = df_filtered[df_filtered['status'] == status_filter]
    if 'data' in df_filtered.columns:
        df_filtered = df_filtered[
            (pd.to_datetime(df_filtered['data']).dt.date >= date_start) &
            (pd.to_datetime(df_filtered['data']).dt.date <= date_end)
        ]

    # Charts layout
    col_left, col_right = st.columns(2)

    # Chart 1: Status Distribution
    with col_left:
        pie_chart = alt.Chart(df_filtered).mark_arc(innerRadius=50).encode(
            theta=alt.Theta(field="count", type="quantitative"),
            color=alt.Color(field="status", type="nominal",
                            scale=alt.Scale(domain=status_domain, range=status_range),
                            legend=alt.Legend(title="Status")),
            tooltip=[alt.Tooltip('status', title='Status'),
                     alt.Tooltip('count:Q', title='Quantidade')]
        ).transform_aggregate(
            count='count()',
            groupby=['status']
        ).properties(
            width=350,
            height=350,
            title="Distribuição por Status"
        )
        st.altair_chart(pie_chart, use_container_width=True)

    # Chart 2: Projects by Creator
    with col_right:
        df_creators = df_filtered[['id', 'criadores', 'status']].copy()
        def split_creators(criadores):
            if pd.isna(criadores) or criadores.strip() == "":
                return []
            return [nome.strip() for nome in criadores.split(',') if nome.strip()]
        df_creators['criadores_list'] = df_creators['criadores'].apply(split_creators)
        df_exploded = df_creators.explode('criadores_list')
        df_exploded = df_exploded[df_exploded['criadores_list'] != '']

        creator_status_counts = df_exploded.groupby(['criadores_list', 'status']).size().reset_index(name='Quantidade')

        bar_chart_creators = alt.Chart(creator_status_counts).mark_bar().encode(
            x=alt.X('criadores_list:N', title="Criador", sort='-y'),
            y=alt.Y('Quantidade:Q', title="Número de Projetos"),
            color=alt.Color('status:N', title='Status',
                            scale=alt.Scale(domain=status_domain, range=status_range)),
            tooltip=[alt.Tooltip('criadores_list', title='Criador'),
                     alt.Tooltip('status', title='Status'),
                     alt.Tooltip('Quantidade', title='Quantidade')]
        ).properties(
            width=350,
            height=350,
            title="Projetos por Criador"
        )
        st.altair_chart(bar_chart_creators, use_container_width=True)

    st.markdown("---")

    # Chart 3: Project Evolution
    evolution_chart = alt.Chart(df_filtered).mark_line(point=True).encode(
        x=alt.X('yearmonth(data):T', title="Mês/Ano"),
        y=alt.Y('count()', title='Número de Projetos'),
        color=alt.Color('status:N', title='Status',
                        scale=alt.Scale(domain=status_domain, range=status_range)),
        tooltip=[alt.Tooltip('yearmonth(data):T', title='Mês/Ano'),
                 alt.Tooltip('count()', title='Contagem')]
    ).properties(
        width=750,
        height=350,
        title="Evolução dos Projetos"
    )
    st.altair_chart(evolution_chart, use_container_width=True)

    st.markdown("---")

    # Editable table
    edited_df = st.data_editor(
        df_filtered,
        num_rows="dynamic",
        key="editable_table_dashboard",
        use_container_width=True
    )

    if st.button("Salvar alterações"):
        # Detect removed rows
        original_ids = set(df_filtered['id'])
        edited_ids = set(edited_df['id'])
        deleted_ids = original_ids - edited_ids

        for project_id in deleted_ids:
            delete_project(project_id)
            st.success(f"Projeto com ID {project_id} excluído!")

        # Check for updates
        original_dict = df_filtered.set_index('id').to_dict('index')
        for _, row in edited_df.iterrows():
            project_id = row['id']
            if project_id in original_dict:
                original_row = original_dict[project_id]
                changes = {}
                for col in row.index:
                    if col != 'id' and row[col] != original_row.get(col):
                        changes[col] = row[col]
                if changes:
                    update_project(project_id, changes)
                    st.success(f"Projeto '{row['nome']}' atualizado!")

        # Update session data
        st.session_state.df_projects = load_data()
        st.success("Alterações salvas com sucesso!")

def new_project_page():
    st.header("Novo Projeto")
    with st.form(key='form_add_project'):
        nome = st.text_input("Nome do Projeto")
        data_projeto = st.date_input("Data de Criação", value=datetime.date.today())
        data_finalizacao = st.date_input("Data de Finalização", value=None)
        descricao = st.text_area("Descrição Curta")
        status = st.selectbox("Status", options=status_domain)
        link_projeto = st.text_input("Link do Projeto")
        ferramentas = st.text_area("Ferramentas Utilizadas")
        versao = st.text_input("Versão do Projeto", value="v1")
        criadores = st.multiselect("Criador(es) do Projeto", options=["Murillo", "Vinicius", "Matheus", "Diretoria"])
        submit_button = st.form_submit_button(label="Adicionar Projeto")

    if submit_button:
        if not nome:
            st.error("O campo 'Nome do Projeto' é obrigatório!")
        elif not criadores:
            st.error("Selecione pelo menos um criador para o projeto!")
        else:
            insert_project(nome, data_projeto, data_finalizacao, descricao, status, link_projeto, ferramentas, versao, criadores)
            st.success(f"Projeto '{nome}' adicionado com sucesso!")
            st.session_state.df_projects = load_data()
            st.info("Agora, acesse o 'Dashboard de Projetos' para ver o novo projeto.")

def feedbacks_page():
    create_feedback_table()
    st.header("Feedbacks Recebidos")
    feedbacks = load_feedbacks()
    if feedbacks.empty:
        st.info("Nenhum feedback recebido até o momento.")
    else:
        for index, row in feedbacks.iterrows():
            with st.container():
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"**Feedback ID {row['id']}**")
                    st.write(f"**Timestamp:** {row['timestamp']}")
                    st.write(row['feedback'])
                with col2:
                    if st.button("Excluir", key=f"delete_{row['id']}"):
                        delete_feedback(row['id'])
                        st.success("Feedback excluído!")
                        st.rerun()

def main():
    st.title("GC IA & Automações")
    
    # Use tabs for navigation
    tabs = st.tabs(["Dashboard", "Novo Projeto", "Feedbacks"])
    
    with tabs[0]:
        dashboard_page()
    
    with tabs[1]:
        new_project_page()
    
    with tabs[2]:
        feedbacks_page()

if __name__ == "__main__":
    main()