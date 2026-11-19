from rest_framework import routers

from rest_api.views import UserViewSet

# Routers provide an easy way of automatically determining the URL conf.
router = routers.DefaultRouter()
router.register(r'users', UserViewSet, basename='siteuser')

app_name = 'rest_api'

# Wire up our API using automatic URL routing.
urlpatterns = router.urls
