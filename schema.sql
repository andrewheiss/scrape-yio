PRAGMA foreign_keys = ON;

CREATE TABLE organizations (
  id_org integer PRIMARY KEY,
  org_name text NOT NULL,
  org_name_full text,
  org_acronym_t text,
  org_founded_t text,
  org_city_hq_t text,
  org_country_hq_t text,
  org_type_i_t text,
  org_type_ii_t text,
  org_type_iii_t text,
  org_uia_id_t text,
  org_url text NOT NULL,
  org_url_id text NOT NULL,
  org_subject_t text NOT NULL
);
CREATE UNIQUE INDEX org_url_index ON organizations (org_url_id);
