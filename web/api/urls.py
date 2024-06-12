from django.urls import path
from rest_framework.routers import SimpleRouter
from api.views.account_views import RegisterView,UserInfoView
from api.views.uploadfiles_views import UploadFilesView
from api.views.fault_location_views import FaultLocationView
from api.views.code_manage_views import CodeManageView
from api.views.system_views import GetUserLogView
from api.views.total_views import TotalView
from api.views.prop_map_views import PropMapUploadFilesView
from api.views.Function_calls import FunctionCallView
from api.views.fault_prop import FaultPropView
# from api.views.fault_prop import FaultProp
from api.views.count import Count_view
from api.views.delete import Delete_view
from api.views.file_views import FileViewSet
from api.views.account_views import UserViewSet, UserUpgradeViewSet,UserpasswordViewSet
from api.views.operation_views import OperationViewSet


router = SimpleRouter()
router.register('file_manage', FileViewSet, basename='file-manage')
router.register('user', UserViewSet, basename='user-manage')
router.register('user_upgrade', UserUpgradeViewSet, basename='user-upgrade')
router.register('history', OperationViewSet, basename='history')
router.register('set_password', UserpasswordViewSet, basename='password-upgrade')
# router.register('get_logs', GetUserLogView, basename='get-logs')

urlpatterns = [
    path('total/', TotalView.as_view()),  
    path('register/', RegisterView.as_view()),
    path('user_info/', UserInfoView.as_view()),
    path('upload_file/',UploadFilesView.as_view()),
    path('fault_location/',FaultLocationView.as_view()),
    path('code_manage/',CodeManageView.as_view()),
    path('get_logs/',GetUserLogView.as_view()),
    path('func_call/', FunctionCallView.as_view()),
    path('fault_prop/', FaultPropView.as_view()),
    # path('Function_calls/',       ),
    # path('fault_prop/',FaultProp.as_view()),

    path('prop_upload/',PropMapUploadFilesView.as_view()),
    path('count/',Count_view.as_view()),
    path('delete/',Delete_view.as_view()),

]

urlpatterns += router.urls
