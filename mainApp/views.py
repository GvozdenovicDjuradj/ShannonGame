import datetime
from typing import List, Dict

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render, redirect

# Create your views here.
from django.http import HttpResponse
from django.template import loader

from djangoProject.forms import CreateUserForm
from mainApp.models import Board, Achievement

import json
import redis
from redisgraph import Node, Edge, Graph, Path

CONNECT = "connect"
CUT = "cut"
INITIAL = "initial"

achievement_explanations_and_descriptions = {
    0: ["10 wins", "You have won 10 games in total"],
    1: ["50 wins", "You have won 50 games in total"],
    2: ["100 wins", "You have won 100 games in total"],
    3: ["5 consecutive wins", "You have won 5 games in a row, without loosing a single one"],
    4: ["10 consecutive wins", "You have won 10 games in a row, without loosing a single one"],
    5: ["50 consecutive wins", "You have won 50 games in a row, without loosing a single one"],
    6: ["50 games played", "You have played 50 games in total"],
    7: ["100 games played", "You have played 100 games in total"],
    8: ["500 games played", "You have played 500 games in total"],
    # (9, "#1 rating"),
    # (10, "#2 rating"),
    # (11, "#3 rating"),
    12: ["7 days consecutive logins", "You have logged in 7 days in a row"],
    13: ["14 days consecutive logins", "You have logged in 14 days in a row"],
    14: ["31 days consecutive logins", "You have logged in 31 days in a row"]
}

"""
Session should include fields:
started - indicating weather the game is started
board_id - redis graph db id, referencing the current state on the board
player_role - cut/connect
"""

"""
redis keys needed:
latest_id: number of active games
new_games: Dict[<board_id>, Dict(empty fo now)[<>,<>]]
            
"""


# dummy_node_data = None
# dummy_node_data = [
#     {"number": 0, "type": "START"},
#     {"number": 1, "type": "NODE"},
#     {"number": 2, "type": "NODE"},
#     {"number": 3, "type": "NODE"},
#     {"number": 4, "type": "NODE"},
#     {"number": 5, "type": "NODE"},
#     {"number": 6, "type": "NODE"},
#     {"number": 7, "type": "NODE"},
#     {"number": 8, "type": "FINISH"}
# ]
# dummy_edge_data = None
# dummy_edge_data = [
#     {"source": 0, "target": 1, "state": INITIAL, "order": 1},
#     {"source": 1, "target": 2, "state": CUT, "order": 2},
#     {"source": 3, "target": 4, "state": CONNECT, "order": 3},
#     {"source": 4, "target": 5, "state": CUT, "order": 4},
#     {"source": 6, "target": 7, "state": CONNECT, "order": 5},
#     {"source": 7, "target": 8, "state": INITIAL, "order": 6},
#     {"source": 0, "target": 3, "state": CUT, "order": 7},
#     {"source": 3, "target": 6, "state": CONNECT, "order": 8},
#     {"source": 1, "target": 4, "state": INITIAL, "order": 9},
#     {"source": 4, "target": 7, "state": CUT, "order": 10},
#     {"source": 2, "target": 5, "state": CONNECT, "order": 11},
#     {"source": 5, "target": 8, "state": INITIAL, "order": 12}
# ]

# dummy_edge_data = [
#     {"source": 0, "target": 1, "state": INITIAL, "order": 1},
#     {"source": 1, "target": 2, "state": INITIAL, "order": 2},
#     {"source": 3, "target": 4, "state": INITIAL, "order": 3},
#     {"source": 4, "target": 5, "state": INITIAL, "order": 4},
#     {"source": 6, "target": 7, "state": INITIAL, "order": 5},
#     {"source": 7, "target": 8, "state": INITIAL, "order": 6},
#     {"source": 0, "target": 3, "state": INITIAL, "order": 7},
#     {"source": 3, "target": 6, "state": INITIAL, "order": 8},
#     {"source": 1, "target": 4, "state": INITIAL, "order": 9},
#     {"source": 4, "target": 7, "state": INITIAL, "order": 10},
#     {"source": 2, "target": 5, "state": INITIAL, "order": 11},
#     {"source": 5, "target": 8, "state": INITIAL, "order": 12}
# ]


@login_required(login_url='/login/')
def index(request):
    return HttpResponse(loader.get_template("mainApp/index.html").render())


