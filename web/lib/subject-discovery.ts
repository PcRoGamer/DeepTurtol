export interface SubjectDiscoveryResult {
  subject: string;
  emoji: string;
}

/**
 * Fast, instant synchronous subject classification based on title and active capability.
 */
export function discoverSubject(
  title: string,
  lastMessage?: string,
  capability?: string,
): SubjectDiscoveryResult {
  const text = `${title || ""} ${lastMessage || ""}`.toLowerCase();

  if (
    /\b(rust|python|typescript|javascript|react|next|code|debug|git|api|docker|sql|html|css|compiler|function|bug)\b/i.test(
      text,
    ) ||
    capability === "code_execution" ||
    capability === "exec"
  ) {
    return { subject: "Coding", emoji: "🦀" };
  }
  if (
    /\b(math|calculus|equation|matrix|fourier|algebra|geometry|physics|proof|manim|graph)\b/i.test(
      text,
    ) ||
    capability === "math_animator" ||
    capability === "visualize"
  ) {
    return { subject: "Mathematics", emoji: "📐" };
  }
  if (
    /\b(paper|research|arxiv|study|survey|pdf|analysis|report|literature)\b/i.test(
      text,
    ) ||
    capability === "deep_research" ||
    capability === "rag"
  ) {
    return { subject: "Research", emoji: "📚" };
  }
  if (
    /\b(draft|essay|co-writer|proposal|email|writing|article|story)\b/i.test(
      text,
    ) ||
    capability === "co_writer"
  ) {
    return { subject: "Writing", emoji: "✍️" };
  }

  const cleanTitle = (title || "").replace(/^New conversation$/i, "").trim();
  if (cleanTitle && cleanTitle.length > 0 && !/^testing\b/i.test(cleanTitle) && !/^test\b/i.test(cleanTitle) && !/^first\b/i.test(cleanTitle)) {
    return { subject: cleanTitle.slice(0, 20), emoji: "🐚" };
  }

  return { subject: "General", emoji: "🐚" };
}
