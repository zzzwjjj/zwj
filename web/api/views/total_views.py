from rest_framework.views import APIView
from rest_framework.response import Response
from api.models.opcations_models import OptionLog
from api.models.upload_models import UploadFile
import datetime




def get_previous_days(days_count):
    today = datetime.datetime.now().date()  # 获取今天的日期
    # 创建一个空列表来存储日期
    dates_list = []
    # 循环指定的天数
    for i in range(int(days_count)):
        # 计算今天的日期减去i天的日期
        date = today - datetime.timedelta(days=i)
        # 将计算出的日期添加到列表中
        dates_list.append(date)
    return dates_list[::-1]


class TotalView(APIView):
    def __init__(self):
        self.resp_dict = {
            'status_code':20000,
            'msg':None,
            'data':None
        }
        self.echats_name_dict = {
            'pie':'错误类别分布',
            'zhu':'错误柱状图',
            'line_before':'故障趋势1',
            'line_after':'故障趋势2'
        }

    def get(self,request,*args,**kwargs):
        user_obj = request.user
        echats_name = request.query_params.get('echats_name')
        days = request.query_params.get('days',7)

        chats_cn_name = self.echats_name_dict.get(echats_name)
        if not chats_cn_name:
            self.resp_dict['status_code'] = 50001
            self.resp_dict['msg'] = '参数错误'
        else:
            reversed_dict = {}
            op_dict = {
                        '1': "输入有效性和表示",
                        '2': "API滥用",
                        '3': "安全功能",
                        '4': "时间和状态",
                        '5': "错误",
                        '6': "代码质量",
                        '7': "封装",
                        '8': "环境",
            }
                    
            if echats_name == 'pie'or echats_name == 'zhu':
                # 错误类别转换
                log_objs = UploadFile.objects.filter(
                    upload_user=user_obj,
                    create_time__gte=datetime.datetime.now()-datetime.timedelta(days=int(days))
                )
            
                for log_obj in log_objs:
                    if not log_obj.ext:continue
                    for index_id in log_obj.ext:
                        if index_id not in op_dict:continue
                        if index_id not in reversed_dict:
                            reversed_dict[index_id] = {
                                'name':op_dict.get(index_id),
                                'value':0
                            }
                        select_list_count = len(log_obj.ext.get(index_id).get('select_list'))
                        reversed_dict[index_id]['value'] += select_list_count
                self.resp_dict['data'] = {
                    'title_name':chats_cn_name,
                    'data':reversed_dict
                }
                        
            if echats_name == 'line_before':
                days_list = get_previous_days(days)
                self.resp_dict['data'] = {}
                self.resp_dict['data']['date_list'] = [day.strftime('%m-%d') for day in days_list]
                for log_day in days_list:
                    # 每天的都要查询一下
                    log_objs = UploadFile.objects.filter(
                        upload_user=user_obj,
                        create_time__year=log_day.year,
                        create_time__month=log_day.month,
                        create_time__day=log_day.day,
                    )
                    day_count = {'1':0,'2':0,'3':0,'4':0}
                    for log_obj in log_objs:
                        if not log_obj.ext:continue
                        for index_id in log_obj.ext:
                            if index_id not in ['1','2','3','4']:continue
                            if index_id not in reversed_dict:
                                reversed_dict[index_id] = {
                                    'name':op_dict.get(index_id),
                                    'value_list':[]
                                }
                            select_list_count = len(log_obj.ext.get(index_id).get('select_list'))
                            day_count[index_id] += select_list_count

                    for d in day_count:
                        if d not in reversed_dict:
                            reversed_dict[d] = {
                                    'name':op_dict.get(d),
                                    'value_list':[]
                                }
                        reversed_dict[d]['value_list'].append(day_count[d])
                    
                self.resp_dict['data']['title_name'] = chats_cn_name
                self.resp_dict['data']['data_list'] = reversed_dict

        if echats_name == 'line_after':
                days_list = get_previous_days(days)
                self.resp_dict['data'] = {}
                self.resp_dict['data']['date_list'] = [day.strftime('%m-%d') for day in days_list]
                for log_day in days_list:
                    # 每天的都要查询一下
                    log_objs = UploadFile.objects.filter(
                        upload_user=user_obj,
                        create_time__year=log_day.year,
                        create_time__month=log_day.month,
                        create_time__day=log_day.day,
                    )
                    day_count = {'5':0,'6':0,'7':0,'8':0}
                    for log_obj in log_objs:
                        if not log_obj.ext:continue
                        for index_id in log_obj.ext:
                            if index_id not in ['5','6','7','8']:continue
                            if index_id not in reversed_dict:
                                reversed_dict[index_id] = {
                                    'name':op_dict.get(index_id),
                                    'value_list':[]
                                }
                            select_list_count = len(log_obj.ext.get(index_id).get('select_list'))
                            day_count[index_id] += select_list_count

                    for d in day_count:
                        if d not in reversed_dict:
                            reversed_dict[d] = {
                                    'name':op_dict.get(d),
                                    'value_list':[]
                                }
                        reversed_dict[d]['value_list'].append(day_count[d])
                    
                self.resp_dict['data']['title_name'] = chats_cn_name
                self.resp_dict['data']['data_list'] = reversed_dict
                    

                    
        return Response(self.resp_dict)
        
        
        
        