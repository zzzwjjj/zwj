from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth.models import User
from api.models import opcations_models





class Count_view(APIView):
    def __init__(self):
        self.resp_dict = {
            'status_code': 20000,
            'msg': None,
            'data': None,
        }

    def post(self, request, *args, **kwargs):
        user_obj=request.user
        file_name = request.data.get('file_name')
        error=request.data.get('error')
        func_name=request.data.get('func_name')
        result=request.data.get('result_set')
        func_graph=request.data.get('func_graph')
        print(user_obj.username)
        ext_json={
            "file_name":file_name,
            "error":error,
            "func_name":func_name,
            "result":result,
            "username": user_obj.username,
            "func_graph":func_graph,

        }
        op_obj=opcations_models.OptionLog.objects.create(
            op_user=user_obj,
            op_name='故障预测-提交分析',
            ext=ext_json
        )
        self.resp_dict['msg']=op_obj.id
        return Response(self.resp_dict)
    