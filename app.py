import streamlit as st
import pandas as pd
import altair as alt
import gspread
from datetime import datetime
import json

# =====================================================================
# 1. CONFIGURAÇÃO INICIAL
# =====================================================================
st.set_page_config(
    page_title="Portal Integrado de Festividades",
    page_icon="⛪",
    layout="wide",
    initial_sidebar_state="expanded",
)

LOGO_URL = "https://github.com/rcrystiandados/app-igreja/blob/main/logo.jpeg?raw=true"
PLANILHA_URL = "https://docs.google.com/spreadsheets/d/1XEJ5z3hSdbfGEdeJFljZgZwBqYtuiI3zh6H9bLAT4ks/edit?usp=sharing"

if "logado" not in st.session_state:
    st.session_state["logado"] = False
if "eventos_temporarios" not in st.session_state:
    st.session_state["eventos_temporarios"] = []

# =====================================================================
# 2. ESTILO INSTITUCIONAL
# =====================================================================
st.markdown("""
<style>
    :root {
        --azul: #1E3A8A;
        --azul-escuro: #152C6B;
        --azul-claro: #E8EEFB;
        --fundo: #F5F7FA;
        --borda: #DDE3EC;
        --texto: #1F2937;
    }

    .stApp {background: var(--fundo);}
    header[data-testid="stHeader"] {background: transparent;}
    #MainMenu, footer {visibility: hidden;}

    /* Conteúdo */
    .block-container {
        padding: 2.5rem 3rem 4rem 3rem;
        max-width: 1200px;
    }
    .block-container h1, .block-container h2, .block-container h3, .block-container h4 {
        color: var(--azul) !important; font-weight: 700 !important;
    }
    .block-container h1 {
        font-size: 1.9rem; padding-bottom: .6rem; border-bottom: 2px solid var(--borda);
        margin-bottom: 1.2rem;
    }
    .block-container p, .block-container label, .block-container li {color: var(--texto);}

    /* Barra lateral (menu) */
    section[data-testid="stSidebar"] {background: var(--azul); border-right: none;}
    section[data-testid="stSidebar"] * {color: #FFFFFF !important;}
    .sb-titulo {font-size: 1.2rem; font-weight: 700; line-height: 1.3; margin: .4rem 0 .2rem 0;}
    .sb-sub {font-size: .85rem; opacity: .75; margin-bottom: 1.4rem;}

    section[data-testid="stSidebar"] div[role="radiogroup"] {gap: .25rem;}
    section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {display: none;}
    section[data-testid="stSidebar"] div[role="radiogroup"] label {
        width: 100%; padding: .65rem .9rem; border-radius: 6px;
        cursor: pointer; transition: background .15s;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {background: rgba(255,255,255,.12);}
    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {background: #FFFFFF;}
    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) * {
        color: var(--azul) !important; font-weight: 600;
    }
    .sb-contato {font-size: .82rem; line-height: 1.7; opacity: .9;}
    section[data-testid="stSidebar"] hr {border-color: rgba(255,255,255,.2);}

    /* Cartões */
    .card {
        background: #FFFFFF; border: 1px solid var(--borda); border-radius: 8px;
        padding: 1.1rem 1.3rem; height: 100%;
    }
    .card .card-titulo {color: var(--azul); font-weight: 700; margin-bottom: .3rem;}
    .card .card-texto {color: var(--texto); font-size: .95rem;}

    /* Indicadores */
    div[data-testid="stMetric"] {
        background: #FFFFFF; border: 1px solid var(--borda);
        border-radius: 8px; padding: .9rem 1.1rem;
    }
    div[data-testid="stMetricValue"] {color: var(--azul);}

    /* Botões */
    div.stButton > button, div.stFormSubmitButton > button, a[data-testid="stBaseLinkButton-secondary"] {
        background-color: var(--azul) !important; color: #FFFFFF !important;
        border: none !important; border-radius: 6px !important;
        padding: .55rem 1.4rem !important; font-weight: 600 !important;
    }
    div.stButton > button *, div.stFormSubmitButton > button * {color: #FFFFFF !important;}
    div.stButton > button:hover, div.stFormSubmitButton > button:hover {
        background-color: var(--azul-escuro) !important;
    }

    /* Avisos legíveis */
    div[data-testid="stAlert"] {border-left: 5px solid var(--azul) !important;}
    div[data-testid="stAlert"] * {color: var(--texto) !important;}

    /* Campos */
    div[data-baseweb="input"], div[data-baseweb="select"] > div, div[data-baseweb="base-input"] {
        background-color: #FFFFFF !important; border-color: #CBD5E1 !important;
    }
    div[data-testid="stForm"] {background: #FFFFFF; border: 1px solid var(--borda); border-radius: 8px;}

    /* ---------- Correções de tema e componentes ---------- */
    :root, .stApp {color-scheme: light;}

    .sb-topo {text-align: center; margin: .2rem 0 1.2rem 0;}
    .sb-logo {width: 100%; max-width: 210px; height: auto; border-radius: 8px;
              background: #FFFFFF; margin-bottom: .8rem;}
    .sb-topo .sb-titulo {margin: 0;}

    /* Menu: some com as bolinhas do radio */
    section[data-testid="stSidebar"] label[data-baseweb="radio"] > div:first-child,
    section[data-testid="stSidebar"] label[data-baseweb="radio"] > span:first-child,
    section[data-testid="stSidebar"] [data-testid="stRadio"] label > div:first-child:not([data-testid="stMarkdownContainer"]) {
        display: none !important;
    }

    /* Campos de texto e senha sempre claros */
    div[data-testid="stTextInput"] div[data-baseweb="input"],
    div[data-testid="stTextInput"] div[data-baseweb="base-input"],
    div[data-testid="stTextInput"] input,
    div[data-testid="stTextInput"] button {
        background-color: #FFFFFF !important; color: #111827 !important;
    }
    div[data-testid="stTextInput"] div[data-baseweb="input"] {border: 1px solid #CBD5E1 !important;}
    div[data-testid="stTextInput"] svg {fill: #475569 !important;}

    /* Avisos sempre claros e legíveis */
    div[data-testid="stAlert"] {background-color: #E8EEFB !important;}
    div[data-testid="stAlert"] * {background-color: transparent !important; color: #1F2937 !important;}

    /* Página de login */
    .login-topo {text-align: center; margin: 1.5rem 0 1.2rem 0;}
    .login-topo .login-icone {
        width: 64px; height: 64px; margin: 0 auto .8rem auto; border-radius: 50%;
        background: var(--azul-claro); display: flex; align-items: center;
        justify-content: center; font-size: 1.8rem;
    }
    .login-topo h2 {margin: 0 0 .4rem 0;}
    .login-topo p {color: #6B7280 !important; margin: 0;}

    /* ---------- Menu lateral em botões ---------- */
    section[data-testid="stSidebar"] div.stButton > button {
        width: 100%; justify-content: flex-start; text-align: left;
        padding: .65rem .9rem !important; border-radius: 6px !important;
        background-color: transparent !important; border: none !important;
        box-shadow: none !important; font-weight: 500 !important;
    }
    section[data-testid="stSidebar"] div.stButton > button * {
        color: #FFFFFF !important; justify-content: flex-start; text-align: left;
    }
    section[data-testid="stSidebar"] div.stButton > button:hover {
        background-color: rgba(255,255,255,.14) !important;
    }
    section[data-testid="stSidebar"] div.stButton > button[kind="primary"],
    section[data-testid="stSidebar"] div.stButton > button[data-testid="stBaseButton-primary"] {
        background-color: #FFFFFF !important;
    }
    section[data-testid="stSidebar"] div.stButton > button[kind="primary"] *,
    section[data-testid="stSidebar"] div.stButton > button[data-testid="stBaseButton-primary"] * {
        color: #1E3A8A !important; font-weight: 700 !important;
    }

    /* ---------- Selects e listas sempre claros ---------- */
    div[data-baseweb="select"] > div {background-color: #FFFFFF !important; border: 1px solid #CBD5E1 !important;}
    div[data-baseweb="select"] * {color: #111827 !important;}
    div[data-baseweb="select"] svg {fill: #475569 !important;}
    div[data-baseweb="popover"], div[data-baseweb="popover"] ul,
    div[data-baseweb="popover"] li, div[data-baseweb="menu"] {
        background-color: #FFFFFF !important; color: #111827 !important;
    }
    div[data-baseweb="popover"] li:hover {background-color: #E8EEFB !important;}
    span[data-baseweb="tag"] {background-color: #1E3A8A !important;}
    span[data-baseweb="tag"] * {color: #FFFFFF !important;}
    div[data-testid="stDateInput"] div[data-baseweb="input"],
    div[data-testid="stDateInput"] input {background-color: #FFFFFF !important; color: #111827 !important;}
</style>
""", unsafe_allow_html=True)

