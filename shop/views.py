from datetime import datetime, date, timedelta
import json

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Max
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.clickjacking import xframe_options_sameorigin

from .models import MarketList, FamilyProfile, Notice, Conversation, Message, MarketListComment, Pathway, PathwayImage, DeliveryFlow, SendStatusPreset
from .forms import FamilyRegistrationForm, MarketListForm, NoticeForm, MessageForm, MarketListCommentForm, ProfileEditForm, PasswordChangeForm, AdminMarketListEditForm


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
            return redirect('family_dashboard')
    else:
        form = FamilyRegistrationForm()
    return render(request, 'shop/family_register.html', {'form': form})


def family_login(request):
    if request.user.is_authenticated and not request.user.is_staff:
        return redirect('family_dashboard')
    login_error = None
    if request.method == 'POST':
        phone = (request.POST.get('phone') or '').replace(' ', '').strip()
        password = request.POST.get('password', '')
        username = request.POST.get('username')
        user = None
        if phone:
            try:
                profile = FamilyProfile.objects.get(phone=phone, is_deleted=False)
                user = authenticate(request, username=profile.user.username, password=password)
            except (FamilyProfile.DoesNotExist, FamilyProfile.MultipleObjectsReturned):
                pass
        if not user and username:
            user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_staff:
                return render(request, 'shop/family_login.html')
            login(request, user)
            return redirect('family_dashboard')
        login_error = 'Password incorrect!'
    return render(request, 'shop/family_login.html', {'login_error': login_error})


def management_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('management_dashboard')
    login_error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_staff:
            login(request, user)
            return redirect('management_dashboard')
        login_error = 'Password incorrect!'
    return render(request, 'shop/management_login.html', {'login_error': login_error})


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
    # প্রধান হিস্টোরি: পেন্ডিং + অ্যাপ্রুভড
    lists = MarketList.objects.filter(family=request.user, status__in=['pending', 'approved']).order_by('-created_at')
    # ডেলিভার্ড ফোল্ডার: তারিখ ও সময় অনুযায়ী
    delivered_lists = MarketList.objects.filter(family=request.user, status='delivered').order_by('-delivered_at', '-created_at')
    # ডিক্লাইন্ড ফোল্ডার: তারিখ ও সময় অনুযায়ী
    declined_lists = MarketList.objects.filter(family=request.user, status='declined').order_by('-declined_at', '-created_at')
    # লিস্ট হিস্টোরিতে প্যাক নম্বরের পাশে Send Order Status (Delivery Flow অনুযায়ী)
    flows = list(DeliveryFlow.objects.all().order_by('sort_order', 'id'))
    lists_with_status = []
    for lst in lists:
        order_time = None
        if lst.created_at:
            dt = timezone.localtime(lst.created_at) if getattr(lst.created_at, 'tzinfo', None) else lst.created_at
            order_time = dt.time()
        flow_status = None
        if order_time and flows:
            for f in flows:
                if f.start_time <= order_time <= f.end_time:
                    flow_status = f.status_text or 'Approved'
                    break
        lists_with_status.append((lst, flow_status))
    form = MarketListForm()
    notice = Notice.get_latest()
    unread_count = _unread_message_count(request.user)
    try:
        prof = request.user.family_profile
        display_name = prof.display_name or request.user.username
        profile_avatar = prof.avatar if prof.avatar else None
    except FamilyProfile.DoesNotExist:
        display_name = request.user.username
        profile_avatar = None
    return render(request, 'shop/family_dashboard.html', {
        'lists': lists, 'lists_with_status': lists_with_status,
        'delivered_lists': delivered_lists, 'declined_lists': declined_lists,
        'form': form, 'notice': notice, 'unread_message_count': unread_count,
        'display_name': display_name, 'profile_avatar': profile_avatar,
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
            content = (market_list.content or '').strip()
            lines = [s.strip() for s in content.splitlines() if s.strip()]
            market_list.content = '\n'.join(lines)
            market_list.family = request.user
            # New lists will be treated as approved immediately (no pending state)
            market_list.status = 'approved'
            market_list.approved_at = timezone.now()
            market_list.save()
            # লিস্ট সাবমিট হলেই অটো AI দিয়ে জেনারেট
            if market_list.content:
                market_list.ai_content = _ai_organize_list(market_list.content)
                market_list.save(update_fields=['ai_content'])
            return redirect(reverse('family_dashboard') + '?toast=sent')
        # ফর্ম ভ্যালিড না হলে ড্যাশবোর্ডে ফিরিয়ে পাঠান ভুল সহ
        lists = MarketList.objects.filter(family=request.user, status__in=['pending', 'approved']).order_by('-created_at')
        delivered_lists = MarketList.objects.filter(family=request.user, status='delivered').order_by('-delivered_at', '-created_at')
        declined_lists = MarketList.objects.filter(family=request.user, status='declined').order_by('-declined_at', '-created_at')
        flows = list(DeliveryFlow.objects.all().order_by('sort_order', 'id'))
        lists_with_status = []
        for lst in lists:
            order_time = None
            if lst.created_at:
                dt = timezone.localtime(lst.created_at) if getattr(lst.created_at, 'tzinfo', None) else lst.created_at
                order_time = dt.time()
            flow_status = None
            if order_time and flows:
                for f in flows:
                    if f.start_time <= order_time <= f.end_time:
                        flow_status = f.status_text or 'Approved'
                        break
            lists_with_status.append((lst, flow_status))
        notice = Notice.get_latest()
        unread_count = _unread_message_count(request.user)
        try:
            display_name = request.user.family_profile.display_name or request.user.username
        except FamilyProfile.DoesNotExist:
            display_name = request.user.username
        return render(request, 'shop/family_dashboard.html', {
            'lists': lists, 'lists_with_status': lists_with_status,
            'delivered_lists': delivered_lists, 'declined_lists': declined_lists,
            'form': form, 'notice': notice, 'unread_message_count': unread_count,
            'display_name': display_name,
        })
    return redirect('family_dashboard')


@login_required
def update_market_list(request, pk):
    """Update own market list."""
    if request.user.is_staff:
        return redirect('landing_page')
    market_list = get_object_or_404(MarketList, pk=pk, family=request.user)
    if market_list.status not in ('pending', 'approved'):
        return redirect('family_dashboard')
    if request.method == 'POST':
        form = MarketListForm(request.POST, instance=market_list)
        if form.is_valid():
            obj = form.save(commit=False)
            content = (obj.content or '').strip()
            lines = [s.strip() for s in content.splitlines() if s.strip()]
            obj.content = '\n'.join(lines)
            obj.save()
            # আপডেট সাবমিট হলেই অটো AI দিয়ে জেনারেট
            if obj.content:
                obj.ai_content = _ai_organize_list(obj.content)
                obj.save(update_fields=['ai_content'])
            return redirect('family_dashboard')
    else:
        form = MarketListForm(instance=market_list)
    return render(request, 'shop/update_market_list.html', {'form': form, 'market_list': market_list})


@login_required
def my_profile(request):
    """User's own profile page with edit."""
    if request.user.is_staff:
        return redirect('landing_page')
    try:
        profile = request.user.family_profile
    except FamilyProfile.DoesNotExist:
        profile = FamilyProfile.objects.create(user=request.user, full_name='', phone='-', address='-')
    profile_form = ProfileEditForm(instance=profile)
    password_form = PasswordChangeForm(user=request.user)
    if request.method == 'POST':
        form_type = request.POST.get('form_type', 'profile')
        if form_type == 'profile':
            profile_form = ProfileEditForm(request.POST, instance=profile)
            if profile_form.is_valid():
                profile_form.save()
                return redirect('my_profile')
        elif form_type == 'avatar':
            avatar_file = request.FILES.get('avatar')
            if avatar_file:
                try:
                    from PIL import Image
                    img = Image.open(avatar_file)
                    img = img.convert('RGB')
                    w, h = img.size
                    size = 400
                    if w > size or h > size:
                        r = min(size / w, size / h)
                        img = img.resize((int(w * r), int(h * r)), Image.Resampling.LANCZOS)
                    from io import BytesIO
                    from django.core.files.base import ContentFile
                    out = BytesIO()
                    img.save(out, format='JPEG', quality=85)
                    profile.avatar.save('avatar_%s.jpg' % profile.user_id, ContentFile(out.getvalue()), save=True)
                except Exception:
                    pass
            return redirect('my_profile')
        elif form_type == 'password':
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                request.user.set_password(password_form.cleaned_data['new_password1'])
                request.user.save()
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, request.user)
                return redirect('my_profile')
    return render(request, 'shop/my_profile.html', {
        'profile': profile,
        'profile_form': profile_form,
        'password_form': password_form,
    })


@login_required
def delete_market_list(request, pk):
    """Delete own market list."""
    if request.user.is_staff:
        return redirect('landing_page')
    market_list = get_object_or_404(MarketList, pk=pk, family=request.user)
    market_list.delete()
    return redirect(reverse('family_dashboard') + '?toast=deleted')


# === ADMIN VIEWS ===

@staff_member_required(login_url='management_login')
def management_dashboard(request):
    filter_status = request.GET.get('filter', 'total')
    lists = MarketList.objects.all().select_related('family', 'family__family_profile')
    if filter_status == 'approved':
        lists = lists.filter(status='approved')
    elif filter_status == 'pending':
        lists = lists.filter(status='pending')
    elif filter_status == 'delivered':
        lists = lists.filter(status='delivered')
    elif filter_status == 'declined':
        lists = lists.filter(status='declined')
    # 'late_transferred' status removed
    else:
        # Default "total" view: exclude delivered/declined/late_transferred so they move out once handled
        lists = lists.exclude(status__in=['delivered', 'declined', 'late_transferred'])
    # filter=total or default: show all orders (no status filter)
    for lst in lists:
        try:
            lst.user_display_name = lst.family.family_profile.display_name or lst.family.username
            lst.user_avatar_url = lst.family.family_profile.avatar.url if lst.family.family_profile.avatar else None
        except FamilyProfile.DoesNotExist:
            lst.user_display_name = lst.family.username
            lst.user_avatar_url = None
        except Exception:
            lst.user_avatar_url = None
    # Delivered lists for toggle section on Total view (same display attrs)
    delivered_qs = MarketList.objects.filter(status='delivered').select_related('family', 'family__family_profile').order_by('-delivered_at', '-created_at')
    delivered_lists = []
    for lst in delivered_qs:
        try:
            lst.user_display_name = lst.family.family_profile.display_name or lst.family.username
            lst.user_avatar_url = lst.family.family_profile.avatar.url if lst.family.family_profile.avatar else None
        except FamilyProfile.DoesNotExist:
            lst.user_display_name = lst.family.username
            lst.user_avatar_url = None
        except Exception:
            lst.user_avatar_url = None
        delivered_lists.append(lst)
    # Declined/Cancelled lists for toggle section on Total view
    declined_qs = MarketList.objects.filter(status='declined').select_related('family', 'family__family_profile').order_by('-declined_at', '-created_at')
    declined_lists = []
    for lst in declined_qs:
        try:
            lst.user_display_name = lst.family.family_profile.display_name or lst.family.username
            lst.user_avatar_url = lst.family.family_profile.avatar.url if lst.family.family_profile.avatar else None
        except FamilyProfile.DoesNotExist:
            lst.user_display_name = lst.family.username
            lst.user_avatar_url = None
        except Exception:
            lst.user_avatar_url = None
        declined_lists.append(lst)
    total_count = MarketList.objects.exclude(status__in=['delivered', 'declined']).count()
    approved_count = MarketList.objects.filter(status='approved').count()
    pending_count = MarketList.objects.filter(status='pending').count()
    delivered_count = MarketList.objects.filter(status='delivered').count()
    declined_count = MarketList.objects.filter(status='declined').count()
    late_transferred_count = 0
    # Delivery path setup pending: profiles with at least one path field empty (exclude deleted)
    delivery_path_pending_count = FamilyProfile.objects.filter(is_deleted=False).filter(
        Q(area_name='') | Q(section_no='') | Q(building_name='') |
        Q(floor_no='') | Q(room_no='')
    ).count()
    trash_count = FamilyProfile.objects.filter(is_deleted=True).count()
    notice = Notice.get_latest()
    notice_form = NoticeForm(instance=notice)
    if request.method == 'POST' and request.POST.get('form_type') == 'notice':
        notice_form = NoticeForm(request.POST, instance=notice)
        if notice_form.is_valid():
            notice_form.save()
            return redirect('management_dashboard')
    lists_qs = list(lists)
    merged_items = _get_merged_items_from_lists(lists_qs)
    users_data = {}
    for lst in lists_qs:
        try:
            display_name = lst.family.family_profile.display_name or lst.family.username
        except FamilyProfile.DoesNotExist:
            display_name = lst.family.username
        uid = lst.family_id
        if uid not in users_data:
            users_data[uid] = {'display_name': display_name, 'lists': []}
        users_data[uid]['lists'].append({
            'pk': lst.pk,
            'list_id': lst.list_id or f'Pack-{lst.pk}',
            'created_at': lst.created_at,
            'status': lst.get_status_display(),
            'status_note': (lst.note or '').strip(),
            'content': lst.content or '',
            'ai_content': lst.ai_content or '',
        })
    total_notes_qs = MarketList.objects.exclude(status__in=['delivered', 'declined']).values_list('note', flat=True)
    note_values = []
    for note in total_notes_qs:
        note_clean = (note or '').strip()
        if note_clean and note_clean not in note_values:
            note_values.append(note_clean)
            if len(note_values) > 1:
                break
    status_override = note_values[0] if len(note_values) == 1 else ''
    # Delivery flow configuration (for Delivery Flow Set)
    delivery_flows_qs = DeliveryFlow.objects.all().order_by('sort_order', 'id')
    delivery_flows = []
    for idx, f in enumerate(delivery_flows_qs, 1):
        delivery_flows.append({
            'name': f.name or f"Flow {idx}",
            'label': f.label,
            'start': f.start_time.strftime('%H:%M'),
            'end': f.end_time.strftime('%H:%M'),
            'statusText': f.status_text or 'Approved',
        })
    users_list = [
        {'user_id': uid, 'display_name': data['display_name'], 'count': len(data['lists']), 'lists': data['lists']}
        for uid, data in users_data.items()
    ]
    users_list.sort(key=lambda x: (x['display_name'].upper(), x['user_id']))
    presets = list(SendStatusPreset.objects.values_list('text', flat=True))

    return render(request, 'shop/management_dashboard.html', {
        'lists': lists_qs,
        'delivered_lists': delivered_lists,
        'declined_lists': declined_lists,
        'filter_status': filter_status,
        'total_count': total_count,
        'approved_count': approved_count,
        'pending_count': pending_count,
        'delivered_count': delivered_count,
        'declined_count': declined_count,
        'late_transferred_count': late_transferred_count,
        'delivery_path_pending_count': delivery_path_pending_count,
        'trash_count': trash_count,
        'notice': notice,
        'notice_form': notice_form,
        'merged_items': merged_items,
        'users_list': users_list,
        'status_override': status_override,
        'delivery_flows': delivery_flows,
        'send_status_presets': presets,
    })


@staff_member_required(login_url='management_login')
@require_POST
def save_delivery_flow(request):
    """Persist delivery flow config for Delivery Flow Set (Total Order Received)."""
    import json
    flows_raw = request.POST.get('flows') or '[]'
    try:
        flows = json.loads(flows_raw)
        if not isinstance(flows, list):
            raise ValueError
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid payload'}, status=400)

    # Clear existing flows and recreate from payload
    DeliveryFlow.objects.all().delete()
    from datetime import datetime as _dt
    created = 0
    for idx, flow in enumerate(flows):
        label = (flow.get('label') or '').strip()
        start = (flow.get('start') or '').strip()
        end = (flow.get('end') or '').strip()
        if not (label and start and end):
            continue
        try:
            start_time = _dt.strptime(start, '%H:%M').time()
            end_time = _dt.strptime(end, '%H:%M').time()
        except ValueError:
            continue
        DeliveryFlow.objects.create(
            name=(flow.get('name') or '').strip() or f"Flow {idx+1}",
            label=label,
            start_time=start_time,
            end_time=end_time,
            status_text=(flow.get('statusText') or flow.get('status') or 'Approved').strip()[:255],
            sort_order=idx,
        )
        created += 1
    return JsonResponse({'success': True, 'count': created})


@staff_member_required(login_url='management_login')
@require_POST
def save_send_status_presets(request):
    """Persist admin 'Send Order Status' preset texts globally."""
    raw = request.POST.get('presets') or '[]'
    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid data'}, status=400)

    # Replace all presets with new ordered list
    SendStatusPreset.objects.all().delete()
    bulk = []
    order = 0
    for txt in data:
        txt = (txt or '').strip()
        if not txt:
            continue
        bulk.append(SendStatusPreset(text=txt, sort_order=order))
        order += 1
    if bulk:
        SendStatusPreset.objects.bulk_create(bulk)
    return JsonResponse({'success': True, 'count': len(bulk)})


@staff_member_required(login_url='management_login')
@require_POST
def write_list_status(request):
    status_text = (request.POST.get('status_text') or '').strip()
    qs = MarketList.objects.exclude(status__in=['delivered', 'declined'])
    if status_text:
        qs.update(note=status_text)
    else:
        qs.update(note='')
    return JsonResponse({'success': True, 'status_text': status_text})


@staff_member_required(login_url='management_login')
def user_directory(request):
    """User Profile & Delivery Path manager - vertical list of user blocks."""
    all_profiles = FamilyProfile.objects.filter(is_deleted=False).select_related('user').order_by('user__username')
    # Completed: all 5 delivery path fields filled
    completed = all_profiles.exclude(
        Q(area_name='') | Q(section_no='') | Q(building_name='') |
        Q(floor_no='') | Q(room_no='')
    )
    # Pending: at least one field empty
    pending = all_profiles.filter(
        Q(area_name='') | Q(section_no='') | Q(building_name='') |
        Q(floor_no='') | Q(room_no='')
    )
    completed_ids = set(completed.values_list('user_id', flat=True))
    # Area -> Section -> Building -> Profiles (with approved lists only) for Delivery Funnel
    def _format_section(s):
        s = (s or '').strip()
        if not s:
            return ''
        u = s.upper()
        return u if u.startswith('SECTION') else f"SECTION-{u}"

    # Delivery Funnel: only APPROVED lists (5s auto approval) - delivered/declined excluded
    lists_by_user = {}
    for ml in MarketList.objects.filter(status='approved').select_related('family'):
        uid = ml.family_id
        if uid not in lists_by_user:
            lists_by_user[uid] = []
        ai_content = (ml.ai_content or '').strip()
        orig_content = (ml.content or '').strip()
        ai_items = [ln.strip() for ln in ai_content.splitlines() if ln.strip()] if ai_content else []
        orig_items = [ln.strip() for ln in orig_content.splitlines() if ln.strip()] if orig_content else []
        lists_by_user[uid].append({
            'pk': ml.pk,
            'list_id': ml.list_id or f'Pack-{ml.pk}',
            'created_at': ml.created_at,
            'status': 'approved',
            'ai_items': ai_items,
            'orig_items': orig_items,
            'deliver_url': reverse('deliver_list', args=[ml.pk]),
            'decline_url': reverse('decline_list', args=[ml.pk]),
        })

    area_data = {}
    for profile in completed.select_related('user'):
        area = (profile.area_name or '').strip()
        section = (profile.section_no or '').strip()
        building = (profile.building_name or '').strip()
        if not area or not section or not building:
            continue
        uid = profile.user_id
        sec_fmt = _format_section(section)
        bld = building.strip()
        key = (area, sec_fmt, bld)
        if key not in area_data:
            area_data[key] = {}
        if uid not in area_data[key]:
            area_data[key][uid] = (
                profile.display_name,
                profile.phone or '',
                (profile.floor_no or '').strip(),
                (profile.room_no or '').strip(),
                lists_by_user.get(uid, []),
            )

    def pathway_has_images(a, s, b):
        return PathwayImage.objects.filter(
            pathway__area_name=a, pathway__section_no=s or '', pathway__building_name=b or ''
        ).exists()

    area_sections_buildings_profiles_list = []
    for area in sorted({k[0] for k in area_data.keys()}):
        secs = []
        area_count = 0
        for sec in sorted({k[1] for k in area_data.keys() if k[0] == area}):
            blds = []
            sec_count = 0
            for bld in sorted({k[2] for k in area_data.keys() if k[0] == area and k[1] == sec}):
                key = (area, sec, bld)
                raw_profiles = area_data[key]
                profiles_data = []
                for uid, (name, phone, floor, room, lists) in raw_profiles.items():
                    if not lists:
                        continue
                    profiles_data.append((uid, name, phone, floor, room, lists))
                if not profiles_data:
                    continue
                profiles_data.sort(key=lambda x: (x[1].upper(), x[0]))
                bld_count = sum(len(lists) for _, _, _, _, _, lists in profiles_data)
                if bld_count == 0:
                    continue
                sec_count += bld_count
                blds.append((bld, bld_count, profiles_data, pathway_has_images(area, sec, bld)))
            if sec_count == 0 or not blds:
                continue
            area_count += sec_count
            secs.append((sec, sec_count, blds, pathway_has_images(area, sec, '')))
        if area_count == 0 or not secs:
            continue
        area_sections_buildings_profiles_list.append((area, area_count, secs, pathway_has_images(area, '', '')))

    # Delivery Flow configuration (same as admin dashboard) – used to tag lists in Delivery Funnel
    delivery_flows_qs = DeliveryFlow.objects.all().order_by('sort_order', 'id')
    delivery_flows = []
    for idx, f in enumerate(delivery_flows_qs, 1):
        delivery_flows.append({
            'name': f.name or f"Flow {idx}",
            'label': f.label,
            'start': f.start_time.strftime('%H:%M'),
            'end': f.end_time.strftime('%H:%M'),
        })

    return render(request, 'shop/user_directory.html', {
        'profiles': all_profiles,
        'completed_count': completed.count(),
        'pending_count': pending.count(),
        'completed_ids': completed_ids,
        'area_sections_buildings_profiles_list': area_sections_buildings_profiles_list,
        'delivery_flows': delivery_flows,
    })


@staff_member_required(login_url='management_login')
@require_POST
def save_delivery_path(request, user_id):
    """Save delivery path for a user. Returns JSON."""
    user = get_object_or_404(User, pk=user_id)
    try:
        profile = user.family_profile
    except FamilyProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Profile not found'}, status=404)
    area = (request.POST.get('area_name') or '').strip()
    section = (request.POST.get('section_no') or '').strip()
    building = (request.POST.get('building_name') or '').strip()
    floor = (request.POST.get('floor_no') or '').strip()
    room = (request.POST.get('room_no') or '').strip()
    empty = []
    if not area:
        empty.append('area_name')
    if not section:
        empty.append('section_no')
    if not building:
        empty.append('building_name')
    if not floor:
        empty.append('floor_no')
    if not room:
        empty.append('room_no')
    if empty:
        return JsonResponse({'success': False, 'empty_fields': empty})
    profile.area_name = area
    profile.section_no = section
    profile.building_name = building
    profile.floor_no = floor
    profile.room_no = room
    profile.save()
    return JsonResponse({'success': True, 'delivery_path': profile.delivery_path_display})


@staff_member_required(login_url='management_login')
@require_POST
def update_address(request, user_id):
    """Update address for a user. Returns JSON."""
    user = get_object_or_404(User, pk=user_id)
    try:
        profile = user.family_profile
    except FamilyProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Profile not found'}, status=404)
    addr = (request.POST.get('address') or '').strip()
    if not addr:
        return JsonResponse({'success': False, 'error': 'Address required'})
    profile.address = addr
    profile.save()
    return JsonResponse({'success': True, 'address': profile.address})


@staff_member_required(login_url='management_login')
@require_GET
def pathway_images(request):
    """Get pathway images for area/section/building. Returns JSON."""
    area = (request.GET.get('area') or '').strip()
    section = (request.GET.get('section') or '').strip()
    building = (request.GET.get('building') or '').strip()
    if not area:
        return JsonResponse({'success': False, 'error': 'Area required'}, status=400)
    pathway, _ = Pathway.objects.get_or_create(
        area_name=area,
        section_no=section,
        building_name=building,
        defaults={'area_name': area, 'section_no': section, 'building_name': building}
    )
    images = list(pathway.images.order_by('position').values('id', 'position', 'note'))
    for img in images:
        pi = PathwayImage.objects.get(pk=img['id'])
        img['url'] = pi.image.url if pi.image else ''
    return JsonResponse({'success': True, 'images': images, 'pathway_id': pathway.pk})


@staff_member_required(login_url='management_login')
@require_POST
def pathway_upload(request):
    """Upload new image to pathway. POST: area, section, building, image (file)."""
    area = (request.POST.get('area') or '').strip()
    section = (request.POST.get('section') or '').strip()
    building = (request.POST.get('building') or '').strip()
    if not area:
        return JsonResponse({'success': False, 'error': 'Area required'}, status=400)
    pathway, _ = Pathway.objects.get_or_create(
        area_name=area,
        section_no=section,
        building_name=building,
        defaults={'area_name': area, 'section_no': section, 'building_name': building}
    )
    img_file = request.FILES.get('image')
    if not img_file:
        return JsonResponse({'success': False, 'error': 'Image file required'}, status=400)
    # Frontend sends pre-compressed images (max 500KB); allow up to 600KB as safety
    if img_file.size > 600 * 1024:
        return JsonResponse({'success': False, 'error': 'Image too large (max 500KB after compression)'}, status=400)
    max_pos = pathway.images.aggregate(m=Max('position'))['m']
    position = (max_pos or -1) + 1
    pi = PathwayImage.objects.create(pathway=pathway, image=img_file, position=position)
    return JsonResponse({
        'success': True,
        'id': pi.id,
        'position': position,
        'url': pi.image.url,
    })


@staff_member_required(login_url='management_login')
@require_POST
def pathway_update_note(request, image_id):
    """Update note for a pathway image."""
    pi = get_object_or_404(PathwayImage, pk=image_id)
    note = (request.POST.get('note') or '').strip()
    pi.note = note
    pi.save()
    return JsonResponse({'success': True})


@staff_member_required(login_url='management_login')
@require_POST
def pathway_delete(request, image_id):
    """Delete a pathway image."""
    pi = get_object_or_404(PathwayImage, pk=image_id)
    pi.delete()
    return JsonResponse({'success': True})


@staff_member_required(login_url='management_login')
@require_POST
def pathway_replace(request, image_id):
    """Replace existing pathway image. POST: image (file)."""
    pi = get_object_or_404(PathwayImage, pk=image_id)
    img_file = request.FILES.get('image')
    if not img_file:
        return JsonResponse({'success': False, 'error': 'Image file required'}, status=400)
    if img_file.size > 600 * 1024:
        return JsonResponse({'success': False, 'error': 'Image too large (max 500KB after compression)'}, status=400)
    pi.image = img_file
    pi.save()
    return JsonResponse({'success': True, 'url': pi.image.url})


@staff_member_required(login_url='management_login')
def user_profiles(request):
    """User Profiles list - username, full name, address, phone. Option to delete (soft delete to trash)."""
    profiles = FamilyProfile.objects.filter(is_deleted=False).select_related('user').order_by('user__username')
    trash_profiles = FamilyProfile.objects.filter(is_deleted=True).select_related('user').order_by('-deleted_at')
    trash_count = trash_profiles.count()
    return render(request, 'shop/user_profiles.html', {
        'profiles': profiles, 'trash_profiles': trash_profiles, 'trash_count': trash_count,
    })


@staff_member_required(login_url='management_login')
@require_POST
def soft_delete_profile(request, user_id):
    """Soft delete: move profile to trash (is_deleted=True, user.is_active=False)."""
    user = get_object_or_404(User, pk=user_id)
    try:
        profile = user.family_profile
    except FamilyProfile.DoesNotExist:
        return redirect('user_profiles')
    if profile.is_deleted:
        return redirect('user_profiles')
    profile.is_deleted = True
    profile.deleted_at = timezone.now()
    profile.save()
    user.is_active = False
    user.save()
    return redirect('user_profiles')


@staff_member_required(login_url='management_login')
def trash_folder(request):
    """Trash folder - list of soft-deleted profiles. Options: Restore or Permanent Delete."""
    profiles = FamilyProfile.objects.filter(is_deleted=True).select_related('user').order_by('-deleted_at')
    return render(request, 'shop/trash_folder.html', {'profiles': profiles})


@staff_member_required(login_url='management_login')
@require_POST
def restore_profile(request, user_id):
    """Restore profile from trash."""
    user = get_object_or_404(User, pk=user_id)
    try:
        profile = user.family_profile
    except FamilyProfile.DoesNotExist:
        return redirect('user_profiles')
    if not profile.is_deleted:
        return redirect('user_profiles')
    profile.is_deleted = False
    profile.deleted_at = None
    profile.save()
    user.is_active = True
    user.save()
    return redirect('user_profiles')


@staff_member_required(login_url='management_login')
@require_POST
def permanent_delete_profile(request, user_id):
    """Permanently delete user and profile from trash."""
    user = get_object_or_404(User, pk=user_id)
    try:
        profile = user.family_profile
    except FamilyProfile.DoesNotExist:
        return redirect('user_profiles')
    if not profile.is_deleted:
        return redirect('user_profiles')
    username = user.username
    user.delete()  # Cascades to FamilyProfile
    return redirect('user_profiles')


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
def edit_user_profile(request, user_id):
    """Edit user profile info (full name, phone, address) from User Profiles. Staff only."""
    from .forms import ProfileEditForm
    user = get_object_or_404(User, pk=user_id)
    try:
        profile = user.family_profile
    except FamilyProfile.DoesNotExist:
        messages.error(request, 'প্রোফাইল খুঁজে পাওয়া যায়নি।')
        return redirect('user_profiles')
    if profile.is_deleted:
        messages.error(request, 'মুছে ফেলা প্রোফাইল এডিট করা যাবে না।')
        return redirect('user_profiles')
    form = ProfileEditForm(instance=profile)
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'প্রোফাইল সেভ হয়েছে।')
            return redirect('user_profiles')
    return render(request, 'shop/edit_user_profile.html', {
        'profile': profile,
        'form': form,
    })


@staff_member_required(login_url='management_login')
def approve_list(request, pk):
    market_list = get_object_or_404(MarketList, pk=pk)
    if market_list.status == 'pending':
        market_list.status = 'approved'
        market_list.approved_at = timezone.now()
        market_list.save()
    ref = request.META.get('HTTP_REFERER')
    return redirect(ref if ref else 'management_dashboard')


@staff_member_required(login_url='management_login')
def revert_to_pending(request, pk):
    market_list = get_object_or_404(MarketList, pk=pk)
    if market_list.status == 'approved':
        market_list.status = 'pending'
        market_list.approved_at = None
        market_list.save()
    ref = request.META.get('HTTP_REFERER')
    return redirect(ref if ref else 'management_dashboard')


@staff_member_required(login_url='management_login')
def decline_list(request, pk):
    market_list = get_object_or_404(MarketList, pk=pk)
    if market_list.status in ('pending', 'approved'):
        market_list.status = 'declined'
        market_list.declined_at = timezone.now()
        market_list.save()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'status': 'declined'})
    ref = request.META.get('HTTP_REFERER')
    return redirect(ref if ref else 'management_dashboard')


@staff_member_required(login_url='management_login')
def deliver_list(request, pk):
    market_list = get_object_or_404(MarketList, pk=pk)
    if market_list.status == 'approved':
        market_list.status = 'delivered'
        market_list.delivered_at = timezone.now()
        market_list.save()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'status': 'delivered'})
    ref = request.META.get('HTTP_REFERER')
    return redirect(ref if ref else 'management_dashboard')


@staff_member_required(login_url='management_login')
def restore_list(request, pk):
    """Bring delivered/declined list back to Total Order Received (approved)."""
    market_list = get_object_or_404(MarketList, pk=pk)
    if market_list.status in ('delivered', 'declined'):
        market_list.status = 'approved'
        market_list.approved_at = timezone.now()
        market_list.delivered_at = None
        market_list.declined_at = None
        market_list.save()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'status': 'approved'})
    ref = request.META.get('HTTP_REFERER')
    return redirect(ref if ref else 'management_dashboard')


@staff_member_required(login_url='management_login')
def admin_delete_list(request, pk):
    market_list = get_object_or_404(MarketList, pk=pk)
    market_list.delete()
    ref = request.META.get('HTTP_REFERER')
    return redirect(ref if ref else 'management_dashboard')


@staff_member_required(login_url='management_login')
def admin_edit_list(request, pk):
    """Admin: edit list content, ai_content, note. Redirect back to dashboard with same filter."""
    market_list = get_object_or_404(MarketList, pk=pk)
    back_filter = request.GET.get('filter', 'total')
    if request.method == 'POST':
        form = AdminMarketListEditForm(request.POST, instance=market_list)
        if form.is_valid():
            form.save()
            return redirect(reverse('management_dashboard') + '?filter=' + back_filter)
    else:
        form = AdminMarketListEditForm(instance=market_list)
    return render(request, 'shop/admin_edit_list.html', {
        'form': form,
        'market_list': market_list,
        'back_filter': back_filter,
    })


