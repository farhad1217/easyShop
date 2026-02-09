from datetime import datetime, date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.views.decorators.http import require_GET, require_POST

from .models import MarketList, FamilyProfile, Notice, Conversation, Message, MarketListComment
from .forms import FamilyRegistrationForm, MarketListForm, NoticeForm, MessageForm, MarketListCommentForm


def landing_page(request):
    return render(request, 'shop/landing.html')


def family_register(request):
    if request.user.is_authenticated and not request.user.is_staff:
        return redirect('family_dashboard')
    if request.method == 'POST':
        form = FamilyRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'রেজিষ্ট্রেশন সফল!')
            return redirect('family_dashboard')
        else:
            messages.error(request, 'দয়া করে ভুলগুলো ঠিক করুন।')
    else:
        form = FamilyRegistrationForm()
    return render(request, 'shop/family_register.html', {'form': form})


def family_login(request):
    if request.user.is_authenticated and not request.user.is_staff:
        return redirect('family_dashboard')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_staff:
                messages.error(request, 'এডমিন লগইন জন্য ম্যানেজমেন্ট সেকশনে যান।')
                return render(request, 'shop/family_login.html')
            login(request, user)
            return redirect('family_dashboard')
        else:
            messages.error(request, 'ইউজারনেম বা পাসওয়ার্ড ভুল।')
    return render(request, 'shop/family_login.html')


def management_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('management_dashboard')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_staff:
            login(request, user)
            return redirect('management_dashboard')
        else:
            messages.error(request, 'এডমিন একাউন্ট নয় বা লগইন তথ্য ভুল।')
    return render(request, 'shop/management_login.html')


def user_logout(request):
    logout(request)
    return redirect('landing_page')


def _unread_message_count(user):
    """Count messages received by user that are unread (from admin)."""
    if user.is_staff:
        return 0  # admin sees inbox, no single "unread" badge
    try:
        conv = user.admin_conversation
        return conv.messages.filter(read_at__isnull=True).exclude(sender=user).count()
    except Conversation.DoesNotExist:
        return 0


@login_required
def family_dashboard(request):
    if request.user.is_staff:
        return redirect('landing_page')
    lists = MarketList.objects.filter(family=request.user).order_by('-created_at')
    form = MarketListForm()
    notice = Notice.get_latest()
    unread_count = _unread_message_count(request.user)
    return render(request, 'shop/family_dashboard.html', {
        'lists': lists, 'form': form, 'notice': notice, 'unread_message_count': unread_count,
    })


@login_required
def send_market_list(request):
    """Submit new market list from dashboard."""
    if request.user.is_staff:
        return redirect('landing_page')
    if request.method == 'POST':
        form = MarketListForm(request.POST)
        if form.is_valid():
            market_list = form.save(commit=False)
            market_list.family = request.user
            market_list.save()
            messages.success(request, 'লিস্ট সফলভাবে পাঠানো হয়েছে!')
            return redirect('family_dashboard')
    return redirect('family_dashboard')


@login_required
def update_market_list(request, pk):
    """Update own market list."""
    if request.user.is_staff:
        return redirect('landing_page')
    market_list = get_object_or_404(MarketList, pk=pk, family=request.user)
    if market_list.status != 'pending':
        messages.error(request, 'শুধুমাত্র পেন্ডিং লিস্ট আপডেট করা যাবে।')
        return redirect('family_dashboard')
    if request.method == 'POST':
        form = MarketListForm(request.POST, instance=market_list)
        if form.is_valid():
            form.save()
            messages.success(request, 'লিস্ট আপডেট হয়েছে।')
            return redirect('family_dashboard')
    else:
        form = MarketListForm(instance=market_list)
    return render(request, 'shop/update_market_list.html', {'form': form, 'market_list': market_list})


@login_required
def delete_market_list(request, pk):
    """Delete own market list."""
    if request.user.is_staff:
        return redirect('landing_page')
    market_list = get_object_or_404(MarketList, pk=pk, family=request.user)
    market_list.delete()
    messages.success(request, 'লিস্ট মুছে ফেলা হয়েছে।')
    return redirect('family_dashboard')


# === ADMIN VIEWS ===

@staff_member_required(login_url='management_login')
def management_dashboard(request):
    filter_status = request.GET.get('filter', 'total')
    lists = MarketList.objects.all().select_related('family')
    if filter_status == 'approved':
        lists = lists.filter(status='approved')
    elif filter_status == 'pending':
        lists = lists.filter(status='pending')
    total_count = MarketList.objects.count()
    approved_count = MarketList.objects.filter(status='approved').count()
    pending_count = MarketList.objects.filter(status='pending').count()
    notice = Notice.get_latest()
    notice_form = NoticeForm(instance=notice)
    if request.method == 'POST' and request.POST.get('form_type') == 'notice':
        notice_form = NoticeForm(request.POST, instance=notice)
        if notice_form.is_valid():
            notice_form.save()
            messages.success(request, 'নোটিস আপডেট হয়েছে।')
            return redirect('management_dashboard')
    return render(request, 'shop/management_dashboard.html', {
        'lists': lists,
        'filter_status': filter_status,
        'total_count': total_count,
        'approved_count': approved_count,
        'pending_count': pending_count,
        'notice': notice,
        'notice_form': notice_form,
    })


