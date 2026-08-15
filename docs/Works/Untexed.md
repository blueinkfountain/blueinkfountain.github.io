---
layout: default
title: Handwritten notes
has_children: true
nav_order: 3
---

# Handwritten notes yet to be TeXed.


{% assign pdf_files = site.static_files
  | where_exp: "item", "item.path contains '/untexed/'"
  | sort: "path"
%}


{% assign dates = "" | split: "" %}


{% for file in pdf_files %}

  {% if file.extname == ".pdf" or file.extname == ".PDF" %}

    {% assign parts = file.path | split: "/" %}
    {% assign file_date = parts[2] %}

    {% unless dates contains file_date %}
      {% assign dates = dates | push: file_date %}
    {% endunless %}

  {% endif %}

{% endfor %}


{% assign dates = dates | sort | reverse %}
{% assign latest_date = dates[0] %}
{% assign latest_record = site.data.untexed_records[latest_date] %}

{% assign latest_prefix = "/untexed/"
  | append: latest_date
  | append: "/"
%}



<div class="academic-tree-container">


  {%- comment -%}
  =========================================================
  Total Ink
  =========================================================
  {%- endcomment -%}

  {% if latest_record %}
    {% unless latest_record.baseline %}

      <div class="overall-ink-banner">

        <span class="overall-ink-label">
          Total Ink
        </span>

        <span class="overall-ink-value">
          {{ latest_record.library_total_ink_percent }}% ink
        </span>

      </div>

    {% endunless %}
  {% endif %}



  {%- comment -%}
  =========================================================
  Latest folders
  =========================================================
  {%- endcomment -%}

  {% assign latest_folders = "" | split: "" %}

  {% for file in pdf_files %}

    {% if file.extname == ".pdf" or file.extname == ".PDF" %}

      {% assign parts = file.path | split: "/" %}
      {% assign file_date = parts[2] %}

      {% if file_date == latest_date %}

        {% assign folder_parts = "" | split: "" %}

        {% for part in parts %}
          {% if forloop.index > 3 and forloop.last == false %}
            {% assign folder_parts = folder_parts | push: part %}
          {% endif %}
        {% endfor %}

        {% capture folder_name %}
          {{ folder_parts | join: " / " }}
        {% endcapture %}

        {% assign folder_name = folder_name | strip %}

        {% if folder_name == "" %}
          {% assign folder_name = "General" %}
        {% endif %}

        {% unless latest_folders contains folder_name %}
          {% assign latest_folders = latest_folders | push: folder_name %}
        {% endunless %}

      {% endif %}

    {% endif %}

  {% endfor %}



  {%- comment -%}
  =========================================================
  Latest main view
  =========================================================
  {%- endcomment -%}

  {% assign last_subject = "" %}

  {% for folder in latest_folders %}

    {% assign subject_parts = folder | split: " / " %}
    {% assign current_subject = subject_parts[0] %}

    {%- comment -%}
    Subject heading
    {%- endcomment -%}

    {% if current_subject != last_subject %}

      {% assign subject_ink = nil %}

      {% if latest_record %}
        {% if latest_record.subject_ink_percent %}
          {% assign subject_ink = latest_record.subject_ink_percent[current_subject] %}
        {% endif %}
      {% endif %}

      <div class="subject-divider">

        <div class="subject-heading-row">

          <div class="subject-title">
            {{ current_subject | replace: "_", " " }}
          </div>

          {% if subject_ink %}
            {% if subject_ink > 0 %}
              <span class="subject-ink">
                +{{ subject_ink }}% ink
              </span>
            {% endif %}
          {% endif %}

        </div>

      </div>

      {% assign last_subject = current_subject %}

    {% endif %}



    {%- comment -%}
    Folder subtotal
    IMPORTANT:
    folder_ink_percent key는 "Algebra/1. Linear Algebra" 꼴이므로
    "Algebra / 1. Linear Algebra" -> "Algebra/1. Linear Algebra" 로 변환해서 lookup
    {%- endcomment -%}

    {% assign raw_folder_key = folder | replace: " / ", "/" %}
    {% assign folder_ink = nil %}

    {% if latest_record %}
      {% if latest_record.folder_ink_percent %}
        {% assign folder_ink = latest_record.folder_ink_percent[raw_folder_key] %}
      {% endif %}
    {% endif %}


    <details class="academic-folder">

      <summary class="folder-summary">

        <span class="folder-label">
          {{ folder | replace: "_", " " }}
        </span>

        {% if folder_ink %}
          {% if folder_ink > 0 %}
            <span class="folder-ink">
              +{{ folder_ink }}% ink
            </span>
          {% endif %}
        {% endif %}

      </summary>


      <ul class="file-list">

        {% for file in pdf_files %}

          {% if file.extname == ".pdf" or file.extname == ".PDF" %}

            {% assign parts = file.path | split: "/" %}
            {% assign file_date = parts[2] %}

            {% if file_date == latest_date %}

              {% assign current_folder_parts = "" | split: "" %}

              {% for part in parts %}
                {% if forloop.index > 3 and forloop.last == false %}
                  {% assign current_folder_parts = current_folder_parts | push: part %}
                {% endif %}
              {% endfor %}

              {% capture current_folder %}
                {{ current_folder_parts | join: " / " }}
              {% endcapture %}

              {% assign current_folder = current_folder | strip %}

              {% if current_folder == "" %}
                {% assign current_folder = "General" %}
              {% endif %}


              {% if current_folder == folder %}

                {% assign raw_relative_path = file.path | remove_first: latest_prefix %}

                {% assign file_ink = nil %}

                {% if latest_record %}
                  {% if latest_record.file_ink_percent %}
                    {% assign file_ink = latest_record.file_ink_percent[raw_relative_path] %}
                  {% endif %}
                {% endif %}


                <li class="file-item">

                  <a
                    href="{{ file.path | relative_url }}"
                    target="_blank"
                    class="file-link"
                  >
                    {{ file.basename }}
                  </a>

                  {% if file_ink %}
                    {% if file_ink > 0 %}
                      <span class="file-ink">
                        +{{ file_ink }}% ink
                      </span>
                    {% endif %}
                  {% endif %}

                </li>

              {% endif %}

            {% endif %}

          {% endif %}

        {% endfor %}

      </ul>

    </details>

  {% endfor %}



  {%- comment -%}
  =========================================================
  Latest Record
  =========================================================
  {%- endcomment -%}

  {% if latest_record %}

    <details class="change-record latest-record">

      <summary class="record-summary">

        <span>
          Record
        </span>

        {% unless latest_record.baseline %}
          <span class="record-total-ink">
            +{{ latest_record.total_ink_percent }}% ink
          </span>
        {% endunless %}

      </summary>


      <div class="record-content">

        {% if latest_record.baseline %}

          <div class="record-note">
            Baseline snapshot — no earlier version to compare.
          </div>

        {% else %}

          {% assign has_added = latest_record.added.size %}
          {% assign has_modified = latest_record.modified.size %}
          {% assign has_moved = latest_record.moved_renamed.size %}
          {% assign has_deleted = latest_record.deleted.size %}

          {% if has_added == 0 and has_modified == 0 and has_moved == 0 and has_deleted == 0 %}
            <div class="record-note">
              No changes detected from the previous snapshot.
            </div>
          {% endif %}


          {% if latest_record.added.size > 0 %}

            <div class="record-section">

              <div class="record-label">
                Added
              </div>

              <ul class="record-list">

                {% for item in latest_record.added %}
                  <li class="record-added">

                    <span class="record-path">
                      {{ item.path }}
                    </span>

                    <span class="ink-added">
                      +{{ item.ink_added_percent }}% ink
                    </span>

                  </li>
                {% endfor %}

              </ul>

            </div>

          {% endif %}



          {% if latest_record.modified.size > 0 %}

            <div class="record-section">

              <div class="record-label">
                Modified
              </div>

              <ul class="record-list">

                {% for item in latest_record.modified %}
                  <li class="record-modified">

                    <span class="record-path">
                      {{ item.path }}
                    </span>

                    <span class="ink-added">
                      +{{ item.ink_added_percent }}% ink
                    </span>

                  </li>
                {% endfor %}

              </ul>

            </div>

          {% endif %}



          {% if latest_record.moved_renamed.size > 0 %}

            <div class="record-section">

              <div class="record-label">
                Moved / Renamed
              </div>

              <ul class="record-list">

                {% for move in latest_record.moved_renamed %}
                  <li class="record-moved">

                    <span class="record-move-from">
                      {{ move.from }}
                    </span>

                    <span class="record-arrow">
                      →
                    </span>

                    <span class="record-move-to">
                      {{ move.to }}
                    </span>

                    {% if move.ink_added_percent > 0 %}
                      <span class="ink-added">
                        +{{ move.ink_added_percent }}% ink
                      </span>
                    {% endif %}

                  </li>
                {% endfor %}

              </ul>

            </div>

          {% endif %}



          {% if latest_record.deleted.size > 0 %}

            <div class="record-section">

              <div class="record-label">
                Removed
              </div>

              <ul class="record-list">

                {% for path in latest_record.deleted %}
                  <li class="record-deleted">
                    {{ path }}
                  </li>
                {% endfor %}

              </ul>

            </div>

          {% endif %}

        {% endif %}

      </div>

    </details>

  {% endif %}



  {%- comment -%}
  =========================================================
  Previous versions
  =========================================================
  {%- endcomment -%}

  {% if dates.size > 1 %}

    <details class="previous-versions">

      <summary class="previous-summary">
        Previous versions
      </summary>


      <div class="previous-version-list">

        {% for date in dates %}

          {% unless date == latest_date %}

            <details class="version-folder">

              <summary class="version-summary">
                {{ date }}
              </summary>


              <div class="version-content">

                {% assign version_record = site.data.untexed_records[date] %}

                <div class="record-static">

                  <div class="record-heading">

                    <span>
                      Record
                    </span>

                    {% if version_record %}
                      {% unless version_record.baseline %}
                        <span class="record-total-ink">
                          +{{ version_record.total_ink_percent }}% ink
                        </span>
                      {% endunless %}
                    {% endif %}

                  </div>


                  <div class="record-content">

                    {% if version_record %}

                      {% if version_record.baseline %}

                        <div class="record-note">
                          Baseline snapshot — no earlier version to compare.
                        </div>

                      {% else %}

                        {% assign has_added = version_record.added.size %}
                        {% assign has_modified = version_record.modified.size %}
                        {% assign has_moved = version_record.moved_renamed.size %}
                        {% assign has_deleted = version_record.deleted.size %}

                        {% if has_added == 0 and has_modified == 0 and has_moved == 0 and has_deleted == 0 %}
                          <div class="record-note">
                            No changes detected from the previous snapshot.
                          </div>
                        {% endif %}


                        {% if version_record.added.size > 0 %}

                          <div class="record-section">

                            <div class="record-label">
                              Added
                            </div>

                            <ul class="record-list">

                              {% for item in version_record.added %}
                                <li class="record-added">

                                  <span class="record-path">
                                    {{ item.path }}
                                  </span>

                                  <span class="ink-added">
                                    +{{ item.ink_added_percent }}% ink
                                  </span>

                                </li>
                              {% endfor %}

                            </ul>

                          </div>

                        {% endif %}



                        {% if version_record.modified.size > 0 %}

                          <div class="record-section">

                            <div class="record-label">
                              Modified
                            </div>

                            <ul class="record-list">

                              {% for item in version_record.modified %}
                                <li class="record-modified">

                                  <span class="record-path">
                                    {{ item.path }}
                                  </span>

                                  <span class="ink-added">
                                    +{{ item.ink_added_percent }}% ink
                                  </span>

                                </li>
                              {% endfor %}

                            </ul>

                          </div>

                        {% endif %}



                        {% if version_record.moved_renamed.size > 0 %}

                          <div class="record-section">

                            <div class="record-label">
                              Moved / Renamed
                            </div>

                            <ul class="record-list">

                              {% for move in version_record.moved_renamed %}
                                <li class="record-moved">

                                  <span class="record-move-from">
                                    {{ move.from }}
                                  </span>

                                  <span class="record-arrow">
                                    →
                                  </span>

                                  <span class="record-move-to">
                                    {{ move.to }}
                                  </span>

                                  {% if move.ink_added_percent > 0 %}
                                    <span class="ink-added">
                                      +{{ move.ink_added_percent }}% ink
                                    </span>
                                  {% endif %}

                                </li>
                              {% endfor %}

                            </ul>

                          </div>

                        {% endif %}



                        {% if version_record.deleted.size > 0 %}

                          <div class="record-section">

                            <div class="record-label">
                              Removed
                            </div>

                            <ul class="record-list">

                              {% for path in version_record.deleted %}
                                <li class="record-deleted">
                                  {{ path }}
                                </li>
                              {% endfor %}

                            </ul>

                          </div>

                        {% endif %}

                      {% endif %}

                    {% else %}

                      <div class="record-note">
                        No record data available.
                      </div>

                    {% endif %}

                  </div>

                </div>



                <details class="version-files-toggle">

                  <summary class="files-summary">
                    Files
                  </summary>


                  <div class="version-files">

                    {% assign version_folders = "" | split: "" %}

                    {% for file in pdf_files %}

                      {% if file.extname == ".pdf" or file.extname == ".PDF" %}

                        {% assign parts = file.path | split: "/" %}
                        {% assign file_date = parts[2] %}

                        {% if file_date == date %}

                          {% assign folder_parts = "" | split: "" %}

                          {% for part in parts %}
                            {% if forloop.index > 3 and forloop.last == false %}
                              {% assign folder_parts = folder_parts | push: part %}
                            {% endif %}
                          {% endfor %}

                          {% capture folder_name %}
                            {{ folder_parts | join: " / " }}
                          {% endcapture %}

                          {% assign folder_name = folder_name | strip %}

                          {% if folder_name == "" %}
                            {% assign folder_name = "General" %}
                          {% endif %}

                          {% unless version_folders contains folder_name %}
                            {% assign version_folders = version_folders | push: folder_name %}
                          {% endunless %}

                        {% endif %}

                      {% endif %}

                    {% endfor %}



                    {% assign last_subject = "" %}

                    {% for folder in version_folders %}

                      {% assign subject_parts = folder | split: " / " %}
                      {% assign current_subject = subject_parts[0] %}

                      {% if current_subject != last_subject %}

                        <div class="subject-divider nested-subject-divider">

                          <div class="subject-title">
                            {{ current_subject | replace: "_", " " }}
                          </div>

                        </div>

                        {% assign last_subject = current_subject %}

                      {% endif %}


                      <details class="academic-folder nested-folder">

                        <summary class="folder-summary">

                          <span class="folder-label">
                            {{ folder | replace: "_", " " }}
                          </span>

                        </summary>


                        <ul class="file-list">

                          {% for file in pdf_files %}

                            {% if file.extname == ".pdf" or file.extname == ".PDF" %}

                              {% assign parts = file.path | split: "/" %}
                              {% assign file_date = parts[2] %}

                              {% if file_date == date %}

                                {% assign current_folder_parts = "" | split: "" %}

                                {% for part in parts %}
                                  {% if forloop.index > 3 and forloop.last == false %}
                                    {% assign current_folder_parts = current_folder_parts | push: part %}
                                  {% endif %}
                                {% endfor %}

                                {% capture current_folder %}
                                  {{ current_folder_parts | join: " / " }}
                                {% endcapture %}

                                {% assign current_folder = current_folder | strip %}

                                {% if current_folder == "" %}
                                  {% assign current_folder = "General" %}
                                {% endif %}

                                {% if current_folder == folder %}

                                  <li class="file-item">

                                    <a
                                      href="{{ file.path | relative_url }}"
                                      target="_blank"
                                      class="file-link"
                                    >
                                      {{ file.basename }}
                                    </a>

                                  </li>

                                {% endif %}

                              {% endif %}

                            {% endif %}

                          {% endfor %}

                        </ul>

                      </details>

                    {% endfor %}

                  </div>

                </details>

              </div>

            </details>

          {% endunless %}

        {% endfor %}

      </div>

    </details>

  {% endif %}

