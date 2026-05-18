# BookMem Decimal Classification (BMDC)

BMDC is BookMem's internal decimal subject map for routing a Markdown book corpus.

Its class numbers are intended to be interoperable with the familiar decimal library classification numbering pattern where useful. For example, `510` is used for mathematics works and `332` is used for finance/investing works. The labels, aliases and notes in this repository are BookMem's own working descriptions and must not be copied from proprietary classification manuals.

BMDC is BookMem's internal routing scheme. It is not named as, affiliated with, endorsed by, or a substitute for any third-party classification product.

## How to classify a book

Use one `primary_class` and optional `secondary_class` entries.

```yaml
classification:
  scheme: bmdc
  primary_class: "332"
  primary_label: Finance, investing and financial markets
  secondary_class:
    - "153"
    - "158"
  routing_aliases:
    - finance
    - investing
  topics:
    - risk
    - compounding
```

## Classification rules

- Prefer the interoperable decimal class number where the subject clearly matches.
- Put the book in the class that best describes its main purpose.
- Use secondary classes for genuine cross-domain usefulness.
- Use routing aliases for common agent scopes such as `finance`, `productivity`, `technology` and `health`.
- Use topic tags for specific ideas, models, names and themes.
- Use `999` for unclassified or holding-area books.

## Main classes

| Code | Label | Aliases |
|---:|---|---|
| `000` | General knowledge, information and reference | general, reference, knowledge |
| `010` | Bibliography and catalogues | bibliography, catalogues, reading_lists |
| `020` | Libraries, archives and information work | libraries, archives, information_management |
| `030` | Encyclopaedias and general reference works | encyclopaedias, reference_works |
| `040` | General collected works | collected_works, anthologies |
| `050` | General serials and periodicals | magazines, journals, periodicals |
| `060` | General organisations and institutions | organisations, institutions, associations |
| `070` | News, journalism and publishing | journalism, publishing, media |
| `080` | General miscellany | miscellany, general_collections |
| `090` | Manuscripts, rare books and book history | manuscripts, rare_books, book_history |
| `100` | Philosophy and psychology | philosophy, psychology |
| `110` | Metaphysics | metaphysics, reality, ontology |
| `120` | Epistemology, causation and human existence | epistemology, knowledge, causation |
| `130` | Paranormal and esoteric subjects | paranormal, esoteric |
| `140` | Specific philosophical schools | philosophical_schools |
| `150` | Psychology | psychology, behaviour, cognition |
| `153` | Mental processes, intelligence and decision-making | thinking, attention, decision_making, focus, cognition |
| `155` | Developmental, differential and individual psychology | personality, development, neurodiversity, child_development |
| `158` | Applied psychology and self-improvement | personal_development, self_improvement, productivity, habits, mindset |
| `160` | Logic | logic, reasoning |
| `170` | Ethics | ethics, morality, values |
| `180` | Ancient and medieval philosophy | ancient_philosophy, medieval_philosophy |
| `190` | Modern western philosophy | modern_philosophy, western_philosophy |
| `200` | Religion | religion, faith |
| `210` | Philosophy and theory of religion | religious_philosophy, theology |
| `220` | Bible and biblical studies | bible, biblical_studies |
| `230` | Christianity and Christian theology | christianity, christian_theology |
| `240` | Christian practice and devotional life | devotional, christian_living |
| `250` | Christian ministry and pastoral practice | ministry, pastoral |
| `260` | Christian institutions and social theology | church, christian_institutions |
| `270` | History of Christianity | church_history, christian_history |
| `280` | Christian denominations | denominations |
| `290` | Other religions | world_religions, comparative_religion |
| `300` | Social sciences | society, social_systems, policy |
| `310` | Statistics and data about society | statistics, social_data |
| `320` | Politics and government | politics, government, public_policy |
| `330` | Economics | economics, money |
| `332` | Finance, investing and financial markets | finance, investing, markets, banking, personal_finance, wealth |
| `338` | Production, enterprise and industry | business, entrepreneurship, industry, startups |
| `340` | Law | law, legal, compliance |
| `350` | Public administration and public services | public_administration, public_services |
| `360` | Social problems, services and welfare | welfare, social_services, safeguarding |
| `370` | Education | education, teaching, learning, schools |
| `371` | Schools, teaching practice and educational support | school, teaching_practice, send, ehcp, learning_support |
| `380` | Commerce, communications and transport | commerce, communications, transport |
| `390` | Customs, etiquette and folklore | customs, etiquette, folklore |
| `400` | Language | language, linguistics |
| `410` | Linguistics | linguistics |
| `420` | English language | english_language, english |
| `430` | Germanic languages | germanic_languages |
| `440` | Romance languages: French | french, romance_languages |
| `450` | Italian and related Romance languages | italian |
| `460` | Spanish, Portuguese and related languages | spanish, portuguese |
| `470` | Latin and Italic languages | latin |
| `480` | Classical and modern Greek | greek |
| `490` | Other languages | other_languages |
| `500` | Science | science, natural_science |
| `510` | Mathematics | mathematics, maths |
| `520` | Astronomy | astronomy, space |
| `530` | Physics | physics |
| `540` | Chemistry | chemistry |
| `550` | Earth sciences | earth_science, geology |
| `560` | Fossils and prehistoric life | fossils, palaeontology |
| `570` | Biology | biology, life_science |
| `580` | Plants | plants, botany |
| `590` | Animals | animals, zoology |
| `600` | Applied science and technology | technology, applied_science |
| `610` | Medicine and health | medicine, health |
| `613` | Personal health, wellbeing and safety | sleep, nutrition, exercise, wellbeing, supplements, personal_health |
| `620` | Engineering | engineering |
| `630` | Agriculture and food production | agriculture, food_production |
| `640` | Home, family and personal living | home, family_life, domestic_life |
| `650` | Management, work and business skills | work, productivity_at_work, business_skills, office_work |
| `658` | General management, leadership and operations | management, leadership, operations, strategy |
| `660` | Chemical engineering and industrial chemistry | chemical_engineering |
| `670` | Manufacturing | manufacturing |
| `680` | Manufacture for specific uses | special_manufacturing |
| `690` | Buildings and construction | construction, buildings |
| `700` | Arts, recreation and creativity | arts, creativity, recreation |
| `710` | Landscape and civic art | landscape, civic_art |
| `720` | Architecture | architecture |
| `730` | Sculpture and related arts | sculpture |
| `740` | Drawing, design and decorative arts | design, drawing, decorative_arts |
| `750` | Painting | painting |
| `760` | Graphic arts and printmaking | graphic_arts, printmaking |
| `770` | Photography and imaging | photography, imaging |
| `780` | Music | music, songwriting, music_production |
| `790` | Sport, games and entertainment | sport, games, entertainment |
| `800` | Literature, rhetoric and writing | literature, writing |
| `808` | Writing craft, rhetoric and storytelling | writing_craft, storytelling, composition, rhetoric |
| `810` | American literature | american_literature |
| `820` | English literature | english_literature |
| `830` | German literature | german_literature |
| `840` | French literature | french_literature |
| `850` | Italian literature | italian_literature |
| `860` | Spanish and Portuguese literature | spanish_literature, portuguese_literature |
| `870` | Latin literature | latin_literature |
| `880` | Greek literature | greek_literature |
| `890` | Other literatures | other_literature |
| `900` | History, geography and biography | history, geography, biography |
| `910` | Geography and travel | geography, travel |
| `920` | Biography and memoir | biography, memoir |
| `930` | Ancient history | ancient_history |
| `940` | European history | european_history |
| `950` | Asian history | asian_history |
| `960` | African history | african_history |
| `970` | North American history | north_american_history |
| `980` | South American history | south_american_history |
| `990` | History of other areas | world_history, other_regions |
| `999` | Unclassified or holding area | unclassified, holding, inbox |

