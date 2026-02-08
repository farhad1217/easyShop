"""
URL configuration for easyShop project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from shop import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.landing_page, name='landing_page'),
    path('family/register/', views.family_register, name='family_register'),
    path('family/login/', views.family_login, name='family_login'),
    path('family/dashboard/', views.family_dashboard, name='family_dashboard'),
    path('family/send-list/', views.send_market_list, name='send_market_list'),
    path('family/list/<int:pk>/update/', views.update_market_list, name='update_market_list'),
    path('family/list/<int:pk>/delete/', views.delete_market_list, name='delete_market_list'),
    path('management/login/', views.management_login, name='management_login'),
    path('management/dashboard/', views.management_dashboard, name='management_dashboard'),
    path('management/date-summary/', views.date_wise_summary, name='date_wise_summary'),
    path('management/user-directory/', views.user_directory, name='user_directory'),
    path('management/user/<int:user_id>/', views.user_profile_detail, name='user_profile_detail'),
    path('management/approve/<int:pk>/', views.approve_list, name='approve_list'),
    path('management/delete/<int:pk>/', views.admin_delete_list, name='admin_delete_list'),
    path('management/date-summary/pdf/', views.date_wise_summary_pdf, name='date_wise_summary_pdf'),
    path('management/date-summary/consolidated/', views.date_wise_consolidated, name='date_wise_consolidated'),
    path('management/date-summary/consolidated/pdf/', views.date_wise_consolidated_pdf, name='date_wise_consolidated_pdf'),
    path('list/<int:pk>/comments/', views.list_comment_thread, name='list_comment_thread'),
    path('messages/', views.messaging_inbox, name='messaging_inbox'),
    path('messages/<int:user_id>/', views.messaging_thread, name='messaging_thread'),
    path('messages/unread-count/', views.message_unread_count, name='message_unread_count'),
    path('logout/', views.user_logout, name='user_logout'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
