from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status
from .models import CentroMedico, Certificado
from .serializers import CentroMedicoSerializer, CertificadoSerializer, UserRegistrationSerializer
from django.http import HttpResponse
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
import os
from PIL import Image as PILImage
import locale
from reportlab.lib.colors import HexColor, white
import arabic_reshaper
from bidi.algorithm import get_display
import unicodedata
import qrcode
from io import BytesIO as BytesIO2
from reportlab.lib.pagesizes import A4
import pytz

# Set locale to English
locale.setlocale(locale.LC_TIME, 'en_US.UTF-8')

# Register Noto Sans Arabic font
pdfmetrics.registerFont(TTFont('NotoSansArabic', 'SehaCloneApp/static/fonts/NotoSansArabic-Regular.ttf'))
pdfmetrics.registerFont(TTFont('NotoSansArabic-Bold', 'SehaCloneApp/static/fonts/NotoSansArabic-Bold.ttf'))

class UserRegistrationView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            {"message": "تم تسجيل المستخدم بنجاح"},
            status=status.HTTP_201_CREATED,
            headers=headers
        )

class CentroMedicoList(generics.ListAPIView):
    queryset = CentroMedico.objects.all()
    serializer_class = CentroMedicoSerializer

class CertificadoDetail(generics.RetrieveAPIView):
    serializer_class = CertificadoSerializer
    
    def get_queryset(self):
        return Certificado.objects.all()
    
    def get_object(self):
        codigo = self.request.query_params.get('codigo')
        identificacion = self.request.query_params.get('identificacion')
        
        if not codigo or not identificacion:
            raise ValidationError("الرمز والتعريف مطلوبان")
            
        try:
            return Certificado.objects.get(codigo=codigo, identificacion=identificacion)
        except Certificado.DoesNotExist:
            raise ValidationError("لم يتم العثور على الشهادة")

