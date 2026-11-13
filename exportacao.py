"""Exportação do calendário de festividades em Excel e PDF.

Não depende do Streamlit: recebe os dados e devolve os bytes do arquivo.
Bibliotecas necessárias (requirements.txt): openpyxl, reportlab.
"""
import calendar
import io
import re
from datetime import date, datetime
from xml.sax.saxutils import escape

import pandas as pd

MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
         "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
MESES_ABREV = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]

AZUL = "#1E3A8A"
AZUL_CLARO = "#E8EEFB"
CINZA = "#64748B"
COR_PRIORIDADE = {1: "#C0392B", 2: "#E39B1F", 3: "#2E7D5B"}
NOME_PRIORIDADE = {1: "Alta", 2: "Média", 3: "Baixa"}
DESC_PRIORIDADE = {
    1: "Alta: aniversário de congregação",
    2: "Média: aniversário de UAC e UHC",
    3: "Baixa: demais atividades",
}


# ---------------------------------------------------------------------------
# Preparação dos dados
# ---------------------------------------------------------------------------
def _texto(valor):
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    return str(valor).strip()


def _data(valor):
    d = pd.to_datetime(valor, dayfirst=True, errors="coerce")
    return None if pd.isna(d) else d.date()


def preparar_eventos(df, peso_fn):
    """Converte o DataFrame do app em uma lista de eventos ordenada por data."""
    eventos = []
    if df is None or df.empty:
        return eventos
    for _, r in df.iterrows():
        ini = _data(r.get("Data de Inicio da Festividade"))
        if ini is None:
            continue
        fim = _data(r.get("Data Final da Festividade")) or ini
        if fim < ini:
            fim = ini
        tipo = _texto(r.get("Tipo de Festividade"))
        eventos.append({
            "ini": ini, "fim": fim,
            "regiao": _texto(r.get("Região da Congregação")),
            "congregacao": _texto(r.get("Congregação")),
            "festividade": _texto(r.get("Nome da Festividade")),
            "tipo": tipo,
            "peso": peso_fn(tipo),
            "responsavel": _texto(r.get("Nome Completo")),
            "cargo": _texto(r.get("Cargo/Função")),
            "whats": _texto(r.get("Whatsapp para Contato")),
        })
    eventos.sort(key=lambda e: (e["ini"], e["fim"], e["festividade"]))
    return eventos


def intervalo(tipo, ano, semestre=1, mes=1):
    """Devolve (inicio, fim, rotulo) do período escolhido."""
    if tipo == "Anual":
        return date(ano, 1, 1), date(ano, 12, 31), f"Ano {ano}"
    if tipo == "Semestral":
        if semestre == 1:
            return date(ano, 1, 1), date(ano, 6, 30), f"1º semestre de {ano}"
        return date(ano, 7, 1), date(ano, 12, 31), f"2º semestre de {ano}"
    ultimo = calendar.monthrange(ano, mes)[1]
    return date(ano, mes, 1), date(ano, mes, ultimo), f"{MESES[mes - 1]} de {ano}"


def filtrar(eventos, ini, fim, regiao=None):
    """Eventos que tocam o período [ini, fim], opcionalmente de uma região."""
    return [
        e for e in eventos
        if e["ini"] <= fim and e["fim"] >= ini and (not regiao or e["regiao"] == regiao)
    ]


# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------
def gerar_excel(eventos, titulo, incluir_contato=False, abas_por_regiao=False):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    wb = Workbook()
    borda = Border(bottom=Side(style="thin", color="DDE3EC"))
    gerado = datetime.now().strftime("%d/%m/%Y %H:%M")

    colunas = [("Início", 12), ("Fim", 12), ("Região", 26), ("Congregação", 28),
               ("Festividade", 44), ("Tipo", 28), ("Prioridade", 12), ("Responsável", 28)]
    if incluir_contato:
        colunas += [("Cargo/Função", 22), ("WhatsApp", 20)]
    ultima_col = len(colunas)

    def escrever(ws, evs):
        ws.sheet_view.showGridLines = False
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ultima_col)
        c = ws.cell(row=1, column=1, value=titulo)
        c.font = Font(name="Calibri", size=15, bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=AZUL[1:])
        c.alignment = Alignment(vertical="center", indent=1)
        ws.row_dimensions[1].height = 30

        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=ultima_col)
        c = ws.cell(row=2, column=1, value=f"Gerado em {gerado}  |  {len(evs)} evento(s)")
        c.font = Font(name="Calibri", size=10, italic=True, color=CINZA[1:])
        c.alignment = Alignment(indent=1)

        for i, (nome, largura) in enumerate(colunas, start=1):
            cab = ws.cell(row=3, column=i, value=nome)
            cab.font = Font(name="Calibri", bold=True, color="FFFFFF")
            cab.fill = PatternFill("solid", fgColor="152C6B")
            cab.alignment = Alignment(horizontal="center", vertical="center")
            ws.column_dimensions[cab.column_letter].width = largura
        ws.row_dimensions[3].height = 22

        for n, e in enumerate(evs):
            linha = 4 + n
            valores = [e["ini"], e["fim"], e["regiao"], e["congregacao"], e["festividade"],
                       e["tipo"], NOME_PRIORIDADE[e["peso"]], e["responsavel"]]
            if incluir_contato:
                valores += [e["cargo"], e["whats"]]
            zebra = PatternFill("solid", fgColor="F3F6FB") if n % 2 else None
            for i, v in enumerate(valores, start=1):
                cel = ws.cell(row=linha, column=i, value=v)
                cel.font = Font(name="Calibri", size=11)
                cel.border = borda
                cel.alignment = Alignment(vertical="center", wrap_text=True)
                if zebra:
                    cel.fill = zebra
                if i in (1, 2):
                    cel.number_format = "DD/MM/YYYY"
                    cel.alignment = Alignment(horizontal="center", vertical="center")
                if i == 7:
                    cel.fill = PatternFill("solid", fgColor=COR_PRIORIDADE[e["peso"]][1:])
                    cel.font = Font(name="Calibri", bold=True, color="FFFFFF")
                    cel.alignment = Alignment(horizontal="center", vertical="center")
            ws.row_dimensions[linha].height = 20

        ws.freeze_panes = "A4"
        if evs:
            ws.auto_filter.ref = f"A3:{ws.cell(row=3, column=ultima_col).column_letter}{3 + len(evs)}"
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True

    ws = wb.active
    ws.title = "Calendário"
    escrever(ws, eventos)

    if abas_por_regiao:
        usados = {"Calendário"}
        for regiao in sorted({e["regiao"] for e in eventos if e["regiao"]}):
            nome = re.sub(r"[\\/*?:\[\]]", "", regiao)[:31] or "Região"
            base, k = nome, 2
            while nome in usados:
                nome = f"{base[:28]} {k}"
                k += 1
            usados.add(nome)
            escrever(wb.create_sheet(nome), [e for e in eventos if e["regiao"] == regiao])

    saida = io.BytesIO()
    wb.save(saida)
    return saida.getvalue()


