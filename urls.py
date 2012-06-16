import controllers
import config

URLS = [
    (r"^/$", controllers.main),
    (r"^/join/?([\w\d]*)/?$", controllers.join),
    (r"^/login/?$", controllers.login),
    (r"^/logout/?$", controllers.logout),
    (r"^/profile/?$", controllers.user_profile),
    (r"^/admin/?$", controllers.admin_panel),
    (r"^/admin/update_user_roles/?$", controllers.change_roles),
    (r"^/upload/?$", controllers.upload),
    (r"^/room/([\w\d]+)/socket/?$", controllers.room_socket),
    (r"^/room/([\w\d]+)/?$", controllers.room),
]
    