def print_certificate(request, certificado_id):
    try:
        certificado = Certificado.objects.get(id=certificado_id)
    except Certificado.DoesNotExist:
        return HttpResponse("لم يتم العثور على الشهادة", status=404)

    # Create a file-like buffer to receive PDF data
    buffer = BytesIO()

    # Create the PDF object, using the buffer as its "file."
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=0.5*inch, rightMargin=0.5*inch, topMargin=0, bottomMargin=0.5*inch)
    elements = []

    # Define colors
    BLUE_COLOR = HexColor('#1e3c72')  # Dark blue for headers and text
    LIGHT_BLUE_COLOR = HexColor('#3073b5')  # Slightly lighter blue for column 1 and 4
    LIGHT_GRAY = HexColor('#f5f5f5')  # Light gray for alternating rows
    BORDER_GRAY = HexColor('#d0d0d0')  # Gray for borders
    LINK_COLOR = HexColor('#0000EE')

    # Add styles
    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontSize=8,
        leading=14,
        fontName='NotoSansArabic',
        alignment=1,  # Center alignment
        textColor=BLUE_COLOR
    )
    
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=cell_style,
        fontName='NotoSansArabic',
        textColor=LIGHT_BLUE_COLOR  # Lighter blue for column 1 titles
    )

    rtl_title_style = ParagraphStyle(
        'RTLTitleStyle',
        parent=title_style,
        alignment=1,  # Center alignment
        fontSize=9,
        textColor=LIGHT_BLUE_COLOR  # Lighter blue for column 4 titles
    )
    
    cell_style_rtl = ParagraphStyle(
        'CellStyleRTL',
        parent=cell_style,
        alignment=1,  # Center alignment
        fontName='NotoSansArabic'
    )
    
    white_cell_style = ParagraphStyle(
        'WhiteCellStyle',
        parent=cell_style,
        textColor=white
    )

    white_title_style = ParagraphStyle(
        'WhiteTitleStyle',
        parent=title_style,
        textColor=white
    )

    white_title_style_rtl = ParagraphStyle(
        'WhiteTitleStyleRTL',
        parent=white_title_style,
        alignment=1  # Center alignment
    )

    white_cell_style_rtl = ParagraphStyle(
        'WhiteCellStyleRTL',
        parent=white_cell_style,
        alignment=1,  # Center alignment
        fontName='NotoSansArabic'
    )

    normal_style = ParagraphStyle(
        'NormalText',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        fontName='NotoSansArabic'
    )
    
    bold_style = ParagraphStyle(
        'BoldText',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        fontName='NotoSansArabic-Bold'
    )

    link_style = ParagraphStyle(
    'NormalText',
    parent=styles['Normal'],
    fontSize=8,
    leading=14,
    fontName='NotoSansArabic',
    alignment=1,
    textColor=LINK_COLOR
    )

    left_content_english_style = ParagraphStyle(
    'NormalText',
    parent=styles['Normal'],
    fontSize=8,
    leading=14,
    fontName='NotoSansArabic',
    alignment=1,
    )

    left_content_english2_style = ParagraphStyle(
    'NormalText',
    parent=styles['Normal'],
    fontSize=7,
    leading=10,
    fontName='NotoSansArabic',
    alignment=1,
    )

    left_content_english3_style = ParagraphStyle(
    'NormalText',
    parent=styles['Normal'],
    fontSize=7,
    leading=8,  # Reducido de 10 a 8 para menos espacio entre líneas
    fontName='NotoSansArabic-Bold',
    alignment=1,
    )

    # Define verification link
    VERIFICATION_LINK = "sehaclonefront.onrender.com/leave-query"

    def reshape_rtl_text(text):
        """Reshape and reverse Arabic text for RTL rendering"""
        if not text:
            return text
        # Normalize text to composed form
        text = unicodedata.normalize('NFC', text)
        # Reshape Arabic text
        reshaped_text = arabic_reshaper.reshape(text)
        # Apply bidirectional algorithm
        return get_display(reshaped_text)

    # Add header image
    img_path = os.path.join(settings.MEDIA_ROOT, 'PDF_Header.jpeg')
    if os.path.exists(img_path):
        with PILImage.open(img_path) as img:
            img_width, img_height = img.size
            # Calculate scale to fit full page width (including margins)
            scale = (doc.width + inch) / img_width
            new_height = img_height * scale
            
            # Create a table with a single cell spanning the full width
            header_table = Table([[Image(img_path, width=doc.width + inch, height=new_height)]], 
                               colWidths=[doc.width + inch])
            
            # Style the table to remove padding and borders
            header_table.setStyle(TableStyle([
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            elements.append(header_table)
            elements.append(Spacer(1, 20))

    # Create certificate data
    data = [
        [Paragraph('Leave ID', title_style), 
         Paragraph(certificado.codigo or '', cell_style), 
         Paragraph(certificado.codigo or '', cell_style),  # No RTL for Leave ID
         Paragraph(reshape_rtl_text('رمز الإجازة'), rtl_title_style)],
        [Paragraph('Leave Duration', white_title_style), 
         Paragraph(f'{certificado.duracion} {"day" if certificado.duracion == 1 else "days"} ({certificado.fecha_inicio.strftime("%d-%m-%Y")} to {certificado.fecha_salida.strftime("%d-%m-%Y")})', white_cell_style), 
         Paragraph(reshape_rtl_text(f'{certificado.duracion} {"يوم" if certificado.duracion == 1 else "أيام"} ({certificado.fecha_inicio_lunar.strftime("%Y-%m-%d")} الى {certificado.fecha_salida_lunar.strftime("%Y-%m-%d")})'), white_cell_style_rtl), 
         Paragraph(reshape_rtl_text('مدة الإجازة'), white_title_style_rtl)],
        [Paragraph('Admission Date', title_style), 
         Paragraph(certificado.fecha_inicio.strftime('%d-%m-%Y') or '', cell_style), 
         Paragraph(reshape_rtl_text(certificado.fecha_inicio_lunar.strftime('%d-%m-%Y') or ''), cell_style_rtl), 
         Paragraph(reshape_rtl_text('تاريخ الدخول'), rtl_title_style)],
        [Paragraph('Discharge Date', title_style), 
         Paragraph(certificado.fecha_salida.strftime('%d-%m-%Y') or '', cell_style), 
         Paragraph(reshape_rtl_text(certificado.fecha_salida_lunar.strftime('%d-%m-%Y') or ''), cell_style_rtl), 
         Paragraph(reshape_rtl_text('تاريخ الخروج'), rtl_title_style)],
        [Paragraph('Issue Date', title_style), 
         Paragraph(certificado.fecha_creacion.strftime('%d-%m-%Y') or '', cell_style), 
         Paragraph(certificado.fecha_creacion.strftime('%d-%m-%Y') or '', cell_style),  # No RTL for Issue Date
         Paragraph(reshape_rtl_text('تاريخ إصدار التقرير'), rtl_title_style)],
        [Paragraph('Name', title_style), 
         Paragraph(certificado.nombre_paciente_ingles or '', cell_style), 
         Paragraph(reshape_rtl_text(certificado.nombre_paciente or ''), cell_style_rtl), 
         Paragraph(reshape_rtl_text('الاسم'), rtl_title_style)],
        [Paragraph('National ID / Iqama', title_style), 
         Paragraph(certificado.identificacion or '', cell_style), 
         Paragraph(certificado.identificacion or '', cell_style),  # No RTL for Iqama
         Paragraph(reshape_rtl_text('رقم الهوية / الإقامة'), rtl_title_style)],
        [Paragraph('Nationality', title_style), 
         Paragraph(certificado.nacionalidad_ingles or '', cell_style), 
         Paragraph(reshape_rtl_text(certificado.nacionalidad or ''), cell_style_rtl), 
         Paragraph(reshape_rtl_text('الجنسية'), rtl_title_style)],
        [Paragraph('Employer', title_style), 
         Paragraph(certificado.centro_servicio_ingles or '', cell_style), 
         Paragraph(reshape_rtl_text(certificado.centro_servicio or ''), cell_style_rtl), 
         Paragraph(reshape_rtl_text('جهة العمل'), rtl_title_style)],
        [Paragraph('Physician Name', title_style), 
         Paragraph(certificado.nombre_medico_ingles or '', cell_style), 
         Paragraph(reshape_rtl_text(certificado.nombre_medico or ''), cell_style_rtl), 
         Paragraph(reshape_rtl_text('اسم الطبيب المعالج'), rtl_title_style)],
        [Paragraph('Position', title_style), 
         Paragraph(certificado.titulo_trabajo_ingles or '', cell_style), 
         Paragraph(reshape_rtl_text(certificado.titulo_trabajo or ''), cell_style_rtl), 
         Paragraph(reshape_rtl_text('المسمى الوظيفي'), rtl_title_style)]
    ]

    # Create table with adjusted column widths (narrower outer columns)
    total_width = doc.width
    outer_col_width = total_width * 0.15  # 20% for title columns
    inner_col_width = total_width * 0.35  # 30% for value columns
    table = Table(data, colWidths=[outer_col_width, inner_col_width, inner_col_width, outer_col_width])

    # Define table styles
    table_style = [
        # Alignment
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Fonts and colors
        ('TEXTCOLOR', (0, 0), (0, -1), LIGHT_BLUE_COLOR),  # Column 1 (English titles)
        ('TEXTCOLOR', (1, 0), (1, -1), BLUE_COLOR),  # Column 2 (English values)
        ('TEXTCOLOR', (2, 0), (2, -1), BLUE_COLOR),  # Column 3 (Arabic values)
        ('TEXTCOLOR', (3, 0), (3, -1), LIGHT_BLUE_COLOR),  # Column 4 (Arabic titles)
        ('FONTNAME', (0, 0), (-1, -1), 'NotoSansArabic'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        
        # Borders
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ('ROUNDEDCORNERS', [6, 6, 6, 6]),
        
        # Row colors
        ('BACKGROUND', (0, 1), (-1, 1), BLUE_COLOR),  # Leave Duration row in blue
        ('TEXTCOLOR', (0, 1), (-1, 1), white),  # White text for blue row
        
        # Merge cells for specific rows (Leave ID, Issue Date, National ID)
        ('SPAN', (1, 0), (2, 0)),  # Leave ID
        ('SPAN', (1, 4), (2, 4)),  # Issue Date
        ('SPAN', (1, 6), (2, 6)),  # National ID / Iqama
        
        # Padding
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),

        # Aumentar padding vertical
        ('TOPPADDING', (0, 0), (-1, -1), 8),  # Aumentado de 6 a 10
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),  # Aumentado de 6 a 10
        ('LEFTPADDING', (0, 0), (-1, -1), 2),  # Añadir padding horizontal
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),  # Añadir padding horizontal
        
        # Aumentar espacio entre líneas en el contenido
        ('LEADING', (0, 0), (-1, -1), 14),  # Añadir espacio entre líneas
    ]

    # Add alternating row colors (inverted)
    for i in range(len(data)):
        if i != 1 and i % 2 == 1:  # Changed from 0 to 1 to invert the pattern
            table_style.append(('BACKGROUND', (0, i), (-1, i), LIGHT_GRAY))

    table.setStyle(TableStyle(table_style))
    elements.append(table)
    elements.append(Spacer(1, 20))

    ############################################# INFO SECTION ########################################################

    # Calculate the total width of the document and margins
    doc_width = doc.width
    side_margin = 1  # Small margin on each side, adjust as needed
    usable_width = doc_width - 2 * side_margin

    # Define column widths to center the separator
    center_col_width = 50  # Minimum width for the center column with the separator
    outer_col_width = (usable_width - center_col_width) / 2  # Equal width for left and right columns

    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(VERIFICATION_LINK)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")

    # Save QR code to BytesIO
    qr_buffer = BytesIO2()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)

    # Create QR image with fixed size
    qr_image = Image(qr_buffer, width=1*inch, height=1*inch)
    qr_image.hAlign = 'CENTER'

    # Prepare center icon
    center_icon = None
    if certificado.centro_medico.icono and os.path.exists(certificado.centro_medico.icono.path):
        with PILImage.open(certificado.centro_medico.icono.path) as img:
            img_width, img_height = img.size
            aspect_ratio = img_width / img_height
            icon_height = 0.75*inch
            icon_width = icon_height * aspect_ratio
            
            center_icon = Image(certificado.centro_medico.icono.path, width=icon_width, height=icon_height)
            center_icon.hAlign = 'CENTER'

    # 1) Collect your raw text lines
    lines = []
    if certificado.centro_medico.nombre:
        lines.append(certificado.centro_medico.nombre)
    if certificado.centro_medico.descripcion:
        lines.append(certificado.centro_medico.descripcion)
    if certificado.centro_medico.numero_licencia:
        lines.append(f"ﺮﻗﻢ اﻟﺘﺮﺧﻴﺺ: {certificado.centro_medico.numero_licencia}")

    cell_flowables = []
    for line in lines:
        cell_flowables.append(Paragraph(reshape_rtl_text(line), left_content_english3_style))
        cell_flowables.append(Spacer(1, 2))

    # Create table data
    table_data = [
    # Fila 1: QR y Icono
        [
            qr_image,
            '',
            center_icon if center_icon else ''
        ],
        # Fila 2: Contenido combinado en columna 3
        [
            Paragraph(reshape_rtl_text("ﻟﻠﺘﺤﻘﻖ ﻣﻦ ﺑﻴﺎﻧﺎت اﻟﺘﻘﺮﻳﺮ ﻳﺮﺟﻰ اﻟﺘﺄﻛﺪ ﻣﻦ زﻳﺎرة ﻣﻮﻗﻊ ﻣﻨﺼﺔ ﺻﺤﺔ اﻟﺮﺳﻤﻲ"), left_content_english_style),
            '',
            cell_flowables
        ],
        # Fila 3: Mantener estructura para otras columnas
        [
            Paragraph("To check the report please visit Seha's official website", left_content_english2_style),
            '',
            ''  # Celda vacía
        ],
        # Fila 4: Mantener estructura para el link
        [
            Paragraph(VERIFICATION_LINK, link_style),
            '',
            ''  # Celda vacía
        ]
    ]   

    # Create table with adjusted column widths
    info_table = Table(table_data, colWidths=[outer_col_width, center_col_width, outer_col_width])

    # Style the table
    info_table.setStyle(TableStyle([
        # General alignment
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

        # Remove horizontal padding in outer columns
        ('LEFTPADDING', (0, 0), (0, -1), 0),
        ('RIGHTPADDING', (2, 0), (2, -1), 0),

        # Row heights
        ('TOPPADDING', (0, 0), (-1, 0), 5),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
        ('TOPPADDING', (0, 1), (-1, 1), 1),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 1),
        ('TOPPADDING', (0, 2), (-1, 2), 1),
        ('BOTTOMPADDING', (0, 2), (-1, 2), 1),

        ('SPAN', (2, 1), (2, 3)),  # Combinar celdas verticalmente en columna 3
        ('VALIGN', (2, 1), (2, 3), 'TOP'),  # Alinear verticalmente al centro
        ('LEADING', (2, 1), (2, 1), 8),  # Aplicar espaciado reducido
    ]))

    # Add the table with proper margins
    margin_table = Table([[info_table]], colWidths=[doc_width])
    margin_table.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (0, 0), side_margin),
        ('RIGHTPADDING', (0, 0), (0, 0), side_margin),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))

    # Add styles for text alignment
    normal_style.alignment = 1  # 1 = TA_CENTER
    bold_style.alignment = 1    # 1 = TA_CENTER

    elements.append(margin_table)
    elements.append(Spacer(1, 20))

    ############################################## FOOT SECTION ################################################################

    # Bottom section with creation time and signature
    fecha = certificado.fecha_creacion
    # Convertir a Asia/Riyadh
    fecha_riyadh = fecha.astimezone(pytz.timezone('Asia/Riyadh'))
    hora_str = f"{fecha_riyadh.strftime('%I:%M %p')}"
    fecha_str = f"{fecha_riyadh.strftime('%A, %d %B %Y')}"
    
    # Create time/date style with left alignment
    left_style = ParagraphStyle(
        'LeftStyle',
        parent=normal_style,
        alignment=0,  # 0 = TA_LEFT
        fontSize=8,
        leading=10,
        fontName='NotoSansArabic'
    )
    
    # Create signature image if it exists
    signature = None
    if os.path.exists(os.path.join(settings.MEDIA_ROOT, 'signature.jpeg')):
        with PILImage.open(os.path.join(settings.MEDIA_ROOT, 'signature.jpeg')) as img:
            width, height = img.size
            aspect_ratio = width / height
            target_height = 0.6*inch
            target_width = target_height * aspect_ratio
            signature = Image(os.path.join(settings.MEDIA_ROOT, 'signature.jpeg'), 
                            width=target_width, height=target_height)
            signature.hAlign = 'RIGHT'  # Align the image itself to the right
    
    # Calculate available width and column widths
    available_width = doc.width - (2 * side_margin)  # Total width minus margins
    col1_width = available_width * 0.6  # 60% for date/time column
    col2_width = available_width * 0.4  # 40% for signature column
    
    bottom_table = Table([
        [
            Paragraph(hora_str, left_style),
            signature if signature else ''
        ],
        [
            Paragraph(fecha_str, left_style),
            ''  # Empty cell for the second row of the signature
        ]
    ], colWidths=[col1_width, col2_width])

    bottom_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),  # Left align time and date
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),  # Right align signature column
        ('VALIGN', (0, 0), (0, 0), 'BOTTOM'),  # Time aligned to bottom
        ('VALIGN', (0, 1), (0, 1), 'TOP'),  # Date aligned to top
        ('VALIGN', (1, 0), (1, -1), 'MIDDLE'),  # Signature vertically centered
        ('SPAN', (1, 0), (1, 1)),  # Make signature span both rows
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (0, -1), side_margin),  # Left margin for time/date
        ('RIGHTPADDING', (1, 0), (1, -1), side_margin * 2),  # Double right margin for signature
    ]))

    # Create a wrapper table without additional margins
    wrapper_table = Table([[bottom_table]], colWidths=[doc.width])
    wrapper_table.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
    ]))

    elements.append(wrapper_table)
    elements.append(Spacer(1, 10))

    # Build PDF
    doc.build(elements)

    # Get the value of the buffer and write the response
    pdf = buffer.getvalue()
    buffer.close()

    # Create the HTTP response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="SickLeaves-{certificado.codigo}.PDF"'
    response.write(pdf)

    return response