from django.db import models
from django.core.exceptions import ValidationError
import random
from datetime import datetime

class CentroMedico(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="اسم" )
    descripcion = models.CharField(max_length=255, blank=True, null=True, verbose_name="وصف")
    numero_licencia = models.CharField(max_length=50, blank=True, null=True, unique=True, db_index=True, verbose_name="رقم الترخيص")
    icono = models.ImageField(upload_to='icons/', verbose_name="ايقون")
    privado = models.BooleanField(default=False, verbose_name="مركز خاص")

    def __str__(self):
        return self.nombre
    
    class Meta:
        verbose_name = 'المركز الطبي'
        verbose_name_plural = 'المراكز الطبية'

class Certificado(models.Model):
    centro_medico = models.ForeignKey(
        CentroMedico,
        on_delete=models.PROTECT,
        related_name='certificados',
        verbose_name="المركز الطبي"
    )
    nombre_paciente = models.CharField(max_length=100, verbose_name="اسم المريض")
    identificacion = models.CharField(max_length=50, db_index=True, verbose_name="الهوية / الإقامة")
    codigo = models.CharField(max_length=50, unique=True, db_index=True, verbose_name="رمز الإجازة")
    nacionalidad = models.CharField(max_length=50, verbose_name="جنسية")
    centro_servicio = models.CharField(max_length=100, verbose_name="مركز الخدمة")
    nombre_medico = models.CharField(max_length=100, verbose_name="اسم الطبيب")
    titulo_trabajo = models.CharField(max_length=100, verbose_name="مسمى وظيفي")
    fecha_inicio = models.DateField(verbose_name="تاريخ البدء")
    fecha_salida = models.DateField(verbose_name="تاريخ الانتهاء")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    duracion = models.IntegerField(blank=True, null=True, verbose_name="مدة")

    class Meta:
        verbose_name = 'شهادة'
        verbose_name_plural = 'الشهادات'

    def generate_code(self):
        today = datetime.now()
        year = str(today.year)[-2:]
        month = str(today.month).zfill(2)
        day = str(today.day).zfill(2)
        random_digits = ''.join([str(random.randint(0, 9)) for _ in range(5)])
        prefix = "PSL" if self.centro_medico.privado else "GSL"
        return f"{prefix}{year}{month}{day}{random_digits}"

    def clean(self):
        if self.fecha_salida <= self.fecha_inicio:
            raise ValidationError("يجب أن يكون تاريخ البدء بعد تاريخ الانتهاء")
    
    def save(self, *args, **kwargs):
        if not self.codigo:
            while True:
                new_code = self.generate_code()
                if not Certificado.objects.filter(codigo=new_code).exists():
                    self.codigo = new_code
                    break
        
        # Calculate duration if not provided
        if not self.duracion:
            delta = self.fecha_salida - self.fecha_inicio
            self.duracion = delta.days
        
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"شهادة {self.codigo} - {self.nombre_paciente}"