</div>



<style>

/* =====================================================
   Container
   ===================================================== */

.academic-tree-container {
  font-family: "Times New Roman", Times, serif;
  line-height: 1.6;
  max-width: 100%;
  margin: 2rem 0;
  color: #1a1a1a;
}


/* =====================================================
   Ink accent color
   ===================================================== */

:root {
  --ink-accent: #0b84c6;
}


/* =====================================================
   Overall Total Ink
   ===================================================== */

.overall-ink-banner {
  margin: 1.3rem 0 2.2rem 0;
  padding: 0.8rem 0 1rem 0;
  border-bottom: 1px solid #ddd;
}

.overall-ink-label {
  font-size: 0.95rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #666;
}

.overall-ink-value {
  display: inline-block;
  margin-left: 0.8rem;
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--ink-accent);
  white-space: nowrap;
}


/* =====================================================
   Subject
   ===================================================== */

.subject-divider {
  margin-top: 2.8rem;
  margin-bottom: 0.8rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #ddd;
}

.subject-heading-row {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
}

.subject-title {
  font-size: 0.9rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #777;
}

.subject-ink {
  display: inline-block;
  margin-left: 0.65rem;
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0;
  text-transform: none;
  color: var(--ink-accent);
  white-space: nowrap;
}

.nested-subject-divider {
  margin-top: 2rem;
  margin-bottom: 0.6rem;
}

