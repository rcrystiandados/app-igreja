import streamlit as st
import pandas as pd
import altair as alt
import gspread
from datetime import date, datetime, timedelta
import json
import re
import unicodedata

try:
    import exportacao
    EXPORT_OK, EXPORT_ERRO = True, ""
except Exception as _erro_import:  # arquivo exportacao.py ausente no repositório
    EXPORT_OK, EXPORT_ERRO = False, str(_erro_import)

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
    st.session_state["sub_lideranca"] = "Painel inicial"
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

    /* ---------- Bloco de exportação em destaque ---------- */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.marca-exportar) {
        background: #F3F7FF; border: 2px solid #1E3A8A !important;
        border-left: 8px solid #1E3A8A !important; border-radius: 12px;
        box-shadow: 0 4px 14px rgba(30,58,138,.15); padding: .6rem .8rem;
    }
    .exp-topo {display: flex; align-items: center; gap: .9rem; margin-bottom: .6rem;}
    .exp-icone {
        width: 46px; height: 46px; border-radius: 50%; background: #1E3A8A; color: #FFFFFF;
        display: flex; align-items: center; justify-content: center; font-size: 1.4rem; flex: none;
    }
    .exp-titulo {font-size: 1.25rem; font-weight: 700; color: #1E3A8A; line-height: 1.2;}
    .exp-sub {font-size: .9rem; color: #475569;}
    div[data-testid="stDownloadButton"] button {
        background-color: #2E7D5B !important; border: none !important; border-radius: 6px !important;
        padding: .65rem 1.6rem !important; font-weight: 700 !important;
    }
    div[data-testid="stDownloadButton"] button, div[data-testid="stDownloadButton"] button * {color: #FFFFFF !important;}
    div[data-testid="stDownloadButton"] button:hover {background-color: #256649 !important;}

    /* ---------- Blocos da página inicial da liderança ---------- */
    .adm-card {padding: .2rem .2rem .4rem .2rem;}
    .adm-tit {font-size: 1.15rem; font-weight: 700; color: #1E3A8A; margin-bottom: .5rem;}
    .adm-num {font-size: 2.6rem; font-weight: 700; line-height: 1;}
    .adm-lbl {font-size: .8rem; text-transform: uppercase; letter-spacing: .04em; color: #64748B; margin: .2rem 0 .6rem 0;}
    .adm-desc {font-size: .92rem; color: #475569; min-height: 2.6rem;}
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
    """Lê a planilha como texto e guarda o número da linha (coluna _linha) de cada evento."""
    valores = _abrir_aba().get_all_values()
    if len(valores) < 2:
        return pd.DataFrame()
    cab = [c.strip() for c in valores[0]]
    linhas = []
    for numero, l in enumerate(valores[1:], start=2):
        if not any(str(c).strip() for c in l):
            continue
        l = (list(l) + [""] * len(cab))[:len(cab)]
        linhas.append(l + [numero])
    return pd.DataFrame(linhas, columns=cab + ["_linha"])


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
    """Grava logo abaixo da última linha preenchida da coluna A (carimbo de data/hora).
    Não usa a detecção automática de tabela, que sobrescrevia linhas existentes."""
    if not dados_novos_lista:
        return
    aba = _abrir_aba()
    proxima = len(aba.col_values(1)) + 1
    ultima = proxima + len(dados_novos_lista) - 1
    if ultima > aba.row_count:
        aba.add_rows(ultima - aba.row_count)
    aba.update(values=dados_novos_lista, range_name=f"A{proxima}", value_input_option="RAW")


# =====================================================================
# 3b. REGRAS DE AGENDA (PRIORIDADE E CHOQUES)
# =====================================================================
# Prioridade: 1 = Alta (aniversário de congregação), 2 = Média (aniversário
# de UAC/UHC), 3 = Baixa (demais atividades).
# Choque: datas que se sobrepõem E (mesma região OU um dos eventos é
# aniversário de congregação, que não pode coincidir com nada, nem em
# regiões diferentes).
NOME_PRIORIDADE = {1: "Alta", 2: "Média", 3: "Baixa"}


def _formatar_whats():
    """Formata o campo de WhatsApp como (83) 9 9962-3735 ao sair do campo."""
    d = re.sub(r"\D", "", st.session_state.get("resp_whats", ""))
    if d.startswith("55") and len(d) > 11:
        d = d[2:]
    d = d[:11]
    if len(d) == 11:
        f = f"({d[:2]}) {d[2]} {d[3:7]}-{d[7:]}"
    elif len(d) == 10:
        f = f"({d[:2]}) {d[2:6]}-{d[6:]}"
    elif len(d) > 2:
        f = f"({d[:2]}) {d[2:]}"
    else:
        f = d
    st.session_state["resp_whats"] = f


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


def _registro(nome, regiao, tipo, inicio, fim, origem, linha=None, congregacao=""):
    ini = _para_data(inicio)
    if pd.isna(ini):
        return None
    f = _para_data(fim)
    if pd.isna(f) or f < ini:
        f = ini
    return {"nome": str(nome), "regiao": str(regiao), "tipo": str(tipo),
            "ini": ini, "fim": f, "peso": peso_evento(tipo), "origem": origem, "linha": linha,
            "congregacao": str(congregacao).strip()}


def registros_da_planilha(df_base):
    regs = []
    if df_base is None or df_base.empty:
        return regs
    for _, r in df_base.iterrows():
        reg = _registro(
            r.get("Nome da Festividade", ""), r.get("Região da Congregação", ""),
            r.get("Tipo de Festividade", ""), r.get("Data de Inicio da Festividade"),
            r.get("Data Final da Festividade"), "Planilha",
            int(r["_linha"]) if "_linha" in r and str(r["_linha"]).strip() != "" else None,
            r.get("Congregação", ""),
        )
        if reg:
            regs.append(reg)
    return regs


def registros_da_fila():
    regs = []
    for e in st.session_state["eventos_temporarios"]:
        reg = _registro(e["Festividade"], e["Regiao"], e["Tipo"], e["Inicio"], e["Fim"], "Fila",
                       congregacao=e.get("Congregacao", ""))
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
    local = " · ".join(x for x in (reg.get("congregacao", ""), reg["regiao"]) if x)
    return f"{reg['nome']} ({local}, {periodo})" if local else f"{reg['nome']} ({periodo})"


# =====================================================================
# 3d. FERIADOS, SUGESTÃO DE DATAS E AJUSTE
# =====================================================================
# Feriados fixos locais. Edite esta lista para incluir feriados de outras cidades.
FERIADOS_LOCAIS_FIXOS = {
    (6, 24): "São João (feriado em Campina Grande)",
    (8, 5): "Fundação da Paraíba (feriado estadual)",
    (10, 11): "Aniversário de Campina Grande (feriado municipal)",
}
DIAS_SEMANA = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


def _pascoa(ano):
    a, b, c = ano % 19, ano // 100, ano % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    return date(ano, mes, dia)


def feriados_do_ano(ano):
    p = _pascoa(ano)
    f = {
        date(ano, 1, 1): "Confraternização Universal",
        p - timedelta(days=48): "Carnaval (ponto facultativo)",
        p - timedelta(days=47): "Carnaval (ponto facultativo)",
        p - timedelta(days=2): "Sexta-feira Santa",
        p: "Páscoa",
        date(ano, 4, 21): "Tiradentes",
        date(ano, 5, 1): "Dia do Trabalho",
        p + timedelta(days=60): "Corpus Christi",
        date(ano, 9, 7): "Independência do Brasil",
        date(ano, 10, 12): "Nossa Senhora Aparecida",
        date(ano, 11, 2): "Finados",
        date(ano, 11, 15): "Proclamação da República",
        date(ano, 11, 20): "Consciência Negra",
        date(ano, 12, 24): "Véspera de Natal (ponto facultativo)",
        date(ano, 12, 25): "Natal",
        date(ano, 12, 31): "Véspera de Ano-Novo (ponto facultativo)",
    }
    for (m, d), nome in FERIADOS_LOCAIS_FIXOS.items():
        f[date(ano, m, d)] = nome
    return f


def feriados_no_periodo(ini, fim):
    achados = []
    for ano in range(ini.year, fim.year + 1):
        for d, nome in feriados_do_ano(ano).items():
            if ini <= d <= fim:
                achados.append((d, nome))
    return sorted(achados)


def fmt_data(d):
    return f"{d:%d/%m/%Y} ({DIAS_SEMANA[d.weekday()]})"


def fmt_periodo(ini, fim):
    return fmt_data(ini) if ini == fim else f"{fmt_data(ini)} a {fmt_data(fim)}"


def sugerir_datas(alvo, todos, evitar_feriados=True, mesmo_dia_semana=True, limite=6, janela=180):
    """Datas livres, com a mesma duração do evento, mais próximas da data original.
    Respeita as regras de choque da região, os aniversários de congregação e os feriados."""
    duracao = alvo["fim"] - alvo["ini"]
    hoje = pd.Timestamp.today().normalize()
    outros = [r for r in todos if r.get("linha") != alvo.get("linha")]
    sugestoes = []
    for delta in sorted(range(-janela, janela + 1), key=lambda x: (abs(x), x)):
        if delta == 0 or (mesmo_dia_semana and delta % 7 != 0):
            continue
        ini = alvo["ini"] + pd.Timedelta(days=delta)
        fim = ini + duracao
        if ini < hoje or ini.year != alvo["ini"].year or fim.year != alvo["ini"].year:
            continue
        cand = dict(alvo, ini=ini, fim=fim)
        if any(motivo_do_choque(cand, o) for o in outros):
            continue
        if evitar_feriados and feriados_no_periodo(ini.date(), fim.date()):
            continue
        sugestoes.append({"ini": ini, "fim": fim, "delta": delta})
        if len(sugestoes) >= limite:
            break
    return sugestoes


def atualizar_datas_planilha(alvo, novo_ini, novo_fim, motivo):
    """Grava as novas datas na linha do evento e registra a alteração na aba 'Alterações de datas'."""
    from gspread.utils import rowcol_to_a1
    aba = _abrir_aba()
    cab = [c.strip() for c in aba.row_values(1)]
    ci = cab.index("Data de Inicio da Festividade") + 1
    cf = cab.index("Data Final da Festividade") + 1
    cn = cab.index("Nome da Festividade") + 1
    linha = alvo["linha"]
    atual = aba.row_values(linha)
    atual += [""] * (max(ci, cf, cn) - len(atual))
    ini_antigo, fim_antigo = alvo["ini"].strftime("%d/%m/%Y"), alvo["fim"].strftime("%d/%m/%Y")
    if (atual[cn - 1].strip() != alvo["nome"].strip()
            or _para_data(atual[ci - 1]) != alvo["ini"]):
        raise ValueError("A planilha foi alterada por outra pessoa. Recarregue a página e tente de novo.")
    aba.batch_update(
        [{"range": rowcol_to_a1(linha, ci), "values": [[novo_ini.strftime("%d/%m/%Y")]]},
         {"range": rowcol_to_a1(linha, cf), "values": [[novo_fim.strftime("%d/%m/%Y")]]}],
        value_input_option="RAW",
    )
    planilha = aba.spreadsheet
    try:
        hist = planilha.worksheet("Alterações de datas")
    except gspread.WorksheetNotFound:
        hist = planilha.add_worksheet(title="Alterações de datas", rows=200, cols=7)
        hist.append_row(["Data da alteração", "Festividade", "Região", "Início anterior",
                         "Fim anterior", "Novo início", "Novo fim", "Motivo"])
    hist.append_row([
        datetime.now().strftime("%d/%m/%Y %H:%M:%S"), alvo["nome"], alvo["regiao"],
        ini_antigo, fim_antigo, novo_ini.strftime("%d/%m/%Y"), novo_fim.strftime("%d/%m/%Y"), motivo,
    ], value_input_option="RAW")


def painel_ajuste_datas(df_base):
    regs = registros_da_planilha(df_base)
    regs = [r for r in regs if r["linha"] is not None]
    if not regs:
        st.info("Não há eventos cadastrados para ajustar.")
        return

    # aplica a data escolhida nas sugestões (antes de criar os campos de data)
    pend = st.session_state.pop("aj_pendente", None)
    if pend:
        st.session_state["aj_ini"], st.session_state["aj_fim"] = pend
    msg = st.session_state.pop("aj_msg", None)
    if msg:
        st.success(msg)

    pares = todos_os_choques(regs)
    em_choque = {x["linha"] for a_, b_, _m in pares for x in (a_, b_)}

    st.markdown("#### 1. Escolha o evento")
    so_choques = st.checkbox("Mostrar apenas eventos com choque de data", value=bool(em_choque),
                             key="aj_so_choques", disabled=not em_choque)
    lista = [r for r in regs if (r["linha"] in em_choque or not so_choques)]
    lista.sort(key=lambda r: (r["ini"], r["nome"]))
    if not lista:
        st.info("Nenhum evento para mostrar.")
        return
    por_linha = {r["linha"]: r for r in lista}

    def rotulo(linha):
        r = por_linha[linha]
        marca = "  [CHOQUE]" if linha in em_choque else ""
        local = " · ".join(x for x in (r["congregacao"], r["regiao"]) if x)
        return f"{r['ini']:%d/%m/%Y} · {r['nome']} · {local}{marca}"

    escolhido = st.selectbox("Evento", list(por_linha.keys()), format_func=rotulo, key="aj_evento")
    alvo = por_linha[escolhido]
    outros = [r for r in regs if r["linha"] != alvo["linha"]]

    if (st.session_state.get("aj_ultimo") != escolhido
            or "aj_ini" not in st.session_state or "aj_fim" not in st.session_state):
        st.session_state["aj_ultimo"] = escolhido
        st.session_state["aj_ini"] = alvo["ini"].date()
        st.session_state["aj_fim"] = alvo["fim"].date()

    with st.container(border=True):
        st.markdown(
            f"**{alvo['nome']}**  \n{alvo['tipo']} · prioridade **{NOME_PRIORIDADE[alvo['peso']].lower()}**  \n"
            f"{alvo['congregacao'] or '-'} · {alvo['regiao']}  \n"
            f"Período atual: **{fmt_periodo(alvo['ini'].date(), alvo['fim'].date())}**"
        )
    atuais = choques_do_novo(alvo, outros)
    if atuais:
        st.warning("Este evento está em choque com:\n\n" + "\n".join(
            f"- {descrever(c)}  ({m.lower()}, prioridade {NOME_PRIORIDADE[c['peso']].lower()})" for c, m in atuais))
    else:
        st.success("Este evento não tem choque de datas.")

    # ---------------- sugestões ----------------
    st.markdown("#### 2. Datas sugeridas")
    o1, o2 = st.columns(2)
    evitar = o1.checkbox("Evitar feriados e pontos facultativos", value=True, key="aj_feriados")
    manter = o2.checkbox("Manter o mesmo dia da semana", value=True, key="aj_semana")
    sugestoes = sugerir_datas(alvo, regs, evitar_feriados=evitar, mesmo_dia_semana=manter)
    if not sugestoes:
        st.info("Não encontrei datas livres neste ano com essas opções. Tente desmarcar uma delas "
                "ou escolha a data manualmente abaixo.")
    for i, sg in enumerate(sugestoes):
        dias = abs(sg["delta"])
        quando = f"{dias} dia(s) {'depois' if sg['delta'] > 0 else 'antes'}"
        with st.container(border=True):
            c1, c2, c3 = st.columns([5, 2, 1.4], vertical_alignment="center")
            c1.markdown(f"**{fmt_periodo(sg['ini'].date(), sg['fim'].date())}**")
            c2.caption(f"{quando} · sem choques" + (" e sem feriados" if evitar else ""))
            if c3.button("Escolher", key=f"aj_sug_{i}", use_container_width=True):
                st.session_state["aj_pendente"] = (sg["ini"].date(), sg["fim"].date())
                st.rerun()

    # ---------------- ajuste manual ----------------
    st.markdown("#### 3. Confirme a nova data")
    d1, d2 = st.columns(2)
    novo_ini = d1.date_input("Nova data de início", format="DD/MM/YYYY", key="aj_ini")
    if st.session_state.get("aj_fim") is None or st.session_state["aj_fim"] < novo_ini:
        st.session_state["aj_fim"] = novo_ini
    novo_fim = d2.date_input("Nova data final", format="DD/MM/YYYY", min_value=novo_ini, key="aj_fim")

    cand = dict(alvo, ini=pd.Timestamp(novo_ini), fim=pd.Timestamp(novo_fim))
    conflitos = choques_do_novo(cand, outros)
    feriados = feriados_no_periodo(novo_ini, novo_fim)
    if conflitos:
        st.error("A nova data entra em choque com:\n\n" + "\n".join(
            f"- {descrever(c)}  ({m.lower()})" for c, m in conflitos))
    else:
        st.success("A nova data não tem choque com a agenda.")
    if feriados:
        st.warning("Feriados no período: " + "; ".join(f"{d:%d/%m} ({n})" for d, n in feriados) + ".")
    if pd.Timestamp(novo_ini) < pd.Timestamp.today().normalize():
        st.warning("A nova data de início já passou.")

    motivo = st.text_input("Motivo da alteração (opcional)", key="aj_motivo",
                           placeholder="Ex.: choque com aniversário de congregação")
    confirma = True
    if conflitos:
        confirma = st.checkbox("Salvar mesmo com choque de datas", key="aj_confirma")
    igual = novo_ini == alvo["ini"].date() and novo_fim == alvo["fim"].date()
    if st.button("Salvar nova data", disabled=igual or not confirma):
        try:
            atualizar_datas_planilha(alvo, novo_ini, novo_fim, motivo.strip())
        except Exception as erro:
            st.error(f"Não foi possível salvar: {erro}")
        else:
            st.cache_data.clear()
            st.session_state.pop("aj_ultimo", None)
            st.session_state["aj_msg"] = (
                f"Datas de \"{alvo['nome']}\" atualizadas para {fmt_periodo(novo_ini, novo_fim)}."
            )
            st.rerun()


def painel_inicial_lideranca(df_base):
    """Página inicial da liderança: blocos com atalho para cada área."""
    regs = registros_da_planilha(df_base)
    pares = todos_os_choques(regs)
    em_choque = {x["linha"] for a_, b_, _m in pares for x in (a_, b_) if x["linha"] is not None}
    mapa = lista_de_congregacoes()
    n_cong = sum(len(v) for v in mapa.values())

    verde, vermelho, azul = "#2E7D5B", "#C0392B", "#1E3A8A"
    blocos = [
        ("Choques de agenda", "Choques de agenda", len(pares),
         "choque(s) detectado(s)" if pares else "nenhum choque detectado",
         "Veja quais eventos se sobrepõem e qual deve ser remanejado.",
         vermelho if pares else verde),
        ("Ajustar datas", "Ajustar datas", len(em_choque),
         "evento(s) para remarcar" if em_choque else "nenhum evento para remarcar",
         "Remarque um evento com sugestões de datas livres e sem feriados.",
         vermelho if em_choque else verde),
        ("Congregações", "Congregações", n_cong,
         f"congregações em {len(mapa)} regiões",
         "Cadastre novas congregações para aparecerem no cadastro de eventos.", azul),
        ("Exportar calendário", "Exportar calendário", len(regs),
         "evento(s) no calendário",
         "Baixe o calendário em PDF ou Excel, completo ou por região, com contatos.", azul),
    ]

    st.markdown("#### O que você deseja fazer?")
    for i in range(0, len(blocos), 2):
        colunas = st.columns(2)
        for coluna, (rotulo, destino, numero, legenda, descricao, cor) in zip(colunas, blocos[i:i + 2]):
            with coluna:
                with st.container(border=True):
                    st.markdown(
                        f'<div class="adm-card"><div class="adm-tit">{rotulo}</div>'
                        f'<div class="adm-num" style="color:{cor}">{numero}</div>'
                        f'<div class="adm-lbl">{legenda}</div>'
                        f'<div class="adm-desc">{descricao}</div></div>',
                        unsafe_allow_html=True,
                    )
                    if st.button("Abrir", key=f"painel_{destino}", use_container_width=True):
                        st.session_state["sub_lideranca"] = destino
                        st.rerun()


# =====================================================================
# 3c. EXPORTAÇÃO (EXCEL E PDF)
# =====================================================================
@st.cache_data(ttl=86400)
def baixar_logo():
    try:
        import urllib.request
        with urllib.request.urlopen(LOGO_URL, timeout=6) as r:
            return r.read()
    except Exception:
        return None


def _slug(texto):
    return re.sub(r"[^a-z0-9]+", "_", _norm(texto)).strip("_")


def _painel_exportacao(df_base, chave, incluir_contato=False):
    """Painel para exportar o calendário (completo ou por região; anual, semestral ou mensal)."""
    if not EXPORT_OK:
        st.warning("A exportação não está disponível: o arquivo exportacao.py não foi encontrado "
                   f"no repositório. Detalhe: {EXPORT_ERRO}")
        return
    eventos = exportacao.preparar_eventos(df_base, peso_evento)
    if not eventos:
        st.info("Ainda não há eventos para exportar.")
        return

    anos = sorted({e["ini"].year for e in eventos} | {e["fim"].year for e in eventos})
    agora = datetime.now()
    futuros = [a for a in anos if a >= agora.year]
    ano_padrao = futuros[0] if futuros else anos[-1]
    regioes = sorted({e["regiao"] for e in eventos if e["regiao"]})

    c1, c2 = st.columns(2)
    escopo = c1.radio("O que exportar", ["Calendário completo", "Por região"],
                      horizontal=True, key=f"{chave}_escopo")
    regiao = None
    if escopo == "Por região":
        regiao = c2.selectbox("Região", regioes, key=f"{chave}_regiao")

    p1, p2, p3 = st.columns(3)
    tipo_periodo = p1.selectbox("Período", ["Anual", "Semestral", "Mensal"], key=f"{chave}_periodo")
    ano = p2.selectbox("Ano", anos, index=anos.index(ano_padrao), key=f"{chave}_ano")
    semestre, mes = 1, 1
    if tipo_periodo == "Semestral":
        semestre = p3.selectbox("Semestre", [1, 2], format_func=lambda x: f"{x}º semestre", key=f"{chave}_sem")
    elif tipo_periodo == "Mensal":
        mes = p3.selectbox("Mês", list(range(1, 13)), index=agora.month - 1,
                           format_func=lambda m: exportacao.MESES[m - 1], key=f"{chave}_mes")

    formato = st.radio("Formato", ["PDF (visual)", "Excel"], horizontal=True, key=f"{chave}_formato")

    ini, fim, rotulo = exportacao.intervalo(tipo_periodo, ano, semestre, mes)
    selecionados = exportacao.filtrar(eventos, ini, fim, regiao)
    st.caption(f"{len(selecionados)} evento(s) no período selecionado.")

    sig = (escopo, regiao, tipo_periodo, ano, semestre, mes, formato, len(eventos), incluir_contato)
    chave_arq = f"{chave}_arquivo"

    if st.button("Gerar arquivo", key=f"{chave}_gerar", disabled=not selecionados):
        titulo = "Calendário de Atividades MEN"
        subtitulo = f"{rotulo} · {regiao if regiao else 'Todas as regiões'}"
        if incluir_contato:
            subtitulo += " · Uso interno"
        try:
            if formato.startswith("PDF"):
                dados = exportacao.gerar_pdf(selecionados, titulo, subtitulo, incluir_contato, baixar_logo())
                ext, mime = "pdf", "application/pdf"
            else:
                dados = exportacao.gerar_excel(selecionados, f"{titulo} - {subtitulo}", incluir_contato,
                                               abas_por_regiao=regiao is None)
                ext, mime = "xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            st.session_state[chave_arq] = {
                "sig": sig, "dados": dados, "mime": mime,
                "nome": f"calendario_men_{_slug(regiao or 'completo')}_{_slug(rotulo)}.{ext}",
                "rotulo": "PDF" if ext == "pdf" else "Excel",
            }
        except ImportError:
            st.error("Faltam bibliotecas para exportar. Adicione `openpyxl` e `reportlab` ao arquivo "
                     "requirements.txt do repositório.")
        except Exception as erro:
            st.error(f"Não foi possível gerar o arquivo: {erro}")

    arq = st.session_state.get(chave_arq)
    if arq and arq["sig"] == sig:
        st.download_button(f"Baixar {arq['rotulo']}", data=arq["dados"], file_name=arq["nome"],
                           mime=arq["mime"], key=f"{chave}_baixar")


def bloco_exportacao(df_base, chave, incluir_contato=False):
    """Bloco em destaque com o painel de exportação."""
    with st.container(border=True):
        st.markdown(
            '<div class="marca-exportar"></div>'
            '<div class="exp-topo"><div class="exp-icone">⬇</div><div>'
            '<div class="exp-titulo">Exportar calendário</div>'
            '<div class="exp-sub">Baixe o calendário em PDF (visual) ou Excel, completo ou por região.</div>'
            '</div></div>',
            unsafe_allow_html=True,
        )
        _painel_exportacao(df_base, chave, incluir_contato)


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
    SUBMENU_LIDERANCA = [("Painel inicial", "sub_painel"), ("Choques de agenda", "sub_choques"),
                        ("Ajustar datas", "sub_ajuste"), ("Congregações", "sub_congregacoes"),
                        ("Exportar calendário", "sub_exportar")]
    pagina_atual = st.session_state["pagina"]
    for nome_pag in PAGINAS:
        eh_lideranca = nome_pag == "Área da liderança"
        ativo = pagina_atual == nome_pag and not (eh_lideranca and st.session_state["logado"])
        if st.button(nome_pag, key=f"menu_{nome_pag}",
                     type="primary" if ativo else "secondary",
                     use_container_width=True):
            st.session_state["pagina"] = nome_pag
            if eh_lideranca:
                st.session_state["sub_lideranca"] = "Painel inicial"
            st.session_state.pop("envio_concluido", None)
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
            "Tipo de Festividade", "Nome Completo", "Cargo/Função", "Whatsapp para Contato", "_linha",
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
            bloco_exportacao(df, "pub", incluir_contato=False)
            st.write("")

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
                columns=[c for c in ["Whatsapp para Contato", "Cargo/Função", "_linha"] if c in df_exibicao.columns]
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
        fila = st.session_state["eventos_temporarios"]
        concluido = st.session_state.get("envio_concluido")

        # =============================================================
        # TELA DE AGRADECIMENTO (depois do envio)
        # =============================================================
        if concluido:
            _, centro, _ = st.columns([1, 2, 1])
            with centro:
                st.markdown(
                    '<div class="login-topo"><div class="login-icone">✅</div>'
                    '<h2>Obrigado pelo cadastro!</h2>'
                    f'<p>{concluido["total"]} evento(s) enviado(s) com sucesso para o calendário da MEN.</p></div>',
                    unsafe_allow_html=True,
                )
                if concluido["choques"]:
                    st.warning(
                        "Identificamos choque de datas dentro da mesma região nos eventos abaixo. Eles foram enviados e "
                        "**serão analisados pela Secretária da MEN para validação**.\n\n"
                        + "\n".join(f"- {m}" for m in concluido["choques"])
                    )
                b1, b2 = st.columns(2)
                if b1.button("Ver calendário público", use_container_width=True):
                    st.session_state["pagina"] = "Calendário"
                    st.session_state.pop("envio_concluido", None)
                    st.rerun()
                if b2.button("Cadastrar mais eventos", use_container_width=True):
                    st.session_state.pop("envio_concluido", None)
                    st.rerun()

        else:
            st.title("Cadastro de novo evento")
            resp = st.session_state.get("responsavel")
            editando = st.session_state.get("editando_resp", False)

            # =========================================================
            # ETAPA 1: dados do responsável (preenchidos uma única vez)
            # =========================================================
            if not resp or editando:
                st.markdown("#### Etapa 1 de 2: seus dados")
                st.caption("Preencha uma vez. Depois você poderá cadastrar quantos eventos quiser.")
                nome_r = st.text_input("Nome completo", key="resp_nome")
                cargo_r = st.selectbox("Cargo/Função", CARGOS, key="resp_cargo")
                whats_r = st.text_input(
                    "WhatsApp para contato", key="resp_whats", on_change=_formatar_whats,
                    placeholder="(83) 9 9999-9999",
                    help="Digite só os números. O formato é aplicado ao sair do campo.",
                )
                if st.button("Continuar"):
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

            # =========================================================
            # ETAPA 2: cadastro dos eventos
            # =========================================================
            else:
                nome, cargo, whatsapp = resp["nome"], resp["cargo"], resp["whats"]

                with st.container(border=True):
                    r1, r2 = st.columns([5, 1], vertical_alignment="center")
                    r1.markdown(f"**Responsável:** {nome} · {cargo} · {whatsapp}")
                    if r2.button("Alterar dados", use_container_width=True):
                        st.session_state["resp_nome"] = nome
                        st.session_state["resp_cargo"] = cargo
                        st.session_state["resp_whats"] = whatsapp
                        st.session_state["editando_resp"] = True
                        st.rerun()

                with st.expander("Regras de agenda e prioridade"):
                    st.markdown(
                        "- **Prioridade alta:** aniversário de congregação.\n"
                        "- **Prioridade média:** aniversário de UAC e de UHC.\n"
                        "- **Prioridade baixa:** demais atividades.\n"
                        "- **Choque de datas:** eventos da mesma região em datas que se sobrepõem.\n"
                        "- Você pode enviar normalmente. Se houver choque, o evento será analisado "
                        "pela Secretária da MEN para validação."
                    )

                st.markdown("#### Etapa 2 de 2: congregação e evento")
                mapa_congregacoes = lista_de_congregacoes()
                if not any(mapa_congregacoes.values()):
                    st.warning("A lista de congregações não foi encontrada na planilha. "
                               "Use a opção 'Outra congregação' para digitar o nome.")

                # --- carrega um evento da fila para edição (antes de criar os campos) ---
                carregar = st.session_state.pop("carregar_edicao", None)
                if carregar is not None and carregar < len(fila):
                    ev = fila[carregar]
                    st.session_state["editando_idx"] = carregar
                    if ev["Regiao"] in mapa_congregacoes:
                        reg_ed = ev["Regiao"]
                        st.session_state["cad_regiao"] = reg_ed
                        lista_ed = sorted(mapa_congregacoes.get(reg_ed, []))
                        if ev["Congregacao"] in lista_ed:
                            st.session_state[f"cad_congregacao_{reg_ed}"] = ev["Congregacao"]
                        else:
                            st.session_state[f"cad_congregacao_{reg_ed}"] = OUTRA_CONGREGACAO
                            st.session_state[f"cad_outra_{reg_ed}"] = ev["Congregacao"]
                    st.session_state["cad_festividade"] = ev["Festividade"]
                    st.session_state["cad_tipo"] = ev["Tipo"]
                    st.session_state["cad_data_inicio"] = datetime.strptime(ev["Inicio"], "%d/%m/%Y").date()
                    st.session_state["cad_data_fim"] = datetime.strptime(ev["Fim"], "%d/%m/%Y").date()
                idx_edicao = st.session_state.get("editando_idx")

                # --- depois de adicionar/salvar, limpa só os campos do evento ---
                if st.session_state.pop("limpar_evento", False):
                    for k in ("cad_festividade", "cad_tipo", "cad_data_inicio", "cad_data_fim"):
                        st.session_state.pop(k, None)

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

                msg_cadastro = st.session_state.pop("msg_cadastro", None)
                if msg_cadastro:
                    st.success(msg_cadastro)

                if idx_edicao is not None:
                    st.info(f"Você está editando o evento {idx_edicao + 1} da fila.")

                festividade = st.text_input("Nome da festividade", key="cad_festividade")
                f1, f2, f3 = st.columns(3)
                tipo = f1.selectbox(
                    "Tipo de festividade",
                    ["", "Aniversário de Congregação", "Aniversário de UAC", "Aniversário de UHC",
                     "Aniversário de Departamento", "Intercâmbio", "Evangelismo", "Outros"],
                    key="cad_tipo",
                )
                data_inicio = f2.date_input("Data de início", format="DD/MM/YYYY", key="cad_data_inicio")
                # a data final nunca pode ser anterior à data de início
                if st.session_state.get("cad_data_fim") is None or st.session_state["cad_data_fim"] < data_inicio:
                    st.session_state["cad_data_fim"] = data_inicio
                data_fim = f3.date_input(
                    "Data final", format="DD/MM/YYYY", min_value=data_inicio, key="cad_data_fim"
                )

                def _validar():
                    if festividade.strip() == "":
                        return "Informe o nome da festividade."
                    if regiao == "":
                        return "Selecione a região da congregação."
                    if congregacao.strip() == "":
                        return "Selecione ou informe a congregação."
                    if tipo == "":
                        return "Selecione o tipo de festividade."
                    if data_fim < data_inicio:
                        return "A data final não pode ser anterior à data de início."
                    return None

                def _evento():
                    return {
                        "Nome": nome, "Cargo": cargo, "Whats": whatsapp, "Regiao": regiao,
                        "Congregacao": congregacao.strip(), "Festividade": festividade.strip(), "Tipo": tipo,
                        "Inicio": data_inicio.strftime("%d/%m/%Y"), "Fim": data_fim.strftime("%d/%m/%Y"),
                    }

                if idx_edicao is None:
                    if st.button("Adicionar à fila"):
                        erro = _validar()
                        if erro:
                            st.error(erro)
                        else:
                            fila.append(_evento())
                            st.session_state["msg_cadastro"] = "Evento adicionado à fila. Você pode cadastrar o próximo."
                            st.session_state["limpar_evento"] = True
                            st.rerun()
                else:
                    e1, e2, _ = st.columns([1, 1, 2])
                    if e1.button("Salvar alterações", use_container_width=True):
                        erro = _validar()
                        if erro:
                            st.error(erro)
                        else:
                            fila[idx_edicao] = _evento()
                            st.session_state["editando_idx"] = None
                            st.session_state["msg_cadastro"] = "Alterações salvas."
                            st.session_state["limpar_evento"] = True
                            st.rerun()
                    if e2.button("Cancelar edição", use_container_width=True):
                        st.session_state["editando_idx"] = None
                        st.session_state["limpar_evento"] = True
                        st.rerun()

                # =====================================================
                # FILA DE ENVIO (editar, remover e enviar)
                # =====================================================
                if fila:
                    st.markdown(f"#### Fila de envio ({len(fila)})")
                    for i, e in enumerate(fila):
                        periodo = e["Inicio"] if e["Inicio"] == e["Fim"] else f'{e["Inicio"]} a {e["Fim"]}'
                        with st.container(border=True):
                            c1, c2, c3, c4 = st.columns([5, 3, 1.3, 1.3], vertical_alignment="center")
                            c1.markdown(f'**{e["Festividade"]}**  \n{e["Tipo"]} · {periodo}')
                            c2.markdown(f'{e["Congregacao"]}  \n{e["Regiao"]}')
                            if c3.button("Editar", key=f"editar_{i}", use_container_width=True):
                                st.session_state["carregar_edicao"] = i
                                st.rerun()
                            if c4.button("Remover", key=f"remover_{i}", use_container_width=True):
                                fila.pop(i)
                                ed = st.session_state.get("editando_idx")
                                if ed is not None:
                                    if ed == i:
                                        st.session_state["editando_idx"] = None
                                    elif ed > i:
                                        st.session_state["editando_idx"] = ed - 1
                                st.rerun()

                    b1, b2, _ = st.columns([1, 1, 3])
                    if b1.button("Limpar lista", use_container_width=True):
                        st.session_state["eventos_temporarios"] = []
                        st.session_state["editando_idx"] = None
                        st.rerun()
                    if b2.button("Enviar", use_container_width=True):
                        carregar_dados.clear()
                        base_atual = registros_da_planilha(carregar_dados())
                        novos = registros_da_fila()
                        # Só choques dentro da mesma região geram aviso; nenhum bloqueia o envio.
                        vistos, avisos = set(), []
                        for n in novos:
                            for c, m in choques_do_novo(n, base_atual):
                                if m == "Mesma região":
                                    avisos.append(f"{descrever(n)} × {descrever(c)}")
                        for a_, b_, m in todos_os_choques(novos):
                            if m == "Mesma região":
                                avisos.append(f"{descrever(a_)} × {descrever(b_)}")
                        avisos = [x for x in avisos if not (x in vistos or vistos.add(x))]

                        data_atual = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                        linhas = [
                            [data_atual, r["Nome"], r["Cargo"], r["Whats"], r["Regiao"],
                             r["Congregacao"], "", "", "", r["Festividade"], r["Tipo"],
                             r["Inicio"], r["Fim"], ""]
                            for r in fila
                        ]
                        salvar_lote_no_banco(linhas)
                        st.cache_data.clear()
                        st.session_state["envio_concluido"] = {"total": len(linhas), "choques": avisos}
                        st.session_state["eventos_temporarios"] = []
                        st.session_state["editando_idx"] = None
                        st.rerun()

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
                        st.session_state["sub_lideranca"] = "Painel inicial"
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

            if st.session_state["sub_lideranca"] == "Painel inicial":
                painel_inicial_lideranca(df)
            elif st.session_state["sub_lideranca"] == "Choques de agenda":
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

                    st.markdown("#### Corrigir os choques")
                st.info("Para remarcar um evento, use **Ajustar datas** no menu lateral. O app sugere datas "
                        "livres na região e evita feriados. A planilha continua disponível para consulta.")
                st.link_button("Abrir planilha do banco de dados", PLANILHA_URL)


            elif st.session_state["sub_lideranca"] == "Ajustar datas":
                st.markdown("### Ajustar datas de um evento")
                painel_ajuste_datas(df)
            elif st.session_state["sub_lideranca"] == "Exportar calendário":
                st.caption("Na área da liderança, a exportação inclui cargo e WhatsApp dos responsáveis.")
                bloco_exportacao(df, "adm", incluir_contato=True)
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
