from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import User, Book, Rental, Favorite, ReadingProgress, UserWord
# ВИПРАВЛЕНО ІМПОРТ: прибираємо timezone звідси, щоб не було конфлікту
from datetime import datetime, timedelta
import json
import random
from django.core.paginator import Paginator
import os
import re
from django.conf import settings
import requests
from bs4 import BeautifulSoup
import deepl
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .forms import BookForm
import stripe
from django.urls import reverse
# ВИПРАВЛЕНО: Використовуємо цей timezone для всього часу
from django.utils import timezone
from .models import UserProfile, DailyUsage


# Ваш API ключ
DEEPL_API_KEY = "fca85a96-efe6-41f3-ba01-73be29067401:fx"

# Налаштовуємо ключ Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


def check_limits(user, action_type):
    """
    Перевіряє, чи може користувач виконати дію.
    action_type: 'translation' або 'dictionary'
    Повертає: (True, "") або (False, "Повідомлення про ліміт")
    """
    # 1. Перевіряємо Premium
    profile, _ = UserProfile.objects.get_or_create(user=user)

    if profile.is_premium:
        # Якщо преміум ще діє - безліміт
        if profile.premium_end_date and profile.premium_end_date > timezone.now():
            return True, "Premium"
        else:
            # Преміум закінчився
            profile.is_premium = False
            profile.save()

    # 2. Перевіряємо ліміти для Free
    today = timezone.now().date()
    usage, _ = DailyUsage.objects.get_or_create(user=user, date=today)

    LIMITS = {
        'translation': 50,  # 50 слів на день
        'dictionary': 20  # 20 слів у словник
    }

    if action_type == 'translation':
        if usage.translations_count >= LIMITS['translation']:
            return False, "Вичерпано ліміт перекладів на сьогодні (50 слів)."
        usage.translations_count += 1

    elif action_type == 'dictionary':
        if usage.words_added_count >= LIMITS['dictionary']:
            return False, "Вичерпано ліміт додавання слів (20 слів)."
        usage.words_added_count += 1

    usage.save()
    return True, "OK"

@login_required
def profile_view(request):
    """
    Сторінка профілю користувача.
    Містить: редагування даних, статистику читання та історію.
    """
    # --- 1. Обробка зміни даних (Ім'я, Прізвище) ---
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')

        user = request.user
        user.first_name = first_name
        user.last_name = last_name
        user.save()
        messages.success(request, 'Профіль оновлено!')
        return redirect('profile')

    # --- 2. Збір статистики ---

    # Кількість орендованих книг
    rentals_count = Rental.objects.filter(user=request.user).count()

    # Загальна кількість прочитаних сторінок (сума current_page усіх книг)
    total_pages_data = ReadingProgress.objects.filter(user=request.user).aggregate(Sum('current_page'))
    total_pages = total_pages_data['current_page__sum'] or 0

    # Кількість слів у словнику
    words_count = UserWord.objects.filter(user=request.user).count()

    # --- 3. Історія оренд (останні 5) ---
    recent_rentals = Rental.objects.filter(user=request.user).select_related('book').order_by('-start_date')[:5]

    context = {
        'rentals_count': rentals_count,
        'total_pages': total_pages,
        'words_count': words_count,
        'recent_rentals': recent_rentals
    }
    return render(request, 'main/profile.html', context)

@login_required
def bookmarks(request):
    """
    Сторінка зі списком книг, які читає користувач.
    """
    reading_list = ReadingProgress.objects.filter(
        user=request.user,
        rental__status='active',
        rental__end_date__gte=timezone.now() # ВИПРАВЛЕНО
    ).select_related('book', 'rental').order_by('-last_read_at')

    return render(request, 'main/bookmarks.html', {'reading_list': reading_list})

@login_required
def create_checkout_session(request):
    """
    Створює сесію оплати в Stripe.
    """
    if request.method == 'POST':
        book_id = request.POST.get('book_id')
        rental_type = request.POST.get('rental_type')
        book = get_object_or_404(Book, id=book_id)

        if rental_type == 'daily':
            price_amount = book.daily_price
            product_name = f"Оренда книги '{book.title}' (1 день)"
        else:
            price_amount = book.monthly_price
            product_name = f"Оренда книги '{book.title}' (30 днів)"

        unit_amount = int(price_amount * 100)

        success_url = request.build_absolute_uri(reverse('payment_success')) + '?session_id={CHECKOUT_SESSION_ID}'
        cancel_url = request.build_absolute_uri(reverse('book_details', args=[book.id]))

        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': settings.STRIPE_CURRENCY,
                        'unit_amount': unit_amount,
                        'product_data': {
                            'name': product_name,
                            'images': [request.build_absolute_uri(book.cover_url)] if book.cover_url else [],
                        },
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'book_id': str(book.id),
                    'user_id': str(request.user.id),
                    'rental_type': rental_type,
                    'price_paid': str(price_amount)
                }
            )
            return redirect(checkout_session.url, code=303)

        except Exception as e:
            messages.error(request, f"Помилка Stripe: {str(e)}")
            return redirect('book_details', book_id=book.id)

    return redirect('catalog')


