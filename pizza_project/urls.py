"""
URL configuration for pizza_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
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
# orders/urls.py
from django.urls import path
from orders import views
from django.contrib import admin

urlpatterns = [
    path('', views.home, name='home'),  # Home page at the root URL
    path('admin/', admin.site.urls),
    path('login/', views.user_login, name='login'),
    path('register/', views.register, name='register'),
    path('place_order/', views.place_order, name='place_order'),
    path('order_confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('order_history/', views.order_history, name='order_history'),
    path('cancel_order/<int:order_id>/', views.cancel_order, name='cancel_order'),
    path('restaurant_monitoring/', views.restaurant_monitoring, name='restaurant_monitoring'),
    path('earnings_report/', views.earnings_report, name='earnings_report'),
]