# =====================================================================
# 3. BANCO DE DADOS (GOOGLE PLANILHAS)
# =====================================================================
def _abrir_aba():
    credenciais = json.loads(st.secrets["google_credentials"])
    gc = gspread.service_account_from_dict(credenciais)
    return gc.open_by_url(PLANILHA_URL).get_worksheet(0)


@st.cache_data(ttl=60)
def carregar_dados():
    return pd.DataFrame(_abrir_aba().get_all_records())


def salvar_lote_no_banco(dados_novos_lista):
    _abrir_aba().append_rows(dados_novos_lista)


# =====================================================================
# 4. MENU LATERAL
# =====================================================================
with st.sidebar:
    st.markdown(
        f'<div class="sb-topo"><img class="sb-logo" src="{LOGO_URL}" alt="Logo">'
        '<div class="sb-titulo">Portal Integrado MEN</div>'
        '<div class="sb-sub">Gestão de eventos das congregações</div></div>',
        unsafe_allow_html=True,
    )
    PAGINAS = ["Início", "Calendário", "Cadastro de eventos", "Área da liderança"]
    if "pagina" not in st.session_state:
        st.session_state["pagina"] = "Início"
    for nome_pag in PAGINAS:
        ativo = st.session_state["pagina"] == nome_pag
        if st.button(nome_pag, key=f"menu_{nome_pag}",
                     type="primary" if ativo else "secondary",
                     use_container_width=True):
            st.session_state["pagina"] = nome_pag
            st.rerun()
    pagina = st.session_state["pagina"]
    st.markdown("---")
    st.markdown(
        '<div class="sb-contato">Desenvolvido por <b>Rodolfo Crystian</b><br>'
        'rcrystiandados@gmail.com<br>WhatsApp: (83) 9 9962-3735</div>',
        unsafe_allow_html=True,
    )

