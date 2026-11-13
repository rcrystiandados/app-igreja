import streamlit as st
import pandas as pd
import altair as alt
import gspread
from datetime import datetime
import json
import re
import unicodedata

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
# Lista base de congregações. Novas congregações cadastradas na Área da liderança
# ficam salvas na aba "Congregações" da planilha e são somadas a esta lista.
CARGOS = ["", "Pastor", "Dirigente", "Líder de Departamento", "Secretário"]
OUTRA_CONGREGACAO = "Outra congregação (digitar o nome)"
CONGREGACOES_POR_REGIAO = {
    "Região Cariri": [
        "IEC - São João do Cariri", "IEC - Sumé", "IEC - Serra Branca", "IEC - Monteiro",
        "IEC - Sertânia", "IEC - Santa Luzia do Cariri", "IEC - São José dos Cordeiros",
        "IEC - Coxixola", "IEC - Assentamento Mandacaru",
    ],
    "Região Curimataú": [
        "IEC - Canoa de Dentro", "IEC - Baraúna", "IEC - Sossego", "IEC - Alto do Umbuzeiro",
        "IEC - Pedra Lavrada", "IEC - Soledade",
    ],
    "Região Metropolitana": [
        "IEC - Capim Grande", "IEC - Fagundes", "IEC - Itatuba", "IEC - São Tomé",
        "IEC - Puxinanã", "IEC - Queimadas", "IEC - Ronaldo Cunha Lima",
        "IEC - Santa Terezinha", "IEC - Sítio Rafael", "IEC - Sítio Bastiões",
        "IEC - Galante", "IEC - Chã de Galante",
    ],
    "Região Nacional/Internacional": [
        "IEC - Juliana/BH", "IEC - Juazeiro do Norte/CE", "IEC - Guadalajara/MX",
    ],
}

PLANILHA_URL = "https://docs.google.com/spreadsheets/d/1XEJ5z3hSdbfGEdeJFljZgZwBqYtuiI3zh6H9bLAT4ks/edit?usp=sharing"

if "logado" not in st.session_state:
    st.session_state["logado"] = False
