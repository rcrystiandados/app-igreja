"""Banco de dados da gestão das congregações.

Usa PostgreSQL na nuvem (Neon ou Supabase) via psycopg2. Para testes locais também
aceita SQLite (url no formato sqlite:///arquivo.db). Não depende do Streamlit.

Biblioteca necessária (requirements.txt): psycopg2-binary
"""
import re
import sqlite3
import unicodedata
from contextlib import contextmanager
from datetime import date, datetime, timedelta

# Listas editáveis: ajuste os nomes conforme a realidade da igreja.
SITUACOES = ["Ativo", "Em observação", "Inativo", "Transferido", "Falecido"]
CARGOS = ["Membro", "Congregado", "Diácono", "Presbítero", "Obreiro", "Dirigente", "Pastor"]
FUNCOES_DEPARTAMENTO = ["Membro", "Líder", "Vice-líder", "Secretário(a)", "Tesoureiro(a)"]
TIPOS_EVENTO_INTERNO = ["Culto especial", "Reunião", "Ensaio", "Escola bíblica", "Visita", "Outro"]

LIDER = "Líder"


# ---------------------------------------------------------------------------
# Conexão
# ---------------------------------------------------------------------------
class Sessao:
    """Uma conexão aberta, com métodos simples para consultar e gravar."""

    def __init__(self, con, sqlite):
        self.con = con
        self.sqlite = sqlite

    def _sql(self, sql):
        # Escrevemos :nome nas consultas; o PostgreSQL usa %(nome)s.
        return sql if self.sqlite else re.sub(r"(?<![:\w]):(\w+)", r"%(\1)s", sql)

    def consultar(self, sql, params=None):
        cur = self.con.cursor()
        cur.execute(self._sql(sql), params or {})
        return [dict(linha) for linha in cur.fetchall()]

    def executar(self, sql, params=None):
        cur = self.con.cursor()
        cur.execute(self._sql(sql), params or {})
        return cur.rowcount

    def inserir(self, sql, params=None):
        """Executa um INSERT ... RETURNING id e devolve o id criado."""
        cur = self.con.cursor()
        cur.execute(self._sql(sql), params or {})
        return cur.fetchone()["id"]


