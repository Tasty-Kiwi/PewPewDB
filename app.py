import pickle
from datetime import datetime, timezone
import os
import csv
import sqlite3
import pycountry
import markupsafe
import jinja2
from flask import Flask, render_template, request, g

app = Flask(__name__)
DATABASE = "./data/databases/latest.db"

account_data = {}
with open("./ppl-data/account_data.csv", newline="", encoding="utf8") as csvfile:
    reader = csv.reader(csvfile)
    next(reader)  # Skip the header
    for row in reader:
        account_data[row[0]] = row[1]


def pull_account_name(id: str | None):
    if id is None:
        return
    try:
        return account_data[id]
    except:
        return "Unknown"


# def pull_account_name(id: str | None):
#     if id is None:
#         return

#     result = query_db("SELECT * FROM accounts WHERE account_id = ?", [id])
#     if len(result) == 0:
#         return "Unknown"

#     return result[0][1]


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


def return_date_string(num):
    return datetime.fromtimestamp(int(num), tz=timezone.utc).strftime(
        "%d/%m/%Y, %H:%M:%S UTC"
    )


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


def get_style_for_color(color, with_glow):
    """Creates a CSS style string for a given color, with an optional glow effect."""
    if with_glow:
        return f'style="color:#{color}; text-shadow:0 0 20px #{color}"'
    else:
        return f'style="color:#{color}"'


def colorize(s, with_glow=False):
    """Colorizes a string containing special color codes."""
    parts = s.split("#")
    # The first part of the string is assumed to be white
    result = f'<span {get_style_for_color("ffffffff", with_glow)}>{parts[0]}</span>'
    for i in range(1, len(parts)):
        color_str = parts[i][:6]
        # The actual text begins after the 8-character color code
        text = parts[i][8:]
        result += f"<span {get_style_for_color(color_str, with_glow)}>{text}</span>"
    return markupsafe.Markup(result)


app.jinja_env.filters["colorize"] = colorize


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
        "era2/scoreboard.html",
        entries=entries,
        date="latest",
        country_info=country_info,
    )


@app.route("/era2/<string:date>")
def era2_archive(date):
    ls = os.listdir("./data/era2_archive")
    if date + ".csv" not in ls:
        return "Invalid date", 404

    entries = []
    with open(
        f"./data/era2_archive/{date}.csv", newline="", encoding="utf8"
    ) as csvfile:
        reader = csv.DictReader(csvfile)
        for i, row in enumerate(reader):
            entries.append(
                (
                    i + 1,
                    row["account_id"],
                    row["player_name"],
                    row["score"],
                    row["country"],
                    row["wr"],
                )
            )

    return render_template(
        "era2/scoreboard.html", entries=entries, date=date, country_info=country_info
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
    if len(account_results) == 0:
        account_results = query_db(
            "SELECT * FROM accounts WHERE clean_username = ?", [request.args.get("q")]
        )
    level_results = query_db(
        "SELECT * FROM levels WHERE clean_levelname MATCH ? ORDER BY rank",
        [request.args.get("q")],
    )
    level_results += query_db(
        "SELECT * FROM levels WHERE clean_authorname MATCH ? ORDER BY rank",
        [request.args.get("q")],
    )
    if len(level_results) == 0:
        level_results = query_db(
            "SELECT * FROM levels WHERE clean_levelname = ?", [request.args.get("q")]
        )
    return render_template(
        "fragments/search_result.html",
        account_results=account_results,
        level_results=level_results,
        check_for_verified=check_for_verified,
    )


@app.route("/fragments/user_scores/<string:id>")
def fragment_user_scores(id):
    account_result = query_db("SELECT * FROM accounts WHERE account_id = ?", [id])
    if not account_result:
        return "Unknown player", 404

    raw_user_scores = query_db("SELECT * FROM all_scores WHERE account_id0 = ?", [id])
    # raw_user_scores += query_db("SELECT * FROM all_scores WHERE account_id1 = ?", [id])
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
    # raw_user_scores += query_db("SELECT * FROM all_scores WHERE account_id1 = ?", [id])
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
                "user_name_0": pull_account_name(i[1]),
                "user_name_1": pull_account_name(i[2]),
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