## Routing aliases

Routing aliases are convenience scopes. They let an agent search a practical domain without knowing every class code.

| Alias | Primary classes | Secondary classes |
|---|---|---|
| `business` | 338, 650, 658 | 330, 332 |
| `creativity` | 700, 780, 800, 808 |  |
| `education` | 370, 371 | 155 |
| `finance` | 330, 332 | 338, 658 |
| `health` | 610, 613 | 158 |
| `investing` | 332 | 330 |
| `personal_development` | 158 | 153, 155, 613, 650 |
| `productivity` | 158, 650 | 153, 658 |
| `psychology` | 150, 153, 155, 158 |  |
| `technology` | 000, 003, 004, 005, 006 |  |

## Suggested folder names

Folder names should begin with the three-digit class code so BookMem can infer classification when frontmatter is missing.

```text
data/books/158-applied-psychology-and-self-improvement/
data/books/332-finance-investing-and-financial-markets/
data/books/338-production-enterprise-and-industry/
data/books/370-education/
data/books/610-medicine-and-health/
data/books/613-personal-health-wellbeing-and-safety/
data/books/650-management-work-and-business-skills/
data/books/658-general-management-leadership-and-operations/
data/books/808-writing-craft-rhetoric-and-storytelling/
data/books/999-unclassified-or-holding-area/
```
