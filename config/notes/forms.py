from django import forms
from .models import Note

class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ['title', 'text', 'reminder', 'category']
        # Додамо гарні віджети для відображення в браузері
        widgets = {
            'reminder': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }