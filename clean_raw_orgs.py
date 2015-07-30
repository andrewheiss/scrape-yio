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
    if not html:
        return

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

def strip_tags(html, whitelist=['a', 'i', 'b', 'em', 'strong'], remove_search_link=False):
    """Strip all HTML tags except for a list of whitelisted tags."""
    # Adapted from http://stackoverflow.com/a/16144379/120898
    if not html:
        return ""

    soup = BeautifulSoup(html)

    for tag in soup.findAll(True):
        # Remove unallowed tags
        if tag.name not in whitelist:
            tag.replaceWithChildren()

        # Remove all attributes except href
        if any(tag.attrs):
            if remove_search_link:
                tag_link = tag.attrs.get('href')
                if tag_link and 'icco/search' in tag_link:
                    tag.extract()

            tag.attrs = {key: value for key, value in tag.attrs.items()
                         if key in ['href']}

    return str(soup).strip()

def clean_news(cell):
    if not cell:
        return ""
    soup = BeautifulSoup(cell)
    actual_date = soup.select("div")[0].get_text()
    return actual_date.strip()

def clean_delim(cell, delim=r'\.\s*'):
    separated = "\n".join(re.split(delim, strip_tags(cell)))
    return separated.strip()

def clean_events(cell):
    events = strip_tags(cell, remove_search_link=True)
    return events

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

    for row in rows[28:29]:
        # logger.info("Last news received: " + clean_news(row.last_news_received))
        # logger.info("Structure: " + clean_delim(row.structure))
        # logger.info("History: " + strip_tags(row.history))
        # logger.info("Financing: " + strip_tags(row.financing))
        # logger.info("Aims: " + strip_tags(row.aims))
        # logger.info("Staff: " + strip_tags(row.staff))
        # logger.info("Information services: " + strip_tags(row.information_services))
        # logger.info("Publications: " + clean_delim(row.publications))
        # logger.info("Activities: " + strip_tags(row.activities))
        logger.info("Events: " + clean_events(row.events))


if __name__ == '__main__':
    clean_rows()
