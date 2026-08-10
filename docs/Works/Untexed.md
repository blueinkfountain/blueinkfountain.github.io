---
layout: default
title: UnTexed
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
  /* 전체 컨테이너: 학술적 세리프체 설정 */
  .academic-tree-container { 
    font-family: "Times New Roman", Times, serif;
    line-height: 1.6;
    max-width: 100%;
    margin: 2rem 0;
    color: #1a1a1a;
  }

  /* 폴더 섹션 간격 및 구분선 */
  .academic-folder {
    margin-bottom: 0.5rem;
    border-bottom: 1px solid #eee;
  }

  /* 폴더 제목 스타일 및 기본 화살표 제거 */
  .folder-summary {
    list-style: none; /* Firefox */
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

  /* 닫힌 상태: 대거 기호 (†) */
  .folder-summary::before {
    content: "\2020";
    margin-right: 12px;
    color: #999;
    font-weight: normal;
    font-family: serif;
    transition: color 0.2s;
  }

  /* 열린 상태: 더블 대거 기호 (‡) */
  .academic-folder[open] .folder-summary::before {
    content: "\2021";
    color: #000;
  }

  /* 파일 리스트: 불렛 제거 및 들여쓰기 */
  .file-list {
    list-style: none;
    padding: 0 0 1rem 1.8rem;
    margin: 0;
  }

  /* 파일 항목: 하이픈(-) 표시 */
  .file-item {
    margin: 0.4rem 0;
    position: relative;
  }

  .file-item::before {
    content: "-";
    position: absolute;
    left: -1.2rem;
    color: #999;
  }

  /* 파일 링크 스타일 */
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

  /* 모바일 대응 폰트 조정 */
  @media (max-width: 600px) {
    .folder-summary { font-size: 1rem; }
    .file-link { font-size: 0.9rem; }
  }
</style>