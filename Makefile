install:
	pip3 install -r requirements.txt	
run:
	sed -i '' '/^DATABASE_URL/d' .env
	heroku config:get --app coach-easy-deploy DATABASE_URL -s  >> .env
	env FLASK_APP=app.py flask run