# =====================================================================
# 5. CARREGAMENTO E TRATAMENTO DOS DADOS
# =====================================================================
try:
    df = carregar_dados()

    if not df.empty:
        colunas_cong = [c for c in df.columns if "Congregação -" in c]
        if colunas_cong:
            df["Congregação"] = df[colunas_cong].astype(str).agg("".join, axis=1)
            df = df.drop(columns=colunas_cong)
        else:
            df["Congregação"] = "Não informada"

        colunas_finais = [
            "Data de Inicio da Festividade", "Data Final da Festividade",
            "Região da Congregação", "Congregação", "Nome da Festividade",
            "Tipo de Festividade", "Nome Completo", "Cargo/Função", "Whatsapp para Contato",
        ]
        df = df[[c for c in colunas_finais if c in df.columns]]

    # =================================================================
    # PÁGINA: INÍCIO
    # =================================================================
    if pagina == "Início":
        st.title("Portal de Gestão de Eventos")
        st.write(
            "Este sistema centraliza, organiza e gerencia as festividades da nossa "
            "congregação. Use o menu à esquerda para navegar."
        )

        if not df.empty:
            datas = pd.to_datetime(df["Data de Inicio da Festividade"], dayfirst=True, errors="coerce")
            futuros = datas[datas >= pd.Timestamp.today().normalize()]
            m1, m2, m3 = st.columns(3)
            m1.metric("Eventos cadastrados", len(df))
            m2.metric("Regiões com eventos", df["Região da Congregação"].nunique())
            m3.metric(
                "Próximo evento",
                futuros.min().strftime("%d/%m/%Y") if not futuros.empty else "—",
            )
            st.write("")

        st.markdown("#### Como utilizar")
        c1, c2, c3 = st.columns(3)
        c1.markdown(
            '<div class="card"><div class="card-titulo">Calendário</div>'
            '<div class="card-texto">Consulte os eventos já marcados e filtre por região '
            'ou tipo de festividade.</div></div>', unsafe_allow_html=True)
        c2.markdown(
            '<div class="card"><div class="card-titulo">Cadastro de eventos</div>'
            '<div class="card-texto">Adicione um ou mais eventos à fila e envie todos '
            'de uma vez para o banco de dados oficial.</div></div>', unsafe_allow_html=True)
        c3.markdown(
            '<div class="card"><div class="card-titulo">Área da liderança</div>'
            '<div class="card-texto">Acesso por senha ao painel de choques de datas '
            'e à administração do calendário.</div></div>', unsafe_allow_html=True)
        st.write("")
        st.caption("Dúvidas técnicas ou problemas de acesso? Use os contatos no menu lateral.")

    # =================================================================
    # PÁGINA: CALENDÁRIO (PÚBLICO)
    # =================================================================
    elif pagina == "Calendário":
        st.title("Calendário geral de eventos")

        if df.empty:
            st.info("O calendário ainda não possui eventos registrados.")
        else:
            df_exibicao = df.copy()
            f1, f2 = st.columns(2)
            with f1:
                regioes = st.multiselect(
                    "Filtrar por região", options=sorted(df_exibicao["Região da Congregação"].unique())
                )
                if regioes:
                    df_exibicao = df_exibicao[df_exibicao["Região da Congregação"].isin(regioes)]
            with f2:
                tipos = st.multiselect(
                    "Filtrar por tipo", options=sorted(df_exibicao["Tipo de Festividade"].unique())
                )
                if tipos:
                    df_exibicao = df_exibicao[df_exibicao["Tipo de Festividade"].isin(tipos)]

            # Visão pública: datas reais, ordenadas, sem dados de contato
            publico = df_exibicao.drop(
                columns=[c for c in ["Whatsapp para Contato", "Cargo/Função"] if c in df_exibicao.columns]
            ).copy()
            for col in ["Data de Inicio da Festividade", "Data Final da Festividade"]:
                publico[col] = pd.to_datetime(publico[col], dayfirst=True, errors="coerce")
            publico = publico.sort_values("Data de Inicio da Festividade")

            st.dataframe(
                publico,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Data de Inicio da Festividade": st.column_config.DateColumn("Início", format="DD/MM/YYYY"),
                    "Data Final da Festividade": st.column_config.DateColumn("Fim", format="DD/MM/YYYY"),
                    "Região da Congregação": st.column_config.TextColumn("Região"),
                    "Nome da Festividade": st.column_config.TextColumn("Festividade", width="large"),
                    "Tipo de Festividade": st.column_config.TextColumn("Tipo"),
                    "Nome Completo": st.column_config.TextColumn("Responsável"),
                },
            )
            st.caption(f"{len(publico)} evento(s) exibido(s).")

            st.markdown("#### Eventos por região")
            contagem = df_exibicao["Região da Congregação"].value_counts()
            dfc = contagem.reset_index()
            dfc.columns = ["Região", "Eventos"]
            grafico = (
                alt.Chart(dfc)
                .mark_bar(color="#1E3A8A")
                .encode(
                    x=alt.X("Eventos:Q", title=None, axis=alt.Axis(tickMinStep=1, format="d")),
                    y=alt.Y("Região:N", sort="-x", title=None),
                )
                .properties(height=max(120, 42 * len(dfc)), background="#FFFFFF")
                .configure_view(strokeWidth=0)
                .configure_axis(labelColor="#1F2937", gridColor="#E5E7EB", domainColor="#CBD5E1")
            )
            st.altair_chart(grafico, use_container_width=True, theme=None)

    # =================================================================
    # PÁGINA: CADASTRO DE EVENTOS
    # =================================================================
    elif pagina == "Cadastro de eventos":
        st.title("Cadastro de novo evento")

        with st.form("form_evento", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nome = st.text_input("Nome completo")
                cargo = st.selectbox("Cargo/Função", ["", "Pastor", "Dirigente", "Líder de Departamento", "Secretário"])
                whatsapp = st.text_input("WhatsApp para contato")
                regiao = st.selectbox("Região da congregação", ["", "Região Cariri", "Região Curimataú", "Região Metropolitana", "Nacional/Internacional"])
                congregacao = st.text_input("Nome da congregação")
            with col2:
                festividade = st.text_input("Nome da festividade")
                tipo = st.selectbox("Tipo de festividade", ["", "Aniversário de Congregação", "Congresso de Departamento", "Culto de Intercâmbio", "Evangelismo", "Outros"])
                data_inicio = st.date_input("Data de início", format="DD/MM/YYYY")
                data_fim = st.date_input("Data final", format="DD/MM/YYYY")

            adicionar_btn = st.form_submit_button("Adicionar à fila")
            if adicionar_btn:
                if nome == "" or festividade == "":
                    st.error("Preencha ao menos o nome completo e o nome da festividade.")
                elif data_fim < data_inicio:
                    st.error("A data final não pode ser anterior à data de início.")
                else:
                    st.session_state["eventos_temporarios"].append({
                        "Nome": nome, "Cargo": cargo, "Whats": whatsapp, "Regiao": regiao,
                        "Congregacao": congregacao, "Festividade": festividade, "Tipo": tipo,
                        "Inicio": data_inicio.strftime("%d/%m/%Y"), "Fim": data_fim.strftime("%d/%m/%Y"),
                    })
                    st.success("Evento adicionado à fila.")

        if st.session_state["eventos_temporarios"]:
            st.markdown("#### Fila de envio")
            st.dataframe(
                pd.DataFrame(st.session_state["eventos_temporarios"]),
                use_container_width=True, hide_index=True,
            )
            b1, b2, _ = st.columns([1, 2, 3])
            if b1.button("Limpar lista"):
                st.session_state["eventos_temporarios"] = []
                st.rerun()
            if b2.button("Enviar para o banco de dados"):
                data_atual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                linhas = [
                    [data_atual, r["Nome"], r["Cargo"], r["Whats"], r["Regiao"],
                     r["Congregacao"], "", "", "", r["Festividade"], r["Tipo"],
                     r["Inicio"], r["Fim"], ""]
                    for r in st.session_state["eventos_temporarios"]
                ]
                salvar_lote_no_banco(linhas)
                st.success("Eventos salvos com sucesso.")
                st.session_state["eventos_temporarios"] = []
                st.cache_data.clear()

    # =================================================================
    # PÁGINA: ÁREA DA LIDERANÇA
    # =================================================================
    elif pagina == "Área da liderança":
        if not st.session_state["logado"]:
            _, centro, _ = st.columns([1, 1.6, 1])
            with centro:
                st.markdown(
                    '<div class="login-topo"><div class="login-icone">🔒</div>'
                    '<h2>Acesso restrito à liderança</h2>'
                    '<p>Informe a senha de administrador para ver o painel de choques de datas.</p></div>',
                    unsafe_allow_html=True,
                )
                with st.form("form_login"):
                    senha_digitada = st.text_input("Senha", type="password", placeholder="Digite a senha")
                    entrar = st.form_submit_button("Entrar", use_container_width=True)
                if entrar:
                    if "senha_lideranca" in st.secrets and senha_digitada == st.secrets["senha_lideranca"]:
                        st.session_state["logado"] = True
                        st.rerun()
                    else:
                        st.error("Senha incorreta. Tente novamente.")
        else:
            st.title("Painel administrativo")
            top1, top2 = st.columns([5, 1])
            top1.success("Autenticação realizada com sucesso.")
            if top2.button("Sair"):
                st.session_state["logado"] = False
                st.rerun()

            if not df.empty:
                st.markdown("#### Choques de datas")
                contagem_datas = df["Data de Inicio da Festividade"].value_counts()
                choques = df[df["Data de Inicio da Festividade"].isin(contagem_datas[contagem_datas > 1].index)]

                if not choques.empty:
                    st.error(f"Foram detectados {len(choques)} eventos com choque de data (mesmo dia de início).")

                    def destacar_choques(row):
                        data = row.get("Data de Inicio da Festividade", "")
                        if data != "" and contagem_datas.get(data, 0) > 1:
                            return ["background-color: #FDE2E2; color: #7F1D1D; font-weight: 600"] * len(row)
                        return [""] * len(row)

                    st.dataframe(df.style.apply(destacar_choques, axis=1), use_container_width=True, hide_index=True)
                else:
                    st.success("O calendário está limpo. Nenhum choque de data detectado.")

                st.markdown("#### Alteração de datas")
                st.info(
                    "Para evitar alterações acidentais, correções de data são feitas diretamente "
                    "no banco de dados central (Google Planilhas)."
                )
                st.link_button("Abrir banco de dados", PLANILHA_URL)

except Exception as e:
    st.error(f"Erro de execução: {e}")
