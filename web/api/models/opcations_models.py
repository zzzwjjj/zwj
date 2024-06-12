from django.db import models
from django.contrib.auth.models import User

class OptionLog(models.Model):
    op_user = models.ForeignKey(User,on_delete=models.DO_NOTHING,verbose_name='操作用户')
    op_name = models.CharField(max_length=200,null=False,blank=False,verbose_name='操作名称')
    status = models.BooleanField(default=True,null=False,blank=False,verbose_name='状态')
    ext = models.JSONField(null=True,blank=True,verbose_name='补充字段')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='录入时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = '操作记录'
        ordering = ['-id']