document.addEventListener('DOMContentLoaded', () => {
    const $ = id => document.getElementById(id);

    // Views
    const vSetup    = $('view-setup');
    const vScanning = $('view-scanning');
    const vResults  = $('view-results');
    const navActs   = $('nav-actions');

    const form = $('scan-form');

    // Progress
    const pf  = $('pf');
    const pp  = $('pp');
    const pm  = $('pm');
    const log = $('term-log');

    // The Docs are now served natively via docs.html

    // Provider Dropdown
    const provider = $('provider');
    const customFields = $('custom-fields');
    provider.addEventListener('change', () => {
        customFields.style.display = provider.value === 'custom' ? 'flex' : 'none';
    });

    const useHibp = $('use-hibp');
    const hibpField = $('hibp-field');
    const hibpKeyInput = $('hibp-key');
    if(useHibp) {
        useHibp.addEventListener('change', () => {
            hibpField.style.display = useHibp.checked ? 'block' : 'none';
            if (hibpKeyInput) hibpKeyInput.required = useHibp.checked;
        });
    }

    // Form Submit
    form.addEventListener('submit', async e => {
        e.preventDefault();

        const email = $('email').value.trim();
        let host = $('host').value;
        let port = $('port').value;
        const password = $('password').value;
        const deep = false;
        const useHibp = $('use-hibp').checked;
        const hibpKey = useHibp ? $('hibp-key').value.trim() : null;

        if (document.getElementById('provider').value !== 'custom') {
            const [h, p] = document.getElementById('provider').value.split('|');
            host = h;
            port = p;
        }

        vSetup.classList.add('hidden');
        vScanning.classList.remove('hidden');

        try {
            const res = await fetch('/api/scan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, host, port, password, deep, hibp_key: hibpKey })
            });

            if (!res.ok) {
                const d = await res.json();
                throw new Error(d.error || 'Scan failed to initialize');
            }

            poll();
        } catch (err) {
            alert(err.message);
            location.reload();
        }
    });

    function appendLog(msg) {
        log.insertAdjacentHTML('beforeend', `> ${msg}<br>`);
        requestAnimationFrame(() => {
            log.scrollTop = log.scrollHeight;
        });
    }

    // Polling
    let lastMsg = '';
    async function poll() {
        try {
            const res = await fetch('/api/status');
            const d = await res.json();

            pf.style.width = d.progress + '%';
            pp.textContent = d.progress + '%';
            pm.textContent = d.message;

            if (d.message !== lastMsg && d.message) {
                appendLog(d.message);
                lastMsg = d.message;
            }

            if (d.status === 'error' || d.status === 'auth_failed') {
                alert('Execution Error: ' + d.message);
                location.reload();
                return;
            }

            if (d.status === 'done') {
                setTimeout(loadResults, 500);
                return;
            }

            setTimeout(poll, 250);
        } catch {
            setTimeout(poll, 1000);
        }
    }

    async function loadResults() {
        try {
            const res = await fetch('/api/results');
            const d = await res.json();
            sessionStorage.setItem('chekreg_dashboard', JSON.stringify(d));
            renderDashboard(d);
            vScanning.classList.add('hidden');
            vResults.classList.remove('hidden');
            navActs.classList.remove('hidden');
        } catch {
            alert('Failed to retrieve footprint payload.');
        }
    }

    // Render Dashboard
    window.renderDashboard = function renderDashboard(d) {
        // Sync calculations perfectly across the board
        let countBreach = d.all_organisations.filter(o => o.is_breached).length;
        let countGhost = d.all_organisations.filter(o => o.is_inactive).length;

        // Stats
        $('r-score').textContent = d.score;
        
        // Insight logic
        const insight = $('r-insight');
        const action = $('r-action');
        
        let actionText = "";

        if (d.score >= 80) {
            insight.textContent = "Excellent";
            insight.style.color = "var(--green)";
            actionText = "Your footprint is minimal. Maintain current habits.";
        } else if (d.score >= 50) {
            insight.textContent = "Needs Attention";
            insight.style.color = "var(--warning)";
            if (countBreach > 0) actionText = `Fix ${countBreach} compromised accounts immediately. `;
            else if (countGhost > 10) actionText = `Delete inactive ghost accounts to reduce attack surface. `;
            else actionText = "Reduce clutter and unsubscribe from unnecessary newsletters.";
        } else {
            insight.textContent = "Critical Risk";
            insight.style.color = "var(--danger)";
            if (countBreach > 0) actionText = `CRITICAL: Resolve ${countBreach} data breaches. `;
            else actionText = `You have ${countGhost} ghost accounts exposing your data. Purge them now.`;
        }

        if(action) action.textContent = actionText;

        $('s-breach').textContent = countBreach;
        // The other stats are updated dynamically inside renderAll to guarantee 100% sync

        renderAll(d.all_organisations);
    }

    function renderAll(orgs) {
        const grid = $('grid-all');
        const filterContainer = $('filter-container');

        if (!orgs || !orgs.length) { 
            grid.innerHTML = '<div class="empty-state">No footprint data resolved.</div>'; 
            return; 
        }

        // Sync buckets using accurate boolean evaluations
        let countGeneral = orgs.filter(o => o.delete_url && !o.unsub_link).length;
        let countNewsletter = orgs.filter(o => (o.is_newsletter || o.unsub_link) && !o.delete_url).length;
        let countHybrid = orgs.filter(o => o.delete_url && o.unsub_link).length;
        let countSpam = orgs.filter(o => o.is_high_volume).length;
        let countGhost = orgs.filter(o => o.is_inactive).length;
        let countBreach = orgs.filter(o => o.is_breached).length;

        // Perfectly sync sidebar numbers
        $('s-orgs').textContent = orgs.length;
        $('s-ghost').textContent = countGhost;
        $('s-news').textContent = countNewsletter + countHybrid;

        filterContainer.innerHTML = `
            <button class="filter-pill active" data-filter="all">All Entities (${orgs.length})</button>
            <button class="filter-pill" data-filter="general">General Accounts (${countGeneral})</button>
            <button class="filter-pill" data-filter="newsletter">Newsletters Only (${countNewsletter})</button>
            <button class="filter-pill" data-filter="hybrid">Hybrid (${countHybrid})</button>
            <button class="filter-pill" data-filter="spam">Spam & Clutter (${countSpam})</button>
            <button class="filter-pill" data-filter="ghost" style="border-color: rgba(250,173,20,0.3); color: var(--warning);">Ghost Accounts (${countGhost})</button>
            <button class="filter-pill" data-filter="breached" style="border-color: rgba(255,77,79,0.3); color: var(--danger);">Breached (${countBreach})</button>
        `;

        let html = '';
        orgs.forEach(o => {
            let tagsHtml = '';
            
            // Labels
            if (o.delete_url && o.unsub_link) tagsHtml += `<span class="ctag cat" title="Provides both Unsubscribe and Deletion URLs">Hybrid</span>`;
            else if (o.delete_url) tagsHtml += `<span class="ctag cat" title="Provides a Direct Deletion URL">General Account</span>`;
            else if (o.unsub_link) tagsHtml += `<span class="ctag cat" title="Provides an Unsubscribe link">Newsletter</span>`;
            else tagsHtml += `<span class="ctag cat" title="No automated links detected">Other</span>`;

            if (o.is_breached) tagsHtml += `<span class="ctag breach" title="Flagged in a known data breach via HIBP">Compromised</span>`;
            if (o.is_inactive) tagsHtml += `<span class="ctag ghost" title="No activity detected in the last 6 months">Ghost</span>`;
            if (o.is_high_volume) tagsHtml += `<span class="ctag ghost" title="Exceptionally high volume of emails received">Spam & Clutter</span>`;

            let actionsHtml = '';
            if (o.delete_url) {
                actionsHtml += `<a href="${o.delete_url}" target="_blank" class="btn btn-danger"><i class="fa-solid fa-trash"></i> Request Deletion</a>`;
            }
            if (o.unsub_link) {
                actionsHtml += `<a href="${o.unsub_link}" target="_blank" class="btn btn-secondary"><i class="fa-solid fa-ban"></i> Unsubscribe</a>`;
            }
            
            // Add Feedback / Flag button to the top right corner
            let flagHtml = '';
            if (o.delete_url || o.unsub_link) {
                const domainStr = encodeURIComponent(o.domains[0] || o.name);
                const issueBody = encodeURIComponent(`The current link for **${o.name}** (\`${o.domains[0] || 'unknown domain'}\`) is outdated or incorrect.\n\n**Current Link:** ${o.delete_url || o.unsub_link}\n**Correct Link:** [Please paste the correct working link here if you know it]`);
                const issueUrl = `https://github.com/taraladka/ChekReg/issues/new?title=Update+Link:+${domainStr}&body=${issueBody}`;
                flagHtml = `<a href="${issueUrl}" target="_blank" title="Report this link as outdated or incorrect" style="color: var(--text-muted); transition: color 0.2s;"><i class="fa-regular fa-flag"></i></a>`;
            }

            let isGen = !!(o.delete_url && !o.unsub_link);
            let isNews = !!((o.unsub_link || o.is_newsletter) && !o.delete_url);
            let isHyb = !!(o.delete_url && o.unsub_link);
            let isSpam = !!o.is_high_volume;
            let isGhost = !!o.is_inactive;
            let isBreached = !!o.is_breached;

            html += `
                <div class="data-card fcard" data-general="${isGen}" data-newsletter="${isNews}" data-hybrid="${isHyb}" data-spam="${isSpam}" data-ghost="${isGhost}" data-breach="${isBreached}">
                    <div>
                        <div class="card-top">
                            <div class="org-title">
                                <h4>${o.name}</h4>
                                <span class="org-domain">${o.domains[0] || ''}</span>
                            </div>
                            ${flagHtml}
                        </div>
                        <div class="tags-area">${tagsHtml}</div>
                    </div>
                    ${actionsHtml ? `<div class="card-actions">${actionsHtml}</div>` : ''}
                </div>
            `;
        });

        grid.innerHTML = html;

        // Filter behavior
        const hibpKeyInput = document.getElementById('hibp-key');
        
        function applyFilters() {
            const activeBtn = document.querySelector('.filter-pill.active');
            const f = activeBtn ? activeBtn.dataset.filter : 'all';
            
            const currentSearchInput = document.getElementById('org-search');
            const query = currentSearchInput ? currentSearchInput.value.toLowerCase().trim() : '';
            
            let visibleCount = 0;
            document.querySelectorAll('.fcard').forEach(c => {
                let showFilter = false;
                if (f === 'all') showFilter = true;
                else if (f === 'general' && c.dataset.general === 'true') showFilter = true;
                else if (f === 'newsletter' && c.dataset.newsletter === 'true') showFilter = true;
                else if (f === 'hybrid' && c.dataset.hybrid === 'true') showFilter = true;
                else if (f === 'spam' && c.dataset.spam === 'true') showFilter = true;
                else if (f === 'ghost' && c.dataset.ghost === 'true') showFilter = true;
                else if (f === 'breached' && c.dataset.breach === 'true') showFilter = true;
                
                let showSearch = true;
                if (query) {
                    const title = c.querySelector('h4').textContent.toLowerCase();
                    const domain = c.querySelector('.org-domain').textContent.toLowerCase();
                    showSearch = title.includes(query) || domain.includes(query);
                }
                
                const show = showFilter && showSearch;
                c.style.display = show ? 'flex' : 'none';
                if (show) visibleCount++;
            });

            // Empty State Logic
            const existingEmpty = grid.querySelector('.empty-state');
            if (existingEmpty) existingEmpty.remove();

            if (visibleCount === 0) {
                const msg = document.createElement('div');
                msg.className = 'empty-state';
                msg.style.width = '100%';
                msg.style.gridColumn = '1 / -1';
                
                if (f === 'breached' && !query) {
                    const noKey = !document.getElementById('use-hibp').checked || !hibpKeyInput.value.trim();
                    if (noKey) {
                        msg.innerHTML = `
                            <p style="margin-bottom:1rem;">No security breaches detected.</p>
                            <p style="font-size:0.85rem; color:var(--text-muted);">
                                Did you skip the HIBP API Key? You can manually check your footprint for breaches at 
                                <a href="https://haveibeenpwned.com" target="_blank" style="color:var(--green); text-decoration:underline;">haveibeenpwned.com</a>
                            </p>
                        `;
                    } else {
                        msg.innerHTML = '<p>Excellent! No security breaches detected.</p>';
                    }
                } else {
                    msg.innerHTML = '<p>No results found matching your criteria.</p>';
                }
                grid.appendChild(msg);
            }
        }

        const searchInput = document.getElementById('org-search');
        if (searchInput) {
            searchInput.oninput = applyFilters;
        }

        document.querySelectorAll('.filter-pill').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.filter-pill').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                applyFilters();
            });
        });
    }

    // Restore state from sessionStorage if navigating back from Docs
    try {
        const cached = sessionStorage.getItem('chekreg_dashboard');
        if (cached) {
            const d = JSON.parse(cached);
            renderDashboard(d);
            vSetup.classList.add('hidden');
            vResults.classList.remove('hidden');
            navActs.classList.remove('hidden');
        }
    } catch(e) {}
});
