from django.urls import path
from . import views

urlpatterns = [
    # --- Сторінки ---
    path('', views.landing_page, name='landing_page'),  # bookly.com/
    path('dashboard/', views.dashboard, name='dashboard'),  # bookly.com/dashboard/
    path('catalog/', views.catalog, name='catalog'),  # bookly.com/catalog/
    path('book/<uuid:book_id>/', views.book_details, name='book_details'),  # bookly.com/book/uuid...
    path('reader/<uuid:rental_id>/', views.reader, name='reader'),  # bookly.com/reader/uuid...

    # --- Автентифікація ---
    path('register/', views.register_view, name='register'),  # bookly.com/register/
    path('login/', views.login_view, name='login'),  # bookly.com/login/
    path('logout/', views.logout_view, name='logout'),  # bookly.com/logout/

    # --- Функції (POST-запити) ---
    path('rent/', views.create_rental, name='create_rental'),
    path('favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('progress/update/<uuid:rental_id>/', views.update_progress, name='update_progress'),
]