from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework import status
from .models import CentroMedico, Certificado
from .serializers import CentroMedicoSerializer, CertificadoSerializer, UserRegistrationSerializer
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.conf import settings
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, Frame, PageTemplate, BaseDocTemplate
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
from datetime import datetime
import os
from PIL import Image as PILImage
import locale

# Set locale to English
locale.setlocale(locale.LC_TIME, 'en_US.UTF-8')

# Register Cairo font
pdfmetrics.registerFont(TTFont('Cairo', 'SehaCloneApp/static/fonts/Cairo-Regular.ttf'))
pdfmetrics.registerFont(TTFont('Cairo-Bold', 'SehaCloneApp/static/fonts/Cairo-Bold.ttf'))

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
    doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=0, rightMargin=0, topMargin=0, bottomMargin=0)
    elements = []

    # Add styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        alignment=1,  # Center alignment
        spaceAfter=30,
        fontName='Cairo-Bold'
    )
    
    normal_style = ParagraphStyle(
        'NormalText',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        fontName='Cairo'
    )
    
    bold_style = ParagraphStyle(
        'BoldText',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        fontName='Cairo-Bold'
    )

    # Add header image
    img_path = os.path.join(settings.MEDIA_ROOT, 'PDF_Header.jpeg')
    if os.path.exists(img_path):
        # Get image dimensions using PIL
        with PILImage.open(img_path) as img:
            img_width, img_height = img.size
            # Calculate scale to fit page width
            scale = doc.width / img_width
            # Calculate new height maintaining aspect ratio
            new_height = img_height * scale
            
            img = Image(img_path, width=doc.width, height=new_height)
            img.hAlign = 'CENTER'
            elements.append(img)
            elements.append(Spacer(1, 5))


    # Define table widths that will be used consistently
    content_width = 4*inch
    label_width = 2*inch
    table_width = label_width + content_width

    # Create certificate data
    data = [
        [certificado.codigo, 'رمز الإجازة'],
        [certificado.nombre_paciente, 'اسم المريض'],
        [certificado.identificacion, 'الهوية / الإقامة'],
        [certificado.nacionalidad, 'جنسية'],
        [certificado.centro_servicio, 'مركز الخدمة'],
        [certificado.nombre_medico, 'اسم الطبيب'],
        [certificado.titulo_trabajo, 'مسمى وظيفي'],
        [certificado.fecha_inicio.strftime('%d-%m-%Y'), 'تاريخ البدء'],
        [certificado.fecha_salida.strftime('%d-%m-%Y'), 'تاريخ الانتهاء'],
        [f"أيام {certificado.duracion}", 'مدة'],
    ]

    # Create table
    table = Table(data, colWidths=[content_width, label_width])
    table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),  # Right alignment for Arabic
        ('FONTNAME', (0, 0), (0, -1), 'Cairo'),
        ('FONTNAME', (1, 0), (1, -1), 'Cairo-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 10))

    # Calculate the remaining space on each side
    remaining_width = doc.width - table_width
    side_margin = remaining_width / 2

    # Create two columns for company info and verification link
    left_content = []
    right_content = []

    # Left column - Verification info
    left_content.append(Paragraph("للتأكد من صحة بيانات التقرير، يرجى زيارة الموقع الرسمي لهيئة الصحة.", normal_style))
    left_content.append(Spacer(1, 5))
    left_content.append(Paragraph("www.seha.sa/facilities/sehaenqiry", normal_style))

    # Right column - Company info
    # Add company icon
    if certificado.centro_medico.icono:
        # Get original image dimensions to calculate aspect ratio
        with PILImage.open(certificado.centro_medico.icono.path) as img:
            img_width, img_height = img.size
            # Calculate width based on fixed height to maintain aspect ratio
            aspect_ratio = img_width / img_height
            icon_height = 0.5*inch
            icon_width = icon_height * aspect_ratio
            
            icon = Image(certificado.centro_medico.icono.path, width=icon_width, height=icon_height)
            icon.hAlign = 'RIGHT'
            # Create a table cell for the icon with right alignment
            icon_cell = Table([[icon]], colWidths=[table_width/2])
            icon_cell.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ]))
            right_content.append(icon_cell)
            right_content.append(Spacer(1, 5))

    right_content.append(Paragraph(certificado.centro_medico.nombre, bold_style))
    right_content.append(Paragraph(certificado.centro_medico.descripcion, normal_style))
    right_content.append(Spacer(1, 5))
    right_content.append(Paragraph(f"{certificado.centro_medico.numero_licencia} :رقم الترخيص", normal_style))

    # Create table for two columns layout with proper margins
    info_table = Table([[
        Table([[content] for content in left_content], colWidths=[table_width/2]),
        Table([[content] for content in right_content], colWidths=[table_width/2])
    ]], colWidths=[table_width/2, table_width/2])
    
    # Add the table with proper left margin to align with certificate data table
    margin_table = Table([[info_table]], colWidths=[doc.width])
    margin_table.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (0, 0), side_margin),
        ('RIGHTPADDING', (0, 0), (0, 0), side_margin),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),  # Right alignment for Arabic
    ]))

    # Add styles for RTL text alignment
    normal_style.alignment = 2  # 2 = TA_RIGHT
    bold_style.alignment = 2    # 2 = TA_RIGHT

    elements.append(margin_table)
    elements.append(Spacer(1, 10))

    # Bottom section with creation time and signature
    fecha = certificado.fecha_creacion
    fecha_str = f"AM {fecha.strftime('%H:%M')}, {fecha.strftime('%A')}, {fecha.strftime('%d %B %Y')}"
    
    bottom_table = Table([
        [
            Paragraph(fecha_str, normal_style),
            Image(os.path.join(settings.MEDIA_ROOT, 'signature.jpeg'), width=1.5*inch, height=0.75*inch) if os.path.exists(os.path.join(settings.MEDIA_ROOT, 'signature.jpeg')) else ''
        ]
    ], colWidths=[4*inch, 4*inch])

    bottom_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
    ]))

    elements.append(bottom_table)

    # Build PDF
    doc.build(elements)

    # Get the value of the buffer and write the response
    pdf = buffer.getvalue()
    buffer.close()

    # Create the HTTP response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="certificate_{certificado.codigo}.pdf"'
    response.write(pdf)

    return response