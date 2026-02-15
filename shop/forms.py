from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import FamilyProfile, MarketList, Notice, Message, MarketListComment


class FamilyRegistrationForm(forms.Form):
    full_name = forms.CharField(
        max_length=200, required=False, label='পূর্ণ নাম',
        help_text='প্রোফাইলে এই নাম সংরক্ষিত হবে।'
    )
    phone = forms.CharField(
        max_length=20, label='ফোন নম্বর',
        help_text='যোগাযোগের জন্য আপনার মোবাইল নম্বর দিন। লগইনের জন্যও ব্যবহার হবে।'
    )
    address = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}), label='ঠিকানা',
        help_text='বাড়ির পূর্ণ ঠিকানা লিখুন (বাড়ি নম্বর, রোড, এলাকা)।'
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput,
        label='পাসওয়ার্ড',
        help_text='পাসওয়ার্ড অন্তত ৮ অক্ষর হতে হবে।',
        min_length=8
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput,
        label='পাসওয়ার্ড নিশ্চিত করুন',
        help_text='নিশ্চিত হওয়ার জন্য একই পাসওয়ার্ড আবার লিখুন।'
    )

    def clean_phone(self):
        phone = (self.cleaned_data.get('phone') or '').replace(' ', '').strip()
        if not phone:
            raise forms.ValidationError('ফোন নম্বর দিন।')
        if FamilyProfile.objects.filter(phone=phone, is_deleted=False).exists():
            raise forms.ValidationError('এই ফোন নম্বর দিয়ে ইতিমধ্যে রেজিষ্ট্রেশন হয়েছে।')
        return phone

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('পাসওয়ার্ড মিলছে না।')
        return p2

    def save(self, commit=True):
        import re
        phone = self.cleaned_data['phone'].replace(' ', '').strip()
        base_username = re.sub(r'[^\w.@+-]', '_', f'user_{phone}')[:150]
        username = base_username
        n = 0
        while User.objects.filter(username=username).exists():
            n += 1
            username = f'{base_username}_{n}'[:150]
        user = User(username=username)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
            FamilyProfile.objects.create(
                user=user,
                full_name=self.cleaned_data.get('full_name', '').strip(),
                phone=phone,
                address=self.cleaned_data['address']
            )
        return user


class MarketListForm(forms.ModelForm):
    content = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'আপনার বাজারের লিস্ট এখানে লিখুন...'
        }),
        label=''
    )

    class Meta:
        model = MarketList
        fields = ['content']


class AdminMarketListEditForm(forms.ModelForm):
    content = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 5, 'placeholder': 'মূল লিস্ট'}), label='মূল লিস্ট')
    ai_content = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 5, 'placeholder': 'AI লিস্ট'}), label='AI লিস্ট')
    note = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'স্ট্যাটাস নোট (যেমন Delivered)'}), label='নোট')

    class Meta:
        model = MarketList
        fields = ['content', 'ai_content', 'note']


class ProfileEditForm(forms.ModelForm):
    email = forms.EmailField(required=False, label='ইমেইল', widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'example@email.com'}))

    class Meta:
        model = FamilyProfile
        fields = ['full_name', 'phone', 'address']
        labels = {'full_name': 'পূর্ণ নাম', 'phone': 'ফোন নম্বর', 'address': 'ঠিকানা'}
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'পূর্ণ নাম'}),
            'phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'ফোন নম্বর'}),
            'address': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'ঠিকানা'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user_id:
            self.fields['email'].initial = self.instance.user.email
    def clean_phone(self):
        phone = (self.cleaned_data.get('phone') or '').replace(' ', '').strip()
        if not phone:
            raise forms.ValidationError('ফোন নম্বর দিন।')
        qs = FamilyProfile.objects.filter(phone=phone, is_deleted=False)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('এই ফোন নম্বর ইতিমধ্যে ব্যবহৃত।')
        return phone

    def save(self, commit=True):
        obj = super().save(commit=False)
        if 'email' in self.cleaned_data:
            obj.user.email = self.cleaned_data.get('email', '') or ''
            if commit:
                obj.user.save(update_fields=['email'])
        if commit:
            obj.save()
        return obj


class PasswordChangeForm(forms.Form):
    current_password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-input'}), label='বর্তমান পাসওয়ার্ড')
    new_password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-input'}), label='নতুন পাসওয়ার্ড', min_length=8)
    new_password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-input'}), label='নতুন পাসওয়ার্ড নিশ্চিত করুন')

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        if not self.user.check_password(self.cleaned_data.get('current_password', '')):
            raise forms.ValidationError('বর্তমান পাসওয়ার্ড ভুল।')
        return self.cleaned_data['current_password']

    def clean_new_password2(self):
        p1 = self.cleaned_data.get('new_password1')
        p2 = self.cleaned_data.get('new_password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('পাসওয়ার্ড মিলছে না।')
        return p2


class NoticeForm(forms.ModelForm):
    class Meta:
        model = Notice
        fields = ['content']
        widgets = {'content': forms.Textarea(attrs={'rows': 1, 'placeholder': 'নোটিস লিখুন...', 'class': 'notice-input-small'})}
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
