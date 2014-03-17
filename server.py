#!/usr/bin/python

import tornado.web
import tornado.ioloop
import config

from urls import URLS
from settings import settings

application = tornado.web.Application(URLS, **config.APPLICATION)

if __name__ == "__main__":
    application.listen(config.SERVER['port'])
    tornado.ioloop.IOLoop.instance().start()
