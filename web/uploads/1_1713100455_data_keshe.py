import requests
from django.shortcuts import render, HttpResponse, redirect
from app01.models import User, Store, Buy,  Commodity, Manage,OpLog
from django.utils import timezone
import pymysql
from django.db import connection

def user_list(req):
    with connection.cursor() as cursor:
        cursor.execute("select * from app01_user")
        data_list = cursor.fetchall()
        cursor.execute("select count(*) from app01_user")
        ((count,),) = cursor.fetchall()
    return render(req, 'user_list.html', {'n1': data_list, 'account': 'admin','count':count})
    # 返回 user_list.html 这个文件，req是一个参数，该文件根据app注册顺序，以此在它们的templates里面寻找


def login_manage(req):
    if req.method == "GET":
        # 如果是GET请求
        return render(req, 'login_manage.html')
    else:
        # 如果是POST请求
        with connection.cursor() as cursor:
            cursor.execute("select * from app01_user")
            data_list = cursor.fetchall()
            res = req.POST
            name = res.get('user_name')
            pwd = res.get('user_password')
            if name == 'admin' and pwd == '666':
                return redirect('/users/list/')
            return redirect('/login_manage/')


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
            OpLog.objects.create(account=name, action='登录')
            req.session["info"]={'account':name}
            for a in data_list:
                if name == a[2] and pwd == a[3]:
                    return redirect('/user/buy/')
            # return render(req, 'login_user.html')
            return redirect("/login_user/")


def user_delete(req, id):
    with connection.cursor() as cursor:
        if req.method == "GET":
            # User.objects.get(id=id).delete()
            cursor.execute("delete from app01_user where id=%s",[id])
            return redirect('/users/list/')
        else:
            # data_list = User.objects.all()
            cursor.execute("select * from app01_user")
            data_list=cursor.fetchall()
            return render(req, 'user_list.html', {'n1': data_list})


def user_update(req, id):
    with connection.cursor() as cursor:
        if req.method == "GET":
            # 如果是GET请求
            re = User.objects.get(id=id)
            return render(req, 'user_update.html', {'n1': re, 'n2': id})
        else:
            # 如果是POST请求
            res = req.POST
            name = res.get('user_name')
            account = res.get('user_account')
            pwd = res.get('user_password')
            address = res.get('user_address')
            phone = res.get('user_phone')
            sql="update app01_user set name=%s , account=%s , password=%s , address=%s , phone=%s where id=%s"
            cursor.execute(sql,[name,account,pwd,address,phone,id])
            return redirect('/users/list/')



def user_add(req):
    try:
        with connection.cursor() as cursor:
            if req.method == "POST":
                res = req.POST
                name = res.get('user_name')
                account = res.get('user_account')
                pwd = res.get('user_password')
                address = res.get('user_address')
                phone = res.get('user_phone')
                req.session['info'] = {'account': account}
                sql = "CALL add_user(%s,%s,%s,%s,%s)"
                cursor.execute(sql, (name, account, pwd, address, phone))
                return redirect('/users/list/')
            return render(req, 'user_add.html')
    except Exception as e:
        print(f"An exception occurred in change: {str(e)}")
        return HttpResponse("失败")


def store_add(req):
    try:
        with connection.cursor() as cursor:
            if req.method == "GET":
                return render(req, 'store_add.html')
            else:
                # 如果是POST请求
                res = req.POST
                name = res.get('store_name')
                store_kinds = res.get('store_kinds')
                in_time = res.get('in_time')
                score = res.get('score')
                store_sale = res.get('store_sale')
                sql = "CALL add_store(%s,%s,%s,%s,%s)"
                cursor.execute(sql, (name, store_kinds, in_time, score, store_sale))
                cursor.execute("select * from app01_store")
                data_list = cursor.fetchall()
                info = req.session.get("info")
            return render(req, 'store_list.html', {'n1': data_list, 'account': info["account"]})
    except Exception as e:
        print(f"An exception occurred in change: {str(e)}")
        return HttpResponse("失败")



def commodity_add(req,s_id):
    try:
        with connection.cursor() as cursor:
            if req.method == "GET":
                return render(req, 'commodity_add.html',{'s_id':s_id})
            else:
                # 如果是POST请求
                res = req.POST
                c_name = res.get('c_name')
                c_price = res.get('c_price')
                inventory = res.get('inventory')
                sql = "CALL add_commodity(%s,%s,%s)"
                cursor.execute(sql, (c_name,c_price,0))
                cursor.execute("select max(id) from app01_commodity ")
                ((c_id,),)=cursor.fetchall()
                sql = "CALL add_manage(%s,%s,%s)"
                cursor.execute(sql, (s_id,c_id, inventory))
                # cursor.execute("select * from app01_store")
                # data_list = cursor.fetchall()
                # info = req.session.get("info")
            return redirect(f'/store/{s_id}/more/')
    except Exception as e:
        print(f"An exception occurred in change: {str(e)}")
        return HttpResponse("失败")


