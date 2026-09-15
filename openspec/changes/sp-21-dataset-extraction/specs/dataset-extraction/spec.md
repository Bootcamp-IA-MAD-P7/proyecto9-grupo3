## Purpose

Provide a safe and reproducible way to load and validate the local YouToxic dataset before transformation, analysis, or model training.

## ADDED Requirements

### Requirement: Configurable dataset source

The system SHALL load the dataset from a local path supplied through configuration and MUST NOT require the CSV to be committed to the repository.

#### Scenario: Valid local path

- **WHEN** a valid dataset path is provided
- **THEN** the system loads every row while preserving its original order

#### Scenario: File does not exist

- **WHEN** the configured path does not reference an existing file
- **THEN** the system stops with an actionable file-not-found error

### Requirement: Required schema validation

The system SHALL verify that the dataset contains `CommentId`, `VideoId`, `Text`, and `IsToxic`.

#### Scenario: Required column is missing

- **WHEN** the CSV does not contain every required column
- **THEN** the system stops and identifies the missing columns

### Requirement: Essential value validation

The system SHALL reject empty datasets, missing comment text, and `IsToxic` values other than `0` or `1`.

#### Scenario: Dataset is empty

- **WHEN** the CSV contains no data rows
- **THEN** the system stops with an actionable validation error

#### Scenario: Comment text is missing

- **WHEN** at least one row has missing or blank `Text`
- **THEN** the system stops and reports the invalid row count without exposing comment text

#### Scenario: Target value is invalid

- **WHEN** at least one `IsToxic` value is not `0` or `1`
- **THEN** the system stops and reports the invalid row count

### Requirement: Sensitive text protection

The extraction process MUST NOT write real comment text to logs, errors, tests, or committed artifacts.

#### Scenario: Validation fails

- **WHEN** the dataset fails validation
- **THEN** diagnostic output contains metadata and counts but no comment content