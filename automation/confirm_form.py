"""Read-only discovery for the upload confirmation -> description transition."""

CONFIRM_FORM_SNAPSHOT = r"""
const normalize = value => (value || '').replace(/\s+/g, ' ').trim();
const parent = node => node.parentElement || node.getRootNode()?.host || null;
function nodes(root) {
    const result = [];
    for (const node of root.querySelectorAll('*')) {
        result.push(node);
        if (node.shadowRoot) result.push(...nodes(node.shadowRoot));
    }
    return result;
}
function inside(root, node) {
    for (let item = node; item; item = parent(item)) {
        if (item === root) return true;
    }
    return false;
}
function visible(node) {
    if (!node.isConnected || !node.getClientRects().length) return false;
    for (let item = node; item; item = parent(item)) {
        const style = getComputedStyle(item);
        if (item.hidden || item.hasAttribute('inert') ||
            item.getAttribute('aria-hidden') === 'true' ||
            style.display === 'none' || style.visibility === 'hidden' ||
            style.opacity === '0') return false;
    }
    return true;
}
function disabled(node) {
    for (let item = node; item; item = parent(item)) {
        if (item.disabled || item.hasAttribute('disabled') ||
            item.getAttribute('aria-disabled') === 'true' ||
            item.getAttribute('aria-busy') === 'true' ||
            (item.hasAttribute('loading') && item.getAttribute('loading') !== 'false')) return true;
    }
    return false;
}
function label(node) {
    const own = normalize(node.innerText || node.textContent || node.getAttribute('aria-label'));
    if (own) return own;
    const host = node.getRootNode()?.host;
    // The supplied ks-button markup puts its label in a light-DOM slot.
    return host && (host.localName.startsWith('ks-button') || host.matches('.KsButton'))
        ? normalize(host.textContent || host.getAttribute('aria-label')) : '';
}
const shown = nodes(document).filter(visible);
const titles = shown.filter(node => /^Tải video lên(?:\s*\(\d+\))?$/.test(normalize(node.textContent)) &&
    !node.matches('button, [role="button"], [role="menuitem"], a'));
const step3 = shown.filter(node => /^Bước\s*3\s*\/\s*3\s*:/.test(normalize(node.textContent)) &&
    !Array.from(node.children).some(child => /^Bước\s*3\s*\/\s*3\s*:/.test(normalize(child.textContent))));
const buttons = shown.filter(node => node.matches('button, [role="button"]'));
function uploadScope(button) {
    for (let scope = parent(button); scope && scope !== document.body && scope !== document.documentElement;
         scope = parent(scope)) {
        if (titles.some(title => inside(scope, title)) || step3.some(marker => inside(scope, marker))) return scope;
    }
    return null;
}
// Prefer the inner native button over a role=button custom host; never match substrings.
const confirmations = buttons.filter(button => label(button) === 'Xác nhận' && uploadScope(button))
    .filter(button => !buttons.some(other => other !== button && inside(button, other) && label(other) === 'Xác nhận'));
const active = confirmations.filter(button => !step3.length || step3.some(marker => inside(uploadScope(button), marker)));
const ready = active.filter(button => !disabled(button));
const formScopes = [...new Set(buttons.filter(button => label(button) === 'Lưu').map(uploadScope).filter(Boolean))];
const fields = shown.filter(node => node.matches('textarea, input, [contenteditable="true"]') &&
    !disabled(node) && !node.readOnly && formScopes.some(scope => inside(scope, node)));
function descriptionLabel(node) {
    const host = node.getRootNode()?.host;
    return [node, host].filter(Boolean).map(item =>
        [item.getAttribute('placeholder'), item.getAttribute('aria-label')].join(' ')).join(' ');
}
const named = fields.filter(node => /mô tả|nội dung sáng tạo|description/i.test(descriptionLabel(node)));
const descriptions = named.length ? named : fields.filter(node => node.matches('textarea, [contenteditable="true"]'));
const formReady = !step3.length && !confirmations.length && formScopes.length === 1 && descriptions.length === 1;
return {
    confirm: active.length === 1 && ready.length === 1 ? ready[0] : null,
    description: formReady ? descriptions[0] : null,
    formReady,
    step3Visible: !!step3.length,
    confirmCount: active.length,
    readyConfirmCount: ready.length,
    descriptionCount: descriptions.length
};
"""

SET_DESCRIPTION = r"""
const node = arguments[0], value = arguments[1];
node.focus();
if (node.isContentEditable) {
    node.textContent = value;
} else {
    const proto = node instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
    setter.call(node, value);
}
node.dispatchEvent(new InputEvent('input', {bubbles: true, composed: true, inputType: 'insertText', data: value}));
node.dispatchEvent(new Event('change', {bubbles: true, composed: true}));
return (node.isContentEditable ? node.textContent : node.value) === value;
"""

# Chrome can report a slotted label's own host as intercepting its inner button.
# Allow pointer actions only when hit testing every shadow boundary proves that
# no unrelated overlay would receive the click. This script does not click.
CONFIRM_POINTER_SAFE = r"""
const button = arguments[0];
if (!button.isConnected) return false;
for (let node = button; node; node = node.parentElement || node.getRootNode()?.host || null) {
    const style = getComputedStyle(node);
    if (node.disabled || node.hasAttribute('disabled') || node.hidden || node.hasAttribute('inert') ||
        node.getAttribute('aria-disabled') === 'true' || node.getAttribute('aria-busy') === 'true' ||
        node.getAttribute('aria-hidden') === 'true' || style.display === 'none' ||
        style.visibility === 'hidden' || style.opacity === '0' ||
        (node.hasAttribute('loading') && node.getAttribute('loading') !== 'false')) return false;
}
const bounds = button.getBoundingClientRect();
const left = Math.max(0, bounds.left), right = Math.min(innerWidth, bounds.right);
const top = Math.max(0, bounds.top), bottom = Math.min(innerHeight, bounds.bottom);
if (left >= right || top >= bottom || button.disabled) return false;
const x = Math.floor((left + right) / 2), y = Math.floor((top + bottom) / 2);
const roots = [];
for (let root = button.getRootNode(); root; root = root.host ? root.host.getRootNode() : null) roots.unshift(root);
for (let i = 0; i < roots.length; i++) {
    const root = roots[i], hit = root.elementFromPoint(x, y);
    if (i + 1 < roots.length) {
        if (hit !== roots[i + 1].host) return false;
    } else {
        if (hit === button || button.contains(hit)) return true;
        // Slotted text may be retargeted to this exact host, not the inner button.
        return !!root.host && hit === root.host;
    }
}
return false;
"""
