---
layout: default
title: Handwritten
has_children: true
nav_order: 3
---
<link rel="stylesheet" href="{{ '/assets/css/handwritten.css' | relative_url }}">


# Handwritten notes.

{% assign untexed_data = site.data.untexed_records %}
{% assign latest_date = untexed_data.latest_date %}
{% assign dates = untexed_data.dates %}
{% assign records = untexed_data.records %}
{% assign latest_record = records[latest_date] %}


<div class="academic-tree-container">


  {%- comment -%}
  =========================================================
  Absolute Total Ink
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
  Latest snapshot
  =========================================================
  {%- endcomment -%}

  {% if latest_record %}

    {% for subject in latest_record.subjects %}

      <div class="subject-divider">

        <div class="subject-heading-row">

          <div class="subject-title">
            {{ subject.name | replace: "_", " " }}
          </div>

          {% if subject.ink_added_percent > 0 %}

            <span class="subject-ink">
              +{{ subject.ink_added_percent }}% ink
            </span>

          {% endif %}

        </div>

      </div>


      {% if subject.files.size > 0 %}

        <ul class="file-list subject-direct-files">

          {% for file in subject.files %}

            <li class="file-item">

              <a
                href="{{ file.url | relative_url }}"
                target="_blank"
                class="file-link"
              >
                {{ file.name }}
              </a>

              {% if file.total_ink_percent != nil %}
                <span class="file-total-ink">
                  {{ file.total_ink_percent }}%
                </span>
              {% endif %}

            </li>

          {% endfor %}

        </ul>

      {% endif %}


      {% for folder in subject.folders %}
        {% include untexed_folder.html node=folder mode="latest" %}
      {% endfor %}

    {% endfor %}

  {% endif %}



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

          <span class="record-change-summary">

            {% if latest_record.added.size > 0 %}
              <span class="record-change-count">
                {{ latest_record.added.size }} added
              </span>
            {% endif %}

            {% if latest_record.modified.size > 0 %}
              <span class="record-change-count">
                {{ latest_record.modified.size }} modified
              </span>
            {% endif %}

            {% if latest_record.moved_renamed.size > 0 %}
              <span class="record-change-count">
                {{ latest_record.moved_renamed.size }} moved
              </span>
            {% endif %}

            {% if latest_record.deleted.size > 0 %}
              <span class="record-change-count">
                {{ latest_record.deleted.size }} removed
              </span>
            {% endif %}

            {% if latest_record.added.size == 0 and latest_record.modified.size == 0 and latest_record.moved_renamed.size == 0 and latest_record.deleted.size == 0 %}
              <span class="record-change-count">
                no changes
              </span>
            {% endif %}

          </span>

          {% if latest_record.note %}
            <span class="record-daily-note">
              — {{ latest_record.note | escape }}
            </span>
          {% endif %}

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

            <details class="record-section record-collapsible-section">

              <summary class="record-label record-collapsible-summary">
                <span>
                  Moved / Renamed
                </span>

                <span class="record-collapsible-count">
                  {{ latest_record.moved_renamed.size }}
                </span>
              </summary>

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

            </details>

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

  Historical PDFs themselves are NOT on GitHub.
  The lists below come entirely from YAML generated locally.
  =========================================================
  {%- endcomment -%}

  {% if dates.size > 1 %}

    <details class="previous-versions">

      <summary class="previous-summary">
        Previous
      </summary>


      <div class="previous-version-list">

        {% for date in dates %}

          {% unless date == latest_date %}

            {% assign version_record = records[date] %}

            <details class="version-folder">

              <summary class="version-summary">

                <span class="version-date">
                  {{ date }}
                </span>

                {% if version_record %}

                  {% unless version_record.baseline %}

                    <span class="record-total-ink">
                      +{{ version_record.total_ink_percent }}% ink
                    </span>

                    <span class="record-change-summary">

                      {% if version_record.added.size > 0 %}
                        <span class="record-change-count">
                          {{ version_record.added.size }} added
                        </span>
                      {% endif %}

                      {% if version_record.modified.size > 0 %}
                        <span class="record-change-count">
                          {{ version_record.modified.size }} modified
                        </span>
                      {% endif %}

                      {% if version_record.moved_renamed.size > 0 %}
                        <span class="record-change-count">
                          {{ version_record.moved_renamed.size }} moved
                        </span>
                      {% endif %}

                      {% if version_record.deleted.size > 0 %}
                        <span class="record-change-count">
                          {{ version_record.deleted.size }} removed
                        </span>
                      {% endif %}

                      {% if version_record.added.size == 0 and version_record.modified.size == 0 and version_record.moved_renamed.size == 0 and version_record.deleted.size == 0 %}
                        <span class="record-change-count">
                          no changes
                        </span>
                      {% endif %}

                    </span>

                    {% if version_record.note %}
                      <span class="record-daily-note">
                        — {{ version_record.note | escape }}
                      </span>
                    {% endif %}

                  {% else %}

                    <span class="version-baseline-label">
                      baseline
                    </span>

                  {% endunless %}

                {% endif %}

              </summary>


              <div class="version-content">


                {%- comment -%}
                =============================================
                Previous Record
                =============================================
                {%- endcomment -%}

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

                          <details class="record-section record-collapsible-section">

                            <summary class="record-label record-collapsible-summary">
                              <span>
                                Moved / Renamed
                              </span>

                              <span class="record-collapsible-count">
                                {{ version_record.moved_renamed.size }}
                              </span>
                            </summary>

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

                          </details>

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



                {%- comment -%}
                =============================================
                Previous file list
                No links: old PDFs are local-only.
                =============================================
                {%- endcomment -%}

                {% if version_record %}

                  <details class="version-files-toggle">

                    <summary class="files-summary">
                      Files
                    </summary>


                    <div class="version-files">

                      {% for subject in version_record.subjects %}

                        <div class="subject-divider nested-subject-divider">

                          <div class="subject-title">
                            {{ subject.name | replace: "_", " " }}
                          </div>

                        </div>


                        {% if subject.files.size > 0 %}

                          <ul class="file-list subject-direct-files">

                            {% for file in subject.files %}

                              <li class="file-item historical-file-item">

                                <span class="historical-file-name">
                                  {{ file.name }}
                                </span>

                                {% if file.total_ink_percent != nil %}
                                  <span class="file-total-ink">
                                    {{ file.total_ink_percent }}%
                                  </span>
                                {% endif %}

                              </li>

                            {% endfor %}

                          </ul>

                        {% endif %}


                        {% for folder in subject.folders %}
                          {% include untexed_folder.html node=folder mode="historical" %}
                        {% endfor %}

                      {% endfor %}

                    </div>

                  </details>

                {% endif %}


              </div>

            </details>

          {% endunless %}

        {% endfor %}

      </div>

    </details>

  {% endif %}


</div>
