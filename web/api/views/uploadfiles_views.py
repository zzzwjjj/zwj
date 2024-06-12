from rest_framework.views import APIView
from rest_framework.response import Response
from api.models import upload_models
import time
from utils import Get_features
from utils import Forecast
from django.conf import settings





def analysis_hook(file_path):
    Get_features.extract_function_features(file_path)
    label_name_dict = Forecast.go()
    # 整理一下分析结果，然后给回前端渲染
    select_data_op = {}
    for item in label_name_dict:
        if item not in select_data_op:
            if label_name_dict.get(item):
                select_data_op[item] = {'is_op':False,'select_list':[]}
                for name in label_name_dict.get(item):
                    if name not in select_data_op[item]['select_list']:
                        select_data_op[item]['select_list'].append(name)
            else:
                select_data_op[item] = {'is_op':True,'select_list':[]}     
    return select_data_op
    

class UploadFilesView(APIView):
    def __init__(self):
        self.base_dir = settings.BASE_DIR
        self.resp_dict = {
            'status_code':20000,
            'msg':None,
            'data':None
        }
    def post(self,request,*args,**kwargs):
        if 'file' not in request.FILES:
            self.resp_dict['status_code'] = 50001
            self.resp_dict['msg'] = '无上传文件'
            return Response(self.resp_dict)
        
        file_obj = request.FILES['file']
        if file_obj.name[-3:] != '.py':
            self.resp_dict['status_code'] = 50002
            self.resp_dict['msg'] = '上传文件格式不符'
            return Response(self.resp_dict)
        
        now_time = str(int(time.time()))
        file_name = f'{request.user.id}_{now_time}_{file_obj.name}'
        file_path = f'{self.base_dir}/uploads/{file_name}'

        file_content = file_obj.chunks()
        with open(file_path,'wb') as w:
            for i in file_content:
                w.write(i)

        # 需要执行代码分析
        select_data_op = analysis_hook(file_path)
        if len(select_data_op) == 0:
            self.resp_dict['status_code'] = 50002
            self.resp_dict['msg'] = '上传文件内部需定义函数，请重新上传'
            return Response(self.resp_dict)
        self.resp_dict['msg'] = '上传成功'
        self.resp_dict['data'] = {'file_name':file_name,'select_data_op':select_data_op}
        
        # 创建上传记录
        upload_models.UploadFile.objects.create(
            upload_user=request.user,
            name=file_path,
            file_name=file_name,
            ext=select_data_op
        )
        
        return Response(self.resp_dict)


