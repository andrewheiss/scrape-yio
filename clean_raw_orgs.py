#!/usr/bin/env python3

import config
from yio import DB

import logging
import re
import os
import webbrowser
import cgi
from pprint import pprint
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
        return

    # Remove newlines first because they conflict with check for malformed HTML
    soup = BeautifulSoup(html.replace('\n', ''))

    if len(soup) == 0:
        # There's probably malformed HTML, like </p></p></p></div> in the lists
        logger.info("Trying to fix malformed HTML")
        html = html.replace('</p>', '').replace('</div>', '')
        soup = BeautifulSoup(html)

    for tag in soup.find_all(True):
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

    return str(soup).strip().replace('\xa0', ' ')

def clean_news(cell):
    if not cell:
        return
    soup = BeautifulSoup(cell)
    actual_date = soup.select('div')[0].get_text()
    return actual_date.strip()

def clean_delim(cell, delim=r'\.\s*'):
    if not cell:
        return
    separated = "\n".join(re.split(delim, strip_tags(cell)))
    return separated.strip()

def clean_events(cell):
    if not cell:
        return
    events = strip_tags(cell, remove_search_link=True)

    if events == '':
        return
    else:
        return events

def clean_type(cell):
    if not cell:
        return
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

    Contact = namedtuple('Contact', ['contact', 'telephone', 'fax', 'email'])
    Details = namedtuple('Details', ['contacts', 'url'])

    contacts = []
    urls = []

    for section in text.split('\n'):
        lines = [strip_tags(line, whitelist=[])
                 for line in section.split('<br/>')]
        lines = list(filter(None, lines))

        if len(lines) == 0:
            break

        # Initialize variables
        telephone = fax = email = url = None

        # lines[:] makes a copy of lines so that elements can be removed in place
        for line in lines[:]:
            if line.startswith('Tel:'):
                telephone = line.replace('Tel:', '').strip()
                lines.remove(line)
            elif line.startswith('Fax:'):
                fax = line.replace('Fax:', '').strip()
                lines.remove(line)
            elif line.startswith('Email:'):
                email = line.replace('Email:', '').replace(' (at) ', '@').strip()
                lines.remove(line)
            elif line.startswith('URL:'):
                url = line.replace('URL:', '').strip()
                lines.remove(line)
            # Sometimes there's a standalone URL without the 'URL:' prefix
            elif line.startswith('http'):
                urls.append(line.strip())
                lines.remove(line)

        if url and len(lines) == 0:
            urls.append(url)
        elif len(lines) > 0:
            contact = Contact('\n'.join(lines), telephone, fax, email)
            contacts.append(contact)

    if len(urls) > 0:
        # Just use a comma separated string, since it's rare and I can split it
        # in R later
        url = ', '.join([url.replace('.proxy.lib.duke.edu', '') for url in urls])
    else:
        url = None

    return Details(contacts, url)

