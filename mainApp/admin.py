from django.contrib import admin

from .models import User, Game, Profile, Board, Achievement

# Register your models here.

admin.site.register(Profile)
admin.site.register(Game)
admin.site.register(Board)
admin.site.register(Achievement)

