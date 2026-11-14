"""Consulta (somente leitura) aos dados do sistema de gestão das congregações.

Usada na área da liderança do site do calendário. Não grava nada no banco.
Segredos (Streamlit Cloud > Settings > Secrets):
    database_url_leitura = "postgresql://..."  # de preferência um usuário só com permissão de leitura
    url_gestao = "https://seu-site-de-gestao.streamlit.app"   # opcional: botão para abrir o site
Biblioteca necessária (requirements.txt): psycopg2-binary
"""
import unicodedata
from datetime import date

import altair as alt
import pandas as pd
import streamlit as st

import gestao_db as db

MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
         "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]


def _sem_acento(texto):
    return unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode().lower()


def _fmt(d):
    return d.strftime("%d/%m/%Y") if d else ""


@st.cache_data(ttl=120, show_spinner="Carregando dados da gestão...")
def _carregar(url):
    banco = db.Banco(url, somente_leitura=True)
    return {
        "resumo": db.resumo(banco),
        "por_congregacao": db.membros_por_congregacao(banco),
        "congregacoes": db.listar_congregacoes(banco, apenas_ativas=False),
        "departamentos": db.listar_departamentos(banco),
        "membros": db.listar_membros(banco),
    }


def _instrucoes():
    st.info(
        "A consulta ao sistema de gestão ainda não foi configurada. No Streamlit Cloud, abra "
        "**Settings > Secrets** deste app e acrescente a linha:\n\n"
        '`database_url_leitura = "connection-string-do-banco-de-gestao"`\n\n'
        "Use, de preferência, um usuário do banco com permissão apenas de leitura. "
        "Confirme também que o `requirements.txt` tem `psycopg2-binary`."
    )


def renderizar():
    try:
        url = st.secrets.get("database_url_leitura") or st.secrets["database_url"]
    except Exception:
        url = None
    if not url:
        _instrucoes()
        return

    topo1, topo2, topo3 = st.columns([4, 1.4, 1.4], vertical_alignment="center")
    topo1.caption("Somente leitura. Os dados são mantidos no sistema de gestão das congregações.")
    if topo2.button("Atualizar dados", key="gc_atualizar", use_container_width=True):
        _carregar.clear()
        st.rerun()
    url_site = st.secrets.get("url_gestao") if hasattr(st.secrets, "get") else None
    if url_site:
        topo3.link_button("Abrir sistema de gestão", url_site, use_container_width=True)

    try:
        dados = _carregar(url)
    except ImportError:
        st.error("Falta a biblioteca `psycopg2-binary`. Acrescente-a ao requirements.txt do repositório.")
        return
    except Exception as erro:
        st.error(f"Não foi possível consultar o banco de dados: {erro}")
        return

    aba_resumo, aba_membros, aba_deps, aba_cong = st.tabs(["Resumo", "Membros", "Departamentos", "Congregações"])

    # ---------------- Resumo ----------------
    with aba_resumo:
        r = dados["resumo"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Membros ativos", r["membros_ativos"])
        c2.metric("Congregações", r["congregacoes"])
        c3.metric("Departamentos", r["departamentos"])
        c4.metric("Novos membros (30 dias)", r["novos_30_dias"])

        st.markdown("#### Membros por congregação")
        tabela = pd.DataFrame(dados["por_congregacao"])
        if not tabela.empty and tabela["total"].sum() > 0:
            tabela = tabela.rename(columns={"nome": "Congregação", "total": "Membros"})
            grafico = (
                alt.Chart(tabela).mark_bar(color="#1E3A8A")
                .encode(x=alt.X("Membros:Q", title=None, axis=alt.Axis(tickMinStep=1, format="d")),
                        y=alt.Y("Congregação:N", sort="-x", title=None))
                .properties(height=max(120, 30 * len(tabela)), background="#FFFFFF")
                .configure_view(strokeWidth=0)
                .configure_axis(labelColor="#1F2937", gridColor="#E5E7EB", domainColor="#CBD5E1")
            )
            st.altair_chart(grafico, use_container_width=True, theme=None)
        else:
            st.caption("Ainda não há membros cadastrados no sistema de gestão.")

        st.markdown("#### Aniversariantes")
        mes = st.selectbox("Mês", list(range(1, 13)), index=date.today().month - 1,
                           format_func=lambda m: MESES[m - 1], key="gc_mes")
        aniv = sorted(
            [m for m in dados["membros"]
             if m["situacao"] == "Ativo" and m["data_nascimento"] and m["data_nascimento"].month == mes],
            key=lambda m: (m["data_nascimento"].day, m["nome"]))
        if aniv:
            st.dataframe(pd.DataFrame([{"Dia": m["data_nascimento"].day, "Nome": m["nome"],
                                        "Congregação": m["congregacao"]} for m in aniv]),
                         use_container_width=True, hide_index=True)
        else:
            st.caption("Nenhum aniversariante neste mês.")

    # ---------------- Membros ----------------
    with aba_membros:
        nomes_cong = sorted({m["congregacao"] for m in dados["membros"]})
        f1, f2, f3 = st.columns(3)
        cong = f1.selectbox("Congregação", [None] + nomes_cong, key="gc_m_cong",
                            format_func=lambda c: "Todas" if c is None else c)
        sit = f2.selectbox("Situação", [None] + db.SITUACOES, key="gc_m_sit",
                           format_func=lambda s: "Todas" if s is None else s)
        busca = f3.text_input("Buscar por nome", key="gc_m_busca")
        lista = dados["membros"]
        if cong:
            lista = [m for m in lista if m["congregacao"] == cong]
        if sit:
            lista = [m for m in lista if m["situacao"] == sit]
        if busca.strip():
            alvo = _sem_acento(busca.strip())
            lista = [m for m in lista if alvo in _sem_acento(m["nome"])]
        st.caption(f"{len(lista)} membro(s). Por privacidade, telefone, e-mail e observações aparecem "
                   "só no sistema de gestão.")
        if lista:
            st.dataframe(pd.DataFrame([{
                "Nome": m["nome"], "Congregação": m["congregacao"], "Cargo": m["cargo"] or "",
                "Situação": m["situacao"], "Departamentos": m["departamentos"],
                "Entrada": _fmt(m["data_entrada"]),
            } for m in lista]), use_container_width=True, hide_index=True)

    # ---------------- Departamentos ----------------
    with aba_deps:
        deps = dados["departamentos"]
        if deps:
            st.dataframe(pd.DataFrame([{
                "Congregação": d["congregacao"], "Departamento": d["nome"], "Líder": d["lider"] or "",
                "Membros ativos": d["total_membros"], "Fundação": _fmt(d["data_fundacao"]),
                "Situação": "Ativo" if d["ativo"] else "Inativo",
            } for d in deps]), use_container_width=True, hide_index=True)
        else:
            st.caption("Nenhum departamento cadastrado no sistema de gestão.")

    # ---------------- Congregações ----------------
    with aba_cong:
        congs = dados["congregacoes"]
        if congs:
            st.dataframe(pd.DataFrame([{
                "Congregação": c["nome"], "Região": c["regiao"] or "", "Endereço": c["endereco"] or "",
                "Fundação": _fmt(c["data_fundacao"]), "Situação": "Ativa" if c["ativa"] else "Inativa",
            } for c in congs]), use_container_width=True, hide_index=True)
        else:
            st.caption("Nenhuma congregação cadastrada no sistema de gestão.")
