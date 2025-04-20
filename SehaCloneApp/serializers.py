from rest_framework import serializers
from .models import CentroMedico, Certificado
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password

class CentroMedicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CentroMedico
        fields = '__all__'

class CertificadoSerializer(serializers.ModelSerializer):
    centro_medico = CentroMedicoSerializer(read_only=True)
    
    class Meta:
        model = Certificado
        fields = '__all__'

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'confirm_password', 'first_name', 'last_name']

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("كلمات المرور غير متطابقة")
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        validated_data['password'] = make_password(validated_data['password'])
        validated_data['is_staff'] = True
        return super().create(validated_data)