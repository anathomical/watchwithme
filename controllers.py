import tornado.web
import tornado.template
import os

import redis

import models

loader = tornado.template.Loader(os.getcwd() + "/views")
sockets = []

class main(tornado.web.RequestHandler):
    def get(self):
        self.write(loader.load("home.html").generate())

class user_profile(tornado.web.RequestHandler):
    def get(self):
        self.write(loader.load("profile.html").generate())

class invite_index(tornado.web.RequestHandler):
    def get(self):
        self.write(loader.load("enter_invite.html").generate())

class invite_code(tornado.web.RequestHandler):
    def get(self, code):
        # do some stuff to validate the invite code
        self.write(loader.load("user_create.html").generate())

class room(tornado.web.RequestHandler):
    def get(self, room_id):
        self.write(loader.load("room.html").generate())

class room_socket(tornado.websocket.WebSocketHandler):
    def open(self, room_id):
        print("socket opened")
	self.write_message('welcome!')
	self.room = models.Room(room_id)
	self.user = models.User(1)
        self.room.join(self.user)
        self.subscription = models.RedisListener(self.room, self)
        self.subscription.start()

    def on_message(self, message):
        message = self.construct_message(message)
        print(message)
        redis.conn.rpush("room:%s:logs" % self.room.id, message)
        redis.conn.publish("room:%s" % self.room.id, message)

    def on_close(self):
        print("socket closed")
        self.subscription.stop()
        redis.conn.publish("room:%s" % self.room.id, self.construct_message("Goodbye."))
        self.room.leave(self.user)

    def construct_message(self, message):
        from time import time
        import json
        message_object = {
            'user' : self.user.email,
            'time' : time(),
            'data' : message
        }
        return json.dumps(message_object)