@login_required(login_url='/login/')
def profile(request):
    user = User.objects.get(id=request.session["_auth_user_id"])
    achievements = Achievement.objects.filter(user_id=user.id)
    achievement_for_front = []
    for achievement in achievements:
        achievement_for_front.append(achievement_explanations_and_descriptions[achievement.value])
    profile = user.profile
    context = dict(
        last_login=user.last_login,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        date_joined=user.date_joined,
        games_lost_as_connect=profile.games_lost_as_connect,
        games_lost_as_cut=profile.games_lost_as_cut,
        games_won_as_connect=profile.games_won_as_connect,
        games_won_as_cut=profile.games_won_as_cut,
        number_of_achievements=profile.number_of_achievements,
        rating=profile.rating,
        consecutive_logins=profile.consecutive_logins,
        consecutive_logins_max=profile.consecutive_logins_max,
        achievements=achievement_for_front
    )
    return HttpResponse(loader.get_template("mainApp/profile.html").render(context))


def get_board_id(user_id: str):
    # TODO realise this as an atomic operation(use redis transactions)
    r = redis.Redis(host='localhost', port=6379, db=0)
    new_games = json.loads(r.get("new_games"))
    if len(new_games) == 0:
        new_db = int(r.get("latest_db")) + 1
        r.set("latest_db", new_db)
        new_games = {new_db: {}}
        r.set("new_games", json.dumps(new_games))
        r.set(f"game_{new_db}", json.dumps([user_id]))
        return new_db, True
    else:
        new_db = int(list(new_games.keys())[0])
        new_games.pop(str(new_db), None)
        r.set("new_games", json.dumps(new_games))
        ids = json.loads(r.get(f"game_{new_db}"))
        ids.append(user_id)
        r.set(f"game_{new_db}", json.dumps(ids))
        return new_db, False


@login_required(login_url='/login/')
def load_game(request):
    if request.method == 'GET':
        alias = request.session["board_alias"]
        board = Board.objects.get(board_alias=alias)
        request.session["db_board_id"] = board.id
        edge_data = json.loads(board.edges_configuration)
        node_data = json.loads(board.nodes_configuration)
        if "started" not in request.session:
            request.session["started"] = False
        else:
            board_id = request.session["board_id"]
            r = redis.Redis(host='localhost', port=6379, db=board_id)
            redis_graph = Graph('shannon', r)
            nodes = redis_graph.query("match(n) return n").result_set
            if len(nodes) == 0:
                request.session["started"] = False

        if request.session["started"]:
            board_id = request.session["board_id"]
            nodes, edges = get_graph_data(board_id)
            # restart_session(request)
            return HttpResponse(json.dumps(dict(nodes=nodes, edges=edges, role=request.session["player_role"])))

        else:
            request.session["started"] = True
            board_id, new_game = get_board_id(request.session._session["_auth_user_id"])
            request.session["board_id"] = board_id
            request.session["player_to_move"] = CONNECT
            if new_game:
                request.session["player_role"] = CONNECT
                post_graph(board_id, edge_data, node_data)
            else:
                request.session["player_role"] = CUT
            return HttpResponse(
                json.dumps(dict(nodes=node_data, edges=edge_data, role=request.session["player_role"],
                                board_number=board_id)))

    else:
        return HttpResponse(status=404)


@login_required(login_url='/login/')
def game(request, alias):
    request.session["board_alias"] = alias
    context = dict(
        board_name=alias,
    )
    return HttpResponse(loader.get_template("mainApp/game.html").render(context))


def register_page(request):
    if request.user.is_authenticated:
        return redirect('/app/')
    else:
        form = CreateUserForm()
        if request.method == 'POST':
            form = CreateUserForm(request.POST)
            if form.is_valid():
                form.save()
                user = form.cleaned_data.get('username')
                messages.success(request, 'Account was created for ' + user)

                return redirect('login')

        context = {'form': form}
        return render(request, 'accounts/register.html', context)


