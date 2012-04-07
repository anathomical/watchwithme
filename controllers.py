import tornado.web, tornado.template, tornado.escape
import os, functools

import redis

import models

sockets = []

def has_role(role):
    def role_wrapper(method):
        @tornado.web.authenticated
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            if not self.current_user.has_role(role):
                raise tornado.web.HTTPError(403)
            return method(self, *args, **kwargs)
        return wrapper
    return role_wrapper

class AuthenticationHandler(object):
    """
    We use an authentication handler that descends directly from Object so that we
    can apply it to both standard request handlers and to websocket request handlers
    using multiple inheritance.
    """
    def get_current_user(self):
        user =  models.User(self.get_secure_cookie('user_email'))
        token = user.auth_with_token(self.get_secure_cookie('user_token'))
        if token:
            self.set_secure_cookie('user_token', token)
            return user
        else:
            return None

    def has_role(self, role):
        return self.current_user.has_role(role)

class BaseHandler(AuthenticationHandler, tornado.web.RequestHandler):
    """
    This is a convenience class that pulls in the authentication handler
    """
    pass

class main(BaseHandler):
    def get(self):
        self.render("views/home.html")

class admin_panel(BaseHandler):
    @has_role('admin')
    def get(self):
        self.render("views/admin.html", users=models.User.get_all_users())

class send_invite(BaseHandler):
    @has_role('admin')
    def post(self):
        email = self.get_argument('email', None)
        # SEND AN EMAIL

class change_roles(BaseHandler):
    @has_role('admin')
    def post(self):
        email = self.get_argument('email', None)
        if email:
            user = models.User(email)
            roles = {}
            roles['guest'] = self.get_argument('guest', False)
            roles['host'] = self.get_argument('host', False)
            roles['admin'] = self.get_argument('admin', False)
            for role in roles:
                if roles[role] == 'true':
                    user.add_role(role)
                else:
                    user.remove_role(role)

class user_profile(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("views/profile.html", user=self.current_user)

    @tornado.web.authenticated
    def post(self):
        self.current_user.update(name = self.get_argument('name', self.current_user.name))
        password = self.get_argument('password', None)
        confirm = self.get_argument('confirm_password', None)
        if password and confirm and password == confirm:
            self.current_user.set_password(password)
        self.redirect('/profile')

class upload(BaseHandler):
    @has_role('host')
    def get(self):
        self.render("views/upload.html")

class join(BaseHandler):
    def get(self, token=None):
        self.render("views/join.html", token=token)

    def post(self, token=None):
        email = self.get_argument('email', None)
        token = self.get_argument('token', '')
        password = self.get_argument('password', None)
        if models.User(email).create(password, token):
            self.redirect('/welcome')
        else:
            self.redirect('/join/'+token)

class login(BaseHandler):
    def get(self):
        redirect = self.get_argument('next', None)
        self.render('views/login.html', redirect=redirect)

    def post(self):
        redirect = self.get_argument('redirect', '/profile')
        email = self.get_argument('email', None)
        password = self.get_argument('password', None)
        user = models.User(email)
        token = user.auth_for_token(password)
        if not email or not password or not token:
            self.redirect('/login?next=' + redirect)
        self.set_secure_cookie('user_email', email)
        self.set_secure_cookie('user_token', token)
        self.redirect(redirect)

class room(BaseHandler):
    def get(self, room_id):
        self.render("views/room.html")

class room_socket(AuthenticationHandler, tornado.websocket.WebSocketHandler):
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

