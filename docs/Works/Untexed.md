---
layout: default
title: Handwritten notes
has_children: true
nav_order: 6
---

# Handwritten notes yet to be TeXed.

{% assign pdf_files = site.static_files | where_exp: "item", "item.path contains '/untexed/'" | sort: "path" %}

<div class="academic-tree-container">
{% assign last_folder_str = "" %}
{% assign first_folder = true %}

{% for file in pdf_files %}
  {% if file.extname == ".pdf" or file.extname == ".PDF" %}
    
    {% assign current_path_parts = file.path | split: "/" %}
    
    {% assign folder_parts = "" | split: "/" %}
    {% for part in current_path_parts %}
      {% if forloop.index > 2 and forloop.last == false %}
        {% assign folder_parts = folder_parts | push: part %}
      {% endif %}
    {% endfor %}
    
    {% capture current_folder_str %}{{ folder_parts | join: " / " }}{% endcapture %}
    {% if current_folder_str == "" %}{% assign current_folder_str = "General" %}{% endif %}

    {% if current_folder_str != last_folder_str %}
      {% if first_folder == false %}
        </ul>
        </details>
      {% endif %}
      
      <details class="academic-folder">
        <summary class="folder-summary">
          <span class="folder-label">{{ current_folder_str | replace: "_", " " }}</span>
        </summary>
        <ul class="file-list">
      {% assign last_folder_str = current_folder_str %}
      {% assign first_folder = false %}
    {% endif %}

    <li class="file-item">
      <a href="{{ file.path | relative_url }}" target="_blank" class="file-link">
        {{ file.basename }}
      </a>
    </li>

  {% endif %}
{% endfor %}

{% if first_folder == false %}
    </ul>
  </details>
{% endif %}
</div>

<style>
  /* 전체 컨테이너 */
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

  /* 폴더 요약 스타일 */
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
  
  .folder-summary::-webkit-details-marker { display: none; }

  /* 대거 기호 († / ‡) */
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

  /* 파일 리스트 스타일 */
  .academic-tree-container .file-list {
    list-style: none !important; /* 테마 불렛 강제 제거 */
    padding: 0 0 1rem 1.5rem !important;
    margin: 0 !important;
  }

  /* 하이픈(-) 적용 핵심 로직 */
  .academic-tree-container .file-item {
    margin: 0.4rem 0 !important;
    padding-left: 1.2rem !important; /* 하이픈이 들어갈 공간 확보 */
    position: relative !important;
    list-style: none !important;
  }

  .academic-tree-container .file-item::before {
    content: "\2013" !important; /* 학술적으로 더 예쁜 En-dash(–) 사용 */
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
    .folder-summary { font-size: 1rem; }
    .file-link { font-size: 0.9rem; }
  }
</style>