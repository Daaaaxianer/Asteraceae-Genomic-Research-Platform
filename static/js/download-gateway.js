/* Keep existing one-click downloads while routing file access through the API. */
(function () {
    'use strict';
    if (window.AGRPDownloads) return;
    const config = window.AGRPDownloadConfig || { roots: [], rules: [] };
    const rules = config.rules.map(function (rule) {
        return Object.assign({}, rule, { pattern: new RegExp(rule.regex) });
    });
    const nativeFetch = window.fetch.bind(window);
    const nativeClick = HTMLAnchorElement.prototype.click;
    const nativeDispatch = HTMLAnchorElement.prototype.dispatchEvent;
    const nativeCreate = URL.createObjectURL.bind(URL);
    const nativeRevoke = URL.revokeObjectURL.bind(URL);
    const nativeBlob = Response.prototype.blob;
    const objects = new Map();
    const controlled = new WeakSet();
    const pageToken = new URL(location.href).searchParams.get('access_token');

    function url(value, navigation, method) {
        let selected;
        try { selected = new URL(value, document.baseURI); } catch (_) { return value; }
        if (selected.protocol !== 'http:' && selected.protocol !== 'https:') return value;
        if (selected.origin !== location.origin) return value;
        let path = selected.pathname;
        if (path.indexOf('/tools/sequenceserver-app/download/') === 0 ||
            (path === '/tools/sequenceserver-app/get_sequence' && (method || 'GET').toUpperCase() === 'POST')) {
            path = '/api/download/service/sequenceserver/' + path.slice('/tools/sequenceserver-app/'.length);
        } else if (path.indexOf('/tools/jbrowse/') === 0 && /\.(?:json|fa|fasta|fna|gff3?|gtf|bed|bam|bai|cram|crai|vcf|tbi|csi|bw|bigwig|bb|bigbed|2bit|gz|bgz|fai|gzi|ix|ixx)$/i.test(path)) {
            path = (navigation ? '/api/download/public/jbrowse/' : '/api/files/public/jbrowse/') + path.slice('/tools/jbrowse/'.length);
        } else if (path.indexOf('/static/') === 0 && config.roots.indexOf(path.split('/')[2]) !== -1) {
            path = (navigation ? '/api/download/public/static/' : '/api/files/public/static/') + path.slice(8);
        } else if (navigation && path.indexOf('/static/image/') === 0 && /\.(?:png|jpe?g|gif|svg|pdf|webp)$/i.test(path)) {
            path = '/api/download/public/static_assets/' + path.slice(8);
        } else if (path.indexOf('/file_keep/') === 0) {
            path = (navigation ? '/api/download/result/' : '/api/files/result/') + path.slice(11);
        } else if (navigation && path.indexOf('/api/files/public/') === 0) {
            path = path.replace('/api/files/public/', '/api/download/public/');
        } else if (navigation && path.indexOf('/api/files/result/') === 0) {
            path = path.replace('/api/files/result/', '/api/download/result/');
        } else if (path.indexOf('/api/') !== 0) {
            const rule = rules.find(function (entry) { return entry.pattern.test(path); });
            if (rule && (rule.download || (rule.run && (method || 'GET').toUpperCase() === 'POST') ||
                (rule.export && selected.searchParams.get('export') === 'tsv'))) path = '/api/download' + path;
        }
        selected.pathname = path;
        if (pageToken && /^[0-9a-f]{64}$/.test(pageToken) &&
            (/\/api\/(?:download|files)\/result\//.test(path) || /(?:job_(?:status|result|download)|interproscan_(?:result|download)|ancestral_ks_dotplot_|wgdi.*(?:status|download))/.test(path))) {
            if (!selected.searchParams.has('access_token')) selected.searchParams.set('access_token', pageToken);
        }
        return selected.pathname + selected.search + selected.hash;
    }

    Response.prototype.blob = async function () {
        const result = await nativeBlob.call(this);
        try {
            const source = new URL(this.url, location.href);
            if (source.origin === location.origin && source.pathname.indexOf('/api/download/') === 0) controlled.add(result);
        } catch (_) { /* Synthetic responses have no URL. */ }
        return result;
    };
    URL.createObjectURL = function (object) {
        const value = nativeCreate(object);
        if (object instanceof Blob) objects.set(value, object);
        return value;
    };
    URL.revokeObjectURL = function (value) { objects.delete(value); return nativeRevoke(value); };

    window.fetch = async function (input, options) {
        const original = input instanceof Request ? input.url : String(input);
        const mapped = url(original, false, options && options.method || input.method || 'GET');
        if (input instanceof Request) {
            if (new URL(mapped, location.href).href === input.url) return nativeFetch(input, options);
            const init = {
                method: input.method, headers: input.headers, mode: input.mode,
                credentials: input.credentials, cache: input.cache, redirect: input.redirect,
                referrer: input.referrer, referrerPolicy: input.referrerPolicy,
                integrity: input.integrity, keepalive: input.keepalive, signal: input.signal
            };
            // A raw ReadableStream body would require HTTP/2 in Chromium.
            // Blob preserves multipart bytes and a known length over HTTP/1.1.
            if (input.body && !(options && options.body)) init.body = await input.clone().blob();
            return nativeFetch(mapped, Object.assign(init, options));
        }
        return nativeFetch(mapped, options);
    };
    const nativeOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function (method, target) {
        const args = Array.from(arguments);
        args[1] = url(String(target), false, method);
        this.addEventListener('load', function () {
            if (this.response instanceof Blob && String(this.responseURL).indexOf('/api/download/') !== -1) controlled.add(this.response);
        }, { once: true, capture: true });
        return nativeOpen.apply(this, args);
    };

    function showError() {
        let alert = document.getElementById('agrp-download-error');
        if (!alert) {
            alert = document.createElement('div');
            alert.id = 'agrp-download-error';
            alert.setAttribute('role', 'alert');
            alert.style.cssText = 'position:fixed;bottom:20px;right:20px;max-width:360px;padding:12px 16px;background:#fff;color:#9d2525;border:1px solid #bd6262;border-radius:6px;z-index:2147483647';
            document.body.appendChild(alert);
        }
        alert.textContent = 'Download could not be completed. Please retry shortly.';
    }

    async function exportBlob(blob, filename) {
        try {
            const form = new FormData();
            form.append('file', blob, filename || 'export.txt');
            const response = await nativeFetch('/api/download/export/', { method: 'POST', body: form, credentials: 'same-origin' });
            if (!response.ok) throw new Error('Export rejected');
            const result = await response.blob();
            controlled.add(result);
            const link = document.createElement('a');
            const object = nativeCreate(result);
            link.href = object;
            link.download = filename || 'export.txt';
            link.dataset.agrpReady = '1';
            document.body.appendChild(link);
            nativeClick.call(link);
            link.remove();
            setTimeout(function () { nativeRevoke(object); }, 1000);
        } catch (_) { showError(); }
    }

    function prepare(link) {
        if (link.dataset.agrpReady || !link.href) return false;
        const href = link.href;
        const blob = objects.get(href);
        if (blob) {
            if (!controlled.has(blob)) { exportBlob(blob, link.download); return true; }
            return false;
        }
        if (href.indexOf('data:') === 0 && link.hasAttribute('download')) {
            nativeFetch(href).then(function (r) { return r.blob(); }).then(function (b) { return exportBlob(b, link.download); }).catch(showError);
            return true;
        }
        const mapped = url(href, true, 'GET');
        if (mapped !== href) link.href = mapped;
        return false;
    }
    HTMLAnchorElement.prototype.click = function () { if (!prepare(this)) return nativeClick.call(this); };
    HTMLAnchorElement.prototype.dispatchEvent = function (event) {
        if (event.type === 'click' && prepare(this)) return true;
        return nativeDispatch.call(this, event);
    };
    document.addEventListener('click', function (event) {
        const link = event.target.closest && event.target.closest('a');
        if (link && prepare(link)) { event.preventDefault(); event.stopImmediatePropagation(); }
    }, true);

    function prepareForm(form) { form.action = url(form.action, false, form.method || 'GET'); }
    const nativeSubmit = HTMLFormElement.prototype.submit;
    HTMLFormElement.prototype.submit = function () { prepareForm(this); return nativeSubmit.call(this); };
    document.addEventListener('submit', function (event) { if (event.target instanceof HTMLFormElement) prepareForm(event.target); }, true);
    const nativeWindowOpen = window.open;
    window.open = function (target) {
        const args = Array.from(arguments);
        if (target) args[0] = url(String(target), true, 'GET');
        return nativeWindowOpen.apply(window, args);
    };
    function rewriteNodes(root) {
        const nodes = [];
        if (root.matches && root.matches('a[href],form[action],img[src],iframe[src],source[src]')) nodes.push(root);
        if (root.querySelectorAll) nodes.push.apply(nodes, root.querySelectorAll('a[href],form[action],img[src],iframe[src],source[src]'));
        nodes.forEach(function (node) {
            if (node instanceof HTMLFormElement) prepareForm(node);
            else if (node instanceof HTMLAnchorElement) {
                if (!/^(?:blob:|data:)/.test(node.href)) node.href = url(node.href, true, 'GET');
            } else if (node.src) node.src = url(node.src, false, 'GET');
        });
    }
    function start() {
        rewriteNodes(document);
        new MutationObserver(function (changes) {
            changes.forEach(function (change) { change.addedNodes.forEach(function (node) { if (node.nodeType === 1) rewriteNodes(node); }); });
        }).observe(document.documentElement, { childList: true, subtree: true });
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true }); else start();
    window.AGRPDownloads = { url: url };
}());
