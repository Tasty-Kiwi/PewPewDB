CREATE VIRTUAL TABLE IF NOT EXISTS accounts USING fts5 (
  account_id UNINDEXED,
  username UNINDEXED,
  clean_username,
  tokenize = 'trigram'
);

CREATE VIRTUAL TABLE IF NOT EXISTS levels USING fts5 (
  level_id UNINDEXED,
  levelname UNINDEXED,
  clean_levelname,
  author_id UNINDEXED,
  authorname UNINDEXED,
  clean_authorname,
  pub_date UNINDEXED,
  pub_state UNINDEXED,
  leaderboard_kind UNINDEXED,
  current_version UNINDEXED,
  difficulty UNINDEXED,
  tokenize = 'trigram'
);

CREATE TABLE
  IF NOT EXISTS era_scores (
    rowid INTEGER PRIMARY KEY,
    account_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    score REAL NOT NULL,
    country TEXT,
    wr INTEGER,
    FOREIGN KEY (account_id) REFERENCES accounts (account_id)
  );

CREATE TABLE
  IF NOT EXISTS all_scores (
    rowid INTEGER PRIMARY KEY,
    account_id0 TEXT NOT NULL,
    account_id1 TEXT,
    level_uuid TEXT NOT NULL,
    level_version INTEGER,
    score INTEGER NOT NULL,
    score_type INTEGER NOT NULL,
    score_date INTEGER NOT NULL,
    country TEXT NOT NULL,
    -- FOREIGN KEY (account_id0) REFERENCES accounts (account_id),
    -- FOREIGN KEY (account_id1) REFERENCES accounts (account_id),
    FOREIGN KEY (level_uuid) REFERENCES levels (level_id)
  );