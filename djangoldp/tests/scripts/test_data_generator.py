import uuid
import json
import sys
import random
from pathlib import Path
from copy import deepcopy

'''
A script which generates and outputs random test data, into a file used by the performance unit tests
'''

count = int(sys.argv[1])
fixture = list()

user_template = {
    'model': 'tests.user',
    'pk': 0,
    'fields': {
        'username': 'john',
        'email': 'jlennon@c.coop',
        'password':'glass onion'
    }
}

project_template = {
    'model': 'tests.project',
    'pk': 0,
    'fields': {
        'description': 'Test'
    }
}

def generate_user(i):
    user = deepcopy(user_template)
    user['pk'] = i
    user['fields']['username'] = str(uuid.uuid4())
    user['fields']['email'] = user['fields']['username'] + "@c.coop"
    return user

def generate_project(i):
    project = deepcopy(project_template)
    project['pk'] = i
    project['fields']['team'] = list()

    # append random number of users, max 10 for a single project
    for j in range(random.randint(1, 10)):
        project['fields']['team'].append(random.randint(1, count-1))
    return project

# create N users
for i in range(count):
    user = generate_user(i)
    fixture.append(user)

# create N projects
for i in range(count):
    project = generate_project(i)
    fixture.append(project)

with open(Path(__file__).parent / "../fixtures/test.json", 'w') as output:
    json.dump(fixture, output)

print(str(count))
