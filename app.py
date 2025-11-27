from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import os
from data_models import db, Author, Book
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from datetime import datetime


app = Flask(__name__)


basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'data', 'library.sqlite')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path.replace('\\', '/')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')


db.init_app(app)


def _parse_date(val: str):
    if not val:
        return None
    try:
        return datetime.strptime(val, "%Y-%m-%d").date()
    except ValueError:
        return None


@app.route("/add_author", methods=["GET", "POST"])
def add_author():
    message = None
    status = None
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        birth_date = _parse_date(request.form.get("birth_date"))
        date_of_death = _parse_date(request.form.get("date_of_death"))

        if not name:
            message = "Bitte einen Namen angeben."
            status = "error"
        else:
            try:
                author = Author(name=name, birth_date=birth_date, date_of_death=date_of_death)
                db.session.add(author)
                db.session.commit()
                message = "Autor erfolgreich hinzugefügt."
                status = "success"
            except Exception:
                db.session.rollback()
                message = "Fehler beim Speichern des Autors."
                status = "error"
    authors = Author.query.order_by(Author.name.asc()).all()
    return render_template("add_author.html", message=message, status=status, authors=authors)


@app.route("/add_book", methods=["GET", "POST"])
def add_book():
    message = None
    status = None
    authors = Author.query.order_by(Author.name.asc()).all()

    if request.method == "POST":
        isbn = (request.form.get("isbn") or "").strip()
        title = (request.form.get("title") or "").strip()
        publication_year_raw = (request.form.get("publication_year") or "").strip()
        rating_raw = (request.form.get("rating") or "").strip()
        author_id_raw = request.form.get("author_id")

        try:
            publication_year = int(publication_year_raw) if publication_year_raw else None
        except ValueError:
            publication_year = None

        try:
            rating = int(rating_raw) if rating_raw else None
            if rating is not None and not (1 <= rating <= 10):
                rating = None
        except ValueError:
            rating = None

        try:
            author_id = int(author_id_raw) if author_id_raw else None
        except (TypeError, ValueError):
            author_id = None

        if not isbn or not title or not author_id:
            message = "Bitte ISBN, Titel und Autor auswählen."
            status = "error"
        else:
            author = Author.query.get(author_id)
            if not author:
                message = "Ausgewählter Autor nicht gefunden."
                status = "error"
            else:
                try:
                    book = Book(isbn=isbn, title=title, publication_year=publication_year, rating=rating, author_id=author_id)
                    db.session.add(book)
                    db.session.commit()
                    message = "Buch erfolgreich hinzugefügt."
                    status = "success"
                except IntegrityError:
                    db.session.rollback()
                    message = "ISBN existiert bereits."
                    status = "error"
                except Exception:
                    db.session.rollback()
                    message = "Fehler beim Speichern des Buches."
                    status = "error"

    return render_template("add_book.html", authors=authors, message=message, status=status)


@app.route("/")
def home():
    sort = (request.args.get("sort") or "title").lower()
    query_text = (request.args.get("q") or "").strip()

    q = Book.query.options(joinedload(Book.author))

    if query_text:
        like = f"%{query_text}%"
        
        q = (
            q.join(Author, isouter=True)
             .filter(
                 or_(
                     Book.title.ilike(like),
                     Book.isbn.ilike(like),
                     Author.name.ilike(like),
                 )
             )
        )

    if sort == "author":
        
        if not query_text:
            q = q.join(Author)
        q = q.order_by(Author.name.asc(), Book.title.asc())
    else:
        q = q.order_by(Book.title.asc())

    books = q.all()
    no_results = bool(query_text) and len(books) == 0
    return render_template("home.html", books=books, current_sort=sort, q=query_text, no_results=no_results)


@app.get('/book/<int:book_id>')
def book_detail(book_id: int):
    book = Book.query.options(joinedload(Book.author)).get(book_id)
    if not book:
        flash('Buch nicht gefunden.', 'error')
        return redirect(url_for('home'))
    return render_template('book_detail.html', book=book)


@app.get('/author/<int:author_id>')
def author_detail(author_id: int):
    author = Author.query.options(joinedload(Author.books)).get(author_id)
    if not author:
        flash('Autor nicht gefunden.', 'error')
        return redirect(url_for('home'))
    books = sorted(author.books, key=lambda b: (b.title or '').lower())
    return render_template('author_detail.html', author=author, books=books)


@app.post('/author/<int:author_id>/delete')
def delete_author(author_id: int):
    author = Author.query.get(author_id)
    if not author:
        flash('Autor nicht gefunden.', 'error')
        return redirect(url_for('home'))
    try:
        db.session.delete(author)
        db.session.commit()
        flash('Autor und zugehörige Bücher wurden gelöscht.', 'success')
    except Exception:
        db.session.rollback()
        flash('Fehler beim Löschen des Autors.', 'error')
    return redirect(url_for('home'))


@app.post('/book/<int:book_id>/rate')
def rate_book(book_id: int):
    book = Book.query.get(book_id)
    if not book:
        flash('Buch nicht gefunden.', 'error')
        return redirect(url_for('home'))
    rating_raw = (request.form.get('rating') or '').strip()
    try:
        rating = int(rating_raw)
    except ValueError:
        rating = None
    if rating is None or not (1 <= rating <= 10):
        flash('Bitte eine Bewertung von 1 bis 10 angeben.', 'error')
        return redirect(url_for('home'))
    try:
        book.rating = rating
        db.session.commit()
        flash('Bewertung gespeichert.', 'success')
    except Exception:
        db.session.rollback()
        flash('Fehler beim Speichern der Bewertung.', 'error')
    return redirect(url_for('home'))


@app.get('/recommendations')
def recommendations():
    
    books = (
        Book.query.options(joinedload(Book.author))
        .order_by(Book.rating.desc().nullslast(), Book.title.asc())
        .all()
    )
    return render_template('recommendations.html', books=books)


@app.post('/book/<int:book_id>/delete', endpoint='delete_book')
def delete_book(book_id: int):
    book = Book.query.get(book_id)
    if not book:
        flash('Buch nicht gefunden.', 'error')
        return redirect(url_for('home'))
    try:
        db.session.delete(book)
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash('Fehler beim Löschen des Buches.', 'error')
        return redirect(url_for('home'))

    flash('Buch wurde gelöscht.', 'success')
    return redirect(url_for('home'))
