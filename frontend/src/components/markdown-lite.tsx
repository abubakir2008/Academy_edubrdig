/**
 * Deliberately not a full markdown parser — just enough of GitHub-flavoured
 * markdown to render AI explanations (headings, bold, lists, fenced code)
 * without pulling in a dependency for what is, so far, one feature.
 */

function renderInline(text: string, keyPrefix: string): React.ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) =>
    part.startsWith("**") && part.endsWith("**") ? (
      <strong key={`${keyPrefix}-${i}`}>{part.slice(2, -2)}</strong>
    ) : (
      <span key={`${keyPrefix}-${i}`}>{part}</span>
    ),
  );
}

function renderTextBlock(text: string, keyPrefix: string): React.ReactNode[] {
  const lines = text.split("\n");
  const blocks: React.ReactNode[] = [];
  let list: { ordered: boolean; items: string[] } | null = null;
  let paragraph: string[] = [];

  const flushParagraph = () => {
    if (paragraph.length) {
      blocks.push(
        <p key={`${keyPrefix}-p-${blocks.length}`} className="leading-relaxed">
          {renderInline(paragraph.join(" "), `${keyPrefix}-p-${blocks.length}`)}
        </p>,
      );
      paragraph = [];
    }
  };
  const flushList = () => {
    if (list) {
      const Tag = list.ordered ? "ol" : "ul";
      blocks.push(
        <Tag key={`${keyPrefix}-l-${blocks.length}`} className={`${list.ordered ? "list-decimal" : "list-disc"} space-y-1 pl-5`}>
          {list.items.map((item, i) => (
            <li key={i}>{renderInline(item, `${keyPrefix}-li-${i}`)}</li>
          ))}
        </Tag>,
      );
      list = null;
    }
  };

  for (const raw of lines) {
    const line = raw.trim();
    const heading = /^(#{1,4})\s+(.*)$/.exec(line);
    const bullet = /^[-*]\s+(.*)$/.exec(line);
    const numbered = /^\d+\.\s+(.*)$/.exec(line);

    if (!line) {
      flushParagraph();
      flushList();
    } else if (heading) {
      flushParagraph();
      flushList();
      const level = heading[1].length;
      const Tag = (level <= 2 ? "h3" : "h4") as "h3" | "h4";
      blocks.push(
        <Tag key={`${keyPrefix}-h-${blocks.length}`} className="display mt-2 text-base">
          {renderInline(heading[2], `${keyPrefix}-h-${blocks.length}`)}
        </Tag>,
      );
    } else if (bullet) {
      flushParagraph();
      if (!list || list.ordered) {
        flushList();
        list = { ordered: false, items: [] };
      }
      list.items.push(bullet[1]);
    } else if (numbered) {
      flushParagraph();
      if (!list || !list.ordered) {
        flushList();
        list = { ordered: true, items: [] };
      }
      list.items.push(numbered[1]);
    } else {
      flushList();
      paragraph.push(line);
    }
  }
  flushParagraph();
  flushList();
  return blocks;
}

export function MarkdownLite({ text }: { text: string }) {
  const segments = text.split(/```(\w*)\n?([\s\S]*?)```/g);
  const nodes: React.ReactNode[] = [];
  // String.split with a capturing regex interleaves [text, lang, code, text, lang, code, ...]
  for (let i = 0; i < segments.length; i += 3) {
    const plain = segments[i];
    if (plain) nodes.push(...renderTextBlock(plain, `t${i}`));
    const code = segments[i + 2];
    if (code !== undefined) {
      nodes.push(
        <pre key={`c${i}`} className="overflow-x-auto rounded-xl bg-ink px-4 py-3 text-xs text-paper-2">
          <code>{code.replace(/\n$/, "")}</code>
        </pre>,
      );
    }
  }
  return <div className="space-y-3 text-sm text-ink-2">{nodes}</div>;
}
