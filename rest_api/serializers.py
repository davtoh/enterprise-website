from django.contrib.auth import get_user_model
from rest_framework import serializers


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
        super().__init__(*args, **kwargs)

        context = kwargs.get('context') or {}
        request = context.get('request')
        if request is not None:
            tabs = request.query_params.getlist('val', [])
            if tabs:
                included = set(tabs)
                existing = set(self.fields.keys())
                for other in existing - included:
                    self.fields.pop(other)

    # view_name must be set with the instance name (app_name here or namespace in father), in this case rest_api:
    url = serializers.HyperlinkedIdentityField(view_name="rest_api:siteuser-detail")  # this fails if user model changes

    class Meta:
        model = get_user_model()
        # fields = '__all__'
        fields = [
            'url',
            'username',
            'first_name',
            'last_name',
            'email',
            'birthdate',
            'phone_number',
            'is_staff',
            'is_superuser',
        ]