.version-files > .nested-subject-divider:first-child {
  margin-top: 1rem;
}


/* =====================================================
   Academic folders
   ===================================================== */

.academic-folder {
  margin-bottom: 0.5rem;
  border-bottom: 1px solid #eee;
}

.folder-summary {
  list-style: none !important;
  padding: 0.75rem 0;
  cursor: pointer;
  font-weight: 600;
  font-size: 1.1rem;
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  color: #2c3e50;
}

.folder-summary::-webkit-details-marker {
  display: none;
}

.folder-summary::before {
  content: "\2020";
  margin-right: 12px;
  color: #999;
  font-weight: normal;
  font-family: serif;
}

.academic-folder[open] > .folder-summary::before {
  content: "\2021";
  color: #000;
}

.folder-ink {
  display: inline-block;
  margin-left: 0.55rem;
  font-size: 0.72em;
  font-weight: 600;
  color: var(--ink-accent);
  white-space: nowrap;
}


/* =====================================================
   PDF files
   ===================================================== */

.academic-tree-container .file-list {
  list-style: none !important;
  padding: 0 0 1rem 1.5rem !important;
  margin: 0 !important;
}

.academic-tree-container .file-item {
  margin: 0.4rem 0 !important;
  padding-left: 1.2rem !important;
  position: relative !important;
  list-style: none !important;
}

