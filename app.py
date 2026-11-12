import streamlit as st
import pandas as pd
import gspread
from datetime import datetime
import json

# 1. CONFIGURAÇÃO INICIAL E VARIÁVEIS DE SESSÃO
st.set_page_config(page_title="Portal de Festividades", page_icon="⛪", layout="wide")

if 'logado' not in st.session_state:
    st.session_state['logado'] = False
if 'eventos_temporarios' not in st.session_state:
    st.session_state['eventos_temporarios'] = []

# 2. IDENTIDADE VISUAL E CSS (PLANO DE FUNDO E RODAPÉ)
# Quando você tiver o link da sua imagem, basta trocar "COLE_O_LINK_DA_FOTO_AQUI" pelo link real dela.
st.markdown("""
<style>
    /* Imagem de Fundo */
    .stApp {
        background-image: url("https://github.com/rcrystiandados/app-igreja/blob/main/logo.jpeg");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }
    
    /* Fundo branco semi-transparente para as áreas de conteúdo não sumirem no fundo */
    .block-container {
        background-color: rgba(255, 255, 255, 0.92);
        padding-top: 2rem;
        padding-bottom: 5rem;
        border-radius: 15px;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.1);
    }

    /* Estilizando o Rodapé Fixo */
    .rodape {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #1E3A8A;
        color: white;
        text-align: center;
        padding: 12px;
        font-size: 14px;
        font-weight: 500;
        z-index: 100;
        box-shadow: 0px -2px 10px rgba(0,0,0,0.2);
    }
</style>

<!-- Injeção do Rodapé Fixo na tela -->
<div class="rodape">
    Desenvolvido por <strong>rcrystiandados</strong>  |  
    📧 Contato: rcrystiandados@gmail.com  |  
    📱 WhatsApp: (83) 9 9962-3735
</div>
""", unsafe_allow_html=True)

# 3. FUNÇÕES DE BANCO DE DADOS
@st.cache_data(ttl=60)
def carregar_dados():
    credenciais = json.loads(st.secrets["google_credentials"])
    gc = gspread.service_account_from_dict(credenciais)
    # COLE O LINK DA PLANILHA AQUI DENTRO
    planilha = gc.open_by_url("https://docs.google.com/spreadsheets/d/1XEJ5z3hSdbfGEdeJFljZgZwBqYtuiI3zh6H9bLAT4ks/edit?usp=sharing")
    aba = planilha.get_worksheet(0)
    return pd.DataFrame(aba.get_all_records())

def salvar_lote_no_banco(dados_novos_lista):
    credenciais = json.loads(st.secrets["google_credentials"])
    gc = gspread.service_account_from_dict(credenciais)
    # COLE O MESMO LINK DA PLANILHA AQUI DENTRO
    planilha = gc.open_by_url("https://docs.google.com/spreadsheets/d/1XEJ5z3hSdbfGEdeJFljZgZwBqYtuiI3zh6H9bLAT4ks/edit?usp=sharing")
    aba = planilha.get_worksheet(0)
    aba.append_rows(dados_novos_lista)

