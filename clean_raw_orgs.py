#!/usr/bin/env python3

import config
from yio import DB

import logging
import re
from bs4 import BeautifulSoup
from collections import namedtuple

def clean_simple(cell):
    soup = BeautifulSoup(cell)
    return soup.get_text()

def clean_rows():
    db = DB()

    # Get existing column names and create named tuple row factory
    colnames_raw = db.c.execute("PRAGMA table_info(organizations_raw);").fetchall()
    colnames = [col[1] for col in colnames_raw]
    OrgRawRow = namedtuple("OrgRawRow", colnames)
    db.add_factory(factory=OrgRawRow)

    results = db.c.execute("SELECT * FROM organizations_raw")

    rows = results.fetchall()

    for row in rows[:1]:
        # type_i = clean_simple(row.type_i_classification)

        type_i = re.search(r"^(\w):",
                           clean_simple(row.type_i_classification)).group(1)

        print(type_i)

if __name__ == '__main__':
    clean_rows()
