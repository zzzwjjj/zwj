from rest_framework.views import APIView
from rest_framework.response import Response
from api.models import opcations_models
from utils.analyze import code_locate
import json
from api.models import upload_models
from datetime import datetime, time


class FaultLocationView(APIView):
    def __init__(self) :
        
        self.resp_dict = {
            'status_code':20000,
            'msg':None,
            'data':None
        }

    def post(self,request,*args,**kwargs):

        code_file_name = request.data.get('upload_file')
        func_name = request.data.get('func_name')

        code = None
        with open(f'./uploads/{code_file_name}','r',encoding="UTF-8") as f:
            code = f.read()
        
        result,result_set = code_locate(code=code,errorfunction=func_name)
        if len(result_set) == 0:
            self.resp_dict['status_code'] = 50002
            self.resp_dict['msg'] = '您所上传的文件有误或无故障关联关系,无法进行定位'
            upload_models.UploadFile.objects.filter(file_name=code_file_name).delete()
            return Response(self.resp_dict)
        else:
            self.resp_dict["result_set"] = result_set
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
            # 创建上传记录
            # opcations_models.OptionLog.objects.create(
            #     op_user=request.user,
            #     op_name=f'故障定位 - 提交分析 - {code_file_name}',
            #     ext=result
            # )
            self.resp_dict['data'] = result
            # timestamp_ms1 = int(time.time() * 1000)
            # print()
            return Response(self.resp_dict)