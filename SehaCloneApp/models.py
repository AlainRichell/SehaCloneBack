from django.db import models
from django.core.exceptions import ValidationError
import random
from datetime import datetime
from hijri_converter import convert

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
    nombre_paciente_ingles = models.CharField(max_length=100, verbose_name="Patient Name", blank=True, null=True)
    identificacion = models.CharField(max_length=50, db_index=True, verbose_name="الهوية / الإقامة")
    codigo = models.CharField(max_length=50, unique=True, db_index=True, verbose_name="رمز الإجازة")
    nacionalidad = models.CharField(max_length=50, verbose_name="جنسية")
    nacionalidad_ingles = models.CharField(max_length=50, verbose_name="Nationality", blank=True, null=True)
    centro_servicio = models.CharField(max_length=100, verbose_name="مركز الخدمة")
    centro_servicio_ingles = models.CharField(max_length=100, verbose_name="Service Center", blank=True, null=True)
    nombre_medico = models.CharField(max_length=100, verbose_name="اسم الطبيب")
    nombre_medico_ingles = models.CharField(max_length=100, verbose_name="Doctor Name", blank=True, null=True)
    titulo_trabajo = models.CharField(max_length=100, verbose_name="مسمى وظيفي")
    titulo_trabajo_ingles = models.CharField(max_length=100, verbose_name="Job Title", blank=True, null=True)
    fecha_inicio = models.DateField(verbose_name="تاريخ البدء")
    fecha_salida = models.DateField(verbose_name="تاريخ الانتهاء")
    fecha_inicio_lunar = models.DateField(verbose_name="تاريخ البدء القمري", blank=True, null=True)
    fecha_salida_lunar = models.DateField(verbose_name="تاريخ الانتهاء القمري", blank=True, null=True)
    fecha_creacion = models.DateTimeField(verbose_name="تاريخ الإنشاء")
    duracion = models.IntegerField(blank=True, null=True, verbose_name="مدة")

    class Meta:
        verbose_name = 'شهادة'
        verbose_name_plural = 'الشهادات'

    def generate_code(self):
        today = self.fecha_inicio
        year = str(today.year)[-2:]
        month = str(today.month).zfill(2)
        day = str(today.day).zfill(2)
        random_digits = ''.join([str(random.randint(0, 9)) for _ in range(5)])
        prefix = "PSL" if self.centro_medico.privado else "GSL"
        return f"{prefix}{year}{month}{day}{random_digits}"

    def clean(self):
        if self.fecha_inicio is None or self.fecha_salida is None:
            raise ValidationError("يجب إدخال تاريخ البدء وتاريخ الانتهاء")
        if self.fecha_creacion is None or self.fecha_creacion.date() < self.fecha_inicio:
            raise ValidationError("تاريخ الإنشاء غير صحيح، يجب أن يكون تاريخ الإنشاء مساويًا أو أكبر من تاريخ البدء")
        if self.fecha_salida < self.fecha_inicio:
            raise ValidationError("يجب أن يكون تاريخ الانتهاء بعد أو يساوي تاريخ البدء")
    
    def save(self, *args, **kwargs):
        if not self.codigo:
            while True:
                new_code = self.generate_code()
                if not Certificado.objects.filter(codigo=new_code).exists():
                    self.codigo = new_code
                    break
        
        # Calculate duration if not provided
        if self.fecha_inicio and self.fecha_salida:
            delta = self.fecha_salida - self.fecha_inicio
            self.duracion = delta.days + 1
        
        # Convert Gregorian dates to Hijri
        if self.fecha_inicio:
            hijri_date = convert.Gregorian(self.fecha_inicio.year, self.fecha_inicio.month, self.fecha_inicio.day).to_hijri()
            self.fecha_inicio_lunar = datetime(hijri_date.year, hijri_date.month, hijri_date.day).date()
            
        if self.fecha_salida:
            hijri_date = convert.Gregorian(self.fecha_salida.year, self.fecha_salida.month, self.fecha_salida.day).to_hijri()
            self.fecha_salida_lunar = datetime(hijri_date.year, hijri_date.month, hijri_date.day).date()
        
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"شهادة {self.codigo} - {self.nombre_paciente}"