import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import BookingCard from '../components/bookings/booking-card';
import { mockBooking, mockApprovedBooking, mockRejectedBooking } from './fixtures';

// Mock the CSS module — SCSS modules return empty objects in jsdom
vi.mock('../components/bookings/booking-card.module.scss', () => ({
  default: {
    card: 'card',
    top: 'top',
    title: 'title',
    statusPending: 'statusPending',
    statusApproved: 'statusApproved',
    statusRejected: 'statusRejected',
    details: 'details',
    row: 'row',
    icon: 'icon',
    value: 'value',
    notes: 'notes',
    notesLabel: 'notesLabel',
    notesText: 'notesText',
  },
}));

describe('BookingCard', () => {
  it('renders the booking title and room name', () => {
    render(<BookingCard booking={mockBooking} />);
    expect(screen.getByText('CS F111 Lecture')).toBeInTheDocument();
    expect(screen.getByText('DLT-8')).toBeInTheDocument();
  });

  it('renders the booking description when present', () => {
    render(<BookingCard booking={mockBooking} />);
    expect(screen.getByText('Regular class')).toBeInTheDocument();
  });

  it('does not render description section when description is absent', () => {
    const noDesc = { ...mockBooking, description: null };
    render(<BookingCard booking={noDesc} />);
    expect(screen.queryByText('Regular class')).not.toBeInTheDocument();
  });

  it('shows PENDING status badge for pending bookings', () => {
    render(<BookingCard booking={mockBooking} />);
    expect(screen.getByText('PENDING')).toBeInTheDocument();
  });

  it('shows APPROVED status badge for approved bookings', () => {
    render(<BookingCard booking={mockApprovedBooking} />);
    expect(screen.getByText('APPROVED')).toBeInTheDocument();
  });

  it('shows REJECTED status badge for rejected bookings', () => {
    render(<BookingCard booking={mockRejectedBooking} />);
    expect(screen.getByText('REJECTED')).toBeInTheDocument();
  });

  it('renders admin notes when present', () => {
    render(<BookingCard booking={mockApprovedBooking} />);
    expect(screen.getByText('Admin Notes')).toBeInTheDocument();
    expect(screen.getByText('Approved. Have a great class!')).toBeInTheDocument();
  });

  it('does not render admin notes section when absent', () => {
    render(<BookingCard booking={mockBooking} />);
    expect(screen.queryByText('Admin Notes')).not.toBeInTheDocument();
  });

  it('renders start and end time in the card', () => {
    render(<BookingCard booking={mockBooking} />);
    // Arrow separator should be present between the two times
    const valueElements = screen.getAllByText(/→/);
    expect(valueElements.length).toBeGreaterThan(0);
  });
});
