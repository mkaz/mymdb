#!/Users/mkaz/.venv/bin/python3
"""
MCP Server for IMDB Database

This server provides tools to query the IMDB database for movies, directors, actors, and ratings.
"""

import sqlite3
from typing import Any, Dict, List, Optional, Tuple
from mcp.server.fastmcp import FastMCP

# Create the FastMCP server instance
mcp = FastMCP("imdb-server")

DB_PATH = "imdb.db"


def get_db_connection() -> sqlite3.Connection:
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def format_order_by(order_by: str) -> str:
    """Convert order_by parameter to SQL ORDER BY clause"""
    order_mapping = {
        "rating_desc": "tr.averageRating DESC NULLS LAST",
        "rating_asc": "tr.averageRating ASC NULLS LAST",
        "year_desc": "tb.startYear DESC NULLS LAST",
        "year_asc": "tb.startYear ASC NULLS LAST",
        "title_asc": "tb.primaryTitle ASC",
    }
    return order_mapping.get(order_by, "tr.averageRating DESC NULLS LAST")


@mcp.tool()
def query_movies_by_director(
    director_name: str, order_by: str = "rating_desc", limit: int = 20
) -> str:
    """Find movies directed by a specific director, optionally ordered by rating

    Args:
        director_name: Name of the director to search for
        order_by: How to order the results (rating_desc, rating_asc, year_desc, year_asc, title_asc)
        limit: Maximum number of results to return
    """
    conn = get_db_connection()
    try:
        query = f"""
        SELECT DISTINCT tb.primaryTitle, tb.startYear, tr.averageRating, tr.numVotes,
               nb.primaryName as director_name
        FROM title_basics tb
        JOIN title_principals tp ON tb.tconst = tp.tconst
        JOIN name_basics nb ON tp.nconst = nb.nconst
        LEFT JOIN title_ratings tr ON tb.tconst = tr.tconst
        WHERE tb.titleType = 'movie'
        AND tp.category = 'director'
        AND nb.primaryName LIKE ?
        ORDER BY {format_order_by(order_by)}
        LIMIT ?
        """

        cursor = conn.cursor()
        cursor.execute(query, (f"%{director_name}%", limit))
        results = cursor.fetchall()

        if not results:
            return f"No movies found for director '{director_name}'"

        output = [f"Movies directed by '{director_name}':\n"]
        output.append(f"{'Title':<50} {'Year':<6} {'Rating':<7} {'Votes':<10}")
        output.append("-" * 80)

        for row in results:
            title = (
                row["primaryTitle"][:47] + "..."
                if len(row["primaryTitle"]) > 50
                else row["primaryTitle"]
            )
            year = str(row["startYear"]) if row["startYear"] else "N/A"
            rating = f"{row['averageRating']:.1f}" if row["averageRating"] else "N/A"
            votes = f"{row['numVotes']:,}" if row["numVotes"] else "N/A"
            output.append(f"{title:<50} {year:<6} {rating:<7} {votes:<10}")

        return "\n".join(output)

    finally:
        conn.close()


@mcp.tool()
def query_movies_by_actor(
    actor_name: str, order_by: str = "rating_desc", limit: int = 20
) -> str:
    """Find movies featuring a specific actor or actress

    Args:
        actor_name: Name of the actor/actress to search for
        order_by: How to order the results (rating_desc, rating_asc, year_desc, year_asc, title_asc)
        limit: Maximum number of results to return
    """
    conn = get_db_connection()
    try:
        query = f"""
        SELECT DISTINCT tb.primaryTitle, tb.startYear, tr.averageRating, tr.numVotes,
               nb.primaryName as actor_name, tp.category
        FROM title_basics tb
        JOIN title_principals tp ON tb.tconst = tp.tconst
        JOIN name_basics nb ON tp.nconst = nb.nconst
        LEFT JOIN title_ratings tr ON tb.tconst = tr.tconst
        WHERE tb.titleType = 'movie'
        AND tp.category IN ('actor', 'actress')
        AND nb.primaryName LIKE ?
        ORDER BY {format_order_by(order_by)}
        LIMIT ?
        """

        cursor = conn.cursor()
        cursor.execute(query, (f"%{actor_name}%", limit))
        results = cursor.fetchall()

        if not results:
            return f"No movies found for actor '{actor_name}'"

        output = [f"Movies featuring '{actor_name}':\n"]
        output.append(f"{'Title':<50} {'Year':<6} {'Rating':<7} {'Votes':<10}")
        output.append("-" * 80)

        for row in results:
            title = (
                row["primaryTitle"][:47] + "..."
                if len(row["primaryTitle"]) > 50
                else row["primaryTitle"]
            )
            year = str(row["startYear"]) if row["startYear"] else "N/A"
            rating = f"{row['averageRating']:.1f}" if row["averageRating"] else "N/A"
            votes = f"{row['numVotes']:,}" if row["numVotes"] else "N/A"
            output.append(f"{title:<50} {year:<6} {rating:<7} {votes:<10}")

        return "\n".join(output)

    finally:
        conn.close()


