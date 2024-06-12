import ast
import inspect
import importlib.util
from collections import defaultdict


from django.conf import settings
import os
import openpyxl

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'guzhang.settings')






# 1。格式化验证、转换、验证
def input_format(code):

    # 解析代码字符串为抽象语法树（AST）
    tree = ast.parse(code)

    # 初始化评分
    score = 0

    # 检查代码中是否存在对输入进行格式化、转换或验证的函数调用
    function_calls = ['format', 'int', 'float', 'str', 'list', 'tuple', 'encode', 'decode', 're', 'regex',
                      'email.utils', 'email_validator']

    # 遍历抽象语法树，查找函数调用节点
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            function_name = node.func.id
            if function_name in function_calls:
                score += 1

    return score


# 2、API滥用
def analyze_api_abuse(source_code):
    # 解析函数的源代码，生成AST
    func_ast = ast.parse(source_code)

    # 初始化 API 调用次数统计字典
    api_call_counts = defaultdict(int)

    # 遍历AST节点
    for node in ast.walk(func_ast):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            # 统计函数调用中的API名称
            api_name = node.func.attr
            # 更新API调用次数统计
            api_call_counts[api_name] += 1

    # 计算总的API调用次数
    total_api_calls = sum(api_call_counts.values())

    # 根据API调用次数分级
    if total_api_calls == 0:
        return 0
    elif total_api_calls < 2:
        return 1
    elif total_api_calls < 5:
        return 2  
    elif total_api_calls < 10:
        return 3
    elif total_api_calls < 20:
        return 4
    elif total_api_calls < 50:
        return 5
    elif total_api_calls < 100:
        return 6
    elif total_api_calls < 150:
        return 7
    elif total_api_calls < 200:
        return 8
    else:
        return 9


# 3.安全
def analyze_security_issues(source_code):
    # 解析函数的源代码，生成AST
    func_ast = ast.parse(source_code)

    # 初始化问题级别
    security_issues_level = 0

    # 检查是否涉及数据库操作
    db_operations = {
        'sqlite3.connect': 1,  # SQLite 连接操作
        'psycopg2.connect': 1,  # PostgreSQL 连接操作
        'pymysql.connect': 1,  # MySQL 连接操作
        'cursor.execute': 1,  # 执行 SQL 语句
    }
    for node in ast.walk(func_ast):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name):
                    api_name = (node.func.value.id+ '.' + node.func.attr)
                    if api_name in db_operations:
                        # 涉及数据库操作，设置安全等级为 1
                        security_issues_level = 1

    # 如果涉及数据库操作，再检查是否涉及权限操作
    if security_issues_level == 1:
        # 检查是否涉及权限操作
        auth_operations = {
            'rbac': 1,  # 基于角色的访问控制库
            'abac': 1,  # 基于属性的访问控制库
            'jwt': 1,   # JSON Web Token 库
        }
        for node in ast.walk(func_ast):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in auth_operations:
                        # 涉及权限操作，设置安全等级为 0
                        security_issues_level = 0
                        break

    return security_issues_level



# 4.时间和状态
def analyze_time_and_state_issues(source_code):
    # 解析函数的源代码，生成AST

    func_ast = ast.parse(source_code)

    # 初始化问题级别
    time_and_state_issues_level = 0
    # 考虑并发访问共享资源情况
    for node in ast.walk(func_ast):
        if isinstance(node, ast.Call):
            if hasattr(node.func, 'attr'):
                api_name = node.func.attr
                if api_name in ['Lock', 'RLock', 'Semaphore', 'Condition', 'Event']:
                    time_and_state_issues_level += 3
    # 检查时间戳处理函数
    timestamp_issues = {
        'time.time': 1,  # 获取当前时间戳函数
        'datetime.now': 1,  # 获取当前时间函数
    }
    for node in ast.walk(func_ast):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                api_name = node.func.value.id + '.' + node.func.attr
                if api_name in timestamp_issues:
                    time_and_state_issues_level += timestamp_issues[api_name]

    # 检查时间区间计算函数
    time_range_issues = {
        'datetime.timedelta': 1,  # 时间差计算函数
    }
    for node in ast.walk(func_ast):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            api_name = node.func.id
            if api_name in time_range_issues:
                time_and_state_issues_level += time_range_issues[api_name]

    # 检查全局变量状态管理
    global_state_issues = {
        'global': 1,  # 使用global关键字的全局变量
    }
    for node in ast.walk(func_ast):
        if isinstance(node, ast.Global):
            for var_name in node.names:
                if var_name in global_state_issues:
                    time_and_state_issues_level += global_state_issues[var_name]

    # 检查对象状态管理
    object_state_issues = {
        'self': 1,  # 对象实例的状态管理
    }
    for node in ast.walk(func_ast):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id in object_state_issues:
                time_and_state_issues_level += object_state_issues[node.value.id]

    # 将问题级别限制在1到10之间
    time_and_state_issues_level = min(max(time_and_state_issues_level, 0), 9)

    return time_and_state_issues_level


