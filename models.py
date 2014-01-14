import redis
import tornado.websocket
import threading
import config
from hashlib import sha1, md5
from random import random

redis.conn = redis.Redis(host=config.REDIS['host'], port=config.REDIS['port'], db=config.REDIS['db'])

def generate_salt():
    return sha1(str(random())).hexdigest()

def generate_room():
    room = md5(str(random())).hexdigest()[0:12]
    while redis.conn.sismember('rooms', room):
        room = md5(str(random())).hexdigest()[0:12]
    return room

def create_token():
    token = generate_salt()
    while redis.conn.sismember('tokens', token):
        token = generate_salt()
    redis.conn.sadd('tokens', token)
    return token

def claim_token(token):
    if not token or not redis.conn.srem('tokens', token):
        return False
    return True

class Room(object):
    def __init__(self, room_id):
        self.id = room_id
        self.host = None

    def get_users_hash(self):
        return "room:%s:users" % self.id

    def get_rooms_hash(self):
        return "rooms"

    def get_room_timecodes_hash(self):
        return 'rooms:timecodes'

    @property
    def timecode(self):
        return redis.conn.zscore(self.get_room_timecodes_hash(), self.id)

    @timecode.setter
    def timecode(self, value):
        redis.conn.zadd(self.get_room_timecodes_hash(), self.id, value)

    @property
    def host(self):
        return redis.conn.get('room:%s:host' % self.id)

    @host.setter
    def host(self, val):
        redis.conn.set('room:%s:host' % self.id, val)

    def get_video_id(self):
        return redis.conn.get('room:%s:video_id' % self.id)

    def exists(self):
        if redis.conn.zscore(self.get_rooms_hash(), self.id):
            return True
        else:
            return False

    def get_size(self):
        return redis.conn.zscore(self.get_rooms_hash(), self.id)

    def create(self):
        redis.conn.zadd(self.get_rooms_hash(), 0, self.id)
        return self

    def destroy(self):
        redis.conn.zrem(self.get_rooms_hash(), self.id)
        return self

    def join(self, user):
        if redis.conn.sadd(self.get_users_hash(), user.email):
            redis.conn.zincrby(self.get_rooms_hash(), self.id, 1)
            print user.email, self.host, type(self.host)
            if self.host == 'None':
                print '%s is now host of room %s' % (user.email, self.id)
                self.host = user.email
            return True
        else:
            print 'join failed'
            return False

    def leave(self, user):
        if redis.conn.srem(self.get_users_hash(), user.email):
            redis.conn.zincrby(self.get_rooms_hash(), self.id, -1)
            #unset host if necessary
            if self.host == user.email:
                self.host = None
            #murder user
            user.destroy()
            return True
        else:
            return False


class RedisListener(threading.Thread):
    def __init__(self, room, socket):
        self.room = room
        self.socket = socket
        self.time_to_die = threading.Event()
        super(RedisListener, self).__init__()

    def run(self):
        self.subscription = redis.conn.pubsub()
        self.subscription.subscribe("room:%s" % self.room.id)
        for message in self.subscription.listen():
            if self.time_to_die.isSet():
                break
            try:
                self.socket.write_message(message['data'])
            except:
                print message, 'was badly formatted'


    def stop(self):
        self.time_to_die.set()

class User(object):
    def __init__(self, email):
        self.email = email

    @staticmethod
    def get_all_users():
         users = redis.conn.smembers('users')
         user_set = set()
         for user in users:
             user_set.add(User(user))
         return user_set

    @property
    def name(self):
        if not hasattr(self, '_name'):
            self._name = redis.conn.get(self.get_hash('name'))
        return self._name

    @property
    def token(self):
        return self.get_from_redis('token')

    def create(self, password, token=None):
        if token == None:
            token = create_token()
            self.set_in_redis("token", token)
        if not self.email or not password or not claim_token(token) or self.exists():
            return False
        self.set_in_redis("name", self.email)
        self.set_password(password)
        self.add_role("guest")
        redis.conn.sadd('users', self.email)
        return self

    def destroy(self):
        redis.conn.delete(self.get_hash('name'))
        redis.conn.delete(self.get_hash('password'))
        redis.conn.delete(self.get_hash('salt'))
        redis.conn.delete(self.get_hash('token'))
        redis.conn.delete(self.get_hash('roles'))
        redis.conn.srem('users', self.email)

    def exists(self):
        return redis.conn.sismember('users', self.email)

    def get_hash(self, value):
        return "user:%s:%s" % (self.email, value)

    def get_from_redis(self, value):
        if value == "roles":
            return redis.conn.smembers(self.get_hash(value))
        else:
            return redis.conn.get(self.get_hash(value))

    def set_in_redis(self, value, set_to):
        if value == "roles":
            redis.conn.delete(self.get_hash(value))
            for role in set_to:
                redis.conn.sadd(self.get_hash(value), role)
        else:
            redis.conn.set(self.get_hash(value), set_to)
        return self

    def update(self, **kwargs):
        for key in kwargs:
            if kwargs[key]:
                self.set_in_redis(key, kwargs[key])

    def salt_password(self, salt, password):
        hash_me = salt + password
        for i in range(100):
            hash_me = sha1(hash_me).hexdigest()
        return hash_me

    def authenticate(self, password):
        if self.exists() and self.salt_password(self.get_from_redis("salt"), password) == self.get_from_redis("password"):
            return True
        else:
            return False

    def auth_with_token(self, token):
        if token == self.get_from_redis("token"):
            token = generate_salt()
            self.set_in_redis("token", token)
            return token
        else:
            return False

    def auth_keep_token(self, token):
        print('%s == %s' % (token, self.get_from_redis('token')))
        if token == self.get_from_redis("token"):
            return token
        else:
            return False

    def auth_for_token(self, password):
        if self.authenticate(password):
            token = generate_salt()
            self.set_in_redis("token", token)
            return token
        else:
            return False

    def set_password(self, password):
        salt = generate_salt()
        self.set_in_redis("salt", salt)
        self.set_in_redis("password", self.salt_password(salt, password))
        return self

    def add_role(self, role):
        redis.conn.sadd(self.get_hash("roles"), role)
        return self

    def remove_role(self, role):
        redis.conn.srem(self.get_hash("roles"), role)
        return self

    def has_role(self, role):
        return redis.conn.sismember(self.get_hash("roles"), role)

