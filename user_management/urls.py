from django.urls import path

from . import views

#app_name = 'user_management'
urlpatterns = [
    path('', views.SiteUserListView.as_view(), name='index'),
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('<int:pk>/', views.SiteUserUpdateView.as_view(), name='update'),
    path('login/',  views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('profile/', views.SiteUserProfileView.as_view(), name='profile'),
]

#from django.contrib.auth import views
#
#urlpatterns += [
#
#    path('password_change/', views.PasswordChangeView.as_view(), name='password_change'),
#    path('password_change/done/', views.PasswordChangeDoneView.as_view(), name='password_change_done'),
#
#    path('password_reset/', views.PasswordResetView.as_view(), name='password_reset'),
#    path('password_reset/done/', views.PasswordResetDoneView.as_view(), name='password_reset_done'),
#    path('reset/<uidb64>/<token>/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
#    path('reset/done/', views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
#]