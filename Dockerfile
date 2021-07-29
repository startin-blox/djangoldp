# use with your own settings.yml
FROM python:3.6
LABEL maintainer="Plup <plup@plup.io>"

# get server
RUN pip install djangoldp

# create a server instance
RUN djangoldp initserver ldpserver
WORKDIR /ldpserver
#COPY settings.yml .
RUN djangoldp install
RUN djangoldp configure --with-dummy-admin

# run the server
EXPOSE 8000
CMD ["djangoldp", "runserver"]