def _ai_organize_list(content):
    """AI-style organization: clean lines, remove dupes, number with Bengali numerals."""
    if not content or not content.strip():
        return content or ""
    bengali_digits = '০১২৩৪৫৬৭৮৯'
    lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
    seen = set()
    unique = []
    for ln in lines:
        key = ln.lower().strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(ln)
    result = []
    for i, ln in enumerate(unique, 1):
        num = ''.join(bengali_digits[int(d)] for d in str(i))
        result.append(f"{num}. {ln}")
    return '\n'.join(result)


@staff_member_required(login_url='management_login')
def list_entry_all_pdf(request):
    """Download all lists from list entry as a single PDF. Uses fpdf2 for proper Bengali font."""
    filter_status = request.GET.get('filter', 'total')
    lists = MarketList.objects.all().select_related('family')
    if filter_status == 'approved':
        lists = lists.filter(status='approved')
    elif filter_status == 'pending':
        lists = lists.filter(status='pending')
    for lst in lists:
        try:
            lst.user_display_name = lst.family.family_profile.display_name or lst.family.username
        except FamilyProfile.DoesNotExist:
            lst.user_display_name = lst.family.username

    from .pdf_utils import generate_list_entry_pdf_fpdf2
    pdf_bytes = generate_list_entry_pdf_fpdf2(list(lists))
    if pdf_bytes:
        response = HttpResponse(bytes(pdf_bytes), content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="list-entry-all.pdf"'
        return response

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from .pdf_utils import get_pdf_styles, safe_paragraph, safe_paragraph_bold
        from io import BytesIO
    except ImportError:
        return HttpResponse('PDF জেনারেট করতে reportlab ইনস্টল করুন', status=501)
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    st = get_pdf_styles()
    story = []
    story.append(safe_paragraph(st['title'], 'লিস্ট এন্ট্রি - সব লিস্ট (পিডিএফ)'))
    story.append(Spacer(1, 16))
    for idx, lst in enumerate(lists, 1):
        name = getattr(lst, 'user_display_name', lst.family.username)
        story.append(safe_paragraph_bold(st['heading'], f'সিরিয়াল: {idx} | লিস্ট: {lst.list_id} | ব্যবহারকারী: {name}'))
        story.append(safe_paragraph(st['body'], f'তারিখ: {lst.created_at.strftime("%d/%m/%Y %H:%M") if lst.created_at else "-"}'))
        story.append(safe_paragraph_bold(st['body'], 'মূল লিস্ট:'))
        story.append(safe_paragraph(st['body'], lst.content or '—'))
        if lst.ai_content:
            story.append(safe_paragraph_bold(st['body'], 'AI লিস্ট:'))
            story.append(safe_paragraph(st['body'], lst.ai_content))
        story.append(Spacer(1, 14))
    doc.build(story)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="list-entry-all.pdf"'
    return response


def _strip_number_prefix(line):
    """Remove leading '১. ' or '1. ' style prefix from line."""
    import re
    return re.sub(r'^[\d০-৯]+[.\s]+', '', line).strip()


def _number_with_bengali(lines):
    """Number lines with Bengali numerals. Keeps duplicates (same point can appear multiple times)."""
    if not lines:
        return []
    bengali_digits = '০১২৩৪৫৬৭৮৯'
    result = []
    for i, ln in enumerate(lines, 1):
        num = ''.join(bengali_digits[int(d)] for d in str(i))
        result.append(f"{num}. {ln}")
    return result


def _get_merged_items_from_lists(lists):
    """Merge all AI list lines from lists. Same points listed multiple times (no dedupe)."""
    all_lines = []
    for lst in lists:
        src = lst.ai_content or ''
        if src:
            for line in src.strip().splitlines():
                line = _strip_number_prefix(line.strip())
                if line:
                    all_lines.append(line)
    return _number_with_bengali(all_lines) if all_lines else []


@staff_member_required(login_url='management_login')
def list_entry_user_view(request):
    """User View: bazar lists grouped by user name, with order count badge. Click user to see lists."""
    filter_status = request.GET.get('filter', 'total')
    lists = MarketList.objects.all().select_related('family')
    if filter_status == 'approved':
        lists = lists.filter(status='approved')
    elif filter_status == 'pending':
        lists = lists.filter(status='pending')
    # filter=total or default: show all orders
    users_data = {}
    for lst in lists:
        try:
            display_name = lst.family.family_profile.display_name or lst.family.username
        except FamilyProfile.DoesNotExist:
            display_name = lst.family.username
        uid = lst.family_id
        if uid not in users_data:
            users_data[uid] = {'display_name': display_name, 'lists': []}
        users_data[uid]['lists'].append({
            'pk': lst.pk,
            'list_id': lst.list_id or f'Pack-{lst.pk}',
            'created_at': lst.created_at,
            'status': lst.get_status_display(),
            'content': lst.content or '',
            'ai_content': lst.ai_content or '',
        })
    users_list = [
        {'user_id': uid, 'display_name': data['display_name'], 'count': len(data['lists']), 'lists': data['lists']}
        for uid, data in users_data.items()
    ]
    users_list.sort(key=lambda x: (x['display_name'].upper(), x['user_id']))
    return render(request, 'shop/list_entry_user_view.html', {
        'users_list': users_list,
        'filter_status': filter_status,
    })


@staff_member_required(login_url='management_login')
def list_entry_consolidated(request):
    """Consolidated list: all market list points merged, one list with Bengali numbering."""
    filter_status = request.GET.get('filter', 'total')
    lists = MarketList.objects.all().select_related('family')
    if filter_status == 'approved':
        lists = lists.filter(status='approved')
    elif filter_status == 'pending':
        lists = lists.filter(status='pending')
    merged_lines = _get_merged_items_from_lists(list(lists))
    return render(request, 'shop/list_entry_consolidated.html', {
        'merged_items': merged_lines,
        'filter_status': filter_status,
    })


@staff_member_required(login_url='management_login')
def list_entry_consolidated_pdf(request):
    """Download consolidated list as PDF."""
    filter_status = request.GET.get('filter', 'total')
    lists = MarketList.objects.all().select_related('family')
    if filter_status == 'approved':
        lists = lists.filter(status='approved')
    elif filter_status == 'pending':
        lists = lists.filter(status='pending')
    merged_lines = _get_merged_items_from_lists(list(lists))
    from .pdf_utils import generate_consolidated_pdf_fpdf2
    from datetime import date
    dt = date.today()
    pdf_bytes = generate_consolidated_pdf_fpdf2(merged_lines, dt, title='Consolidated List', pre_numbered=True)
    if pdf_bytes:
        response = HttpResponse(bytes(pdf_bytes), content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="consolidated-list.pdf"'
        return response
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
    story = [safe_paragraph(st['title'], 'সম্মিলিত লিস্ট'), Spacer(1, 16)]
    for line in merged_lines:
        story.append(safe_paragraph(st['body'], line))
        story.append(Spacer(1, 4))
    doc.build(story)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="consolidated-list.pdf"'
    return response


@staff_member_required(login_url='management_login')
@require_GET
def ai_generate_list(request, pk):
    market_list = get_object_or_404(MarketList, pk=pk)
    generated = _ai_organize_list(market_list.content)
    market_list.ai_content = generated
    market_list.save(update_fields=['ai_content'])
    return JsonResponse({'success': True, 'content': generated})


# --- List comment thread (management + user) ---

@login_required
@xframe_options_sameorigin
def list_comment_thread(request, pk):
    """View and add comments on a market list. Allowed: list owner or staff."""
    market_list = get_object_or_404(MarketList, pk=pk)
    if not request.user.is_staff and market_list.family_id != request.user.id:
        return redirect('family_dashboard')
    comments = market_list.comments.select_related('author').order_by('created_at')
    form = MarketListCommentForm()
    if request.method == 'POST':
        form = MarketListCommentForm(request.POST)
        if form.is_valid():
            MarketListComment.objects.create(market_list=market_list, author=request.user, body=form.cleaned_data['body'])
            embed = request.GET.get('embed') == '1'
            url = reverse('list_comment_thread', kwargs={'pk': pk})
            if embed:
                url += '?embed=1'
            return redirect(url)
    back_url = request.GET.get('back') or request.META.get('HTTP_REFERER') or (reverse('management_dashboard') if request.user.is_staff else reverse('family_dashboard'))
    embed = request.GET.get('embed') == '1'
    return render(request, 'shop/list_comment_thread.html', {
        'market_list': market_list, 'comments': comments, 'form': form, 'back_url': back_url, 'embed': embed,
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


# --- Notice (already in dashboard; update via management_dashboard form)
