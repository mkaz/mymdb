IMDb Dataset Details

Each dataset is contained in a gzipped, tab-separated-values (TSV) formatted file in the UTF-8 character set. The first line in each file contains headers that describe what is in each column. A '\N' is used to denote that a particular field is missing or null for that title/name. The available datasets are as follows:
title.akas.tsv.gz

    titleId (string) - a tconst, an alphanumeric unique identifier of the title
    ordering (integer) – a number to uniquely identify rows for a given titleId
    title (string) – the localized title
    region (string) - the region for this version of the title
    language (string) - the language of the title
    types (array) - Enumerated set of attributes for this alternative title. One or more of the following: "alternative", "dvd", "festival", "tv", "video", "working", "original", "imdbDisplay". New values may be added in the future without warning
    attributes (array) - Additional terms to describe this alternative title, not enumerated
    isOriginalTitle (boolean) – 0: not original title; 1: original title

title.basics.tsv.gz

    tconst (string) - alphanumeric unique identifier of the title
    titleType (string) – the type/format of the title (e.g. movie, short, tvseries, tvepisode, video, etc)
    primaryTitle (string) – the more popular title / the title used by the filmmakers on promotional materials at the point of release
    originalTitle (string) - original title, in the original language
    isAdult (boolean) - 0: non-adult title; 1: adult title
    startYear (YYYY) – represents the release year of a title. In the case of TV Series, it is the series start year
    endYear (YYYY) – TV Series end year. '\N' for all other title types
    runtimeMinutes – primary runtime of the title, in minutes
    genres (string array) – includes up to three genres associated with the title

title.crew.tsv.gz

    tconst (string) - alphanumeric unique identifier of the title
    directors (array of nconsts) - director(s) of the given title
    writers (array of nconsts) – writer(s) of the given title

title.episode.tsv.gz

    tconst (string) - alphanumeric identifier of episode
    parentTconst (string) - alphanumeric identifier of the parent TV Series
    seasonNumber (integer) – season number the episode belongs to
    episodeNumber (integer) – episode number of the tconst in the TV series

title.principals.tsv.gz

    tconst (string) - alphanumeric unique identifier of the title
    ordering (integer) – a number to uniquely identify rows for a given titleId
    nconst (string) - alphanumeric unique identifier of the name/person
    category (string) - the category of job that person was in
    job (string) - the specific job title if applicable, else '\N'
    characters (string) - the name of the character played if applicable, else '\N'

title.ratings.tsv.gz

    tconst (string) - alphanumeric unique identifier of the title
    averageRating – weighted average of all the individual user ratings
    numVotes - number of votes the title has received

name.basics.tsv.gz

    nconst (string) - alphanumeric unique identifier of the name/person
    primaryName (string)– name by which the person is most often credited
    birthYear – in YYYY format
    deathYear – in YYYY format if applicable, else '\N'
    primaryProfession (array of strings)– the top-3 professions of the person
    knownForTitles (array of tconsts) – titles the person is known for
# IMDB MCP Server

This is a Model Context Protocol (MCP) server that provides tools to query the IMDB database for movies, directors, actors, and ratings.

## Features

The MCP server provides the following tools:

1. **query_movies_by_director** - Find movies directed by a specific director, ordered by rating
2. **query_movies_by_actor** - Find movies featuring a specific actor or actress
3. **search_movies** - Search for movies by title with optional filters (year, rating, genre)
4. **get_movie_details** - Get detailed information about a specific movie
5. **top_rated_movies** - Get top rated movies with optional filters
6. **execute_sql_query** - Execute custom SQL queries (SELECT only, for advanced users)

## Setup

### Prerequisites

- Python 3.8 or higher
- The IMDB database (`imdb.db`) should be present in the same directory
- Required Python packages (install with `pip install -r requirements.txt`)

### Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Make sure your `imdb.db` database file is in the same directory as the MCP server

3. Test the server functionality:
```bash
python test_mcp_server.py
```

## Usage

### Running the MCP Server

The server is designed to be used with MCP clients. To run it directly:

```bash
python mcp_server.py
```

### Configuration for MCP Clients

Add the following configuration to your MCP client configuration file:

```json
{
  "mcpServers": {
    "imdb": {
      "command": "python",
      "args": ["mcp_server.py"],
      "cwd": "/path/to/your/mymdb/directory",
      "env": {}
    }
  }
}
```

### Example Queries

Once connected to an MCP client, you can ask questions like:

- "List movies directed by Sam Raimi and order by ratings highest to lowest"
- "Show me Tom Hanks movies from the 1990s"
- "What are the top 10 highest rated movies?"
- "Give me details about The Shawshank Redemption"
- "Find action movies from 2020 with rating above 8.0"

## Tool Descriptions

### query_movies_by_director

Find movies directed by a specific director.

**Parameters:**
- `director_name` (required): Name of the director to search for
- `order_by` (optional): How to order results - "rating_desc", "rating_asc", "year_desc", "year_asc", "title_asc"
- `limit` (optional): Maximum number of results (default: 20)

### query_movies_by_actor

Find movies featuring a specific actor or actress.

**Parameters:**
- `actor_name` (required): Name of the actor/actress to search for
- `order_by` (optional): How to order results
- `limit` (optional): Maximum number of results (default: 20)

### search_movies

Search for movies by title with optional filters.

**Parameters:**
- `title` (required): Movie title to search for (partial matches allowed)
- `year` (optional): Release year filter
- `min_rating` (optional): Minimum IMDB rating
- `genre` (optional): Genre filter (e.g., 'Action', 'Drama', 'Comedy')
- `order_by` (optional): How to order results
- `limit` (optional): Maximum number of results (default: 20)

### get_movie_details

Get detailed information about a specific movie including cast and crew.

**Parameters:**
- `movie_title` (required): Exact or partial movie title

### top_rated_movies

Get top rated movies with optional filters.

**Parameters:**
- `year` (optional): Filter by release year
- `genre` (optional): Filter by genre
- `min_votes` (optional): Minimum number of votes required (default: 1000)
- `limit` (optional): Number of movies to return (default: 20)

### execute_sql_query

Execute a custom SQL query on the IMDB database (advanced users only).

**Parameters:**
- `query` (required): SQL query to execute (SELECT statements only)
- `limit` (optional): Maximum number of results to return (default: 100)

**Note:** Only SELECT statements are allowed for security reasons.

## Database Schema

The IMDB database contains the following main tables:

- `title_basics` - Basic movie information (title, year, genre, etc.)
- `title_ratings` - Movie ratings and vote counts
- `name_basics` - Person information (actors, directors, etc.)
- `title_principals` - Relationships between movies and people (who directed/acted in what)

## Security

- The server only allows SELECT queries for the custom SQL tool
- Dangerous SQL operations (DROP, DELETE, INSERT, etc.) are blocked
- Query results are limited to prevent excessive resource usage

## Troubleshooting

1. **Database not found**: Make sure `imdb.db` is in the same directory as the MCP server
2. **Import errors**: Install required packages with `pip install -r requirements.txt`
3. **No results**: The database only contains movies (not TV shows, episodes, etc.)
4. **Performance**: Large queries may take time; use the `limit` parameter to restrict results

## Testing

Run the test script to verify functionality:

```bash
python test_mcp_server.py
```

This will test all the main functions with sample queries.