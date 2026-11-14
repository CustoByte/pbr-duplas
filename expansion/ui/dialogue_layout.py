"""Source-bounded reflow and gated continuation, without changing translated words."""
import re
from translation.messages import TOKEN, encoded, readable
from ui.layout_text import LEAD, preserve_alignment_breaks

PAGE = '{000D}'
FONT = re.compile(r'^(?:\{F[0-9A-F]{3}\})+')
# Existing source-specific screenshot budgets; these are not generic frames.
COMMON_WIDTHS = {6872:130,9218:160,7085:180,7664:220,7665:100,7671:100,
                7673:220,7826:100,8055:100,9915:160,9916:150,9920:100,
                9924:160,9925:160,9433:380,8442:380,7061:146}
COMMON_WIDTHS.update({i:112 for i in range(7649,7657)})
COMMON_WIDTHS.update({i:125 for i in range(3237,3255)})
COMMON_WIDTHS.update({i:220 for i in range(8282,8307)})


def lexical(text):
    return re.sub(r'\s+', '', TOKEN.sub('', text))


def validate_presentation(before, after, allow_pages=False):
    """Only whitespace and explicitly authorized extra continuation may change."""
    a, b = TOKEN.findall(before), TOKEN.findall(after)
    if allow_pages:
        if b.count(PAGE) < a.count(PAGE):
            raise ValueError('Existing continuation removed')
        # Voiced NPC pages close the existing speaking effect before waiting
        # and reopen it after continuing, matching the game's original pattern.
        if '{0027}' in before and '{0028}' in before:
            reset = re.compile(r'\{0028\}\{000D\}\s*\{0027\}')
            a = TOKEN.findall(reset.sub(PAGE, before))
            b = TOKEN.findall(reset.sub(PAGE, after))
        a, b = [x for x in a if x != PAGE], [x for x in b if x != PAGE]
    if a != b:
        raise ValueError('Layout changed formatting, variables, or their order')
    if encoded(before)[:8] != encoded(after)[:8]:
        raise ValueError('Font or style changed')
    return encoded(after)


def validate_layout(before, after, allow_pages=False):
    result=validate_presentation(before,after,allow_pages)
    if lexical(before)!=lexical(after):
        raise ValueError('Layout changed translated words')
    return result


def can_paginate(kind, source):
    # Native continuation has been replayed, but caller support is only inferred
    # for a pre-existing interactive common dialogue. 0067 and 000D dispatch
    # to identical native continuation wrappers (80160a10/80160a18), not static descriptions,
    # buttons, choices, battle announcements or trainer speech.
    return (kind == 'common' and ('{0067}' in source or
            (PAGE in source and '{0027}' in source and '{0028}' in source)) and not re.search(r'\{000[23]:|\{8011\}|[▼▽]', source))


def protected_words(body, names):
    sentinel = '\ue000'
    if sentinel in body:
        raise ValueError('Unexpected private character')
    multi = sorted((n for n in names if ' ' in n), key=len, reverse=True)
    if multi:
        pattern = r'(?<!\w)(?:' + '|'.join(re.escape(n) for n in multi) + r')(?!\w)'
        body = re.sub(pattern, lambda m: m[0].replace(' ', sentinel), body)
    return [word.replace(sentinel, ' ') for word in body.split()]


def paginate_words(prefix, lead, words, width, height, metrics, continuation):
    """Prefer sentence boundaries and avoid nearly empty trailing pages."""
    count = len(words)
    best = {count: ((0, 0), [])}
    for start in range(count - 1, -1, -1):
        lines = ['']
        first = lead if start == 0 else ''
        for end in range(start + 1, count + 1):
            word = words[end - 1]
            trial = (lines[-1] + ' ' + word).strip()
            def measure(value):
                value = first + value
                if start == 0 and continuation and value.startswith('\n'):
                    value = value[1:]
                return metrics(prefix + value)
            if lines[-1] and measure('\n'.join(lines[:-1] + [trial]))[0] > width:
                lines.append(word)
            else:
                lines[-1] = trial
            body = '\n'.join(lines)
            w,h = measure(body)
            if w > width or h > height:
                break
            if end not in best:
                continue
            visible = TOKEN.sub('', first + body).split()
            penalty = 100 if len(visible) < 4 and count >= 6 else 0
            if end != count:
                previous = TOKEN.sub('', words[end - 1])
                following = TOKEN.sub('', words[end]).lower().strip('.,;:!?')
                if not re.search(r'[.!?:;]$', previous):
                    penalty += 5
                if following in {'de','do','da','dos','das','e','ou','com','para','por'}:
                    penalty += 12
            cost = (1 + best[end][0][0], penalty + best[end][0][1])
            if start not in best or cost < best[start][0]:
                best[start] = (cost, [first + body] + best[end][1])
    if 0 not in best:
        return None
    output = ''; speaking = False
    for index, page in enumerate(best[0][1]):
        output += page
        for token in TOKEN.findall(page):
            if token == '{0027}': speaking = True
            elif token == '{0028}': speaking = False
        if index + 1 < len(best[0][1]):
            output += ('{0028}' + PAGE + '\n{0027}') if speaking else (PAGE + '\n')
    return output