@staff_member_required(login_url='management_login')
def date_wise_summary(request):
    """Date-wise consolidated view of all market lists."""
    selected_date = request.GET.get('date')
    if selected_date:
        try:
            dt = datetime.strptime(selected_date, '%Y-%m-%d').date()
            lists = MarketList.objects.filter(
                created_at__date=dt
            ).select_related('family').order_by('family__username')
        except ValueError:
            dt = date.today()
            lists = MarketList.objects.filter(created_at__date=dt).select_related('family')
    else:
        dt = date.today()
        lists = MarketList.objects.filter(created_at__date=dt).select_related('family')
    for lst in lists:
        try:
            lst.user_display_name = lst.family.family_profile.display_name or lst.family.username
        except FamilyProfile.DoesNotExist:
            lst.user_display_name = lst.family.username
    return render(request, 'shop/date_wise_summary.html', {
        'lists': lists,
        'selected_date': dt,
    })


@staff_member_required(login_url='management_login')
def user_directory(request):
    """All registered family profiles."""
    profiles = FamilyProfile.objects.select_related('user').order_by('user__username')
    return render(request, 'shop/user_directory.html', {'profiles': profiles})


@staff_member_required(login_url='management_login')
def user_profile_detail(request, user_id):
    """User profile with full details and market list history."""
    from django.contrib.auth.models import User
    user = get_object_or_404(User, pk=user_id)
    try:
        profile = user.family_profile
    except FamilyProfile.DoesNotExist:
        profile = None
    lists = MarketList.objects.filter(family=user).order_by('-created_at')
    return render(request, 'shop/user_profile_detail.html', {
        'profile_user': user,
        'profile': profile,
        'lists': lists,
    })


@staff_member_required(login_url='management_login')
def approve_list(request, pk):
    market_list = get_object_or_404(MarketList, pk=pk)
    if market_list.status == 'pending':
        market_list.status = 'approved'
        market_list.approved_at = timezone.now()
        market_list.save()
        messages.success(request, 'লিস্ট অনুমোদিত হয়েছে।')
    ref = request.META.get('HTTP_REFERER')
    return redirect(ref if ref else 'management_dashboard')


@staff_member_required(login_url='management_login')
def admin_delete_list(request, pk):
    market_list = get_object_or_404(MarketList, pk=pk)
    market_list.delete()
    messages.success(request, 'লিস্ট মুছে ফেলা হয়েছে।')
    ref = request.META.get('HTTP_REFERER')
    return redirect(ref if ref else 'management_dashboard')


# --- PDF & Consolidated ---

def _get_lists_for_date(dt):
    return MarketList.objects.filter(created_at__date=dt).select_related('family').order_by('family__username')


@staff_member_required(login_url='management_login')
def date_wise_summary_pdf(request):
    """Download date-wise summary as PDF: all lists with serial and user address."""
    selected_date = request.GET.get('date') or date.today().isoformat()
    try:
        dt = datetime.strptime(selected_date, '%Y-%m-%d').date()
    except ValueError:
        dt = date.today()
    lists = _get_lists_for_date(dt)
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from .pdf_utils import get_pdf_styles, safe_paragraph, safe_paragraph_bold
        from io import BytesIO
    except ImportError:
        return HttpResponse('PDF জেনারেট করতে reportlab ইনস্টল করুন: pip install reportlab', status=501)
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    st = get_pdf_styles()
    story = []
    story.append(safe_paragraph(st['title'], 'তারিখ অনুযায়ী বাজার তালিকা - ' + dt.strftime('%d/%m/%Y')))
    story.append(Spacer(1, 16))
    for idx, lst in enumerate(lists, 1):
        try:
            profile = lst.family.family_profile
            addr = profile.address or '-'
            name = profile.display_name or lst.family.username
        except FamilyProfile.DoesNotExist:
            addr = '-'
            name = lst.family.username
        story.append(safe_paragraph_bold(st['heading'], f'সিরিয়াল: {idx} | লিস্ট আইডি: #{lst.list_id} | ব্যবহারকারী: {name}'))
        story.append(safe_paragraph(st['body'], f'ঠিকানা: {addr}'))
        story.append(safe_paragraph(st['body'], f'লিস্ট: {lst.content or "-"}'))
        story.append(Spacer(1, 14))
    doc.build(story)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="date-summary-{dt.isoformat()}.pdf"'
    return response


