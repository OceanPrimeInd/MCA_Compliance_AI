/**
 * Minimal markdown renderer for compliance answers.
 *
 * The engine returns a fixed three-part structure — headings, bold verdicts,
 * and blockquoted verbatim statute. Rendering that raw shows `###` and `**` to
 * the reader, which makes a working answer look broken. A full markdown library
 * would be ~40KB for four constructs we control the shape of.
 *
 * Deliberately renders as React elements rather than HTML strings: the answer
 * text originates from a model, and building innerHTML from it would open an
 * injection path into a page that shows regulatory determinations.
 */

/**
 * Inline constructs, in precedence order. Bold must be tested before italic —
 * a single-asterisk rule would otherwise consume the first two asterisks of a
 * `**bold**` run and leave the closing pair stranded as literal text.
 *
 * Backticks matter here specifically: statute quotes contain clause numbers and
 * measurements the model tends to wrap in code spans, and an unrendered
 * backtick inside a legal quotation reads to an auditor as a corrupted output.
 */
const INLINE_RULES = [
  { re: /\*\*(.+?)\*\*/g, tag: "strong" },
  { re: /(?<!\w)_([^_]+)_(?!\w)/g, tag: "em" },
  { re: /(?<![*\w])\*([^*\n]+)\*(?![*\w])/g, tag: "em" },
  { re: /`([^`]+)`/g, tag: "code" },
];

/** Recursively split a string on the first matching inline rule. */
function inline(text, keyPrefix, ruleIndex = 0) {
  if (ruleIndex >= INLINE_RULES.length) return [text];

  const { re, tag } = INLINE_RULES[ruleIndex];
  const Tag = tag;
  const parts = [];
  let cursor = 0;
  let match;

  re.lastIndex = 0;
  while ((match = re.exec(text)) !== null) {
    if (match.index > cursor) {
      // Text before the match may still contain later-precedence constructs.
      parts.push(...inline(text.slice(cursor, match.index), `${keyPrefix}-p${cursor}`, ruleIndex + 1));
    }
    parts.push(
      <Tag key={`${keyPrefix}-${tag}${match.index}`} className={tag === "code" ? "md-code" : undefined}>
        {tag === "code"
          ? match[1]
          : inline(match[1], `${keyPrefix}-i${match.index}`, ruleIndex + 1)}
      </Tag>
    );
    cursor = match.index + match[0].length;
  }

  if (cursor < text.length) {
    parts.push(...inline(text.slice(cursor), `${keyPrefix}-t${cursor}`, ruleIndex + 1));
  }

  return parts.length ? parts : [text];
}

export function Markdown({ text, className = "" }) {
  if (!text) return null;

  const blocks = [];
  const lines = String(text).split("\n");

  let listBuffer = [];
  let quoteBuffer = [];

  const flushList = () => {
    if (!listBuffer.length) return;
    blocks.push(
      <ul key={`ul-${blocks.length}`} className="md-list">
        {listBuffer.map((item, i) => (
          <li key={i}>{inline(item, `li${blocks.length}-${i}`)}</li>
        ))}
      </ul>
    );
    listBuffer = [];
  };

  const flushQuote = () => {
    if (!quoteBuffer.length) return;
    blocks.push(
      <blockquote key={`bq-${blocks.length}`} className="md-quote">
        {quoteBuffer.map((line, i) => (
          <p key={i}>{inline(line, `bq${blocks.length}-${i}`)}</p>
        ))}
      </blockquote>
    );
    quoteBuffer = [];
  };

  lines.forEach((raw, index) => {
    const line = raw.trimEnd();

    if (!line.trim()) {
      flushList();
      flushQuote();
      return;
    }

    const heading = line.match(/^(#{1,6})\s+(.*)$/);
    if (heading) {
      flushList();
      flushQuote();
      const level = Math.min(heading[1].length + 1, 6); // never emit an h1 inside a page
      const Tag = `h${level}`;
      blocks.push(
        <Tag key={`h-${index}`} className="md-h">
          {inline(heading[2], `h${index}`)}
        </Tag>
      );
      return;
    }

    if (line.startsWith(">")) {
      flushList();
      quoteBuffer.push(line.replace(/^>\s?/, ""));
      return;
    }

    const bullet = line.match(/^\s*[-*]\s+(.*)$/);
    if (bullet) {
      flushQuote();
      listBuffer.push(bullet[1]);
      return;
    }

    flushList();
    flushQuote();
    blocks.push(
      <p key={`p-${index}`} className="md-p">
        {inline(line, `p${index}`)}
      </p>
    );
  });

  flushList();
  flushQuote();

  return <div className={`md ${className}`.trim()}>{blocks}</div>;
}

export default Markdown;
