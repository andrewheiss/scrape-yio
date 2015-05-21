#!/usr/bin/env python3

# --------------
# Load modules
# --------------
import config
import json
import logging
import os
import pickle
import re
import requests
import sqlite3
import sys
from bs4 import BeautifulSoup
from collections import namedtuple
from random import choice
from time import sleep

from pprint import pprint

BASEURL = "http://ybio.brillonline.com.proxy.lib.duke.edu"


# ------------
# Set up log
# ------------
# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(levelname)s %(asctime)s: %(message)s")

# Create handlers
to_console = logging.StreamHandler()
to_console.setLevel(logging.WARNING)
to_file = logging.FileHandler("yio.log", mode="a")

# Add formatting
to_console.setFormatter(formatter)
to_file.setFormatter(formatter)

# Add to logger
logger.addHandler(to_console)
logger.addHandler(to_file)

# Function to redirect exceptions to the log
# Via http://stackoverflow.com/a/16993115/120898
def handle_exception(exc_type, exc_value, exc_traceback):
    # Ignore KeyboardInterrupt so a console Python program can exit with Ctrl + C
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception


# ---------
# Classes
# ---------
class YIO():
    """Connect to the Yearbook of International Organizations through
    Duke's Shibboleth authentication system.
    """
    def __init__(self):
        self.s = requests.session()
        self.s.headers.update({"User-Agent": choice(config.user_agents)})

        self.login_through_duke()

    def login_through_duke(self):
        """Bounce between all the different authentication layers to log into
        the Yearbook site.

        Leaves self.s logged in and ready to be used for all other YIO URLs
        """

        # URLs to be used
        yio_url = BASEURL + "/ybio"
        shib_url = "https://shib.oit.duke.edu/idp/profile/SAML2/POST/SSO"
        shib_login_url = "https://shib.oit.duke.edu/idp/authn/external"

        # ----------------------------------------------------------------
        # Step 1: Go to the first YIO page to get authentication cookies
        # ----------------------------------------------------------------
        initial_yio_page = self.s.get(yio_url).text

        if "Shibboleth Authentication Request" not in initial_yio_page:
            raise RuntimeError("Did not correctly connect to the initial YIO proxy page.")
        else:
            soup = BeautifulSoup(initial_yio_page)
            relaystate = soup.find(attrs={"name": "RelayState"})
            samlrequest = soup.find(attrs={"name": "SAMLRequest"})

            # Use these two values in the POST data
            saml_relay_data = {"RelayState": relaystate['value'],
                               "SAMLRequest": samlrequest['value']}

        # -------------------------------------------------------------
        # Step 2: Go to Duke's login page with the YIO SAML POST data
        # -------------------------------------------------------------
        duke_shib_page = self.s.post(shib_url, data=saml_relay_data).text

        if "This service requires cookies" in duke_shib_page:
            raise RuntimeError("Did not get the correct Duke login page.")
        else:
            duke_form_data = {
                "j_username": config.duke_username,
                "j_password": config.duke_password,
                "passwordEntered": "1"
            }

        # ------------------------------------------------------------
        # Step 3: Submit Duke's login form and get redirected to YIO
        # ------------------------------------------------------------
        response_yio = self.s.post(shib_login_url, data=duke_form_data).text

        if "you must press the Continue button once to proceed" not in response_yio:
            raise RuntimeError("Did not login to Duke or redirect to YIO.")
        else:
            soup = BeautifulSoup(response_yio)

            action_url = soup.find('form')['action']
            relaystate = soup.find(attrs={"name": "RelayState"})
            samlresponse = soup.find(attrs={"name": "SAMLResponse"})

            saml_response_data = {"RelayState": relaystate['value'],
                                  "SAMLResponse": samlresponse['value']}

        # --------------------------------------------------------------
        # Step 4: Submit the final authenticated SAML POST data to YIO
        # --------------------------------------------------------------
        self.s.post(action_url, data=saml_response_data)

        # \ (•◡•) /  All logged in!  \ (•◡•) /


