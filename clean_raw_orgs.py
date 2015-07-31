#!/usr/bin/env python3

import config
from yio import DB

import logging
import re
import os
import webbrowser
import cgi
from bs4 import BeautifulSoup
from collections import namedtuple, defaultdict

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
        return ''

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
        return ''
    soup = BeautifulSoup(cell)
    actual_date = soup.select('div')[0].get_text()
    return actual_date.strip()

def clean_delim(cell, delim=r'\.\s*'):
    if not cell:
        return ''
    separated = "\n".join(re.split(delim, strip_tags(cell)))
    return separated.strip()

def clean_events(cell):
    if not cell:
        return ''
    events = strip_tags(cell, remove_search_link=True)
    return events

def clean_type(cell):
    if not cell:
        return ''
    org_type = strip_tags(cell).split(':')
    return org_type[0]

def clean_contact(text):
    # Each field is formatted like this:
    #
    #   Main address: 1234 Main Street
    #   More address (sometimes)
    #   Even more address (sometimes)
    #   Tel: 555-555-5555
    #   Fax: 555-555-5555
    #   Email: test@example.com
    #
    #   (Possibly more contacts, following same format as above)
    #
    #   URL: http://www.example.com
    #
    # This function puts each of those sections in a dictionary of lists and
    # then loops through each section to extract telephone, fax, e-mail, and
    # URL information. All that is left behind is considered part of the
    # address.

    if not text:
        return

    details = defaultdict(list)

    for section in text.split('\n'):
        lines = [strip_tags(line, whitelist=[])
                 for line in section.split('<br/>')]
        lines = list(filter(None, lines))

        if len(lines) == 0:
            break

        # lines[:] makes a copy of lines so that elements can be removed in place
        for line in lines[:]:
            if line.startswith('Tel:'):
                details['telephone'].append(line.replace('Tel:', '').strip())
                lines.remove(line)
            elif line.startswith('Fax:'):
                details['fax'].append(line.replace('Fax:', '').strip())
                lines.remove(line)
            elif line.startswith('Email:'):
                details['email'].append(line.replace('Email:', '')
                                        .replace(' (at) ', '@').strip())
                lines.remove(line)
            elif line.startswith('URL:'):
                details['url'].append(line.replace('URL:', '').strip())
                lines.remove(line)

        if len(lines) > 0:
            details['contact'].append("\n".join(lines))

    return details


def clean_rows():
    # All the rows to parse (organizations collected with `requests` and
    # manually) are in the view `clean_me`, created with this command:
    #
    # CREATE VIEW clean_me AS
    #   SELECT * FROM organizations_raw_requests
    #   UNION ALL
    #   SELECT fk_org, org_name, type_i_classification, contact_details, members,
    #     last_news_received, events, structure, history, activities, financing,
    #     relations_with_inter_governmental_organizations, consultative_status,
    #     aims, publications, relations_with_non_governmental_organizations,
    #     staff, subjects, type_ii_classification, languages, information_services
    #   FROM organizations_raw
    #
    # The column names for the second table have to be specified manually,
    # or else the two tables won't be stacked properly

    # Get existing column names and create named tuple row factory
    db = DB()
    colnames_raw = db.c.execute("PRAGMA table_info(clean_me);").fetchall()
    colnames = [col[1] for col in colnames_raw]
    OrgRawRow = namedtuple("OrgRawRow", colnames)
    db.add_factory(factory=OrgRawRow)

    results = db.c.execute("SELECT * FROM clean_me")

    rows = results.fetchall()

    for i, row in enumerate(rows[0:1]):
        # logger.info("Last news received: " + clean_news(row.last_news_received))
        # logger.info("Structure: " + clean_delim(row.structure))
        # logger.info("History: " + strip_tags(row.history))
        # logger.info("Financing: " + strip_tags(row.financing))
        # logger.info("Aims: " + strip_tags(row.aims))
        # logger.info("Staff: " + strip_tags(row.staff))
        # logger.info("Information services: " + strip_tags(row.information_services))
        # logger.info("Publications: " + clean_delim(row.publications))
        # logger.info("Activities: " + strip_tags(row.activities))
        # logger.info("Events: " + clean_events(row.events))
        logger.info(clean_type(row.type_i_classification))
        logger.info(clean_type(row.type_ii_classification))

        # TODO: Unpack this into multiple columns somehow
        # logger.info(clean_contact(row.contact_details))

        # Relational tables for these:
        # TODO: members
        # TODO: relations_with_inter_governmental_organizations
        # TODO: relations_With_non_governmental_organization
        # TODO: consultative_status
        # TODO: subjects
        # TODO: languages

        # TODO: Make sure all nones are actually none or NA, not just ""


if __name__ == '__main__':
    clean_rows()
