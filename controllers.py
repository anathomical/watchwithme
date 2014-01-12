from tornado.web import RequestHandler, authenticated, HTTPError, decode_signed_value, create_signed_value
from tornado.websocket import WebSocketHandler

from config import APPLICATION

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
        self.render("views/room.html", video_key=room.get_video_id(),
            user_email=create_signed_value(APPLICATION['cookie_secret'], 'user_email', self.current_user.email),
            user_token=create_signed_value(APPLICATION['cookie_secret'], 'user_token', self.current_user.token))

class room_socket(WebSocketHandler):
    def open(self, room_id):
        print('room_id: %s' % room_id)
        self.room = Room(room_id)
        self.user = None
        self.subscription = None

    def on_message(self, data):
        data = json.loads(data)
        if not self.user:
            print('No user attached to this message, authenticating.')
            user =  User(decode_signed_value(APPLICATION['cookie_secret'], 'user_email', data.get('user_email')))
            print(data)
            if user.auth_keep_token(decode_signed_value(APPLICATION['cookie_secret'], 'user_token', data.get('user_token'))):
                print('Auth successful.  Setting user to %s' % user.email)
                self.user = user
                self.room.join(self.user)
                self.subscription = RedisListener(self.room, self)
                self.subscription.start()
                self.log_and_publish(construct_message('JOIN', 'Welcome!', self.user))
            else:
                print('Authentication error.')
                self.write_message(construct_message("ERROR", 'Authentication error.'))
                self.close()
        else:
            self.log_and_publish(construct_message(data.get('type'), data.get('message'), self.user))

    def on_close(self):
        print("socket closed")
        if self.subscription:
            self.subscription.stop()
            self.log_and_publish(construct_message('LEAVE', 'Goodbye.', self.user))
        self.room.leave(self.user)

    def log_and_publish(self, message):
        print(message.get('log'))
        conn.rpush("room:%s:logs" % self.room.id, message.get('log'))
        conn.publish("room:%s" % self.room.id, message.get('display'))

class simpleroom(BaseHandler):
    def get(self, room_id):
        room = Room(room_id)
        if not room.exists():
            room.create()
        self.render("views/room.html",
                    video_url='/static/testvid.mp4', #TODO set video_key to something meaningful
                    room_id=room_id,
                    user_email=create_signed_value(APPLICATION['cookie_secret'], 'user_email', self.current_user.email),
                    user_token=create_signed_value(APPLICATION['cookie_secret'], 'user_token', self.current_user.token))

def construct_message(type, message, user=None, timestamp=None):
    return construct_wire_data(type, {'message':message}, user, timestamp)

def construct_wire_data(type, data, user=None, timestamp=None):
    if not timestamp:
        timestamp = time()
    log_object = {
        'type' : type,
        'user' : getattr(user, 'email', None),
        'time' : timestamp,
        'data' : data,
    }
    display_object = {
        'type' : log_object.get('type'),
        'user' : getattr(user, 'name', None),
        'time' : log_object.get('time'),
        'data' : log_object.get('data'),
    }
    return {
        'log' : json.dumps(log_object),
        'display' : json.dumps(display_object),
    }

