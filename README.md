# ce-be
CoachEasy repository to house backend code

## Setup instructions
- Install the heroku cli from https://devcenter.heroku.com/articles/heroku-cli
- Login to the heroku cli by running `heroku login`. Enter your own heroku credentials as the application should have been shared with you (if not, ask justin or nati for access)
- Install packages by running `make install`

## Running the application
- Run `make run`. This will pull the DATABASE_URL from heroku and start the application
