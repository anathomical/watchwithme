from tornado.web import RequestHandler, authenticated, HTTPError
from tornado.websocket import WebSocketHandler

from functools import wraps

from models import User, Room

from redis import conn
from models import RedisListener
from time import time
import json

sockets = []

def has_role(role):
    def role_wrapper(method):
        @authenticated
        @wraps(method)
        def wrapper(self, *args, **kwargs):
            if not self.current_user.has_role(role):
                raise HTTPError(403)
            return method(self, *args, **kwargs)
        return wrapper
    return role_wrapper

class AuthenticationHandler(RequestHandler):
    """
    We use an authentication handler that descends directly from Object so that we
    can apply it to both standard request handlers and to websocket request handlers
    using multiple inheritance.
    """
    def get_current_user(self):
        user =  User(self.get_secure_cookie('user_email'))
        token = user.auth_with_token(self.get_secure_cookie('user_token'))
        if token:
            self.set_secure_cookie('user_token', token)
            return user
        else:
            return None

    def has_role(self, role):
        return self.current_user.has_role(role)

class BaseHandler(AuthenticationHandler):
    """
    This is a convenience class that pulls in the authentication handler.
    It also ensures that the current user is always passed to the view.
    """
    def render(self, template_name, **kwargs):
        kwargs['current_user'] = kwargs.get('current_user', self.current_user)
        if self.current_user:
            kwargs['is_admin'] = kwargs.get('is_admin', self.current_user.has_role('admin'))
            kwargs['is_host'] = kwargs.get('is_host', self.current_user.has_role('host'))
            kwargs['is_guest'] = kwargs.get('is_guest', self.current_user.has_role('guest'))
        super(BaseHandler, self).render(template_name, **kwargs)

class main(BaseHandler):
    def get(self):
        self.render("views/home.html")

class admin_panel(BaseHandler):
    @has_role('admin')
    def get(self):
        self.render("views/admin.html", users=User.get_all_users())

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
            user = User(email)
            roles = {}
            roles['guest'] = self.get_argument('guest', False)
            roles['host'] = self.get_argument('host', False)
            roles['admin'] = self.get_argument('admin', False)
            for role in roles:
                # The submission process through AJAX sets the values to strings rather than booleans
                if roles[role] == 'true':
                    user.add_role(role)
                else:
                    user.remove_role(role)
            self.write('success')

class user_profile(BaseHandler):
    @authenticated
    def get(self):
        self.render("views/profile.html", user=self.current_user)

    @authenticated
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
        if User(email).create(password, token):
            self.redirect('/welcome')
        else:
            self.redirect('/join/'+token)

class logout(BaseHandler):
    def get(self):
        self.clear_cookie('user_email')
        self.clear_cookie('user_token')
        self.render('views/logout.html', current_user = None)

class login(BaseHandler):
    def get(self):
        redirect = self.get_argument('next', None)
        self.render('views/login.html', redirect=redirect)

    def post(self):
        redirect = self.get_argument('redirect', '/profile')
        email = self.get_argument('email', None)
        password = self.get_argument('password', None)
        user = User(email)
        token = user.auth_for_token(password)
        if not email or not password or not token:
            self.redirect('/login?next=' + redirect)
        self.set_secure_cookie('user_email', email)
        self.set_secure_cookie('user_token', token)
        self.redirect(redirect)

class room(BaseHandler):
    def get(self, room_id):
	room = Room(room_id)
        if not room.exists():
            self.redirect('/')
        self.render("views/room.html", video_key=room.get_video_id())

class room_socket(WebSocketHandler):
    def open(self, room_id):
        print('room_id: %s' % room_id)
        self.write_message('welcome!')
        self.room = Room(room_id)
        self.user = None

    def on_message(self, message):
        message = json.parse(message)
        if not self.user:
            user =  User(message.data.user.email)
            if user.auth_keep_token(message.data.user.token):
                self.user = user
                self.room.join(self.user)
                self.subscription = RedisListener(self.room, self)
                self.subscription.start()
            else:
                self.write_message('Authentication error.')
                self.close()
        else:
            message = self.construct_message(message)
            print(message)
            conn.rpush("room:%s:logs" % self.room.id, message)
            conn.publish("room:%s" % self.room.id, message)

    def on_close(self):
        print("socket closed")
        self.subscription.stop()
        conn.publish("room:%s" % self.room.id, self.construct_message("Goodbye."))
        self.room.leave(self.user)

    def construct_message(self, message):
        message_object = {
            'user' : self.user.email,
            'time' : time(),
            'data' : message
        }
        return json.dumps(message_object)