# ---------------------------------------------------------------------------
# PDF visual
# ---------------------------------------------------------------------------
def gerar_pdf(eventos, titulo, subtitulo, incluir_contato=False, logo_bytes=None):
    from reportlab.graphics.charts.barcharts import HorizontalBarChart
    from reportlab.graphics.shapes import Drawing
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate, Paragraph,
                                    Spacer, Table, TableStyle)

    C = colors.HexColor
    pagina_w, pagina_h = landscape(A4)
    margem = 12 * mm
    util = pagina_w - 2 * margem
    gerado = datetime.now().strftime("%d/%m/%Y %H:%M")

    imagem_logo = None
    if logo_bytes:
        try:
            imagem_logo = ImageReader(io.BytesIO(logo_bytes))
        except Exception:
            imagem_logo = None

    # ---------- cabeçalho e rodapé de cada página ----------
    def moldura(canvas, doc):
        canvas.saveState()
        faixa = 24 * mm
        canvas.setFillColor(C(AZUL))
        canvas.rect(0, pagina_h - faixa, pagina_w, faixa, stroke=0, fill=1)
        canvas.setFillColor(C("#E39B1F"))
        canvas.rect(0, pagina_h - faixa - 1.4 * mm, pagina_w, 1.4 * mm, stroke=0, fill=1)

        x = margem
        if imagem_logo:
            caixa_w, caixa_h = 38 * mm, 18 * mm
            canvas.setFillColor(colors.white)
            canvas.roundRect(x, pagina_h - faixa + 3 * mm, caixa_w, caixa_h, 2 * mm, stroke=0, fill=1)
            iw, ih = imagem_logo.getSize()
            escala = min((caixa_w - 4 * mm) / iw, (caixa_h - 3 * mm) / ih)
            w, h = iw * escala, ih * escala
            canvas.drawImage(imagem_logo, x + (caixa_w - w) / 2, pagina_h - faixa + 3 * mm + (caixa_h - h) / 2,
                             width=w, height=h, mask="auto")
            x += caixa_w + 6 * mm

        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 19)
        canvas.drawString(x, pagina_h - 12.5 * mm, titulo)
        canvas.setFont("Helvetica", 10)
        canvas.setFillColor(C("#DCE5FA"))
        canvas.drawString(x, pagina_h - 18.5 * mm, "Portal Integrado de Festividades")
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 12)
        canvas.drawRightString(pagina_w - margem, pagina_h - 12.5 * mm, subtitulo)

        canvas.setStrokeColor(C("#DDE3EC"))
        canvas.setLineWidth(0.6)
        canvas.line(margem, 11 * mm, pagina_w - margem, 11 * mm)
        canvas.setFillColor(C(CINZA))
        canvas.setFont("Helvetica", 8)
        canvas.drawString(margem, 6.5 * mm, f"Gerado em {gerado}")
        canvas.drawRightString(pagina_w - margem, 6.5 * mm, f"Página {doc.page}")
        canvas.restoreState()

    buffer = io.BytesIO()
    doc = BaseDocTemplate(
        buffer, pagesize=landscape(A4), leftMargin=margem, rightMargin=margem,
        topMargin=32 * mm, bottomMargin=15 * mm, title=f"{titulo} - {subtitulo}", author="Portal Integrado MEN",
    )
    quadro = Frame(margem, 15 * mm, util, pagina_h - 47 * mm, leftPadding=0, rightPadding=0,
                   topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="p", frames=[quadro], onPage=moldura)])

    estilo_num = ParagraphStyle("num", fontName="Helvetica-Bold", fontSize=24, leading=26, alignment=TA_CENTER)
    estilo_rot = ParagraphStyle("rot", fontName="Helvetica", fontSize=8.5, leading=10, alignment=TA_CENTER,
                                textColor=C(CINZA))
    estilo_vazio = ParagraphStyle("vazio", fontName="Helvetica", fontSize=12, textColor=C(CINZA), alignment=TA_CENTER)
    estilo_sec = ParagraphStyle("sec", fontName="Helvetica-Bold", fontSize=11, textColor=C(AZUL), leading=14)

    historia = []
    if not eventos:
        historia += [Spacer(1, 30 * mm), Paragraph("Nenhum evento encontrado para este período.", estilo_vazio)]
        doc.build(historia)
        return buffer.getvalue()

    # ---------- cartões de resumo ----------
    por_peso = {p: sum(1 for e in eventos if e["peso"] == p) for p in (1, 2, 3)}
    regioes = {}
    for e in eventos:
        regioes[e["regiao"] or "Sem região"] = regioes.get(e["regiao"] or "Sem região", 0) + 1

    itens = [
        (len(eventos), "EVENTOS", AZUL),
        (len(regioes), "REGIÕES", AZUL),
        (por_peso[1], "PRIORIDADE ALTA", COR_PRIORIDADE[1]),
        (por_peso[2], "PRIORIDADE MÉDIA", COR_PRIORIDADE[2]),
        (por_peso[3], "PRIORIDADE BAIXA", COR_PRIORIDADE[3]),
    ]
    celulas = []
    for valor, rotulo, cor in itens:
        celulas.append([
            Paragraph(f'<font color="{cor}">{valor}</font>', estilo_num),
            Paragraph(rotulo, estilo_rot),
        ])
    largura_cartao = (util - 4 * 4 * mm) / 5
    linha_cartoes = []
    for i, cel in enumerate(celulas):
        interno = Table([[cel[0]], [cel[1]]], colWidths=[largura_cartao])
        interno.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C("#F3F6FB")),
            ("LINEABOVE", (0, 0), (-1, 0), 3, C(itens[i][2])),
            ("TOPPADDING", (0, 0), (-1, 0), 7), ("BOTTOMPADDING", (0, 1), (-1, 1), 7),
            ("BOX", (0, 0), (-1, -1), 0.4, C("#DDE3EC")),
        ]))
        linha_cartoes.append(interno)
    cartoes = Table([[c for pair in zip(linha_cartoes, [""] * 5) for c in pair][:-1]],
                    colWidths=sum(([largura_cartao, 4 * mm] for _ in range(5)), [])[:-1])
    cartoes.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                                 ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    historia += [cartoes, Spacer(1, 6 * mm)]

    # ---------- legenda + gráfico por região ----------
    legenda_linhas = [[Paragraph("<b>Legenda de prioridade</b>", estilo_sec), "", ""]]
    for p in (1, 2, 3):
        legenda_linhas.append(["", "", Paragraph(DESC_PRIORIDADE[p], ParagraphStyle("l", fontName="Helvetica", fontSize=9, leading=11))])
    legenda = Table(legenda_linhas, colWidths=[0, 5 * mm, 80 * mm])
    legenda.setStyle(TableStyle([
        ("SPAN", (0, 0), (-1, 0)),
        ("BACKGROUND", (1, 1), (1, 1), C(COR_PRIORIDADE[1])),
        ("BACKGROUND", (1, 2), (1, 2), C(COR_PRIORIDADE[2])),
        ("BACKGROUND", (1, 3), (1, 3), C(COR_PRIORIDADE[3])),
        ("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 1), (-1, -1), 4), ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ("LEFTPADDING", (2, 1), (2, -1), 6), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (1, 1), (1, 1), 3, colors.white), ("LINEBELOW", (1, 2), (1, 2), 3, colors.white),
    ]))

    if len(regioes) >= 2:
        ordenadas = sorted(regioes.items(), key=lambda kv: -kv[1])
        altura = 9 * mm * len(ordenadas) + 8 * mm
        largura_graf = util - 100 * mm
        desenho = Drawing(largura_graf, altura)
        grafico = HorizontalBarChart()
        grafico.x, grafico.y = 62 * mm, 4 * mm
        grafico.width, grafico.height = largura_graf - 70 * mm, altura - 8 * mm
        grafico.data = [[v for _, v in ordenadas]]
        grafico.categoryAxis.categoryNames = [k for k, _ in ordenadas]
        grafico.categoryAxis.reverseDirection = 1
        grafico.categoryAxis.labels.fontName = "Helvetica"
        grafico.categoryAxis.labels.fontSize = 9
        grafico.categoryAxis.labels.dx = -3
        grafico.categoryAxis.strokeColor = C("#CBD5E1")
        grafico.categoryAxis.visibleTicks = 0
        grafico.valueAxis.valueMin = 0
        grafico.valueAxis.valueMax = max(v for _, v in ordenadas) + 1
        grafico.valueAxis.valueStep = 1 if max(v for _, v in ordenadas) < 8 else None
        grafico.valueAxis.visible = 0
        grafico.bars[0].fillColor = C(AZUL)
        grafico.bars[0].strokeColor = None
        grafico.barWidth = 6 * mm
        grafico.barLabelFormat = "%d"
        grafico.barLabels.nudge = 7
        grafico.barLabels.fontName = "Helvetica-Bold"
        grafico.barLabels.fontSize = 9
        desenho.add(grafico)
        bloco = Table([[[Paragraph("Eventos por região", estilo_sec), desenho], legenda]],
                      colWidths=[largura_graf, 100 * mm])
    else:
        bloco = Table([[legenda]], colWidths=[util])
    bloco.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    historia += [bloco, Spacer(1, 6 * mm)]

    # ---------- eventos agrupados por mês ----------
    estilo_data = ParagraphStyle("dt", fontName="Helvetica-Bold", fontSize=15, leading=17, alignment=TA_CENTER,
                                 textColor=colors.white)
    estilo_mes = ParagraphStyle("mes", fontName="Helvetica", fontSize=7.5, leading=9, alignment=TA_CENTER,
                                textColor=C("#DCE5FA"))
    estilo_nome = ParagraphStyle("nm", fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=C("#1F2937"))
    estilo_sub = ParagraphStyle("sb", fontName="Helvetica", fontSize=8.5, leading=11, textColor=C(CINZA))
    estilo_prio = ParagraphStyle("pr", fontName="Helvetica-Bold", fontSize=8.5, leading=10, alignment=TA_CENTER,
                                 textColor=colors.white)
    estilo_banda = ParagraphStyle("bd", fontName="Helvetica-Bold", fontSize=12.5, leading=15, textColor=C(AZUL))

    larguras = [26 * mm, 92 * mm, 64 * mm, 24 * mm, util - 206 * mm]

    grupos = {}
    for e in eventos:
        grupos.setdefault((e["ini"].year, e["ini"].month), []).append(e)

    for (ano, mes), evs in sorted(grupos.items()):
        linhas = [[Paragraph(
            f'{MESES[mes - 1].upper()} {ano}  <font name="Helvetica" size="9" color="{CINZA}">'
            f'&nbsp;&nbsp;{len(evs)} evento(s)</font>', estilo_banda), "", "", "", ""]]
        estilos = [
            ("SPAN", (0, 0), (-1, 0)),
            ("BACKGROUND", (0, 0), (-1, 0), C(AZUL_CLARO)),
            ("LINEBEFORE", (0, 0), (0, 0), 4, C(AZUL)),
            ("TOPPADDING", (0, 0), (-1, 0), 6), ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("LEFTPADDING", (0, 0), (-1, 0), 10),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, 1), (0, -1), C(AZUL)),
            ("ROWBACKGROUNDS", (1, 1), (2, -1), [colors.white, C("#F7F9FC")]),
            ("ROWBACKGROUNDS", (4, 1), (4, -1), [colors.white, C("#F7F9FC")]),
            ("LINEBELOW", (0, 1), (-1, -1), 0.4, C("#DDE3EC")),
            ("TOPPADDING", (0, 1), (-1, -1), 6), ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
            ("LEFTPADDING", (1, 1), (-1, -1), 8),
        ]
        for n, e in enumerate(evs, start=1):
            d1, d2 = e["ini"], e["fim"]
            if d1 == d2:
                topo, base = f"{d1.day:02d}", MESES_ABREV[d1.month - 1]
            elif d1.month == d2.month and d1.year == d2.year:
                topo, base = f"{d1.day:02d}-{d2.day:02d}", MESES_ABREV[d1.month - 1]
            else:
                topo = f"{d1.day:02d}-{d2.day:02d}"
                base = f"{MESES_ABREV[d1.month - 1]}-{MESES_ABREV[d2.month - 1]}"
            celula_data = [Paragraph(topo, estilo_data), Paragraph(base, estilo_mes)]

            nome = escape(e["festividade"] or "(sem nome)")
            tipo = escape(e["tipo"])
            celula_nome = [Paragraph(nome, estilo_nome), Paragraph(tipo, estilo_sub)]
            celula_local = [Paragraph(f"<b>{escape(e['congregacao'] or '-')}</b>",
                                      ParagraphStyle("lc", fontName="Helvetica", fontSize=9.5, leading=12)),
                            Paragraph(escape(e["regiao"]), estilo_sub)]
            celula_prio = Paragraph(NOME_PRIORIDADE[e["peso"]].upper(), estilo_prio)
            resp = [Paragraph(escape(e["responsavel"] or "-"),
                              ParagraphStyle("rs", fontName="Helvetica", fontSize=9.5, leading=12))]
            if incluir_contato:
                contato = " | ".join(x for x in (e["cargo"], e["whats"]) if x)
                if contato:
                    resp.append(Paragraph(escape(contato), estilo_sub))
            linhas.append([celula_data, celula_nome, celula_local, celula_prio, resp])
            estilos.append(("BACKGROUND", (3, n), (3, n), C(COR_PRIORIDADE[e["peso"]])))
            estilos.append(("LINEBELOW", (3, n), (3, n), 3, colors.white))
            estilos.append(("LINEABOVE", (3, n), (3, n), 3, colors.white))

        tabela = Table(linhas, colWidths=larguras, repeatRows=1)
        tabela.setStyle(TableStyle(estilos))
        historia += [tabela, Spacer(1, 7 * mm)]

    doc.build(historia)
    return buffer.getvalue()
