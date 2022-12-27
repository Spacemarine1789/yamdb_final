from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_admin or request.user.is_superuser)


class IsAdminOrReadOnly(permissions.BasePermission):
    """Permissions for change or delete Admin only"""
    message = 'Данное действие разрешено только администратору!'

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        return bool(
            request.user and request.user.is_authenticated
            and (request.user.is_admin or request.user.is_superuser)
        )


class IsStaffOrAuthorOrReadOnly(permissions.BasePermission):
    """Permissions for change or delete Admin, Moderator or Author only"""
    message = 'Данное действие разрешено администратору, модератору или автору'

    def has_permission(self, request, view):
        return (request.method in permissions.SAFE_METHODS
                or request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(
            request.user.is_superuser
            or request.user.is_admin
            or request.user.is_moderator
            or obj.author == request.user
        )
