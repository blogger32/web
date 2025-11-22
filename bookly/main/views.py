from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import User, Book, Rental, Favorite, ReadingProgress
from datetime import datetime, timedelta, timezone
import json  # Потрібен для оновлення прогресу


# --- 1. Сторінки (GET-запити) ---

def landing_page(request):
    """
    Показує головну сторінку. Якщо користувач вже увійшов,
    перенаправляє його на дашборд.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    # Ми створимо 'main/landing.html' пізніше
    return render(request, 'main/landing.html')


@login_required  # Захищає сторінку від неавторизованих користувачів
def dashboard(request):
    """
    Показує головний дашборд користувача.
    """
    # Отримуємо книги, які користувач зараз читає
    currently_reading = Rental.objects.filter(
        user=request.user,
        status='active',
        end_date__gte=datetime.now(timezone.utc)
    ).select_related('book', 'progress')  # select_related оптимізує запит

    # Отримуємо рекомендовані книги (поки що просто останні)
    recommended_books = Book.objects.all().order_by('-created_at')[:10]

    # Отримуємо жанри для іншої каруселі
    genres = Book.objects.values_list('genre', flat=True).distinct()[:3]

    context = {
        'currently_reading': currently_reading,
        'recommended_books': recommended_books,
        'genres': genres
    }
    return render(request, 'main/dashboard.html', context)


@login_required
def catalog(request):
    """
    Показує каталог книг з фільтрацією та пошуком.
    """
    books = Book.objects.all()
    genres = Book.objects.values_list('genre', flat=True).distinct()

    # Обробка пошуку (з <form GET>)
    search_query = request.GET.get('search')
    if search_query:
        books = books.filter(
            Q(title__icontains=search_query) |
            Q(author_name__icontains=search_query)
        )

    # Обробка фільтру за жанром
    genre_query = request.GET.get('genre')
    if genre_query:
        books = books.filter(genre=genre_query)

    context = {
        'books': books,
        'genres': genres,
        'search_query': search_query,  # Щоб показати у полі пошуку
    }
    return render(request, 'main/catalog.html', context)


@login_required
def book_details(request, book_id):
    """
    Показує детальну сторінку однієї книги.
    """
    book = get_object_or_404(Book, id=book_id)
    is_favorite = Favorite.objects.filter(user=request.user, book=book).exists()

    context = {
        'book': book,
        'is_favorite': is_favorite
    }
    return render(request, 'main/book_details.html', context)


@login_required
def reader(request, rental_id):
    """
    Показує сторінку "читалки".
    """
    # Переконуємося, що оренда належить цьому користувачу
    rental = get_object_or_404(Rental, id=rental_id, user=request.user)

    # Знаходимо прогрес для цієї оренди
    progress = get_object_or_404(ReadingProgress, rental=rental)

    context = {
        'rental': rental,
        'progress': progress,
        'book': rental.book
    }
    return render(request, 'main/reader.html', context)


# --- 2. Автентифікація (GET + POST-запити) ---

def register_view(request):
    """
    Обробляє реєстрацію користувача.
    """
    if request.method == 'POST':
        # Отримуємо дані з HTML-форми
        name = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Перевірки
        if not all([name, email, password]):
            messages.error(request, 'Будь ласка, заповніть усі поля.')
            return redirect('register')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Користувач з таким email вже існує.')
            return redirect('register')

        # Створюємо користувача. Django автоматично хешує пароль.
        # Використовуємо email як username для входу
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=name  # 'name' йде у 'first_name'
        )

        # Автоматично входимо в систему
        login(request, user)
        messages.success(request, f'Вітаємо, {name}! Реєстрація успішна.')
        return redirect('dashboard')  # Перенаправляємо на дашборд

    return render(request, 'main/register.html')  # Повертаємо сторінку реєстрації


def login_view(request):
    """
    Обробляє вхід користувача.
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Перевіряємо, чи правильні дані
        # Використовуємо email як username
        user = authenticate(request, username=email, password=password)

        if user is not None:
            # Дані правильні, входимо
            login(request, user)
            return redirect('dashboard')
        else:
            # Дані неправильні
            messages.error(request, 'Неправильний email або пароль.')
            return redirect('login')

    return render(request, 'main/login.html')  # Повертаємо сторінку входу


@login_required
def logout_view(request):
    """
    Обробляє вихід користувача.
    """
    logout(request)
    messages.info(request, 'Ви вийшли з системи.')
    return redirect('landing_page')  # Повертаємо на головну


# --- 3. Функції (тільки POST-запити) ---

@login_required
def create_rental(request):
    """
    Створює нову оренду (очікує POST-запит з book_details).
    """
    if request.method == 'POST':
        book_id = request.POST.get('book_id')
        rental_type = request.POST.get('rental_type')

        book = get_object_or_404(Book, id=book_id)
        user = request.user

        # 1. Створюємо оренду
        if rental_type == 'daily':
            end_date = datetime.now(timezone.utc) + timedelta(days=1)
            price = book.daily_price
        else:
            end_date = datetime.now(timezone.utc) + timedelta(days=30)
            price = book.monthly_price

        rental = Rental.objects.create(
            user=user,
            book=book,
            rental_type=rental_type,
            end_date=end_date,
            price_paid=price
        )

        # 2. Створюємо прогрес читання
        ReadingProgress.objects.create(
            user=user,
            book=book,
            rental=rental,
            total_pages=book.total_pages
        )

        # 3. Оновлюємо лічильник книги
        book.rentals_count += 1
        book.save()

        messages.success(request, 'Книгу успішно орендовано!')
        return redirect('reader', rental_id=rental.id)  # Переходимо до читалки

    return redirect('catalog')  # Якщо не POST, повертаємо в каталог


@login_required
def toggle_favorite(request):
    """
    Додає або видаляє книгу з обраного.
    """
    if request.method == 'POST':
        book_id = request.POST.get('book_id')
        book = get_object_or_404(Book, id=book_id)

        # get_or_create: намагається знайти, і якщо не знаходить - створює
        fav, created = Favorite.objects.get_or_create(user=request.user, book=book)

        if created:
            messages.success(request, 'Додано в улюблене.')
        else:
            # Якщо не 'created', значить 'get' - книга вже була, видаляємо
            fav.delete()
            messages.info(request, 'Видалено з улюбленого.')

        # Повертаємося на сторінку, з якої прийшли
        return redirect(request.META.get('HTTP_REFERER', 'book_details', kwargs={'book_id': book.id}))

    return redirect('catalog')


@login_required
def update_progress(request, rental_id):
    """
    Оновлює сторінку, на якій зупинився користувач.
    Ця функція очікує JS (AJAX) запит з `reader.html`.
    """
    if request.method == 'POST':
        try:
            # Отримуємо дані з JS
            data = json.loads(request.body)
            current_page = int(data.get('current_page'))

            # Оновлюємо прогрес, переконуючись, що він належить юзеру
            ReadingProgress.objects.filter(
                rental_id=rental_id,
                user=request.user
            ).update(
                current_page=current_page,
                last_read_at=datetime.now(timezone.utc)
            )
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

# Тут буде логіка для кабінету автора (створимо пізніше)