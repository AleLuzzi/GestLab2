"""Service layer stampa (PDF DDT, etichette DYMO, scontrini).

Genera i documenti lato server (framework-agnostico, niente dipendenza dalla
UI). I PDF vengono restituiti come bytes/buffer e possono essere salvati su
Object Storage (SaaS) oppure stampati localmente dal **Local Print Agent**
(vedi ``SAAS_PRINTING_BARCODE_PLAN.md`` e il piano ``MERGE_PLAN.md``).

Dipendenze opzionali:
- ``reportlab``: generazione PDF (DDT A4, etichette DYMO).
- ``python-escpos``: scontrini termici ESC/POS (usato dall'Agent locale).
"""

from dataclasses import dataclass, field
from datetime import date, datetime
import io
from typing import List, Optional

# ------------------------------------------------------------------------- #
#  DTO di output (framework-agnostici)
# ------------------------------------------------------------------------- #

@dataclass
class DdtDocument:
    """Documento di trasporto (DDT) generato lato server."""
    numero: str
    data: str
    fornitore: str
    righe: List[dict] = field(default_factory=list)
    pdf_bytes: Optional[bytes] = None
    tenant_id: Optional[int] = None

    def add_riga(self, prodotto="", taglio="", quantita="", peso=""):
        """Aggiunge una riga articolo al DDT."""
        self.righe.append({
            "prodotto": prodotto,
            "taglio": taglio,
            "quantita": quantita,
            "peso": peso,
        })


@dataclass
class EtichettaDymo:
    """Etichetta DYMO per prodotto (formato 54x101 mm)."""
    plu: str
    prodotto: str
    prezzo_kg: str
    ingredienti: str
    codice: str
    pdf_bytes: Optional[bytes] = None
    tenant_id: Optional[int] = None


@dataclass
class ScontrinoTermico:
    """Scontrino/ricevuta termica (testo ESC/POS)."""
    testata: str
    righe: List[dict] = field(default_factory=list)
    totale: str = "0.00"
    iva: str = "0.00"
    escpos: Optional[bytes] = None
    tenant_id: Optional[int] = None

    def add_riga(self, descrizione="", prezzo="", qta=""):
        """Aggiunge una riga di vendita allo scontrino."""
        self.righe.append({
            "descrizione": descrizione,
            "prezzo": prezzo,
            "qta": qta,
        })


# ------------------------------------------------------------------------- #
#  Generazione PDF DDT (ReportLab)
# ------------------------------------------------------------------------- #

