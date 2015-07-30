#!/usr/bin/env python3

import config
from yio import DB

import logging
import re
import os
import webbrowser
import cgi
from bs4 import BeautifulSoup
from collections import namedtuple

# Start log
logger = logging.getLogger(__name__)

def show(html):
    template = """<!DOCTYPE html>
<html>
<meta charset="utf-8" />
<style type="text/css">
    body {{
        text-align: center;
        font-family: "Source Sans Pro";
    }}

    pre {{
        white-space: pre-wrap;
        font-size: 80%;
    }}

    #wrapper {{
        width: 80%;
        margin: 20px auto;
        text-align: left;
    }}
</style>
<body>
<div id="wrapper">

{0}

<hr>

<code><pre>{1}</pre></code>

</div>
</body>
</html>
"""
    path = os.path.abspath('temp.html')
    url = 'file://' + path

    with open(path, 'w') as f:
        f.write(template.format(html, cgi.escape(html)))
    webbrowser.open(url)

def clean_simple(cell):
    soup = BeautifulSoup(cell)
    return soup.get_text()

def clean_news(cell):
    soup = BeautifulSoup(cell)
    actual_date = soup.select("div")[0].get_text()
    return actual_date


def clean_rows():
    # All the rows to parse (organizations collected with `requests` and
    # manually) are in the view `clean_me`, created with this command:
    # CREATE VIEW clean_me AS
    #   SELECT * FROM organizations_raw_requests
    #   UNION ALL
    #   SELECT * FROM organizations_raw
    # Get existing column names and create named tuple row factory
    db = DB()
    colnames_raw = db.c.execute("PRAGMA table_info(clean_me);").fetchall()
    colnames = [col[1] for col in colnames_raw]
    OrgRawRow = namedtuple("OrgRawRow", colnames)
    db.add_factory(factory=OrgRawRow)

    results = db.c.execute("SELECT * FROM clean_me")

    rows = results.fetchall()

    for row in rows[27:28]:
        # logger.info("Last news received: " + clean_news(row.last_news_received))
        # type_i = clean_simple(row.type_i_classification)

        # type_i = re.search(r"^(\w):",
        #                    clean_simple(row.type_i_classification)).group(1)

        # print(type_i)

if __name__ == '__main__':
    clean_rows()
