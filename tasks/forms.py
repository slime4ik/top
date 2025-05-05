from django import forms
from .models import Task, SubTask, Comment
from django.db.models import Q
from groups.models import Group

class TaskForm(forms.ModelForm):
    files = forms.FileField(
        required=False,
        label="Вложение (один файл)"
    )

    class Meta:
        model = Task
        fields = ['title', 'group', 'description']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['group'].queryset = Group.objects.filter(
                Q(creator=user) | Q(admins=user)
            ).distinct()

class SubTaskForm(forms.ModelForm):
    files = forms.FileField(
        required=False,
        label="put 1 file here"
    )
    class Meta:
        model = SubTask
        fields = ['title']
        widgets = {
            'title': forms.Textarea(attrs={'placeholder': 'what a subtask?'}),
        }
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)  # извлекаем user
        super().__init__(*args, **kwargs)

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text', 'image']
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Введите комментарий...',
                'style': 'resize: none;',
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
            }),
        }
        labels = {
            'text': '',
            'image': 'Картинка (необязательно)',
        }
