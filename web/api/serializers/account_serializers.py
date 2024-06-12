from rest_framework import serializers
from django.conf import settings
from django.contrib.auth.models import User


class AccountReadOnlySerializer(serializers.ModelSerializer):
    date_joined = serializers.DateTimeField(format=settings.DATETIME_FORMAT)
    last_login = serializers.DateTimeField(format=settings.DATETIME_FORMAT)

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'is_superuser', 'date_joined', 'last_login']
        extra_kwargs = {field: {'read_only': True} for field in fields}


class AccountUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = '__all__'
