from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.http import JsonResponse
import os

from django.conf import settings
class Delete_view(APIView):
    def __init__(self):
        self.resp_dict = {
            'status_code': 20000,
            'msg': None,
            'data': None,
        }

    def post(self, request, *args, **kwargs):
        user_obj = request.user
        file_name = request.data.get('file_name')
        try:
            for item in file_name:
                file_path = os.path.join(settings.BASE_DIR,'uploads',item)  # 替换为实际的文件路径
                try:
                    os.remove(file_path)
                    print(f"{file_path} 文件删除成功")
                except Exception as e:
                    print(f"删除文件时出现错误：{e}")
                print(file_path)
            return JsonResponse({'message': '文件删除成功'})
        except Exception as e:
            return JsonResponse({'error': '文件删除失败'}, status=500)
        # return Response(self.resp_dict)