@staff_member_required(login_url='management_login')
def date_wise_consolidated(request):
    """Same date: one page with all items merged (no user names). Option to download PDF."""
    selected_date = request.GET.get('date') or date.today().isoformat()
    try:
        dt = datetime.strptime(selected_date, '%Y-%m-%d').date()
    except ValueError:
        dt = date.today()
    lists = _get_lists_for_date(dt)
    # Merge all content lines into one list of "points" (items)
    all_lines = []
    for lst in lists:
        if lst.content:
            for line in lst.content.strip().splitlines():
                line = line.strip()
                if line:
                    all_lines.append(line)
    return render(request, 'shop/date_wise_consolidated.html', {
        'selected_date': dt,
        'lists': lists,
        'merged_items': all_lines,
    })


@staff_member_required(login_url='management_login')
def date_wise_consolidated_pdf(request):
    """Download consolidated (merged) items for the date as PDF."""
    selected_date = request.GET.get('date') or date.today().isoformat()
    try:
        dt = datetime.strptime(selected_date, '%Y-%m-%d').date()
    except ValueError:
        dt = date.today()
    lists = _get_lists_for_date(dt)
    all_lines = []
    for lst in lists:
        if lst.content:
            for line in lst.content.strip().splitlines():
                if line.strip():
                    all_lines.append(line.strip())
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from .pdf_utils import get_pdf_styles, safe_paragraph
        from io import BytesIO
    except ImportError:
        return HttpResponse('PDF জেনারেট করতে reportlab ইনস্টল করুন', status=501)
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    st = get_pdf_styles()
    story = [safe_paragraph(st['title'], 'সম্মিলিত বাজার পয়েন্ট - ' + dt.strftime('%d/%m/%Y')), Spacer(1, 16)]
    for i, line in enumerate(all_lines, 1):
        story.append(safe_paragraph(st['body'], f'{i}. {line}'))
        story.append(Spacer(1, 6))
    doc.build(story)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="consolidated-{dt.isoformat()}.pdf"'
    return response


# --- List comment thread (management + user) ---

@login_required
def list_comment_thread(request, pk):
    """View and add comments on a market list. Allowed: list owner or staff."""
    market_list = get_object_or_404(MarketList, pk=pk)
    if not request.user.is_staff and market_list.family_id != request.user.id:
        messages.error(request, 'এই লিস্টে মন্তব্য করার অনুমতি নেই।')
        return redirect('family_dashboard')
    comments = market_list.comments.select_related('author').order_by('created_at')
    form = MarketListCommentForm()
    if request.method == 'POST':
        form = MarketListCommentForm(request.POST)
        if form.is_valid():
            MarketListComment.objects.create(market_list=market_list, author=request.user, body=form.cleaned_data['body'])
            messages.success(request, 'মন্তব্য যোগ হয়েছে।')
            return redirect('list_comment_thread', pk=pk)
    from django.urls import reverse
    back_url = request.GET.get('back') or request.META.get('HTTP_REFERER') or (reverse('date_wise_summary') if request.user.is_staff else reverse('family_dashboard'))
    return render(request, 'shop/list_comment_thread.html', {
        'market_list': market_list, 'comments': comments, 'form': form, 'back_url': back_url,
    })


# --- Messaging (user–admin) ---

def _get_or_create_conversation(user):
    conv, _ = Conversation.objects.get_or_create(user=user)
    return conv


@login_required
def messaging_inbox(request):
    """Staff: list all conversations. User: redirect to own thread."""
    if not request.user.is_staff:
        conv = _get_or_create_conversation(request.user)
        return redirect('messaging_thread', user_id=request.user.id)
    conversations = Conversation.objects.all().select_related('user').order_by('-id')
    # Add last message and unread count per conversation
    conv_list = []
    for c in conversations:
        last = c.messages.order_by('-created_at').first()
        unread = c.messages.filter(read_at__isnull=True).exclude(sender=c.user).count()
        conv_list.append({'conv': c, 'last_message': last, 'unread': unread})
    return render(request, 'shop/messaging_inbox.html', {'conversations': conv_list})


@login_required
def messaging_thread(request, user_id):
    """Open conversation with user_id. Staff can open any; user only own."""
    target_user = get_object_or_404(User, pk=user_id)
    if not request.user.is_staff and request.user.id != int(user_id):
        messages.error(request, 'অনুমতি নেই।')
        return redirect('family_dashboard')
    conv = _get_or_create_conversation(target_user)
    # Mark messages received by current user as read
    conv.messages.exclude(sender=request.user).filter(read_at__isnull=True).update(read_at=timezone.now())
    msgs = conv.messages.select_related('sender').order_by('created_at')
    form = MessageForm()
    if request.method == 'POST':
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.conversation = conv
            msg.sender = request.user
            msg.save()
            return redirect('messaging_thread', user_id=user_id)
    other = target_user
    return render(request, 'shop/messaging_thread.html', {
        'conversation': conv, 'messages': msgs, 'form': form, 'other_user': other,
    })


@login_required
@require_GET
def message_unread_count(request):
    """API: return unread count for current user (for badge)."""
    count = _unread_message_count(request.user)
    return JsonResponse({'unread': count})


#delivery section
def delivery(request):
    return render(request, "shop/delivery.html")


# --- Notice (already in dashboard; update via management_dashboard form)
