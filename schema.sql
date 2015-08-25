PRAGMA foreign_keys = ON;

CREATE TABLE organizations (
  id_org integer PRIMARY KEY,
  org_name_t text NOT NULL,
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


-- Final tables
CREATE TABLE organizations_final (
  id_org integer PRIMARY KEY,
  org_name text NOT NULL,
  acronym text,
  founded text,
  city_hq text,
  country_hq text,
  type_i_dir text,
  type_ii_dir text,
  type_iii_dir text,
  type_i text,
  type_ii text,
  uia_id text NOT NULL,
  url_id text NOT NULL,
  subject_dir text,
  history text,
  aims text,
  events text,
  activities text,
  structure text,
  staff text,
  financing text,
  languages text,
  consultative_status text,
  relations_igos text,
  relations_ngos text,
  publications text,
  information_services text,
  members text,
  last_news text,
  contact text
);
CREATE UNIQUE INDEX org_url_index_final ON organizations_final (url_id);

CREATE TABLE subjects (
  id_subject integer PRIMARY KEY,
  subject_name text NOT NULL,
  subject_parent text NOT NULL
);
CREATE UNIQUE INDEX subject_index ON subjects (subject_name, subject_parent);

CREATE TABLE orgs_subjects (
  fk_org integer NOT NULL,
  fk_subject integer NOT NULL,
  FOREIGN KEY (fk_org) REFERENCES organizations (id_org) ON DELETE CASCADE,
  FOREIGN KEY (fk_subject) REFERENCES subjects (id_subject) ON DELETE CASCADE,
  PRIMARY KEY(fk_org, fk_subject)
);
