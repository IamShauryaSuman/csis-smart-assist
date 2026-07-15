"use client";

/**
 * OnboardingForm — Captures academic profile data for new users.
 *
 * Non-dismissible form that collects role, department, year, and
 * technical interests before allowing access to the main application.
 */

import { useCallback, useState, type FormEvent } from "react";
import type { OnboardingFormData } from "@/lib/types";
import styles from "./onboarding-form.module.scss";

interface OnboardingFormProps {
  onSubmit: (data: OnboardingFormData) => Promise<void>;
}

const INTEREST_OPTIONS = [
  "Machine Learning",
  "Web Development",
  "Systems Programming",
  "Databases",
  "Computer Networks",
  "Cybersecurity",
  "Cloud Computing",
  "Data Science",
  "Algorithms",
  "Operating Systems",
  "Computer Vision",
  "NLP",
  "Mobile Development",
  "DevOps",
  "Blockchain",
  "Embedded Systems",
];

export default function OnboardingForm({ onSubmit }: OnboardingFormProps) {
  const [formData, setFormData] = useState<OnboardingFormData>({
    full_name: "",
    academic_role: "undergraduate",
    department: "Computer Science & Information Systems",
    year: null,
    interests: [],
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const toggleInterest = useCallback((interest: string) => {
    setFormData((prev) => ({
      ...prev,
      interests: prev.interests.includes(interest)
        ? prev.interests.filter((i) => i !== interest)
        : [...prev.interests, interest],
    }));
  }, []);

  const handleSubmit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      setError("");

      if (!formData.full_name.trim()) {
        setError("Please enter your full name.");
        return;
      }

      setLoading(true);
      try {
        await onSubmit(formData);
      } catch (err: any) {
        console.error("Onboarding error:", err);
        setError(
          err?.message || (typeof err === "object" ? JSON.stringify(err) : "An error occurred. Please try again.")
        );
      } finally {
        setLoading(false);
      }
    },
    [formData, onSubmit]
  );

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <div className={styles.field}>
        <label className={styles.label} htmlFor="full-name">
          Full Name
        </label>
        <input
          id="full-name"
          className={styles.input}
          type="text"
          value={formData.full_name}
          onChange={(e) =>
            setFormData((prev) => ({ ...prev, full_name: e.target.value }))
          }
          placeholder="Enter your full name"
          required
        />
      </div>

      <div className={styles.field}>
        <label className={styles.label} htmlFor="academic-role">
          Academic Role
        </label>
        <select
          id="academic-role"
          className={styles.select}
          value={formData.academic_role}
          onChange={(e) =>
            setFormData((prev) => ({
              ...prev,
              academic_role: e.target.value as OnboardingFormData["academic_role"],
            }))
          }
        >
          <option value="undergraduate">Undergraduate Student</option>
          <option value="higher_degree">Higher Degree (M.E. / Ph.D.)</option>
          <option value="faculty">Faculty</option>
        </select>
      </div>

      <div className={styles.field}>
        <label className={styles.label} htmlFor="department">
          Department
        </label>
        <input
          id="department"
          className={styles.input}
          type="text"
          value={formData.department}
          onChange={(e) =>
            setFormData((prev) => ({ ...prev, department: e.target.value }))
          }
          placeholder="e.g., Computer Science & Information Systems"
        />
      </div>

      {formData.academic_role !== "faculty" && (
        <div className={styles.field}>
          <label className={styles.label} htmlFor="year">
            Year of Study
          </label>
          <select
            id="year"
            className={styles.select}
            value={formData.year ?? ""}
            onChange={(e) =>
              setFormData((prev) => ({
                ...prev,
                year: e.target.value ? parseInt(e.target.value, 10) : null,
              }))
            }
          >
            <option value="">Select year</option>
            <option value="1">1st Year</option>
            <option value="2">2nd Year</option>
            <option value="3">3rd Year</option>
            <option value="4">4th Year</option>
            <option value="5">5th Year (Dual Degree)</option>
          </select>
        </div>
      )}

      <div className={styles.field}>
        <label className={styles.label}>Technical Interests</label>
        <div className={styles.interestsGrid}>
          {INTEREST_OPTIONS.map((interest) => (
            <button
              key={interest}
              type="button"
              className={`${styles.interestChip} ${
                formData.interests.includes(interest)
                  ? styles.interestChipActive
                  : ""
              }`}
              onClick={() => toggleInterest(interest)}
            >
              {interest}
            </button>
          ))}
        </div>
      </div>

      {error && <div className={styles.error}>{error}</div>}

      <button
        type="submit"
        className={styles.submitBtn}
        disabled={loading}
        id="onboarding-submit"
      >
        {loading ? "Setting up your profile..." : "Complete Setup"}
      </button>
    </form>
  );
}
