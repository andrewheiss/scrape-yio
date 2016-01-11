library(dplyr)
library(rvest)
library(readr)

feeling.lucky <- function(name.to.find) {
  s <- html_session("https://google.com/")
  Sys.sleep(rnorm(1, 4, 1))
  name.escaped <- URLencode(name.to.find)
  url <- paste0("https://google.com/search?btnI=&q=", name.escaped)
  
  lucky.url <- tryCatch({
    lucky <- s %>% jump_to(url) %>% .$url
    return(lucky)
  }, error=function(cond) {
    return(NA)
  })
  
  return(lucky.url)
}

feeling.lucky("feeling lucky")

# Load the full database
yio.db <- src_sqlite(path="data/yio.db")

# Convert all the tables to R dataframes with collect() just so I don't have 
# to deal with raw SQL statements
orgs <- tbl(yio.db, "organizations_final") %>% collect()
subjects <- tbl(yio.db, "subjects") %>% collect()
orgs_subjects <- tbl(yio.db, "orgs_subjects") %>% collect()
contacts <- tbl(yio.db, "contacts") %>% collect()
orgs_contacts <- tbl(yio.db, "orgs_contacts") %>% collect()

i.to.ignore <- c("J", "H", "R", "S", "T", "U")
ii.to.ignore <- c("c", "d", "e", "g", "s")
iii.to.ignore <- c("Alumni and Veterans", "European Union Bodies", "FAO Bodies", 
                   "ILO Bodies", "NATO Bodies", "Parliaments", "Political Parties", 
                   "Treaties", "United Nations Bodies", "WHO Bodies", 
                   "Corporations, Companies", "Intergovernmental Communities")

orgs.clean <- orgs %>%
  filter(!(type_i_dir %in% i.to.ignore),
         !grepl(paste0(ii.to.ignore, collapse="|"), type_ii_dir),
         !(type_iii_dir %in% iii.to.ignore)) %>%
  select(id_org:country_hq, subject_dir, aims, activities, 
         type_i_dir:type_iii_dir, url_id, last_news)

foe <- orgs.clean %>% 
  filter(subject_dir != "Education")

education <- orgs.clean %>%
  filter(subject_dir == "Education")

write_csv(foe, "~/Desktop/to_filter_foe_WILL_BE_OVERWRITTEN.csv")
write_csv(education, "~/Desktop/to_filter_education_WILL_BE_OVERWRITTEN.csv")



foe.urls <- foe %>% select(id_org, org_name, org_url) %>% filter(is.na(org_url))
write_csv(foe.urls, "~/Desktop/foe_to_find.csv")

ed.urls <- education %>% select(id_org, org_name, org_url) %>% filter(is.na(org_url))
write_csv(ed.urls, "~/Desktop/ed_to_find.csv")

# foe.lucky <- foe.urls %>%
#   mutate(lucky_url = sapply(org_name, FUN=feeling.lucky))
# write_csv(foe.lucky, "~/Desktop/foe_lucky.csv")

# ed.lucky <- ed.urls %>%
#   mutate(lucky_url = sapply(org_name, FUN=feeling.lucky))
# write_csv(ed.lucky, "~/Desktop/ed_lucky.csv")

sites.to.ignore <- c("wikipedia", "google", "yahoo", "facebook", "cnn",
                     "twitter", "acronym", "sciencedirect")

foe.lucky <- read_csv("~/Desktop/foe_lucky.csv") %>%
  mutate(ignore = grepl(paste0(sites.to.ignore, collapse="|"), lucky_url),
         lucky.final = ifelse(ignore, NA, lucky_url))

ed.lucky <- read_csv("~/Desktop/ed_lucky.csv") %>%
  mutate(ignore = grepl(paste0(sites.to.ignore, collapse="|"), lucky_url),
         lucky.final = ifelse(ignore, NA, lucky_url))

foe.fixed <- foe %>% 
  left_join(foe.lucky %>% select(c(id_org, lucky.final)), by="id_org") %>%
  mutate(org_url = ifelse(is.na(org_url), lucky.final, org_url)) %>%
  filter(subject_dir != "Media")

ed.fixed <- education %>% 
  left_join(ed.lucky %>% select(c(id_org, lucky.final)), by="id_org") %>%
  mutate(org_url = ifelse(is.na(org_url), lucky.final, org_url))

write_csv(foe.fixed, "~/Desktop/foe_final_ybio.csv")
