from django.contrib.auth import get_user_model
from rest_framework import permissions, viewsets

from rest_api.serializers import UserSerializer


# ViewSets define the view behavior.
class UserViewSet(viewsets.ModelViewSet):
    """API endpoint for viewing and managing SiteUser records."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return all users for staff; restrict standard users to their own record."""
        user_model = get_user_model()
        user = self.request.user
        if not user.is_authenticated:
            return user_model.objects.none()
        if user.is_staff:
            return user_model.objects.all().order_by('id')
        return user_model.objects.filter(pk=user.pk).order_by('id')

