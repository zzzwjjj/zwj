import django
from django.utils import timezone
import pymysql
from django.db import connection
import ast
from django.shortcuts import render, redirect, HttpResponse
import json
import networkx as nx
from django.contrib import messages

import ast
import inspect
from django.conf import settings
import os
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'guzhang.settings')


# Create your views here.
def login_user(req):
    if req.method == "GET":
        # 如果是GET请求
        return render(req, 'login_user.html')
    else:
        # 如果是POST请求
        with connection.cursor() as cursor:

            cursor.execute("select * from app01_user")
            data_list = cursor.fetchall()
            res = req.POST
            name = res.get('user_name')
            pwd = res.get('user_password')
            req.session["info"] = {'account': name, 'password': pwd}
            for a in data_list:
                if name == a[2] and pwd == a[3]:
                    info = req.session.get("info")
                    account = info['account']
                    action = '登录'
                    d1 = timezone.now()
                    d2 = timezone.localtime(d1)
                    time = d2.strftime("%Y-%m-%d %H:%M:%S")
                    OpLog.objects.create(account=account, action=action, time=time)

                    return redirect('/main/')
            return redirect("/login_user/")


def user_register(req):
    try:
        with connection.cursor() as cursor:
            if req.method == "GET":
                return render(req, 'user_register.html')
            else:
                # 如果是POST请求
                res = req.POST
                name = res.get('user_name')
                account = res.get('user_account')
                pwd = res.get('user_password')
                address = res.get('user_address')
                phone = res.get('user_phone')
                req.session['info'] = {'account': account}
                info = req.session.get("info")
                print(info["account"])
                User.objects.create(name=name, account=account, password=pwd)
                # sql = "CALL add_user(%s,%s,%s,%s,%s)"
                # cursor.execute(sql, (name, account, pwd, address, phone))
                return redirect('/login_user/')
    except Exception as e:
        print(f"An exception occurred in change: {str(e)}")
        return HttpResponse("失败")


def main(req):
    info = req.session.get("info")

    return render(req, 'main.html', {'account': info['account']})


def code_manage(req):
    info = req.session.get("info")
    account = info["account"]
    code2 = Code.objects.filter(account=account)
    return render(req, 'code_manage.html', {'n1': code2, 'account': info['account']})


def code_add(req):
    try:
        with connection.cursor() as cursor:
            if req.method == "GET":
                return render(req, 'code_add.html')
            else:
                # 如果是POST请求
                res = req.POST
                title = res.get('title')
                code = res.get('code')
                info = req.session.get("info")
                account = info["account"]
                Code.objects.create(title=title, code=code, account=account)
                info = req.session.get("info")
                account = info['account']
                action = '上传代码'
                d1 = timezone.now()
                d2 = timezone.localtime(d1)
                time = d2.strftime("%Y-%m-%d %H:%M:%S")
                OpLog.objects.create(account=account, action=action, time=time)
                return redirect('/code/manage')
    except Exception as e:
        print(f"An exception occurred in change: {str(e)}")
        return HttpResponse("失败")


def code_update(req, id):
    try:
        with connection.cursor() as cursor:
            if req.method == "GET":
                # 如果是GET请求
                re = Code.objects.get(id=id)
                return render(req, 'code_update.html', {'n1': re, 'n2': id})
            else:
                # 如果是POST请求
                cursor.execute("select * from app01_code")
                res = req.POST
                title = res.get('title')
                code = res.get('code')

                cursor.execute("update app01_code set title=%s,code=%s where id=%s ", (title, code, id))
                info = req.session.get("info")
                account = info['account']
                action = '修改了代码' + str(id) + '的内容'
                d1 = timezone.now()
                d2 = timezone.localtime(d1)
                time = d2.strftime("%Y-%m-%d %H:%M:%S")
                OpLog.objects.create(account=account, action=action, time=time)
                return redirect('/code/manage/')
    except Exception as e:
        print(f"An exception occurred in change: {str(e)}")
        return HttpResponse("失败")


def code_delete(req, id):
    try:
        with connection.cursor() as cursor:
            if req.method == "GET":
                cursor.execute("delete from app01_code where id=%s", [id])
                info = req.session.get("info")
                account = info['account']
                action = '删除了代码' + str(id)
                d1 = timezone.now()
                d2 = timezone.localtime(d1)
                time = d2.strftime("%Y-%m-%d %H:%M:%S")
                OpLog.objects.create(account=account, action=action, time=time)
                return redirect('/code/manage/')
            else:
                return redirect('/code/manage/')
    except Exception as e:
        print(f"An exception occurred in change: {str(e)}")
        return HttpResponse("失败")


def function_dependent(req, id):
    # 从数据库中获取特定代码的详细信息
    # code = get_object_or_404(Code, pk=code_id)
    a = Code.objects.get(id=id)
    # 分析代码，生成函数调用图
    function_call_graph = analyze_code(a.code)

    # 将函数调用图转换为 JSON 格式
    function_call_graph_json = json.dumps(convert_to_vis_format(function_call_graph))

    # 将 JSON 数据传递给模板
    return render(req, 'function_dependent.html',
                  {'code': a.code, 'function_call_graph_json': function_call_graph_json})


