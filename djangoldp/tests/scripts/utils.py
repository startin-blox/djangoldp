from copy import deepcopy
import random


'''
Contains definitions used in common by multiple scripts within this directory
'''


def generate_user(i, user_template):
    user = deepcopy(user_template)
    user['pk'] = i
    user['fields']['username'] = str('fixture-' + str(i))
    user['fields']['email'] = user['fields']['username'] + "@c.coop"
    return user


def generate_users(count, user_template, fixture=None, offset=0):
    if fixture is None:
        fixture = list()

    for i in range(count):
        j = offset + i
        user = generate_user(j, user_template)
        fixture.append(user)

    return fixture


def generate_project(i, project_template, count, offset=0):
    project = deepcopy(project_template)
    project['pk'] = i
    project['fields']['team'] = list()

    # append random number of users, max 10 for a single project
    for j in range(random.randint(1, 10)):
        project['fields']['team'].append(random.randint(max(offset, 1), offset + (count - 1)))
    return project


def generate_projects(count, project_template, fixture=None, offset=0):
    if fixture is None:
        fixture = list()

    for i in range(count):
        j = offset + i
        project = generate_project(j, project_template, count, offset=offset)
        fixture.append(project)

    return fixture