def clean_list(text):
    # Each field is formatted like this:
    #
    #   Type of membership (3):
    #   • <a>Thing 1</a>.
    #   • <a>Thing 2</a>.
    #   • <a>Thing 3</a>.
    #
    #   Other type of membership (2):
    #   • <a>Other thing 1</a>;
    #   • <a>Other thing 2</a>.
    #
    #   Members in 2 countries on 2 continents.
    #

    if not text:
        return

    # Divide into sentences.
    # Sentences that end in : indicate a list header
    # Lists can be nested (like continents)
    # Continent lists are comma separated
    # Non-continent lists can be ; or , delimited, meaning the whole list is really a sentence
    # Essentially every list is a complete sentence; some are just nested
    list_parts = []
    insert_subheading = False

    Line = namedtuple('Line', ['contents', 'line_type'])
    CountrySummary = namedtuple('CountrySummary', ['countries', 'continents'])

    subheading = re.compile(r'• .*: ')
    heading = re.compile(r'(.+?:)')

    for sen in [strip_tags(sen) for sen in text.split('.')]:
        # Check for subheadings first, since they look like headings but don't
        # save them to list_parts until after saving any headings
        check_subheading = subheading.search(sen)
        if check_subheading:
            insert_subheading = True
            clean_subheading = (re.sub(':|•', '', check_subheading.group(0))
                                .strip())
            subheading_temp = Line(clean_subheading, 'subheading')
            sen = subheading.sub('', sen)

        # Extract headings
        check_heading = heading.match(sen)
        if check_heading:
            clean_heading = (re.sub(r'\(\d+\)', '', check_heading.group(0))
                             .replace(':', '').strip())
            list_parts.append(Line(clean_heading, 'heading'))

            sen = heading.sub('', sen)  # Remove heading from sentence

        # Insert subheading if there is one
        if insert_subheading:
            list_parts.append(subheading_temp)

            list_elements = sen.split(',')
            for part in list_elements:
                list_parts.append(extract_links(part))
                # TODO: What if there is no link?
            insert_subheading = False
        else:
            if sen.startswith('Members in'):
                numbers = re.findall(r'\d+', sen)
                countries = numbers[0]
                continents = numbers[1] if len(numbers) > 1 else 0
                list_parts.append(CountrySummary(countries, continents))
            else:
                list_parts.append(Line(sen, 'line'))
            # TODO: Make sure this really works for all situations

    pprint(list_parts)

def parse_list_line(text):
    pass

def extract_links(html):
    Link = namedtuple('Link', ['text', 'url'])
    links = []

    soup = BeautifulSoup(html)
    for link in soup.find_all('a'):
        links.append(Link(link.get_text(), link.get('href')))

    return links

def clean_subject(cell):
    # <ul>
    #     <li>Level 1a</li>
    #     <ul>
    #         <li>Level 2a</li>
    #     </ul>
    #     <li>Level 1b</li>
    #     <ul>
    #         <li>Level 2b</li>
    #         <li>Level 2c</li>
    #         <li>Level 2d</li>
    #     </ul>
    # </ul>
    if not cell:
        return
    soup = BeautifulSoup(cell)
    ul = soup.select('ul')

    Subject = namedtuple('Subject', ['level_2', 'level_1'])
    subjects = []

    level_1 = ''
    for li in ul[0].find_all(['li']):
        if li.parent.parent.name == 'ul':
            subjects.append(Subject(li.get_text(), level_1))
        else:
            level_1 = li.get_text()

    return subjects