def store_list(req):
    try:
        with connection.cursor() as cursor:
            cursor.execute("select * from app01_store")
            data_list=cursor.fetchall()
            cursor.execute("select count(*) from app01_store")
            ((count,),) = cursor.fetchall()
        return render(req, 'store_list.html', {'n1': data_list, 'account': 'admin','count':count})
    except Exception as e:
        print(f"An exception occurred in change: {str(e)}")
        return HttpResponse("失败")


def store_more(req, id):
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT app01_commodity.id,c_name,c_price,c_sale,inventory,app01_manage.id,app01_store.id from app01_manage,app01_commodity,app01_store where app01_store.id=app01_manage.s_id and app01_manage.c_id=app01_commodity.id and app01_store.id=%s",[id])
        # data_list = Manage.objects.filter(s_id=id)
        # daya_list2 = Commodity.objects.all()
            na = Store.objects.get(id=id)
            res=cursor.fetchall()
        # return render(req, 'store_more.html', {'n1': data_list, 'n2': daya_list2, 'name': na.s_name})
            return render(req, 'store_more.html', {'n1': res,'name': na.s_name,'s_id':id})

    except Exception as e:
        print(f"An exception occurred in change: {str(e)}")
        return HttpResponse("失败")


def store_update(req, id):
    try:
        with connection.cursor() as cursor:
            if req.method == "GET":
                # 如果是GET请求
                re = Store.objects.get(id=id)
                return render(req, 'store_update.html', {'n1': re, 'n2': id})
            else:
                # 如果是POST请求
                cursor.execute("select * from app01_store")
                res = req.POST
                name = res.get('store_name')
                store_kinds = res.get('store_kinds')
                in_time = res.get('in_time')
                score = res.get('score')
                store_sale = res.get('store_sale')
                cursor.execute("update app01_store set s_name=%s,s_kinds=%s, check_in_time=%s, score=%s,s_sale=%s where id=%s ",(name,store_kinds,in_time,score,store_sale,id))
                return redirect('/store/list/')
    except Exception as e:
        print(f"An exception occurred in change: {str(e)}")
        return HttpResponse("失败")


def store_delete(req, id):
    try:
        with connection.cursor() as cursor:
            if req.method == "GET":
                # Store.objects.get(id=id).delete()
                cursor.execute("delete from app01_store where id=%s", [id])
                return redirect('/store/list/')
            else:
                cursor.execute("select * from app01_store")
                data_list = cursor.fetchall()
                return render(req, 'store_list.html', {'n1': data_list})
    except Exception as e:
        print(f"An exception occurred in change: {str(e)}")
        return HttpResponse("失败")


def store_buy(req, id):
    try:
        with connection.cursor() as cursor:
            # data_list = Manage.objects.filter(s_id=id)
            # daya_list2 = Commodity.objects.all()
            cursor.execute(
                "SELECT c_name,c_price,inventory,app01_store.id,app01_commodity.id from app01_manage,app01_commodity,app01_store where app01_store.id=app01_manage.s_id and app01_manage.c_id=app01_commodity.id and app01_store.id=%s",[id])
            res=cursor.fetchall()
            na = Store.objects.get(id=id)
            info = req.session.get("info")
            return render(req, 'store_buy.html',
                          {'n1': res ,'name': na.s_name, 'account': info["account"]})
    except Exception as e:
        print(f"An exception occurred in change: {str(e)}")
        return HttpResponse("失败")


def user_buy(req):
        conn = pymysql.connect(
            host='127.0.0.1',
            user='1_user',
            password='123456',
            database='sales_platform',
            port=3306  # 默认MySQL端口
        )
        cursor = conn.cursor()
        info = req.session.get("info")
        cursor.execute("select * from app01_store")
        data = cursor.fetchall()
        print(info["account"])
        return render(req, 'user_buy.html', {'n1': data, 'account': info["account"]})

    # except Exception as e:
    #     print(f"An exception occurred in change: {str(e)}")
    #     return HttpResponse("失败")


