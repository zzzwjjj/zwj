from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin, UpdateModelMixin
from rest_framework.decorators import action
from utils.permissions import IsSuperAdminUser
from rest_framework.response import Response
from api.serializers.account_serializers import AccountReadOnlySerializer
from utils.pagination import CustomPageNumberPagination
from django.contrib.auth.models import User
from django.db.models import Q
from api.models import opcations_models


class UserInfoView(APIView):
    """
    Args:
        获取请求的用户的，根据jwt返回信息
    Returns:
        _type_: _description_
    """
    def __init__(self):
        self.resp_dict = {
            'status_code':20000,
            'msg':None,
            'data':None,
        }
    def post(self,request,*args,**kwargs):
        user_obj = request.user
        try:
            self.resp_dict['msg'] = '鉴权成功'
            self.resp_dict['data'] = {
                'username':request.user.username,
                'nickname':request.user.first_name,
                'user_id':request.user.id,
                'is_superuser': request.user.is_superuser
            }
            # opcations_models.OptionLog.objects.create(
            #     op_user=user_obj,
            #     op_name='登录',
            #     ext={'file_name': ''}
            # )
        except:
            self.resp_dict['status_code'] = 50001
            self.resp_dict['msg'] = '身份识别信息出错,请重新登陆'
        
        return Response(self.resp_dict)


class RegisterView(APIView):
    permission_classes = []
    """
    注册接口
    Args:
        APIView (_type_): _description_
    """
    def __init__(self):
        self.resp_dict = {
            'status_code':20000,
            'msg':None,
            'data':None,
        }
    def post(self,request,*args,**kwargs):
        register_dict = request.data
        register_dict.pop('re_password')
        username_exists = User.objects.filter(username=request.data.get('username')).count()
        if username_exists:
            self.resp_dict['status_code'] = 50001
            self.resp_dict['msg'] = '账号已存在'
        else:
            user_obj = User.objects.create_user(
                username=register_dict.get('username'),
                password = register_dict.get('password'),
                first_name=register_dict.get('nickname')
            )
            self.resp_dict['msg'] = '注册成功'
            self.resp_dict['data'] = user_obj.id
        
        return Response(self.resp_dict)


class UserViewSet(GenericViewSet, ListModelMixin, UpdateModelMixin):
    queryset = User.objects.all()
    serializer_class =  AccountReadOnlySerializer
    pagination_class = CustomPageNumberPagination

    def get_permissions(self):
        permissions = super().get_permissions()
        permissions.append(IsSuperAdminUser())
        return permissions

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == 'list':
            name = self.request.query_params.get('name', '')
            start_date = self.request.query_params.get('start_date', '')
            end_date = self.request.query_params.get('end_date', '')
            queryset = queryset.filter(
                Q(username__icontains=name) | Q(first_name__icontains=name)
            )
            if start_date:
                queryset = queryset.filter(date_joined__date__gte=start_date)
            if end_date:
                queryset = queryset.filter(date_joined__date__lt=end_date)
        return queryset

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        resp_dict = {
            'status_code': 20000,
            'msg': None,
            'data': None,
        }
        first_name = request.data.get('first_name', None)
        username = request.data.get('username', None)
        is_superuser = request.data.get('is_superuser', None)
        password = request.data.get('password', None)
        if not first_name or not username or not isinstance(is_superuser, bool):
            resp_dict['status_code'] = 40000
            resp_dict['msg'] = '缺少参数'
            return Response(resp_dict)
        if User.objects.exclude(id=instance.id).filter(username=username).exists():
            resp_dict['status_code'] = 40000
            resp_dict['msg'] = f'用户名{username}已存在'
            return Response(resp_dict)
        instance.first_name = first_name
        instance.username = username
        if password:
            instance.set_password(password)
        instance.save()
        print(password)
        print(request.data)
        return Response(resp_dict)


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
        if ids:
            queryset = self.get_queryset()
            queryset.filter(id__in=ids).delete()
        resp_dict = {
            'status_code': 20000,
            'msg': None,
            'data': None,
        }
        return Response(resp_dict)


class UserUpgradeViewSet(GenericViewSet):
    queryset = User.objects.all()

    @action(methods=['PUT'], detail=True)
    def upgrade(self, request, *args, **kwargs):
        resp_dict = {
            'status_code': 20000,
            'msg': None,
            'data': None
        }
        instance = self.get_object()
        # instance.is_superuser = 1
        if instance.id != self.request.user.id:
            resp_dict['status_code'] = 40000
            resp_dict['msg'] = '只能修改自己的信息'
            return Response(resp_dict)

        username = request.data.get('username')
        firstname = request.data.get('nickname')
        # password = request.data.get('password')

        if not all([username, firstname]):
            resp_dict['status_code'] = 40000
            resp_dict['msg'] = '缺失请求参数'
            return Response(resp_dict)
        queryset = self.get_queryset()
        if queryset.filter(username=username).exclude(id=instance.id).exists():
            resp_dict['status_code'] = 40000
            resp_dict['msg'] = f'用户名{username}已存在'
            return Response(resp_dict)
        instance.username = username
        instance.first_name = firstname
        # instance.password = password
        # instance.is_superuser = 0
        # if password:
        #     instance.set_password(password)
        instance.save()
        user_obj=request.user
        opcations_models.OptionLog.objects.create(
            op_user=user_obj,
            op_name='修改个人资料',
            ext={'file_name': ''}
        )
        return Response(resp_dict)
class UserpasswordViewSet(GenericViewSet):
    queryset = User.objects.all()

    @action(methods=['PUT'], detail=True)
    def upgrade(self, request, *args, **kwargs):
        resp_dict = {
            'status_code': 20000,
            'msg': "zzzzz",
            'data': None
        }
        instance = self.get_object()
        print(instance.id)
        print(instance.username)
        print(instance.password)
        print(instance.first_name)
        print(type(instance))
        # instance.is_superuser = 1
        if instance.id != self.request.user.id:
            resp_dict['status_code'] = 40000
            resp_dict['msg'] = '只能修改自己的信息'
            return Response(resp_dict)


        password = request.data.get('password')
        print(password)
        if password:
             instance.set_password(password)
        instance.save()
        user_obj=request.user
        opcations_models.OptionLog.objects.create(
            op_user=user_obj,
            op_name='修改密码',
            ext={'file_name': ''}
        )
        return Response(resp_dict)