# 5.1错误日志记录
def log_remember(code):
    # 解析代码字符串为抽象语法树（AST）
    tree = ast.parse(code)

    # 检查代码中是否存在输入验证函数
    log_functions = ['logging.exception', 'logging.basicConfig', 'log', 'logging.ERROR', 'logging', 'loguru',
                     'structlog', 'Log', 'Diary', 'diary','error','warning','ERROR','info','logger.error']
    log_score = 0

    # 遍历抽象语法树，查找函数调用节点
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            function_name = node.func.id
            if function_name in log_functions:
                log_score += 1
    if log_score > 0:
        log_score = 1
    return log_score


# 5.2语法错误
def check_syntax(c):
    try:
        compile(c, "<string>", "exec")
        syntax_error = False
    except SyntaxError as e:
        syntax_error = True
        error_message = str(e.msg)  # 获取错误消息

    if syntax_error:
        return 1
    else:
        return 0


# 6.代码质量
def evaluate_code_quality(code):
    # 解析代码字符串为抽象语法树（AST）

    tree = ast.parse(code)
    # 进行代码质量评估，根据评估结果给出分数
    score = 0

    # 检查函数命名和注释
    function_def = next((node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)), None)
    if function_def:
        if function_def.name.islower():
            score -= 1  # 函数名称不应该以小写字母开头
        if not function_def.body or not any(isinstance(statement, ast.Return) for statement in function_def.body):
            score -= 1  # 函数应该有返回语句
        score += 2  # 函数命名和注释正确性得分（根据需求可调整）

    # 检查代码可读性和可维护性
    lines = code.split('\n')
    if len(lines) > 50:
        score -= 1  # 代码行数过多可能导致可读性下降
    if any(line.startswith('\t') for line in lines):
        score -= 1  # 使用制表符而不是空格进行缩进是不推荐的
    score += 2  # 代码可读性和可维护性得分（根据需求可调整）

    # 检查错误处理和异常处理
    except_nodes = [node for node in ast.walk(tree) if isinstance(node, ast.ExceptHandler)]
    if not except_nodes:
        score -= 1  # 缺乏异常处理可降低代码质量
    score += 1  # 错误处理和异常处理得分（根据需求可调整）

    # 检查性能和效率
    ast_nodes = list(ast.walk(tree))
    if sum(isinstance(node, ast.For) for node in ast_nodes) > 3:
        score -= 1  # 循环次数过多可能降低性能
    score += 1  # 性能和效率得分（根据需求可调整）
    return max(min(score, 10), 1)  # 防止得分超出范围


# 7.封装
class Package(ast.NodeVisitor):
    def __init__(self):

        self.classes = 0  # 记录类使用次数
        self.functions = 0  # 记录函数使用次数
        self.nested_functions_count = 0  # 记录存在嵌套函数的次数
        self.nested_classes_count = 0  # 记录存在嵌套类的次数

    def generic_visit(self, node):
        super().generic_visit(node)

    def visit(self, node):
        method_name = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def visit_ClassDef(self, node):
        self.classes += 1
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.functions += 1
        self.generic_visit(node)

    def analyze(self, code):
        tree = ast.parse(code)
        self.visit(tree)

        # 统计嵌套函数和类的次数
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                parent = node
                while parent:
                    if isinstance(parent, ast.FunctionDef):
                        self.nested_functions_count += 1
                        break
                    parent = getattr(parent, 'parent', None)
            elif isinstance(node, ast.ClassDef):
                parent = node
                while parent:
                    if isinstance(parent, ast.ClassDef):
                        self.nested_classes_count += 1
                        break
                    parent = getattr(parent, 'parent', None)

        return [
            self._classify_usage(self.classes),
            self._classify_usage(self.functions),
            self._classify_usage(self.nested_functions_count),
            self._classify_usage(self.nested_classes_count)
        ]

    def _classify_usage(self, count):
        if count >= 10:
            return 10
        else:
            return count


