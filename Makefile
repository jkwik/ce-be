install:
	pip3 install -r requirements.txt	

run-dev:
	sed -i '' '/^DATABASE_URL/d' .env
	heroku config:get --app coach-easy-deploy DATABASE_URL -s  >> .env
	env FLASK_APP=app.py FLASK_DEBUG=1 FLASK_ENV=development flask run

run-prod:
	env FLASK_APP=app.py FLASK_ENV=production flask run