def genera_ddt_pdf(numero, data=None, fornitore="", righe=None) -> bytes:
    """Genera il PDF A4 di un DDT e restituisce i bytes.

    Riadatta la logica ReportLab gia' presente in ``Laboratorio/lotti_vendita.py``
    (``crea_pdf``) in una funzione pura e riutilizzabile.

    Args:
        numero: numero/identificativo del documento.
        data: data del documento (default: oggi).
        fornitore: ragione sociale del fornitore.
        righe: lista di dict ``{prodotto, taglio, quantita, peso}``.

    Returns:
        I bytes del PDF generato.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import (SimpleDocTemplate, Spacer, Table,
                                        TableStyle, Paragraph)
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "reportlab non installato. Aggiungerlo a requirements.txt."
        ) from exc

    data = data or date.today().strftime("%d/%m/%y")
    righe = righe or []

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Center", alignment=TA_CENTER))

# Intestazione DDT
    header = [
        ("NUMERO DOCUMENTO", str(numero)),
        ("DATA", str(data)),
        ("FORNITORE", str(fornitore)),
    ]

    # Tabella articoli
    colonne = [("Articolo / Taglio", "Quantita'", "Peso")]
    for r in righe:
        desc = r.get("taglio") or r.get("prodotto") or ""
        colonne.append((str(desc), str(r.get("quantita", "")), str(r.get("peso", ""))))

    titolo = "Documento di Trasporto n. {}".format(numero)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)

    parts = []
    parts.append(Paragraph(titolo, styles["Center"]))
    parts.append(Spacer(1, 0.3 * inch))

    # Tabella intestazione fornitore
    table_header = Table(header, colWidths=[1.2 * inch, 4 * inch])
    table_header.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica"),
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
    ]))
    parts.append(table_header)
    parts.append(Spacer(1, 0.3 * inch))

    # Tabella articoli
    table_items = Table(colonne, colWidths=[3.5 * inch, 1.2 * inch, 1.2 * inch])
    table_items.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica"),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
        ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
    ]))
    parts.append(table_items)

    doc.build(parts)
    return buffer.getvalue()  # bytes del PDF generato


def genera_ddt_vendita_pdf(numero, data, mittente, destinatario, righe) -> bytes:
    """Genera un DDT dai dati della vendita persistita."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "reportlab non installato. Aggiungerlo a requirements.txt."
        ) from exc

    from xml.sax.saxutils import escape

    def paragrafo(value, style):
        return Paragraph(escape(str(value or "")).replace("\n", "<br/>"), style)

    def dettagli_soggetto(soggetto, campi):
        return "<br/>".join(
            escape(str(soggetto.get(campo, "")).strip())
            for campo in campi
            if soggetto.get(campo)
        )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="DdtVenditaTitle", alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="DdtVenditaCell", parent=styles["BodyText"], fontSize=8))
    styles.add(ParagraphStyle(name="DdtVenditaSmall", parent=styles["BodyText"], fontSize=8))
    data_formattata = data.strftime("%d/%m/%Y") if hasattr(data, "strftime") else str(data)
    mittente_indirizzo = mittente.get("indirizzo") or mittente.get("laboratorio", "")
    mittente_dettagli = dettagli_soggetto(
        {
            **mittente,
            "indirizzo": mittente_indirizzo,
            "partita_iva": (
                f"P. IVA {mittente['partita_iva']}" if mittente.get("partita_iva") else ""
            ),
        },
        ("indirizzo", "partita_iva"),
    )
    destinatario_indirizzo = " ".join(
        value
        for value in (
            destinatario.get("indirizzo"),
            destinatario.get("numero_civico"),
            destinatario.get("cap"),
            destinatario.get("citta"),
            destinatario.get("provincia"),
            destinatario.get("paese"),
        )
        if value
    )
    destinatario_partita_iva = (
        f"P. IVA {destinatario['partita_iva']}"
        if destinatario.get("partita_iva")
        else ""
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    parts = [
        Paragraph(f"Documento di Trasporto n. {escape(str(numero))}", styles["DdtVenditaTitle"]),
        Spacer(1, 0.2 * inch),
    ]
    riepilogo = Table(
        [
            ["Numero progressivo", str(numero), "Data", data_formattata],
            [
                "Mittente OSA",
                Paragraph(
                    f"<b>{escape(mittente.get('ragione_sociale', ''))}</b>"
                    + (f"<br/>{mittente_dettagli}" if mittente_dettagli else ""),
                    styles["DdtVenditaSmall"],
                ),
                "Destinatario",
                Paragraph(
                    f"<b>{escape(destinatario.get('denominazione', ''))}</b>"
                    + (
                        f"<br/>{escape(destinatario_indirizzo)}"
                        if destinatario_indirizzo
                        else ""
                    )
                    + (
                        f"<br/>{escape(destinatario_partita_iva)}"
                        if destinatario_partita_iva
                        else ""
                    ),
                    styles["DdtVenditaSmall"],
                ),
            ],
        ],
        colWidths=[1.15 * inch, 2.15 * inch, 0.9 * inch, 2.15 * inch],
    )
    riepilogo.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    parts.extend((riepilogo, Spacer(1, 0.25 * inch)))

    righe_tabella = [[
        paragrafo("Articolo", styles["DdtVenditaCell"]),
        paragrafo("Lotto", styles["DdtVenditaCell"]),
        paragrafo("Quantità", styles["DdtVenditaCell"]),
    ]]
    righe_tabella.extend(
        [
            paragrafo(riga["articolo"], styles["DdtVenditaCell"]),
            paragrafo(riga["lotto"], styles["DdtVenditaCell"]),
            paragrafo(
                f"{riga['quantita']} {riga['unita_misura']}",
                styles["DdtVenditaCell"],
            ),
        ]
        for riga in righe
    )
    tabella_righe = Table(
        righe_tabella,
        colWidths=[3.0 * inch, 1.5 * inch, 1.85 * inch],
        repeatRows=1,
    )
    tabella_righe.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    parts.append(tabella_righe)
    doc.build(parts)
    return buffer.getvalue()


def genera_scheda_lotto_pdf(dettaglio, genealogia) -> bytes:
    """Genera una scheda riepilogativa del lotto e dei suoi ingressi d'origine."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
        from xml.sax.saxutils import escape
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "reportlab non installato. Aggiungerlo a requirements.txt."
        ) from exc

    def testo(value):
        return escape(str(value)) if value not in (None, "") else "—"

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="LotSheetSubtitle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#9a3412"),
        spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        name="LotSheetCell",
        parent=styles["Normal"],
        fontSize=7.5,
        leading=9,
    ))
    styles.add(ParagraphStyle(
        name="LotSheetHeading",
        parent=styles["Heading2"],
        spaceBefore=12,
        spaceAfter=6,
    ))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )
    story = [
        Paragraph(f"Scheda lotto {testo(dettaglio.get('codice_lotto'))}", styles["Title"]),
        Paragraph(
            "Riepilogo per consultazione e controlli — non è una certificazione legale.",
            styles["LotSheetSubtitle"],
        ),
        Paragraph("Dati del lotto", styles["LotSheetHeading"]),
    ]

    fatti = [
        ("Articolo", dettaglio.get("articolo")),
        ("Tipo lotto", "Ingresso" if dettaglio.get("tipo_lotto") == "A" else "Produzione"),
        ("Data creazione", dettaglio.get("data_creazione")),
        (
            "Quantità iniziale",
            f"{dettaglio.get('quantita_iniziale', '—')} {dettaglio.get('unita_misura', '')}".strip(),
        ),
        (
            "Quantità disponibile",
            f"{dettaglio.get('quantita_disponibile', '—')} {dettaglio.get('unita_misura', '')}".strip(),
        ),
        ("Origine dichiarata", dettaglio.get("origine")),
        ("Lotto fornitore", dettaglio.get("lotto_fornitore")),
        ("Scadenza", dettaglio.get("data_scadenza")),
        ("TMC", dettaglio.get("data_tmc")),
        (
            "Temperatura all'ingresso",
            f"{dettaglio.get('temperatura_ingresso')} °C"
            if dettaglio.get("temperatura_ingresso") is not None
            else None,
        ),
        ("Note lotto", dettaglio.get("note_lotto")),
    ]
    facts_table = Table(
        [[testo(label), testo(value)] for label, value in fatti],
        colWidths=[48 * mm, 130 * mm],
        hAlign="LEFT",
    )
    facts_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.extend([facts_table, Paragraph("Genealogia e documenti d'ingresso", styles["LotSheetHeading"])])

    cell_style = styles["LotSheetCell"]
    genealogy_rows = [[
        Paragraph("<b>Lotto</b>", cell_style),
        Paragraph("<b>Articolo e tipo</b>", cell_style),
        Paragraph("<b>Origine / lotto fornitore</b>", cell_style),
        Paragraph("<b>DDT e fornitore</b>", cell_style),
    ]]
    for item in genealogia:
        lot = item["dettaglio"]
        indent = "&nbsp;" * min(item["livello"] * 4, 40)
        document = lot.get("documento_ingresso") or {}
        quantity = item.get("quantita_usata")
        lot_label = testo(lot.get("codice_lotto"))
        if quantity is not None:
            lot_label += f"<br/>Input lavorato: {testo(quantity)}"
        ddt = " · ".join(
            value for value in (
                str(document.get("numero_ddt")) if document.get("numero_ddt") else None,
                str(document.get("data")) if document.get("data") else None,
                str(document.get("fornitore")) if document.get("fornitore") else None,
            ) if value
        )
        genealogy_rows.append([
            Paragraph(f"{indent}{lot_label}", cell_style),
            Paragraph(
                f"{testo(lot.get('articolo'))}<br/>{testo('Ingresso' if lot.get('tipo_lotto') == 'A' else 'Produzione')}",
                cell_style,
            ),
            Paragraph(
                f"{testo(lot.get('origine'))}<br/>Lotto fornitore: {testo(lot.get('lotto_fornitore'))}",
                cell_style,
            ),
            Paragraph(testo(ddt), cell_style),
        ])

    genealogy_table = Table(
        genealogy_rows,
        colWidths=[30 * mm, 43 * mm, 48 * mm, 57 * mm],
        repeatRows=1,
        hAlign="LEFT",
    )
    genealogy_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(genealogy_table)

    lavorazioni = [
        item["dettaglio"]
        for item in genealogia
        if item["dettaglio"].get("lavorazione")
    ]
    if lavorazioni:
        unita_per_lotto = {
            item["dettaglio"]["id"]: item["dettaglio"].get("unita_misura", "")
            for item in genealogia
        }
        story.append(Paragraph("Lavorazioni registrate", styles["LotSheetHeading"]))
        for lot in lavorazioni:
            work = lot["lavorazione"]
            inputs = ", ".join(
                f"{row.get('codice_lotto')} ({row.get('quantita')} "
                f"{unita_per_lotto.get(row.get('lotto_id'), '')})"
                for row in work.get("input", [])
            )
            description = " · ".join(
                value for value in (
                    str(work.get("data")) if work.get("data") else None,
                    str(work.get("descrizione")) if work.get("descrizione") else None,
                    str(work.get("operatore")) if work.get("operatore") else None,
                ) if value
            )
            story.append(Paragraph(
                f"<b>{testo(lot.get('codice_lotto'))}</b> — {testo(description)}"
                f"<br/>Lotti input: {testo(inputs)}",
                cell_style,
            ))
            story.append(Spacer(1, 3 * mm))

    doc.build(story)
    return buffer.getvalue()


# ------------------------------------------------------------------------- #
#  Generazione etichette DYMO (ReportLab canvas)
# ------------------------------------------------------------------------- #

def genera_etichetta_dymo_pdf(plu, prodotto, prezzo_kg="", ingredienti="",
                              codice="", lotto="", scadenza="", origine="",
                              allergeni=None, conservazione="", osa="",
                              peso="") -> bytes:
    """Genera il PDF dell'etichetta DYMO (formato 54x101 mm).

    Integra i dati di lotto e scadenza necessari nel flusso di laboratorio.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import mm
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.units import mm as millimeter
        from reportlab.pdfgen import canvas as pdfcanvas
        from reportlab.platypus import KeepInFrame, Paragraph, Spacer
        from xml.sax.saxutils import escape
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "reportlab non installato. Aggiungerlo a requirements.txt."
        ) from exc

    width, height = 54 * mm, 101 * mm  # formato DYMO 54x101 mm
    buffer = io.BytesIO()
    c = pdfcanvas.Canvas(buffer, pagesize=(width, height), pageCompression=0)

    normal = ParagraphStyle(
        "LabelNormal", fontName="Helvetica", fontSize=6, leading=7.1,
        spaceAfter=1.5,
    )
    heading = ParagraphStyle(
        "LabelHeading", fontName="Helvetica-Bold", fontSize=9, leading=10,
        alignment=1, spaceAfter=2,
    )
    allergen_style = ParagraphStyle(
        "LabelAllergens", parent=normal, fontName="Helvetica-Bold",
        textColor=colors.HexColor("#9a3412"), borderColor=colors.HexColor("#9a3412"),
        borderWidth=0.6, borderPadding=2, spaceBefore=1, spaceAfter=2,
    )
    story = [
        Paragraph(escape(str(prodotto)).upper(), heading),
        Paragraph(f"PLU / COD: {escape(str(plu))}", normal),
    ]
    if prezzo_kg:
        story.append(Paragraph(f"PREZZO: {escape(str(prezzo_kg))}", normal))
    if peso:
        story.append(Paragraph(f"PESO: {escape(str(peso))}", normal))
    if lotto:
        story.append(Paragraph(f"LOTTO: {escape(str(lotto))}", normal))
    elif codice:
        story.append(Paragraph(f"COD: {escape(str(codice))}", normal))
    if scadenza:
        story.append(Paragraph(escape(str(scadenza)), normal))
    if origine:
        story.append(Paragraph(f"ORIGINE: {escape(str(origine))}", normal))
    if ingredienti:
        story.append(Paragraph(f"<b>INGREDIENTI:</b> {escape(str(ingredienti))}", normal))
    if allergeni:
        etichette = {
            "frutta_a_guscio": "frutta a guscio",
        }
        testo_allergeni = ", ".join(
            etichette.get(str(allergene), str(allergene).replace("_", " "))
            for allergene in allergeni
        )
        story.append(Paragraph(
            f"ALLERGENI: {escape(testo_allergeni.upper())}",
            allergen_style,
        ))
    if conservazione:
        story.append(Paragraph(
            f"<b>CONSERVAZIONE:</b> {escape(str(conservazione))}",
            normal,
        ))
    if osa:
        story.append(Spacer(1, 1 * millimeter))
        story.append(Paragraph(f"<b>OSA</b><br/>{escape(str(osa)).replace(chr(10), '<br/>')}", normal))

    content = KeepInFrame(
        width - 8 * millimeter,
        height - 8 * millimeter,
        story,
        mode="shrink",
        hAlign="LEFT",
        vAlign="TOP",
    )
    content.wrapOn(c, width - 8 * millimeter, height - 8 * millimeter)
    content.drawOn(c, 4 * millimeter, 4 * millimeter)

    c.showPage()
    c.save()
    return buffer.getvalue()


