#!/usr/bin/env /usr/bin/python3

import argparse
import re
# import shtab
from client import Client

parser = argparse.ArgumentParser(description='Small client for Moodle Web Service')
# shtab.add_argument_to(parser, ["-s", "--print-completion"])  # magic!
subparser = parser.add_subparsers(title='Available commands', dest='command', metavar='command')

subparser.add_parser('config', help='show client configuration (stored locally)')
subp = subparser.add_parser('set_domain', help='insert/update a moodle domain')
subp.add_argument('domain', help='domain of moodle server')
subp = subparser.add_parser('auth', help='authenticate with username and password')
subp.add_argument('user')
subp.add_argument('password')
subp = subparser.add_parser('set_comment', help='insert default comment for auto_grade')
subp.add_argument('comment')
subparser.add_parser('site_info', help='get some data')
subparser.add_parser('get_courses', help='get courses')
subp = subparser.add_parser('set_course', help='set a course where to perform operations')
subp.add_argument('course_id', type=int)
subparser.add_parser('get_enr', help='get enrolled users (for selected course)')
subparser.add_parser('get_asn', help='get assignments (for selected course)')
subp = subparser.add_parser('get_sub', help='get submissions for an assignment')
subp.add_argument('assignment_id', type=int)
subp = subparser.add_parser('auto_grade', help='auto grade assignment where submission is missing')
subp.add_argument('assignment_id', type=int)
subp.add_argument('-r', '--remove', action='store_true')
subp.set_defaults(remove=False)

arguments = parser.parse_args()
if arguments.command == 'config':
    cl = Client()
    print(cl, end='')
    exit(0)

if arguments.command == 'set_domain':
    cl = Client()
    domain = arguments.domain
    if not re.match(r'https?://', domain):
        domain = 'https://{}'.format(domain)
    cl.set_domain(domain)
    cl.save_state()
    exit(0)

if arguments.command == 'auth':
    cl = Client()
    cl.authenticate(arguments.user, arguments.password)
    cl.save_state()
    exit(0)

if arguments.command == 'set_comment':
    cl = Client()
    cl.set_comment(arguments.comment)
    cl.save_state()
    exit(0)

if arguments.command == 'site_info':
    cl = Client()
    cl.get_site_info()
    cl.save_state()
    exit(0)

if arguments.command == 'get_courses':
    cl = Client()
    cl.get_courses()
    cl.save_state()
    exit(0)

if arguments.command == 'set_course':
    cl = Client()
    cl.set_course(arguments.course_id)
    cl.save_state()
    exit(0)

if arguments.command == 'get_enr':
    cl = Client()
    cl.get_enrolled()
    cl.save_state()
    exit(0)

if arguments.command == 'get_asn':
    cl = Client()
    cl.get_assignments()
    cl.save_state()
    exit(0)

if arguments.command == 'get_sub':
    cl = Client()
    cl.get_submissions(arguments.assignment_id)
    cl.save_state()
    exit(0)

if arguments.command == 'auto_grade':
    cl = Client()
    cl.auto_grade_missing(arguments.assignment_id, remove_grading=arguments.remove)
    cl.save_state()
    exit(0)
