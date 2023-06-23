from copy import deepcopy
import random
from faker import Faker

'''
Contains definitions used in common by multiple scripts within this directory
'''
def generate_user(i, user_template):
    myFactory = Faker()
    user = deepcopy(user_template)
    email = myFactory.unique.email().split('@')
    email.insert(1, str(random.randint(0, 5)))
    email.insert(2, "@")
    email_str = "".join(email)
    user['pk'] = i
    user['fields']['username'] = myFactory.unique.user_name() + str(random.randint(0, 100))
    user['fields']['email'] = email_str
    user['fields']['first_name'] = myFactory.first_name()
    user['fields']['last_name'] = myFactory.last_name()
    return user


def generate_users(count, user_template, fixture=None, offset=0):
    if fixture is None:
        fixture = list()

    for i in range(count):
        j = offset + i
        user = generate_user(j, user_template)
        fixture.append(user)

    return fixture


def generate_project_member_and_user_pks(project_pk, offset, total_users, max_members_per_project):
    '''
    returns a generator of tuples (new project member PKs and selected user PKs)
    raises error if there are not enough users
    '''
    # we want to select a handful of random users
    # to save time we just select a random user within a safe range and then grab a bunch of adjacent users
    start_user_pk = random.randint(max(offset, 1), offset + (total_users - (max_members_per_project + 1)))
    if start_user_pk < offset:
        raise IndexError('not enough users!')
    
    for i in range(random.randint(1, max_members_per_project)):
        j = offset + (i + (project_pk * max_members_per_project))  # generate a unique integer id
        user_pk = start_user_pk + i  # select the next user

        yield (j, user_pk)


def generate_project_members(project_pk, fixture, offset, total_users):
    max_members_per_project = 10

    def generate_project_member(i, user_pk):
        return {
            'model': 'djangoldp_project.member',
            'pk': i,
            'fields': {
                'project': project_pk,
                'user': user_pk
            }
        }

    for (j, user_pk) in generate_project_member_and_user_pks(project_pk, offset, total_users, max_members_per_project):
        fixture.append(generate_project_member(j, user_pk))

    return fixture

def generate_skill(i, skill_template):
    myFactory = Faker()
    skill = deepcopy(skill_template)

    skill['pk'] = i
    skill['fields']['name'] = myFactory.unique.job()
    return skill


def generate_user_pks(skill_pk, offset, total_users, max_users_per_skill):
    '''
    returns a generator of tuples ()
    raises error if there are not enough users
    '''
    # we want to select a handful of random users
    # to save time we just select a random user within a safe range and then grab a bunch of adjacent users
    start_user_pk = random.randint(0, offset + (total_users - (max_users_per_skill + 1)))
    # if start_user_pk < offset:
    #     raise IndexError('not enough users!')
    
    for i in range(random.randint(1, max_users_per_skill)):
        j = offset + (i + (skill_pk * max_users_per_skill))  # generate a unique integer id
        user_pk = start_user_pk + i  # select the next user

        yield (j, user_pk)

def append_users_to_skill(skill, offset, total_users):
    max_users_per_skill = 250

    skill['fields']['users'] = []
    for (j, user_pk) in generate_user_pks(skill['pk'], offset, total_users, max_users_per_skill):
        skill['fields']['users'].append(user_pk)

    return skill

def generate_skills(count, skill_template, fixture=None, offset=0):
    if fixture is None:
        fixture = list()

    for i in range(count):
        j = offset + i
        skill = generate_skill(j, skill_template)

        skill = append_users_to_skill(skill, offset, count)
        fixture.append(skill)

    return fixture

def generate_project(i, project_template):
    project = deepcopy(project_template)
    project['pk'] = i

    return project


def append_members_to_project(project, offset, total_users):
    max_members_per_project = 10

    project['members'] = []
    for (j, user_pk) in generate_project_member_and_user_pks(project['pk'], offset, total_users, max_members_per_project):
        project['members'].append(user_pk)

    return project


def generate_projects(count, project_template, fixture=None, offset=0, production=True):
    if fixture is None:
        fixture = list()

    for i in range(count):
        j = offset + i
        project = generate_project(j, project_template)

        # project members using direct ManyToMany field. Generate them as a field on project
        if not production:
            project = append_members_to_project(project, offset, count)

        fixture.append(project)

        # project members using Member through model, generate them as separate in the fixture
        if production:
            # append random number of project members, max 10 for a single project
            generate_project_members(j, fixture, offset, count)

    return fixture