def buy(req, s_id, c_id):
    try:
        conn = pymysql.connect(
            host='127.0.0.1',
            user='1_user',
            password='123456',
            database='sales_platform',
            port=3306  # 默认MySQL端口
        )
        cursor = conn.cursor()
        data_list = Manage.objects.filter(s_id=s_id)
        daya_list2 = Commodity.objects.all()
        na = Store.objects.get(id=s_id)
        if req.method == "GET":
            return render(req, 'store_buy.html', {'n1': data_list, 'n2': daya_list2, 'name': na.s_name})
        else:
            info = req.session.get("info")
            s = Store.objects.get(id=s_id)
            s_name = s.s_name
            c = Commodity.objects.get(id=c_id)
            c_price = c.c_price
            c_name = c.c_name
            d1 = timezone.now()
            time = d1.strftime("%Y-%m-%d")
            res = req.POST
            sum = res.get("moment")
            sum2 = float(sum)
            sql = "CALL add_buy(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            cursor.execute(sql,
                           (info["account"], c_id, c_name, s_id, s_name, c_price, sum, c_price * sum2, time, 0))
            conn.commit()
            return redirect(f'/store/{s_id}/buy/')
    except Exception as e:
        print(f"An exception occurred in change: {str(e)}")
        return HttpResponse("失败")


def record_user(req):
    try:
        info = req.session.get("info")
        # data_list = Buy.objects.filter(account=info["account"])
        with connection.cursor() as cursor:
            sql = "SELECT * FROM app01_buy WHERE account = %s"
            cursor.execute(sql,[info["account"]])
            data = cursor.fetchall()
        return render(req, 'record_user.html', {'n1': data, 'account': info["account"]})
    except Exception as e:
        print(f"An exception occurred in change: {str(e)}")
        return HttpResponse("失败")


def record_manager(req):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM app01_buy")
            data_list = cursor.fetchall()
        return render(req, 'buy_list.html', {'n1': data_list, 'account': 'admin'})
    except Exception as e:
        print(f"An exception occurred in change: {str(e)}")
        return HttpResponse("失败")


def search_store(req):
    try:
        res = req.GET
        res2 = res.get("search")
        a = '%' + res2 + '%'
        with connection.cursor() as cursor:
            sql = "SELECT * FROM app01_store WHERE s_name LIKE %s;"
            cursor.execute(sql, [a])
            data = cursor.fetchall()
            info = req.session.get("info")
            print(1)
        return render(req, 'user_buy.html', {'n1': data, 'account': info["account"]})
    except Exception as e:
        print(f"An exception occurred in change: {str(e)}")
        return HttpResponse("失败")


def M_search_store(req):
    try:
        res = req.GET
        res2 = res.get("search")
        a = '%' + res2 + '%'
        with connection.cursor() as cursor:
            sql = "SELECT * FROM app01_store WHERE s_name LIKE %s;"
            cursor.execute(sql, [a])
            data = cursor.fetchall()
            cursor.execute("select count(*) from app01_store where s_name LIKE %s", [a])
            ((count,),) = cursor.fetchall()
        return render(req, 'store_list.html', {'n1': data, 'account': 'admin','count':count})
    except Exception as e:
        print(f"An exception occurred in change: {str(e)}")
        return HttpResponse("失败")


def M_search_user(req):
    try:
        res = req.GET
        res2 = res.get("search")
        a='%'+res2+'%'
        with connection.cursor() as cursor:
            sql = "SELECT * FROM app01_user WHERE account LIKE %s;"
            cursor.execute(sql,[a])
            data = cursor.fetchall()
            cursor.execute("select count(*) from app01_user where account LIKE %s",[a])
            ((count,),) = cursor.fetchall()
        return render(req, 'user_list.html', {'n1': data, 'account': 'admin','count':count})
    except Exception as e:
        print(f"An exception occurred in change: {str(e)}")
        return HttpResponse("失败")


def M_search_buy(req):
    try:
        res = req.GET
        res2 = res.get("search")
        a = '%' + res2 + '%'
        with connection.cursor() as cursor:
            sql = "SELECT * FROM app01_buy WHERE account LIKE %s;"
            cursor.execute(sql,[a])
            data = cursor.fetchall()
        return render(req, 'buy_list.html', {'n1': data, 'account': 'admin'})
    except Exception as e:
        print(f"An exception occurred in change: {str(e)}")
        return HttpResponse("失败")


from django.db.models import Avg


