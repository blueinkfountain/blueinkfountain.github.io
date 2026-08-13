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
  ---------------------------------------------------------
  1. /untexed/ 바로 아래의 날짜 폴더 중 최신 날짜를 찾는다.

  예:
  /untexed/260813/Algebra/1. Linear Algebra/foo.pdf

  split 결과:
    [0] = ""
    [1] = "untexed"
    [2] = "260813"
    [3] = "Algebra"
    [4] = "1. Linear Algebra"
    [5] = "foo.pdf"

  따라서 path_parts[2]가 날짜이다.
  ---------------------------------------------------------
{%- endcomment -%}

{% assign latest_date = "" %}

{% for file in pdf_files %}
  {% if file.extname == ".pdf" or file.extname == ".PDF" %}

    {% assign path_parts = file.path | split: "/" %}
    {% assign file_date = path_parts[2] %}

    {% if file_date > latest_date %}
      {% assign latest_date = file_date %}
    {% endif %}

  {% endif %}
{% endfor %}


{%- comment -%}
  ---------------------------------------------------------
  2. 최신 날짜 폴더에 속한 PDF만 출력한다.

  날짜 폴더 자체(260813)는 표시하지 않고,
  그 아래 폴더부터 트리를 구성한다.

  예:
  /untexed/260813/Algebra/1. Linear Algebra/foo.pdf

  화면:
  Algebra / 1. Linear Algebra
      – foo
  ---------------------------------------------------------
{%- endcomment -%}

<div class="academic-tree-container">

{% assign last_folder_str = "" %}
{% assign first_folder = true %}

{% for file in pdf_files %}

  {% if file.extname == ".pdf" or file.extname == ".PDF" %}

    {% assign current_path_parts = file.path | split: "/" %}
    {% assign file_date = current_path_parts[2] %}

    {% if file_date == latest_date %}

      {% assign folder_parts = "" | split: "/" %}

      {% for part in current_path_parts %}

        {%- comment -%}
          index:
          1 -> ""
          2 -> untexed
          3 -> 날짜
          4 이후 -> 실제 분류 폴더

          따라서 날짜 폴더까지 제외하고,
          파일명도 제외한다.
        {%- endcomment -%}

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

  @media (max-width: 600px) {

    .folder-summary {
      font-size: 1rem;
    }

    .file-link {
      font-size: 0.9rem;
    }

  }

</style>