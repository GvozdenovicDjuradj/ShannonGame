import json

import redis

r = redis.Redis(host='localhost', port=6379, db=0)
r.flushall()
r.set("latest_db", 0)
r.set("new_games", json.dumps(dict()))
# request.session.session_key
