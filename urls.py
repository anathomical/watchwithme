import controllers

urls = [
    (r"^/$", controllers.main),
    (r"^/invite/([\w\d]+)", controllers.invite_code),
    (r"^/invite", controllers.invite_index),
    (r"^/profile", controllers.user_profile),
    (r"^/room/([\w\d]+)/socket", controllers.room_socket),
    (r"^/room/([\w\d]+)", controllers.room)
]
    
