from PIL import Image
from django.core.exceptions import ValidationError
from django import forms
from .models import Group
from taggit.models import Tag

# class ManageGroupForm(forms.Form):
#     model = Group
#     fields = ['']

class JoinGroupForm(forms.Form):
    code = forms.CharField(
        max_length=50,
        label='Enter invite code',
        widget=forms.TextInput(attrs={'placeholder': 'Group invite code'})
    )

    def clean_code(self):
        code = self.cleaned_data['code'].strip()
        try:
            group = Group.objects.get(code=code)
        except Group.DoesNotExist:
            raise ValidationError('Invalid invite code.')
        self.cleaned_data['group'] = group
        return code

class GroupCreateForm(forms.ModelForm):
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = Group
        fields = ['name', 'logo', 'tags', 'about', 'status']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Group name'}),
            'about': forms.Textarea(attrs={'placeholder': 'smth about your group'})
        }

    def save(self, commit=True):
        instance = super().save(commit=False)

        if commit:
            instance.save()
            # только после save можно обращаться к tags
            if 'tags' in self.cleaned_data:
                instance.tags.set(self.cleaned_data['tags'])

        return instance

    def clean_logo(self):
        logo = self.cleaned_data.get('logo')
        if not logo:
            return logo

        valid_extensions = ['jpeg', 'jpg', 'png', 'gif']
        ext = logo.name.rsplit('.', 1)[-1].lower()

        if ext not in valid_extensions:
            raise ValidationError('Allowed file types: jpeg, jpg, png, gif.')

        max_size_mb = 5
        if logo.size > max_size_mb * 1024 * 1024:
            raise ValidationError(f'Max file size is {max_size_mb}MB.')

        try:
            image = Image.open(logo)
            width, height = image.size
        except Exception:
            raise ValidationError('Uploaded file is not a valid image.')

        min_dimension = 420
        if width < min_dimension or height < min_dimension:
            raise ValidationError(
                f'Image must be at least {min_dimension}x{min_dimension} pixels.'
            )

        return logo
