import json

import redis
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from redisgraph import Graph
import time

from mainApp.views import INITIAL, CONNECT, CUT
from mainApp.models import Board, Game, Profile, Achievement
from django.contrib.auth.models import User


class GameConsumer(WebsocketConsumer):
    def connect(self):
        self.board_number = self.scope['url_route']['kwargs']['board_number']
        self.room_group_name = 'game_%s' % self.board_number

        # Join room group
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )

        self.accept()

    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    def receive(self, text_data):

        if self.scope["session"]["started"]:
            data = json.loads(text_data)
            if "resigned" in data:
                r = redis.Redis(host='localhost', port=6379, db=self.scope["session"]["board_id"])
                redis_graph = Graph('shannon', r)
                game_finished = True
                if self.scope["session"]["player_role"] == CONNECT:
                    cut_won = True
                    connect_won = False
                    message = "Connect player resigned the game. Cut player wins"
                else:
                    cut_won = False
                    connect_won = True
                    message = "Cut player resigned the game. Connect player wins"
                self.store_game(redis_graph, True)
                self.exit_game()
                async_to_sync(self.channel_layer.group_send)(self.room_group_name,
                                                             dict(
                                                                 type="move_message", message=
                                                                 dict(message=message,
                                                                      source=None,
                                                                      target=None,
                                                                      player=None,
                                                                      game_finished=game_finished,
                                                                      connect_won=connect_won,
                                                                      cut_won=cut_won))
                                                             )

            if self.scope["session"]["player_to_move"] == self.scope["session"]["player_role"]:
                message = ""
                game_finished = False
                source = data["link"]["source"]
                target = data["link"]["target"]

                r = redis.Redis(host='localhost', port=6379, db=self.scope["session"]["board_id"])
                redis_graph = Graph('shannon', r)

                edge = redis_graph.query(
                    """match({number: """ + str(source) + """})-[rel]-({number:""" + str(target) + """}) return rel""")

                if len(edge.result_set) == 1 and edge.result_set[0][0].relation == INITIAL:
                    # obrada odigranog poteza
                    new_state = self.scope["session"]["player_role"]
                    current_time = str(int(time.time() * 1000))
                    redis_graph.query("""match (n {number:""" + str(source) + """}) -[r]->(m{number:""" + str(target) + """}) 
                                         create (n)-[r2:""" + new_state + """ {time: """ + current_time + """ }""" + """]->(m)
                                         delete r""")
                    cut_won = False
                    connect_won = False
                    connect_or_initial_path = redis_graph.query(
                        """match p = ({type: 'START'})-[:connect|:initial*1..100]-({type:'FINISH'}) return p""").result_set

                    if len(connect_or_initial_path) == 0:
                        cut_won = True
                        game_finished = True
                        message = "cut player has won the game"
                        self.store_game(redis_graph)
                        self.exit_game()
                    else:
                        connect_path = redis_graph.query(
                            """match p = ({type:'START'})-[:connect*1..100]-({type:'FINISH'}) return p""").result_set
                        if len(connect_path) > 0:
                            connect_won = True
                            game_finished = True
                            message = "connect player has won the game"
                            self.store_game(redis_graph)
                            self.exit_game()
                        else:
                            message = "game goes on"

                    async_to_sync(self.channel_layer.group_send)(self.room_group_name,
                                                                 dict(
                                                                     type="move_message", message=
                                                                     dict(message=message,
                                                                          source=source,
                                                                          target=target,
                                                                          player=new_state,
                                                                          game_finished=game_finished,
                                                                          connect_won=connect_won,
                                                                          cut_won=cut_won))
                                                                 )
        #         else:
        #             async_to_sync(self.channel_layer.group_send)(self.room_group_name,
        #                                                          dict(type="move_message",
        #                                                               message=dict(message="invalid move")))
        #     else:
        #         async_to_sync(self.channel_layer.group_send)(self.room_group_name,
        #                                                      dict(type="move_message",
        #                                                           message=dict(message="invalid move")))
        # else:
        #     async_to_sync(self.channel_layer.group_send)(self.room_group_name,
        #                                                  dict(type="move_message", message=dict(message="invalid move"))
        #                                                  )

    # Receive message from room group
    def move_message(self, event):
        if self.scope["session"]["player_to_move"] == CONNECT:
            self.scope["session"]["player_to_move"] = CUT
        else:
            self.scope["session"]["player_to_move"] = CONNECT
        self.scope["session"].save()
        message = event['message']
        if message["game_finished"]:
            self.exit_game()
        # Send message to WebSocket
        self.send(text_data=json.dumps({
            'message': message
        }))

    def achievement_message(self, event):
        message = event['message']
        self.send(text_data=json.dumps({
            'message': message
        }))

    def restart_session(self):
        self.scope["session"]["started"] = False
        self.scope["session"]["board_id"] = None
        self.scope["session"]["player_role"] = None
        self.scope["session"].save()

    def exit_game(self):
        r = redis.Redis(host='localhost', port=6379, db=self.scope["session"]["board_id"])
        redis_graph = Graph('shannon', r)
        redis_graph.query("""match(n) delete n""")
        self.restart_session()

    def store_game(self, redis_graph, resigned=False):
        r = redis.Redis(host='localhost', port=6379, db=0)
        players = json.loads(r.get(f"game_" + str(self.scope["session"]["board_id"])))

        game_graph_edges = redis_graph.query("Match (n)-[r]->(m)Return r").result_set
        db_edges = []
        for edge in game_graph_edges:
            db_edges.append(dict(
                source=edge[0].src_node,
                target=edge[0].dest_node,
                state=edge[0].relation,
                order=edge[0].id,
                time=edge[0].properties["time"]
            ))
        player_won = 0 if self.scope["session"]["player_role"] == "connect" else 1
        if resigned:
            player_won = 1 - player_won
        cut_player = User.objects.get(id=players[1])
        connect_player = User.objects.get(id=players[0])
        board = Board.objects.get(id=self.scope["session"]["db_board_id"])
        new_game = Game(cut_player=cut_player, connect_player=connect_player, board=board,
                        edges_configuration=json.dumps(db_edges), player_won=player_won,
                        timestamp=str(int(time.time() * 1000)))
        new_game.save()

        self.update_users_stats(cut_player, connect_player, player_won)

        users_achievements = {
            CONNECT: self.check_achievements(connect_player),
            CUT: self.check_achievements(cut_player)
        }
        async_to_sync(self.channel_layer.group_send)(self.room_group_name, dict(type="achievement_message",
                                                                                message=dict(
                                                                                    achievements=users_achievements)))

    def update_users_stats(self, cut_player: User, connect_player: User, player_won: int):

        connect_player_profile: Profile = connect_player.profile
        cut_player_profile: Profile = cut_player.profile
        if player_won == 0:
            connect_player_profile.games_won_as_connect += 1
            cut_player_profile.games_lost_as_cut += 1
        else:
            connect_player_profile.games_lost_as_connect += 1
            cut_player_profile.games_won_as_cut += 1

        self.update_user_rating(connect_player)
        self.update_user_rating(cut_player)
        connect_player_profile.save()
        cut_player_profile.save()

    def check_achievements(self, player: User):

        new_achievements = []
        user_achievements = [achievement for achievement in Achievement.objects.filter(user_id=player.id)]
        achievement_values = [achievement.value for achievement in user_achievements]
        user_games = [game for game in Game.objects.filter(cut_player=player.id)]
        user_games += [game for game in Game.objects.filter(connect_player=player.id)]
        user_games.sort(key=lambda x: x.timestamp)

        games_won = player.profile.games_won_as_connect + player.profile.games_won_as_cut
        games_played = games_won + player.profile.games_lost_as_connect + player.profile.games_lost_as_cut

        consecutive_games_won = 0
        current_sequence = 0
        for game in user_games:
            if game.player_won == 0:
                user_won = game.connect_player
            else:
                user_won = game.cut_player
            if user_won.id == player.id:
                current_sequence += 1
            else:
                consecutive_games_won = max(consecutive_games_won, current_sequence)
                current_sequence = 0
        consecutive_games_won = max(consecutive_games_won, current_sequence)

        if games_played > 4:
            if consecutive_games_won > 4:
                if 3 not in achievement_values:
                    new_consecutive_wins_achievement = Achievement(explanation=3, value=3, user_id=player)
                    new_consecutive_wins_achievement.save()
                    player.profile.number_of_achievements += 1
                    player.profile.save()
                    new_achievements.append(3)
            if games_played > 9:
                if games_won > 9:
                    if 0 not in achievement_values:
                        new_total_wins_achievement = Achievement(explanation=0, value=0, user_id=player)
                        new_total_wins_achievement.save()
                        player.profile.number_of_achievements += 1
                        player.profile.save()
                        new_achievements.append(0)
                if consecutive_games_won > 9:
                    if 4 not in achievement_values:
                        new_consecutive_wins_achievement = Achievement(explanation=4, value=4, user_id=player)
                        new_consecutive_wins_achievement.save()
                        player.profile.number_of_achievements += 1
                        player.profile.save()
                        new_achievements.append(4)
                if games_played > 49:
                    if games_won > 49:
                        if 1 not in achievement_values:
                            new_total_wins_achievement = Achievement(explanation=1, value=1, user_id=player)
                            new_total_wins_achievement.save()
                            player.profile.number_of_achievements += 1
                            player.profile.save()
                            new_achievements.append(1)
                    if consecutive_games_won > 49:
                        if 5 not in achievement_values:
                            new_consecutive_wins_achievement = Achievement(explanation=5, value=5, user_id=player)
                            new_consecutive_wins_achievement.save()
                            player.profile.number_of_achievements += 1
                            player.profile.save()
                            new_achievements.append(5)
                    if 6 not in achievement_values:
                        new_total_games_achievement = Achievement(explanation=6, value=6, user_id=player)
                        new_total_games_achievement.save()
                        player.profile.number_of_achievements += 1
                        player.profile.save()
                        new_achievements.append(6)
                    if games_played > 99:
                        if games_won > 99:
                            if 2 not in achievement_values:
                                new_total_wins_achievement = Achievement(explanation=2, value=2, user_id=player)
                                new_total_wins_achievement.save()
                                player.profile.number_of_achievements += 1
                                player.profile.save()
                                new_achievements.append(2)
                        if 7 not in achievement_values:
                            new_total_games_achievement = Achievement(explanation=7, value=7, user_id=player)
                            new_total_games_achievement.save()
                            player.profile.number_of_achievements += 1
                            player.profile.save()
                            new_achievements.append(7)
                        if games_played > 499:
                            if 8 not in achievement_values:
                                new_total_games_achievement = Achievement(explanation=8, value=8, user_id=player)
                                new_total_games_achievement.save()
                                player.profile.number_of_achievements += 1
                                player.profile.save()
                                new_achievements.append(8)
        if len(new_achievements) > 0:
            self.update_user_rating(player)
        return new_achievements

    def update_user_rating(self, player: User):
        player_profile: Profile = player.profile
        games_played = player_profile.games_won_as_connect + player_profile.games_won_as_cut + player_profile.games_lost_as_connect + player_profile.games_lost_as_cut
        player_profile.rating = 100 * (player_profile.games_won_as_connect + player_profile.games_won_as_cut) - 10 * (
                player_profile.games_lost_as_connect + player_profile.games_lost_as_cut) + games_played * player_profile.number_of_achievements
        player.profile.save()


