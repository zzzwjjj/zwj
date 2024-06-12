import ast

import numpy as np
from graphviz import Digraph
import heapq
import networkx as nx
import json
from pathlib import Path
from django.conf import settings
from django.http.response import JsonResponse
from rest_framework.views import APIView
from api.models.upload_models import UploadFile


def convert_to_vis_format(graph):
    # 将 NetworkX 图转换为适用于 vis-network 的格式
    nodes = [{'id': node, 'label': data['label']} for node, data in graph.nodes(data=True)]
    edges = [{'from': u, 'to': v} for u, v in graph.edges()]
    return {'nodes': nodes, 'edges': edges}


def extract_function_calls(source_code):
    tree = ast.parse(source_code)
    function_calls = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            function_name = node.name
            function_calls.append({'function_name': function_name, 'calls': []})

            for call_node in ast.walk(node):
                if isinstance(call_node, ast.Call):
                    if hasattr(call_node.func, 'id'):
                        called_function = call_node.func.id

                        # 排除对print函数的判断
                        if called_function.lower() != 'print':
                            function_calls[-1]['calls'].append(called_function)

    return function_calls


def create_call_graph(source_code):
    function_calls = extract_function_calls(source_code)
    nodes_dict = {function_call['function_name']: i for i, function_call in enumerate(function_calls)}
    num_nodes = len(nodes_dict)
    matrix = [[0] * num_nodes for _ in range(num_nodes)]
    dis_matrix = [[0] * num_nodes for _ in range(num_nodes)]
    dot = Digraph(comment='Function Calls')
    call_relations = set()
    for function_call in function_calls:
        for called_function in function_call['calls']:
            # Ensure function names are in nodes_dict
            if called_function not in nodes_dict and called_function.isidentifier():
                # If not, add them to nodes_dict
                nodes_dict[called_function] = len(nodes_dict)
                num_nodes = len(nodes_dict)
                # Add new row and column to the matrix
                for row in matrix:
                    row.append(0)
                matrix.append([0] * num_nodes)
                for row in dis_matrix:
                    row.append(0)
                dis_matrix.append([0] * num_nodes)
    for function_call in function_calls:
        dot.node(function_call['function_name'])
        for called_function in function_call['calls']:
            dot.node(called_function)
            # 添加普通箭头，确保调用关系只用一个箭头
            relation = (function_call['function_name'], called_function)
            if relation not in call_relations:
                dot.edge(relation[0], relation[1])
                index_0 = nodes_dict.get(relation[0], None)
                index_1 = nodes_dict.get(relation[1], None)
                matrix[index_0][index_1] += 1
                dis_matrix[index_0][index_1] = 1
                dis_matrix[index_1][index_0] = 1
                call_relations.add(relation)
    added_relations = set()
    for function_call in function_calls:
        for i in range(len(function_call['calls'])):
            for j in range(i + 1, len(function_call['calls'])):
                function1, function2 = function_call['calls'][i], function_call['calls'][j]
                # 如果关系尚未添加过，就添加红色双向箭头
                if function1 != function2:
                    relation = tuple(sorted([function1, function2]))
                    if relation not in added_relations:
                        dot.edge(relation[0], relation[1], color='red', dir='both')
                        index_0 = nodes_dict.get(relation[0], None)
                        index_1 = nodes_dict.get(relation[1], None)
                        matrix[index_0][index_1] += 1
                        matrix[index_1][index_0] += 1
                        dis_matrix[index_0][index_1] = 1
                        dis_matrix[index_1][index_0] = 1
                        added_relations.add(relation)
    for i in range(len(function_calls)):
        for j in range(i + 1, len(function_calls)):
            common_calls = set(function_calls[i]['calls']) & set(function_calls[j]['calls'])
            if common_calls:
                function_name1 = function_calls[i]['function_name']
                function_name2 = function_calls[j]['function_name']
                # 在图中使用双向紫色箭头连接具有相同调用的函数对
                index_0 = nodes_dict.get(function_name1, None)
                index_1 = nodes_dict.get(function_name2, None)
                matrix[index_0][index_1] += 1
                matrix[index_1][index_0] += 1
                dis_matrix[index_0][index_1] = 1
                dis_matrix[index_1][index_0] = 1
                dot.edge(function_name1, function_name2, color='purple', dir='both')
    # print(dis_matrix)
    for k in range(len(dis_matrix)):
        for i in range(len(dis_matrix)):
            for j in range(len(dis_matrix)):
                if i==j or i==k or j==k:
                    continue
                if dis_matrix[i][k]!=0 and dis_matrix[k][j]!=0:
                    if dis_matrix[i][j]==0:
                        dis_matrix[i][j]=dis_matrix[i][k]+dis_matrix[k][j]
                    elif dis_matrix[i][j]>dis_matrix[i][k]+dis_matrix[k][j]:
                        dis_matrix[i][j]=dis_matrix[i][k]+dis_matrix[k][j]
    C=[]
    for i in range(len(dis_matrix)):
        num = 0
        for j in range(len(dis_matrix)):
            num += int(dis_matrix[i][j])

        if num == 0:
            C.append(-1)
        else:
            C.append((len(dis_matrix)-1)/num)
    # print("亲近中心性")
    # print(C)
    return dot,nodes_dict,matrix,C


