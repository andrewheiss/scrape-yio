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
  org_url text,
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
  last_news text
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

CREATE TABLE contacts (
  id_contact integer PRIMARY KEY,
  contact_details text,
  contact_phone text,
  contact_fax text,
  contact_email text
);

CREATE TABLE orgs_contacts (
  fk_org integer NOT NULL,
  fk_contact integer NOT NULL,
  FOREIGN KEY (fk_org) REFERENCES organizations (id_org) ON DELETE CASCADE,
  FOREIGN KEY (fk_contact) REFERENCES contacts (id_contact) ON DELETE CASCADE,
  PRIMARY KEY(fk_org, fk_contact)
);


-- Types
CREATE TABLE type_i (
  id_type_i integer PRIMARY KEY NOT NULL,
  type_i text NOT NULL,
  type_i_description text NOT NULL,
  type_i_full_description text NOT NULL
);
CREATE UNIQUE INDEX type_i_index ON type_i (type_i);

INSERT INTO "type_i" VALUES(1,'A','Federations of international organizations','A principal membership category includes at least three autonomous international bodies');
INSERT INTO "type_i" VALUES(2,'B','Universal membership organizations','Membership covers at least 60 countries regardless of distribution, or membership covers at least 30 countries and is equitably distributed over several continents');
INSERT INTO "type_i" VALUES(3,'C','Intercontinental membership organizations','Membership exceeds that of a particular continental region, covers at least 10 countries, and is equitably distributed over at least two continents');
INSERT INTO "type_i" VALUES(4,'D','Regionally defined membership organizations','Membership and preoccupations restricted to a particular continental or sub-continental region or contiguous group of countries, and covers at least 3 countries or includes at least 3 autonomous international bodies');
INSERT INTO "type_i" VALUES(5,'E','Organizations emanating from places, persons or other bodies','May include international centres and institutes created by intergovernmental bodies, and joint bodies, regardless of membership');
INSERT INTO "type_i" VALUES(6,'F','Organizations having a special form','May include foundations, funds, banks, and illegal or unusual bodies');
INSERT INTO "type_i" VALUES(7,'G',' Internationally-oriented national organizations','Includes bilateral bodies, organizations with membership or management structure limited to a single country yet name or activities indicate an international character, and national bodies with formal links (member, funder, partner) with a body of the UN system or other international organization');
INSERT INTO "type_i" VALUES(8,'H','Inactive or dissolved international organizations','Dissolved or inactive organization previously classified as a Type A, B, C or D');
INSERT INTO "type_i" VALUES(9,'J','Recently reported or proposed international organizations','Information available is insufficient to enable classification as another Type');
INSERT INTO "type_i" VALUES(10,'K','Subsidiary and internal bodies','A substantive unit within a complex international organization which has a degree of autonomy');
INSERT INTO "type_i" VALUES(11,'N','National organizations','Membership or management structure is essentially limited to a single country, yet title or activities make it appear to be international');
INSERT INTO "type_i" VALUES(12,'R','Religious orders, fraternities and secular institutes','A religious or fraternal order or similar body based on commitment to a set of religious practices. Membership covers at least 3 countries');
INSERT INTO "type_i" VALUES(13,'S','Autonomous conference series','Not an organization as such but represents a continuing series of international meetings which has a name which could be assumed to refer to an international body');
INSERT INTO "type_i" VALUES(14,'T','Multilateral treaties and agreements','Not an organization as such but a multilateral treaty, convention, agreement, pact, protocol or covenant signed by at least 3 parties, whether States or intergovernmental organizations');
INSERT INTO "type_i" VALUES(15,'U','Inactive or dissolved non-conventional bodies','Dissolved or inactive organization previously classified as a Type other than A, B, C or D');

CREATE TABLE type_ii (
  id_type_ii integer PRIMARY KEY NOT NULL,
  type_ii text NOT NULL,
  type_ii_description text NOT NULL
);
CREATE UNIQUE INDEX type_ii_index ON type_ii (type_ii);

