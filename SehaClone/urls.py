from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from SehaCloneApp import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('centros-medicos/', views.CentroMedicoList.as_view(), name='centros-medicos'),
    path('certificados/', views.CertificadoDetail.as_view(), name='certificados'),
    # /certificados/?codigo=YOUR_CODE&identificacion=YOUR_ID
    path('certificados/<int:certificado_id>/print/', views.print_certificate, name='print_certificate'),
    path('register/', views.UserRegistrationView.as_view(), name='user-registration'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)