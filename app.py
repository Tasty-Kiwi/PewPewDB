import pickle
from datetime import datetime, timezone
import os
import csv
import sqlite3
import pycountry
import markupsafe
from flask import Flask, render_template, request, g

app = Flask(__name__)
DATABASE = "./data/databases/latest.db"

with open("data_cache.pickle", "rb") as f:
    raw_data = pickle.load(f)

account_data = raw_data["account_data"]
level_data = raw_data["level_data"]
score_data = raw_data["score_data"]
era2_data = raw_data["era2_data"]


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def country_info(code):
    return pycountry.countries.get(alpha_2=code)


def pull_level_name(id: str):
    try:
        return level_data[id]
    except:
        return account_data[id]


def pull_account_name(id: str):
    try:
        return account_data[id]
    except:
        return "Unknown"


def return_date_string(num):
    return datetime.fromtimestamp(int(num), tz=timezone.utc).strftime("%d/%m/%Y, %H:%M:%S UTC")


def check_for_verified(id):
    if id in (
        "KnogIETlchLFxgxtLD72o",
        "qEY3iKDcv8JQvNKhNdCXb",
        "k6Ma3dB0uP4sdDcc0nzr6",
        "VrwQA_5k0mSQHWMdRuwJL",
        "fpBpcnHYX0NDuPUr8Yz4h",
    ):
        return True
    else:
        return False


# TODO: port colorize to server-side
def colorize(name):
    pass


@app.route("/fragments/era2/top_20")
def fragment_top_20():
    entries = query_db("SELECT * FROM era_scores LIMIT 20")
    return render_template(
        "fragments/era_2_scoreboard.html", entries=entries, country_info=country_info
    )


@app.route("/fragments/era2/latest")
def fragment_era2_latest():
    entries = query_db("SELECT * FROM era_scores")
    return render_template(
        "fragments/era_2_scoreboard.html", entries=entries, country_info=country_info
    )


@app.route("/era2/latest")
def era2_latest():
    entries = query_db("SELECT * FROM era_scores")
    return render_template(
        "era2/latest.html", entries=entries, country_info=country_info
    )


@app.route("/era2/list")
def era2_list():
    ls = os.listdir("./data/era2_archive")
    ls.sort(reverse=True)
    ls = [i.replace(".csv", "") for i in ls]
    return render_template("era2/list.html", files=ls)


@app.route("/search")
def fragment_search():
    if request.args.get("q") == "":
        return ""

    account_results = query_db(
        "SELECT * FROM accounts WHERE clean_username MATCH ? ORDER BY rank",
        [request.args.get("q")],
    )
    if not account_results:
        account_results = query_db(
            "SELECT * FROM accounts WHERE clean_username = ?", [request.args.get("q")]
        )
    # print(account_results)
    level_results = query_db(
        "SELECT * FROM levels WHERE clean_levelname MATCH ? ORDER BY rank",
        [request.args.get("q")],
    )
    level_results += query_db(
        "SELECT * FROM levels WHERE clean_authorname MATCH ? ORDER BY rank",
        [request.args.get("q")],
    )
    if not level_results:
        level_results = query_db(
            "SELECT * FROM levels WHERE clean_levelname = ?", [request.args.get("q")]
        )
    # print(level_results)
    return render_template(
        "fragments/search_result.html",
        account_results=account_results,
        level_results=level_results,
        check_for_verified=check_for_verified
    )

@app.route("/fragments/user_scores/<string:id>")
def fragment_user_scores(id):
    account_result = query_db("SELECT * FROM accounts WHERE account_id = ?", [id])
    if not account_result:
        return "Unknown player", 404

    raw_user_scores = query_db("SELECT * FROM all_scores WHERE account_id0 = ?", [id])
    user_scores = [
        {
            "level_id": i[3],
            "level_name": query_db("SELECT * FROM levels WHERE level_id = ?", [i[3]])[
                0
            ][1],
            "level_version": i[4],
            "score": (
                i[5]
                if i[6] == 0
                else datetime.fromtimestamp(-1 * i[5] // 30).strftime("%H:%M:%S")
            ),
            "score_type": i[6],
            "date": datetime.fromtimestamp(i[7]).strftime("%d/%m/%Y, %H:%M:%S"),
            "country": i[8],
        }
        for i in raw_user_scores
    ]
    return render_template(
        "fragments/user_scores.html", entries=user_scores, country_info=country_info
    )


@app.route("/user/<string:id>")
def user(id):
    account_result = query_db("SELECT * FROM accounts WHERE account_id = ?", [id])
    if not account_result:
        return "Unknown player", 404
    era2_result = query_db("SELECT * FROM era_scores WHERE account_id = ?", [id])
    raw_user_scores = query_db("SELECT * FROM all_scores WHERE account_id0 = ?", [id])
    raw_user_scores.sort(reverse=True, key=lambda e: e[5])
    print("processing scores:", len(raw_user_scores))
    user_scores = [
        {
            "level_id": i[3],
            "level_name": query_db("SELECT * FROM levels WHERE level_id = ?", [i[3]])[
                0
            ][1],
            "level_version": i[4],
            "score": (
                i[5]
                if i[6] == 0
                else datetime.fromtimestamp(-1 * i[5] // 30, tz=timezone.utc).strftime(
                    "%H:%M:%S"
                )
            ),
            "score_type": i[6],
            "date": datetime.fromtimestamp(i[7], tz=timezone.utc).strftime(
                "%d/%m/%Y, %H:%M:%S UTC"
            ),
            "country": i[8],
        }
        for i in raw_user_scores
    ]
    return render_template(
        "user.html",
        account_result=account_result[0],
        era2_result=era2_result[0],
        entries=user_scores,
        country_info=country_info,
    )


@app.route("/level/<string:id>")
def level(id):
    level_result = query_db("SELECT * FROM levels WHERE level_id = ?", [id])
    if not level_result:
        return "Unknown level", 404
    if level_result[0][7] == 4 or level_result[0][3] == "official":
        raw_user_scores = query_db(
            "SELECT * FROM all_scores WHERE level_uuid = ?", [id]
        )
        # print(raw_user_scores)
        raw_user_scores.sort(reverse=True, key=lambda e: e[5])
        print("processing scores:", len(raw_user_scores))
        user_scores = [
            {
                "user_id_0": i[1],
                "user_id_1": i[2],
                "user_name_0": "Placeholder",
                # "user_name_0": (
                # query_db("SELECT * FROM accounts WHERE account_id = ?", [i[1]])[0][1] # 58hJldHEmy96_omP4ArEi
                # if "," not in i[1]
                # else "Multiplayer game"
                # ),
                # "user_name_1": (
                # query_db("SELECT * FROM accounts WHERE account_id = ?", [i[2]])[0][1]
                # if i[2] is not None
                # else None
                # ),
                "level_version": i[4],
                "score": (
                    i[5]
                    if i[6] == 0
                    else datetime.fromtimestamp(
                        -1 * i[5] // 30, tz=timezone.utc
                    ).strftime("%H:%M:%S")
                ),
                "score_type": i[6],
                "date": datetime.fromtimestamp(i[7], tz=timezone.utc).strftime(
                    "%d/%m/%Y, %H:%M:%S UTC"
                ),
                "country": i[8],
            }
            for i in raw_user_scores
        ]
    else:
        user_scores = None

    return render_template(
        "level.html",
        level_result=level_result[0],
        entries=user_scores,
        country_info=country_info,
        return_date_string=return_date_string,
    )


@app.route("/")
def index():
    return render_template("index.html")


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()