class DB():
    """Functions to interface with SQLite database."""
    def __init__(self, database):
        self.conn = sqlite3.connect(database,
                                    detect_types=sqlite3.PARSE_DECLTYPES)
        self.c = self.conn.cursor()

        # Turn on foreign keys
        self.c.execute("PRAGMA foreign_keys = ON")

        # If the database is brand new, set up the structure
        table_info = self.c.execute("PRAGMA table_info(organizations);").fetchall()

        if len(table_info) == 0:
            logger.info("Creating new database.")
            self.create()

    def create(self):
        # Read the schema file and separate into a list of individual commands
        create_command = open("schema.sql", "r").read().split(";")

        # Execute each command
        for command in create_command:
            self.c.execute(command)

    def insert_org_basic(self, org_details):
        var_names = ", ".join(org_details.keys())
        placeholders = ", ".join([":" + key for key in org_details.keys()])

        insert_string = ("INSERT OR IGNORE INTO organizations ({0}) VALUES ({1})"
                         .format(var_names, placeholders))
        self.c.execute(insert_string, org_details)

        if self.c.rowcount == 1:
            logger.info("Inserted {0} ({1}) into database."
                        .format(org_details['org_name'],
                                org_details['org_url_id']))
        else:
            logger.info("Skipping {0} ({1}). Already in database."
                        .format(org_details['org_name'],
                                org_details['org_url_id']))

        self.conn.commit()

    def close(self):
        self.c.close()
        self.conn.close()

    def add_columns(self, colnames):
        # Make the list a set for cool set math functions
        colnames = set(colnames)

        # Get names of existing columns
        existing_cols_raw = (self.c
                             .execute("PRAGMA table_info(organizations);")
                             .fetchall())
        existing_cols = set([col[1] for col in existing_cols_raw])

        # Determine which columns don't exist yet
        new_cols = colnames.difference(existing_cols)

        # Add new columns if needed
        if len(new_cols) > 0:
            for col in new_cols:
                self.c.execute("ALTER TABLE organizations ADD COLUMN {0} text"
                               .format(col))


def namify(heading_name):
    """Convert to lowercase and replace all spaces with _s"""
    return(heading_name.strip().replace(" ", "_").lower())


def clean_text(org_name):
    """Get rid of all extra whitespace and newlines"""
    return(re.sub("\s+", " ", org_name.strip()))


def subject_url(subject, page=None):
    """Construct URL for subject page to be scraped"""
    url = "/ybio/?wcodes={0}&wcodes_op=contains".format(subject)
    return(BASEURL + url)


def extract_individual_org(page):
    # Select just the main content section
    soup = BeautifulSoup(page)
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

    # Initialize dictionary to be saved as JSON
    raw_data = {}
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

    # Save as JSON, just for fun(?)
    with open('json/{0}.json'.format(namify(org_name)), 'w') as f:
        json.dump(raw_data, f)

    # TODO: Clean up all the fields
    # TODO: Save links to scrape later
    # TODO: Get URL id
    # colnames = ["testing", "testing2", "testing3", "testing4"]
    # db.add_columns(colnames)


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

        db.insert_org_basic(org_details)

    # Check if there's a next page
    pager = soup.select(".view-yearbook-working .pager")[0]
    next_page_raw = pager.select(".pager-next")

    if len(next_page_raw) > 0:
        next_page = BASEURL + next_page_raw[0].select("a")[0]['href']
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


# ------------
# Run script
# ------------
def main():
    """Run actual script."""

    # Open database
    db = DB("data/yio.db")

    # If there's a pre-logged-in session, use it
    if os.path.isfile("yio.pickle"):
        with open("yio.pickle", 'rb') as f:
            yio = pickle.load(f)
        logger.info("No need to log in---using existing session.")
    # Otherwise log in and save the session to file
    else:
        logger.info("Logging in to YIO through Duke's library.")
        yio = YIO().s
        with open('yio.pickle', 'wb') as f:
            pickle.dump(yio, f)
        logger.info("Saving session to file for future use.")

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
        # parse_subject_page(yio, subject.url, subject.name, db)

    # Close everything up
    db.close()

    # Combine all the JSON files into one big file?
    # import glob
    # read_files = glob.glob("json/*.json")
    # with open("merged_file.json", "w") as outfile:
    #     outfile.write('[{}]'.format(
    #         ','.join([open(f, "r").read() for f in read_files])))

    # Do stuff with it in R...
    # library(jsonlite)
    # mydf <- fromJSON("~/Research/•Sandbox/scrape-yio/merged_file.json")


if __name__ == '__main__':
    main()
