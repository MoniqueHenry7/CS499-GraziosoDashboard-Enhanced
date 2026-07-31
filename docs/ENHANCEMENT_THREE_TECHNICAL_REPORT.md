# Enhancement Three: Databases

**Student:** Monique Henry  
**Course:** CS 499 Computer Science Capstone  
**Artifact:** Grazioso Salvare Rescue Match Recommendation Dashboard  
**Branch:** `enhancement-three-databases`  
**Database:** `aac`  
**Primary collection:** `animals_enhanced`

## Enhancement Overview

Enhancement Three modernizes the MongoDB data layer used by the
Grazioso Salvare dashboard. The original artifact connected directly to
the `animals` collection and primarily performed unrestricted reads.

The enhanced implementation introduces a validated, indexed, secure,
and maintainable database service that supports the existing dashboard
and the Enhancement Two recommendation engine.

## Database Architecture

The application uses the following primary collections:

- `animals`: protected source collection containing the original data
- `animals_enhanced`: validated and normalized application collection
- `audit_logs`: audit history for secure create, update, and delete actions

The application now uses `animals_enhanced` as its default operational
collection while preserving the original `animals` collection.

## Schema Validation and Migration

The migration process creates normalized records for
`animals_enhanced`.

Major migration improvements include:

- Generated `record_uid` values for uniquely identifying individual
  database records
- Standardized animal type, breed, sex, and outcome values
- Numeric `age_in_weeks` values
- Normalized latitude and longitude values
- Preservation of the original animal identifier
- Validation of required fields and approved data types
- Logging and reporting of rejected or corrected records

The source collection remains unchanged so that the original artifact
and data can still be reviewed.

## Indexing and Query Optimization

MongoDB indexes were created for frequent dashboard searches,
including fields used for:

- Animal type
- Breed
- Age
- Outcome type
- Sex upon outcome
- Record UID
- Location data

Compound indexes support common dashboard filter combinations.

Query execution plans were evaluated before and after index creation.
The original test queries performed collection scans. After the indexes
were created, MongoDB used indexed query plans and examined substantially
fewer documents.

## Controlled Query Construction

The database service builds queries only from approved application
fields. User-facing filter values are validated before they are added to
a MongoDB query.

Approved filters include:

- Animal type
- Breed
- Outcome type
- Sex upon outcome
- Minimum and maximum age

The service rejects unsupported fields, invalid page values, invalid
sort fields, negative ages, and malformed age ranges.

## Database-Side Filtering

The dashboard no longer retrieves the complete collection and then
performs all filtering in Pandas.

The enhanced service performs the following work in MongoDB:

- Animal-type filtering
- Breed filtering
- Outcome filtering
- Age-range filtering
- Field projection
- Sorting
- Pagination
- Distinct-value retrieval
- Minimum and maximum age aggregation

This reduces unnecessary application-side processing and ensures the
database indexes participate in dashboard searches.

## Pagination

`find_animals_page()` performs validated database pagination.

Each result includes:

- Current page
- Page size
- Total matching records
- Total pages
- Projected records for the requested page

Page sizes are restricted to approved limits to prevent unrestricted
database reads.

The dashboard service retrieves all pages of the already-filtered
candidate set before applying the Enhancement Two recommendation
algorithm. This preserves correct top-k ranking while avoiding an
unfiltered full-collection read.

## Aggregation Pipelines

MongoDB aggregation pipelines are used to calculate database summaries,
including:

- Minimum and maximum animal age
- Outcome-type totals
- Dashboard reporting values

These operations are performed by MongoDB rather than requiring the
application to load all records into a DataFrame first.

## Secure CRUD Operations

Secure record-specific operations were added for:

- Creating one animal record
- Reading one record by `record_uid`
- Updating one record by `record_uid`
- Deleting one record by `record_uid`

Safeguards include:

- Approved-field allowlists
- Required-field validation
- Numeric and geographic boundary validation
- Record-specific update and delete criteria
- Explicit confirmation for deletion
- Protection of the original `animals` collection
- Duplicate-key handling
- Cache-clearing support after database changes

Broad `update_many` and `delete_many` behavior is not used by the secure
mutation interface.

## Audit Logging

Create, update, and delete attempts are recorded in `audit_logs`.

Audit records contain information such as:

- Action type
- Record UID
- Success or failure
- Performing user or process
- Changed fields
- Error information
- Timestamp

Both successful operations and rejected destructive actions are
recorded.

## Secure Configuration

MongoDB connection values are loaded through `AppConfig` and environment
variables.

The application does not require credentials to be embedded directly in
the dashboard or database source files. The safe local defaults are:

- Host: `127.0.0.1`
- Port: `27017`
- Database: `aac`
- Collection: `animals_enhanced`

Environment variables may override these defaults for another
deployment environment.

## Dashboard Integration

`DashboardService` now uses the enhanced database read interface for:

- Paginated record retrieval
- Dropdown breed values
- Dropdown outcome values
- Age boundaries
- Database-side dashboard filters

The existing Dash callbacks continue to call
`DashboardService.filter_and_rank()`.

The Enhancement Two recommendation engine remains responsible for:

- Dictionary-based indexes
- Candidate-set intersections
- Binary-search age boundaries
- Bounded top-k selection
- Recommendation caching
- Match scores and explanations

The database layer narrows the approved candidate set before the
recommendation engine ranks it.

## Testing and Validation

Testing completed for:

- Schema creation
- Data migration
- Migration counts
- Index creation
- Query execution plans
- Query validation
- Pagination
- Distinct-value retrieval
- Aggregations
- Secure CRUD validation
- Source-collection protection
- Audit logging
- Dashboard-service integration
- Configuration safeguards
- Recommendation-engine compatibility
- Live dashboard operation
- Breed, age, outcome, and combined filters
- Table, chart, and map behavior

The complete automated test suite passed after the database interface
was integrated with the existing service tests.

## Course Outcomes

### Outcome One

The enhanced dashboard creates a professional decision-support
environment by presenting validated database results through an
interactive table, chart, map, and recommendation interface.

### Outcome Two

Technical documentation, audit evidence, query-performance results, and
user-facing recommendation explanations communicate the database design
to technical and nontechnical audiences.

### Outcome Three

The database enhancement works with the Enhancement Two dictionaries,
sets, binary search, heap-based top-k ranking, and caching structures.
The database indexes and query plans also demonstrate evaluation of
performance trade-offs.

### Outcome Four

The enhancement applies database engineering techniques to a practical
rescue-candidate selection system, including normalized data,
database-side filtering, secure operations, and reporting.

### Outcome Five

Security-oriented improvements include environment-based configuration,
approved query fields, schema validation, record-specific mutations,
source-collection protection, destructive-action confirmation, and
audit logging.

## Result

Enhancement Three transforms the original MongoDB implementation into a
validated, indexed, auditable, and maintainable data layer. The enhanced
database integrates successfully with the modular dashboard and the
existing rescue recommendation engine while preserving the original
source collection.
