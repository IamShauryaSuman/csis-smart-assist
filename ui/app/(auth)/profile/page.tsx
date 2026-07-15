"use client";

/**
 * Profile Page — User settings and personalization context.
 *
 * Displays editable profile fields, technical interests,
 * and the synthesized session memory from past conversations.
 */

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/lib/hooks/useAuth";
import { useProfile } from "@/lib/hooks/useProfile";
import styles from "./page.module.scss";

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

export default function ProfilePage() {
  const { user } = useAuth();
  const { profile, updateProfile } = useProfile(user?.id);
  const [editData, setEditData] = useState({
    full_name: "",
    academic_role: "undergraduate" as "undergraduate" | "higher_degree" | "faculty" | null,
    department: "",
    year: null as number | null,
    interests: [] as string[],
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (profile) {
      setEditData({
        full_name: profile.full_name || "",
        academic_role: profile.academic_role || "undergraduate",
        department: profile.department || "",
        year: profile.year,
        interests: profile.interests || [],
      });
    }
  }, [profile]);

  const toggleInterest = useCallback((interest: string) => {
    setEditData((prev) => ({
      ...prev,
      interests: prev.interests.includes(interest)
        ? prev.interests.filter((i) => i !== interest)
        : [...prev.interests, interest],
    }));
  }, []);

  const handleSave = useCallback(async () => {
    setSaving(true);
    setSaved(false);
    try {
      await updateProfile(editData);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (error) {
      console.error("Failed to save profile:", error);
    } finally {
      setSaving(false);
    }
  }, [editData, updateProfile]);

  if (!profile) return null;

  return (
    <div className={styles.page}>
      <div className={styles.container}>
        <div className={styles.header}>
          <h1 className={styles.title}>Profile Settings</h1>
          <p className={styles.subtitle}>
            Manage your academic context and personalization preferences.
          </p>
        </div>

        {/* Account Info (Read-only) */}
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Account</h2>
          <div className={styles.field}>
            <span className={styles.label}>Email</span>
            <span className={styles.value}>{profile.email}</span>
          </div>
          <div className={styles.field}>
            <span className={styles.label}>Role</span>
            <span className={styles.value}>
              {profile.is_admin ? "Administrator" : "User"}
            </span>
          </div>
        </div>

        {/* Editable Profile */}
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Academic Profile</h2>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="prof-name">
              Full Name
            </label>
            <input
              id="prof-name"
              className={styles.input}
              type="text"
              value={editData.full_name}
              onChange={(e) =>
                setEditData((prev) => ({
                  ...prev,
                  full_name: e.target.value,
                }))
              }
            />
          </div>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="prof-role">
              Academic Role
            </label>
            <select
              id="prof-role"
              className={styles.select}
              value={editData.academic_role || "undergraduate"}
              onChange={(e) =>
                setEditData((prev) => ({
                  ...prev,
                  academic_role: e.target.value as "undergraduate" | "higher_degree" | "faculty" | null,
                }))
              }
            >
              <option value="undergraduate">Undergraduate</option>
              <option value="higher_degree">Higher Degree (M.E. / Ph.D.)</option>
              <option value="faculty">Faculty</option>
            </select>
          </div>

          <div className={styles.field}>
            <label className={styles.label} htmlFor="prof-dept">
              Department
            </label>
            <input
              id="prof-dept"
              className={styles.input}
              type="text"
              value={editData.department}
              onChange={(e) =>
                setEditData((prev) => ({
                  ...prev,
                  department: e.target.value,
                }))
              }
            />
          </div>

          {editData.academic_role !== "faculty" && (
            <div className={styles.field}>
              <label className={styles.label} htmlFor="prof-year">
                Year
              </label>
              <select
                id="prof-year"
                className={styles.select}
                value={editData.year ?? ""}
                onChange={(e) =>
                  setEditData((prev) => ({
                    ...prev,
                    year: e.target.value
                      ? parseInt(e.target.value, 10)
                      : null,
                  }))
                }
              >
                <option value="">Select</option>
                <option value="1">1st Year</option>
                <option value="2">2nd Year</option>
                <option value="3">3rd Year</option>
                <option value="4">4th Year</option>
                <option value="5">5th Year</option>
              </select>
            </div>
          )}

          <div className={styles.field}>
            <span className={styles.label}>Technical Interests</span>
            <div className={styles.interestsGrid}>
              {INTEREST_OPTIONS.map((interest) => (
                <button
                  key={interest}
                  type="button"
                  className={`${styles.interestChip} ${
                    editData.interests.includes(interest)
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

          {saved && (
            <div className={styles.successMsg}>Profile updated successfully.</div>
          )}

          <button
            className={styles.saveBtn}
            onClick={handleSave}
            disabled={saving}
            id="save-profile-btn"
          >
            {saving ? "Saving..." : "Save Changes"}
          </button>
        </div>

        {/* Synthesized Memory */}
        <div className={styles.section}>
          <h2 className={styles.sectionTitle}>Session Memory</h2>
          <p
            className={styles.subtitle}
            style={{ marginBottom: "16px" }}
          >
            Key facts synthesized from your past conversations, used to
            personalize future responses.
          </p>
          <div className={styles.memorySection}>
            {profile.synthesized_memory ? (
              <div className={styles.memoryContent}>
                {profile.synthesized_memory}
              </div>
            ) : (
              <div className={styles.memoryEmpty}>
                No session memory accumulated yet. Your memory will build as you
                use the chat.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
