# How to use the client in beta

`/!\` The client only works for development projects.

Install the appropriate version of the client:
```
$ python -m pip install 'git+https://git.startinblox.com/djangoldp-packages/djangoldp.git@v0.7.dev1'
```

Setup a new project:
```
$ djangoldp startproject myproject
$ cd myproject
```

Configure the `config.yml` with the dependencies and the LDP packages your server need to serve.

Install the server:
```
$ djangoldp install
$ djangoldp configure
```

Run it:
```
$ djangoldp runserver
```
