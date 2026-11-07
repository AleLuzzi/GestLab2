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
                              codice="", lotto="", scadenza="", origine="") -> bytes:
    """Genera il PDF dell'etichetta DYMO (formato 54x101 mm).

    Integra i dati di lotto e scadenza necessari nel flusso di laboratorio.
    """
    try:
        from reportlab.pdfgen import canvas as pdfcanvas
        from reportlab.lib.pagesizes import mm
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "reportlab non installato. Aggiungerlo a requirements.txt."
        ) from exc

    width, height = 54 * mm, 101 * mm  # formato DYMO 54x101 mm
    buffer = io.BytesIO()
    c = pdfcanvas.Canvas(buffer, pagesize=(width, height))

    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(width / 2, height - 20 * mm, str(plu))

    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(width / 2, height - 30 * mm, str(prodotto).upper())

    c.setFont("Helvetica", 8)
    if prezzo_kg:
        c.drawString(5 * mm, height - 45 * mm, "PREZZO: {}".format(prezzo_kg))

    if codice:
        c.drawString(5 * mm, height - 53 * mm, "COD: {}".format(codice))

    if lotto:
        c.setFont("Helvetica", 6)
        c.drawString(5 * mm, height - 62 * mm, f"LOTTO: {lotto[:24]}")
    if scadenza:
        c.setFont("Helvetica", 6)
        c.drawString(5 * mm, height - 68 * mm, f"SCAD: {scadenza}")
    if origine:
        c.setFont("Helvetica", 6)
        c.drawString(5 * mm, height - 74 * mm, f"ORIG: {origine[:28]}")

    # Ingredienti (testo su piu' righe)
    y = height - 82 * mm
    c.setFont("Helvetica", 6)
    for line in str(ingredienti).splitlines()[:8]:
        c.drawString(5 * mm, y, line[:40])
        y -= 4 * mm

    c.showPage()
    c.save()
    return buffer.getvalue()


# ------------------------------------------------------------------------- #
#  Scontrino termico (ESC/POS)
# ------------------------------------------------------------------------- #

def genera_scontrino_escpos(testata="", righe=None, totale="0.00",
                            iva="0.00") -> bytes:
    """Genera i bytes ESC/POS di uno scontrino termico.

    Se ``python-escpos`` non e' disponibile, produce un testo semplificato
    (UTF-8) che l'Agent locale puo' comunque inviare alla stampante raw.

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

    try:
        from escpos.printer import Network  # noqa: F401
        _use_escpos = True
    except ImportError:
        _use_escpos = False

    if not _use_escpos:
        # Testo semplice con chiusura (ESC/POS "cut" \x1d\x56)
        lines = []
        lines.append((testata or "").center(32))
        lines.append("=" * 32)
        for r in righe:
            desc = str(r.get("descrizione", ""))
            prezzo = str(r.get("prezzo", ""))
            lines.append("{:<26}{:>6}".format(desc[:26], prezzo))
        lines.append("=" * 32)
        lines.append("{:<26}{:>6}".format("TOTALE", totale))
        lines.append("{:<26}{:>6}".format("IVA", iva))
        lines.append("")
        lines.append("GRAZIE")
        text = "\n".join(lines) + "\n\x1d\x56\x41"
        return text.encode("utf-8")

    # TODO: implementazione completa con python-escpos (Network/USB).
    # Di default si produce il testo semplificato anche se la libreria e'
    # installata, per non accoppiare il core al driver di stampa.
    return (testata or "").encode("utf-8")


# ------------------------------------------------------------------------- #
#  Stampa tramite win32 (usato dall'Agent locale / desktop)
# ------------------------------------------------------------------------- #

def stampa_pdf_via_win32(pdf_bytes, nome_file="traccia.pdf", output_dir="."):
    """Salva un PDF e lo invia alla stampante predefinita via ``win32api``.

    Solo Windows (pywin32). Utile per il client desktop o il Local Print
    Agent. In SaaS la stampa e' demandata all'Agent (vedi piano).

    Args:
        pdf_bytes: contenuto del PDF.
        nome_file: nome del file temporaneo.
        output_dir: directory di destinazione.

    Returns:
        Il percorso del file salvato.
    """
    import os
    path = os.path.join(output_dir, nome_file)
    with open(path, "wb") as f:
        f.write(pdf_bytes)

    try:
        import win32api
        win32api.ShellExecute(None, "print", path, None, os.path.dirname(path), 0)
    except ImportError:
        pass  # su piattaforme non Windows la stampa va gestita dall'Agent
    return path
