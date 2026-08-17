# Grazioso Salvare Rescue Match Recommendation System

A CS 499 Computer Science Capstone project that transforms the original **Grazioso Salvare animal rescue dashboard** from CS 340: Client/Server Development into a modular, explainable, secure, and performance-focused **Rescue Match Recommendation System**.

The enhanced application combines software engineering, algorithm design, database development, testing, and user-centered decision support to identify and rank animal candidates for specialized rescue-training profiles.

---

## Project Overview

The original Grazioso Salvare dashboard was developed in **CS 340: Client/Server Development** using Python, Dash, Pandas, MongoDB, PyMongo, Plotly, Dash Leaflet, and a custom `AnimalShelter` data-access class.

The original application allowed users to:

* Filter shelter records for specialized rescue-training profiles
* View matching animals in an interactive table
* Display breed information through data visualization
* Select an animal and view its location on an interactive map

The original rescue profiles included:

* Water Rescue
* Mountain or Wilderness Rescue
* Disaster Rescue or Individual Tracking

Although the original application was functional, much of the database access, filtering logic, interface construction, chart behavior, mapping, and callbacks were tightly coupled.

During **CS 499: Computer Science Capstone**, the application was enhanced across three categories:

1. Software Design and Engineering
2. Algorithms and Data Structures
3. Databases

The completed project is now an explainable Rescue Match Recommendation System that ranks animal candidates, communicates recommendation reasoning, uses optimized database operations, and applies stronger validation and security controls.

---

## Capstone Enhancements

### Enhancement One — Software Design and Engineering

The first enhancement focused on improving the overall architecture, maintainability, reliability, and usability of the original dashboard.

The application was reorganized into focused components responsible for:

* Configuration
* Database access
* Rescue rules
* Recommendation processing
* Service logic
* User-interface layout
* Dash callbacks
* Application startup
* Automated testing

This reduced the tight coupling present in the original notebook and made individual parts of the application easier to understand, maintain, test, and extend.

The dashboard was also expanded from a basic filtering application into an explainable decision-support system.

Enhancement One introduced:

* Modular application architecture
* Reusable service logic
* Explainable suitability scoring
* Ranked rescue candidates
* Match levels
* Match reasons
* Active rescue-profile descriptions
* Top-recommendation summaries
* Improved empty-result handling
* Named-field access instead of fragile column positions
* Coordinate validation
* Improved error handling
* Environment-based configuration
* Database-operation safeguards
* Automated testing

The Enhancement One test suite completed with:

**45 passing tests**

---

### Enhancement Two — Algorithms and Data Structures

The second enhancement focused on improving how rescue candidates are organized, evaluated, searched, and ranked.

Instead of relying only on repeated filtering operations, the recommendation engine uses multiple algorithms and data structures selected for specific tasks.

#### Dictionary-Based Indexes

Dictionary indexes organize records by frequently accessed values such as:

* Breed
* Sex
* Outcome

These indexes provide expected average-case **O(1)** access to candidate groups.

#### Set Operations

Sets are used to efficiently combine candidate groups that satisfy multiple rescue requirements.

This reduces repeated scanning when evaluating combinations of criteria.

#### Binary Search

Sorted age information supports binary-search techniques for locating qualifying age-range boundaries.

Age-boundary lookup operates in approximately:

`O(log n)`

#### Weighted Recommendation Scoring

Each candidate can receive a maximum score of **100 points**.

| Criterion     | Maximum Points |
| ------------- | -------------: |
| Breed Match   |             40 |
| Age Match     |             25 |
| Sex Match     |             20 |
| Outcome Match |             15 |
| **Total**     |        **100** |

The recommendation system also provides explanatory match reasons so the user can understand why each animal received its ranking.

#### Bounded Min-Heap

A bounded min-heap is used to maintain the strongest top-k rescue candidates.

A complete candidate sort requires approximately:

`O(m log m)`

The bounded top-k approach reduces the primary candidate-selection work to approximately:

`O(m log k)`

where:

* `m` = number of evaluated candidates
* `k` = number of top recommendations requested

The dashboard normally displays the strongest ten candidates.

#### Caching

Repeated recommendation requests can reuse recently calculated results.

Caching improves responsiveness while bounded cache sizes prevent uncontrolled memory growth.

The complete integrated application suite for Enhancement Two completed with:

**82 passing tests**

---

### Enhancement Three — Databases

The third enhancement focused on database validation, performance, security, maintainability, and integration with the completed recommendation system.

#### Preserved Original Data

The original MongoDB collection remains available as:

```text
animals
```

A separate enhanced application collection was created:

```text
animals_enhanced
```

This preserves the original CS 340 data while allowing the enhanced system to apply stronger validation and normalization.

The enhanced collection contains:

**10,000 migrated records**

---

### Data Migration and Validation

Records were evaluated, normalized, and migrated into `animals_enhanced`.

Enhanced records include fields used for traceability and secure record-specific operations, including:

```text
record_uid
source_collection
source_record_id
migrated_at
```

MongoDB validation and application-level validation are used to help protect data integrity.

Examples of validation safeguards include:

* Required-field validation
* Numeric validation
* Age validation
* Geographic-coordinate validation
* Approved-field restrictions
* Rejection of unsupported query fields

---

### Optimized Database Queries

Filtering, sorting, projections, pagination, distinct-value retrieval, and aggregation operations were moved into MongoDB where appropriate.

Purpose-built indexes support representative application query patterns.

Examples include:

```text
uidx_record_uid
idx_type_breed_age
idx_type_outcome_age
idx_animal_id
idx_outcome_date
```

Execution-plan testing confirmed that representative rescue queries can use indexed execution rather than scanning the complete collection.

For example, a rescue-data query using:

```text
animal_type
outcome_type
age_in_weeks
```

selected:

```text
IXSCAN
```

through the compound index:

```text
idx_type_outcome_age
```

A representative indexed query returned:

```text
2,539 records
2,539 keys examined
2,539 documents examined
```

instead of requiring a complete scan of the 10,000-record collection.

---

### Secure CRUD Operations

Database mutation operations were strengthened through:

* Approved field allowlists
* Record-specific identifiers
* Input validation
* Protected original collection
* Explicit deletion confirmation
* Controlled query construction
* Environment-based database configuration

Update and delete operations use generated `record_uid` values rather than unrestricted queries.

The enhanced application also rejects unsafe or invalid operations such as:

* Negative age values
* Missing required fields
* Unsupported fields
* Unsafe query operators

---

### Audit Logging

Database mutation activity is recorded in:

```text
audit_logs
```

Audit entries provide information about successful or rejected database operations.

Examples of recorded information include:

* Action
* Timestamp
* Changed fields
* Performing component
* Success status
* Error message
* Rejection reason

This provides improved accountability and traceability for database operations.

---

## Key Features

The completed Rescue Match Recommendation System includes:

* Rescue-profile selection
* Database-driven filters
* Breed filtering
* Age-range filtering
* Outcome filtering
* Interactive candidate table
* Ranked rescue recommendations
* 0–100 suitability scoring
* Match levels
* Match explanations
* Top-recommendation card
* Top-candidate visualization
* Interactive location map
* Coordinate validation
* Dictionary-based candidate indexes
* Set intersections
* Binary-search age-range processing
* Bounded min-heap top-k ranking
* Recommendation caching
* MongoDB schema validation
* Controlled data migration
* Database-side pagination
* Aggregation pipelines
* Purpose-built indexes
* Execution-plan analysis
* Secure CRUD operations
* Audit logging
* Environment-based configuration
* Automated and manual testing

---

## Technologies

### Programming and Application Development

* Python
* Dash
* Pandas
* Plotly
* Dash Leaflet

### Database Development

* MongoDB
* PyMongo
* MongoDB Shell (`mongosh`)
* MongoDB indexes
* MongoDB aggregation pipelines
* MongoDB schema validation

### Algorithms and Data Structures

* Dictionaries
* Sets
* Sorted collections
* Binary search
* Min-heaps / priority queues
* Weighted scoring
* Caching

### Development and Testing

* pytest
* Git
* GitHub
* Jupyter Notebook / JupyterLab
* Python virtual environments

---

## Testing

Automated testing was expanded throughout the capstone.

| Enhancement                         |                 Test Result |
| ----------------------------------- | --------------------------: |
| Software Design and Engineering     |            45 passing tests |
| Algorithms and Data Structures      | 82 passing integrated tests |
| Databases / Final Integrated System |            84 passing tests |

The final automated suite covers areas including:

* Rescue-profile normalization
* Recommendation scoring
* Mixed-breed matching
* Dictionary indexes
* Set intersections
* Binary-search boundaries
* Partial age scoring
* Min-heap ranking
* Tie handling
* Result limits
* Caching
* Invalid input
* Empty-result handling
* Source-data protection
* Database validation
* Secure CRUD safeguards
* Configuration validation
* Coordinate validation
* Collection protection
* Application startup
* Database integration

Manual application testing also confirmed that:

* Database-driven filters load correctly
* Rescue recommendations are produced
* Rankings begin at one
* Scores are presented in descending order
* The top recommendation matches the strongest table result
* Visualizations update correctly
* Table selection updates the map
* Combined filters continue to work
* The dashboard operates with the enhanced MongoDB collection

---

## Project Structure

The enhanced application separates responsibilities into focused modules.

A typical project structure includes:

```text
CS499-GraziosoDashboard-Enhanced/
│
├── app.py
├── animal_shelter.py
├── config.py
├── dashboard_service.py
├── recommendation_engine.py
├── rescue_rules.py
├── callbacks.py
├── ui_layout.py
│
├── tests/
│   └── automated test files
│
├── assets/
│   └── application assets
│
├── .env.example
├── requirements.txt
└── README.md
```

