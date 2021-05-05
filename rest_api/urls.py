from django.urls import path, include
from django.contrib.auth import get_user_model
from rest_framework import routers, serializers, viewsets


# Serializers define the API representation.
class UserSerializer(serializers.HyperlinkedModelSerializer):
    """
    http://127.0.0.1:8000/rest_api/users/?val=username&val=email
    TODO, escalate to apply to any model automatically
    Two ideas:
        1. rest_api maps all models completely except itself
        2. make a decorator to automatically create serializer and viewSet and mapped in router
    """

    def __init__(self, *args, **kwargs):
        # https://django.cowhite.com/blog/dynamically-includeexclude-fields-to-django-rest-framwork-serializers-based-on-user-requests/
        super(UserSerializer, self).__init__(*args, **kwargs)

        if 'context' in kwargs:
            if 'request' in kwargs['context']:
                tabs = kwargs['context']['request'].query_params.getlist('val', [])
                if tabs:
                    # tabs = tabs.split(',')
                    included = set(tabs)
                    existing = set(self.fields.keys())

                    for other in existing - included:
                        self.fields.pop(other)

    # view_name must be set with the instance name (app_name here or namespace in father), in this case rest_api:
    url = serializers.HyperlinkedIdentityField(view_name="rest_api:siteuser-detail")  # this fails if user model changes

    class Meta:
        model = get_user_model()
        # fields = '__all__'
        fields = ['url', 'username', 'first_name', 'last_name', 'email', 'birthdate', 'phone_number', 'is_staff', 'is_superuser']


# ViewSets define the view behavior.
class UserViewSet(viewsets.ModelViewSet):
    queryset = get_user_model().objects.all()
    serializer_class = UserSerializer


# Routers provide an easy way of automatically determining the URL conf.
router = routers.DefaultRouter()
router.register(r'users', UserViewSet)  # specify explicitly if queryset not provided in View with basename='siteuser'


app_name = 'rest_api'

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.

urlpatterns = router.urls
#urlpatterns = [ path('', include(router.urls)),]