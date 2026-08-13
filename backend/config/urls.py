from django.contrib import admin
from django.urls import include, path

from apps.inscricoes.views import DashboardView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.core.urls')),
    path('api/lotes/', include('apps.lotes.urls')),
    path('api/auth/', include('apps.users.urls')),
    path('api/inscricoes/', include('apps.inscricoes.urls')),
    path('api/admin/inscricoes/', include('apps.inscricoes.admin_urls')),
    path('api/admin/checkin/', include('apps.inscricoes.checkin_urls')),
    path('api/admin/cupons/', include('apps.inscricoes.cupom_admin_urls')),
    path('api/admin/lotes/', include('apps.lotes.admin_urls')),
    path('api/admin/dashboard/', DashboardView.as_view(), name='admin-dashboard'),
]
