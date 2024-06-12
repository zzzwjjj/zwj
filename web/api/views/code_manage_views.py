from rest_framework.views import APIView
from rest_framework.response import Response
from api.models import opcations_models
from django.core.paginator import Paginator
from django.db.models import Q
import datetime
import os
from django.conf import settings
import json

from django.db.models.functions import Cast
class CodeManageView(APIView):
    def __init__(self):
        self.base_dir = settings.BASE_DIR
        self.resp_dict = {
            'status_code':20000,
            'msg':None,
            'all_count':None,
            'now_page':None,
            'data':None
        }
    
    def get(self,request,*args,**kwargs):
        # 获取代码管理页面数据
        filter_dict = {}
        user = request.user
        page = request.query_params.get('page',1)
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        file_name = request.query_params.get('file_name')
        if user.is_superuser :
            op_objs  = opcations_models.OptionLog.objects.filter(status=True)
        else:
            op_objs = opcations_models.OptionLog.objects.filter(op_user=user, status=True)
        # op_objs  = opcations_models.OptionLog.objects.all()
        op_objs = op_objs.exclude(ext__file_name='')
        if start_date:
            filter_dict['create_time__gte'] = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            filter_dict['create_time__lte'] = datetime.datetime.strptime(end_date, "%Y-%m-%d")
            for key, value in filter_dict.items():
                field, condition = key.split("__")
                key_name = f'{field}__{condition}'
                # print(key_name)
                op_objs = op_objs.filter(Q(**{key_name: value}))
        if file_name:
            key_name = 'ext__file_name'
            op_objs = op_objs.filter(Q(**{key_name + '__icontains': file_name}))

                
        op_objs=op_objs

        # op_objs = opcations_models.OptionLog.objects.filter(op_user=user,op_name__icontains='故障定位 - 提交分析')
        
        
        target_page_data = Paginator(op_objs,10)
        self.resp_dict['now_page'] = page
        self.resp_dict['all_page'] = target_page_data.num_pages
        self.resp_dict['all_count'] = len(op_objs)
        self.resp_dict['data'] = []
        
        for item in target_page_data.page(page):
            self.resp_dict['data'].append(
                {
                    'sid':item.id,
                    'op_name':item.op_name,
                    'ext':item.ext,
                    'created':item.create_time.strftime("%Y-%m-%d %H:%M")
                }
            )
        

        return Response(self.resp_dict)
    
    def post(self,request,*args,**kwargs):
        sid = request.data.get('sid')
        if not sid:
            self.resp_dict['status_code'] = 50001
            self.resp_dict['msg'] = '参数不对'
        else:
            op_obj = opcations_models.OptionLog.objects.filter(id=sid)
            if not op_obj:
                self.resp_dict['status_code'] = 50002
                self.resp_dict['msg'] = '编号不存在'
            else:
                ext_data = op_obj.first().ext
                if isinstance(ext_data, str):
                    ext_dict = json.loads(ext_data)
                else:
                    ext_dict = ext_data
                file_name = ext_dict.get('file_name')
                file_path = f'{self.base_dir}/uploads/{file_name}'
                print(file_path)
                # 先判断是否存在
                file_exists = os.path.exists(file_path)
                if not file_exists:
                    self.resp_dict['status_code'] = 50003
                    self.resp_dict['msg'] = '文件不存在'
                else:
                    code = None
                    with open(file_path,mode='r',encoding='utf-8') as f:
                        code = f.read()
                    self.resp_dict['data'] = code
        return Response(self.resp_dict)
        
    
    def delete(self,request,*args,**kwargs):

        sid_list = request.data.get('sid_list')

        opcations_models.OptionLog.objects.filter(id__in=sid_list).update(status=False)

        return Response(self.resp_dict)