# 4. CARREGAMENTO DOS DADOS
try:
    df = carregar_dados()
    
    if not df.empty:
        colunas_cong = [col for col in df.columns if 'Congregação -' in col]
        if colunas_cong:
            df['Congregação'] = df[colunas_cong].astype(str).agg(''.join, axis=1)
            df = df.drop(columns=colunas_cong)
        else:
            df['Congregação'] = "Não informada"
            
        colunas_finais = ['Data de Inicio da Festividade', 'Data Final da Festividade', 'Região da Congregação', 'Congregação', 'Nome da Festividade', 'Tipo de Festividade', 'Nome Completo', 'Cargo/Função', 'Whatsapp para Contato']
        df = df[[col for col in colunas_finais if col in df.columns]]

    # 5. ESTRUTURA DO SITE (ABAS PRINCIPAIS)
    st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>Portal Integrado de Festividades</h1>", unsafe_allow_html=True)
    st.markdown("---")

    aba1, aba2, aba3, aba4 = st.tabs(["🏠 Tela Inicial", "📅 Prévia Calendário", "📝 Cadastro de Eventos", "🔒 Área da Liderança"])

    # --- ABA 1: TELA INICIAL ---
    with aba1:
        st.markdown("### Bem-vindo ao Portal Oficial de Gestão de Eventos ⛪")
        st.write("Este sistema foi desenvolvido para centralizar, organizar e gerenciar todas as festividades da nossa congregação. Navegue pelas abas acima para utilizar as funcionalidades.")
        
        st.markdown("""
        #### 📌 Como utilizar esta ferramenta:
        1. **Prévia Calendário:** Acesse esta aba para consultar todos os eventos já marcados. Você pode filtrar por Região ou Tipo de Festividade para encontrar o que precisa rapidamente.
        2. **Cadastro de Eventos:** Área destinada ao preenchimento de novas festividades. Adicione um ou mais eventos à fila e envie todos de uma vez para o banco de dados oficial.
        3. **Área da Liderança:** Acesso restrito via senha. Exclusivo para visualizar painéis de choque de datas e administrar o calendário oficial.
        
        *Dúvidas técnicas ou problemas de acesso? Utilize os contatos no rodapé da página.*
        """)

    # --- ABA 2: PRÉVIA CALENDÁRIO (Público) ---
    with aba2:
        if not df.empty:
            st.markdown("### Calendário Geral de Eventos")
            col_filtro1, col_filtro2 = st.columns(2)
            
            df_exibicao = df.copy()
            with col_filtro1:
                if 'Região da Congregação' in df_exibicao.columns:
                    regioes = st.multiselect("Filtrar por Região:", options=df_exibicao['Região da Congregação'].unique())
                    if regioes:
                        df_exibicao = df_exibicao[df_exibicao['Região da Congregação'].isin(regioes)]
            with col_filtro2:
                if 'Tipo de Festividade' in df_exibicao.columns:
                    tipos = st.multiselect("Filtrar por Tipo:", options=df_exibicao['Tipo de Festividade'].unique())
                    if tipos:
                        df_exibicao = df_exibicao[df_exibicao['Tipo de Festividade'].isin(tipos)]
                        
            st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
            
            st.markdown("#### 📊 Resumo das Regiões")
            if 'Região da Congregação' in df_exibicao.columns:
                st.bar_chart(df_exibicao['Região da Congregação'].value_counts(), color="#1E3A8A")
        else:
            st.info("O calendário ainda não possui eventos registrados.")

    # --- ABA 3: CADASTRO DE EVENTOS ---
    with aba3:
        st.markdown("### 📝 Inserir Novo Evento")
        with st.form("form_evento", clear_on_submit=True):
            col_form1, col_form2 = st.columns(2)
            with col_form1:
                nome = st.text_input("👤 Nome Completo")
                cargo = st.selectbox("👔 Cargo/Função", ["", "Pastor", "Dirigente", "Líder de Departamento", "Secretário"])
                whatsapp = st.text_input("📱 Whatsapp para Contato")
                regiao = st.selectbox("🌍 Região da Congregação", ["", "Região Cariri", "Região Curimataú", "Região Metropolitana", "Nacional/Internacional"])
                congregacao = st.text_input("⛪ Nome da Congregação")
            with col_form2:
                festividade = st.text_input("🎉 Nome da Festividade")
                tipo = st.selectbox("🏷️ Tipo de Festividade", ["", "Aniversário de Congregação", "Congresso de Departamento", "Culto de Intercâmbio", "Evangelismo", "Outros"])
                data_inicio = st.date_input("📅 Data de Início", format="DD/MM/YYYY")
                data_fim = st.date_input("🏁 Data Final", format="DD/MM/YYYY")
            
            adicionar_btn = st.form_submit_button("➕ Adicionar à Fila")
            if adicionar_btn:
                if nome == "" or festividade == "":
                    st.error("Preencha ao menos o Nome e a Festividade.")
                else:
                    evento = {
                        "Nome": nome, "Cargo": cargo, "Whats": whatsapp, "Regiao": regiao, "Congregacao": congregacao, 
                        "Festividade": festividade, "Tipo": tipo, "Inicio": data_inicio.strftime("%d/%m/%Y"), "Fim": data_fim.strftime("%d/%m/%Y")
                    }
                    st.session_state['eventos_temporarios'].append(evento)
                    st.success("Evento na fila!")

        if len(st.session_state['eventos_temporarios']) > 0:
            st.markdown("---")
            st.dataframe(pd.DataFrame(st.session_state['eventos_temporarios']), use_container_width=True)
            col_btn1, col_btn2 = st.columns([1, 4])
            if col_btn1.button("🗑️ Limpar Lista"):
                st.session_state['eventos_temporarios'] = []
                st.rerun()
            if col_btn2.button("💾 ENVIAR PARA O BANCO DE DADOS"):
                linhas_para_inserir = []
                data_atual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                for row in st.session_state['eventos_temporarios']:
                    linhas_para_inserir.append([
                        data_atual, row['Nome'], row['Cargo'], row['Whats'], row['Regiao'], 
                        row['Congregacao'], '', '', '', row['Festividade'], row['Tipo'], row['Inicio'], row['Fim'], ''                    
                    ])
                salvar_lote_no_banco(linhas_para_inserir)
                st.balloons()
                st.success("Eventos salvos com sucesso!")
                st.session_state['eventos_temporarios'] = []
                st.cache_data.clear()

    # --- ABA 4: ÁREA DA LIDERANÇA (Acesso Restrito) ---
    with aba4:
        if not st.session_state['logado']:
            st.markdown("### 🔒 Acesso Restrito à Liderança")
            st.info("Insira a senha de administrador para visualizar o painel de choques de datas e fazer alterações.")
            senha_digitada = st.text_input("Senha:", type="password")
            
            if st.button("Entrar"):
                # Ele vai puxar a senha segura lá do seu cofre do Streamlit
                if "senha_lideranca" in st.secrets and senha_digitada == st.secrets["senha_lideranca"]:
                    st.session_state['logado'] = True
                    st.rerun()
                else:
                    st.error("Senha incorreta. Tente novamente.")
        
        else:
            # Painel do Líder Autenticado
            st.markdown("### 🛡️ Painel Administrativo de Choques")
            st.success("Autenticação realizada com sucesso.")
            if st.button("Sair (Logout)"):
                st.session_state['logado'] = False
                st.rerun()
            
            st.markdown("---")
            if not df.empty:
                contagem_datas = df['Data de Inicio da Festividade'].value_counts()
                choques = df[df['Data de Inicio da Festividade'].isin(contagem_datas[contagem_datas > 1].index)]
                
                if not choques.empty:
                    st.error(f"🚨 ALERTA: Foram detectados {len(choques)} eventos com choque de data (marcados para o mesmo dia).")
                    
                    def destacar_choques(row):
                        data = row.get('Data de Inicio da Festividade', "")
                        if data != "" and contagem_datas.get(data, 0) > 1:
                            return ['background-color: #ffcccc; color: #900000; font-weight: bold'] * len(row)
                        return [''] * len(row)
                        
                    st.dataframe(df.style.apply(destacar_choques, axis=1), use_container_width=True, hide_index=True)
                else:
                    st.success("✅ O calendário está limpo. Não há choques de data detectados.")
                
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("### ✏️ Alteração de Datas")
                st.info("Para garantir a segurança dos dados e evitar deleções acidentais simultâneas, as alterações e correções de datas são feitas diretamente no banco de dados central (Google Planilhas).")
                # COLE O LINK DA PLANILHA NOVAMENTE AQUI PARA O BOTÃO DO LÍDER
                st.link_button("Abrir Banco de Dados para Corrigir Datas 🔗", "https://docs.google.com/spreadsheets/d/1XEJ5z3hSdbfGEdeJFljZgZwBqYtuiI3zh6H9bLAT4ks/edit?usp=sharing")

except Exception as e:
    st.error(f"Erro de execução: {e}")
