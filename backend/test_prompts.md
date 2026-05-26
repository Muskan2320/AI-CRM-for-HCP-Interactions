# AI CRM HCP - Regression Test Prompts

---

# 1. Search HCP Tests

## Search by name
Show doctor Himani from Apollo Hospital

## Search by specialization
Find cardiologists from Fortis Hospital

## Search by ID
Search HCP id 3

---

# 2. Log Interaction Tests

## Basic interaction
Log interaction with Dr Himani from Apollo Hospital regarding diabetes awareness

## Interaction with followup
Dr Shankar from AIIMS requested followup after 3 days for cancer medicine discussion

## Interaction with specialization
Log interaction with cardiologist Himani from Harman Hospital regarding new medicine samples

---

# 3. Pending Followup Tests

## All followups
Show pending followups

## Followups before date
Show pending followups before next week

---

# 4. Interaction History Tests

## History by doctor
Show interaction history for Dr Himani

## History by HCP ID
Get interaction history for HCP id 2

---

# 5. Edit Interaction Tests

## Mark completed
Mark interaction 5 as completed

## Change followup date
Update followup date of interaction 3 to tomorrow

## Update notes
Add notes to interaction 4 saying doctor requested additional samples

---

# 6. Retry / Failure Tests

## Missing hospital
Show interaction history for Dr Sharma

## Unknown doctor
Show history of doctor that does not exist

## Incomplete interaction
Log interaction with Himani regarding medicine awareness

---

# 7. Date Normalization Tests

## Relative date
Schedule followup after 5 days

## Tomorrow
Set followup for tomorrow

## Next week
Schedule meeting next week

---

# 8. Authentication Tests

## Unauthorized access
Call /chat without token

## Invalid token
Call /chat with invalid token

## Valid token
Call /chat with valid JWT token