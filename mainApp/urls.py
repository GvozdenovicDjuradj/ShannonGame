from django.urls import path

from .views import register_page, login_page, index, logout_user, game, load_game, resign, get_boards, \
    check_log_in_achievement, users_ratings, users_wins, users_achievements, users_max_logins, profile

urlpatterns = [
    path('app/', index, name='index'),
    path('app/profile.html/', profile, name='profile'),
    path('app/game.html/<str:alias>', game, name='game'),
    path('login/', login_page, name="login"),
    path('logout/', logout_user, name="logout"),
    path('register/', register_page, name="register"),
    path('loadGraph/', load_game, name='load_game'),
    path('resign/', resign, name='resign'),
    path('boards/', get_boards, name="get_boards"),
    path('newAchievement/', check_log_in_achievement, name="check_log_in_achievement"),
    path('usersRatings/', users_ratings, name="users_ratings"),
    path('usersWins/', users_wins, name="users_wins"),
    path('usersAchievements/', users_achievements, name="users_achievements"),
    path('usersMaxLogins/', users_max_logins, name="users_max_logins")

]
