from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import FamilyProfile, MarketList, Notice, Message, MarketListComment


class FamilyRegistrationForm(UserCreationForm):
    full_name = forms.CharField(
        max_length=200, required=False, label='পূর্ণ নাম',
        help_text='প্রোফাইলে এই নাম সংরক্ষিত হবে।'
    )
    phone = forms.CharField(max_length=20, label='ফোন নম্বর')
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), label='ঠিকানা')

    class Meta:
        model = User
        fields = ['username', 'full_name', 'phone', 'address', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            FamilyProfile.objects.create(
                user=user,
                full_name=self.cleaned_data.get('full_name', '').strip(),
                phone=self.cleaned_data['phone'],
                address=self.cleaned_data['address']
            )
        return user


class MarketListForm(forms.ModelForm):
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'আপনার বাজারের লিস্ট এখানে লিখুন... (প্রতিটি আইটেম নতুন লাইনে)'
        }),
        label=''
    )

    class Meta:
        model = MarketList
        fields = ['content']


class NoticeForm(forms.ModelForm):
    class Meta:
        model = Notice
        fields = ['content']
        widgets = {'content': forms.Textarea(attrs={'rows': 3, 'placeholder': 'নোটিস লিখুন...'})}
        labels = {'content': 'নোটিস'}


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['body', 'image', 'file']
        widgets = {
            'body': forms.Textarea(attrs={'rows': 2, 'placeholder': 'বার্তা লিখুন...'}),
        }
        labels = {'body': '', 'image': 'ছবি', 'file': 'ফাইল'}


class MarketListCommentForm(forms.ModelForm):
    class Meta:
        model = MarketListComment
        fields = ['body']
        widgets = {'body': forms.Textarea(attrs={'rows': 2, 'placeholder': 'মন্তব্য লিখুন...'})}
        labels = {'body': ''}
