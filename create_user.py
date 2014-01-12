import argparse

import models

parser = argparse.ArgumentParser(description='Create/modify users and roles')
parser.add_argument('email')
parser.add_argument('password')
parser.add_argument('role')

if __name__ == '__main__':
    args = parser.parse_args()

    #create admin user
    t = models.create_token()
    u = models.User(args.email)
    print u.create(args.password, t)
    print u.add_role(args.role)
    print u.has_role(args.role)