@mcp.tool()
def search_movies(
    title: str,
    year: Optional[int] = None,
    min_rating: Optional[float] = None,
    genre: Optional[str] = None,
    order_by: str = "rating_desc",
    limit: int = 20,
) -> str:
    """Search for movies by title with optional filters

    Args:
        title: Movie title to search for (partial matches allowed)
        year: Release year filter
        min_rating: Minimum IMDB rating
        genre: Genre filter (e.g., 'Action', 'Drama', 'Comedy')
        order_by: How to order the results (rating_desc, rating_asc, year_desc, year_asc, title_asc)
        limit: Maximum number of results to return
    """
    conn = get_db_connection()
    try:
        conditions = ["tb.titleType = 'movie'", "tb.primaryTitle LIKE ?"]
        params = [f"%{title}%"]

        if year:
            conditions.append("tb.startYear = ?")
            params.append(year)

        if min_rating:
            conditions.append("tr.averageRating >= ?")
            params.append(min_rating)

        if genre:
            conditions.append("tb.genres LIKE ?")
            params.append(f"%{genre}%")

        where_clause = " AND ".join(conditions)

        query = f"""
        SELECT tb.primaryTitle, tb.startYear, tr.averageRating, tr.numVotes, tb.genres
        FROM title_basics tb
        LEFT JOIN title_ratings tr ON tb.tconst = tr.tconst
        WHERE {where_clause}
        ORDER BY {format_order_by(order_by)}
        LIMIT ?
        """

        params.append(limit)

        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()

        if not results:
            return f"No movies found matching the criteria"

        output = [f"Movies matching '{title}':\n"]
        output.append(
            f"{'Title':<40} {'Year':<6} {'Rating':<7} {'Votes':<10} {'Genres':<20}"
        )
        output.append("-" * 90)

        for row in results:
            title_display = (
                row["primaryTitle"][:37] + "..."
                if len(row["primaryTitle"]) > 40
                else row["primaryTitle"]
            )
            year_display = str(row["startYear"]) if row["startYear"] else "N/A"
            rating = f"{row['averageRating']:.1f}" if row["averageRating"] else "N/A"
            votes = f"{row['numVotes']:,}" if row["numVotes"] else "N/A"
            genres = (
                row["genres"][:17] + "..."
                if row["genres"] and len(row["genres"]) > 20
                else (row["genres"] or "N/A")
            )
            output.append(
                f"{title_display:<40} {year_display:<6} {rating:<7} {votes:<10} {genres:<20}"
            )

        return "\n".join(output)

    finally:
        conn.close()


@mcp.tool()
def get_movie_details(movie_title: str) -> str:
    """Get detailed information about a specific movie

    Args:
        movie_title: Exact or partial movie title
    """
    conn = get_db_connection()
    try:
        # Find the movie
        movie_query = """
        SELECT tb.tconst, tb.primaryTitle, tb.startYear, tb.runtimeMinutes, tb.genres,
               tr.averageRating, tr.numVotes
        FROM title_basics tb
        LEFT JOIN title_ratings tr ON tb.tconst = tr.tconst
        WHERE tb.titleType = 'movie'
        AND tb.primaryTitle LIKE ?
        ORDER BY tr.numVotes DESC NULLS LAST
        LIMIT 1
        """

        cursor = conn.cursor()
        cursor.execute(movie_query, (f"%{movie_title}%",))
        movie = cursor.fetchone()

        if not movie:
            return f"Movie '{movie_title}' not found"

        tconst = movie["tconst"]

        # Get director
        director_query = """
        SELECT nb.primaryName
        FROM title_principals tp
        JOIN name_basics nb ON tp.nconst = nb.nconst
        WHERE tp.tconst = ? AND tp.category = 'director'
        ORDER BY tp.ordering
        """
        cursor.execute(director_query, (tconst,))
        directors = [row["primaryName"] for row in cursor.fetchall()]

        # Get main cast
        cast_query = """
        SELECT nb.primaryName, tp.category
        FROM title_principals tp
        JOIN name_basics nb ON tp.nconst = nb.nconst
        WHERE tp.tconst = ? AND tp.category IN ('actor', 'actress')
        ORDER BY tp.ordering
        LIMIT 5
        """
        cursor.execute(cast_query, (tconst,))
        cast = cursor.fetchall()

        # Format output
        output = [f"Movie Details: {movie['primaryTitle']}\n"]
        output.append(f"Year: {movie['startYear'] or 'N/A'}")
        output.append(
            f"Runtime: {movie['runtimeMinutes']} minutes"
            if movie["runtimeMinutes"]
            else "Runtime: N/A"
        )
        output.append(f"Genres: {movie['genres'] or 'N/A'}")
        output.append(
            f"IMDB Rating: {movie['averageRating']:.1f}/10"
            if movie["averageRating"]
            else "IMDB Rating: N/A"
        )
        output.append(
            f"Number of Votes: {movie['numVotes']:,}"
            if movie["numVotes"]
            else "Number of Votes: N/A"
        )
        output.append(f"Director(s): {', '.join(directors) if directors else 'N/A'}")

        if cast:
            output.append("\nMain Cast:")
            for actor in cast:
                output.append(f"  - {actor['primaryName']} ({actor['category']})")

        return "\n".join(output)

    finally:
        conn.close()


