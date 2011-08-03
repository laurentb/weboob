DROP TABLE authors;
CREATE TABLE authors (
    name TEXT PRIMARY KEY,
    sex INTEGER,
    description
);
CREATE INDEX author_idx ON authors(name, sex);

DROP TABLE stories;
CREATE TABLE stories (
    id INTEGER PRIMARY KEY,
    title TEXT,
    date TEXT,
    category TEXT,
    author TEXT REFERENCES authors,
    body TEXT
);

CREATE INDEX stories_idx ON stories(id, category);
