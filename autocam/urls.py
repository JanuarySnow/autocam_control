from django.urls import path
from . import views

app_name = 'autocam'

urlpatterns = [
    path('<int:server_id>/login/', views.session_login, name='session_login'),
    path('', views.autocam_control, name='control'),
    path('<int:server_id>/', views.autocam_control, name='control_server'),

    path('api/<int:server_id>/focus/', views.focus_car, name='api_focus_car'),
    path('api/<int:server_id>/camera/', views.set_camera, name='api_set_camera'),
    path('api/<int:server_id>/clear_override/', views.clear_override, name='api_clear_override'),
    path('api/<int:server_id>/cars/', views.get_cars_json, name='api_get_cars'),

    path('api/register/', views.register_session, name='api_register'),
    path('api/<int:server_id>/command/', views.get_command, name='api_get_command'),
    path('api/<int:server_id>/update/', views.update_car_state, name='api_update_state'),
    path('api/<int:server_id>/deregister/', views.deregister_session, name='api_deregister'),
]
