# Glossary

## Clinical Terms

**EMR (Electronic Medical Record)**
Digital version of a patient's paper chart. Contains medical history, diagnoses, medications, treatment plans, etc.

**FHIR (Fast Healthcare Interoperability Resources)**
HL7 standard for exchanging healthcare information electronically. RESTful API specification.

**Encounter**
A patient visit or interaction with healthcare system. Has admission/discharge dates.

**PHI (Protected Health Information)**
Any health information that can identify a patient. Protected under HIPAA.

**PII (Personally Identifiable Information)**
Any data that could identify a specific individual (SSN, name, DOB, etc.).

## Engineering Terms

**Property-Based Testing (PBT)**
Testing approach where you define properties (invariants) that must hold for all inputs, then generate random test cases to verify.

**Invariant**
A condition that must always be true. Example: "All dates in AI output must be within patient's admission window."

**Result Pattern**
Type-safe error handling where functions return `Result[T, E]` instead of throwing exceptions.

**Wrapper Pattern**
Isolating external API complexity by creating a clean interface that returns domain models.

**Zero-Trust**
Security principle: never trust external input (AI output, EMR data) without verification.

## FHIR Resources

**Patient**
Demographics and administrative information about a person receiving care.

**Encounter**
An interaction between a patient and healthcare provider(s) for the purpose of providing healthcare services.

**Observation**
Measurements or simple assertions made about a patient (vitals, lab results, etc.).
