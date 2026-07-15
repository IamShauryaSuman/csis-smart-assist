import React from 'react';

export default function PolyhedronIcon({
  size = 24,
  className = '',
}: {
  size?: number | string;
  className?: string;
}) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      stroke="currentColor"
      strokeWidth="5"
      strokeLinejoin="round"
      strokeLinecap="round"
      className={className}
    >
      <polygon points="50,5 89,27 89,73 50,95 11,73 11,27" />
      <polygon points="50,35 75,65 25,65" />
      <line x1="50" y1="5" x2="50" y2="35" />
      <line x1="89" y1="27" x2="50" y2="35" />
      <line x1="11" y1="27" x2="50" y2="35" />
      <line x1="89" y1="27" x2="75" y2="65" />
      <line x1="89" y1="73" x2="75" y2="65" />
      <line x1="50" y1="95" x2="75" y2="65" />
      <line x1="50" y1="95" x2="25" y2="65" />
      <line x1="11" y1="73" x2="25" y2="65" />
      <line x1="11" y1="27" x2="25" y2="65" />
    </svg>
  );
}
