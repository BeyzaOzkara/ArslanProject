"""Mail ile aynı verilerden Türkçe destekli PDF oluşturur."""
import os
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape


def build_sevkiyat_pdf(context):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle

    if 'SevkiyatFont' not in pdfmetrics.getRegisteredFontNames():
        candidates = [os.environ.get('SEVKIYAT_PDF_FONT', ''),
                      str(Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts/arial.ttf'),
                      '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                      '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf']
        font = next((p for p in candidates if p and Path(p).is_file()), None)
        if not font:
            raise RuntimeError('PDF için Türkçe TTF font bulunamadı; SEVKIYAT_PDF_FONT tanımlayın.')
        pdfmetrics.registerFont(TTFont('SevkiyatFont', font))
    normal = ParagraphStyle('normal', fontName='SevkiyatFont', fontSize=9, leading=13)
    heading = ParagraphStyle('heading', parent=normal, fontSize=12, leading=17,
                             textColor=colors.HexColor('#1f3864'), spaceBefore=14, spaceAfter=8)

    def text(value, style=normal):
        return Paragraph(escape(str(value if value is not None else '-')), style)

    def kg(value):
        return f'{value or 0:,.2f}'.translate(str.maketrans(',.', '.,'))

    stream = BytesIO()
    width = A4[0] - 72

    def table(headers, rows, ratios):
        data = [[text(h) for h in headers]]
        for row in rows:
            cells = [text(v) for v in row]
            cells[-1] = text(row[-1], ParagraphStyle('right', parent=normal, alignment=2))
            data.append(cells)
        result = Table(data, colWidths=[width * r for r in ratios], repeatRows=1, hAlign='LEFT')
        result.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#d9e2f3')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7f7f7')]),
            ('GRID', (0, 0), (-1, -1), .5, colors.HexColor('#8c8c8c')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ]))
        return result

    title_style = ParagraphStyle('title', parent=normal, fontSize=16, leading=21, textColor=colors.white)
    subtitle_style = ParagraphStyle('subtitle', parent=normal, fontSize=9, leading=14, textColor=colors.white)
    banner = Table([[text('GÜNLÜK SEVKİYAT RAPORU', title_style)],
                    [text(f"Rapor Tarihi: {context['report_date']} | Rapor Saati: {context['report_time']}", subtitle_style)]],
                   colWidths=[A4[0]], hAlign='LEFT')
    banner.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#1f3864')),
        ('LEFTPADDING', (0, 0), (-1, -1), 42),
        ('RIGHTPADDING', (0, 0), (-1, -1), 42),
        ('TOPPADDING', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 14),
    ]))
    story = [text(f"{context['detail_date']} tarihine ait günlük sevkiyat dökümü, "
                  f"{context['report_date']} saat {context['report_time']} itibarıyla "
                  'sistemde kayıtlı veriler esas alınarak hazırlanmıştır.')]
    story.extend([text('1. Genel Özet', heading), table(['Gösterge', 'Miktar (kg)'], [
        [f"Günlük Sevk Edilen ({context['today']})", kg(context['daily_total_kg'])],
        [f"Bu Ay Toplam Sevk Edilen ({context['period']})", kg(context['total_kg'])]], [.72, .28])])
    rows = [[i, r['Firma'], r['SatisPozisyon'], kg(r['TOPLAM'])]
            for i, r in enumerate(context['details'], 1)]
    rows = rows or [['-', 'Bu tarih için sevkiyat bulunamadı.', '-', kg(0)]]
    rows.append(['', 'GÜNLÜK SEVKİYAT TOPLAMI', '', kg(context['detail_total_kg'])])
    story.extend([text(f"2. Günlük Sevkiyat Dökümü - {context['detail_date']}", heading),
                  table(['Sıra', 'Firma', 'Satış Pozisyonu', 'Toplam (kg)'], rows, [.07, .46, .25, .22])])
    top = [[i, r['Firma'], kg(r['TOPLAM'])] for i, r in enumerate(context['top_firms'], 1)]
    story.extend([text(f"3. Bu Ay En Çok Sevkiyat Yapılan 5 Firma - {context['period']}", heading),
                  table(['Sıra', 'Firma', 'Toplam (kg)'],
                        top or [['-', 'Bu ay için sevkiyat bulunamadı.', kg(0)]], [.07, .68, .25])])
    note = Table([[text('Bu rapor Arslan Takip sistemi tarafından otomatik olarak oluşturulmuştur. '
                       'Miktarlar kilogram (kg) cinsindendir. Günlük döküm ve aylık ilk 5 listesi '
                       'Fason dışındaki kartlarla eşleşen sevk edilmiş ürün çıkışlarını içerir; '
                       'genel özetin filtreleri farklıdır.')]], colWidths=[A4[0]])
    note.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f2f2f2')),
        ('LEFTPADDING', (0, 0), (-1, -1), 42),
        ('RIGHTPADDING', (0, 0), (-1, -1), 42),
        ('TOPPADDING', (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 28),
    ]))
    _, banner_height = banner.wrap(A4[0], A4[1])
    _, note_height = note.wrap(A4[0], A4[1])
    # İçerik her sayfada sabit başlık ve footer için ayrılan alanın dışında kalır.
    doc = SimpleDocTemplate(stream, pagesize=A4, leftMargin=36, rightMargin=36,
                            topMargin=banner_height + 16, bottomMargin=note_height + 16,
                            title='Günlük Sevkiyat Raporu')

    def footer(canvas, document):
        canvas.saveState()
        banner.drawOn(canvas, 0, A4[1] - banner_height)
        note.drawOn(canvas, 0, 0)
        canvas.setFillColor(colors.HexColor('#666666'))
        canvas.setFont('SevkiyatFont', 8)
        canvas.drawRightString(A4[0] - 42, 10, f'Sayfa {document.page}')
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return stream.getvalue()
