# use with your own settings.yml
FROM python:3.6
LABEL maintainer="Plup <plup@plup.io>"

# get server
RUN pip install git+https://git.startinblox.com/djangoldp-packages/djangoldp.git

# create a server instance
RUN djangoldp initserver ldpserver
WORKDIR /ldpserver
COPY settings.yml .
RUN djangoldp install
RUN djangoldp configure

# create a default admin
RUN echo "from django.contrib.auth import get_user_model; CustomUser = get_user_model(); CustomUser.objects.create_superuser('admin', 'admin@startinblox.com', 'admin')" | python manage.py shell

# run the server
EXPOSE 8000
CMD ["djangoldp", "runserver"]
