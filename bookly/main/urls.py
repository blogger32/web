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
    path('create-checkout-session/', views.create_checkout_session, name='create_checkout_session'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('progress/update/<uuid:rental_id>/', views.update_progress, name='update_progress'),
    # ... інші url
    path('english/', views.english_catalog, name='english_catalog'),
    path('dictionary/', views.dictionary_view, name='dictionary'),
    path('learn/', views.learn_words, name='learn_words'),
    path('api/get_question/', views.get_learn_question_api, name='get_learn_question'),
    path('api/define_word/', views.get_word_definition, name='define_word'),
    path('api/add_word/', views.add_word_api, name='add_word_api'),
    path('dictionary/', views.dictionary_view, name='dictionary'),
    path('cabinet/', views.author_dashboard, name='author_dashboard'),
    path('cabinet/add/', views.add_book, name='add_book'),
    path('bookmarks/', views.bookmarks, name='bookmarks'),
    path('profile/', views.profile_view, name='profile'),
    path('premium/', views.premium_page, name='premium_page'),
    path('premium/buy/', views.create_premium_checkout, name='create_premium_checkout'),
    path('premium/success/', views.premium_success, name='premium_success'),
]