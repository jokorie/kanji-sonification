import { describe, it, expect } from 'vitest';
import { getTemplate, getAvailableCharacters, KANJI_TEMPLATES } from '../templates/kanji-data';

describe('getTemplate', () => {
  it('returns a template for a known character', () => {
    const t = getTemplate('一');
    expect(t).toBeDefined();
    expect(t!.character).toBe('一');
    expect(t!.reading).toBe('いっしゅうかん');
  });

  it('returns undefined for an unknown character', () => {
    expect(getTemplate('X')).toBeUndefined();
    expect(getTemplate('')).toBeUndefined();
  });

  it('strokeCount matches the actual number of strokes in the data', () => {
    for (const char of getAvailableCharacters()) {
      const t = getTemplate(char)!;
      expect(t.strokes.length).toBe(t.strokeCount);
    }
  });

  it('every stroke has at least 2 points', () => {
    for (const char of getAvailableCharacters()) {
      for (const stroke of getTemplate(char)!.strokes) {
        expect(stroke.length).toBeGreaterThanOrEqual(2);
      }
    }
  });

  it('all coordinates are normalized to [0, 1]', () => {
    for (const char of getAvailableCharacters()) {
      for (const stroke of getTemplate(char)!.strokes) {
        for (const [x, y] of stroke) {
          expect(x).toBeGreaterThanOrEqual(0);
          expect(x).toBeLessThanOrEqual(1);
          expect(y).toBeGreaterThanOrEqual(0);
          expect(y).toBeLessThanOrEqual(1);
        }
      }
    }
  });
});

describe('getAvailableCharacters', () => {
  it('returns a non-empty array', () => {
    expect(getAvailableCharacters().length).toBeGreaterThan(0);
  });

  it('includes the expected starter kanji', () => {
    const chars = getAvailableCharacters();
    for (const expected of ['一', '二', '三', '人', '山', '川', '日', '月', '木', '火', '大']) {
      expect(chars).toContain(expected);
    }
  });

  it('matches the keys of KANJI_TEMPLATES', () => {
    expect(getAvailableCharacters().sort()).toEqual(Object.keys(KANJI_TEMPLATES).sort());
  });
});
