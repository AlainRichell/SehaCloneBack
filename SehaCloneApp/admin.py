from django.contrib import admin
from .models import CentroMedico, Certificado
from django.utils.html import format_html
from django.urls import reverse
from admin_interface.models import Theme
from django.conf import settings

admin.site.site_url = settings.CLIENT_URL

admin.site.unregister(Theme)

@admin.register(CentroMedico)
class CentroMedicoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion', 'privado', 'mostrar_icono')
    exclude = ('usuario',)
    
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

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(usuario=request.user)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.usuario = request.user
        super().save_model(request, obj, form, change)

@admin.register(Certificado)
class CertificadoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre_paciente', 'centro_medico', 'fecha_inicio', 'fecha_salida', 'print_certificate')
    search_fields = ('codigo', 'nombre_paciente', 'identificacion')
    readonly_fields = ('codigo', 'fecha_inicio_lunar', 'fecha_salida_lunar')
    exclude = ('usuario',)

    def print_certificate(self, obj):
        url = reverse('print_certificate', args=[obj.id])
        return format_html(
            '<a class="button" href="{}" target="_blank">طباعة</a>',
            url
        )
    print_certificate.short_description = 'خيارات'
    print_certificate.allow_tags = True

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(usuario=request.user)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "centro_medico":
            kwargs["queryset"] = CentroMedico.objects.filter(usuario=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.usuario = request.user
        super().save_model(request, obj, form, change)
