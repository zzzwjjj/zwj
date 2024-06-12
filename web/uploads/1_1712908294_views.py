import ast
import heapq

from django.http import HttpResponse
from graphviz import Digraph,Source
from django.shortcuts import render

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



def W(i,j,matrix,matrix_W):
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
    if max((chui+rui),(chuj+ruj)) == 0:
        matrix_W[i][j]=-1
    else:
        B = round((len(union_set)+1)/max((chui+rui),(chuj+ruj)), 4)
        matrix_W[i][j]=B

def B(matrix_W):
    length=len(matrix_W)
    beta=[0]*length
    for row in range(length):
        for i in matrix_W:
            beta[row]+=i[row]
    return beta

def qiang(matrix,length):
    qiang=[0]*length
    for i in range(length):
        for a in matrix:
            qiang[i] += a[i]
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
    # 初始化最大值和最小值为None，以便在数组中找到第一个非负数时进行赋值
    length=len(qiang)
    max = None
    min = None
    # 遍历数组中的每个元素
    for num in qiang:
        # 仅考虑非负数
        if num >= 0:
            # 如果最大值或最小值为None，或者当前元素大于最大值，更新最大值
            if max is None or num > max:
                max = num
            # 如果最小值或最大值为None，或者当前元素小于最小值，更新最小值
            if min is None or num < min:
                min = num
    new_qiang=[-1]*length
    for i in range(length):
        if qiang[i]!= -1:
            new_qiang[i]=(qiang[i]-min)/(max - min)
    max=None
    min=None
    for num in rong:
        # 仅考虑非负数
        if num >= 0:
            # 如果最大值或最小值为None，或者当前元素大于最大值，更新最大值
            if max is None or num > max:
                max = num
            # 如果最小值或最大值为None，或者当前元素小于最小值，更新最小值
            if min is None or num < min:
                min = num
    new_rong = [-1] * length
    for i in range(length):
        if rong[i] != -1:
            new_rong[i] = (rong[i]-min) / (max - min)
    P=[[-1] * length for _ in range(length)]
    for i in range(length):
        for j in range(length):
            if new_qiang[i]==-1 or new_rong[j]==-1:   # i故障强度或者j容错能力为-1，则概率为0
                P[i][j]=0
            else:
                if new_qiang[i]>=new_rong[j]:
                    P[i][j]=matrix_W[i][j]
                elif new_qiang[i]<new_rong[j]:
                    P[i][j]=round(new_qiang[i]/new_rong[j]*matrix_W[i][j],4)
    print(new_rong)
    print(new_qiang)
    return P


def suanfa(name,data_dict,matrix,P,beta,matrix_w):
    # name是用户传入的函数名集合，data_dict是函数名对应的字典，matrix关联关系矩阵，P概率矩阵,beta传播因子
    # 关联矩阵平均度数K
    K = 0
    for a in matrix_w:
        print(a)
    for aa in matrix:
        for a in aa:
            K+=a
    # print(K)
    # print(data_dict)
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
    # if cita_C>0:
    #     cita_C=1/cita_C
    # 计算矩阵的特征值和特征向量
    # eigenvalues, eigenvectors = np.linalg.eig(matrix_w)
    #
    # # 找到最大特征值的索引
    # max_eigenvalue_index = np.argmax(eigenvalues)
    #
    # # 获取最大特征值
    # max_eigenvalue = eigenvalues[max_eigenvalue_index]
    #
    # # 计算最大特征值的倒数
    # cita_C = 1 / max_eigenvalue
    # print("cita_C")
    # print(cita_C)
    #依据name和data_dict找到所有的函数序号作为初始M
    M = [data_dict[n] for n in name if n in data_dict]
    # print(M)
    #计算初始cita_K
    cita_K =0
    for a in M:
        cita_K+=beta[a]
    if len(M)>0:
        cita_K=cita_K/len(M)
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
        # print(m)
        m=list(set(m))
        M = m
        for a in M:
            cita_K += beta[a]
        # print(M)

        cita_K = cita_K / len(M)

    return m

def analyze_code(req):
    if req.method == 'POST':
        res = req.POST
        title = res.get('title')
        code = res.get('code')
        name1=res.get('message')
        name2=res.get('message2')
        graph,nodes_dict, matrix, C = create_call_graph(code)
        length=len(matrix)
        matrix_W = [[0] * length for _ in range(length)]
        for i in range(length):
            for j in range(length):
                W(i, j, matrix, matrix_W)
        beta=B(matrix_W)
        a=qiang(matrix,length)#a,b分别为故障强度和容错能力数组
        b=rong(C,beta)
        PP=P(a,b,matrix_W)
        function_names=[]
        function_names.append(name1)
        # function_names.append(name2)
        # error_message = res.get('message')
        # function_names = extract_function_names_from_traceback(error_message)
        M=suanfa(function_names,nodes_dict,matrix,PP,beta,matrix_W)
        print(M)
        graph.save('call_graph.dot')
        graph.render('call_graph', format='png', cleanup=True, view=False)
        # return render(req, 'result.html')
        return HttpResponse("分析完毕")
    else:
        return render(req, 'analyze_code.html')