The exact contents may vary as the project evolves, but the enhanced architecture separates database access, business rules, recommendation processing, presentation logic, and testing rather than concentrating application responsibilities in one notebook.

---

## Security and Configuration

Sensitive credentials should **not** be committed to this repository.

Database configuration is handled through centralized configuration and environment variables.

Do not commit:

```text
.env
```

Instead, use the provided configuration example:

```text
.env.example
```

Typical configuration values may include:

```text
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DATABASE=aac
MONGO_COLLECTION=animals_enhanced
```

Use environment-specific values appropriate for your system.

The repository should also exclude:

* Passwords
* Authentication tokens
* API keys
* Virtual-environment directories
* Python cache directories
* Temporary development files
* Local machine-specific configuration

---

## Running the Application

### 1. Clone the Repository

```bash
git clone https://github.com/MoniqueHenry7/CS499-GraziosoDashboard-Enhanced.git
```

Move into the project directory:

```bash
cd CS499-GraziosoDashboard-Enhanced
```

---

### 2. Create a Virtual Environment

On macOS or Linux:

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

On Windows:

```powershell
python -m venv .venv
```

Then:

```powershell
.venv\Scripts\activate
```

---

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 4. Start MongoDB

Ensure that a local MongoDB server is running.

The application uses the:

```text
aac
```

database.

The enhanced application collection is:

```text
animals_enhanced
```

The audit collection is:

```text
audit_logs
```

You can confirm the database from `mongosh`:

```bash
mongosh
```

Then:

```javascript
use aac
```

and:

```javascript
show collections
```

A completed enhanced environment should include:

```text
animals
animals_enhanced
audit_logs
```

---

### 5. Configure Environment Variables

Create a local `.env` file based on:

```text
.env.example
```

Do not commit the `.env` file.

Update the configuration values for your local MongoDB environment as needed.

---

### 6. Run the Application

From the activated virtual environment, run the application's entry point:

```bash
python app.py
```

When the Dash development server starts, open the local address displayed in the terminal.

A typical local Dash address is:

```text
http://127.0.0.1:8050/
```

---

## Running the Tests

With the virtual environment activated, run:

```bash
pytest
```

For more detailed test output:

```bash
pytest -v
```

The final integrated project completed with:

```text
84 passing tests
```

---

## Rescue Match Recommendation Model

The recommendation system evaluates animals according to rescue-profile criteria and produces ranked results.

The scoring model uses:

```text
Breed Match   = 40 points
Age Match     = 25 points
Sex Match     = 20 points
Outcome Match = 15 points
------------------------
Maximum Score = 100 points
```

The system does more than display a numerical score.

Each recommendation can also communicate:

* Match level
* Match reasons
* Preferred characteristics satisfied
* Ranking relative to other candidates

This makes the recommendation system more transparent and understandable to the user.

---

## Database Integration

The completed system integrates all three capstone enhancement categories.

```text
Validated MongoDB Records
          ↓
Secure Data Access Layer
          ↓
Recommendation Engine
          ↓
Ranking and Scoring
          ↓
Dashboard Service
          ↓
Interactive Dash Interface
          ↓
Table + Visualization + Map
```

This integration demonstrates how software architecture, algorithms, data structures, databases, testing, security, and user-interface development work together in a complete computing solution.

---

## CS 499 ePortfolio

The complete Computer Science ePortfolio includes detailed artifact explanations, enhancement evidence, screenshots, and reflection narratives for all three capstone categories.

**ePortfolio:**

https://moniquehenry7.github.io/

The portfolio includes:

* Software Design and Engineering
* Algorithms and Data Structures
* Databases
* Enhancement evidence
* Reflection narratives
* Course-outcome alignment

---

## Academic Context

**Course:** CS 499 — Computer Science Capstone
**Original Artifact:** CS 340 — Client/Server Development
**Artifact:** Grazioso Salvare Animal Rescue Dashboard
**Enhanced Artifact:** Grazioso Salvare Rescue Match Recommendation System

The same original artifact was intentionally enhanced across all three CS 499 technical categories to demonstrate progressive improvement and integration within a single computing system.

---

## Author

**Monique Henry**
Bachelor of Science in Computer Science
Concentration in Software Engineering
Southern New Hampshire University

GitHub:

https://github.com/MoniqueHenry7

ePortfolio:

https://moniquehenry7.github.io/

---

## Repository Purpose

This repository serves as the enhanced source-code artifact for my CS 499 Computer Science Capstone.

It demonstrates my ability to evaluate an existing computing solution and improve it through:

* Modular software engineering
* Algorithmic problem-solving
* Appropriate data-structure selection
* Database design and optimization
* Secure development practices
* Automated testing
* Technical documentation
* User-centered decision support

The original CS 340 project demonstrated that I could build a functional client/server application. The completed CS 499 enhancement demonstrates that I can redesign, optimize, secure, test, document, and integrate that application as a more professional software system.