@login_required
def payment_success(request):
    """
    Обробка успішної оплати.
    """
    session_id = request.GET.get('session_id')

    if not session_id:
        return redirect('dashboard')

    try:
        session = stripe.checkout.Session.retrieve(session_id)

        if session.payment_status == 'paid':
            book_id = session.metadata['book_id']
            rental_type = session.metadata['rental_type']
            price_paid = session.metadata['price_paid']

            book = get_object_or_404(Book, id=book_id)

            # ВИПРАВЛЕНО: timezone.now()
            existing_rental = Rental.objects.filter(
                user=request.user,
                book=book,
                status='active',
                end_date__gte=timezone.now()
            ).exists()

            if not existing_rental:
                # ВИПРАВЛЕНО: timezone.now()
                if rental_type == 'daily':
                    end_date = timezone.now() + timedelta(days=1)
                else:
                    end_date = timezone.now() + timedelta(days=30)

                rental = Rental.objects.create(
                    user=request.user,
                    book=book,
                    rental_type=rental_type,
                    end_date=end_date,
                    price_paid=price_paid,
                    status='active'
                )

                ReadingProgress.objects.create(
                    user=request.user,
                    book=book,
                    rental=rental,
                    total_pages=book.total_pages
                )

                book.rentals_count += 1
                book.save()

                messages.success(request, f"Оплата успішна! Приємного читання '{book.title}'.")
                return redirect('reader', rental_id=rental.id)
            else:
                messages.info(request, "Ця книга вже доступна вам.")
                rental = Rental.objects.filter(user=request.user, book=book, status='active').first()
                return redirect('reader', rental_id=rental.id)
        else:
            messages.error(request, "Оплата не була завершена.")
            return redirect('dashboard')

    except Exception as e:
        messages.error(request, f"Помилка обробки оплати: {e}")
        return redirect('dashboard')


# --- КАБІНЕТ АВТОРА ---

@login_required
def author_dashboard(request):
    """Головна сторінка автора."""
    if not request.user.is_author:
        return render(request, 'main/author_promo.html')

    my_books = Book.objects.filter(author=request.user).order_by('-created_at')
    total_books = my_books.count()

    rentals = Rental.objects.filter(book__in=my_books)
    total_rentals = rentals.count()

    income_data = rentals.aggregate(Sum('price_paid'))
    total_income = income_data['price_paid__sum'] or 0.0
    top_book = my_books.order_by('-rentals_count').first()

    context = {
        'my_books': my_books,
        'total_books': total_books,
        'total_rentals': total_rentals,
        'total_income': total_income,
        'top_book': top_book
    }
    return render(request, 'main/author_dashboard.html', context)


@login_required
def add_book(request):
    """Створення нової книги."""
    if not request.user.is_author:
        return redirect('dashboard')

    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            book = form.save(commit=False)
            book.author = request.user
            book.author_name = request.user.first_name or request.user.email

            # 1. Текст
            text_file = request.FILES['text_file']
            file_name = f"{request.user.id}_{text_file.name.replace(' ', '_')}"
            save_path = f"main/books_text/{file_name}"

            full_save_path = os.path.join(settings.BASE_DIR, 'main', 'static', save_path)
            with open(full_save_path, 'wb+') as destination:
                for chunk in text_file.chunks():
                    destination.write(chunk)

            book.text_file_path = f"/static/{save_path}"

            # 2. Обкладинка
            if 'cover_image' in request.FILES:
                image = request.FILES['cover_image']
                img_name = f"{request.user.id}_{image.name.replace(' ', '_')}"
                img_save_path = f"main/imgs/{img_name}"

                full_img_path = os.path.join(settings.BASE_DIR, 'main', 'static', img_save_path)
                with open(full_img_path, 'wb+') as destination:
                    for chunk in image.chunks():
                        destination.write(chunk)

                book.cover_url = f"/static/{img_save_path}"
            else:
                book.cover_url = "/static/main/imgs/book_placeholder.png"

            book.pdf_path = ""
            book.rating = 0.0
            book.rentals_count = 0

            book.save()
            messages.success(request, f"Книга '{book.title}' успішно опублікована!")
            return redirect('author_dashboard')
    else:
        form = BookForm()

    return render(request, 'main/add_book.html', {'form': form})


# --- API METHODS (СЛОВНИК) ---

@login_required
def get_learn_question_api(request):
    user_words = list(UserWord.objects.filter(user=request.user))

    if len(user_words) < 4:
        return JsonResponse({'status': 'error', 'message': 'Not enough words'})

    target = random.choice(user_words)
    distractors = random.sample([w for w in user_words if w != target], 3)
    options_objects = distractors + [target]
    random.shuffle(options_objects)

    options_data = [
        {'id': w.id, 'translation': w.translation}
        for w in options_objects
    ]

    data = {
        'status': 'ok',
        'target': {
            'id': target.id,
            'word': target.word,
            'transcription': target.transcription or '',
            'part_of_speech': target.part_of_speech or ''
        },
        'options': options_data
    }
    return JsonResponse(data)

@login_required
def get_word_definition(request):
    """
    API для отримання перекладу.
    Тепер перевіряє денний ліміт (50 слів) для безкоштовних юзерів.
    """
    word = request.GET.get('word', '').strip().lower()

    if not word:
        return JsonResponse({'error': 'No word provided'}, status=400)

    # --- 1. ПЕРЕВІРКА ЛІМІТУ ---
    # Якщо ліміт вичерпано, повертаємо спеціальний прапорець is_limit_reached
    allowed, message = check_limits(request.user, 'translation')
    if not allowed:
        return JsonResponse({
            'translation': message,
            'is_limit_reached': True  # Це сигнал для JS показати вікно Premium
        })
    # ---------------------------

    data = {
        'word': word,
        'transcription': '',
        'part_of_speech': '',
        'translation': 'Переклад не знайдено'
    }

    # 1. Oxford Dictionary (Парсинг)
    try:
        oxford_url = f"https://www.oxfordlearnersdictionaries.com/definition/english/{word.replace(' ', '-')}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(oxford_url, headers=headers)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            pos_tag = soup.find('span', class_='pos')
            if pos_tag: data['part_of_speech'] = pos_tag.text
            phon_tag = soup.find('span', class_='phon')
            if phon_tag: data['transcription'] = phon_tag.text
    except Exception as e:
        print(f"Oxford error: {e}")

    # 2. DeepL API (Переклад)
    try:
        translator = deepl.Translator(DEEPL_API_KEY)
        result = translator.translate_text(word, source_lang="EN", target_lang="UK")
        data['translation'] = result.text
    except Exception as e:
        print(f"DeepL error: {e}")
        data['translation'] = "Помилка перекладу (API)"

    return JsonResponse(data)