if "sub_lideranca" not in st.session_state:
    st.session_state["sub_lideranca"] = "Choques de agenda"
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

    /* ---------- Título do painel, submenu e botão de link ---------- */
    .block-container h1.titulo-sem-linha {border-bottom: none; padding-bottom: 0; margin: 0;}
    .block-container hr.linha-titulo {border: none; border-top: 2px solid #DDE3EC; margin: .6rem 0 1.4rem 0;}

    section[data-testid="stSidebar"] [class*="st-key-sub_"] button {
        padding-left: 2rem !important; font-size: .9rem !important;
    }

    .block-container a[data-testid^="stBaseLinkButton"] {
        background: #FFFFFF !important; border: 1.5px solid #1E3A8A !important;
        border-radius: 6px !important; padding: .55rem 1.4rem !important;
        text-decoration: none !important; transition: background .15s;
    }
    .block-container a[data-testid^="stBaseLinkButton"],
    .block-container a[data-testid^="stBaseLinkButton"] * {
        color: #1E3A8A !important; font-weight: 600 !important;
    }
    .block-container a[data-testid^="stBaseLinkButton"]:hover {background: #1E3A8A !important;}
    .block-container a[data-testid^="stBaseLinkButton"]:hover * {color: #FFFFFF !important;}
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


@st.cache_data(ttl=300)
def carregar_congregacoes():
    """Lê a lista de congregações de uma aba da planilha cujo nome contenha 'congrega'.
    Aceita dois formatos:
      A) colunas 'Região' e 'Congregação' (uma congregação por linha);
      B) uma coluna por região (o título é a região, as células são as congregações).
    """
    try:
        credenciais = json.loads(st.secrets["google_credentials"])
        gc = gspread.service_account_from_dict(credenciais)
        planilha = gc.open_by_url(PLANILHA_URL)
        aba = None
        for ws in planilha.worksheets()[1:]:
            if "congrega" in _norm(ws.title):
                aba = ws
                break
        if aba is None:
            return {}
        dados = aba.get_all_values()
        if not dados:
            return {}
        cab = [c.strip() for c in dados[0]]
        cabn = [_norm(c) for c in cab]
        ir = next((i for i, c in enumerate(cabn) if "regiao" in c), None)
        ic = next((i for i, c in enumerate(cabn) if "congrega" in c and "regiao" not in c), None)
        res = {}
        if ir is not None and ic is not None:
            for linha in dados[1:]:
                if len(linha) > max(ir, ic) and linha[ir].strip() and linha[ic].strip():
                    res.setdefault(linha[ir].strip(), []).append(linha[ic].strip())
        else:
            for i, regiao in enumerate(cab):
                if not regiao:
                    continue
                nomes = [l[i].strip() for l in dados[1:] if len(l) > i and l[i].strip()]
                if nomes:
                    res[regiao] = nomes
        return {k: sorted(set(v)) for k, v in res.items()}
    except Exception:
        return {}


def salvar_congregacao(regiao, nome):
    credenciais = json.loads(st.secrets["google_credentials"])
    gc = gspread.service_account_from_dict(credenciais)
    planilha = gc.open_by_url(PLANILHA_URL)
    aba = next((ws for ws in planilha.worksheets()[1:] if "congrega" in _norm(ws.title)), None)
    if aba is None:
        aba = planilha.add_worksheet(title="Congregações", rows=200, cols=2)
        aba.append_row(["Região", "Congregação"])
    aba.append_row([regiao, nome])


def lista_de_congregacoes():
    """Lista base do código + congregações cadastradas na planilha."""
    mapa = {r: list(v) for r, v in CONGREGACOES_POR_REGIAO.items()}
    for regiao, nomes in carregar_congregacoes().items():
        alvo = next((r for r in mapa if _norm(r) == _norm(regiao)), regiao)
        mapa.setdefault(alvo, [])
        existentes = {_norm(x) for x in mapa[alvo]}
        for n in nomes:
            if _norm(n) not in existentes:
                mapa[alvo].append(n)
                existentes.add(_norm(n))
    return {r: sorted(v) for r, v in mapa.items()}


def salvar_lote_no_banco(dados_novos_lista):
    _abrir_aba().append_rows(dados_novos_lista)


# =====================================================================
# 3b. REGRAS DE AGENDA (PRIORIDADE E CHOQUES)
# =====================================================================
# Prioridade: 1 = Alta (aniversário de congregação), 2 = Média (aniversário
# de UAC/UHC), 3 = Baixa (demais atividades).
# Choque: datas que se sobrepõem E (mesma região OU um dos eventos é
# aniversário de congregação, que não pode coincidir com nada, nem em
# regiões diferentes).
NOME_PRIORIDADE = {1: "Alta", 2: "Média", 3: "Baixa"}


def _norm(texto):
    return unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode().lower().strip()


def peso_evento(tipo):
    t = _norm(tipo)
    if "aniversario" in t and "congrega" in t:
        return 1
    if "aniversario" in t and ("uac" in t or "uhc" in t):
        return 2
    return 3


def _para_data(valor):
    return pd.to_datetime(valor, dayfirst=True, errors="coerce")


def _registro(nome, regiao, tipo, inicio, fim, origem):
    ini = _para_data(inicio)
    if pd.isna(ini):
        return None
    f = _para_data(fim)
    if pd.isna(f) or f < ini:
        f = ini
    return {"nome": str(nome), "regiao": str(regiao), "tipo": str(tipo),
            "ini": ini, "fim": f, "peso": peso_evento(tipo), "origem": origem}


def registros_da_planilha(df_base):
    regs = []
    if df_base is None or df_base.empty:
        return regs
    for _, r in df_base.iterrows():
        reg = _registro(
            r.get("Nome da Festividade", ""), r.get("Região da Congregação", ""),
            r.get("Tipo de Festividade", ""), r.get("Data de Inicio da Festividade"),
            r.get("Data Final da Festividade"), "Planilha",
        )
        if reg:
            regs.append(reg)
    return regs


def registros_da_fila():
    regs = []
    for e in st.session_state["eventos_temporarios"]:
        reg = _registro(e["Festividade"], e["Regiao"], e["Tipo"], e["Inicio"], e["Fim"], "Fila")
        if reg:
            regs.append(reg)
    return regs


def motivo_do_choque(a, b):
    if not (a["ini"] <= b["fim"] and b["ini"] <= a["fim"]):
        return None
    ra, rb = _norm(a["regiao"]), _norm(b["regiao"])
    if ra and ra == rb:
        return "Mesma região"
    if a["peso"] == 1 or b["peso"] == 1:
        return "Aniversário de congregação"
    return None


def choques_do_novo(novo, base):
    return [(b, m) for b in base if (m := motivo_do_choque(novo, b))]


def todos_os_choques(regs):
    pares = []
    for i in range(len(regs)):
        for j in range(i + 1, len(regs)):
            m = motivo_do_choque(regs[i], regs[j])
            if m:
                pares.append((regs[i], regs[j], m))
    return pares


def descrever(reg):
    ini, fim = reg["ini"].strftime("%d/%m/%Y"), reg["fim"].strftime("%d/%m/%Y")
    periodo = ini if ini == fim else f"{ini} a {fim}"
    return f"{reg['nome']} ({reg['regiao']}, {periodo})"


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
    SUBMENU_LIDERANCA = [("Choques de agenda", "sub_choques"), ("Congregações", "sub_congregacoes")]
    pagina_atual = st.session_state["pagina"]
    for nome_pag in PAGINAS:
        eh_lideranca = nome_pag == "Área da liderança"
        ativo = pagina_atual == nome_pag and not (eh_lideranca and st.session_state["logado"])
        if st.button(nome_pag, key=f"menu_{nome_pag}",
                     type="primary" if ativo else "secondary",
                     use_container_width=True):
            st.session_state["pagina"] = nome_pag
            st.rerun()
        if eh_lideranca and st.session_state["logado"]:
            for rotulo, chave in SUBMENU_LIDERANCA:
                ativo_sub = pagina_atual == "Área da liderança" and st.session_state["sub_lideranca"] == rotulo
                if st.button(f"› {rotulo}", key=chave,
                             type="primary" if ativo_sub else "secondary",
                             use_container_width=True):
                    st.session_state["pagina"] = "Área da liderança"
                    st.session_state["sub_lideranca"] = rotulo
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
            publico["Prioridade"] = publico["Tipo de Festividade"].map(lambda t: NOME_PRIORIDADE[peso_evento(t)])

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
                    "Prioridade": st.column_config.TextColumn("Prioridade"),
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
        resp = st.session_state.get("responsavel")
        editando = st.session_state.get("editando_resp", False)

        # -------------------------------------------------------------
        # ETAPA 1: dados do responsável (preenchidos uma única vez)
        # -------------------------------------------------------------
        if not resp or editando:
            st.markdown("#### Etapa 1 de 2: seus dados")
            st.caption("Preencha uma vez. Depois você poderá cadastrar quantos eventos quiser.")
            with st.form("form_responsavel"):
                nome_r = st.text_input("Nome completo", value=resp["nome"] if resp else "")
                cargo_r = st.selectbox(
                    "Cargo/Função", CARGOS,
                    index=CARGOS.index(resp["cargo"]) if resp and resp["cargo"] in CARGOS else 0,
                )
                whats_r = st.text_input("WhatsApp para contato", value=resp["whats"] if resp else "",
                                        placeholder="(83) 9 0000-0000")
                continuar = st.form_submit_button("Continuar")
            if continuar:
                if nome_r.strip() == "":
                    st.error("Informe o nome completo.")
                elif cargo_r == "":
                    st.error("Selecione o cargo ou função.")
                elif len(re.sub(r"\D", "", whats_r)) < 10:
                    st.error("Informe um WhatsApp válido, com DDD.")
                else:
                    st.session_state["responsavel"] = {
                        "nome": nome_r.strip(), "cargo": cargo_r, "whats": whats_r.strip(),
                    }
                    st.session_state["editando_resp"] = False
                    st.rerun()

        # -------------------------------------------------------------
        # ETAPA 2: cadastro dos eventos
        # -------------------------------------------------------------
        else:
            nome, cargo, whatsapp = resp["nome"], resp["cargo"], resp["whats"]

            with st.container(border=True):
                r1, r2 = st.columns([5, 1], vertical_alignment="center")
                r1.markdown(f"**Responsável:** {nome} · {cargo} · {whatsapp}")
                if r2.button("Alterar dados", use_container_width=True):
                    st.session_state["editando_resp"] = True
                    st.rerun()

            with st.expander("Regras de agenda e prioridade"):
                st.markdown(
                    "- **Prioridade alta:** aniversário de congregação.\n"
                    "- **Prioridade média:** aniversário de UAC e de UHC.\n"
                    "- **Prioridade baixa:** demais atividades.\n"
                    "- **Mesma região:** não pode haver eventos em datas que se sobrepõem.\n"
                    "- **Regiões diferentes:** os eventos podem coincidir, exceto aniversários "
                    "de congregação, que não podem coincidir com nenhum outro evento.\n"
                    "- Um evento de prioridade maior pode ocupar a data de um de prioridade menor. "
                    "Nesse caso, o menor fica sinalizado para remanejamento na área da liderança."
                )

            st.markdown("#### Etapa 2 de 2: congregação e evento")
            mapa_congregacoes = lista_de_congregacoes()
            if not any(mapa_congregacoes.values()):
                st.warning("A lista de congregações não foi encontrada na planilha. "
                           "Use a opção 'Outra congregação' para digitar o nome.")
            l1, l2 = st.columns(2)
            regiao = l1.selectbox(
                "Região da congregação", [""] + list(mapa_congregacoes.keys()), key="cad_regiao"
            )
            opcoes = (sorted(mapa_congregacoes.get(regiao, [])) + [OUTRA_CONGREGACAO]) if regiao else []
            congregacao = l2.selectbox(
                "Congregação", [""] + opcoes, key=f"cad_congregacao_{regiao}", disabled=not regiao,
                placeholder="Escolha a região primeiro" if not regiao else "Escolha a congregação",
            )
            if congregacao == OUTRA_CONGREGACAO:
                congregacao = st.text_input("Nome da congregação", key=f"cad_outra_{regiao}")

            # Depois de adicionar um evento, limpa só os campos do evento.
            if st.session_state.pop("limpar_evento", False):
                for k in ("cad_festividade", "cad_tipo", "cad_data_inicio", "cad_data_fim"):
                    st.session_state.pop(k, None)
            msg_cadastro = st.session_state.pop("msg_cadastro", None)
            if msg_cadastro:
                (st.warning if msg_cadastro[0] == "warning" else st.success)(msg_cadastro[1])

            with st.form("form_evento", clear_on_submit=False):
                festividade = st.text_input("Nome da festividade", key="cad_festividade")
                f1, f2, f3 = st.columns(3)
                tipo = f1.selectbox(
                    "Tipo de festividade",
                    ["", "Aniversário de Congregação", "Aniversário de UAC", "Aniversário de UHC",
                     "Aniversário de Demais Departamento", "Culto de Intercâmbio", "Evangelismo", "Outros"],
                    key="cad_tipo",
                )
                data_inicio = f2.date_input("Data de início", format="DD/MM/YYYY", key="cad_data_inicio")
                data_fim = f3.date_input("Data final", format="DD/MM/YYYY", key="cad_data_fim")

                adicionar_btn = st.form_submit_button("Adicionar à fila")
                if adicionar_btn:
                    if festividade.strip() == "":
                        st.error("Informe o nome da festividade.")
                    elif regiao == "":
                        st.error("Selecione a região da congregação.")
                    elif congregacao.strip() == "":
                        st.error("Selecione ou informe a congregação.")
                    elif tipo == "":
                        st.error("Selecione o tipo de festividade.")
                    elif data_fim < data_inicio:
                        st.error("A data final não pode ser anterior à data de início.")
                    else:
                        novo = _registro(
                            festividade, regiao, tipo,
                            data_inicio.strftime("%d/%m/%Y"), data_fim.strftime("%d/%m/%Y"), "Novo",
                        )
                        base = registros_da_planilha(df) + registros_da_fila()
                        conflitos = choques_do_novo(novo, base)
                        impeditivos = [(c, m) for c, m in conflitos if c["peso"] <= novo["peso"]]
                        if impeditivos:
                            c, m = impeditivos[0]
                            st.error(
                                f"Choque de datas ({m.lower()}): já existe {descrever(c)}, "
                                f"com prioridade {NOME_PRIORIDADE[c['peso']].lower()}. Escolha outra data."
                            )
                        else:
                            st.session_state["eventos_temporarios"].append({
                                "Nome": nome, "Cargo": cargo, "Whats": whatsapp, "Regiao": regiao,
                                "Congregacao": congregacao, "Festividade": festividade.strip(), "Tipo": tipo,
                                "Inicio": data_inicio.strftime("%d/%m/%Y"), "Fim": data_fim.strftime("%d/%m/%Y"),
                            })
                            if conflitos:
                                nomes = "; ".join(descrever(c) for c, _ in conflitos)
                                st.session_state["msg_cadastro"] = (
                                    "warning",
                                    "Evento adicionado à fila. Ele tem prioridade maior e ocupa a data de: "
                                    f"{nomes}. A liderança será avisada para remanejar.",
                                )
                            else:
                                st.session_state["msg_cadastro"] = (
                                    "success", "Evento adicionado à fila. Você pode cadastrar o próximo evento.")
                            st.session_state["limpar_evento"] = True
                            st.rerun()

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
                carregar_dados.clear()
                base_atual = registros_da_planilha(carregar_dados())
                problemas = []
                for e in st.session_state["eventos_temporarios"]:
                    novo = _registro(e["Festividade"], e["Regiao"], e["Tipo"], e["Inicio"], e["Fim"], "Fila")
                    for c, m in choques_do_novo(novo, base_atual):
                        if c["peso"] <= novo["peso"]:
                            problemas.append(f"{descrever(novo)} conflita com {descrever(c)}")
                if problemas:
                    st.error("Nada foi enviado. Outro evento ocupou estas datas enquanto você preenchia:\n\n- "
                             + "\n- ".join(problemas))
                else:
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
                        st.session_state["msg_login"] = True
                        st.rerun()
                    else:
                        st.error("Senha incorreta. Tente novamente.")
        else:
            if st.session_state.pop("msg_login", False):
                try:
                    st.toast("Autenticação realizada com sucesso.", icon="✅", duration=3)
                except TypeError:
                    st.toast("Autenticação realizada com sucesso.", icon="✅")

            t1, t2 = st.columns([5, 1], vertical_alignment="center")
            t1.markdown('<h1 class="titulo-sem-linha">Painel administrativo</h1>', unsafe_allow_html=True)
            if t2.button("Sair", use_container_width=True):
                st.session_state["logado"] = False
                st.rerun()
            st.markdown('<hr class="linha-titulo">', unsafe_allow_html=True)

            if st.session_state["sub_lideranca"] == "Choques de agenda":
                if not df.empty:
                    st.markdown("#### Choques de agenda")
                    pares = todos_os_choques(registros_da_planilha(df))
                    if pares:
                        st.error(f"Foram detectados {len(pares)} choque(s) de agenda.")
                        linhas = []
                        for a_, b_, motivo in pares:
                            if a_["peso"] < b_["peso"]:
                                remanejar = descrever(b_)
                            elif b_["peso"] < a_["peso"]:
                                remanejar = descrever(a_)
                            else:
                                remanejar = "Mesma prioridade: a liderança define"
                            linhas.append({
                                "Evento A": descrever(a_), "Prioridade A": NOME_PRIORIDADE[a_["peso"]],
                                "Evento B": descrever(b_), "Prioridade B": NOME_PRIORIDADE[b_["peso"]],
                                "Motivo": motivo, "Deve remanejar": remanejar,
                            })
                        st.dataframe(pd.DataFrame(linhas), use_container_width=True, hide_index=True)
                    else:
                        st.success("A agenda está limpa. Nenhum choque detectado.")

                    st.markdown("#### Alteração de datas")
                    st.info(
                        "Para evitar alterações acidentais, correções de data são feitas diretamente "
                        "no banco de dados central (Google Planilhas)."
                    )
                    st.link_button("Abrir planilha do banco de dados", PLANILHA_URL)


            else:
                mapa_atual = lista_de_congregacoes()
                total = sum(len(v) for v in mapa_atual.values())
                st.markdown("#### Cadastrar nova congregação")
                with st.form("form_nova_congregacao", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    regiao_nova = c1.selectbox("Região", [""] + list(mapa_atual.keys()))
                    nome_nova = c2.text_input("Nome da congregação", placeholder="Ex.: IEC - Nome da cidade")
                    salvar_cong = st.form_submit_button("Cadastrar congregação")
                if salvar_cong:
                    nome_limpo = nome_nova.strip()
                    if regiao_nova == "" or nome_limpo == "":
                        st.error("Escolha a região e informe o nome da congregação.")
                    elif _norm(nome_limpo) in {_norm(x) for x in mapa_atual.get(regiao_nova, [])}:
                        st.error("Essa congregação já está cadastrada nesta região.")
                    else:
                        salvar_congregacao(regiao_nova, nome_limpo)
                        carregar_congregacoes.clear()
                        st.success(f"Congregação cadastrada em {regiao_nova}.")
                        mapa_atual = lista_de_congregacoes()
                        total = sum(len(v) for v in mapa_atual.values())

                st.markdown(f"#### Congregações cadastradas ({total})")
                for reg, nomes in mapa_atual.items():
                    with st.expander(f"{reg} ({len(nomes)})"):
                        st.write("\n".join(f"- {n}" for n in nomes) if nomes else "Nenhuma congregação.")

except Exception as e:
    st.error(f"Erro de execução: {e}")
