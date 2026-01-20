from django import forms
from .models import Book


class BookForm(forms.ModelForm):
    cover_image = forms.ImageField(label="Обкладинка книги", required=False)
    text_file = forms.FileField(label="Текстовий файл (.txt)", required=True)

    # Робимо genre звичайним текстовим полем, але ховаємо його (HiddenInput).
    # Ми заповнимо його через JS перед відправкою.
    genre = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Book
        fields = ['title', 'description', 'genre', 'language', 'total_pages', 'daily_price', 'monthly_price']
        labels = {
            'title': 'Назва книги',
            'description': 'Опис',
            'language': 'Мова',
            'total_pages': 'Кількість сторінок',
            'daily_price': 'Ціна за день (грн)',
            'monthly_price': 'Ціна за місяць (грн)',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }