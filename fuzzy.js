// Pure fuzzy matching utilities. No imports.

/**
 * Score a case-insensitive subsequence match of `query` in `text`.
 * Returns null if not all query characters appear in order.
 * Higher score = better match.
 *
 * Scoring:
 *  - Base: 100 per matched character.
 *  - Consecutive bonus: +50 for each consecutive run length > 1 (i.e. +50*(run-1)).
 *  - Word-start bonus: +30 if the match starts at index 0 or after a space.
 *  - Shorter text bonus: +20 * (1 - text.length / 100) capped at +20 (shorter is better).
 */
export function fuzzyScore(query, text) {
  if (!query || query.length === 0) return 0;
  if (!text) return null;

  const q = query.toLowerCase();
  const t = text.toLowerCase();

  let qi = 0;
  let score = 0;
  let run = 0;
  let firstMatchIndex = -1;

  for (let ti = 0; ti < t.length && qi < q.length; ti++) {
    if (t[ti] === q[qi]) {
      if (firstMatchIndex === -1) {
        firstMatchIndex = ti;
      }
      qi++;
      score += 100;

      if (run > 0) {
        score += 50;
      }
      run++;
    } else {
      run = 0;
    }
  }

  if (qi < q.length) {
    return null;
  }

  // Word-start bonus
  if (firstMatchIndex === 0 || t[firstMatchIndex - 1] === ' ') {
    score += 30;
  }

  // Shorter text bonus
  const shortBonus = Math.max(0, 20 * (1 - t.length / 100));
  score += shortBonus;

  return score;
}

/**
 * Rank items by fuzzy score against query.
 * Items: {id, label, hint?, keywords?: string}
 * Returns sorted array (best first), limited to `limit`.
 * Empty query returns first `limit` items unchanged.
 */
export function rank(query, items, limit = 8) {
  if (!query || query.length === 0) {
    return items.slice(0, limit);
  }

  const scored = [];
  for (const item of items) {
    const label = item.label || '';
    const keywords = item.keywords || '';
    const combined = label + ' ' + keywords;

    const s = fuzzyScore(query, combined);
    if (s !== null) {
      scored.push({ item, score: s });
    }
  }

  scored.sort((a, b) => b.score - a.score);

  return scored.slice(0, limit).map(x => x.item);
}