@mcp.tool()
def top_rated_movies(
    year: Optional[int] = None,
    genre: Optional[str] = None,
    min_votes: int = 1000,
    limit: int = 20,
) -> str:
    """Get top rated movies with optional filters

    Args:
        year: Filter by release year
        genre: Filter by genre
        min_votes: Minimum number of votes required
        limit: Number of movies to return
    """
    conn = get_db_connection()
    try:
        conditions = ["tb.titleType = 'movie'", "tr.numVotes >= ?"]
        params = [min_votes]

        if year:
            conditions.append("tb.startYear = ?")
            params.append(year)

        if genre:
            conditions.append("tb.genres LIKE ?")
            params.append(f"%{genre}%")

        where_clause = " AND ".join(conditions)

        query = f"""
        SELECT tb.primaryTitle, tb.startYear, tr.averageRating, tr.numVotes, tb.genres
        FROM title_basics tb
        JOIN title_ratings tr ON tb.tconst = tr.tconst
        WHERE {where_clause}
        ORDER BY tr.averageRating DESC
        LIMIT ?
        """

        params.append(limit)

        cursor = conn.cursor()
        cursor.execute(query, params)
        results = cursor.fetchall()

        if not results:
            return "No movies found matching the criteria"

        filter_desc = []
        if year:
            filter_desc.append(f"from {year}")
        if genre:
            filter_desc.append(f"in {genre} genre")
        if min_votes > 1000:
            filter_desc.append(f"with at least {min_votes:,} votes")

        title_suffix = " " + " ".join(filter_desc) if filter_desc else ""

        output = [f"Top Rated Movies{title_suffix}:\n"]
        output.append(
            f"{'Rank':<4} {'Title':<40} {'Year':<6} {'Rating':<7} {'Votes':<10}"
        )
        output.append("-" * 70)

        for i, row in enumerate(results, 1):
            title_display = (
                row["primaryTitle"][:37] + "..."
                if len(row["primaryTitle"]) > 40
                else row["primaryTitle"]
            )
            year_display = str(row["startYear"]) if row["startYear"] else "N/A"
            rating = f"{row['averageRating']:.1f}"
            votes = f"{row['numVotes']:,}"
            output.append(
                f"{i:<4} {title_display:<40} {year_display:<6} {rating:<7} {votes:<10}"
            )

        return "\n".join(output)

    finally:
        conn.close()


@mcp.tool()
def execute_sql_query(query: str, limit: int = 100) -> str:
    """Execute a custom SQL query on the IMDB database (advanced users)

    Args:
        query: SQL query to execute (SELECT statements only)
        limit: Maximum number of results to return
    """
    # Security check - only allow SELECT statements
    query_upper = query.strip().upper()
    if not query_upper.startswith("SELECT"):
        return "Error: Only SELECT statements are allowed"

    # Check for dangerous keywords
    dangerous_keywords = [
        "DROP",
        "DELETE",
        "INSERT",
        "UPDATE",
        "ALTER",
        "CREATE",
        "TRUNCATE",
    ]
    if any(keyword in query_upper for keyword in dangerous_keywords):
        return "Error: Query contains potentially dangerous operations"

    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # Add LIMIT if not present
        if "LIMIT" not in query_upper:
            query = f"{query.rstrip(';')} LIMIT {limit}"

        cursor.execute(query)
        results = cursor.fetchall()

        if not results:
            return "No results found"

        # Get column names
        columns = [description[0] for description in cursor.description]

        # Format results
        output = [f"Query Results ({len(results)} rows):\n"]

        # Header
        header = " | ".join(f"{col:<15}" for col in columns)
        output.append(header)
        output.append("-" * len(header))

        # Data rows
        for row in results:
            row_data = []
            for value in row:
                if value is None:
                    row_data.append("NULL")
                elif isinstance(value, float):
                    row_data.append(f"{value:.2f}")
                else:
                    str_value = str(value)
                    row_data.append(
                        str_value[:15] + "..." if len(str_value) > 15 else str_value
                    )

            output.append(" | ".join(f"{val:<15}" for val in row_data))

        return "\n".join(output)

    except sqlite3.Error as e:
        return f"SQL Error: {str(e)}"
    finally:
        conn.close()


if __name__ == "__main__":
    mcp.run()