def score(req, id):
    try:
        conn = pymysql.connect(
            host='127.0.0.1',
            user='1_user',
            password='123456',
            database='sales_platform',
            port=3306  # 默认MySQL端口
        )
        cursor = conn.cursor()
        if req.method == "GET":
            res = req.GET
            res2 = res.get("score")
            cursor.execute("update app01_buy set score=%s where id=%s",[res2,id])
            # Buy.objects.filter(id=id).update(score=res2)
            conn.commit()
            return redirect('/buy/record/')
        else:
            info = req.session.get("info")
            # data_list = Buy.objects.filter(account=info["account"])
            cursor.execute("select * from app01_buy where account=%s",[info["account"]])
            data_list=cursor.fetchall()
            return render(req, 'record_user.html', {'n1': data_list, 'account': info["account"]})
    except Exception as e:
        print(f"An exception occurred in change: {str(e)}")
        return HttpResponse("失败")


def commodity_update(req, id, c_id, s_id):
    try:
        if req.method == "GET":
            # 如果是GET请求
            name_list = Commodity.objects.filter(id=c_id).first()
            inventory = Manage.objects.filter(id=id).first()
            na = Store.objects.get(id=s_id)
            return render(req, 'commodity_update.html',
                          {'id': id, 's_id': s_id, 'c_id': c_id, 'n1': name_list.c_name, 'n2': name_list.c_price,
                           'n3': inventory.inventory, 'name': na.s_name})

        else:
            # 如果是POST请求
            res = req.POST
            name = res.get('commodity_name')
            price = res.get('commodity_price')
            inventory = res.get('commodity_inventory')
            Commodity.objects.filter(id=c_id).update(c_name=name, c_price=price)
            Manage.objects.filter(id=id).update(inventory=inventory)
            # data_list = Store.objects.all()
            return redirect(f'/store/{s_id}/more/')
    except Exception as e:
        print(f"An exception occurred in change: {str(e)}")
        return HttpResponse("失败")



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
                # req.session['info'] = {'account':account}
                # info = req.session.get("info")
                # print(info["account"])
                # User.objects.create(name=name, account=account, password=pwd, address=address, phone=phone)
                sql = "CALL add_user(%s,%s,%s,%s,%s)"
                cursor.execute(sql, (name, account, pwd, address, phone))
                return redirect('/login_user/')
    except Exception as e:
        print(f"An exception occurred in change: {str(e)}")
        return HttpResponse("失败")


def meishi(req):
    try:
        info = req.session.get("info")
        with connection.cursor() as cursor:
            cursor.execute("select * from meishi")
            data = cursor.fetchall()
            print(data)
            return render(req, 'user_buy.html', {'n1': data, 'account': info["account"]})
    except Exception as e:
        print(f"An exception occurred in change: {str(e)}")
        return HttpResponse("失败")


def fuzhuang(req):
    try:
        info = req.session.get("info")
        with connection.cursor() as cursor:
            cursor.execute("select * from fuzhuang")
            data = cursor.fetchall()
            print(data)
            return render(req, 'user_buy.html', {'n1': data, 'account': info["account"]})
    except Exception as e:
        print(f"An exception occurred in change: {str(e)}")
        return HttpResponse("失败")


def yundong(req):
    try:
        info = req.session.get("info")
        with connection.cursor() as cursor:
            cursor.execute("select * from yundong")
            data = cursor.fetchall()
            print(data)
            return render(req, 'user_buy.html', {'n1': data, 'account': info["account"]})
    except Exception as e:
        print(f"An exception occurred in change: {str(e)}")
        return HttpResponse("失败")

def zhubao(req):
    try:
        info = req.session.get("info")
        with connection.cursor() as cursor:
            cursor.execute("select * from zhubao")
            data = cursor.fetchall()
            print(data)
            return render(req, 'user_buy.html', {'n1': data, 'account': info["account"]})
    except Exception as e:
        print(f"An exception occurred in change: {str(e)}")
        return HttpResponse("失败")

def self_update(req):
    try:
        with connection.cursor() as cursor:
            info = req.session.get("info")
            id = info["id"]
            if req.method == "GET":
                # 如果是GET请求
                re = User.objects.get(id=id)
                return render(req, 'self_update.html', {'n1': re, 'n2': id})
            else:
                # 如果是POST请求
                res = req.POST
                name = res.get('user_name')
                account = res.get('user_account')
                pwd = res.get('user_password')
                address = res.get('user_address')
                phone = res.get('user_phone')
                sql="update app01_user set name=%s , account=%s , password=%s , address=%s , phone=%s where id=%s"
                cursor.execute(sql,[name,account,pwd,address,phone,id])
                cursor.execute("select * from app01_store")
                data_list = cursor.fetchall()
            return render(req, 'user_buy.html', {'n1': data_list,'account': info["account"]})
    except Exception as e:
        print(f"An exception occurred in change: {str(e)}")
        return HttpResponse("失败")



