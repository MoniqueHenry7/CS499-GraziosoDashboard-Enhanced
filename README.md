# Grazioso Salvare Rescue Match Recommendation System

## Enhancement Two: Algorithms and Data Structures

This branch contains **Enhancement Two: Algorithms and Data Structures** for my CS 499 Computer Science Capstone at Southern New Hampshire University.

The enhancement builds upon the modular software architecture completed during Enhancement One and introduces a more purposeful recommendation process for evaluating and ranking rescue-animal candidates. The original Grazioso Salvare dashboard relied primarily on repeated filtering operations. Enhancement Two expands that functionality into a **Rescue Match Recommendation System** using appropriate data structures, searching techniques, scoring logic, and top-candidate selection.

---

## Enhancement Overview

**Category:** Algorithms and Data Structures
**Original Course:** CS 340 – Client/Server Development
**Capstone Course:** CS 499 – Computer Science Capstone
**Artifact:** Grazioso Salvare Rescue Dashboard
**Enhanced System:** Grazioso Salvare Rescue Match Recommendation System

The goal of this enhancement was to improve how animal records are organized, filtered, evaluated, and ranked while demonstrating the practical application of algorithms and data structures within an existing software system.

---

## Key Enhancements

### Dictionary-Based Lookups

Python dictionaries are used to organize frequently accessed information and provide efficient key-based retrieval.

Average dictionary lookup complexity:

```text
O(1)
```

This reduces the need for repeated sequential searches when retrieving indexed information.

### Set-Based Candidate Filtering

Sets are used to represent groups of animal records that satisfy different rescue criteria.

Candidate groups can be combined through set intersection so that only animals satisfying multiple requirements remain under consideration.

Conceptually:

```text
Breed Candidates
      ∩
Age Candidates
      ∩
Sex Candidates
      ↓
Eligible Rescue Candidates
```

This provides a clearer and more efficient approach to multi-criteria filtering.

### Binary Search

Sorted age information supports binary-search techniques for identifying candidate boundaries within rescue-specific age ranges.

Binary search provides:

```text
O(log n)
```

search behavior compared with repeatedly scanning an entire sorted collection.

### Weighted Recommendation Scoring

Eligible animals are evaluated using rescue-related criteria and assigned recommendation scores.

The scoring process considers characteristics relevant to rescue profiles, allowing candidates to be compared based on how closely they satisfy the requested requirements.

The resulting score supports a more meaningful recommendation process than simple yes-or-no filtering.

### Bounded Min-Heap

A bounded min-heap is used to retain the strongest candidates without requiring the complete candidate collection to be fully sorted.

For:

```text
m = number of evaluated candidates
k = number of recommendations requested
```

top-candidate selection operates approximately in:

```text
O(m log k)
```

This is particularly useful when only a small number of the highest-ranked candidates are needed.

### Recommendation Caching

Repeated recommendation requests can reuse previously calculated results when appropriate, reducing unnecessary recomputation and supporting more responsive dashboard behavior.

---

## Rescue Match Recommendation Process

The enhanced recommendation workflow can be summarized as:

```text
Animal Records
      ↓
Indexed Data Structures
      ↓
Rescue Profile Criteria
      ↓
Candidate Set Intersection
      ↓
Age-Range Search
      ↓
Weighted Candidate Scoring
      ↓
Bounded Min-Heap
      ↓
Top Rescue Recommendations
      ↓
Dashboard Presentation
```

This process separates basic filtering from candidate evaluation and ranking, allowing the application to provide decision-support information rather than simply displaying matching database records.

---

## Software Integration

Enhancement Two builds directly on the modular architecture created during Enhancement One.

Important components include:

* `recommendation.py` – recommendation and ranking logic
* `rescue_rules.py` – rescue profile definitions and rules
* `dashboard_service.py` – integration between dashboard behavior and recommendation processing
* `callbacks.py` – interactive dashboard updates
* `ui.py` – dashboard presentation components
* `animal_shelter.py` – animal-record access
* `tests/` – automated tests for recommendation, filtering, service, and security behavior

The recommendation engine is integrated with the dashboard so that rescue-profile selections and filtering criteria can produce ranked candidate results for the user.

---

## Testing

Automated and manual testing were used to verify the algorithm enhancement.

Testing covers areas including:

* rescue-profile evaluation
* recommendation scoring
* candidate filtering
* dictionary and set behavior
* age-range processing
* top-candidate selection
* dashboard-service integration
* regression behavior
* security safeguards
* CSV-based smoke testing when the source dataset is available

Supporting test evidence for Enhancement Two is available in:

```text
docs/enhancement-two/
```

The automated test suite can be executed with:

```bash
python -m pytest -q
```

---

## Technologies

* Python
* Dash
* Pandas
* MongoDB
* PyMongo
* Python dictionaries
* Python sets
* Binary search
* Heap-based selection
* Pytest
* Jupyter Notebook

---

## Running the Project

### 1. Clone the Repository

```bash
git clone https://github.com/MoniqueHenry7/CS499-GraziosoDashboard-Enhanced.git
cd CS499-GraziosoDashboard-Enhanced
```

### 2. Switch to the Enhancement Two Branch

```bash
git switch enhancement-two-algorithms
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

### 5. Configure the Application

Create a local `.env` file using the repository's `.env.example` file as a reference.

Sensitive credentials and local environment configuration should not be committed to source control.

### 6. Run the Tests

```bash
python -m pytest -q
```

### 7. Run the Dashboard

```bash
python app.py
```

The application can then be accessed through the local address displayed by Dash.

---

## Security Considerations

Although this enhancement focuses primarily on algorithms and data structures, the application continues to follow security-conscious development practices established during the software-engineering enhancement.

These practices include:

* separating environment-specific configuration from application logic
* avoiding committed credentials
* validating application inputs
* maintaining clear module responsibilities
* preserving automated security and regression tests

Additional database-specific security controls are introduced in **Enhancement Three**.

---

## Enhancement Progression

This branch represents the second stage of the CS 499 artifact enhancement process:

```text
Original CS 340 Dashboard
        ↓
Enhancement One
Software Design and Engineering
        ↓
Enhancement Two
Algorithms and Data Structures
        ↓
Enhancement Three
Databases
        ↓
Final Rescue Match Recommendation System
```

Enhancement Two demonstrates the transition from a dashboard based primarily on filtering to a system capable of evaluating, scoring, and ranking candidates using purposeful algorithms and data structures.

---

## Related Resources

**CS 499 ePortfolio:**
https://moniquehenry7.github.io/

**Enhancement Two Portfolio Page:**
https://moniquehenry7.github.io/algorithms.html

**GitHub Repository:**
https://github.com/MoniqueHenry7/CS499-GraziosoDashboard-Enhanced

**Branch:**
`enhancement-two-algorithms`

**Completion Tag:**
`enhancement-two-complete`

---

## Author

**Monique Henry**
Bachelor of Science in Computer Science
Software Engineering Concentration
Southern New Hampshire University
CS 499 Computer Science Capstone
