import controllers

urls = [
    (r"^/$", controllers.main),
    (r"^/profile", controllers.user_profile)
]
    
