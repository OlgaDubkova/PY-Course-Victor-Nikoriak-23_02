from django.test import TestCase
from django.urls import reverse
from .models import Note, Category


class NoteTests(TestCase):

    def setUp(self):
        """Цей метод виконується перед кожним тестом. Створимо базову категорію."""
        self.category = Category.objects.create(name="Тестова Категорія")
        # Також створимо одну базову нотатку для тестів редагування
        self.note = Note.objects.create(
            title="Стара назва",
            text="Старий текст нотатки",
            category=self.category
        )

    def test_note_create_view_get(self):
        """Перевіряємо, чи відкривається сторінка створення нотатки (GET-запит)"""
        response = self.client.get(reverse('note_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'notes/note_form.html')

    def test_note_create_view_post(self):
        """Перевіряємо, чи успішно створюється нотатка через форму (POST-запит)"""
        data = {
            'title': 'Нова тестова нотатка',
            'text': 'Текст нової тестової нотатки',
            'category': self.category.id,
            'reminder': ''  # залишаємо порожнім, бо воно необов'язкове
        }
        # Відправляємо дані на сторінку створення
        response = self.client.post(reverse('note_create'), data)

        # Після успішного створення view робить редірект (status code 302)
        self.assertEqual(response.status_code, 302)

        # Перевіряємо, чи дійсно нотатка з'явилася в базі даних
        self.assertTrue(Note.objects.filter(title='Нова тестова нотатка').exists())

    def test_note_edit_view_post(self):
        """Перевіряємо зміну (редагування) існуючої нотатки"""
        data = {
            'title': 'Оновлена назва',
            'text': 'Оновлений текст нотатки',
            'category': self.category.id,
            'reminder': ''
        }
        # Відправляємо POST-запит на адресу редагування нашої тестової нотатки
        response = self.client.post(reverse('note_detail_edit', kwargs={'pk': self.note.pk}), data)

        # Перевіряємо редірект
        self.assertEqual(response.status_code, 302)

        # Оновлюємо дані об'єкта з бази даних
        self.note.refresh_from_db()

        # Перевіряємо, чи змінилися поля в базі даних
        self.assertEqual(self.note.title, 'Оновлена назва')
        self.assertEqual(self.note.text, 'Оновлений текст нотатки')