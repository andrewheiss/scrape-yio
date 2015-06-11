#!/usr/bin/env python3

# ------------------------------------------------------------------------------
# NB: It's best to run this in a virutal machine so it's minimizable/hideable.
# Selenium can't run browsers in the background.
# ------------------------------------------------------------------------------

# --------------
# Load modules
# --------------
# My modules
import config
import scrape_yio
from yio import DB

# Pip-installed modules
import logging

# Just parts of modules
from collections import namedtuple
from random import choice, sample
from time import sleep
from selenium import webdriver
from selenium.common.exceptions import NoAlertPresentException

# Start log
logger = logging.getLogger(__name__)


# Determine which pages to get
def get_ids(db, k):
    # Create sets of the primary and foreign key ids from all the tables
    db.c.execute("SELECT id_org FROM organizations")
    master_list = {row_id[0] for row_id in db.c.fetchall()}

    db.c.execute("SELECT fk_org FROM organizations_raw")
    already_processed = {row_id[0] for row_id in db.c.fetchall()}

    db.c.execute("SELECT fk_org FROM data_raw")
    saved_raw = {row_id[0] for row_id in db.c.fetchall()}

    # Determine which ids in the master list haven't already been processed
    orgs_todo = master_list - already_processed - saved_raw

    # Select a random subset of uncaptured organizations
    OrgInfo = namedtuple('OrgInfo', ['id_org', 'name', 'url'])
    db.add_factory(factory=OrgInfo)

    do_these = [str(org) for org in sample(orgs_todo, k)]
    subset_sql = ("SELECT id_org, org_name, org_url FROM organizations "
                  "WHERE id_org IN ({0})""".format(", ".join(do_these)))
    db.c.execute(subset_sql)
    orgs_to_process = db.c.fetchall()

    return(orgs_to_process)


# Manually get pages
def get_page(browser, url):
    browser.get(url)
    logger.info(browser.title)

    # Acknowledge the broken Google Maps warning alert
    # There are actual ways to check for alerts with Selenium,
    # but this works well enough.
    try:
        browser.switch_to.alert.accept()
    except NoAlertPresentException:
        pass

    # Select just the #content div
    # content = browser.find_element_by_id("content")
    # return(content.get_attribute('innerHTML'))

    # But, just to be safe, save the whole stinking page
    return(browser.page_source)


# Log in
def login_manually(browser):
    browser.get("http://ybio.brillonline.com.proxy.lib.duke.edu")

    assert "NetID Services" in browser.title
    logger.info("Logging in through Duke.")

    username_input = browser.find_element_by_id("j_username")
    password_input = browser.find_element_by_id("j_password")

    username_input.send_keys(config.duke_username)
    password_input.send_keys(config.duke_password)

    browser.find_element_by_id("Submit").click()


# Parse the raw HTML and save as raw columned data
def parse_raw_html():
    OrgPage = namedtuple('OrgPage', ['id_org', 'org_html'])

    # Open database and log into YIO
    db = DB()
    db.add_factory(factory=OrgPage)

    db.c.execute("SELECT fk_org, org_html FROM data_raw")

    orgs = db.c.fetchall()

    db.add_factory(None)  # Clear custom factory
    for org in orgs[0:1]:
        logger.info("Parsing details for {0}".format(org.id_org))
        scrape_yio.parse_individual_org(None, org, db)


# This is all totally procedural, not functional or object-oriented at all,
# but that's okay because it's really just replicating the exact procedures
# a human does (and I don't want to OOP it, since this is all just temporary)
def get_raw_html(num_orgs):
    # Choose a random browser
    if choice(["Chrome", "Firefox"]) is "Firefox":
        browser = webdriver.Firefox()
    else:
        # Download this from https://sites.google.com/a/chromium.org/chromedriver/
        browser = webdriver.Chrome("bin/chromedriver")

    login_manually(browser)

    db = DB()
    orgs_to_get = get_ids(db, num_orgs)

    # Get, save, wait, repeat
    for org in orgs_to_get:
        logger.info("Getting details for {0}.".format(org.name))
        raw_html = get_page(browser, org.url)
        data_to_insert = {"fk_org": org.id_org, "org_html": raw_html}
        db.insert_dict(data_to_insert, table="data_raw")
        wait = choice(config.wait_time)
        logger.info("Waiting for {0} seconds before moving on".format(wait))
        sleep(wait)

    browser.close()
    db.close()


if __name__ == '__main__':
    get_raw_html(num_orgs=2)