def login_page(request):
    if request.user.is_authenticated:
        return redirect('/app/')
    else:
        if request.method == 'POST':
            username = request.POST.get('username')
            password = request.POST.get('password')

            user = authenticate(request, username=username, password=password)

            if user is not None:
                last_login = user.last_login
                if user.last_login is None:
                    last_login = datetime.datetime.now()
                    user.last_login = last_login
                user.save()
                login(request, user)
                yesterday_time = datetime.datetime.now() - datetime.timedelta(days=1)
                if last_login.year == yesterday_time.year and last_login.month == yesterday_time.month and last_login.day == yesterday_time.day:
                    user.profile.consecutive_logins += 1
                    if user.profile.consecutive_logins > user.profile.consecutive_logins_max:
                        user.profile.consecutive_logins_max = user.profile.consecutive_logins
                else:
                    user.profile.consecutive_logins = 0
                user.profile.save()

                if user.profile.consecutive_logins_max > 6:
                    try:
                        logins_achievement_30 = Achievement.objects.get(value=12, user_id=user)
                    except:
                        logins_achievement_30 = None
                    if logins_achievement_30 is None:
                        new_logins_achievement = Achievement(explanation=12, value=12, user_id=user)
                        new_logins_achievement.save()
                        user.profile.number_of_achievements += 1
                        user.profile.save()
                        request.session["new_achievement"] = 12
                    if user.profile.consecutive_logins_max > 13:
                        try:
                            logins_achievement_30 = Achievement.objects.get(value=13, user_id=user)
                        except:
                            logins_achievement_30 = None
                        if logins_achievement_30 is None:
                            new_logins_achievement = Achievement(explanation=13, value=13, user_id=user)
                            new_logins_achievement.save()
                            user.profile.number_of_achievements += 1
                            user.profile.save()
                            request.session["new_achievement"] = 13
                        if user.profile.consecutive_logins_max > 30:
                            try:
                                logins_achievement_30 = Achievement.objects.get(value=14, user_id=user)
                            except:
                                logins_achievement_30 = None
                            if logins_achievement_30 is None:
                                new_logins_achievement = Achievement(explanation=14, value=14, user_id=user)
                                new_logins_achievement.save()
                                user.profile.number_of_achievements += 1
                                user.profile.save()
                                request.session["new_achievement"] = 14
                return redirect('/app/')
            else:
                messages.info(request, 'Username OR password is incorrect')

        context = {}
        return render(request, 'accounts/login.html', context)


@login_required()
def check_log_in_achievement(request):
    if request.method == 'GET':
        if "new_achievement" in request.session:
            achievement = request.session["new_achievement"]
            request.session.pop("new_achievement")
            if achievement > -1:
                return HttpResponse(json.dumps(dict(achievement=achievement)))
        return HttpResponse(json.dumps(dict(achievement=-1)))


@login_required()
def logout_user(request):
    logout(request)
    return redirect('login')


def post_graph(board_id: int, edge_data: List[Dict[str, object]], node_data: List[Dict[str, object]]):
    r = redis.Redis(host='localhost', port=6379, db=board_id)
    redis_graph = Graph('shannon', r)
    for node_element in node_data:
        number = "a" + str(node_element["number"])
        node = Node(label=number, properties=node_element, alias=number)
        redis_graph.add_node(node)

    for edge_element in edge_data:
        source = redis_graph.nodes["a" + str(edge_element["source"])]
        dest = redis_graph.nodes["a" + str(edge_element["target"])]
        edge = Edge(source, edge_element["state"], dest,
                    edge_id=edge_element["order"],
                    properties={"time": 1})
        redis_graph.add_edge(edge)

    redis_graph.commit()


def get_graph_data(board_id: int):
    r = redis.Redis(host='localhost', port=6379, db=board_id)
    redis_graph = Graph('shannon', r)
    redis_graph.query("""MATCH(n) RETURN n""")
    nodes = redis_graph.query("""MATCH(n) RETURN n""").result_set
    edges = redis_graph.query("""Match (n)-[r]->(m) Return n,r,m""").result_set
    nodes_data = []
    edges_data = []
    for node in nodes:
        nodes_data.append(dict(number=node[0].properties["number"], type=node[0].properties["type"]))

    for edge in edges:
        edge_dict = dict(
            source=edge[0].properties["number"],
            target=edge[2].properties["number"],
            state=edge[1].relation,
            order=edge[1].id
        )
        edges_data.append(edge_dict)
    return nodes_data, edges_data


