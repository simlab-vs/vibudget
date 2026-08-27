/** The little bit of glue four hand-written screens need instead of a framework. */

type Child = Node | string | null | undefined | false;

export function element<E extends Element = HTMLElement>(selector: string): E {
  const node = document.querySelector<E>(selector);
  if (!node) throw new Error(`no element matches ${selector}`);
  return node;
}

export function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  attributes: Record<string, unknown> = {},
  ...children: Child[]
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);

  for (const [name, value] of Object.entries(attributes)) {
    if (value === null || value === undefined || value === false) continue;
    if (name.startsWith("on") && typeof value === "function") {
      node.addEventListener(name.slice(2).toLowerCase(), value as EventListener);
    } else if (value === true) {
      node.setAttribute(name, "");
    } else {
      node.setAttribute(name, String(value));
    }
  }

  for (const child of children) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child);
  }

  return node;
}

export function replace(parent: Element, ...children: Child[]): void {
  parent.replaceChildren(...children.filter((child): child is Node | string => Boolean(child)));
}

export function row(columns: number, message: string): HTMLTableRowElement {
  return el("tr", { class: "empty" }, el("td", { colspan: columns }, message));
}

export interface Option {
  value: string;
  label: string;
  group?: string;
}

/** Refill a select, keeping the current choice when it is still on offer. */
export function fillSelect(select: HTMLSelectElement, options: Option[], placeholder?: string): void {
  const previous = select.value;
  const groups = new Map<string, HTMLElement>();
  replace(select, placeholder ? el("option", { value: "" }, placeholder) : null);

  for (const option of options) {
    const node = el("option", { value: option.value }, option.label);
    if (!option.group) {
      select.append(node);
      continue;
    }
    let group = groups.get(option.group);
    if (!group) {
      group = el("optgroup", { label: option.group });
      groups.set(option.group, group);
      select.append(group);
    }
    group.append(node);
  }

  if (options.some((option) => option.value === previous)) select.value = previous;
}

/**
 * Run a request, showing whatever the API refused it with in the page banner.
 *
 * A failure leaves the banner standing: the reload that follows a refused write
 * would otherwise wipe the explanation before it could be read. Each gesture
 * calls ``resetStatus`` on its way in instead.
 */
export async function attempt<T>(work: () => Promise<T>): Promise<T | undefined> {
  try {
    return await work();
  } catch (error) {
    const banner = element("#status");
    banner.textContent = error instanceof Error ? error.message : String(error);
    banner.hidden = false;
    return undefined;
  }
}

export function resetStatus(): void {
  const banner = element("#status");
  banner.textContent = "";
  banner.hidden = true;
}

export function fields(form: HTMLFormElement): (name: string) => string {
  const data = new FormData(form);
  return (name) => String(data.get(name) ?? "").trim();
}
