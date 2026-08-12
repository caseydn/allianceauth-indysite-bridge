import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import redirect

from .models import IndustrySiteAccount
from .tasks import deactivate_account, push_account

logger = logging.getLogger(__name__)

SERVICES_PAGE = "services:services"


@login_required
@permission_required("industrysite.access_industrysite")
def activate(request):
    IndustrySiteAccount.objects.get_or_create(user=request.user)
    push_account.delay(request.user.pk, activate=True)
    messages.success(
        request,
        "Industry Site registration sent. Your characters will appear on the "
        "site shortly.",
    )
    return redirect(SERVICES_PAGE)


@login_required
def deactivate(request):
    if IndustrySiteAccount.objects.filter(user=request.user).exists():
        deactivate_account.delay(request.user.pk)
        messages.success(request, "Industry Site account disconnected.")
    return redirect(SERVICES_PAGE)
