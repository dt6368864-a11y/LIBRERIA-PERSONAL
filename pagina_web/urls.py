from django.urls import path
from . import views

urlpatterns = [
    # path('', views.home, name='home'),
    path('registro/', views.registro_usuario, name='registro'),
    path('login/', views.iniciar_sesion, name='login'),
    path('logout/', views.cerrar_sesion, name='logout'),

    path('dashboard/', views.dashboard, name='dashboard'),
    # path('libros/', views.listar_libros, name='listar_libros'),


    path('libro/añadir/', views.añadir_libro, name='añadir_libro'),
    path('libro/editar/<str:libro_id>/', views.editar_libro, name='editar_libro'),
    path('libro/eliminar/<str:libro_id>/', views.eliminar_libro, name='eliminar_libro'),
]