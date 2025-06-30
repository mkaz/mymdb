#!/usr/bin/env python3
"""
IMDb Data Importer

This script imports IMDb dataset files from the data directory into a SQLite database.
The data files are gzipped TSV format and contain various IMDb datasets.
"""

import sqlite3
import gzip
import csv
import os
import sys
from typing import Optional, List, Dict, Any


class IMDbImporter:
    def __init__(self, db_path: str = "imdb.db", data_dir: str = "data"):
        self.db_path = db_path
        self.data_dir = data_dir
        self.conn = None
        # Track tconst values that were imported from title_basics (movies only)
        self.imported_tconst = set()

    def connect(self):
        """Connect to SQLite database"""
        self.conn = sqlite3.connect(self.db_path)
        # Disable foreign keys during import for better error handling
        self.conn.execute("PRAGMA foreign_keys = OFF")
        return self.conn

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def create_tables(self):
        """Create all necessary tables with proper schema"""

        # Title basics table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS title_basics (
                tconst TEXT PRIMARY KEY,
                titleType TEXT,
                primaryTitle TEXT,
                originalTitle TEXT,
                isAdult INTEGER,
                startYear INTEGER,
                endYear INTEGER,
                runtimeMinutes INTEGER,
                genres TEXT
            )
        """)

        # Title ratings table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS title_ratings (
                tconst TEXT PRIMARY KEY,
                averageRating REAL,
                numVotes INTEGER,
                FOREIGN KEY (tconst) REFERENCES title_basics(tconst)
            )
        """)

        # Name basics table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS name_basics (
                nconst TEXT PRIMARY KEY,
                primaryName TEXT,
                birthYear INTEGER,
                deathYear INTEGER,
                primaryProfession TEXT,
                knownForTitles TEXT
            )
        """)

        # Title principals table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS title_principals (
                tconst TEXT,
                ordering INTEGER,
                nconst TEXT,
                category TEXT,
                job TEXT,
                characters TEXT,
                PRIMARY KEY (tconst, ordering),
                FOREIGN KEY (tconst) REFERENCES title_basics(tconst),
                FOREIGN KEY (nconst) REFERENCES name_basics(nconst)
            )
        """)

        self.conn.commit()
        print("Tables created successfully")

    def create_indexes(self):
        """Create indexes for better query performance"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_title_basics_titleType ON title_basics(titleType)",
            "CREATE INDEX IF NOT EXISTS idx_title_basics_startYear ON title_basics(startYear)",
            "CREATE INDEX IF NOT EXISTS idx_title_basics_genres ON title_basics(genres)",
            "CREATE INDEX IF NOT EXISTS idx_title_ratings_averageRating ON title_ratings(averageRating)",
            "CREATE INDEX IF NOT EXISTS idx_title_ratings_numVotes ON title_ratings(numVotes)",
            "CREATE INDEX IF NOT EXISTS idx_name_basics_primaryName ON name_basics(primaryName)",
            "CREATE INDEX IF NOT EXISTS idx_title_principals_nconst ON title_principals(nconst)",
            "CREATE INDEX IF NOT EXISTS idx_title_principals_category ON title_principals(category)",
        ]

        for index_sql in indexes:
            self.conn.execute(index_sql)

        self.conn.commit()
        print("Indexes created successfully")

    def normalize_value(self, value: str) -> Optional[str]:
        """Convert '\\N' to None and handle empty strings"""
        if value == "\\N" or value == "" or value is None:
            return None
        return value

    def normalize_int(self, value: str) -> Optional[int]:
        """Convert string to int, handling null values"""
        normalized = self.normalize_value(value)
        if normalized is None:
            return None
        try:
            return int(normalized)
        except ValueError:
            return None

    def normalize_float(self, value: str) -> Optional[float]:
        """Convert string to float, handling null values"""
        normalized = self.normalize_value(value)
        if normalized is None:
            return None
        try:
            return float(normalized)
        except ValueError:
            return None

    def import_title_basics(self):
        """Import title.basics.tsv.gz - only movies"""
        file_path = os.path.join(self.data_dir, "title.basics.tsv.gz")
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return

        print("Importing title basics (movies only)...")
        count = 0
        movie_count = 0

        with gzip.open(file_path, "rt", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            next(reader)  # Skip header

            batch = []
            batch_size = 10000

            for row in reader:
                count += 1
                if len(row) >= 9:  # Ensure we have all columns
                    title_type = self.normalize_value(row[1])  # titleType

                    # Only import if titleType is "movie"
                    if title_type == "movie":
                        tconst = self.normalize_value(row[0])
                        record = (
                            tconst,  # tconst
                            title_type,  # titleType
                            self.normalize_value(row[2]),  # primaryTitle
                            self.normalize_value(row[3]),  # originalTitle
                            self.normalize_int(row[4]),  # isAdult
                            self.normalize_int(row[5]),  # startYear
                            self.normalize_int(row[6]),  # endYear
                            self.normalize_int(row[7]),  # runtimeMinutes
                            self.normalize_value(row[8]),  # genres
                        )
                        batch.append(record)
                        # Track this tconst as imported
                        if tconst:
                            self.imported_tconst.add(tconst)
                        movie_count += 1

                        if len(batch) >= batch_size:
                            try:
                                self.conn.executemany(
                                    """
                                    INSERT OR REPLACE INTO title_basics
                                    (tconst, titleType, primaryTitle, originalTitle, isAdult, startYear, endYear, runtimeMinutes, genres)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                    batch,
                                )
                                self.conn.commit()
                            except Exception as e:
                                print(f"  Error processing batch: {e}")
                            batch = []
                            if movie_count % 100000 == 0:
                                print(
                                    f"  Processed {movie_count:,} movie records (scanned {count:,} total records)"
                                )

            # Insert remaining records
            if batch:
                try:
                    self.conn.executemany(
                        """
                        INSERT OR REPLACE INTO title_basics
                        (tconst, titleType, primaryTitle, originalTitle, isAdult, startYear, endYear, runtimeMinutes, genres)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        batch,
                    )
                    self.conn.commit()
                except Exception as e:
                    print(f"  Error processing final batch: {e}")

        print(
            f"Imported {movie_count:,} movie records (scanned {count:,} total records)"
        )
        print(
            f"Tracking {len(self.imported_tconst):,} movie tconst values for filtering other tables"
        )

    def import_title_ratings(self):
        """Import title.ratings.tsv.gz - only for movies that were imported"""
        file_path = os.path.join(self.data_dir, "title.ratings.tsv.gz")
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return

        print("Importing title ratings (for movies only)...")
        count = 0
        imported_count = 0

        with gzip.open(file_path, "rt", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            next(reader)  # Skip header

            batch = []
            batch_size = 10000

            for row in reader:
                count += 1
                if len(row) >= 3:  # Ensure we have all columns
                    tconst = self.normalize_value(row[0])  # tconst

                    # Only import if this tconst was imported from title_basics (movies)
                    if tconst in self.imported_tconst:
                        record = (
                            tconst,  # tconst
                            self.normalize_float(row[1]),  # averageRating
                            self.normalize_int(row[2]),  # numVotes
                        )
                        batch.append(record)
                        imported_count += 1

                    if len(batch) >= batch_size:
                        try:
                            self.conn.executemany(
                                """
                                INSERT OR REPLACE INTO title_ratings
                                (tconst, averageRating, numVotes)
                                VALUES (?, ?, ?)
                            """,
                                batch,
                            )
                            self.conn.commit()
                        except sqlite3.IntegrityError as e:
                            print(
                                f"  Warning: Skipping batch due to constraint error: {e}"
                            )
                            # Try inserting records one by one to save what we can
                            saved_count = 0
                            for record in batch:
                                try:
                                    self.conn.execute(
                                        """
                                        INSERT OR REPLACE INTO title_ratings
                                        (tconst, averageRating, numVotes)
                                        VALUES (?, ?, ?)
                                    """,
                                        record,
                                    )
                                    saved_count += 1
                                except sqlite3.IntegrityError:
                                    pass  # Skip this record
                            self.conn.commit()
                            print(f"  Saved {saved_count} records from batch")
                        except Exception as e:
                            print(f"  Error processing batch: {e}")

                        batch = []
                        if count % 100000 == 0:
                            print(
                                f"  Processed {imported_count:,} movie ratings (scanned {count:,} total records)"
                            )

            # Insert remaining records
            if batch:
                try:
                    self.conn.executemany(
                        """
                        INSERT OR REPLACE INTO title_ratings
                        (tconst, averageRating, numVotes)
                        VALUES (?, ?, ?)
                    """,
                        batch,
                    )
                    self.conn.commit()
                except sqlite3.IntegrityError as e:
                    print(
                        f"  Warning: Skipping final batch due to constraint error: {e}"
                    )
                    # Try inserting records one by one to save what we can
                    saved_count = 0
                    for record in batch:
                        try:
                            self.conn.execute(
                                """
                                INSERT OR REPLACE INTO title_ratings
                                (tconst, averageRating, numVotes)
                                VALUES (?, ?, ?)
                            """,
                                record,
                            )
                            saved_count += 1
                        except sqlite3.IntegrityError:
                            pass  # Skip this record
                    self.conn.commit()
                    print(f"  Saved {saved_count} records from final batch")
                except Exception as e:
                    print(f"  Error processing final batch: {e}")

        print(
            f"Imported {imported_count:,} movie ratings (scanned {count:,} total records)"
        )

    def import_name_basics(self):
        """Import name.basics.tsv.gz"""
        file_path = os.path.join(self.data_dir, "name.basics.tsv.gz")
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return

        print("Importing name basics...")
        count = 0

        with gzip.open(file_path, "rt", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            next(reader)  # Skip header

            batch = []
            batch_size = 10000

            for row in reader:
                if len(row) >= 6:  # Ensure we have all columns
                    record = (
                        self.normalize_value(row[0]),  # nconst
                        self.normalize_value(row[1]),  # primaryName
                        self.normalize_int(row[2]),  # birthYear
                        self.normalize_int(row[3]),  # deathYear
                        self.normalize_value(row[4]),  # primaryProfession
                        self.normalize_value(row[5]),  # knownForTitles
                    )
                    batch.append(record)
                    count += 1

                    if len(batch) >= batch_size:
                        try:
                            self.conn.executemany(
                                """
                                INSERT OR REPLACE INTO name_basics
                                (nconst, primaryName, birthYear, deathYear, primaryProfession, knownForTitles)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """,
                                batch,
                            )
                            self.conn.commit()
                        except Exception as e:
                            print(f"  Error processing batch: {e}")
                        batch = []
                        if count % 100000 == 0:
                            print(f"  Processed {count:,} name basics records")

            # Insert remaining records
            if batch:
                try:
                    self.conn.executemany(
                        """
                        INSERT OR REPLACE INTO name_basics
                        (nconst, primaryName, birthYear, deathYear, primaryProfession, knownForTitles)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        batch,
                    )
                    self.conn.commit()
                except Exception as e:
                    print(f"  Error processing final batch: {e}")

        print(f"Imported {count:,} name basics records")

    def import_title_principals(self):
        """Import title.principals.tsv.gz - only for movies that were imported"""
        file_path = os.path.join(self.data_dir, "title.principals.tsv.gz")
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return

        print("Importing title principals (for movies only)...")
        count = 0
        imported_count = 0

        with gzip.open(file_path, "rt", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            next(reader)  # Skip header

            batch = []
            batch_size = 10000

            for row in reader:
                count += 1
                if len(row) >= 6:  # Ensure we have all columns
                    tconst = self.normalize_value(row[0])  # tconst

                    # Only import if this tconst was imported from title_basics (movies)
                    if tconst in self.imported_tconst:
                        record = (
                            tconst,  # tconst
                            self.normalize_int(row[1]),  # ordering
                            self.normalize_value(row[2]),  # nconst
                            self.normalize_value(row[3]),  # category
                            self.normalize_value(row[4]),  # job
                            self.normalize_value(row[5]),  # characters
                        )
                        batch.append(record)
                        imported_count += 1

                    if len(batch) >= batch_size:
                        try:
                            self.conn.executemany(
                                """
                                INSERT OR REPLACE INTO title_principals
                                (tconst, ordering, nconst, category, job, characters)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """,
                                batch,
                            )
                            self.conn.commit()
                        except sqlite3.IntegrityError as e:
                            print(
                                f"  Warning: Skipping batch due to constraint error: {e}"
                            )
                            # Try inserting records one by one to save what we can
                            saved_count = 0
                            for record in batch:
                                try:
                                    self.conn.execute(
                                        """
                                        INSERT OR REPLACE INTO title_principals
                                        (tconst, ordering, nconst, category, job, characters)
                                        VALUES (?, ?, ?, ?, ?, ?)
                                    """,
                                        record,
                                    )
                                    saved_count += 1
                                except sqlite3.IntegrityError:
                                    pass  # Skip this record
                            self.conn.commit()
                            print(f"  Saved {saved_count} records from batch")
                        except Exception as e:
                            print(f"  Error processing batch: {e}")

                        batch = []
                        if count % 100000 == 0:
                            print(
                                f"  Processed {imported_count:,} movie principals (scanned {count:,} total records)"
                            )

            # Insert remaining records
            if batch:
                try:
                    self.conn.executemany(
                        """
                        INSERT OR REPLACE INTO title_principals
                        (tconst, ordering, nconst, category, job, characters)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        batch,
                    )
                    self.conn.commit()
                except sqlite3.IntegrityError as e:
                    print(
                        f"  Warning: Skipping final batch due to constraint error: {e}"
                    )
                    # Try inserting records one by one to save what we can
                    saved_count = 0
                    for record in batch:
                        try:
                            self.conn.execute(
                                """
                                INSERT OR REPLACE INTO title_principals
                                (tconst, ordering, nconst, category, job, characters)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """,
                                record,
                            )
                            saved_count += 1
                        except sqlite3.IntegrityError:
                            pass  # Skip this record
                    self.conn.commit()
                    print(f"  Saved {saved_count} records from final batch")
                except Exception as e:
                    print(f"  Error processing final batch: {e}")

        print(
            f"Imported {imported_count:,} movie principals (scanned {count:,} total records)"
        )

    def import_all(self):
        """Import all available data files"""
        print("Starting IMDb data import...")
        print(f"Database: {self.db_path}")
        print(f"Data directory: {self.data_dir}")
        print()

        self.connect()
        self.create_tables()

        # Import in order of dependencies
        try:
            self.import_title_basics()
        except Exception as e:
            print(f"Error importing title basics: {e}")

        try:
            self.import_name_basics()
        except Exception as e:
            print(f"Error importing name basics: {e}")

        try:
            self.import_title_ratings()
        except Exception as e:
            print(f"Error importing title ratings: {e}")

        try:
            self.import_title_principals()
        except Exception as e:
            print(f"Error importing title principals: {e}")

        self.create_indexes()

        # Show summary statistics
        self.show_statistics()

        self.close()
        print("\nImport completed successfully!")

    def show_statistics(self):
        """Show database statistics"""
        print("\nDatabase Statistics:")
        print("-" * 40)

        tables = [
            ("title_basics", "Title Basics"),
            ("title_ratings", "Title Ratings"),
            ("name_basics", "Name Basics"),
            ("title_principals", "Title Principals"),
        ]

        for table_name, display_name in tables:
            cursor = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"{display_name:20}: {count:,} records")


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Import IMDb data into SQLite database"
    )
    parser.add_argument("--db", default="imdb.db", help="SQLite database file path")
    parser.add_argument(
        "--data-dir", default="data", help="Directory containing data files"
    )
    parser.add_argument(
        "--table",
        help="Import specific table only (title_basics, title_ratings, name_basics, title_principals)",
    )

    args = parser.parse_args()

    importer = IMDbImporter(args.db, args.data_dir)

    if args.table:
        importer.connect()
        importer.create_tables()

        if args.table == "title_basics":
            importer.import_title_basics()
        elif args.table == "title_ratings":
            # Need to load movie tconst values first if not already loaded
            if not importer.imported_tconst:
                print("Loading movie tconst values from database for filtering...")
                cursor = importer.conn.execute(
                    "SELECT tconst FROM title_basics WHERE titleType = 'movie'"
                )
                importer.imported_tconst = {row[0] for row in cursor.fetchall()}
                print(f"Loaded {len(importer.imported_tconst):,} movie tconst values")
            importer.import_title_ratings()
        elif args.table == "name_basics":
            importer.import_name_basics()
        elif args.table == "title_principals":
            # Need to load movie tconst values first if not already loaded
            if not importer.imported_tconst:
                print("Loading movie tconst values from database for filtering...")
                cursor = importer.conn.execute(
                    "SELECT tconst FROM title_basics WHERE titleType = 'movie'"
                )
                importer.imported_tconst = {row[0] for row in cursor.fetchall()}
                print(f"Loaded {len(importer.imported_tconst):,} movie tconst values")
            importer.import_title_principals()
        else:
            print(f"Unknown table: {args.table}")
            sys.exit(1)

        importer.create_indexes()
        importer.show_statistics()
        importer.close()
    else:
        importer.import_all()


if __name__ == "__main__":
    main()