""" 
    CREATE (a0:a0{number:0,type:"START"}),(a1:a1{number:1,type:"NODE"}),(a2:a2{number:2,type:"NODE"}),
    (a3:a3{number:3,type:"NODE"}),(a4:a4{number:4,type:"NODE"}),(a5:a5{number:5,type:"NODE"}),
    (a6:a6{number:6,type:"NODE"}),(a7:a7{number:7,type:"NODE"}),(a8:a8{number:8,type:"FINISH"}),
    (a0:a0{number:0,type:"START"})-[:initial{time:1}]->(a5:a5{number:5,type:"NODE"}),(a0:a0{number:0,type:"START"})-
    [:initial{time:1}]->(a4:a4{number:4,type:"NODE"}),(a0:a0{number:0,type:"START"})-
    [:initial{time:1}]->(a7:a7{number:7,type:"NODE"}),(a1:a1{number:1,type:"NODE"})-
    [:initial{time:1}]->(a6:a6{number:6,type:"NODE"}),(a1:a1{number:1,type:"NODE"})-
    [:initial{time:1}]->(a4:a4{number:4,type:"NODE"}),(a1:a1{number:1,type:"NODE"})-
    [:initial{time:1}]->(a8:a8{number:8,type:"FINISH"}),(a2:a2{number:2,type:"NODE"})-
    [:initial{time:1}]->(a3:a3{number:3,type:"NODE"}),(a2:a2{number:2,type:"NODE"})-
    [:initial{time:1}]->(a4:a4{number:4,type:"NODE"}),(a2:a2{number:2,type:"NODE"})-
    [:initial{time:1}]->(a7:a7{number:7,type:"NODE"}),(a3:a3{number:3,type:"NODE"})-
    [:initial{time:1}]->(a4:a4{number:4,type:"NODE"}),(a3:a3{number:3,type:"NODE"})-
    [:initial{time:1}]->(a8:a8{number:8,type:"FINISH"}),(a5:a5{number:5,type:"NODE"})-
    [:initial{time:1}]->(a4:a4{number:4,type:"NODE"}),(a5:a5{number:5,type:"NODE"})-
    [:initial{time:1}]->(a6:a6{number:6,type:"NODE"}),(a6:a6{number:6,type:"NODE"})-
    [:initial{time:1}]->(a4:a4{number:4,type:"NODE"}),(a7:a7{number:7,type:"NODE"})-
    [:initial{time:1}]->(a4:a4{number:4,type:"NODE"}),(a8:a8{number:8,type:"FINISH"})-
    [:initial{time:1}]->(a4:a4{number:4,type:"NODE"})
"""





