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

{%- comment -%}
  날짜 목록 수집
{%- endcomment -%}

{% assign dates = "" | split: "" %}

{% for file in pdf_files %}
  {% if file.extname == ".pdf" or file.extname == ".PDF" %}
    {% assign path_parts = file.path | split: "/" %}
    {% assign file_date = path_parts[2] %}

    {% unless dates contains file_date %}
      {% assign dates = dates | push: file_date %}
    {% endunless %}
  {% endif %}
{% endfor %}

{% assign dates = dates | sort | reverse %}
{% assign latest_date = dates[0] %}


<div class="academic-tree-container">

  {%- comment -%}
    =====================================================
    최신 버전
    =====================================================
  {%- endcomment -%}

  {% assign last_folder_str = "" %}
  {% assign first_folder = true %}

  {% for file in pdf_files %}

    {% if file.extname == ".pdf" or file.extname == ".PDF" %}

      {% assign current_path_parts = file.path | split: "/" %}
      {% assign file_date = current_path_parts[2] %}

      {% if file_date == latest_date %}

        {% assign folder_parts = "" | split: "" %}

        {% for part in current_path_parts %}
          {% if forloop.index > 3 and forloop.last == false %}
            {% assign folder_parts = folder_parts | push: part %}
          {% endif %}
        {% endfor %}

        {% capture current_folder_str %}
          {{ folder_parts | join: " / " }}
        {% endcapture %}

        {% assign current_folder_str = current_folder_str | strip %}

        {% if current_folder_str == "" %}
          {% assign current_folder_str = "General" %}
        {% endif %}


        {% if current_folder_str != last_folder_str %}

          {% if first_folder == false %}
            </ul>
            </details>
          {% endif %}

          <details class="academic-folder">
            <summary class="folder-summary">
              <span class="folder-label">
                {{ current_folder_str | replace: "_", " " }}
              </span>
            </summary>

            <ul class="file-list">

          {% assign last_folder_str = current_folder_str %}
          {% assign first_folder = false %}

        {% endif %}


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

  {% endfor %}


  {% if first_folder == false %}
    </ul>
    </details>
  {% endif %}


  {%- comment -%}
    =====================================================
    이전 버전
    =====================================================
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

                {% assign last_folder_str = "" %}
                {% assign first_folder = true %}

                {% for file in pdf_files %}

                  {% if file.extname == ".pdf" or file.extname == ".PDF" %}

                    {% assign current_path_parts = file.path | split: "/" %}
                    {% assign file_date = current_path_parts[2] %}

                    {% if file_date == date %}

                      {% assign folder_parts = "" | split: "" %}

                      {% for part in current_path_parts %}
                        {% if forloop.index > 3 and forloop.last == false %}
                          {% assign folder_parts = folder_parts | push: part %}
                        {% endif %}
                      {% endfor %}

                      {% capture current_folder_str %}
                        {{ folder_parts | join: " / " }}
                      {% endcapture %}

                      {% assign current_folder_str = current_folder_str | strip %}

                      {% if current_folder_str == "" %}
                        {% assign current_folder_str = "General" %}
                      {% endif %}


                      {% if current_folder_str != last_folder_str %}

                        {% if first_folder == false %}
                          </ul>
                          </details>
                        {% endif %}

                        <details class="academic-folder nested-folder">

                          <summary class="folder-summary">
                            <span class="folder-label">
                              {{ current_folder_str | replace: "_", " " }}
                            </span>
                          </summary>

                          <ul class="file-list">

                        {% assign last_folder_str = current_folder_str %}
                        {% assign first_folder = false %}

                      {% endif %}


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

                {% endfor %}


                {% if first_folder == false %}
                  </ul>
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


<style>

  .academic-tree-container { 
    font-family: "Times New Roman", Times, serif;
    line-height: 1.6;
    max-width: 100%;
    margin: 2rem 0;
    color: #1a1a1a;
  }

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
    align-items: center;
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

  .academic-folder[open] .folder-summary::before {
    content: "\2021";
    color: #000;
  }

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
    font-weight: normal !important;
  }

  .file-link {
    text-decoration: none !important;
    color: #555 !important;
    font-size: 0.95rem !important;
    transition: all 0.2s;
  }

  .file-link:hover {
    color: #000 !important;
    text-decoration: underline !important;
    text-underline-offset: 3px;
  }


  /* ================================
     Previous versions
     ================================ */

  .previous-versions {
    margin-top: 2rem;
    padding-top: 1rem;
    border-top: 1px solid #ddd;
  }

  .previous-summary {
    list-style: none !important;
    cursor: pointer;
    font-size: 0.95rem;
    color: #777;
    font-weight: 600;
  }

  .previous-summary::-webkit-details-marker {
    display: none;
  }

  .previous-summary::before {
    content: "\25B8";
    display: inline-block;
    margin-right: 8px;
    transition: transform 0.15s;
  }

  .previous-versions[open] > .previous-summary::before {
    transform: rotate(90deg);
  }

  .previous-version-list {
    margin-top: 0.8rem;
    padding-left: 1rem;
  }

  .version-folder {
    margin: 0.35rem 0;
  }

  .version-summary {
    list-style: none !important;
    cursor: pointer;
    color: #777;
    font-size: 0.95rem;
  }

  .version-summary::-webkit-details-marker {
    display: none;
  }

  .version-summary::before {
    content: "\25B8";
    display: inline-block;
    margin-right: 8px;
    transition: transform 0.15s;
  }

  .version-folder[open] > .version-summary::before {
    transform: rotate(90deg);
  }

  .version-content {
    padding-left: 1.2rem;
    margin-top: 0.4rem;
  }

  .nested-folder .folder-summary {
    font-size: 0.95rem;
    padding: 0.4rem 0;
  }


  @media (max-width: 600px) {

    .folder-summary {
      font-size: 1rem;
    }

    .file-link {
      font-size: 0.9rem;
    }

  }

</style>