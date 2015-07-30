#!/usr/bin/env python3

# --------------
# Load modules
# --------------
# My modules
import config
from yio import YIO, DB

# Pip-installed modules
import logging
import re
import requests

# Just parts of modules
from bs4 import BeautifulSoup
from collections import namedtuple
from random import choice
from time import sleep

from pprint import pprint

# Start log
logger = logging.getLogger(__name__)


# Useful functions
def namify(heading_name):
    """Convert to lowercase and replace all spaces with _s"""
    return(heading_name.strip().replace(" ", "_").replace("-", "_").lower())


def clean_text(org_name):
    """Get rid of all extra whitespace and newlines"""
    return(re.sub("\s+", " ", org_name.strip()))


def subject_url(subject, page=None):
    """Construct URL for subject page to be scraped"""
    url = "/ybio/?wcodes={0}&wcodes_op=contains".format(subject)
    return(config.BASE_URL + url)


# Scraping functions
def parse_individual_org(session, org, db):
    # Hacky thing. Ordinarily, this takes an existing YIO session object and
    # uses it to get a URL and then parse it. However, since I can't scrape
    # with requests anymore and have to manually collect the remaining few
    # rows, I have all the organzation content saved as HTML in the data_raw
    # table. So instead of getting a URL, if the session parameter is empty,
    # this will just start parsing the pre-saved HTML.
    if type(session) is requests.sessions.Session:
        print("This is a session object.")
        logger.info("Getting organization details from {0}".format(org.url))
        page = session.get(org.url).text
    else:
        logger.info("Using existing HTML for {0}".format(org.id_org))
        page = org.org_html

    soup = BeautifulSoup(page)

    # Select just the main content section
    try:
        content = soup.select("#content")[0]

        # Get rid of embedded Javascript
        [tag.extract() for tag in content.findAll("script")]

        # Get organization name
        org_name = clean_text(content.find("h1").get_text())

        # Find all H2s, since the page is structured like so:
        #   <h2></h2>
        #   <p></p>
        #   <h2></h2>
        #   <p></p>
        #   etc.
        headings = content.findAll("h2")

        # Initialize dictionary to be saved to the database
        raw_data = {}
        raw_data['fk_org'] = org.id_org
        raw_data['org_name'] = org_name

        # Loop through each heading, move along each sibling until coming to a H2
        for heading in headings:
            raw_section = []  # Track the parts of the section
            for sibling in heading.next_siblings:
                if sibling.name == "h2":
                    break  # Stop, since we're in a new section
                else:
                    if sibling != "\n":
                        raw_section.append(str(sibling))  # Add to section

            # Save the section to the dictionary
            raw_data[namify(heading.get_text())] = '\n'.join(raw_section)

        # pprint(raw_data)

        # This is tremendously hacky, but I have no idea which sections the YIO
        # uses---they change depending on the organization. So, this
        # (inefficiently, probably) adds new columns to the organizations_raw table
        # as necessary
        colnames = raw_data.keys()
        db.add_raw_columns(colnames)

        db.insert_dict(raw_data, table="organizations_raw")
    except Exception as e:
        message = "{0} ({1}): row {2}\n".format(e.__class__.__name__,
                                                e, org.id_org)
        logger.warning(message)

        with open("borked.txt", "a") as myfile:
            myfile.write(message)

        return


def parse_subject_page(session, url, subject, db):
    logger.info("Parsing organizations listed at {0}".format(url))
    page = session.get(url).text
    soup = BeautifulSoup(page)
    table = soup.select(".view-yearbook-working .views-table")[0]

    # Loop through each row in the table and add it to the database
    for org in table.select("tr")[1:]:
        org_details = extract_from_row(org)
        org_details['org_subject_t'] = subject

        logger.info("Dealing with {0} ({1})."
                    .format(org_details['org_name'],
                            org_details['org_url_id']))

        # db.insert_org_basic(org_details)
        db.insert_dict(org_details, table="organizations")

    # Check if there's a next page
    pager = soup.select(".view-yearbook-working .pager")[0]
    next_page_raw = pager.select(".pager-next")

    if len(next_page_raw) > 0:
        next_page = config.BASE_URL + next_page_raw[0].select("a")[0]['href']
    else:
        next_page = None

    # Recursively get and parse the next page
    if next_page is not None:
        logger.info("There's another page. Parse it.")

        wait = choice(config.wait_time)
        logger.info("Waiting for {0} seconds before moving on".format(wait))
        sleep(wait)
        parse_subject_page(session, next_page, subject, db)


