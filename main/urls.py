from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf.urls.static import static
from django.conf import settings
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('browse/', views.browse, name='browse'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html', redirect_authenticated_user=True), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/food/new/", views.food_create, name="food_create"),
    path("dashboard/food/<int:pk>/edit/", views.food_edit, name="food_edit"),
    path("dashboard/food/<int:pk>/delete/", views.food_delete, name="food_delete"),
    path("food/<int:pk>/", views.food_detail, name="food_detail"),
    path("food/<int:pk>/checkout/", views.checkout, name="checkout"),
    path("orders/", views.my_orders, name="my_orders"),
    path("orders/<int:pk>/success/", views.order_success, name="order_success"),
    path("orders/<int:pk>/cancel/", views.order_cancel, name="order_cancel"),
    path("orders/<int:pk>/picked-up/", views.order_mark_picked_up, name="order_mark_picked_up"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)