# ------------------------------------------------------------------------- #
#  Scontrino termico (ESC/POS)
# ------------------------------------------------------------------------- #

def genera_scontrino_escpos(testata="", righe=None, totale="0.00",
                            iva="0.00") -> bytes:
    """Genera i bytes ESC/POS di uno scontrino termico.

    Produce testo semplice UTF-8 con comando di taglio, inviabile dall'Agent
    locale alla stampante termica raw.

    Args:
        testata: intestazione (nome azienda, P.IVA, ecc.).
        righe: lista di dict ``{descrizione, prezzo, qta}``.
        totale: totale dello scontrino.
        iva: importo IVA.

    Returns:
        I bytes in formato ESC/POS (o testo semplice se non e' installata la
        libreria).
    """
    righe = righe or []

    lines = []
    lines.extend(line.center(32) for line in (testata or "").splitlines())
    lines.append("=" * 32)
    for riga in righe:
        descrizione = str(riga.get("descrizione", ""))
        quantita = str(riga.get("qta", ""))
        prezzo = str(riga.get("prezzo", ""))
        lines.append(descrizione[:32])
        lines.append("{:<16}{:>16}".format(quantita[:16], prezzo[:16]))
    lines.append("=" * 32)
    lines.append("{:<26}{:>6}".format("TOTALE", totale))
    lines.append("{:<26}{:>6}".format("IVA", iva))
    lines.append("")
    lines.append("GRAZIE")
    text = "\n".join(lines) + "\n\x1d\x56\x41"
    return text.encode("utf-8")


