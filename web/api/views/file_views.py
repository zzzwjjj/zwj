import os

from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin
from rest_framework.decorators import action
from django.db import transaction
from utils.permissions import IsSuperAdminUser
from rest_framework.response import Response
from django.conf import settings
from pathlib import Path
from api.serializers.file_serializers import UploadFileReadOnlySerializer
from utils.pagination import CustomPageNumberPagination
from api.models.upload_models import UploadFile


class FileViewSet(GenericViewSet, ListModelMixin):
    queryset = UploadFile.objects.all()
    serializer_class = UploadFileReadOnlySerializer
    pagination_class = CustomPageNumberPagination

    def get_permissions(self):
        permissions = super().get_permissions()
        permissions.append(IsSuperAdminUser())
        return permissions

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == 'list':
            file = self.request.query_params.get('file', '')
            start_date = self.request.query_params.get('start_date', '')
            end_date = self.request.query_params.get('end_date', '')
            filter_kwargs = {'file_name__icontains': file}
            if start_date:
                filter_kwargs['create_time__date__gte'] = start_date
            if end_date:
                filter_kwargs['create_time__date__lt'] = end_date
            queryset = queryset.filter(**filter_kwargs)
        return queryset

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        resp_dict = {
            'status_code': 20000,
            'msg': None,
            'data': response.data,
        }
        response.data = resp_dict
        return response

    @action(methods=['PUT'], detail=False)
    def delete(self, request, *args, **kwargs):
        ids = request.data.get('ids', [])
        queryset = self.get_queryset()
        queryset = queryset.filter(id__in=ids)
        for instance in queryset:
            file_path = Path(settings.BASE_DIR, 'uploads', instance.file_name)
            if file_path.exists():
                os.remove(file_path)
        queryset.delete()

        resp_dict = {
            'status_code': 20000,
            'msg': None,
            'data': None,
        }
        return Response(resp_dict)
