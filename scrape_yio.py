#!/usr/bin/env python3

# --------------
# Load modules
# --------------
import config
import requests
import json
import re
from bs4 import BeautifulSoup
from random import choice

from pprint import pprint


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
        yio_url = "http://ybio.brillonline.com.proxy.lib.duke.edu/ybio"
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

def namify(heading_name):
    """Convert to lowercase and replace all spaces with _s"""
    return(heading_name.strip().replace(" ", "_").lower())

def clean_name(org_name):
    """Get rid of all extra whitespace and newlines"""
    return(re.sub("\s+", " ", org_name.strip()))

def extract_individual_org(page):
    # Select just the main content section
    soup = BeautifulSoup(page)
    content = soup.select("#content")[0]

    # Get rid of embedded Javascript
    [tag.extract() for tag in content.findAll("script")]

    # Get organization name
    org_name = clean_name(content.find("h1").get_text())

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
    # TODO: Save information from table listing, like UIA Org ID, acronym, etc.


# ------------
# Run script
# ------------
def main():
    """Run actual script."""
    # yio = YIO().s

    url = "http://ybio.brillonline.com.proxy.lib.duke.edu/ybio/v3/"
    org1 = "http://ybio.brillonline.com.proxy.lib.duke.edu/s/or/en/1100065284"

    # extract_individual_org(yio.get(org1).text)
    temp = open('individual.html', 'r').read()
    extract_individual_org(temp)

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