def extract_from_row(org):
    org_details = {}

    org_raw = org.select("td")

    # Parse name and URL information
    org_details['org_name'] = clean_text(org_raw[0].get_text())
    org_details['org_url'] = clean_text(org_raw[0].select("a")[0]['href'])
    org_details['org_url_id'] = re.search(r"/(\d+)$",
                                          org_details['org_url']).group(1)

    # Get all other details
    org_details['org_acronym_t'] = clean_text(org_raw[1].get_text())
    org_details['org_founded_t'] = clean_text(org_raw[2].get_text())
    org_details['org_city_hq_t'] = clean_text(org_raw[3].get_text())
    org_details['org_country_hq_t'] = clean_text(org_raw[4].get_text())
    org_details['org_type_i_t'] = clean_text(org_raw[5].get_text())
    org_details['org_type_ii_t'] = clean_text(org_raw[6].get_text())
    org_details['org_type_iii_t'] = clean_text(org_raw[7].get_text())
    org_details['org_uia_id_t'] = clean_text(org_raw[8].get_text())

    # Convert blank cells to none
    for key, value in org_details.items():
        if value == '':
            org_details[key] = None

    return(org_details)


def parse_manual_orgs():
    ManualOrg = namedtuple('ManualOrg', ['id_org', 'org_html'])

    db = DB()
    db.add_factory(factory=ManualOrg)

    db.c.execute("SELECT fk_org, org_html FROM data_raw")

    orgs = db.c.fetchall()

    db.add_factory(None)  # Clear custom factory

    for org in orgs:
        parse_individual_org(None, org, db)


# ------------
# Run script
# ------------
def scrape_subjects():
    """Run actual script."""

    # Open database and log into YIO
    db = DB()
    yio = YIO().s

    # First page of the subject
    subject_page = namedtuple('SubjectPage', ['name', 'url'])
    subjects = [
        subject_page(name="Censorship", url=subject_url("Censorship")),
        subject_page(name="Journalism", url=subject_url("Journalism")),
        subject_page(name="Media", url=subject_url("Media")),
        subject_page(name="Education", url=subject_url("Education"))
    ]

    for subject in subjects[:1]:
        logger.info("Beginning to parse the {0} subject ({1})"
                    .format(subject.name, subject.url))
        parse_subject_page(yio, subject.url, subject.name, db)

    # Close everything up
    db.close()


def scrape_org():
    OrgPage = namedtuple('OrgPage', ['id_org', 'name', 'url'])

    # Open database and log into YIO
    db = DB()
    db.add_factory(factory=OrgPage)
    yio = YIO().s

    db.c.execute("SELECT id_org, org_name, org_url FROM organizations")

    orgs = db.c.fetchall()

    db.add_factory(None)  # Clear custom factory
    for org in orgs[0:1]:
        wait = choice(config.wait_time)
        logger.info("Waiting for {0} seconds before moving on".format(wait))
        sleep(wait)
        logger.info("Parsing details for ({1}) {0}".format(org.name, org.id_org))
        parse_individual_org(yio, org, db)
    # TODO: UNESCO (2744) is broken: http://ybio.brillonline.com.proxy.lib.duke.edu/s/or/en/1100010946
    # TODO: Check if 2745 is done


if __name__ == '__main__':
    # scrape_subjects()
    # scrape_org()
    parse_manual_orgs()
