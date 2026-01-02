import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# Список файлів, які ми прописали в initial_data.json
books_files = [
    ("harry_potter_1.pdf", "Harry Potter and the Philosopher's Stone"),
    ("kobzar.pdf", "Kobzar - Taras Shevchenko"),
    ("dune.pdf", "Dune - Frank Herbert"),
    ("1984.pdf", "1984 - George Orwell"),
    ("sherlock.pdf", "The Adventures of Sherlock Holmes"),
    ("shining.pdf", "The Shining - Stephen King"),
    ("thinking_fast.pdf", "Thinking, Fast and Slow"),
    ("tini.pdf", "Shadows of Forgotten Ancestors"),
    ("sapiens.pdf", "Sapiens: A Brief History of Humankind"),
    ("little_prince.pdf", "The Little Prince"),
    ("witcher.pdf", "The Witcher: The Last Wish"),
    ("rich_dad.pdf", "Rich Dad Poor Dad"),
    ("pride.pdf", "Pride and Prejudice"),
    ("lotr.pdf", "The Lord of the Rings"),
    ("kaydash.pdf", "Kaydasheva simya")
]

# Шлях, куди зберігати (згідно з налаштуваннями Django static)
output_dir = os.path.join('main', 'static', 'books')

# Створюємо папку, якщо її немає
if not os.path.exists(output_dir):
    os.makedirs(output_dir)
    print(f"Created directory: {output_dir}")


def create_dummy_pdf(filename, title):
    filepath = os.path.join(output_dir, filename)
    c = canvas.Canvas(filepath, pagesize=A4)

    # Малюємо простий текст на сторінці
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(300, 700, "Bookly Placeholder")

    c.setFont("Helvetica", 18)
    c.drawCentredString(300, 600, title)

    c.setFont("Helvetica-Oblique", 12)
    c.drawCentredString(300, 500, "This is a dummy file for testing purposes.")
    c.drawCentredString(300, 480, "Replace this file with the real book content.")

    # Створюємо кілька сторінок, щоб протестувати гортання
    c.showPage()  # Кінець 1-ї сторінки

    c.setFont("Helvetica", 40)
    c.drawCentredString(300, 400, "Page 2")
    c.showPage()  # Кінець 2-ї сторінки

    c.setFont("Helvetica", 40)
    c.drawCentredString(300, 400, "Page 3")
    c.showPage()  # Кінець 3-ї сторінки

    c.save()
    print(f"Generated: {filename}")


if __name__ == "__main__":
    print("Starting PDF generation...")
    for filename, title in books_files:
        create_dummy_pdf(filename, title)
    print("Done! All books created.")