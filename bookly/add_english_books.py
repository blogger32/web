import os
import django

# Налаштування Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookly.settings')
django.setup()

from main.models import Book
from django.contrib.auth import get_user_model

User = get_user_model()
author_user = User.objects.first()

if not author_user:
    print("❌ Помилка: Немає користувачів. Створіть superuser!")
    exit()

print("------------------------------------------------")
print("🔄 Очищення старих англійських книг...")

# 1. ВИДАЛЯЄМО всі книги, де мова = 'en'
deleted_count, _ = Book.objects.filter(language='en').delete()
print(f"🗑️ Видалено {deleted_count} старих книг.")

print("------------------------------------------------")
print(f"📚 Додавання нових книг від імені: {author_user.username}")

# 2. Список нових книг
books_data = [
    {
        "title": "The Adventures of Robin Hood",
        "author_name": "Howard Pyle",
        "description": "In the depths of Sherwood Forest, Robin Hood and his band of Merry Men fight against the injustice of the Sheriff of Nottingham. A classic tale of heroism, archery, and stealing from the rich to give to the poor.",
        "genre": "Adventure",
        "language": "en",
        "daily_price": 4.50,
        "monthly_price": 10.00,
        "total_pages": 296,
        # Тимчасові обкладинки з інтернету (щоб було гарно)
        "cover_url": "https://m.media-amazon.com/images/I/91J-d9b8XIL._AC_UF1000,1000_QL80_.jpg",
        "pdf_path": "/static/main/pdfs/robin_hood.pdf"
    },
    {
        "title": "Pirates of the Caribbean: The Curse of the Black Pearl",
        "author_name": "Irene Trimble",
        "description": "Jack Sparrow, a roguish pirate, and Will Turner, a blacksmith, team up to rescue Elizabeth Swann from the cursed crew of the Black Pearl, led by the menacing Captain Barbossa.",
        "genre": "Fantasy",
        "language": "en",
        "daily_price": 6.00,
        "monthly_price": 14.00,
        "total_pages": 245,
        "cover_url": "https://m.media-amazon.com/images/I/51wXwEecC0L.jpg",
        "pdf_path": "/static/main/pdfs/pirates.pdf"
    }
]

for data in books_data:
    Book.objects.create(
        author=author_user,
        **data
    )
    print(f"✅ Додано: {data['title']}")

print("------------------------------------------------")
print("🎉 Готово! Перевірте розділ 'English Learning -> Books'")