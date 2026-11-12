import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
import json

# Inicializa a lista de espera de eventos na memória do site
if 'eventos_temporarios' not in st.session_state:
    st.session_state['eventos_temporarios'] = []

st.set_page_config(page_title="Gestão de Festividades", page_icon="📅", layout="wide")
st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>📅 Sistema Integrado de Festividades - Sede</h1>", unsafe_allow_html=True)
st.markdown("---")

@st.cache_data(ttl=60)
def carregar_dados():
    # Conexão de nuvem usando o cofre seguro do Streamlit
    credenciais = json.loads(st.secrets["google_credentials"])
    gc = gspread.service_account_from_dict(credenciais)
    
    # COLE O LINK DA PLANILHA AQUI DENTRO DAS ASPAS
    link_planilha = "https://docs.google.com/spreadsheets/d/1XEJ5z3hSdbfGEdeJFljZgZwBqYtuiI3zh6H9bLAT4ks/edit?usp=sharing"
    
    planilha = gc.open_by_url(link_planilha)
    aba = planilha.get_worksheet(0)
    dados = aba.get_all_records()
    return pd.DataFrame(dados)

def salvar_lote_no_banco(dados_novos_lista):
    # Conexão de nuvem usando o cofre seguro do Streamlit para salvar dados
    credenciais = json.loads(st.secrets["google_credentials"])
    gc = gspread.service_account_from_dict(credenciais)
    
    # COLE O MESMO LINK DA PLANILHA AQUI DENTRO DAS ASPAS
    link_planilha = "https://docs.google.com/spreadsheets/d/1XEJ5z3hSdbfGEdeJFljZgZwBqYtuiI3zh6H9bLAT4ks/edit?usp=sharing"
    
    planilha = gc.open_by_url(link_planilha)
    aba = planilha.get_worksheet(0)
    aba.append_rows(dados_novos_lista)

