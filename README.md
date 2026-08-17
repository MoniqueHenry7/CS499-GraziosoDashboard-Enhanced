# Grazioso Salvare Rescue Match Recommendation System

## Enhancement Three: Databases

This branch contains **Enhancement Three: Databases** for my CS 499 Computer Science Capstone at Southern New Hampshire University.

Enhancement Three builds upon the modular software architecture completed during Enhancement One and the Rescue Match Recommendation System developed during Enhancement Two. The focus of this enhancement is strengthening the application's database layer through validation, controlled migration, database-side querying, indexing, secure CRUD operations, audit logging, and integration with the completed recommendation dashboard.

---

## Enhancement Overview

**Category:** Databases
**Original Course:** CS 340 – Client/Server Development
**Capstone Course:** CS 499 – Computer Science Capstone
**Artifact:** Grazioso Salvare Rescue Dashboard
**Enhanced System:** Grazioso Salvare Rescue Match Recommendation System

The original CS 340 application successfully connected a Python Dash dashboard to MongoDB and supported basic data retrieval and CRUD functionality. Enhancement Three expands that implementation into a more structured database service designed around:

* data integrity
* controlled migration
* query efficiency
* indexing
* database-side processing
* secure record-specific operations
* auditability
* maintainability
* integration with the Rescue Match Recommendation System

---

## Database Architecture

The database enhancement preserves the original CS 340 data while introducing a validated collection for the enhanced application.

```text
Original CS 340 Data
       |
       v
animals
       |
       v
Validation and Normalization
       |
       v
Controlled Migration
       |
       v
animals_enhanced
       |
       v
Database Service Layer
       |
       v
Rescue Match Recommendation System
```

The original `animals` collection remains preserved as the source artifact, while the enhanced application uses the validated `animals_enhanced` collection.

---

## Key Enhancements

### Schema Validation

MongoDB validation rules are used to strengthen data integrity within the enhanced collection.

Validation helps ensure that application records contain expected fields, data types, identifiers, and geographic information before being used by the application.

The enhanced structure reduces reliance on unvalidated source records and provides a more predictable data model for the dashboard and recommendation engine.

---

### Controlled Data Migration

The original CS 340 records are evaluated and normalized before being migrated into the enhanced collection.

The migration process supports:

* preservation of the original collection
* normalization of application data
* generated record identifiers
* validation before insertion
* migration reporting
* separation between original and enhanced data

This approach allows the original academic artifact to remain intact while supporting a more structured database design for the completed system.

---

### Database-Side Query Processing

The enhanced database layer moves more processing into MongoDB rather than unnecessarily loading the entire dataset into application memory.

Supported database operations include:

* filtering
* field projection
* sorting
* pagination
* distinct-value retrieval
* aggregation
* record-specific queries

This design reduces unnecessary application-side processing and creates clearer boundaries between data access and application logic.

---

### Query Optimization and Indexing

Purpose-built indexes were created around representative application query patterns.

Rather than assuming that an index automatically improves performance, MongoDB execution plans were evaluated before and after optimization.

Enhancement Three includes evidence comparing query behavior for representative filtering patterns and verifying that MongoDB selects appropriate indexed execution plans.

Database optimization work is supported by:

* index creation
* compound indexes
* execution-plan analysis
* keys-examined comparisons
* documents-examined comparisons
* before-and-after query evidence

The related implementation is contained in:

```text
database_indexes.py
```

and supporting query-plan evidence is included in the project documentation.

---

### Secure CRUD Operations

Create, update, and delete functionality was strengthened to reduce the risk of unrestricted or unintended database changes.

Security controls include:

* record-specific identifiers
* approved query fields
* approved mutation fields
* input validation
* collection safeguards
* explicit confirmation for destructive operations
* protection of the original `animals` collection

Updates and deletions target individual enhanced records rather than allowing unrestricted bulk modifications.

---

### Audit Logging

Database mutations are recorded so that important operations can be traced and reviewed.

Audit records support both successful and rejected mutation attempts and provide evidence of:

* operation type
* affected record
* requested changes
* operation result
* validation failures
* rejected actions

This enhancement improves accountability and demonstrates a security-focused approach to database development.

---

## Database Components

Important Enhancement Three components include:

### `animal_shelter.py`

Provides the primary MongoDB data-access functionality and enhanced database operations.

Responsibilities include database reads, validated writes, secure record-specific CRUD operations, query handling, and audit-related behavior.

### `database_setup.py`

Supports initialization and configuration of the enhanced database environment.

### `database_migration.py`

Provides controlled migration from the preserved original data into the enhanced application collection.

### `database_indexes.py`

Defines and manages indexes used to support representative application query patterns.

### `dashboard_service.py`

Integrates the enhanced database read layer with filtering, recommendation processing, and dashboard behavior.

### `EnhancementThree-DatabaseDevelopment.ipynb`

Documents and demonstrates database-development activities completed during Enhancement Three.

### `tests/`

Contains automated tests covering database behavior, dashboard integration, validation, security safeguards, recommendation functionality, and regression behavior.

---

## Enhanced Database Flow

The completed system separates database responsibilities from recommendation and presentation logic.

