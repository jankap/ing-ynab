![ing_ynab logo](logo.jpg)

[![lint](https://github.com/bahlo/fints_ynab/workflows/lint/badge.svg)](https://github.com/bahlo/ing_ynab/actions?query=workflow%3Alint) [![docker](https://github.com/bahlo/ing_ynab/workflows/docker/badge.svg)](https://github.com/bahlo/ing_ynab/actions?query=workflow%3Adocker)

Import your ING Germany bank statements via FinTS into YNAB.

## Setup

Before setting this up, please 
[register your FinTS product](https://www.hbci-zka.de/register/prod_register.htm) 
– it's free and takes only a few days.  
If you don't do this, the application will fallback to the product id from the
[python-fints](https://python-fints.readthedocs.io) library, which should only
be used for evaluation.

Since this application will need your ING pin and YNAB access token it's 
recommended to run this in your local network (could be a Raspberry Pi, it's 
pretty light).

The application writes the last date and a hash of the last imported transaction
to a `state` file. If you use it in a container be sure to mount it to
prevent duplicates.

There are various ways to start the application:

### Local

This can be run on any environment with Python 3.8 or higher.

```sh
$ pip install pipenv # to install pipenv (https://pipenv.pypa.io) 
$ pipenv shell # to spawn a new shell with your env
$ pipenv install # to install dependencies
$ cp .env.example .env # and customize fields
$ python ing_ynab # to run the app
```

### Docker

```sh
$ cp .env.example .env # and customize fields
$ docker run \
    -v $PWD/ing_ynab_state:/app/state \
    --env-file .env \
    docker.pkg.github.com/bahlo/ing_ynab/ing_ynab:0.3.1
```

### docker-compose

```yml
version: "2.0"

services:
  ing_ynab:
    image: docker.pkg.github.com/bahlo/ing_ynab/ing_ynab:0.3.1
    volumes:
      - ${PWD}/ing_ynab_state:/app/state
    environment:
      # Environment variables, see the configuration section
```

## Configuration

The configuration is done via environment variables:

* `START_DATE`: The date to start getting transactions (defaults to today).
* `SLEEP_INTERVAL`: Interval in seconds until the next check happens 
  (defaults to 5 minutes).
* `FINTS_PRODUCT_ID`: Your FinTS product ID (deafults to python-fints one).
* `ING_LOGIN`: The login id of your ING account.
* `ING_IBAN`: The IBAN of the account you want to add.
* `ING_PIN`: The pin of your ING account (leave empty to be prompted).
* `YNAB_ACCESS_TOKEN`: Go to your budget settings to create one (leave empty
  to be prompted).
* `YNAB_BUDGET_ID`: On the webpage of your budget the last number in the path.
* `YNAB_ACCOUNT_ID`: On the webpage of the account the last uuid in the path.
* `YNAB_FLAG_COLOR`: If set, use that color for the imported transactions.
* `DEBUG`: Set to `1` to enable debug output and print transactions instead of
  importing them.

## Security

You can pass in your bank pin and YNAB access token via environment variables, 
if you like. This has the drawback that anyone with system access can read 
and potentially use them so it's discouraged (but supported).

The alternative is not specifying `YNAB_ACCESS_TOKEN` and/or `ING_PIN`, which
will cause the application to prompt you on startup. This has the drawback that
you need to input them everytime the application restarts.

For docker you'll need to pass the `-it` flags to be able to input these 
variables. For docker-compose, add these fields:
```yml
  tty: true
  stdin_open: true
```

After starting with `docker-compose up -d`, run `docker attach $container_id` 
to attach to the container. Note that the prompt for the pin might be hidden, 
so you have to enter the pin directly.