try:
    df = carregar_dados()
    
    if not df.empty:
        # Unificar colunas dinamicamente
        colunas_cong = [col for col in df.columns if 'Congregação -' in col]
        if colunas_cong:
            df['Congregação'] = df[colunas_cong].astype(str).agg(''.join, axis=1)
            df = df.drop(columns=colunas_cong)
        else:
            df['Congregação'] = "Não informada"

        # Barra lateral de filtros
        st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3050/3050525.png", width=100)
        st.sidebar.header("🔍 Filtros de Busca")
        
        if 'Região da Congregação' in df.columns:
            regioes_selecionadas = st.sidebar.multiselect("Filtrar por Região:", options=df['Região da Congregação'].unique())
            if regioes_selecionadas:
                df = df[df['Região da Congregação'].isin(regioes_selecionadas)]
                
        if 'Tipo de Festividade' in df.columns:
            tipos_selecionados = st.sidebar.multiselect("Filtrar por Tipo:", options=df['Tipo de Festividade'].unique())
            if tipos_selecionados:
                df = df[df['Tipo de Festividade'].isin(tipos_selecionados)]

        # Lógica de choque de datas
        choques = pd.DataFrame()
        if 'Data de Inicio da Festividade' in df.columns:
            contagem_datas = df['Data de Inicio da Festividade'].value_counts()
            
            def destacar_choques(row):
                data = row.get('Data de Inicio da Festividade', "")
                if data != "" and contagem_datas.get(data, 0) > 1:
                    return ['background-color: #ffcccc; color: #900000; font-weight: bold'] * len(row)
                return [''] * len(row)

            choques = df[df['Data de Inicio da Festividade'].isin(contagem_datas[contagem_datas > 1].index)]
            estilo_df = df.style.apply(destacar_choques, axis=1)
        else:
            estilo_df = df

        # Cartões superiores
        col1, col2, col3 = st.columns(3)
        col1.metric("📌 Total de Eventos Agendados", len(df))
        col2.metric("🚨 Alertas de Choque de Datas", len(choques))
        col3.metric("🌍 Regiões Mobilizadas", df['Região da Congregação'].nunique() if 'Região da Congregação' in df.columns else 0)

        st.markdown("<br>", unsafe_allow_html=True)

        aba1, aba2, aba3 = st.tabs(["📋 Tabela Geral e Alertas", "📈 Gráficos", "➕ Cadastro Form Dinâmico"])

        with aba1:
            if not choques.empty:
                st.error(f"⚠️ ATENÇÃO: Há {len(choques)} eventos marcados para o mesmo dia! Estão destacados em vermelho.")
            else:
                st.success("✅ Calendário limpo! Nenhum conflito de datas.")
            
            colunas_finais = ['Data de Inicio da Festividade', 'Data Final da Festividade', 'Região da Congregação', 'Congregação', 'Nome da Festividade', 'Tipo de Festividade', 'Nome Completo', 'Cargo/Função', 'Whatsapp para Contato', 'A congregação precisará de suporte da Sede?', 'Carimbo de data/hora']
            df_tabela = df[[col for col in colunas_finais if col in df.columns]]
            st.dataframe(df_tabela.style.apply(destacar_choques, axis=1) if 'Data de Inicio da Festividade' in df.columns else df_tabela, use_container_width=True, hide_index=True)

        with aba2:
            st.markdown("### Visão Geral do Ano")
            col_grafico1, col_grafico2 = st.columns(2)
            with col_grafico1:
                if 'Região da Congregação' in df.columns:
                    st.bar_chart(df['Região da Congregação'].value_counts(), color="#1E3A8A")
            with col_grafico2:
                if 'Tipo de Festividade' in df.columns:
                    st.bar_chart(df['Tipo de Festividade'].value_counts(), color="#22C55E")

        with aba3:
            st.markdown("### 📝 Adicionar Eventos à Fila")
            
            with st.form("form_evento", clear_on_submit=True):
                st.markdown("Preencha os dados abaixo e clique em 'Adicionar à Lista'.")
                
                col_form1, col_form2 = st.columns(2)
                with col_form1:
                    nome = st.text_input("Nome Completo")
                    cargo = st.selectbox("Cargo/Função", ["", "Pastor", "Dirigente", "Líder de Departamento", "Secretário"])
                    whatsapp = st.text_input("Whatsapp para Contato")
                    regiao = st.selectbox("Região da Congregação", ["", "Região Cariri", "Região Curimataú", "Região Metropolitana", "Nacional/Internacional"])
                    congregacao = st.text_input("Nome da Congregação")
                
                with col_form2:
                    festividade = st.text_input("Nome da Festividade")
                    tipo = st.selectbox("Tipo de Festividade", ["", "Aniversário de Congregação", "Congresso de Departamento", "Culto de Intercâmbio", "Evangelismo", "Outros"])
                    data_inicio = st.date_input("Data de Início", format="DD/MM/YYYY")
                    data_fim = st.date_input("Data Final", format="DD/MM/YYYY")
                
                adicionar_btn = st.form_submit_button("➕ Adicionar à Lista", type="secondary")
                
                if adicionar_btn:
                    if nome == "" or festividade == "":
                        st.error("Por favor, preencha pelo menos o Nome Completo e o Nome da Festividade.")
                    else:
                        data_ini_str = data_inicio.strftime("%d/%m/%Y")
                        data_fim_str = data_fim.strftime("%d/%m/%Y")
                        
                        evento = {
                            "Nome": nome, "Cargo": cargo, "Whats": whatsapp, 
                            "Regiao": regiao, "Congregacao": congregacao, 
                            "Festividade": festividade, "Tipo": tipo, 
                            "Inicio": data_ini_str, "Fim": data_fim_str
                        }
                        st.session_state['eventos_temporarios'].append(evento)
                        st.success("Evento adicionado à lista! O formulário foi limpo para o próximo.")

            if len(st.session_state['eventos_temporarios']) > 0:
                st.markdown("---")
                st.markdown(f"#### 🛒 Eventos aguardando envio: {len(st.session_state['eventos_temporarios'])}")
                
                df_espera = pd.DataFrame(st.session_state['eventos_temporarios'])
                st.dataframe(df_espera, use_container_width=True)
                
                col_btn1, col_btn2 = st.columns([1, 4])
                
                if col_btn1.button("🗑️ Limpar Lista"):
                    st.session_state['eventos_temporarios'] = []
                    st.rerun()
                    
                if col_btn2.button("💾 ENVIAR TODOS PARA O GOOGLE PLANILHAS", type="primary"):
                    st.toast("Salvando dados, aguarde...")
                    linhas_para_inserir = []
                    data_atual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    
                    for row in st.session_state['eventos_temporarios']:
                        nova_linha = [
                            data_atual,           
                            row['Nome'],          
                            row['Cargo'],         
                            row['Whats'],         
                            row['Regiao'],        
                            row['Congregacao'],   
                            '', '', '',           
                            row['Festividade'],   
                            row['Tipo'],          
                            row['Inicio'],        
                            row['Fim'],           
                            ''                    
                        ]
                        linhas_para_inserir.append(nova_linha)
                    
                    try:
                        salvar_lote_no_banco(linhas_para_inserir)
                        st.success(f"✅ {len(linhas_para_inserir)} eventos salvos no banco de dados!")
                        st.session_state['eventos_temporarios'] = [] 
                        st.cache_data.clear() 
                        st.rerun()
                    except Exception as erro_salvar:
                        st.error(f"Erro ao salvar: {erro_salvar}")

    else:
        st.info("A planilha está conectada, mas aguardando o cadastro do primeiro evento.")

except Exception as e:
    st.error(f"Erro de execução: {e}")