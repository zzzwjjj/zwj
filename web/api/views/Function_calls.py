import ast
import json
import os
import networkx as nx
from pathlib import Path
from django.conf import settings
from django.http.response import JsonResponse
from rest_framework.views import APIView
from api.models.upload_models import UploadFile

def read_python_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        code_content = file.read()
    return code_content

def convert_to_vis_format(graph):
    # 将 NetworkX 图转换为适用于 vis-network 的格式
    nodes = [{'id': node, 'label': data['label']} for node, data in graph.nodes(data=True)]
    edges = [{'from': u, 'to': v} for u, v in graph.edges()]
    return {'nodes': nodes, 'edges': edges}


def analyze_code_diaoyong(code_text):
    tree = ast.parse(code_text)
    G = nx.DiGraph()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            function_name = node.name
            if function_name != 'print':
                G.add_node(function_name, label=function_name)
                for child_node in ast.walk(node):
                    if isinstance(child_node, ast.Call):
                        if isinstance(child_node.func, ast.Name):
                            called_function_name = child_node.func.id
                            if called_function_name != function_name and called_function_name != 'print':
                                G.add_node(called_function_name, label=called_function_name)
                                G.add_edge(function_name, called_function_name)
    return G

def analyze_python_files_in_folder(folder_path):
    call_graphs = {}
    for file_name in os.listdir(folder_path):
        if file_name.endswith(".py"):
            file_path = os.path.join(folder_path, file_name)
            code = read_python_file(file_path)
            function_call_graph = analyze_code_diaoyong(code)
            function_call_graph_json = json.dumps(convert_to_vis_format(function_call_graph))
            call_graphs[file_name] = function_call_graph_json

    return call_graphs


def analyze_python_file(file_name):
    # call_graphs = {}
    file_path = Path(settings.BASE_DIR, 'uploads', file_name)
    if not file_path.exists() or file_path.suffix != '.py':
        return
    code = read_python_file(file_path)
    return convert_to_vis_format(analyze_code_diaoyong(code))
    # for file_name in os.listdir(folder_path):
    #     if file_name.endswith(".py"):
    #         file_path = os.path.join(folder_path, file_name)
    #         code = read_python_file(file_path)
    #         function_call_graph = analyze_code_diaoyong(code)
    #         function_call_graph_json = json.dumps(convert_to_vis_format(function_call_graph))
    #         call_graphs[file_name] = function_call_graph_json

    # return call_graphs


# # red=analyze_python_files_in_folder('../../uploads')
# # print(red)
# # print(type(red))
# # print(type(red['1_1712461534_views.py']))
# # print(red['1_1712461534_views.py'])
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from api.models import upload_models
# from api.models import opcations_models
# import time
# import json
# from utils import Get_features
# from utils import Forecast
# from django.conf import settings
# from utils.analyze import code_locate
class FunctionCallView(APIView):
    def __init__(self):
        self.resp_dict = {
            'status_code': 20000,
            'msg': None,
            'data': None
        }

    def get(self, request, *args, **kwargs):
        # uploads = Path(settings.BASE_DIR, 'uploads')
        search = request.GET.get('file', '')
        data = []
        # for f in uploads.iterdir():
        #     if f.is_file() and f.suffix == '.py':
        #         if search:
        #             if search in f.name:
        #                 data.append({'file': f.name, 'image': f'{request._current_scheme_host}/media/python.png'})
        #         else:
        #             data.append({'file': f.name, 'image': f'{request._current_scheme_host}/media/python.png'})
        queryset = UploadFile.objects.filter(upload_user=request.user)
        if search:
            queryset = queryset.filter(file_name__icontains=search)
        for instance in queryset:
            data.append({'file': instance.file_name, 'image': f'{request._current_scheme_host}/media/python.png'})
        self.resp_dict['data'] = data
        return JsonResponse(self.resp_dict)

    def post(self, request, *args, **kwargs):
        # select_data_op = analyze_python_files_in_folder('../../uploads')
        file_name = request.data.get('file')
        # self.resp_dict = select_data_op
        if not file_name:
            self.resp_dict['status_code'] = 40000
            self.resp_dict['msg'] = '缺少file参数'
            return JsonResponse(self.resp_dict)
        # 创建上传记录
        self.resp_dict['data'] = analyze_python_file(file_name)
        return JsonResponse(self.resp_dict)