INSERT INTO "type_ii" VALUES(1,'b','bilateral intergovernmental organization (normally but not always assigned to Type G)');
INSERT INTO "type_ii" VALUES(2,'c','conference series (normally but not always assigned to Type S)');
INSERT INTO "type_ii" VALUES(3,'d','dissolved, dormant (normally but not always assigned to Type H or Type U)');
INSERT INTO "type_ii" VALUES(4,'e','commercial enterprise');
INSERT INTO "type_ii" VALUES(5,'f','foundation, fund (normally but not always assigned to Type F)');
INSERT INTO "type_ii" VALUES(6,'g','intergovernmental');
INSERT INTO "type_ii" VALUES(7,'j','research institute');
INSERT INTO "type_ii" VALUES(8,'n','has become national (normally but not always assigned to Type N)');
INSERT INTO "type_ii" VALUES(9,'p','proposed body (normally but not always assigned to Type J)');
INSERT INTO "type_ii" VALUES(10,'s','information suspect');
INSERT INTO "type_ii" VALUES(11,'v','individual membership only');
INSERT INTO "type_ii" VALUES(12,'x','no recent information received');
INSERT INTO "type_ii" VALUES(13,'y','international organization membership');

CREATE TABLE type_iii (
  id_type_iii integer PRIMARY KEY NOT NULL,
  type_iii text NOT NULL
);
CREATE UNIQUE INDEX type_iii_index ON type_iii (type_iii);

INSERT INTO "type_iii" VALUES(1,'Academies');
INSERT INTO "type_iii" VALUES(2,'Agencies');
INSERT INTO "type_iii" VALUES(3,'Alumni and Veterans');
INSERT INTO "type_iii" VALUES(4,'Banks');
INSERT INTO "type_iii" VALUES(5,'Charismatic Bodies');
INSERT INTO "type_iii" VALUES(6,'Clubs');
INSERT INTO "type_iii" VALUES(7,'Colleges');
INSERT INTO "type_iii" VALUES(8,'Common Markets and Free Trade Zones');
INSERT INTO "type_iii" VALUES(9,'Conference Series');
INSERT INTO "type_iii" VALUES(10,'Corporations, Companies');
INSERT INTO "type_iii" VALUES(11,'Courts, Tribunals');
INSERT INTO "type_iii" VALUES(12,'European Union Bodies');
INSERT INTO "type_iii" VALUES(13,'Exile Bodies');
INSERT INTO "type_iii" VALUES(14,'FAO Bodies');
INSERT INTO "type_iii" VALUES(15,'Foundations');
INSERT INTO "type_iii" VALUES(16,'Funds');
INSERT INTO "type_iii" VALUES(17,'Human Rights Organizations');
INSERT INTO "type_iii" VALUES(18,'Humanitarian Organizations');
INSERT INTO "type_iii" VALUES(19,'ILO Bodies');
INSERT INTO "type_iii" VALUES(20,'Individual Membership Bodies');
INSERT INTO "type_iii" VALUES(21,'Influential Policy Groups');
INSERT INTO "type_iii" VALUES(22,'Institutes');
INSERT INTO "type_iii" VALUES(23,'Intergovernmental Communities');
INSERT INTO "type_iii" VALUES(24,'International Federations');
INSERT INTO "type_iii" VALUES(25,'Multinational Company Councils');
INSERT INTO "type_iii" VALUES(26,'NATO Bodies');
INSERT INTO "type_iii" VALUES(27,'Networks');
INSERT INTO "type_iii" VALUES(28,'Parliaments');
INSERT INTO "type_iii" VALUES(29,'Plans');
INSERT INTO "type_iii" VALUES(30,'Political Parties');
INSERT INTO "type_iii" VALUES(31,'Professional Bodies');
INSERT INTO "type_iii" VALUES(32,'Programmes');
INSERT INTO "type_iii" VALUES(33,'Projects');
INSERT INTO "type_iii" VALUES(34,'Proper Names');
INSERT INTO "type_iii" VALUES(35,'Religious Orders');
INSERT INTO "type_iii" VALUES(36,'Staff Associations');
INSERT INTO "type_iii" VALUES(37,'Systems');
INSERT INTO "type_iii" VALUES(38,'Trade and Labour Unions');
INSERT INTO "type_iii" VALUES(39,'Treaties');
INSERT INTO "type_iii" VALUES(40,'UNESCO Bodies');
INSERT INTO "type_iii" VALUES(41,'United Nations Bodies');
INSERT INTO "type_iii" VALUES(42,'WHO Bodies');
