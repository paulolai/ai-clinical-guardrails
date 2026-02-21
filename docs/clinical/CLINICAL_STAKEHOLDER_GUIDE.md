# Clinical Stakeholder Guide

**For:** General Practitioners, Specialists, Nurses, Practice Managers
**Purpose:** How voice transcription extraction works in clinical practice

---

## What Is This?

A system that listens to your voice dictation, extracts the important clinical information (medications, diagnoses, dates), and helps populate your clinical software automatically. You remain in complete control—you review everything before it goes into the patient record.

**Think of it as:** A very smart assistant that takes your dictation and fills out the structured fields for you to check.

---

## How It Works (Step by Step)

### 1. You Dictate
After seeing a patient, click "Voice Document" in your clinical software and speak naturally:

> "Mrs. Johnson came in yesterday for her diabetes follow-up. Her HbA1c was 7.8. I've increased her Metformin to 1000mg twice daily. Recheck in three months."

### 2. System Extracts
The system converts your speech to text, then extracts:
- **Patient:** Mrs. Johnson
- **Date:** Yesterday → [Resolved to actual date]
- **Condition:** Diabetes
- **Lab Result:** HbA1c 7.8
- **Medication Change:** Metformin increased to 1000mg twice daily
- **Follow-up:** 3 months

### 3. System Verifies
Checks against the patient's record:
- ✓ Is Mrs. Johnson the patient in this appointment?
- ✓ Does the date "yesterday" match?
- ✓ Is Metformin in her medication list?
- ✓ Any missing elements?

### 4. You Review
You see a screen showing:
- Your original dictation (full text)
- Extracted information (organised)
- Any alerts (e.g., "Medication not in active list")
- Confidence scores

### 5. You Approve
You can:
- ✓ Click "Accept All" if everything looks right
- ✏️ Edit any field that needs correction
- 🗑️ Delete incorrect extractions
- ➕ Add anything that was missed
- ✍️ Reject extraction and type manually

**Nothing enters the patient record until you explicitly approve it.**

---

## When Does It Help Most?

**Complex Consultations:**
- Multiple medication changes
- Chronic disease management
- Detailed examination findings

**Long Consultations:**
- Mental health reviews
- Comprehensive health assessments
- New patient workups

**Time-Pressured Situations:**
- Emergency department
- Busy morning clinics
- End-of-session catch-up

---

## Confidence Levels

The system shows you how confident it is about each extraction:

| Icon | Meaning | What You Should Do |
|------|---------|-------------------|
| ✅ High (>95%) | Very confident | Quick review, likely correct |
| ⚠️ Medium (70-95%) | Somewhat confident | Check carefully, may need correction |
| ❓ Low (<70%) | Not confident | System won't auto-populate; you decide |

**Safety Rule:** Critical things (medication changes) need 98%+ confidence before auto-populating.

---

## Common Questions

### "What if it gets something wrong?"

You can edit or delete any extraction before approving. The system learns from corrections to improve over time. Nothing goes into the record without your explicit approval.

### "Will this slow me down?"

Initially, you might spend extra time reviewing while learning to trust the system. Most clinicians find it saves 3-5 minutes per patient after the first week.

### "What about patient privacy?"

- All data stays in Australia (AWS Sydney)
- No audio recordings stored (just transcripts)
- Same security as your clinical software
- Complies with Privacy Act and My Health Record rules

### "Does it work with my software?"

Currently integrating with:
- Best Practice Software
- MedicalDirector
- Major hospital systems

If you use different software, let us know—we're expanding integrations.

### "What about Medicare billing?"

The system **suggests** MBS item numbers based on complexity, but **you must manually select** the billing item. We never automate Medicare billing (legal requirement).

### "Can I still type if I prefer?"

Absolutely. Voice is optional. You can always use templates or free text as you do now.

### "What if the system goes down?"

You'll get an error message and can use manual entry. No data is lost.

---

## Getting Started

### For Early Adopters (Alpha/Beta)

**What's involved:**
- 1-hour training session
- Use for 2-4 weeks
- Provide feedback (surveys, interviews)
- Help improve the system

**What's in it for you:**
- Shape the product to meet your needs
- Early access to productivity improvements
- Recognition as clinical champion

### For Later Adopters (General Availability)

**What's involved:**
- Self-paced training (videos, 30 minutes)
- Optional: 30-minute group webinar
- Use when you're ready

**Support available:**
- Help desk (email/phone)
- Online resources
- Peer support network

---

## Safety Features

### You Control Everything
- No automatic actions without your approval
- Override any extraction
- Reject extraction entirely
- Switch to manual entry anytime

### Verification Layer
- Cross-checks against patient record
- Alerts on discrepancies
- Flags unusual patterns
- Won't let you sign if critical alerts unresolved

### Audit Trail
- Records what was extracted
- Records what you changed
- Records when you approved
- Available for medicolegal purposes

---

## Feedback

**We want to hear from you:**
- What's working well?
- What's frustrating?
- What features would help?
- What concerns do you have?

**How to provide feedback:**
- In-app feedback button
- Email: [feedback email]
- Monthly user forums
- Direct contact with Clinical Advisory Board

**Your feedback directly shapes the product.**

---

## Clinical Governance

**Clinical Advisory Board:**
- GPs, specialists, nurses, practice managers
- Meets regularly to review safety and features
- You can nominate to join

**Safety Monitoring:**
- All errors logged and reviewed
- Monthly safety reports
- Immediate response to critical issues

**Continuous Improvement:**
- Accuracy improves based on corrections
- Features added based on user feedback
- Regular updates and enhancements

---

## Contact

**Clinical Questions:** [Clinical Lead Email]
**Technical Support:** [Support Email/Phone]
**Feedback:** [Feedback Email]

**Documentation:**
- Full Requirements: [VOICE_TRANSCRIPTION_REQUIREMENTS.md](../business/VOICE_TRANSCRIPTION_REQUIREMENTS.md)
- Workflow Details: [CLINICAL_WORKFLOW_INTEGRATION.md](CLINICAL_WORKFLOW_INTEGRATION.md)
- Privacy & Security: [VOICE_DATA_COMPLIANCE.md](../compliance/VOICE_DATA_COMPLIANCE.md)

---

*Thank you for considering this technology. Our goal is to give you time back for patient care while maintaining the highest safety standards.*
