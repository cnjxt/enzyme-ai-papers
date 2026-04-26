---
hide:
  - navigation
  - toc
---

<!-- AUTO-GENERATED. DO NOT EDIT DIRECTLY. -->


<section class="paper-start">
  <nav class="paper-switcher" aria-label="Section navigation">
    
<a class="switch-item" href="../">
  <span class="switch-icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h12v18l-6-3-6 3z"/><path d="M9 8h6M9 11h6"/></svg></span>
  <strong>Weekly</strong>
</a>

    
<a class="switch-item" href="../archive/">
  <span class="switch-icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 5h16v4H4z"/><path d="M6 9h12v10H6z"/><path d="M10 13h4"/></svg></span>
  <strong>Archive</strong>
</a>

    
<a class="switch-item is-active" href="./">
  <span class="switch-icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4v12"/><path d="M7 9l5-5 5 5"/><path d="M5 20h14"/></svg></span>
  <strong>Submit</strong>
</a>

  </nav>
  
<aside class="issue-card">
  <span class="issue-kicker">Latest issue</span>
  <strong>2026-W17</strong>
  <span class="issue-range">2026.4.20-</span>
</aside>

</section>



<section class="submit-panel">
  <form id="paper-submit-form" class="submit-form" data-issue-url="https://github.com/cnjxt/enzyme-ai-papers/issues/new">
    <div>
      <div class="section-label">Submit paper</div>
      <h2>Share a paper URL</h2>
    </div>
    <label for="submit-paper-url">Paper URL</label>
    <input id="submit-paper-url" name="url" type="url" required placeholder="https://doi.org/...">
    <label for="submit-paper-title">Title</label>
    <input id="submit-paper-title" name="title" type="text" placeholder="Optional">
    <label for="submit-paper-note">Why this paper matters</label>
    <textarea id="submit-paper-note" name="note" rows="4" placeholder="Optional"></textarea>
    <label for="submit-paper-tags">Tags</label>
    <input id="submit-paper-tags" name="tags" type="text" placeholder="enzyme design, PLM, wet lab validation">
    <label for="submit-paper-code">Code or project link</label>
    <input id="submit-paper-code" name="code" type="url" placeholder="https://github.com/...">
    <div class="submit-actions">
      <button type="submit">Open GitHub Submission</button>
      <a href="https://github.com/cnjxt/enzyme-ai-papers/issues/new">Open blank issue</a>
    </div>
    <p id="submit-form-status" class="form-status" aria-live="polite"></p>
  </form>
  <aside class="review-boundary">
    <div class="section-label">Review boundary</div>
    <ul>
      <li>Submissions open as GitHub issues under the submitter account.</li>
      <li>The website does not store a GitHub token or write repository data.</li>
      <li>Only maintainers can apply curation labels such as <code>accepted</code>.</li>
      <li>Accepted papers are generated through a pull request and validation checks.</li>
    </ul>
  </aside>
</section>


<section class="info-grid">
  <article class="info-block">
    <h2>Readers</h2>
    <p>Start with the latest weekly issue. Use the archive when you want to browse by tag or keyword.</p>
  </article>
  <article class="info-block">
    <h2>Submitters</h2>
    <p>Open a GitHub issue with a paper URL. Notes, tags, title, code, and project links are optional.</p>
  </article>
  <article class="info-block">
    <h2>Maintainers</h2>
    <p>Review the issue preview, add <code>accepted</code> to include it, and add <code>featured</code> for a weekly pick.</p>
  </article>
</section>

<section class="command-block">
  <h2>Automation</h2>
  <pre><code>Issue opened -> metadata preview
Label accepted -> paper YAML draft + generated weekly digest
Label featured -> Pick of the Week candidate
Pull request -> validation + MkDocs build</code></pre>
</section>