```text
MongoDB
   |
   v
Validated Enhanced Collection
   |
   v
Data-Access Layer
   |
   v
Dashboard Service
   |
   +-------------------+
   |                   |
   v                   v
Filtering       Recommendation Engine
   |                   |
   +---------+---------+
             |
             v
       Dash Interface
             |
             v
 Table + Chart + Map + Ranked Recommendations
```

This separation improves maintainability while allowing database operations to support the algorithmic and software-engineering enhancements completed earlier in the capstone.

---

## Query Performance Evaluation

Enhancement Three includes documented query-plan comparisons demonstrating the effect of database indexing.

Representative query patterns were evaluated before and after optimization using MongoDB execution statistics.

Supporting evidence includes files for:

* breed and age queries
* outcome and age queries
* before-index execution plans
* after-index execution plans
* index comparisons
* index summaries

The purpose of this evaluation was not simply to create indexes, but to verify that MongoDB actually selected and used them for representative application queries.

---

## Security Considerations

Security is integrated directly into the enhanced database architecture.

Key safeguards include:

* environment-based configuration
* separation of database settings from primary application logic
* restricted query and mutation fields
* record-specific operations
* protected original data
* explicit delete confirmation
* validation before mutation
* audit logging
* automated security testing

Sensitive credentials and local environment values should never be committed to the repository.

---

## Testing

Enhancement Three was validated through automated and manual testing.

Testing covers:

* schema and record validation
* database migration
* database reads
* filtering
* sorting
* pagination
* aggregation
* secure CRUD operations
* collection protection
* audit logging
* dashboard-service integration
* recommendation integration
* security safeguards
* regression behavior
* live dashboard functionality

The completed integrated test suite passes:

```text
84 passed
```

Run the automated tests with:

```bash
python -m pytest -q
```

The final branch was validated with all 84 tests passing.

Supporting Enhancement Three evidence is available in the repository documentation and includes database setup results, migration results, CRUD/security results, query-plan comparisons, dashboard validation, and final test results.

---

## Technologies

* Python
* MongoDB
* PyMongo
* Dash
* Pandas
* JSON Schema Validation
* MongoDB Aggregation
* Database Indexing
* Query Execution Plans
* Secure CRUD
* Audit Logging
* Pytest
* Jupyter Notebook

---

## Running the Project

### 1. Clone the Repository

```bash
git clone https://github.com/MoniqueHenry7/CS499-GraziosoDashboard-Enhanced.git
cd CS499-GraziosoDashboard-Enhanced
```

### 2. Switch to the Enhancement Three Branch

```bash
git switch enhancement-three-databases
```

### 3. Create a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure MongoDB

Ensure MongoDB is available and configure the database connection values required by the application.

Keep local credentials and environment-specific configuration outside source control.

### 6. Prepare the Enhanced Database

Enhancement Three provides dedicated database utilities for setup, migration, and indexing:

```text
database_setup.py
database_migration.py
database_indexes.py
```

These components support creation of the enhanced database structure and preparation of the application data.

### 7. Run the Tests

```bash
python -m pytest -q
```

Expected completed-branch result:

```text
84 passed
```

### 8. Run the Dashboard

```bash
python app.py
```

Open the local address displayed by Dash to access the Rescue Match Recommendation System.

---

## Enhancement Progression

Enhancement Three represents the final technical enhancement of the CS 499 capstone artifact.

```text
Original CS 340 Dashboard
        |
        v
Enhancement One
Software Design and Engineering
        |
        v
Enhancement Two
Algorithms and Data Structures
        |
        v
Enhancement Three
Databases
        |
        v
Final Integrated
Rescue Match Recommendation System
```

### Enhancement One

Improved the original dashboard through modular architecture, clearer separation of concerns, configuration management, improved error handling, and automated testing.

### Enhancement Two

Introduced dictionaries, sets, binary search, weighted recommendation scoring, bounded heap-based candidate selection, and integration of the Rescue Match Recommendation System.

### Enhancement Three

Completed the system by strengthening data integrity, database architecture, query efficiency, indexing, secure CRUD operations, audit logging, and full database integration.

---

## Git History

This branch preserves the incremental development of Enhancement Three.

Major Enhancement Three commits include:

```text
3281916  Add database validation migration and query optimization
3bc94ac  Add database filtering pagination and aggregation
8717515  Add secure CRUD operations and database audit logging
f5874c7  Integrate enhanced database queries with dashboard service
4fec00c  Document live enhanced database dashboard validation
93c0580  Finalize Enhancement Three database documentation and evidence
```

**Branch:**
`enhancement-three-databases`

**Completion Tag:**
`enhancement-three-complete`

The completed branch was subsequently integrated into `main` through Pull Request #2.

---

## Related Resources

**CS 499 ePortfolio:**
https://moniquehenry7.github.io/

**Enhancement Three Portfolio Page:**
https://moniquehenry7.github.io/databases.html

**GitHub Repository:**
https://github.com/MoniqueHenry7/CS499-GraziosoDashboard-Enhanced

**Branch:**
`enhancement-three-databases`

**Completion Tag:**
`enhancement-three-complete`

---

## Author

**Monique Henry**
Bachelor of Science in Computer Science
Software Engineering Concentration
Southern New Hampshire University
CS 499 Computer Science Capstone