.academic-tree-container .file-item::before {
  content: "\2013" !important;
  position: absolute !important;
  left: 0 !important;
  color: #999 !important;
}

.file-link {
  text-decoration: none !important;
  color: #555 !important;
  font-size: 0.95rem !important;
}

.file-link:hover {
  color: #000 !important;
  text-decoration: underline !important;
  text-underline-offset: 3px;
}

.file-ink {
  display: inline-block;
  margin-left: 0.45rem;
  font-size: 0.75rem;
  color: #aaa;
  white-space: nowrap;
}


/* =====================================================
   Record
   ===================================================== */

.record-content {
  padding: 0.8rem 0 0.5rem 1.3rem;
}

.record-section {
  margin-bottom: 0.9rem;
}

.record-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #777;
  margin-bottom: 0.25rem;
}

.record-note {
  font-size: 0.85rem;
  color: #888;
  font-style: italic;
}

.academic-tree-container .record-list {
  list-style: none !important;
  margin: 0 !important;
  padding: 0 0 0 1rem !important;
}

.academic-tree-container .record-list li {
  position: relative !important;
  list-style: none !important;
  margin: 0.25rem 0 !important;
  padding-left: 1.3rem !important;
  font-size: 0.85rem;
  color: #777;
  overflow-wrap: anywhere;
}