@login_required
@require_POST
def add_word_api(request):
    """
    API для додавання слова у словник.
    Тепер перевіряє денний ліміт (20 слів) для безкоштовних юзерів.
    """
    # --- 1. ПЕРЕВІРКА ЛІМІТУ ---
    allowed, message = check_limits(request.user, 'dictionary')
    if not allowed:
        # Повертаємо 403 Forbidden з повідомленням про ліміт
        return JsonResponse({'status': 'error', 'message': message}, status=403)
    # ---------------------------

    try:
        data = json.loads(request.body)
        word_text = data.get('word')
        translation = data.get('translation')
        transcription = data.get('transcription', '')
        part_of_speech = data.get('part_of_speech', '')

        if not word_text or not translation:
            return JsonResponse({'status': 'error', 'message': 'Пусті дані'}, status=400)

        obj, created = UserWord.objects.get_or_create(
            user=request.user,
            word=word_text,
            defaults={
                'translation': translation,
                'transcription': transcription,
                'part_of_speech': part_of_speech
            }
        )

        if not created:
            return JsonResponse({'status': 'exists', 'message': 'Слово вже у словнику'})

        return JsonResponse({'status': 'ok', 'message': 'Слово додано!'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


# --- допоміжні функції ---

def load_and_format_text(file_path):
    if not file_path:
        return []

    current_app_dir = os.path.dirname(os.path.abspath(__file__))
    relative_path = file_path.lstrip('/')

    if relative_path.startswith('static/main/'):
        relative_path = relative_path.replace('static/main/', '')

    full_path = os.path.join(current_app_dir, 'static', 'main', relative_path)

    if not os.path.exists(full_path):
        return []

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            text = f.read()

        text = text.replace('\\', '')
        text = re.sub(r'\[\d+\]', '', text)
        text = re.sub(r'[\u200b\uFEFF]', '', text)

        paragraphs = text.split('\n')
        content_list = []

        for p in paragraphs:
            clean_p = p.strip()
            if not clean_p:
                continue

            is_header = (
                    len(clean_p) < 80 and
                    (clean_p.lower().startswith("chapter") or clean_p.isupper())
            )

            if is_header:
                html_block = f"""
                <div class='paragraph-row'>
                    <button class='tts-paragraph-btn' onclick='playParagraph(this)'>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon></svg>
                    </button>
                    <h3 class='book-chapter'>{clean_p}</h3>
                </div>
                """
                content_list.append(html_block)
            else:
                html_block = f"""
                <div class='paragraph-row'>
                    <button class='tts-paragraph-btn' onclick='playParagraph(this)'>
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon></svg>
                    </button>
                    <p class='book-text'>{clean_p}</p>
                </div>
                """
                content_list.append(html_block)

        return content_list

    except Exception as e:
        print(f"❌ Помилка: {e}")
        return []


# --- СТОРІНКИ ---

def landing_page(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'main/landing.html')


@login_required
def dashboard(request):
    """
    Головна сторінка.
    Відображає ТІЛЬКИ українські книги.
    Англійські книги знаходяться в окремому розділі 'english_catalog'.
    """

    # 1. Рекомендації: Шукаємо тільки книги з мовою 'uk' (Українська)
    # Якщо у вас в базі код мови 'ua', замініть 'uk' на 'ua'
    recommended_books = Book.objects.filter(language='uk').order_by('-created_at')[:10]

    # 2. Жанри: Показуємо жанри тільки з українських книг
    genres = Book.objects.filter(language='uk').values_list('genre', flat=True).distinct()[:3]

    context = {
        'recommended_books': recommended_books,
        'genres': genres
    }
    return render(request, 'main/dashboard.html', context)



@login_required
def catalog(request):
    books = Book.objects.all().order_by('-created_at')
    genres = Book.objects.values_list('genre', flat=True).distinct()

    search_query = request.GET.get('search', '').strip()
    search_type = request.GET.get('search_type', 'all')

    if search_query:
        if search_type == 'title':
            books = books.filter(title__icontains=search_query)
        elif search_type == 'author':
            books = books.filter(author_name__icontains=search_query)
        elif search_type == 'text':
            books = books.filter(
                Q(description__icontains=search_query) |
                Q(text_content__icontains=search_query)
            )
        else:
            books = books.filter(
                Q(title__icontains=search_query) |
                Q(author_name__icontains=search_query) |
                Q(description__icontains=search_query)
            )

    genre_query = request.GET.get('genre')
    if genre_query:
        books = books.filter(genre=genre_query)

    context = {
        'books': books,
        'genres': genres,
        'search_query': search_query,
        'search_type': search_type,
    }
    return render(request, 'main/catalog.html', context)


@login_required
def english_catalog(request):
    english_books = Book.objects.filter(language='en')
    genres = english_books.values_list('genre', flat=True).distinct()
    recommended = english_books.order_by('?')[:10]

    context = {
        'books': english_books,
        'genres': genres,
        'recommended_books': recommended,
    }
    return render(request, 'main/english_catalog.html', context)


@login_required
def book_details(request, book_id):
    book = get_object_or_404(Book, id=book_id)

    # ВИПРАВЛЕНО: timezone.now()
    active_rental = Rental.objects.filter(
        user=request.user,
        book=book,
        status='active',
        end_date__gte=timezone.now()
    ).first()

    if active_rental and request.GET.get('view_details') != 'true':
        return redirect('reader', rental_id=active_rental.id)

    is_favorite = Favorite.objects.filter(user=request.user, book=book).exists()

    context = {
        'book': book,
        'is_favorite': is_favorite,
        'active_rental': active_rental
    }
    return render(request, 'main/book_details.html', context)


@login_required
def reader(request, rental_id):
    """Сторінка читалки: виправлено розрахунок Total Pages"""
    rental = get_object_or_404(Rental, id=rental_id, user=request.user)
    progress = get_object_or_404(ReadingProgress, rental=rental)
    book = rental.book

    # 1. Завантажуємо текст
    content_list = []
    if book.text_file_path:
        content_list = load_and_format_text(book.text_file_path)

    if not content_list and book.text_content:
        content_list = book.text_content.split('\n')

    # 2. Пагінація
    page_obj = None
    if content_list:
        paginator = Paginator(content_list, 15)  # 15 абзаців на сторінку
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        # --- ЗБЕРЕЖЕННЯ ПРОГРЕСУ ---
        if page_obj:
            # 1. Оновлюємо поточну сторінку
            progress.current_page = page_obj.number

            # 2. ВАЖЛИВО: Оновлюємо ЗАГАЛЬНУ кількість сторінок на реальну (від пагінатора)
            # Це виправить ваші відсотки
            progress.total_pages = paginator.num_pages

            progress.last_read_at = timezone.now()
            progress.save()

    context = {
        'rental': rental,
        'progress': progress,  # Тепер тут правильний total_pages
        'book': book,
        'page_obj': page_obj
    }
    return render(request, 'main/reader.html', context)


@login_required
def dictionary_view(request):
    words = UserWord.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'main/dictionary.html', {'words': words})


@login_required
def learn_words(request):
    user_words = list(UserWord.objects.filter(user=request.user))

    if len(user_words) < 4:
        return render(request, 'main/learn_error.html', {
            'message': 'Додайте мінімум 4 слова в словник, щоб почати гру!'
        })

    correct_word = random.choice(user_words)
    distractors = random.sample([w for w in user_words if w != correct_word], 3)
    options = distractors + [correct_word]
    random.shuffle(options)

    if request.method == "POST":
        selected_id = request.POST.get('selected_id')
        correct_id = request.POST.get('correct_id')
        if selected_id == correct_id:
            return redirect('learn_words')

    return render(request, 'main/learn_words.html', {
        'target_word': correct_word,
        'options': options,
    })


# --- AUTH & ACTIONS ---

def register_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('password')

        if not all([name, email, password]):
            messages.error(request, 'Будь ласка, заповніть усі поля.')
            return redirect('register')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Користувач з таким email вже існує.')
            return redirect('register')

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=name
        )
        login(request, user)
        messages.success(request, f'Вітаємо, {name}! Реєстрація успішна.')
        return redirect('dashboard')

    return render(request, 'main/register.html')


