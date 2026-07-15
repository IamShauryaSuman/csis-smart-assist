"use client";

/**
 * Navbar — Persistent navigation bar for authenticated pages.
 *
 * Displays logo, page links, user avatar, and sign-out action.
 * Responsive with mobile hamburger menu.
 */

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/hooks/useAuth";
import { Menu, X } from "lucide-react";
import type { Profile } from "@/lib/types";
import styles from "./navbar.module.scss";

interface NavbarProps {
  profile: Profile | null;
}

const NAV_ITEMS = [
  { href: "/chat", label: "Chat" },
  { href: "/bookings", label: "Bookings" },
];

function ProfileIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: 16, height: 16 }}>
      <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  );
}

function SignOutIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ width: 16, height: 16 }}>
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" x2="9" y1="12" y2="12" />
    </svg>
  );
}

function ChevronDownIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ width: 16, height: 16, color: "var(--text-muted, #a1a1aa)" }}>
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

export default function Navbar({ profile }: NavbarProps) {
  const { user, signOut } = useAuth();
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const initials =
    profile?.full_name
      ?.split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .slice(0, 2) || "??";

  const avatarUrl = user?.user_metadata?.avatar_url;

  return (
    <nav className={styles.nav}>
      <div className={styles.left}>
        <Link href="/chat" className={styles.logo}>
          <div className={styles.logoMark}>CSIS</div>
          <span className={styles.logoText}>SmartAssist</span>
        </Link>

        <div className={styles.navLinks}>
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`${styles.navLink} ${
                pathname === item.href ? styles.navLinkActive : ""
              }`}
            >
              {item.label}
            </Link>
          ))}
        </div>
      </div>

      <div className={styles.right}>
        {profile?.is_admin && (
          <Link
            href="/admin"
            className={`${styles.navLink} ${styles.adminLink} ${
              pathname === "/admin" ? styles.navLinkActive : ""
            }`}
          >
            Admin
          </Link>
        )}

        <div className={styles.dropdownContainer} ref={dropdownRef}>
          <button 
            className={styles.userInfo} 
            onClick={() => setDropdownOpen(!dropdownOpen)}
            aria-expanded={dropdownOpen}
          >
            {avatarUrl ? (
              <img
                src={avatarUrl}
                alt="Avatar"
                className={styles.avatar}
                referrerPolicy="no-referrer"
              />
            ) : (
              <div className={styles.avatarFallback}>{initials}</div>
            )}
            <span className={styles.userName}>
              {profile?.full_name || user?.email}
            </span>
            <ChevronDownIcon />
          </button>

          {dropdownOpen && (
            <div className={styles.dropdownMenu}>
              <Link 
                href="/profile" 
                className={styles.dropdownItem}
                onClick={() => setDropdownOpen(false)}
              >
                <ProfileIcon />
                <span>Profile</span>
              </Link>
              <button
                className={`${styles.dropdownItem} ${styles.signOutItem}`}
                onClick={() => {
                  setDropdownOpen(false);
                  signOut();
                }}
                id="sign-out-btn"
              >
                <SignOutIcon />
                <span>Sign Out</span>
              </button>
            </div>
          )}
        </div>

        <button
          className={styles.mobileToggle}
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label="Toggle navigation menu"
          id="mobile-nav-toggle"
        >
          {mobileOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {mobileOpen && (
        <div className={styles.mobileMenu}>
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={styles.mobileNavLink}
              onClick={() => setMobileOpen(false)}
            >
              {item.label}
            </Link>
          ))}
          {profile?.is_admin && (
            <Link
              href="/admin"
              className={styles.mobileNavLink}
              onClick={() => setMobileOpen(false)}
            >
              Admin
            </Link>
          )}
          
          <hr className={styles.mobileDivider} />
          
          <Link
            href="/profile"
            className={styles.mobileNavLink}
            onClick={() => setMobileOpen(false)}
          >
            Profile
          </Link>
          <button
            className={`${styles.mobileNavLink} ${styles.mobileSignOut}`}
            onClick={() => {
              setMobileOpen(false);
              signOut();
            }}
          >
            Sign Out
          </button>
        </div>
      )}
    </nav>
  );
}
