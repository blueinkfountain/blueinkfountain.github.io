---
layout: default
title: UnTexed
parent: Works
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
  .academic-tree-container { 
    font-family: "Times New Roman", Times, serif; /* 학술적 느낌을 위한 세리프체 권장 (시스템에 따라 다름) */
    line-height: 1.6;
    max-width: 100%;
    margin: 2rem 0;
    color: #1a1a1a;
  }

  /* 폴더 섹션 */
  .academic-folder {
    margin-bottom: 0.5rem;
    border-bottom: 1px solid #eee;
  }

  /* 폴더 제목 (Summary) */
/* 1. 기본 화살표 제거 (모든 브라우저 대응) */
  .folder-summary {
    list-style: none; /* Firefox, Standard */
    padding: 0.75rem 0;
    cursor: pointer;
    font-weight: 600;
    font-size: 1.1rem;
    display: flex;
    align-items: center;
    color: #2c3e50;
  }
  .folder-summary::-webkit-details-marker {
    display: none; /* Chrome, Safari */
  }

  /* 2. Dagger 기호 추가 (열기 전: †) */
  .folder-summary::before {
    content: "\2020"; /* Dagger (†) Unicode */
    margin-right: 12px;
    color: #999;
    font-weight: normal;
    font-family: serif;
    transition: all 0.2s;
  }

  /* 3. 폴더가 열렸을 때 기호 변경 (열린 후: ‡) */
  .academic-folder[open] .folder-summary::before {
    content: "\2021"; /* Double Dagger (‡) Unicode */
    color: #000;
  }

  /* 파일 리스트 */
/* 파일 리스트 (점 제거 및 하이픈 추가) */
  .file-list {
    list-style: none; /* 기본 점 제거 */
    padding: 0 0 1rem 1.5rem; 
    margin: 0;
  }

  .file-item {
    margin: 0.4rem 0;
    position: relative;
  }

  /* 하이픈(-) 기호 추가 */
  .file-item::before {
    content: "-"; /* 하이픈 기호 */
    position: absolute;
    left: -1.2rem; /* 하이픈의 위치 조절 */
    color: #999;   /* 기호 색상을 약간 연하게 */
    font-family: "Times New Roman", Times, serif;
  }

  .file-link {
    text-decoration: none;
    color: #555;
    font-size: 0.95rem;
    transition: all 0.2s;
  }

  .file-link:hover {
    color: #000;
    text-decoration: underline;
    text-underline-offset: 3px;
  }

  /* 모바일 대응 */
  @media (max-width: 600px) {
    .folder-summary { font-size: 1rem; }
    .file-link { font-size: 0.9rem; }
  }
</style>