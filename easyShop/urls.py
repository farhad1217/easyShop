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
from django.views.static import serve as static_serve
from shop import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.landing_page, name='landing_page'),
    path('family/register/', views.family_register, name='family_register'),
    path('family/login/', views.family_login, name='family_login'),
    path('family/dashboard/', views.family_dashboard, name='family_dashboard'),
    path('family/profile/', views.my_profile, name='my_profile'),
    path('family/send-list/', views.send_market_list, name='send_market_list'),
    path('family/list/<int:pk>/update/', views.update_market_list, name='update_market_list'),
    path('family/list/<int:pk>/delete/', views.delete_market_list, name='delete_market_list'),
    path('management/login/', views.management_login, name='management_login'),
    path('management/dashboard/', views.management_dashboard, name='management_dashboard'),
    path('management/user-directory/', views.user_directory, name='user_directory'),
    path('management/write-status/', views.write_list_status, name='write_list_status'),
    path('management/user-profiles/', views.user_profiles, name='user_profiles'),
    path('management/user-profiles/<int:user_id>/delete/', views.soft_delete_profile, name='soft_delete_profile'),
    path('management/trash/', views.trash_folder, name='trash_folder'),
    path('management/trash/<int:user_id>/restore/', views.restore_profile, name='restore_profile'),
    path('management/trash/<int:user_id>/permanent-delete/', views.permanent_delete_profile, name='permanent_delete_profile'),
    path('management/user/<int:user_id>/', views.user_profile_detail, name='user_profile_detail'),
    path('management/user/<int:user_id>/edit/', views.edit_user_profile, name='edit_user_profile'),
    path('management/profile/<int:user_id>/save-delivery-path/', views.save_delivery_path, name='save_delivery_path'),
    path('management/profile/<int:user_id>/update-address/', views.update_address, name='update_address'),
    path('management/pathway/images/', views.pathway_images, name='pathway_images'),
    path('management/pathway/upload/', views.pathway_upload, name='pathway_upload'),
    path('management/pathway/replace/<int:image_id>/', views.pathway_replace, name='pathway_replace'),
    path('management/pathway/delete/<int:image_id>/', views.pathway_delete, name='pathway_delete'),
    path('management/pathway/note/<int:image_id>/', views.pathway_update_note, name='pathway_update_note'),
    path('management/approve/<int:pk>/', views.approve_list, name='approve_list'),
    path('management/revert-pending/<int:pk>/', views.revert_to_pending, name='revert_to_pending'),
    path('management/decline/<int:pk>/', views.decline_list, name='decline_list'),
    path('management/deliver/<int:pk>/', views.deliver_list, name='deliver_list'),
    path('management/restore/<int:pk>/', views.restore_list, name='restore_list'),
    path('management/delete/<int:pk>/', views.admin_delete_list, name='admin_delete_list'),
    path('management/list/<int:pk>/edit/', views.admin_edit_list, name='admin_edit_list'),
    path('management/list/<int:pk>/ai-generate/', views.ai_generate_list, name='ai_generate_list'),
    path('management/list-entry/user-view/', views.list_entry_user_view, name='list_entry_user_view'),
    path('management/list-entry/consolidated/', views.list_entry_consolidated, name='list_entry_consolidated'),
    path('management/list-entry/consolidated/pdf/', views.list_entry_consolidated_pdf, name='list_entry_consolidated_pdf'),
    path('management/delivery-flow/save/', views.save_delivery_flow, name='save_delivery_flow'),
    path('management/send-status-presets/save/', views.save_send_status_presets, name='save_send_status_presets'),
    path('list/<int:pk>/comments/', views.list_comment_thread, name='list_comment_thread'),
    path('messages/', views.messaging_inbox, name='messaging_inbox'),
    path('messages/<int:user_id>/', views.messaging_thread, name='messaging_thread'),
    path('messages/unread-count/', views.message_unread_count, name='message_unread_count'),
    path('logout/', views.user_logout, name='user_logout'),
]
# Media files (profile pictures, pathway images, etc.)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # Production: Django serves media so profile pictures and uploads are visible on live
    media_prefix = settings.MEDIA_URL.strip('/')
    if media_prefix:
        urlpatterns += [
            path(media_prefix + '/<path:path>', static_serve, {'document_root': settings.MEDIA_ROOT}),
        ]