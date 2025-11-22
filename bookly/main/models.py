import uuid
from django.db import models
# Імпортуємо вбудовану модель User
from django.contrib.auth.models import AbstractUser


# Розширюємо стандартну модель User
class User(AbstractUser):
    """
    Розширена модель користувача.
    Django автоматично обробляє email, name (first_name, last_name), password.
    Ми додаємо лише кастомні поля.
    """
    picture = models.URLField(max_length=500, null=True, blank=True)
    is_author = models.BooleanField(default=False)

    # Ми не додаємо 'created_at', оскільки Django має 'date_joined'
    # Ми не додаємо 'password_hash', оскільки Django керує цим сам
    # Ми не додаємо 'id', оскільки Django має авто-id, або ми можемо використовувати 'username' / 'email'

    def __str__(self):
        return self.email


class Book(models.Model):
    """
    Модель для книги.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)

    # Зв'язок з автором (користувачем)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="books")
    author_name = models.CharField(max_length=255)  # Зберігаємо ім'я для простоти

    description = models.TextField()
    genre = models.CharField(max_length=100, db_index=True)  # db_index для швидкого пошуку/фільтрації
    cover_url = models.URLField(max_length=500)

    # Ми не зберігаємо pdf_path в базі, краще використовувати FileField,
    # але для простоти перенесення вашої логіки, залишимо URL або шлях
    pdf_path = models.CharField(max_length=1000)

    total_pages = models.IntegerField()
    daily_price = models.DecimalField(max_digits=6, decimal_places=2)
    monthly_price = models.DecimalField(max_digits=8, decimal_places=2)

    # Поля, які будуть оновлюватися
    rating = models.FloatField(default=0.0)
    rentals_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)  # auto_now_add=True автоматично ставить час створення

    def __str__(self):
        return self.title


class Rental(models.Model):
    """
    Модель для оренди книги.
    """
    RENTAL_TYPE_CHOICES = [
        ('daily', 'Щоденна'),
        ('monthly', 'Щомісячна'),
    ]
    STATUS_CHOICES = [
        ('active', 'Активна'),
        ('completed', 'Завершена'),
        ('expired', 'Протермінована'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rentals")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="rentals")

    rental_type = models.CharField(max_length=10, choices=RENTAL_TYPE_CHOICES)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()  # Це поле має бути розраховане у views.py
    price_paid = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.book.title}"


class ReadingProgress(models.Model):
    """
    Модель для збереження прогресу читання.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="progress")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="progress")
    rental = models.OneToOneField(Rental, on_delete=models.CASCADE,
                                  related_name="progress")  # OneToOne, бо в однієї оренди - один прогрес

    current_page = models.IntegerField(default=1)
    total_pages = models.IntegerField()  # Дублюємо з книги для зручності
    last_read_at = models.DateTimeField(auto_now=True)  # auto_now=True оновлює час при кожному збереженні

    class Meta:
        # Унікальний індекс, щоб користувач не мав двох прогресів для однієї книги
        unique_together = ('user', 'book', 'rental')

    def __str__(self):
        return f"Progress for {self.user.email} on {self.book.title}"


class Favorite(models.Model):
    """
    Модель для обраних книг користувача.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="favorites")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Користувач може додати книгу в обране лише один раз
        unique_together = ('user', 'book')

    def __str__(self):
        return f"{self.user.email} likes {self.book.title}"