# 8.环境
class Environment(ast.NodeVisitor):
    def __init__(self):
        # 初始化各项计数器和标志
        self.config_read_count = 0  # 配置文件读取次数和文件访问次数
        self.third_party_library_count = 0  # 第三方库和工具使用次数

    def generic_visit(self, node):
        # 默认遍历节点的行为
        super().generic_visit(node)

    def visit_Call(self, node):
        # 分析普通函数调用
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id == 'open':
                # 如果是对文件的操作，计数器加一
                self.config_read_count += 1
        elif isinstance(node.func, ast.Name) and node.func.id != 'print':
            # 如果是对其他函数的调用（排除 print），认为是使用了第三方库或工具
            self.third_party_library_count += 1
        self.generic_visit(node)

    def visit_Str(self, node):
        # 分析字符串
        parent = getattr(node, 'parent', None)
        if isinstance(parent, ast.Assign):
            if isinstance(parent.targets[0], ast.Name) and parent.targets[0].id == 'config':
                # 如果字符串是赋值给变量 config 的，认为进行了配置文件读取
                self.config_read_count += 1
        self.generic_visit(node)

    def visit_With(self, node):
        # 分析 with 语句，检查是否是对文件的操作
        if isinstance(node.items[0].context_expr, ast.Call):
            if isinstance(node.items[0].context_expr.func, ast.Name) and node.items[0].context_expr.func.id == 'open':
                # 如果是对文件的操作，计数器加一
                self.config_read_count += 1
        self.generic_visit(node)

    def analyze(self, code):
        # 解析代码并分析
        tree = ast.parse(code)
        self.visit(tree)
        # 返回分析结果，包括计数值和标志
        return [self._classify_count(self.config_read_count),
                self._classify_count(self.third_party_library_count)]

    def _classify_count(self, count):
        # 根据计数值分类
        if count >= 10:
            return 10
        else:
            return count


def load_module(file_path):
    spec = importlib.util.spec_from_file_location("module_name", file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# 1.异常处理统计及特征值总函数
def extract_function_features(file_path):


    with open(file_path, 'r', encoding='utf-8') as file:
        code = file.read()
        tree = ast.parse(code, file_path)

    nodes_content = {}

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and getattr(node, 'col_offset', 0) == 0:
            # 提取节点名称和源代码片段
            node_name = node.name
            node_source = ast.get_source_segment(code, node)
            # 存储节点内容
            nodes_content[node_name] = node_source

    for key, value in nodes_content.items():
        # print(key)
        name = key
        source_code =value
        func_ast = ast.parse(source_code)


        features = {
            'name': name,
            'input_format': 0,  # 0-10表示输入转换验证操作的次数
            'exception_handling': 0,  # 0-10异常处理的次数
            'code_quality': 0,  # 0-10表示代码质量好坏
            'log_score': 0,  # 0-10表示调用日志的函数
            'API': 0,  # 1-10表示是否滥用API，等级越高越滥用
            'Time_State': 0,  # 1-10等级越高，时间状态隐患严重
            'Security': 0,  # 0表示安全，1表示不安全
            'syntax': 0,  # 0表示无语法错误 1表示有语法错误
            'Package': [],  # 5值，0-10，封装越好
            'Environment': [],  # 3值 0-10，越多越不好
            'label':0,
            # 其他你感兴趣的特征
        }
        sum = 0
        # 遍历AST节点
        for node in ast.walk(func_ast):
            if isinstance(node, ast.Try):
                # 统计异常处理语句的数量：
                sum += 1
        if sum < 5:
            features['exception_handling'] = sum
        else:
            features['exception_handling'] = 10
        if input_format(source_code) < 10:
            features['input_format'] = input_format(source_code)
        else:
            features['input_format'] = 10
        features['code_quality'] = evaluate_code_quality(source_code)
        features['log_score'] = log_remember(source_code)
        features['API'] = analyze_api_abuse(source_code)
        features['Time_State'] = analyze_time_and_state_issues(source_code)
        features['Security'] = analyze_security_issues(source_code)
        analyzer = Package()
        features['Package'] = analyzer.analyze(source_code)
        analyzer2 = Environment()
        features['Environment'] = analyzer2.analyze(source_code)
        features['syntax'] = check_syntax(source_code)
        features['label'] = 0
        # features['input_validation']=input_validation(func)
        save_features_to_excel(features, 'Analyze.xlsx')




def save_features_to_excel(features, filename):
    try:
        # 尝试打开现有的Excel文件
        workbook = openpyxl.load_workbook(filename)

        # 获取默认的工作表
        sheet = workbook.active

    except FileNotFoundError:
        # 如果文件不存在，则创建一个新的工作簿和工作表
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        # 写入特征标题行
        header_row = ['name','input_format', 'exception_handling', 'code_quality',
                      'log_score', 'API', 'Time_State', 'Security', 'syntax', 'Package', 'Environment','label']
        sheet.append(header_row)

    else:
        # 文件存在，获取现有的特征标题行
        header_row = [cell.value for cell in sheet[1]]

    # 写入特征值
    row = []
    for key in header_row:
        if key in ['Package', 'Environment']:
            # 将列表转换为字符串，并使用逗号分隔符
            values_str = ', '.join(str(value) for value in features[key])
            row.append(values_str)
        else:
            row.append(features[key])
    sheet.append(row)
    # 保存工作簿到文件
    workbook.save(filename)


file_path = "views.py"  # 替换为你要分析的 Python 文件的路径
extract_function_features(file_path)





