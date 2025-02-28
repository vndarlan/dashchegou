import streamlit as st
import os

# Configurar o servidor programaticamente
if "PORT" in os.environ:
    port = int(os.environ["PORT"])
    st.set_option('server.port', port)
    st.set_option('server.address', '0.0.0.0')

# Configuração da página inicial
st.set_page_config(
    page_title="Gestão Grupo Chegou",
    page_icon="🏢",
    layout="wide"
)

# Título único na página inicial
st.title("Gestão Grupo Chegou")