from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin
from rest_framework.decorators import action
from rest_framework.response import Response
from api.serializers.operation_serializers import OperationReadOnlySerializer
from utils.pagination import CustomPageNumberPagination
from api.models.opcations_models import OptionLog


class OperationViewSet(GenericViewSet, ListModelMixin):
    queryset = OptionLog.objects.all()
    serializer_class = OperationReadOnlySerializer
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(op_user=self.request.user)
        if self.action == 'list':
            start_date = self.request.query_params.get('start_date', '')
            end_date = self.request.query_params.get('end_date', '')
            file = self.request.query_params.get('file', '')
            filter_kwargs = {'ext__file_name__icontains': file}
            if start_date:
                filter_kwargs['create_time__date__gte'] = start_date
            if end_date:
                filter_kwargs['create_time__date__lt'] = end_date
            queryset = queryset.filter(**filter_kwargs)
        return queryset

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)

        i = len(response.data['results']) - 1
        while i >= 0:
            if response.data['results'][i]['ext']['file_name'] == '' or response.data['results'][i][
                'op_name'] == '故障定位-传播分析':
                del response.data['results'][i]
            i -= 1
            # print(response.data['results'])
        response.data['count'] = len(response.data['results'])
        print(response.data)
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
        queryset.filter(id__in=ids).delete()
        resp_dict = {
            'status_code': 20000,
            'msg': None,
            'data': None,
        }
        return Response(resp_dict)
