from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    """
    Grants access to superusers/staff outright, otherwise requires the
    specific admin permission named in `required_permission`.
    """

    required_permission = None

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_staff or user.is_superuser:
            return True

        return user.has_perm(f'users.{self.required_permission}')


class PodeAprovarPagamento(IsAdminUser):
    required_permission = 'aprovar_pagamento'


class PodeRealizarCheckin(IsAdminUser):
    required_permission = 'realizar_checkin'
