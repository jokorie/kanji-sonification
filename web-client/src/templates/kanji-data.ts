/**
 * Pre-processed kanji stroke templates.
 * 
 * Derived from KanjiVG data. Each stroke is an array of normalized points.
 * Coordinates are 0-1 range, derived from 109x109 viewBox.
 */

export interface KanjiTemplate {
  character: string;
  meaning: string;
  strokeCount: number;
  strokes: number[][][]; // [stroke][point][x,y]
}

// Normalize KanjiVG coordinates (0-109) to 0-1 range
const N = (v: number) => v / 109;

/**
 * Common kanji templates (subset for MVP)
 * Stroke data extracted from KanjiVG project
 */
export const KANJI_TEMPLATES: Record<string, KanjiTemplate> = {
  // 一 (one) - single horizontal stroke
  '一': {
    character: '一',
    meaning: 'one',
    strokeCount: 1,
    strokes: [
      [[N(10), N(54)], [N(30), N(52)], [N(54), N(50)], [N(78), N(52)], [N(99), N(54)]]
    ]
  },

  // 二 (two) - two horizontal strokes
  '二': {
    character: '二',
    meaning: 'two',
    strokeCount: 2,
    strokes: [
      [[N(22), N(33)], [N(40), N(32)], [N(60), N(31)], [N(87), N(33)]],
      [[N(12), N(74)], [N(35), N(73)], [N(60), N(72)], [N(85), N(73)], [N(97), N(75)]]
    ]
  },

  // 三 (three) - three horizontal strokes  
  '三': {
    character: '三',
    meaning: 'three',
    strokeCount: 3,
    strokes: [
      [[N(25), N(22)], [N(45), N(21)], [N(65), N(21)], [N(84), N(22)]],
      [[N(18), N(52)], [N(40), N(51)], [N(65), N(51)], [N(91), N(52)]],
      [[N(10), N(85)], [N(35), N(84)], [N(60), N(83)], [N(85), N(84)], [N(99), N(86)]]
    ]
  },

  // 人 (person) - two strokes forming a person shape
  '人': {
    character: '人',
    meaning: 'person',
    strokeCount: 2,
    strokes: [
      // Left falling stroke
      [[N(54), N(12)], [N(50), N(30)], [N(42), N(50)], [N(30), N(70)], [N(15), N(95)]],
      // Right falling stroke  
      [[N(48), N(38)], [N(58), N(55)], [N(70), N(72)], [N(85), N(90)], [N(95), N(100)]]
    ]
  },

  // 大 (big) - three strokes
  '大': {
    character: '大',
    meaning: 'big',
    strokeCount: 3,
    strokes: [
      // Horizontal stroke
      [[N(15), N(35)], [N(35), N(34)], [N(55), N(33)], [N(75), N(34)], [N(94), N(35)]],
      // Left falling stroke
      [[N(54), N(10)], [N(52), N(35)], [N(45), N(55)], [N(30), N(75)], [N(12), N(98)]],
      // Right falling stroke
      [[N(55), N(35)], [N(65), N(55)], [N(78), N(75)], [N(92), N(95)], [N(98), N(100)]]
    ]
  },

  // 日 (sun/day) - four strokes forming a rectangle
  '日': {
    character: '日',
    meaning: 'sun/day',
    strokeCount: 4,
    strokes: [
      // Left vertical
      [[N(28), N(12)], [N(28), N(35)], [N(28), N(60)], [N(28), N(85)], [N(30), N(97)]],
      // Top horizontal + right vertical (one stroke in traditional)
      [[N(28), N(12)], [N(50), N(11)], [N(80), N(12)], [N(80), N(40)], [N(80), N(70)], [N(80), N(97)]],
      // Middle horizontal
      [[N(28), N(54)], [N(45), N(53)], [N(65), N(53)], [N(80), N(54)]],
      // Bottom horizontal
      [[N(28), N(97)], [N(45), N(96)], [N(65), N(96)], [N(80), N(97)]]
    ]
  },

  // 月 (moon/month) - four strokes
  '月': {
    character: '月',
    meaning: 'moon',
    strokeCount: 4,
    strokes: [
      // Left vertical with hook
      [[N(35), N(8)], [N(32), N(30)], [N(28), N(55)], [N(25), N(80)], [N(15), N(100)]],
      // Top horizontal + right side
      [[N(35), N(12)], [N(55), N(11)], [N(78), N(12)], [N(78), N(40)], [N(78), N(70)], [N(78), N(92)]],
      // First inner horizontal
      [[N(30), N(42)], [N(50), N(41)], [N(70), N(41)], [N(78), N(42)]],
      // Second inner horizontal  
      [[N(30), N(68)], [N(50), N(67)], [N(70), N(67)], [N(78), N(68)]]
    ]
  },

  // 山 (mountain) - three strokes
  '山': {
    character: '山',
    meaning: 'mountain',
    strokeCount: 3,
    strokes: [
      // Middle vertical (tallest)
      [[N(54), N(8)], [N(54), N(35)], [N(54), N(60)], [N(54), N(85)], [N(54), N(98)]],
      // Left vertical (shorter)
      [[N(18), N(45)], [N(18), N(65)], [N(18), N(85)], [N(20), N(98)]],
      // Bottom horizontal connecting all
      [[N(18), N(98)], [N(40), N(97)], [N(60), N(97)], [N(80), N(98)], [N(90), N(98)]]
    ]
  },

  // 川 (river) - three vertical strokes
  '川': {
    character: '川',
    meaning: 'river',
    strokeCount: 3,
    strokes: [
      // Left stroke (curved)
      [[N(20), N(15)], [N(18), N(40)], [N(15), N(65)], [N(10), N(90)]],
      // Middle stroke (straight)
      [[N(50), N(10)], [N(50), N(40)], [N(50), N(70)], [N(50), N(100)]],
      // Right stroke (curved outward)
      [[N(80), N(15)], [N(82), N(40)], [N(85), N(65)], [N(90), N(90)]]
    ]
  },

  // 木 (tree) - four strokes
  '木': {
    character: '木',
    meaning: 'tree',
    strokeCount: 4,
    strokes: [
      // Horizontal
      [[N(12), N(35)], [N(35), N(34)], [N(55), N(33)], [N(75), N(34)], [N(97), N(35)]],
      // Vertical (trunk)
      [[N(54), N(8)], [N(54), N(35)], [N(54), N(60)], [N(54), N(85)], [N(54), N(100)]],
      // Left falling
      [[N(54), N(35)], [N(40), N(55)], [N(25), N(75)], [N(10), N(95)]],
      // Right falling
      [[N(54), N(35)], [N(68), N(55)], [N(82), N(75)], [N(97), N(95)]]
    ]
  },

  // 火 (fire) - four strokes
  '火': {
    character: '火',
    meaning: 'fire',
    strokeCount: 4,
    strokes: [
      // Left dot
      [[N(25), N(40)], [N(22), N(48)], [N(18), N(55)]],
      // Right dot
      [[N(82), N(40)], [N(85), N(48)], [N(88), N(55)]],
      // Left falling from center
      [[N(54), N(12)], [N(50), N(35)], [N(40), N(60)], [N(25), N(85)], [N(12), N(100)]],
      // Right falling from center
      [[N(54), N(35)], [N(65), N(55)], [N(78), N(78)], [N(92), N(98)]]
    ]
  }
};

/**
 * Get a kanji template by character
 */
export function getTemplate(character: string): KanjiTemplate | undefined {
  return KANJI_TEMPLATES[character];
}

/**
 * Get all available characters
 */
export function getAvailableCharacters(): string[] {
  return Object.keys(KANJI_TEMPLATES);
}