# ------------------------------------------------------------------------- #
#  Stampa tramite win32 (usato dall'Agent locale / desktop)
# ------------------------------------------------------------------------- #

def stampa_pdf_via_win32(
    pdf_bytes, nome_file="traccia.pdf", output_dir=".", printer_name=None
):
    """Invia un PDF a Windows Print, opzionalmente a una stampante specifica.

    Solo Windows (pywin32). Utile per il client desktop o il Local Print
    Agent. In SaaS la stampa e' demandata all'Agent (vedi piano).

    Args:
        pdf_bytes: contenuto del PDF.
        nome_file: nome del file temporaneo.
        output_dir: directory di destinazione.
        printer_name: nome Windows della stampante di destinazione.

    Returns:
        True se Windows ha accettato il comando di stampa.

    Raises:
        RuntimeError: se Windows/pywin32 non e' disponibile o rifiuta il job.
    """
    import os
    path = os.path.join(output_dir, nome_file)
    with open(path, "wb") as f:
        f.write(pdf_bytes)

    try:
        import win32api
    except ImportError as exc:
        raise RuntimeError(
            "La stampa PDF richiede Windows e pywin32 sul computer dell'agent."
        ) from exc

    operation = "printto" if printer_name else "print"
    parameters = f'"{printer_name}"' if printer_name else None
    result = win32api.ShellExecute(
        None, operation, path, parameters, os.path.dirname(os.path.abspath(path)), 0
    )
    if not isinstance(result, int) or result <= 32:
        raise RuntimeError(
            f"Windows non ha accettato il job per la stampante "
            f"{printer_name or 'predefinita'}."
        )
    return True
