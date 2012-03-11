import tornado.web
import tornado.ioloop

from urls import urls
from settings import settings

application = tornado.web.Application(urls, **settings)

if __name__ == "__main__":
    application.listen(80)
    tornado.ioloop.IOLoop.instance().start()