# @login_required(login_url='/login/')
# def move(request):
#     if request.method == 'POST':
#         if request.session["started"]:
#             message = ""
#             game_finished = False
#             data = json.loads(request.body)
#             source = data["link"]["source"]
#             target = data["link"]["target"]
#
#             r = redis.Redis(host='localhost', port=6379, db=request.session["board_id"])
#             redis_graph = Graph('shannon', r)
#
#             edge = redis_graph.query(
#                 """match({number: """ + str(source) + """})-[rel]-({number:""" + str(target) + """}) return rel""")
#
#             if len(edge.result_set) == 1 and edge.result_set[0][0].relation == INITIAL:
#                 new_state = request.session["player_role"]
#                 redis_graph.query("""match (n {number:""" + str(source) + """}) -[r]->(m{number:""" + str(target) + """})
#                                      create (n)-[r2:""" + new_state + """]->(m)
#                                      delete r""")
#                 cut_won = False
#                 connect_won = False
#                 # TODO  change 1..12 with something meaningful
#                 connect_or_initial_path = redis_graph.query(
#                     """match p = ({type: 'START'})-[:connect|:initial*1..12]-({type:'FINISH'}) return p""").result_set
#
#                 if len(connect_or_initial_path) == 0:
#                     cut_won = True
#                     game_finished = True
#                     exit_game(request, redis_graph)
#                     message = "cut player has won the game"
#                 else:
#                     connect_path = redis_graph.query(
#                         """match p = ({type:'START'})-[:connect*1..12]-({type:'FINISH'}) return p""").result_set
#                     if len(connect_path) > 0:
#                         connect_won = True
#                         game_finished = True
#                         exit_game(request, redis_graph)
#                         message = "connect player has won the game"
#                     else:
#                         message = "game goes on"
#
#                 return HttpResponse(
#                     json.dumps(dict(message=message,
#                                     game_finished=game_finished,
#                                     connect_won=connect_won,
#                                     cut_won=cut_won)),
#                     status=200)
#             else:
#                 return HttpResponse(json.dumps(dict(message="invalid move")), status=300)
#         else:
#             return HttpResponse(json.dumps(dict(message="invalid move")), status=300)
#
#         # query = """MATCH(n) RETURN n"""
#         # result = redis_graph.query(query)
#         # result.pretty_print()
#
#         # cmd = "GRAPH.QUERY"
#         # command = [cmd, "MotoGP", "match(n) return n"]
#         # r.execute_command("GRAPH.QUERY 'MotoGP' 'match(n) return n'")


def exit_game(request, redis_graph):
    redis_graph.query("""match(n) delete n""")
    restart_session(request)


def restart_session(request):
    request.session["started"] = False
    request.session["board_id"] = None
    request.session["player_role"] = None


@login_required(login_url='/login/')
def resign(request):
    # TODO implement using socket
    if request.method == "GET":
        if request.session["started"] == True:
            request.session["started"] = False
            board_id = request.session["board_id"]
            request.session["board_id"] = None
            request.session["player_role"] = None
            r = redis.Redis(host='localhost', port=6379, db=board_id)
            r.flushdb()
    pass


@login_required(login_url='/login/')
def get_boards(request):
    if request.method == "GET":
        boards = Board.objects.all()
        boards_list = []
        static_images_url = "/static/images/"
        for board in boards:
            boards_list.append(dict(
                url=f"{static_images_url}{board.board_alias}.png",
                alias=board.board_alias
            ))
        return HttpResponse(json.dumps(boards_list))
    else:
        return HttpResponse(status=404)


@login_required(login_url='/login/')
def users_ratings(request):
    if request.method == "GET":
        result_dict = {}
        users = User.objects.all()
        for user in users:
            result_dict[user.username] = user.profile.rating
        return HttpResponse(json.dumps(result_dict))


@login_required(login_url='/login/')
def users_wins(request):
    if request.method == "GET":
        result_dict = {}
        users = User.objects.all()
        for user in users:
            result_dict[user.username] = user.profile.games_won_as_connect + user.profile.games_won_as_cut
        return HttpResponse(json.dumps(result_dict))


@login_required(login_url='/login/')
def users_achievements(request):
    if request.method == "GET":
        result_dict = {}
        users = User.objects.all()
        for user in users:
            result_dict[user.username] = user.profile.number_of_achievements
        return HttpResponse(json.dumps(result_dict))


@login_required(login_url='/login/')
def users_max_logins(request):
    if request.method == "GET":
        result_dict = {}
        users = User.objects.all()
        for user in users:
            result_dict[user.username] = user.profile.consecutive_logins_max
        return HttpResponse(json.dumps(result_dict))
