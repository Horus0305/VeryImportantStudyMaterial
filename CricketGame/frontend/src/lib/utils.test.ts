import { describe, it, expect } from 'vitest';
import { cn } from './utils';

describe('cn utility', () => {
  it('merges basic class strings', () => {
    expect(cn('class1', 'class2')).toBe('class1 class2');
  });

  it('merges conditional classes (object syntax)', () => {
    expect(cn('class1', { 'class2': true, 'class3': false })).toBe('class1 class2');
  });

  it('handles array inputs', () => {
    expect(cn(['class1', 'class2'])).toBe('class1 class2');
  });

  it('merges tailwind classes correctly', () => {
    expect(cn('p-4', 'p-2')).toBe('p-2');
    expect(cn('px-2 py-1', 'p-4')).toBe('p-4');
  });

  it('handles mixed inputs', () => {
    expect(cn('class1', ['class2', { 'class3': true }])).toBe('class1 class2 class3');
  });

  it('ignores falsy values', () => {
    expect(cn('class1', undefined, null, false)).toBe('class1');
  });

  it('handles complex tailwind conflicts', () => {
    expect(cn('text-red-500', 'text-blue-500')).toBe('text-blue-500');
    const result = cn('bg-red-500 hover:bg-red-700', 'bg-blue-500');
    expect(result).toContain('bg-blue-500');
    expect(result).toContain('hover:bg-red-700');
    expect(result.split(' ')).not.toContain('bg-red-500');
  });
});
