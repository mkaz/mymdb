#!/usr/bin/env python3
"""
Movie Query Script for IMDb Database

Usage: python query_movie.py "Movie Title"
"""

import sqlite3
import sys
import argparse


def query_movie(db_path, movie_title):
    """
    Query movie information from IMDb database

    Args:
        db_path (str): Path to the SQLite database
        movie_title (str): Title of the movie to search for

    Returns:
        dict: Movie information including title, rating, director, and top 3 stars
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Enable column access by name

    try:
        # First, find the movie by title
        movie_query = """
        SELECT tb.tconst, tb.primaryTitle, tb.startYear, tr.averageRating, tr.numVotes
        FROM title_basics tb
        LEFT JOIN title_ratings tr ON tb.tconst = tr.tconst
        WHERE tb.titleType = 'movie'
        AND (tb.primaryTitle LIKE ? OR tb.originalTitle LIKE ?)
        ORDER BY tr.numVotes DESC, tr.averageRating DESC
        LIMIT 10
        """

        cursor = conn.cursor()
        search_term = f"%{movie_title}%"
        cursor.execute(movie_query, (search_term, search_term))
        movies = cursor.fetchall()

        if not movies:
            return None

        # If multiple matches, show them and use the first one
        if len(movies) > 1:
            print(f"Found {len(movies)} movies matching '{movie_title}':")
            for i, movie in enumerate(movies):
                year = movie["startYear"] if movie["startYear"] else "Unknown"
                rating = (
                    f"{movie['averageRating']:.1f}" if movie["averageRating"] else "N/A"
                )
                print(f"  {i + 1}. {movie['primaryTitle']} ({year}) - Rating: {rating}")
            print(f"\nUsing: {movies[0]['primaryTitle']}")
            print("-" * 50)

        # Use the first (most popular) match
        selected_movie = movies[0]
        tconst = selected_movie["tconst"]

        # Get director
        director_query = """
        SELECT nb.primaryName
        FROM title_principals tp
        JOIN name_basics nb ON tp.nconst = nb.nconst
        WHERE tp.tconst = ? AND tp.category = 'director'
        ORDER BY tp.ordering
        LIMIT 1
        """

        cursor.execute(director_query, (tconst,))
        director_result = cursor.fetchone()
        director = director_result["primaryName"] if director_result else "Unknown"

        # Get top 3 stars (actors/actresses)
        stars_query = """
        SELECT nb.primaryName, tp.category
        FROM title_principals tp
        JOIN name_basics nb ON tp.nconst = nb.nconst
        WHERE tp.tconst = ? AND tp.category IN ('actor', 'actress')
        ORDER BY tp.ordering
        LIMIT 3
        """

        cursor.execute(stars_query, (tconst,))
        stars_results = cursor.fetchall()
        stars = [star["primaryName"] for star in stars_results]

        return {
            "title": selected_movie["primaryTitle"],
            "year": selected_movie["startYear"],
            "rating": selected_movie["averageRating"],
            "num_votes": selected_movie["numVotes"],
            "director": director,
            "stars": stars,
        }

    finally:
        conn.close()


def format_movie_info(movie_info):
    """Format movie information for display"""
    if not movie_info:
        return "Movie not found."

    year = f" ({movie_info['year']})" if movie_info["year"] else ""
    rating = f"{movie_info['rating']:.1f}/10" if movie_info["rating"] else "N/A"
    votes = f" ({movie_info['num_votes']:,} votes)" if movie_info["num_votes"] else ""

    stars_list = ", ".join(movie_info["stars"]) if movie_info["stars"] else "N/A"

    return f"""
Movie Information:
==================
Title: {movie_info["title"]}{year}
Rating: {rating}{votes}
Director: {movie_info["director"]}
Top Stars: {stars_list}
"""


def main():
    parser = argparse.ArgumentParser(
        description="Query movie information from IMDb database"
    )
    parser.add_argument("title", help="Movie title to search for")
    parser.add_argument(
        "--db", default="imdb.db", help="Path to SQLite database (default: imdb.db)"
    )

    args = parser.parse_args()

    try:
        movie_info = query_movie(args.db, args.title)
        print(format_movie_info(movie_info))
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"Database file '{args.db}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
