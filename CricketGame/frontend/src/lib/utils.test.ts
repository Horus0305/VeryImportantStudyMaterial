import { describe, it, expect } from 'vitest';
import { cn } from './utils';

describe('cn utility', () => {
  it('merges class names correctly', () => {
    expect(cn('class1', 'class2')).toBe('class1 class2');
  });

  it('handles conditional classes', () => {
    expect(cn('class1', { 'class2': true, 'class3': false })).toBe('class1 class2');
  });

  it('handles array inputs', () => {
    expect(cn(['class1', 'class2'])).toBe('class1 class2');
  });

  it('merges tailwind classes correctly (conflict resolution)', () => {
    // p-4 should be overridden by p-2
    expect(cn('p-4', 'p-2')).toBe('p-2');
    // text-red-500 should be overridden by text-blue-500
    expect(cn('text-red-500', 'text-blue-500')).toBe('text-blue-500');
  });

  it('handles mixed inputs (strings, objects, arrays)', () => {
    expect(cn('class1', ['class2'], { 'class3': true })).toBe('class1 class2 class3');
  });

  it('handles undefined, null, and boolean values', () => {
    expect(cn('class1', undefined, null, false, true && 'class2')).toBe('class1 class2');
  });
});
