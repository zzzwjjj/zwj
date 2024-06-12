from rest_framework import serializers
from django.conf import settings
from api.models.upload_models import UploadFile


class UploadFileReadOnlySerializer(serializers.ModelSerializer):
    upload_user = serializers.CharField(source='upload_user.first_name')
    create_time = serializers.DateTimeField(format=settings.DATETIME_FORMAT)
    update_time = serializers.DateTimeField(format=settings.DATETIME_FORMAT)

    class Meta:
        model = UploadFile
        fields = '__all__'
