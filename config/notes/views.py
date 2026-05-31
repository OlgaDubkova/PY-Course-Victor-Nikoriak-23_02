from django.shortcuts import render, get_object_or_404, redirect
from .models import Note
from .forms import NoteForm


# 1. Створення нотатки
def note_create(request):
    if request.method == "POST":
        form = NoteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('note_create')  # Або на список нотаток, коли створиш
    else:
        form = NoteForm()

    notes = Note.objects.all()  # Передамо список усіх нотаток, щоб бачити результат
    return render(request, 'notes/note_form.html', {'form': form, 'notes': notes})


# 2. Деталі + Редагування
def note_detail_edit(request, pk):
    note = get_object_or_404(Note, pk=pk)

    if request.method == "POST":
        form = NoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            return redirect('note_detail_edit', pk=note.pk)
    else:
        form = NoteForm(instance=note)

    return render(request, 'notes/note_detail.html', {'form': form, 'note': note})


# 3. Видалення
def note_delete(request, pk):
    note = get_object_or_404(Note, pk=pk)
    if request.method == "POST":
        note.delete()
        return redirect('note_create')  # Повертаємося на головну сторінку створення
    return render(request, 'notes/note_confirm_delete.html', {'note': note})