def W(i,j,matrix,matrix_W,matrix_b):
    chui = 0   # 出度
    chuj = 0
    rui = 0    # 入度
    ruj = 0
    seti = set()
    setj = set()
    for a in matrix:
        rui += a[i]
        ruj += a[j]
    for a in matrix[i]:
        chui+=a
    for a in matrix[j]:
        chuj+=a
    row=0
    for a in matrix:
        if a[i] != 0:
            seti.add(row)
            row2=0

            for b in matrix:
                if b[row] != 0:
                    seti.add(row2)
                row2+=1
        row+=1
    row=0
    for a in matrix:
        if a[j] != 0:
            setj.add(row)
            row2=0
            for b in matrix:
                if b[row] != 0:
                    setj.add(row2)
                row2+=1
        row+=1
    union_set = seti.union(setj)
    if matrix_b[i][j] == 0:
        matrix_W[i][j] = -1
    else:
        B = round((len(union_set)+1)/max((chui+rui),(chuj+ruj)), 4)
        matrix_W[i][j] = B
    # if(i==24 and j==24):
    #     print(55555555555555555)
    #     print(len(union_set)+1)
    #     print(max((chui+rui),(chuj+ruj)))
    #     print(chui+rui)
    #     print(55555555555555555)


def B(matrix_W,matrix):
    length=len(matrix_W)
    beta=[0]*length
    for row in range(length):
        for j in range(length):
            if matrix[row][j]==1:
                beta[row] += matrix_W[row][j]
    # print("betabetabetabetabetabetabetabeta")
    # print(beta)
    return beta


def qiang(matrix,length):
    qiang=[0]*length
    for i in range(length):
        for a in matrix:
            qiang[i] += a[i]#对一个节点的入度表示故障强度，意思调用该函数的越多，该函数发生故障引起故障的影响就越大
        if qiang[i] == 0:
            qiang[i]=-1
    return qiang


def rong(C,beta):
    length=len(C)
    rong=[0]*length
    for i in range(length):
        if C[i] != -1:
            rong[i]=C[i]*beta[i]
        else:
            rong[i]=-1
    return rong


def P(qiang,rong,matrix_W):
    length=len(matrix_W)
    P = [[0] * length for _ in range(length)]
    for i in range(length):
        for j in range(length):
            if matrix_W[i][j] != -1:
                if qiang[i] >= rong[j] :
                    P[i][j] = matrix_W[i][j]
                else :
                    P[i][j] = float(matrix_W[i][j])*float(qiang[i])/float(rong[i])
            else :
                P[i][j] = 0

    # print(new_qiang)
    # print(new_rong)
    # print("P")
    # for a in P:
    #     print(a)
    return P


