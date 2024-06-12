from rest_framework.views import APIView
from rest_framework.response import Response
from api.models import upload_models
from api.models import opcations_models
import time
import json
from utils import Get_features
from utils import Forecast
from django.conf import settings
from utils.analyze import code_locate


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

class PropMapUploadFilesView(APIView):
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
        self.resp_dict['msg'] = '上传成功'
        
        select_name = None
        for item in select_data_op:
            if len(select_data_op[item]['select_list']) >0:
                select_name = select_data_op[item]['select_list'][0]
                break

        code_full = None
        with open(f'{file_path}','r',encoding="UTF-8") as f:
            code_full = f.read()
            
        result,result_set = code_locate(code=code_full,errorfunction=select_name)
        if len(result_set)==0:
            self.resp_dict['status_code'] = 50002
            self.resp_dict['msg'] = '您所上传的文件无故障关联关系'
            return Response(self.resp_dict)
        else:
            self.resp_dict["result_set"]=result_set
            data = json.loads(result)
            from_to_dict = {}
            for edge in data["edges"]:
                from_key = edge["from"]
                to_value = edge["to"]
                if from_key in from_to_dict:
                    # 至多三个的逻辑
                    if len(from_to_dict[from_key]) < 3:
                        from_to_dict[from_key].append(to_value)
                else:
                    from_to_dict[from_key] = [to_value]

            # 根据处理后的数据重新构建edges列表
            new_edges = [{"from": from_key, "to": to_value} for from_key, to_list in from_to_dict.items() for to_value in
                         to_list]
            # 更新原始数据的edges字段
            data["edges"] = new_edges
            # 处理后的result
            result = json.dumps(data, indent=4)

            self.resp_dict['echats'] = result
            # 创建上传记录
            upload_models.UploadFile.objects.create(
                upload_user=request.user,
                name=file_path,
                file_name=file_name,
                ext=select_data_op
            )

            # 创建生成日志
            opcations_models.OptionLog.objects.create(
                op_user=request.user,
                # op_name=f'故障定位 - 传播分析 -{file_name}',
                op_name='故障定位-传播分析',
                ext={"file_name": file_name,"username":request.user.username}
            )


            return Response(self.resp_dict)
        