import json
import logging
from datetime import datetime
from pathlib import Path
import ws

logging.basicConfig(filename='auto-grade.log',
                    level=logging.INFO)


# Exceptions #
class ClientError(Exception):
    def __init__(self, *args):
        super(ClientError, self).__init__(*args)


# Client class #
class Client(object):
    """This Client stores some data form moodle locally in order to
    save bandwith and fasten execution"""

    filename_config = "config.json"
    downloads_dir = "downloads"
    downloads_path = Path.cwd() / downloads_dir

    @staticmethod
    def save_data(obtained_data, filename):
        if not Client.downloads_path.exists():
            Client.downloads_path.mkdir()
        with open(Client.downloads_path / filename, 'w') as fd:
            json.dump(obtained_data, fd)

    def __init__(self):
        try:
            with open(Client.filename_config, 'r') as fc:
                self.config = json.load(fc)
        except FileNotFoundError:
            self.config = {}

    def save_state(self):
        with open(Client.filename_config, 'w') as fc:
            json.dump(self.config, fc)

    def __str__(self):
        str_out = ""
        if 'domain' in self.config.keys():
            str_out += 'domain: "{}"\n'.format(self.config['domain'])
        if self.is_authenticate():
            str_out += 'Authenticated\n'
        else:
            str_out += 'NOT AUTHENTICATED\n'
        if 'user' in self.config.keys():
            str_out += json.dumps(self.config['user'], indent=True) + '\n'
        if 'course_id' in self.config.keys():
            str_out += 'course_id: {}\n'.format(self.config['course_id'])
        if 'comment' in self.config.keys():
            str_out += 'default comment: "{}"\n'.format(self.config['comment'])
        return str_out

    def set_domain(self, domain):
        # If the domain is changing, we are no longer authenticated
        if 'domain' in self.config.keys() and self.config['domain'] != domain:
            del self.config['token']
        self.config['domain'] = domain

    def authenticate(self, username, password):
        # We need a domain in order to ask for authentication
        if 'domain' not in self.config.keys() or not self.config['domain']:
            raise ClientError('Moodle Domain not inserted!')
        service_name = 'moodle_mobile_app'
        web_service = ws.WS(self.config['domain'])
        web_service.authenticate(user=username, password=password, service=service_name)
        self.config['token'] = web_service.token

    def is_authenticate(self):
        return 'token' in self.config.keys() and self.config['token']

    def set_comment(self, comment):
        self.config['comment'] = comment

    def get_site_info(self):
        if not self.is_authenticate():
            raise ClientError('Not authenticated yet!')
        web_service = ws.WS(self.config['domain'], self.config['token'])
        site_info = web_service.core_webservice_get_site_info()
        Client.save_data(site_info, 'site_info.json')
        self.config['user'] = {
            'userid': site_info.get('userid', ""),
            'username': site_info.get('username', ""),
            'email': site_info.get('email', ""),
            'first': site_info.get('firstname', ""),
            'last': site_info.get('lastname', ""),
            'full': site_info.get('fullname', ""),
        }

    def get_courses(self, verbose=True):
        filename = 'users_courses.json'
        filepath = Client.downloads_path / filename
        if filepath.exists():
            with open(filepath, 'r') as fd:
                users_courses = json.load(fd)
        else:
            if not self.is_authenticate():
                raise ClientError('Not authenticated yet!')
            web_service = ws.WS(self.config['domain'], self.config['token'])
            if 'user' not in self.config.keys():
                self.get_site_info()
            params = {
                'userid': self.config['user']['userid']
            }
            users_courses = web_service.make_request('core_enrol_get_users_courses', params)
            Client.save_data(users_courses, filename)

        if verbose:
            for course in users_courses:
                print("{} : {}".format(course['id'], course['shortname']))
        return [course['id'] for course in users_courses]

    def set_course(self, course_id):
        if course_id not in self.get_courses(verbose=False):
            raise ClientError('Invalid course id!')
        self.config['course_id'] = course_id

    def get_enrolled(self, verbose=True):
        if 'course_id' not in self.config.keys():
            raise ClientError('No course pointed!')
        filename = 'enrolled_{}.json'.format(self.config['course_id'])
        filepath = Client.downloads_path / filename

        if filepath.exists():
            with open(filepath, 'r') as fd:
                enrolled_users = json.load(fd)
        else:
            if not self.is_authenticate():
                raise ClientError('Not authenticated yet!')
            web_service = ws.WS(self.config['domain'], self.config['token'])
            enrolled_users = web_service.core_enrol_get_enrolled_users(self.config['course_id'])
            Client.save_data(enrolled_users, filename)

        if verbose:
            for user in enrolled_users:
                print(user['id'],
                      ' '.join([w.capitalize() for w in user['fullname'].split(' ')]),
                      '({})'.format('.'.join([r['shortname'] for r in user['roles']])))
        return [{
            'userid': user['id'],
            'firstname': user['firstname'],
            'lastname': user['lastname'],
            'roles': '.'.join([r['shortname'] for r in user['roles']])
        } for user in enrolled_users]

    def get_assignments(self, verbose=True):
        if 'course_id' not in self.config.keys():
            raise ClientError('No course pointed!')
        filename = 'assignments_{}.json'.format(self.config['course_id'])
        filepath = Client.downloads_path / filename

        if filepath.exists():
            with open(filepath, 'r') as fd:
                assignments = json.load(fd)
        else:
            if not self.is_authenticate():
                raise ClientError('Not authenticated yet!')
            web_service = ws.WS(self.config['domain'], self.config['token'])
            # mod_assign_get_assignments requires a list of course ids, but we supply only one
            assignments = web_service.mod_assign_get_assignments([self.config['course_id']])
            assignments = assignments['courses'][0]
            Client.save_data(assignments, filename)

        if verbose:
            for asn in assignments['assignments']:
                print(asn['id'], asn['name'])
        return [{
            'id': asn['id'],
            'name': asn['name'],
            'cutoffdate': datetime.fromtimestamp(int(asn['cutoffdate']))
        } for asn in assignments['assignments']]

    def get_submissions(self, asn_id, verbose=True):
        if 'course_id' not in self.config.keys():
            raise ClientError('No course pointed!')
        if asn_id not in [asn['id'] for asn in self.get_assignments(verbose=False)]:
            raise ClientError('Invalid assignment id!')
        filename = 'submissions_{}_{}.json'.format(self.config['course_id'], asn_id)
        filepath = Client.downloads_path / filename

        if filepath.exists():
            with open(filepath, 'r') as fd:
                submissions = json.load(fd)
        else:
            if not self.is_authenticate():
                raise ClientError('Not authenticated yet!')
            web_service = ws.WS(self.config['domain'], self.config['token'])
            # mod_assign_get_submissions requires a list of assignment ids,
            # but we supply only one
            submissions = web_service.mod_assign_get_submissions([asn_id])
            submissions = submissions['assignments'][0]
            Client.save_data(submissions, filename)

        if verbose:
            for sub in submissions['submissions']:
                print(sub['userid'], sub['status'], sub['gradingstatus'])
        return [{
            'userid': sub['userid'],
            'status': sub['status'],
            'gradingstatus': sub['gradingstatus'],
        } for sub in submissions['submissions']]

    def auto_grade_missing(self, asn_id, verbose=True):
        if not self.is_authenticate():
            raise ClientError('Not authenticated yet!')
        assignments = self.get_assignments(verbose=False)
        valid_assignment_ids = [asn['id'] for asn in assignments]
        if asn_id not in valid_assignment_ids:
            raise ClientError('Invalid assignment id!')
        assignments_without_cutoff = [asn['id'] for asn in assignments
                                      if asn['cutoffdate'] == datetime.fromtimestamp(0)]
        if asn_id in assignments_without_cutoff:
            raise ClientError('Assignment without cutoffdate!')
        assignments_not_cutoff = [asn['id'] for asn in assignments
                                  if asn['cutoffdate'] > datetime.now()]
        if asn_id in assignments_not_cutoff:
            raise ClientError('Assignment submissions not cutoff-ed!')
        web_service = ws.WS(self.config['domain'], self.config['token'])

        enrolled_users = self.get_enrolled(verbose=False)
        user_roles = {user['userid']: user['roles'] for user in enrolled_users}
        user_names = {user['userid']: "{} {}".format(user['firstname'].capitalize(),
                                                     user['lastname'].capitalize())
                      for user in enrolled_users}
        submissions = {sub['userid']: {
            'status': sub['status'],
            'gradingstatus': sub['gradingstatus'],
        } for sub in self.get_submissions(asn_id, verbose=False)}

        def is_assignment_missing(userid):
            if 'student' not in user_roles[userid]:
                return False
            if userid not in submissions.keys():
                return True
            if submissions[userid]['gradingstatus'] == 'graded':
                return False
            if submissions[userid]['status'] == 'new':
                return True
            return False

        student_missing = [user['userid']
                           for user in enrolled_users
                           if is_assignment_missing(user['userid'])]
        logging.info('--auto-grading--')
        for st in student_missing:
            if verbose:
                print(st, user_names[st], '({})'.format(user_roles[st]), end=' ')
                if st in submissions.keys():
                    print(submissions[st]['status'], submissions[st]['gradingstatus'])
                else:
                    print('')

            logging.info(f'asn_id={asn_id}, usr_id={st}, user_names={user_names[st]}')
            web_service.mod_assign_save_grade(asn_id=asn_id, usr_id=st,
                                              grade=0, comment=self.config['comment'])

