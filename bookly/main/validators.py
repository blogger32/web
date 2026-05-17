# main/validators.py
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

class ComplexPasswordValidator:
    """
    Валідатор, який перевіряє, чи містить пароль:
    - Хоча б одну цифру
    - Хоча б одну велику або малу літеру
    - Хоча б один спеціальний символ (@, #, $, %, etc.)
    """

    def validate(self, password, user=None):
        # Перевірка на наявність цифр
        if not re.search(r'\d', password):
            raise ValidationError(
                _("Пароль повинен містити хоча б одну цифру (0-9)."),
                code='password_no_number',
            )

        # Перевірка на наявність літер
        if not re.search(r'[a-zA-Z]', password):
            raise ValidationError(
                _("Пароль повинен містити хоча б одну літеру."),
                code='password_no_letter',
            )

        # Перевірка на наявність спеціальних символів
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError(
                _("Пароль повинен містити хоча б один спеціальний символ (!@#$%^&* тощо)."),
                code='password_no_symbol',
            )

    def get_help_text(self):
        return _(
            "Ваш пароль повинен містити хоча б одну цифру, одну літеру "
            "та один спеціальний символ."
        )