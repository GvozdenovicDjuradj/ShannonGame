from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.auth.models import User

# Create your models here.
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    games_won_as_connect = models.IntegerField(default=0)
    games_won_as_cut = models.IntegerField(default=0)
    games_lost_as_connect = models.IntegerField(default=0)
    games_lost_as_cut = models.IntegerField(default=0)
    number_of_achievements = models.IntegerField(default=0)
    rating = models.IntegerField(default=0)
    consecutive_logins = models.IntegerField(default=0)
    consecutive_logins_max = models.IntegerField(default=0)

    def __str__(self):
        return self.name


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


class Board(models.Model):
    board_alias = models.CharField(max_length=200)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="creator")
    nodes_configuration = models.TextField()
    edges_configuration = models.TextField()


class Game(models.Model):
    PLAYER_WON = (
        (0, "connect"),
        (1, "cut")
    )
    cut_player = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cut")
    connect_player = models.ForeignKey(User, on_delete=models.CASCADE, related_name="connect")
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name="board")
    edges_configuration = models.TextField()
    player_won = models.IntegerField(choices=PLAYER_WON)
    timestamp = models.BigIntegerField()

    def __str__(self):
        pass


class Achievement(models.Model):
    DESCRIPTIONS = (
        (0, "10 wins"),
        (1, "50 wins"),
        (2, "100 wins"),
        (3, "5 consecutive wins"),
        (4, "10 consecutive wins"),
        (5, "50 consecutive wins"),
        (6, "50 games played"),
        (7, "100 games played"),
        (8, "500 games played"),
        # (9, "#1 rating"),
        # (10, "#2 rating"),
        # (11, "#3 rating"),
        (12, "7 days consecutive logins"),
        (13, "14 days consecutive logins"),
        (14, "31 days consecutive logins")
    )
    EXPLANATION = (
        (0, "You have won 10 games in total"),
        (1, "You have won 50 games in total"),
        (2, "You have won 100 games in total"),
        (3, "You have won 5 games in a row, without loosing a single one"),
        (4, "You have won 10 games in a row, without loosing a single one"),
        (5, "You have won 50 games in a row, without loosing a single one"),
        (6, "You have played 50 games in total"),
        (7, "You have played 100 games in total"),
        (8, "You have played 500 games in total"),
        # (9, "You have occurred on the first place in rating leaderboard at least once"),
        # (10, "You have occurred on the second place in rating leaderboard at least once"),
        # (11, "You have occurred on the third place in rating leaderboard at least once"),
        (12, "You have logged in 7 days in a row"),
        (13, "You have logged in 14 days in a row"),
        (14, "You have logged in 31 days in a row")
    )
    explanation = models.IntegerField(choices=EXPLANATION)
    value = models.IntegerField(choices=DESCRIPTIONS)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.value
