import tornado.web
import tornado.ioloop

from urls import urls

application = tornado.web.Application(urls)

if __name__ == "__main__":
    application.listen(80)
    tornado.ioloop.IOLoop.instance().start()


