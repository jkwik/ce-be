# ce-be
CoachEasy repository to house backend code
Root endpoint: https://coach-easy-deploy.herokuapp.com/

## Setup instructions
- Install the heroku cli from https://devcenter.heroku.com/articles/heroku-cli
- Login to the heroku cli by running `heroku login`. Enter your own heroku credentials as the application should have been shared with you (if not, ask justin or nati for access)
- Install packages by running `make install`

## Running the application
- Run `make run`. This will pull the DATABASE_URL from heroku and start the application

## Connecting to our database using pgAdmin 4
- Download pgAdmin 4 https://www.pgadmin.org/download/
- Open up a new pgAdmin 4 window
- Right click servers -> create server
- Under connection tab: Enter in credentials from the heroku database credentials tab. Make sure that you enter the name of our database in Maintenance database.
- Under advanced under `DB Restriction` enter the name of our database again.
- Click save
