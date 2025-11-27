from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Author(db.Model):
    __tablename__ = 'authors'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), nullable=False)
    birth_date = db.Column(db.Date, nullable=True)
    date_of_death = db.Column(db.Date, nullable=True)

    
    books = db.relationship('Book', back_populates='author', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Author id={self.id} name={self.name!r}>"

    def __str__(self):
        return f"{self.name} (born: {self.birth_date}, died: {self.date_of_death})"


class Book(db.Model):
    __tablename__ = 'books'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    isbn = db.Column(db.String(20), nullable=False, unique=True)
    title = db.Column(db.String(255), nullable=False)
    publication_year = db.Column(db.Integer, nullable=True)
    rating = db.Column(db.Integer, nullable=True)

    author_id = db.Column(db.Integer, db.ForeignKey('authors.id'), nullable=False)
    author = db.relationship('Author', back_populates='books')

    def __repr__(self):
        return f"<Book id={self.id} isbn={self.isbn!r} title={self.title!r}>"

    def __str__(self):
        return f"{self.title} by {self.author.name if self.author else 'Unknown'} ({self.publication_year})"
