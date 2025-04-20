from django.contrib import admin
from .models import CentroMedico, Certificado
from django.utils.html import format_html
from django.urls import reverse
from admin_interface.models import Theme

admin.site.unregister(Theme)

@admin.register(CentroMedico)
class CentroMedicoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion', 'privado', 'mostrar_icono')
    
    def mostrar_icono(self, obj):
        if obj.icono:
            return format_html(
                '<img src="{}" width="auto" height="20" style="border-radius: 5px;"/>', 
                obj.icono.url
            )
        return "لا توجد صورة"
    mostrar_icono.short_description = 'ايقون'
    
    readonly_fields = ('imagen_preview',)
    fields = ('nombre', 'descripcion', 'icono', 'numero_licencia', 'privado', 'imagen_preview')
    
    def imagen_preview(self, obj):
        if obj.icono:
            return format_html(
                '<img src="{}" width="200" style="border-radius: 8px; margin: 10px 0;"/>', 
                obj.icono.url
            )
        return "لا توجد صورة"
    imagen_preview.short_description = "معاينة الأيقونة"
    
    search_fields = ('nombre',)

@admin.register(Certificado)
class CertificadoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre_paciente', 'centro_medico', 'fecha_inicio', 'fecha_salida', 'print_certificate')
    search_fields = ('codigo', 'nombre_paciente', 'identificacion')
    readonly_fields = ('codigo', 'fecha_creacion')

    def print_certificate(self, obj):
        url = reverse('print_certificate', args=[obj.id])
        return format_html(
            '<a class="button" href="{}" target="_blank">طباعة</a>',
            url
        )
    print_certificate.short_description = 'خيارات'
    print_certificate.allow_tags = True
