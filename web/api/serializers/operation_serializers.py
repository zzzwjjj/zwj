from rest_framework import serializers
from django.conf import settings
from api.models.opcations_models import OptionLog


class OperationReadOnlySerializer(serializers.ModelSerializer):
    op_user = serializers.CharField(source='op_user.first_name')
    create_time = serializers.DateTimeField(format=settings.DATETIME_FORMAT)
    update_time = serializers.DateTimeField(format=settings.DATETIME_FORMAT)

    class Meta:
        model = OptionLog
        fields = '__all__'