def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Неправильний email або пароль.')
            return redirect('login')

    return render(request, 'main/login.html')


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'Ви вийшли з системи.')
    return redirect('landing_page')


@login_required
def toggle_favorite(request):
    if request.method == 'POST':
        book_id = request.POST.get('book_id')
        book = get_object_or_404(Book, id=book_id)
        fav, created = Favorite.objects.get_or_create(user=request.user, book=book)

        if created:
            messages.success(request, 'Додано в улюблене.')
        else:
            fav.delete()
            messages.info(request, 'Видалено з улюбленого.')

        return redirect(request.META.get('HTTP_REFERER', 'book_details', kwargs={'book_id': book.id}))
    return redirect('catalog')


@login_required
def update_progress(request, rental_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            current_page = int(data.get('current_page'))
            ReadingProgress.objects.filter(
                rental_id=rental_id,
                user=request.user
            ).update(
                current_page=current_page,
                last_read_at=timezone.now() # ВИПРАВЛЕНО
            )
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)


@login_required
def premium_page(request):
    """Сторінка порівняння тарифів (як на скріншоті)."""
    return render(request, 'main/premium.html')


@login_required
def create_premium_checkout(request):
    """Створення підписки Stripe ($2/місяць)."""
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'Bookly Premium',
                        'description': 'Безлімітний доступ до всіх функцій.',
                    },
                    'unit_amount': 200,  # 2.00 USD (в центах)
                    'recurring': {'interval': 'month'},  # ПІДПИСКА
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url=request.build_absolute_uri(reverse('premium_success')) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.build_absolute_uri(reverse('premium_page')),
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        messages.error(request, f"Помилка Stripe: {e}")
        return redirect('premium_page')


@login_required
def premium_success(request):
    """Активація преміуму після оплати."""
    session_id = request.GET.get('session_id')
    if not session_id: return redirect('dashboard')

    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == 'paid':
            profile, _ = UserProfile.objects.get_or_create(user=request.user)
            profile.is_premium = True
            profile.premium_end_date = timezone.now() + timedelta(days=30)
            profile.stripe_subscription_id = session.subscription
            profile.save()
            messages.success(request, "Premium успішно активовано! 🚀")
    except Exception as e:
        messages.error(request, "Щось пішло не так при активації.")

    return redirect('dashboard')