class Banco:
    def __init__(self, url, somente_leitura=False):
        self.url = url.strip()
        self.sqlite = self.url.startswith("sqlite:///")
        self.somente_leitura = somente_leitura

    def _conectar(self):
        if self.sqlite:
            con = sqlite3.connect(self.url[len("sqlite:///"):])
            con.row_factory = sqlite3.Row
            con.execute("PRAGMA foreign_keys = ON")
            if self.somente_leitura:
                con.execute("PRAGMA query_only = ON")
            return con
        import psycopg2
        import psycopg2.extras
        url = re.sub(r"^postgres(ql)?(\+\w+)?://", "postgresql://", self.url)
        con = psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor, connect_timeout=20)
        if self.somente_leitura:
            con.set_session(readonly=True)
        return con

    @contextmanager
    def sessao(self):
        con = self._conectar()
        try:
            yield Sessao(con, self.sqlite)
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def criar_tabelas(self):
        pk = "INTEGER PRIMARY KEY AUTOINCREMENT" if self.sqlite else "SERIAL PRIMARY KEY"
        comandos = [
            f"""CREATE TABLE IF NOT EXISTS congregacoes (
                id {pk},
                nome TEXT NOT NULL UNIQUE,
                regiao TEXT,
                endereco TEXT,
                data_fundacao DATE,
                ativa INTEGER NOT NULL DEFAULT 1,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            f"""CREATE TABLE IF NOT EXISTS departamentos (
                id {pk},
                congregacao_id INTEGER NOT NULL REFERENCES congregacoes(id),
                nome TEXT NOT NULL,
                data_fundacao DATE,
                ativo INTEGER NOT NULL DEFAULT 1,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            f"""CREATE TABLE IF NOT EXISTS membros (
                id {pk},
                congregacao_id INTEGER NOT NULL REFERENCES congregacoes(id),
                nome TEXT NOT NULL,
                data_nascimento DATE,
                sexo TEXT,
                telefone TEXT,
                email TEXT,
                cargo TEXT,
                situacao TEXT NOT NULL DEFAULT 'Ativo',
                data_entrada DATE,
                data_batismo DATE,
                observacoes TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            """CREATE TABLE IF NOT EXISTS membros_departamentos (
                membro_id INTEGER NOT NULL REFERENCES membros(id) ON DELETE CASCADE,
                departamento_id INTEGER NOT NULL REFERENCES departamentos(id) ON DELETE CASCADE,
                funcao TEXT NOT NULL DEFAULT 'Membro',
                PRIMARY KEY (membro_id, departamento_id))""",
            f"""CREATE TABLE IF NOT EXISTS eventos_internos (
                id {pk},
                congregacao_id INTEGER NOT NULL REFERENCES congregacoes(id),
                departamento_id INTEGER REFERENCES departamentos(id) ON DELETE SET NULL,
                titulo TEXT NOT NULL,
                tipo TEXT,
                data_inicio DATE NOT NULL,
                data_fim DATE,
                local TEXT,
                descricao TEXT,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
            "CREATE INDEX IF NOT EXISTS idx_membros_cong ON membros(congregacao_id)",
            "CREATE INDEX IF NOT EXISTS idx_dep_cong ON departamentos(congregacao_id)",
            "CREATE INDEX IF NOT EXISTS idx_ev_cong ON eventos_internos(congregacao_id)",
        ]
        with self.sessao() as s:
            for comando in comandos:
                s.executar(comando)


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------
def _iso(valor):
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    return str(valor)[:10]


def _data(valor):
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    try:
        return datetime.strptime(str(valor)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _normalizar(linhas, campos_data):
    for linha in linhas:
        for campo in campos_data:
            if campo in linha:
                linha[campo] = _data(linha[campo])
    return linhas


def _sem_acento(texto):
    return unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode().lower()


def _texto(valor):
    valor = (valor or "").strip() if isinstance(valor, str) else valor
    return valor or None


# ---------------------------------------------------------------------------
# Congregações
# ---------------------------------------------------------------------------
def listar_congregacoes(banco, apenas_ativas=True):
    with banco.sessao() as s:
        linhas = s.consultar(
            "SELECT id, nome, regiao, endereco, data_fundacao, ativa FROM congregacoes "
            "WHERE (:todas = 1 OR ativa = 1) ORDER BY regiao, nome",
            {"todas": 0 if apenas_ativas else 1},
        )
    return _normalizar(linhas, ["data_fundacao"])


def importar_congregacoes(banco, mapa):
    """Cria as congregações que ainda não existem. mapa = {região: [nomes]}. Devolve quantas foram criadas."""
    criadas = 0
    with banco.sessao() as s:
        existentes = {l["nome"].strip().lower() for l in s.consultar("SELECT nome FROM congregacoes")}
        for regiao, nomes in mapa.items():
            for nome in nomes:
                nome = nome.strip()
                if not nome or nome.lower() in existentes:
                    continue
                s.inserir("INSERT INTO congregacoes (nome, regiao) VALUES (:n, :r) RETURNING id",
                          {"n": nome, "r": regiao})
                existentes.add(nome.lower())
                criadas += 1
    return criadas


def criar_congregacao(banco, nome, regiao, endereco=None, data_fundacao=None):
    nome = (nome or "").strip()
    if not nome:
        raise ValueError("Informe o nome da congregação.")
    with banco.sessao() as s:
        if s.consultar("SELECT id FROM congregacoes WHERE LOWER(nome) = LOWER(:n)", {"n": nome}):
            raise ValueError("Já existe uma congregação com esse nome.")
        return s.inserir(
            "INSERT INTO congregacoes (nome, regiao, endereco, data_fundacao) VALUES (:n, :r, :e, :d) RETURNING id",
            {"n": nome, "r": _texto(regiao), "e": _texto(endereco), "d": _iso(data_fundacao)})


def atualizar_congregacao(banco, congregacao_id, endereco, data_fundacao):
    with banco.sessao() as s:
        s.executar("UPDATE congregacoes SET endereco = :e, data_fundacao = :d WHERE id = :i",
                   {"e": _texto(endereco), "d": _iso(data_fundacao), "i": congregacao_id})


# ---------------------------------------------------------------------------
# Departamentos
# ---------------------------------------------------------------------------
def listar_departamentos(banco, congregacao_id=None, apenas_ativos=False):
    with banco.sessao() as s:
        linhas = s.consultar(
            """SELECT d.id, d.congregacao_id, d.nome, d.data_fundacao, d.ativo, c.nome AS congregacao,
                      (SELECT COUNT(*) FROM membros_departamentos md
                         JOIN membros m ON m.id = md.membro_id
                        WHERE md.departamento_id = d.id AND m.situacao = 'Ativo') AS total_membros,
                      (SELECT m2.nome FROM membros_departamentos md2
                         JOIN membros m2 ON m2.id = md2.membro_id
                        WHERE md2.departamento_id = d.id AND md2.funcao = :lider
                        ORDER BY m2.nome LIMIT 1) AS lider
                 FROM departamentos d
                 JOIN congregacoes c ON c.id = d.congregacao_id
                WHERE (:cid IS NULL OR d.congregacao_id = :cid)
                  AND (:so_ativos = 0 OR d.ativo = 1)
                ORDER BY c.nome, d.nome""",
            {"cid": congregacao_id, "so_ativos": 1 if apenas_ativos else 0, "lider": LIDER},
        )
    return _normalizar(linhas, ["data_fundacao"])


def criar_departamento(banco, congregacao_id, nome, data_fundacao=None):
    nome = (nome or "").strip()
    if not nome:
        raise ValueError("Informe o nome do departamento.")
    with banco.sessao() as s:
        if s.consultar("SELECT id FROM departamentos WHERE congregacao_id = :c AND LOWER(nome) = LOWER(:n)",
                       {"c": congregacao_id, "n": nome}):
            raise ValueError("Esta congregação já tem um departamento com esse nome.")
        return s.inserir(
            "INSERT INTO departamentos (congregacao_id, nome, data_fundacao) VALUES (:c, :n, :d) RETURNING id",
            {"c": congregacao_id, "n": nome, "d": _iso(data_fundacao)},
        )


def definir_departamento_ativo(banco, departamento_id, ativo):
    with banco.sessao() as s:
        s.executar("UPDATE departamentos SET ativo = :a WHERE id = :i",
                   {"a": 1 if ativo else 0, "i": departamento_id})


def membros_do_departamento(banco, departamento_id):
    with banco.sessao() as s:
        return s.consultar(
            """SELECT m.id, m.nome, m.situacao, m.telefone, md.funcao
                 FROM membros_departamentos md JOIN membros m ON m.id = md.membro_id
                WHERE md.departamento_id = :d
                ORDER BY CASE WHEN md.funcao = :lider THEN 0 ELSE 1 END, m.nome""",
            {"d": departamento_id, "lider": LIDER},
        )


def definir_funcao_no_departamento(banco, membro_id, departamento_id, funcao):
    """Adiciona o membro ao departamento ou troca a função dele."""
    with banco.sessao() as s:
        s.executar("DELETE FROM membros_departamentos WHERE membro_id = :m AND departamento_id = :d",
                   {"m": membro_id, "d": departamento_id})
        s.executar("INSERT INTO membros_departamentos (membro_id, departamento_id, funcao) VALUES (:m, :d, :f)",
                   {"m": membro_id, "d": departamento_id, "f": funcao})


def remover_do_departamento(banco, membro_id, departamento_id):
    with banco.sessao() as s:
        s.executar("DELETE FROM membros_departamentos WHERE membro_id = :m AND departamento_id = :d",
                   {"m": membro_id, "d": departamento_id})


# ---------------------------------------------------------------------------
# Membros
# ---------------------------------------------------------------------------
_CAMPOS_MEMBRO = ["congregacao_id", "nome", "data_nascimento", "sexo", "telefone", "email", "cargo",
                  "situacao", "data_entrada", "data_batismo", "observacoes"]
_CAMPOS_DATA_MEMBRO = ["data_nascimento", "data_entrada", "data_batismo"]


def _params_membro(dados):
    p = {c: dados.get(c) for c in _CAMPOS_MEMBRO}
    for c in _CAMPOS_DATA_MEMBRO:
        p[c] = _iso(p[c])
    for c in ("nome", "sexo", "telefone", "email", "cargo", "observacoes"):
        p[c] = _texto(p[c])
    p["situacao"] = p["situacao"] or "Ativo"
    return p


def membro_existe(banco, congregacao_id, nome, data_nascimento=None, ignorar_id=None):
    with banco.sessao() as s:
        linhas = s.consultar(
            """SELECT id FROM membros
                WHERE congregacao_id = :c AND LOWER(nome) = LOWER(:n)
                  AND (:nasc IS NULL OR data_nascimento = :nasc)
                  AND (:ign IS NULL OR id <> :ign)""",
            {"c": congregacao_id, "n": (nome or "").strip(), "nasc": _iso(data_nascimento), "ign": ignorar_id},
        )
    return bool(linhas)


def criar_membro(banco, dados, departamentos=()):
    """departamentos = [(departamento_id, funcao), ...]. Devolve o id do novo membro."""
    p = _params_membro(dados)
    if not p["nome"]:
        raise ValueError("Informe o nome do membro.")
    with banco.sessao() as s:
        membro_id = s.inserir(
            """INSERT INTO membros (congregacao_id, nome, data_nascimento, sexo, telefone, email, cargo,
                                    situacao, data_entrada, data_batismo, observacoes)
               VALUES (:congregacao_id, :nome, :data_nascimento, :sexo, :telefone, :email, :cargo,
                       :situacao, :data_entrada, :data_batismo, :observacoes) RETURNING id""", p)
        for dep_id, funcao in departamentos:
            s.executar("INSERT INTO membros_departamentos (membro_id, departamento_id, funcao) VALUES (:m, :d, :f)",
                       {"m": membro_id, "d": dep_id, "f": funcao})
    return membro_id


def atualizar_membro(banco, membro_id, dados, departamentos=()):
    p = _params_membro(dados)
    if not p["nome"]:
        raise ValueError("Informe o nome do membro.")
    p["id"] = membro_id
    with banco.sessao() as s:
        s.executar(
            """UPDATE membros SET congregacao_id = :congregacao_id, nome = :nome,
                      data_nascimento = :data_nascimento, sexo = :sexo, telefone = :telefone, email = :email,
                      cargo = :cargo, situacao = :situacao, data_entrada = :data_entrada,
                      data_batismo = :data_batismo, observacoes = :observacoes,
                      atualizado_em = CURRENT_TIMESTAMP
                WHERE id = :id""", p)
        s.executar("DELETE FROM membros_departamentos WHERE membro_id = :m", {"m": membro_id})
        for dep_id, funcao in departamentos:
            s.executar("INSERT INTO membros_departamentos (membro_id, departamento_id, funcao) VALUES (:m, :d, :f)",
                       {"m": membro_id, "d": dep_id, "f": funcao})


def excluir_membro(banco, membro_id):
    with banco.sessao() as s:
        s.executar("DELETE FROM membros WHERE id = :i", {"i": membro_id})


def _anexar_departamentos(s, membros):
    if not membros:
        return membros
    mapa = {}
    for l in s.consultar(
        """SELECT md.membro_id, md.departamento_id, md.funcao, d.nome
             FROM membros_departamentos md JOIN departamentos d ON d.id = md.departamento_id"""):
        mapa.setdefault(l["membro_id"], []).append(l)
    for m in membros:
        deps = mapa.get(m["id"], [])
        m["departamentos_lista"] = [(d["departamento_id"], d["funcao"]) for d in deps]
        m["departamentos"] = ", ".join(
            d["nome"] if d["funcao"] == "Membro" else f"{d['nome']} ({d['funcao']})" for d in deps)
    return membros


def listar_membros(banco, congregacao_id=None, departamento_id=None, situacao=None, busca="", limite=None):
    texto = (busca or "").strip()
    sql = """SELECT m.*, c.nome AS congregacao
               FROM membros m JOIN congregacoes c ON c.id = m.congregacao_id
              WHERE (:cid IS NULL OR m.congregacao_id = :cid)
                AND (:sit IS NULL OR m.situacao = :sit)
                AND (:dep IS NULL OR m.id IN (SELECT membro_id FROM membros_departamentos
                                               WHERE departamento_id = :dep))
              ORDER BY m.nome"""
    params = {"cid": congregacao_id, "sit": situacao, "dep": departamento_id}
    with banco.sessao() as s:
        linhas = s.consultar(sql, params)
        if texto:
            alvo = _sem_acento(texto)
            linhas = [l for l in linhas if alvo in _sem_acento(l["nome"])]
        if limite:
            linhas = linhas[:limite]
        _anexar_departamentos(s, linhas)
    return _normalizar(linhas, _CAMPOS_DATA_MEMBRO)


def ultimos_membros(banco, quantidade=8):
    with banco.sessao() as s:
        linhas = s.consultar(
            """SELECT m.id, m.nome, m.cargo, m.data_entrada, c.nome AS congregacao
                 FROM membros m JOIN congregacoes c ON c.id = m.congregacao_id
                ORDER BY m.id DESC""")[:quantidade]
    return _normalizar(linhas, ["data_entrada"])


# ---------------------------------------------------------------------------
# Eventos internos das congregações
# ---------------------------------------------------------------------------
def listar_eventos_internos(banco, congregacao_id):
    with banco.sessao() as s:
        linhas = s.consultar(
            """SELECT e.id, e.titulo, e.tipo, e.data_inicio, e.data_fim, e.local, e.descricao,
                      d.nome AS departamento
                 FROM eventos_internos e LEFT JOIN departamentos d ON d.id = e.departamento_id
                WHERE e.congregacao_id = :c
                ORDER BY e.data_inicio DESC, e.titulo""", {"c": congregacao_id})
    return _normalizar(linhas, ["data_inicio", "data_fim"])


def criar_evento_interno(banco, dados):
    titulo = (dados.get("titulo") or "").strip()
    if not titulo:
        raise ValueError("Informe o título do evento.")
    ini = _iso(dados.get("data_inicio"))
    if not ini:
        raise ValueError("Informe a data de início.")
    with banco.sessao() as s:
        return s.inserir(
            """INSERT INTO eventos_internos (congregacao_id, departamento_id, titulo, tipo, data_inicio,
                                             data_fim, local, descricao)
               VALUES (:c, :d, :t, :tipo, :ini, :fim, :loc, :desc) RETURNING id""",
            {"c": dados["congregacao_id"], "d": dados.get("departamento_id"), "t": titulo,
             "tipo": _texto(dados.get("tipo")), "ini": ini, "fim": _iso(dados.get("data_fim")) or ini,
             "loc": _texto(dados.get("local")), "desc": _texto(dados.get("descricao"))})


def remover_evento_interno(banco, evento_id):
    with banco.sessao() as s:
        s.executar("DELETE FROM eventos_internos WHERE id = :i", {"i": evento_id})


# ---------------------------------------------------------------------------
# Indicadores
# ---------------------------------------------------------------------------
def resumo(banco):
    desde = (date.today() - timedelta(days=30)).isoformat()
    with banco.sessao() as s:
        def contar(sql, params=None):
            return s.consultar(sql, params)[0]["n"]
        return {
            "membros_ativos": contar("SELECT COUNT(*) AS n FROM membros WHERE situacao = 'Ativo'"),
            "congregacoes": contar("SELECT COUNT(*) AS n FROM congregacoes WHERE ativa = 1"),
            "departamentos": contar("SELECT COUNT(*) AS n FROM departamentos WHERE ativo = 1"),
            "novos_30_dias": contar("SELECT COUNT(*) AS n FROM membros WHERE data_entrada >= :d", {"d": desde}),
        }


def membros_por_congregacao(banco):
    with banco.sessao() as s:
        return s.consultar(
            """SELECT c.nome, COUNT(m.id) AS total
                 FROM congregacoes c LEFT JOIN membros m ON m.congregacao_id = c.id AND m.situacao = 'Ativo'
                WHERE c.ativa = 1
                GROUP BY c.id, c.nome
                ORDER BY total DESC, c.nome""")


def aniversariantes(banco, mes):
    with banco.sessao() as s:
        linhas = s.consultar(
            """SELECT m.nome, m.data_nascimento, c.nome AS congregacao
                 FROM membros m JOIN congregacoes c ON c.id = m.congregacao_id
                WHERE m.situacao = 'Ativo' AND m.data_nascimento IS NOT NULL""")
    _normalizar(linhas, ["data_nascimento"])
    doa_mes = [l for l in linhas if l["data_nascimento"] and l["data_nascimento"].month == mes]
    return sorted(doa_mes, key=lambda l: (l["data_nascimento"].day, l["nome"]))
