from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100, default='Загальна', verbose_name="Назва категорії")

    def __str__(self):
        return self.name

class Note(models.Model):
    title = models.CharField(max_length=200, verbose_name="Назва")
    text = models.TextField(verbose_name="Текст нотатки")
    reminder = models.DateTimeField(null=True, blank=True, verbose_name="Нагадування")
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Категорія")

    def __str__(self):
        return self.title