install:
	pip install -r requirements.txt --use-mirrors
	./setup.py develop 

sandbox: install
	-rm sandbox/db.sqlite
	sandbox/manage.py syncdb --noinput
	sandbox/manage.py migrate
	sandbox/manage.py loaddata sandbox/fixtures/auth.json countries.json
	sandbox/manage.py oscar_import_catalogue sandbox/fixtures/books-catalogue.csv
