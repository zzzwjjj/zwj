from django.db import models

# Create your models here.
class User(models.Model):
    name = models.CharField(max_length=32)  # 昵称
    account = models.CharField(max_length=64)  # 账号
    password = models.CharField(max_length=64)  # 密码
    gender = models.CharField(max_length=10,blank=True ) #性别
    e_mail = models.CharField(max_length=64,blank=True) #邮箱
    phone = models.CharField(max_length=11,blank=True) #手机
    objects = models.Manager()


class Code(models.Model):
    account = models.CharField(max_length=64)
    title = models.CharField(max_length=100)
    code = models.TextField()
    objects = models.Manager()

class OpLog(models.Model):
    account = models.CharField(max_length=64)
    action = models.CharField(max_length=255)
    time = models.TextField()
    objects = models.Manager()


