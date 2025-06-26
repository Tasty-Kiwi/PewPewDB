import json
import csv
import os
import time
import requests
import sqlite3
import pickle
import re
from datetime import datetime


def strip_colors(s):
    return re.sub(r"#[0-9a-f]{8}", "", s, 0, re.MULTILINE)


def fetch_all_levels():
    r = requests.get("https://pewpew.live/custom_levels_new/get_public_levels")
    return r.json()


def fetch_and_save_era2():
    print("Fetching era2 leaderboard...")

    r = requests.get("https://pewpew.live/get_era_rankings?era=2")
    # data = json.loads(r.text().replace("var data=", ""))
    data = json.loads(r.text[9:])

    # with open("get_era_rankings2.json", "r", encoding="utf8") as f:
        # data = json.load(f)

    snapshot_datetime = datetime.strptime(
        data["date"], "%a, %d %b %Y %X %Z"
    )  # Sun, 28 Jul 2024 00:00:57 UTC

    with open(
        f"./data/era2_archive/{snapshot_datetime.strftime('%Y-%m-%d')}.csv",
        "x",
        newline="",
        encoding="utf8",
    ) as f:
        writer = csv.writer(f)
        # for (var i = 0; i < count; i+=5) {
        #   var accountIDStr = scoreData[i]
        #   var playerName = scoreData[i + 1]
        #   var score = scoreData[i + 2]
        #   var country = scoreData[i + 3]
        #   var wr = scoreData[i + 4]
        #   if (wr == 0) {
        #     wr = ""
        #   }
        # }
        writer.writerow(["account_id", "player_name", "score", "country", "wr"])
        for i in range(0, len(data["scores"]), 5):
            writer.writerow(
                [
                    data["scores"][i],
                    data["scores"][i + 1],
                    data["scores"][i + 2],
                    data["scores"][i + 3],
                    data["scores"][i + 4],
                ]
            )


def read_latest_data():
    account_data = []
    with open("./ppl-data/account_data.csv", newline="", encoding="utf8") as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Skip the header
        for row in reader:
            account_data.append((row[0], row[1], strip_colors(row[1])))

    # API is now used instead
    # level_data = []
    # with open("./data/level_data.csv", newline="", encoding="utf8") as csvfile:
    #     reader = csv.reader(csvfile)
    #     next(reader)  # Skip the header
    #     for row in reader:
    #         level_data.append((row[0], row[1], strip_colors(row[1])))

    level_data = [
        (
            level["level_uuid"],
            level["name"],
            strip_colors(level["name"]),
            level["account_id"],
            level["author"],
            strip_colors(level["author"]),
            level["date"],
            level["publish_state"],
            level["leaderboard_kind"],
            level["v"],
            level["diff"],
        )
        for level in fetch_all_levels()
    ]
    level_data += [
        ("asteroids", "#cfcfcfffAsteroids", "Asteroids", "official", "#fff468ffOfficial levels", "Official levels", None, None, None, None, None),
        ("ceasefire", "#1616ffffCeasefire", "Ceasefire", "official", "#fff468ffOfficial levels", "Official levels", None, None, None, None, None),
        ("eskiv", "#86fa5fffEskiv", "Eskiv", "official", "#fff468ffOfficial levels", "Official levels", None, None, None, None, None),
        ("fury", "#ff8330ffFury", "Fury", "official", "#fff468ffOfficial levels", "Official levels", None, None, None, None, None),
        ("hexagon", "#5bfce4ffHexagon", "Hexagon", "official", "#fff468ffOfficial levels", "Official levels", None, None, None, None, None),
        ("pandemonium", "#ff88ccffPandemonium", "Pandemonium", "official", "#fff468ffOfficial levels", "Official levels", None, None, None, None, None),
        ("partitioner", "#66ff88ffPartitioner", "Partitioner", "official", "#fff468ffOfficial levels", "Official levels", None, None, None, None, None),
        ("symbiosis", "#ff9999ffSymbiosis", "Symbiosis", "official", "#fff468ffOfficial levels", "Official levels", None, None, None, None, None),
        ("waves", "#fcf85dffWaves", "Waves", "official", "#fff468ffOfficial levels", "Official levels", None, None, None, None, None),
    ]

    score_data = []
    with open("./ppl-data/score_data.csv", newline="", encoding="utf8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            score_data.append(row)

    era2_data = []
    ls = os.listdir("./data/era2_archive")
    ls.sort(reverse=True)
    with open(f"./data/era2_archive/{ls[0]}", newline="", encoding="utf8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            era2_data.append(row)

    return {
        "account_data": account_data,
        "level_data": level_data,
        "score_data": score_data,
        "era2_data": era2_data,
    }


def cache_all_data(data):
    with open("data_cache.pickle", "wb") as f:
        pickle.dump(data, f)


def create_weekly_database(data):
    # with sqlite3.connect(f"./data/databases/{datetime.now().strftime('%Y-%m-%d')}.db") as con:
    if os.path.exists("./data/databases/latest.db"):
        print("Removing latest.db")
        os.remove("./data/databases/latest.db")
    with sqlite3.connect(f"./data/databases/latest.db") as con:
        cur = con.cursor()
        with open("schema.sql", "rt", encoding="utf8") as f:
            cur.executescript(f.read())

        cur.executemany("INSERT INTO accounts VALUES(?, ?, ?)", data["account_data"])
        # cur.executemany("INSERT INTO levels VALUES(?, ?, ?)", data["level_data"])
        cur.executemany(
            "INSERT INTO levels VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            data["level_data"],
        )
        cur.executemany(
            "INSERT INTO era_scores VALUES(NULL, ?, ?, ?, ?, ?)",
            [
                (
                    entry["account_id"],
                    entry["player_name"],
                    entry["score"],
                    entry["country"],
                    entry["wr"],
                )
                for entry in data["era2_data"]
            ],
        )
        cur.executemany(
            "INSERT INTO all_scores VALUES(NULL, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    entry["account_ids"].split("|")[0],
                    entry["account_ids"].split("|")[1] if len(entry["account_ids"].split("|")) == 2 else None,
                    entry["level_uuid"],
                    entry["level_version"],
                    entry["value"],
                    entry["value_type"],
                    entry["date"],
                    entry["country"],
                )
                for entry in data["score_data"]
            ],
        )
        con.commit()


if __name__ == "__main__":
    fetch_and_save_era2()
    time.sleep(1)
    data = read_latest_data()
    create_weekly_database(data)