def clean_rows():
    # All the rows to parse (organizations collected with `requests` and
    # manually) are in the view `clean_me`, created with this command:
    #
    # CREATE VIEW clean_me_full AS
    #   SELECT * FROM (
    #     SELECT * FROM organizations_raw_requests
    #     UNION ALL
    #     SELECT fk_org, org_name, type_i_classification, contact_details, members,
    #       last_news_received, events, structure, history, activities, financing,
    #       relations_with_inter_governmental_organizations, consultative_status,
    #       aims, publications, relations_with_non_governmental_organizations,
    #       staff, subjects, type_ii_classification, languages, information_services
    #     FROM organizations_raw) temp_table
    #   INNER JOIN organizations ON temp_table.fk_org = organizations.id_org
    #
    # The column names for the second table have to be specified manually,
    # or else the two tables won't be stacked properly

    # Get existing column names and create named tuple row factory
    db = DB()
    colnames_raw = db.c.execute("PRAGMA table_info(clean_me_full);").fetchall()
    colnames = [col[1] for col in colnames_raw]
    OrgRawRow = namedtuple("OrgRawRow", colnames)
    db.add_factory(factory=OrgRawRow)

    results = db.c.execute("SELECT * FROM clean_me_full")

    rows = results.fetchall()

    CleanOrg = namedtuple("CleanOrg", ['id_org', 'org_name', 'acronym',
                                       'org_url', 'founded', 'city_hq', 'country_hq',
                                       'type_i_dir', 'type_ii_dir',
                                       'type_iii_dir', 'type_i', 'type_ii',
                                       'uia_id', 'url_id', 'subject_dir',
                                       'history', 'aims', 'events', 'activities',
                                       'structure', 'staff', 'financing',
                                       'languages', 'consultative_status',
                                       'relations_igos', 'relations_ngos',
                                       'publications', 'information_services',
                                       'members', 'last_news'])

    # output = ''
    for row in rows:
        logger.info("{0.fk_org}: {0.org_name}".format(row))

        # logger.info(clean_list(row.members))  # TODO: Finish members
        # output += '<h2>{0}: {1}</h2>'.format(i, row.org_name)
        # output += str(row.contact_details)
        # output += '<pre><code>'+str(clean_contact(row.contact_details))+'</pre></code>'
        # output += '<hr>'
        # show(clean_list(row.members))

        # TODO: members
        # TODO: relations_with_inter_governmental_organizations
        # TODO: relations_With_non_governmental_organization
        # TODO: consultative_status
        # TODO: languages

        subjects = clean_subject(row.subjects)
        contact_details = clean_contact(row.contact_details)

        if contact_details:
            org_url = contact_details.url
            contacts = contact_details.contacts
        else:
            org_url = contacts = None

        cleaned = CleanOrg(row.id_org, row.org_name_t, row.org_acronym_t,
                           org_url, row.org_founded_t, row.org_city_hq_t,
                           row.org_country_hq_t, row.org_type_i_t,
                           row.org_type_ii_t, row.org_type_iii_t,
                           clean_type(row.type_i_classification),
                           clean_type(row.type_ii_classification),
                           row.org_uia_id_t, row.org_url_id,
                           row.org_subject_t,
                           strip_tags(row.history), strip_tags(row.aims),
                           clean_events(row.events), strip_tags(row.activities),
                           clean_delim(row.structure), strip_tags(row.staff),
                           strip_tags(row.financing), None,
                           None, None,
                           None, clean_delim(row.publications),
                           strip_tags(row.information_services), None,
                           clean_news(row.last_news_received))

        clean_org_to_db(cleaned, subjects, contacts)
    # show(output)

def clean_org_to_db(clean, subjects, contacts):
    db = DB()

    # Insert organization
    db.c.execute("""INSERT OR IGNORE INTO organizations_final
                 {0} VALUES ({1})"""
                 .format(clean._fields, ', '.join('?' for _ in clean._fields)),
                 (clean))

    # Insert subjects
    if subjects:
        # Insert subjects indivudally since there's no way to use executemany
        # *and* get the resultant row IDs *and* get the IDs of the ignored rows
        subject_ids = []
        for subject in subjects:
            db.c.execute("""INSERT OR IGNORE INTO subjects
                         (subject_name, subject_parent)
                         VALUES (?, ?)""",
                         (subject.level_2, subject.level_1))
            db.c.execute("""SELECT id_subject FROM subjects WHERE
                         subject_name = ? AND subject_parent = ?""",
                         (subject.level_2, subject.level_1))
            subject_ids.append(db.c.fetchall()[0][0])

        # Insert organization and subject IDs into the junction table
        db.c.executemany("""INSERT OR IGNORE INTO orgs_subjects
                      (fk_org, fk_subject)
                      VALUES (?, ?)""",
                      ([(clean.id_org, sub) for sub in subject_ids]))

    # Insert contacts
    if contacts:
        # Insert contacts individually again, since executemany doesn't play
        # well with auto-incrementing IDs
        contact_ids = []
        for contact in contacts:
            db.c.execute("""INSERT INTO contacts
                         (contact_details, contact_phone,
                          contact_fax, contact_email)
                         VALUES (?, ?, ?, ?)""", (contact))
            contact_ids.append(db.c.lastrowid)

        # Insert organization and contact IDs into the junction table
        db.c.executemany("""INSERT OR IGNORE INTO orgs_contacts
                         (fk_org, fk_contact)
                         VALUES (?, ?)""",
                         ([(clean.id_org, con) for con in contact_ids]))

    # db.conn.commit()

if __name__ == '__main__':
    clean_rows()
