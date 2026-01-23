// Utility function for combining class names
// Simple implementation that doesn't require additional dependencies

export function cn(...classes) {
  return classes
    .flat()
    .filter(Boolean)
    .join(' ')
    .replace(/\s+/g, ' ')
    .trim()
}
