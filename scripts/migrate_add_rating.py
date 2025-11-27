import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app import app
from data_models import db
from sqlalchemy import inspect, text


def main():
    with app.app_context():
        insp = inspect(db.engine)
        cols = [c['name'] for c in insp.get_columns('books')]
        if 'rating' not in cols:
            with db.engine.begin() as conn:
                conn.execute(text('ALTER TABLE books ADD COLUMN rating INTEGER'))
            print('Added rating column to books')
        else:
            print('Rating column already exists')


if __name__ == '__main__':
    main()