.academic-tree-container .record-list li::marker {
  content: "";
}

.record-added::before {
  content: "+";
  position: absolute;
  left: 0;
}

.record-modified::before {
  content: "~";
  position: absolute;
  left: 0;
}

.record-deleted::before {
  content: "\2212";
  position: absolute;
  left: 0;
}

.record-moved::before {
  content: "\2192";
  position: absolute;
  left: 0;
}

.record-arrow {
  display: inline-block;
  margin: 0 0.45rem;
  color: #aaa;
}

.record-move-from {
  color: #888;
}

.record-move-to {
  color: #666;
}


/* =====================================================
   Ink in Record
   ===================================================== */

.ink-added {
  display: inline-block;
  margin-left: 0.45rem;
  font-size: 0.80em;
  font-weight: normal;
  color: #aaa;
  white-space: nowrap;
}

.record-total-ink {
  display: inline-block;
  margin-left: 0.65rem;
  font-size: 0.78em;
  font-weight: normal;
  color: #aaa;
  white-space: nowrap;
}


/* =====================================================
   Latest Record
   ===================================================== */

.change-record {
  margin: 1rem 0 1.5rem 0;
}

.latest-record {
  margin-top: 2rem;
}

.record-summary {
  list-style: none !important;
  cursor: pointer;
  font-size: 0.9rem;
  color: #888;
  font-weight: 600;
}