def analyze_code(code_text):
    # 使用 ast 模块解析 Python 代码
    tree = ast.parse(code_text)

    # 创建有向图
    G = nx.DiGraph()

    # 遍历 AST 树，提取函数调用关系
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            function_name = node.name

            # 排除特定函数名，如 'print'
            if function_name != 'print':
                # 添加函数节点
                G.add_node(function_name, label=function_name)

                # 提取函数调用关系
                for child_node in ast.walk(node):
                    if isinstance(child_node, ast.Call):
                        if isinstance(child_node.func, ast.Name):
                            called_function_name = child_node.func.id
                            if called_function_name != function_name and called_function_name != 'print':
                                # 添加被调用的函数节点和调用关系
                                G.add_node(called_function_name, label=called_function_name)
                                G.add_edge(function_name, called_function_name)

    return G


def convert_to_vis_format(graph):
    # 将 NetworkX 图转换为适用于 vis-network 的格式
    nodes = [{'id': node, 'label': data['label']} for node, data in graph.nodes(data=True)]
    edges = [{'from': u, 'to': v} for u, v in graph.edges()]
    return {'nodes': nodes, 'edges': edges}


def system(req):
    info = req.session.get("info")
    pwd = info['password']
    return render(req, 'system.html', {'pwd': pwd, 'account': info['account']})


def new_pwd(req):
    if req.method == "POST":
        res = req.POST
        pwd1 = res.get('pwd1')
        pwd2 = res.get('pwd2')
        pwd3 = res.get('pwd3')
        info = req.session.get("info")
        pwd = info['password']
        account = info['account']
        if pwd == pwd1 and pwd2 == pwd3:
            User.objects.filter(account=info['account']).update(password=pwd2)
            req.session['info'] = {'account': account, 'password': pwd2}
            return redirect('/system/')
        else:
            error_message = "密码验证失败!请您检查输入的密码是否正确并确认新密码是否一致!"

            return render(req, 'new_pwd.html', {'error_message': error_message})

    else:
        return render(req, 'new_pwd.html')


def op_log(req):
    info = req.session.get("info")
    account = info['account']
    n = OpLog.objects.filter(account=account)
    n1 = reversed(n)
    return render(req, 'op_log.html', {'n1': n1, 'account': account})


def log_delete(req, id):
    OpLog.objects.get(id=id).delete()
    return redirect('/op_log/')


def look_code(req, id):
    n = Code.objects.get(id=id)
    code = n.code
    print(code)
    info = req.session.get("info")
    return render(req, 'look_code.html', {'code': code, 'account': info['account']})


def self_update(req):
    try:
        with connection.cursor() as cursor:
            info = req.session.get("info")
            account = info["account"]

            if req.method == "GET":
                # 如果是GET请求
                re = User.objects.get(account=account)
                return render(req, 'self_update.html', {'n1': re})
            else:
                # 如果是POST请求
                res = req.POST
                # name = res.get('user_name')
                # account = res.get('user_account')
                # pwd = res.get('user_password')
                gender_choice = res.get("choice")
                # 在这里处理获取到的性别选择
                if gender_choice == "option1":
                    gender = "男"
                elif gender_choice == "option2":
                    gender = "女"
                else:
                    gender = None
                e_mail = res.get('user_e_mail')
                phone = res.get('user_phone')
                info = req.session.get("info")
                account = info['account']
                User.objects.filter(account=account).update(gender=gender, e_mail=e_mail, phone=phone)
                pwd = info['password']
                return render(req, 'system.html', {'pwd': pwd, 'account': info['account']})
    except Exception as e:
        print(f"An exception occurred in change: {str(e)}")
        return HttpResponse("失败")


# import ast

def extract_function_features(func):
    # 解析函数的源代码，生成AST
    source_code = inspect.getsource(func)
    func_ast = ast.parse(source_code)

    # 初始化特征向量
    features = {
        'name': func.__name__,
        'parameters': [],
        'returns': None,
        'assignments': 0,
        'loops': 0,
        'if_statements': 0,
        'function_calls': 0,
        'exception_handling': 0,
        # 其他你感兴趣的特征
    }

    # 遍历AST节点
    for node in ast.walk(func_ast):
        if isinstance(node, ast.arguments):
            # 提取函数的参数名
            features['parameters'] = [arg.arg for arg in node.args]
        elif isinstance(node, ast.Return):
            # 提取函数的返回值
            features['returns'] = ast.dump(node.value)
        elif isinstance(node, ast.Assign):
            # 统计赋值语句的数量
            features['assignments'] += 1
        elif isinstance(node, ast.For) or isinstance(node, ast.While):
            # 统计循环语句的数量
            features['loops'] += 1
        elif isinstance(node, ast.If):
            # 统计条件语句的数量
            features['if_statements'] += 1
        elif isinstance(node, ast.Call):
            # 提取函数的调用语句数量：
            features['function_calls'] += 1
        elif isinstance(node, ast.Try):
            # 统计异常处理语句的数量：
            features['exception_handling'] += 1
    name_tensor = torch.tensor([ord(c) for c in features['name']], dtype=torch.float32)
    parameters_tensor = torch.tensor([len(features['parameters'])], dtype=torch.float32)
    assignments_tensor = torch.tensor([features['assignments']], dtype=torch.float32)
    loops_tensor = torch.tensor([features['loops']], dtype=torch.float32)
    if_statements_tensor = torch.tensor([features['if_statements']], dtype=torch.float32)
    print(name_tensor)
    print(parameters_tensor)
    print(assignments_tensor)
    print(loops_tensor)
    print(if_statements_tensor)
    return features


features = extract_function_features(login_user)
features2 = extract_function_features(self_update)
print(features)
print(features2)
print(type(login_user))
print('11111111111111')


