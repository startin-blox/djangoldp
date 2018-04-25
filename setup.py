from setuptools import setup

setup(
    name='djangoldp',
    version='0.2.0',
    url='https://git.happy-dev.fr/happy-dev/djangoldp/',
    author="Startin'blox",
    author_email='sylvain@happy-dev.fr',
    description='Linked Data Platform interface for Django Rest Framework',
    packages=['djangoldp'],
    zip_safe=False,
    platforms='any',
    license='MIT',
    install_requires=[
        'django>=1.11',
        'django_rest_framework',
        'pyld',
    ],
)
