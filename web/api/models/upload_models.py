from django.db import models
from django.contrib.auth.models import User

class UploadFile(models.Model):
    upload_user = models.ForeignKey(User,on_delete=models.DO_NOTHING,verbose_name='操作用户')
    name = models.CharField(max_length=200,null=False,blank=False,verbose_name='名称')
    file_name = models.CharField(max_length=200,null=False,blank=False,verbose_name='文章名称')
    ext = models.JSONField(null=False,blank=False,verbose_name='文件选择错误类型')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='录入时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = '上传文件'
        ordering = ['-id']