.record-summary::-webkit-details-marker {
  display: none;
}

.record-summary::before {
  content: "\25B8";
  display: inline-block;
  margin-right: 8px;
  transition: transform 0.15s;
}

.change-record[open] > .record-summary::before {
  transform: rotate(90deg);
}


/* =====================================================
   Previous versions
   ===================================================== */

.previous-versions {
  margin-top: 2rem;
  padding-top: 1rem;
  border-top: 1px solid #ddd;
}

.previous-summary,
.version-summary,
.files-summary {
  list-style: none !important;
  cursor: pointer;
  color: #777;
  font-weight: 600;
}

.previous-summary {
  font-size: 0.95rem;
}

.version-summary {
  font-size: 0.95rem;
}

.files-summary {
  font-size: 0.9rem;
}

.previous-summary::-webkit-details-marker,
.version-summary::-webkit-details-marker,
.files-summary::-webkit-details-marker {
  display: none;
}

.previous-summary::before,
.version-summary::before,
.files-summary::before {
  content: "\25B8";
  display: inline-block;
  margin-right: 8px;
  transition: transform 0.15s;
}

.previous-versions[open] > .previous-summary::before,
.version-folder[open] > .version-summary::before,
.version-files-toggle[open] > .files-summary::before {
  transform: rotate(90deg);
}

.previous-version-list {
  margin-top: 0.8rem;
  padding-left: 1rem;
}

.version-folder {
  margin: 0.45rem 0;
}

.version-content {
  padding-left: 1.2rem;
  margin-top: 0.6rem;
}


/* =====================================================
   Previous Record
   ===================================================== */

.record-static {
  margin-top: 0.8rem;
  margin-bottom: 1.4rem;
}

.record-heading {
  font-size: 0.95rem;
  font-weight: 600;
  color: #666;
  margin-bottom: 0.35rem;
}

.record-static .record-content {
  padding: 0.4rem 0 0.5rem 1.2rem;
}


/* =====================================================
   Previous Files
   ===================================================== */

.version-files-toggle {
  margin-top: 1.2rem;
  padding-top: 0.9rem;
  border-top: 1px solid #eee;
}

.version-files {
  margin-top: 0.8rem;
}

.nested-folder .folder-summary {
  font-size: 0.95rem;
  padding: 0.4rem 0;
}


/* =====================================================
   Mobile
   ===================================================== */

@media (max-width: 600px) {

  .overall-ink-banner {
    margin-top: 1rem;
    margin-bottom: 1.8rem;
  }

  .overall-ink-label {
    font-size: 0.85rem;
  }

  .overall-ink-value {
    font-size: 0.92rem;
  }

  .subject-divider {
    margin-top: 2.2rem;
  }

  .subject-title {
    font-size: 0.82rem;
  }

  .subject-ink {
    font-size: 0.72rem;
  }

  .folder-summary {
    font-size: 1rem;
  }

  .folder-ink {
    font-size: 0.68em;
  }

  .file-link {
    font-size: 0.9rem !important;
  }

  .file-ink {
    font-size: 0.7rem;
  }

  .previous-version-list {
    padding-left: 0.5rem;
  }

  .version-content {
    padding-left: 0.7rem;
  }

  .record-content {
    padding-left: 0.8rem;
  }

  .record-static .record-content {
    padding-left: 0.7rem;
  }

}

</style>