#!/usr/bin/env python3
# Modules
import config
import logging
import os
import pickle
import requests
import sqlite3
from bs4 import BeautifulSoup
from random import choice

# Enable logging for library
# https://docs.python.org/3.4/howto/logging.html#library-config
# logging.getLogger().addHandler(logging.NullHandler())
logger = logging.getLogger(__name__)


class YIO():
    """Connect to the Yearbook of International Organizations through
    Duke's Shibboleth authentication system.
    """
    def __init__(self):
        config.BASE_URL

        # If there's a pre-logged-in session, use it.
        # You can't pickle self and reload it again,
        # but you can pickle self.__dict__ and self.update it
        if os.path.isfile("yio.pickle"):
            with open("yio.pickle", 'rb') as f:
                self.__dict__.update(pickle.load(f))
            logger.info("No need to log in---using existing session.")
        # Otherwise log in and save the session to file
        else:
            logger.info("Logging in to YIO through Duke's library.")
            self.s = requests.session()
            self.s.headers.update({"User-Agent": choice(config.user_agents)})
            self.login_through_duke()

            with open('yio.pickle', 'wb') as f:
                pickle.dump(self.__dict__, f)
            logger.info("Saving session to file for future use.")

    def login_through_duke(self):
        """Bounce between all the different authentication layers to log into
        the Yearbook site.

        Leaves self.s logged in and ready to be used for all other YIO URLs
        """

        # URLs to be used
        yio_url = config.BASE_URL + "/ybio"
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
        logger.info("\ (•◡•) /  All logged in!  \ (•◡•) /")


class DB():
    """Functions to interface with SQLite database."""
    def __init__(self, factory=None):
        self.conn = sqlite3.connect(config.DB_FILE,
                                    detect_types=sqlite3.PARSE_DECLTYPES)
        self.c = self.conn.cursor()

        # Turn on foreign keys
        self.c.execute("PRAGMA foreign_keys = ON")

        # If the database is brand new, set up the structure
        table_info = self.c.execute("PRAGMA table_info(organizations);").fetchall()

        if len(table_info) == 0:
            logger.info("Creating new database.")
            self.create()

        # Closure wizardry: http://stackoverflow.com/a/4020443/120898
        if factory:
            logger.info("Adding a row factory")

            def build_factory(fac):
                def namedtuple_factory(cursor, row):
                    return fac(*row)
                return namedtuple_factory

            # Add the factory and update the cursor
            self.conn.row_factory = build_factory(factory)
            self.c = self.conn.cursor()

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

    def add_raw_columns(self, colnames):
        # Make the list a set for cool set math functions
        colnames = set(colnames)

        # Get names of existing columns
        existing_cols_raw = (self.c
                             .execute("PRAGMA table_info(organizations_raw);")
                             .fetchall())

        if len(existing_cols_raw) == 0:
            start_raw_table = """
                PRAGMA foreign_keys = ON;

                CREATE TABLE organizations_raw (
                  fk_org integer NOT NULL,
                  FOREIGN KEY (fk_org) REFERENCES organizations (id_org) ON DELETE CASCADE,
                  PRIMARY KEY(fk_org)
                );"""

            # Create new table
            for command in start_raw_table.split(";"):
                self.c.execute(command)

            # Get names of existing columns again
            existing_cols_raw = (self.c
                                 .execute("PRAGMA table_info(organizations_raw);")
                                 .fetchall())

        existing_cols = set([col[1] for col in existing_cols_raw])

        # Determine which columns don't exist yet
        new_cols = colnames.difference(existing_cols)

        # Add new columns if needed
        if len(new_cols) > 0:
            for col in new_cols:
                self.c.execute("ALTER TABLE organizations_raw ADD COLUMN {0} text"
                               .format(col))
