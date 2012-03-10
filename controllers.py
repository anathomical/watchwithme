import tornado.web

class main(tornado.web.RequestHandler):
    def get(self):
        self.write("Main")

class user_profile(tornado.web.RequestHandler):
    def get(self):
        self.write("Profile")