def floyd_warshall(adj_matrix):
    n = len(adj_matrix)
    inf = float('inf')

    # 初始化距离矩阵
    dist = [[inf] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                dist[i][j] = 0
            elif adj_matrix[i][j] != 0:
                dist[i][j] = adj_matrix[i][j]

    # Floyd-Warshall 算法
    for k in range(n):
        for i in range(n):
            for j in range(n):
                dist[i][j] = min(dist[i][j], dist[i][k] + dist[k][j])

    return dist


def create_adjacency_matrix(a):
    n = len(a)
    b = [[0] * n for _ in range(n)]  # 创建一个全零的 n × n 空矩阵

    # 使用 Floyd-Warshall 算法计算最短路径
    shortest_paths = floyd_warshall(a)

    # 根据最短路径填充新矩阵
    for i in range(n):
        for j in range(n):
            if shortest_paths[i][j] != float('inf'):  # 如果节点 i 到节点 j 有路径可走
                b[i][j] = 1  # 则将 b[i][j] 记为 1
            if i == j:
                b[i][j] = 0

    return b


def suanfa(name,data_dict,matrix,P,beta,matrix_w):
    # name是用户传入的函数名集合，data_dict是函数名对应的字典，matrix关联关系矩阵，P概率矩阵,beta传播因子
    # 关联矩阵平均度数K
    K = 0
    # print('matrix_W')
    # for a in matrix_w:
    #     print(a)
    for aa in matrix:
        for a in aa:
            K+=a
    # print(K)
    K = K/len(matrix)
    # print("hhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh")
    #根据matrix_b计算cita_C
    cita_C = 0
    cita= 0
    for aa in matrix_w:
         for a in aa:
             if a>0:
                 cita_C+=a
                 cita+=1
    cita_C = cita_C/cita
    if cita_C>0:
        cita_C=1/cita_C
    #计算矩阵的特征值和特征向量
    eigenvalues, eigenvectors = np.linalg.eig(matrix_w)

    # 找到最大特征值的索引
    max_eigenvalue_index = np.argmax(eigenvalues)

    # 获取最大特征值
    max_eigenvalue = eigenvalues[max_eigenvalue_index]

    # 计算最大特征值的倒数
    cita_C = 1 / max_eigenvalue
    # print(cita_C)
    #依据name和data_dict找到所有的函数序号作为初始M
    M = [data_dict[n] for n in name if n in data_dict]
    # print(M)
    #计算初始cita_K
    # cita_K =0
    # for a in M:
    #     cita_K+=beta[a]
    # if len(M)>0:
    #     cita_K=cita_K/len(M)
    for i in range(1):
        my_dict = {}
        m = []
        ans=0
        for a in M:
            row = 0
            for i in range(len(matrix)):
                if matrix[a][i] > 0:
                    if i in my_dict:
                        # 如果键已存在，比较值的大小并保留较大的值
                        if P[a][i] > my_dict[i]:
                            my_dict[i] = P[a][i]
                    else:
                        # 如果键不存在，直接添加键值对
                        my_dict[i] = P[a][i]
                    row += 1
            if row == 0:
                m.append(a)
                ans+=1
        if len(my_dict) <= K-ans:
            # 如果字典数量小于等于 k，则直接返回所有键
            m=list(my_dict.keys())
        else:    # 使用堆来获取前 k 个最大值对应的键
            heap = [(-value, key) for key, value in my_dict.items()]
            heapq.heapify(heap)
            for _ in range(int(K-ans)):
                if heap:
                    key = heapq.heappop(heap)[1]
                    m.append(key)

        m=list(set(m))
        M = m
        # for a in M:
        #     cita_K += beta[a]
        # cita_K = cita_K / len(M)

    return m


def code_locate(file_name):
    file_path = Path(settings.BASE_DIR, 'uploads', file_name)
    if not file_path.exists() or file_path.suffix != '.py':
        return
    with open(file_path, 'r', encoding='utf-8') as fp:
        code = fp.read()

    graph,nodes_dict, matrix, C = create_call_graph(code)
    length=len(matrix)
    matrix_W = [[0] * length for _ in range(length)]
    matrix_b = create_adjacency_matrix(matrix)
    for i in range(length):
        for j in range(length):
            W(i, j, matrix, matrix_W,matrix_b)
    beta=B(matrix_W,matrix)
    a=qiang(matrix,length)#a,b分别为故障强度和容错能力数组
    b=rong(C,beta)
    PP=P(a,b,matrix_W)
    function_names=[]
    # function_names.append(errorfunction)
    print('1111')
    M=suanfa(function_names,nodes_dict,matrix,PP,beta,matrix_W)
    result_set = {key for key, value in nodes_dict.items() if value in M}  # value 转 key
    G = nx.DiGraph()
    for key in nodes_dict.keys():
        function_name = []
        function_name.append(key)
        A = suanfa(function_name, nodes_dict, matrix, PP, beta, matrix_W)

        result_seta = {key for key, value in nodes_dict.items() if value in A}
        if key not in G.nodes:
            G.add_node(key, label=key)
        for function_name in result_seta:
            if function_name != key:  # Avoid self-loops
                if function_name not in G.nodes:
                    G.add_node(function_name, label=function_name)
                if (key, function_name) not in G.edges and (function_name, key) not in G.edges:
                    G.add_edge(key, function_name)
                elif (function_name, key) in G.edges:  # Convert existing edge to bidirectional
                    G.add_edge(key, function_name, direction='forward')  # 添加一个有向边
                    G.add_edge(function_name, key, direction='backward')  # 添加另一个有向边，表示双向关系
    # graph.save('call_graph.dot')
    # graph.render('call_graph', format='png', cleanup=True, view=False)

    data = convert_to_vis_format(G)
    function_call_graph=simply_edge(data)
    # function_call_graph = data
    print(function_call_graph)
    return function_call_graph

def simply_edge(data):
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
    new_edges = [{"from": from_key, "to": to_value} for from_key, to_list in from_to_dict.items() for to_value in
                 to_list]
    # 更新原始数据的edges字段
    data["edges"] = new_edges
    return data

class FaultPropView(APIView):
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
        file_name = request.data.get('file')
        # self.resp_dict = select_data_op
        if not file_name:
            self.resp_dict['status_code'] = 40000
            self.resp_dict['msg'] = '缺少file参数'
            return JsonResponse(self.resp_dict)
        # 创建上传记录

        self.resp_dict['data'] = code_locate(file_name)
        return JsonResponse(self.resp_dict)