def reflow(kind, index, original, translated, metrics, names=()):
    prefix = FONT.match(original)
    if not prefix:
        return translated, dict(status='manual-no-font', pages=[])
    prefix = prefix[0]
    source_pages, target_pages = original.split(PAGE), translated.split(PAGE)
    if len(source_pages) != len(target_pages):
        raise ValueError('Baseline page structure differs from original')
    paginate = can_paginate(kind, original)
    dialogue_frame = None
    if paginate:
        # Continuation keeps the same native frame/coordinates. Its capacity
        # is evidenced by all pages of THIS message, never an unrelated menu.
        sizes = []
        for n, page in enumerate(source_pages):
            if not TOKEN.sub('',page).strip(): continue
            if n and page.startswith('\n'): page=page[1:]
            sizes.append(metrics(prefix+page))
        if sizes:
            dialogue_frame=(min(max(w for w,h in sizes),380),max(h for w,h in sizes))
    output, cases = [], []
    for number, (source, target) in enumerate(zip(source_pages, target_pages)):
        if not TOKEN.sub('', source).strip():
            output.append(target)
            continue
        def measure(text, continuation=number > 0):
            # The native advance handler consumes one leading newline.
            if continuation and text.startswith('\n'):
                text = text[1:]
            return metrics(prefix + text)
        sw, sh = measure(source)
        width, height = sw, sh
        if kind == 'common':
            width = COMMON_WIDTHS.get(index, width)
        if kind == 'battle' and prefix.startswith('{F006}'):
            width = max(sw, 240)
            height = max(sh, metrics(prefix + 'M')[1] * 2)
        if dialogue_frame is not None:
            width,height=dialogue_frame
        before = measure(target)
        if before[0] <= width and before[1] <= height:
            output.append(target)
            cases.append(dict(page=number, before=before, after=before, width=width, height=height, changed=False))
            continue
        # Repeated alignment controls have explicit baselines. Never flatten
        # them, add a page, remove indentation, or wrap a button automatically.
        if '{0003:' in source or '{8011}' in source:
            fixed = preserve_alignment_breaks(source, target)
            after = measure(fixed)
            okay = after[0] <= width and after[1] <= height
        else:
            lead = LEAD.match(target)[0]
            labels = {m[1] for m in re.finditer(r'\{0005:0001\}(.*?)\{0005:0005\}', target, re.S)}
            words = protected_words(target[len(lead):], set(names) | labels)
            lines = ['']
            for word in words:
                trial = (lines[-1] + ' ' + word).strip()
                if lines[-1] and measure(lead + '\n'.join(lines[:-1] + [trial]))[0] > width:
                    lines.append(word)
                else:
                    lines[-1] = trial
            fixed = lead + '\n'.join(lines)
            after = measure(fixed)
            okay = after[0] <= width and after[1] <= height
            if not okay and paginate and after[0] <= width:
                paginated = paginate_words(prefix, lead, words, width, height, metrics, number > 0)
                if paginated is not None:
                    fixed = paginated
                sizes = [measure(p, continuation=number > 0 or k > 0) for k, p in enumerate(fixed.split(PAGE))]
                okay = all(w <= width and h <= height for w, h in sizes)
                after = (max(w for w,h in sizes), max(h for w,h in sizes))
        if okay:
            output.append(fixed)
        else:
            # Apply a safe width-only improvement only if height is not worse.
            # Otherwise retain the prior text and require editorial review.
            output.append(fixed if after[0] <= width and after[1] <= before[1] else target)
        result = output[-1]
        cases.append(dict(page=number, before=before, after=after, width=width, height=height,
                          fits=okay, changed=result != target, extra_pages=result.count(PAGE)))
    result = PAGE.join(output)
    validate_layout(translated, result, allow_pages=paginate)
    unresolved = any(not p.get('fits', True) for p in cases)
    return result, dict(status='needs-editorial-review' if unresolved else 'bounded', pages=cases,
                        extra_pages=result.count(PAGE)-translated.count(PAGE), pagination_allowed=paginate)
